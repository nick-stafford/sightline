"""Generates the written analysis.

The model does not touch the math. Every number in the memo was computed in SQL
or in scores.py first, handed over as a structured block of facts, and the model
is only asked to turn that into readable analysis. That way the prose can be
wrong about emphasis but it cannot be wrong about a figure.

If there's no GROQ_API_KEY the module falls back to a template that assembles
the same points from the same facts. The page then works identically, it just
reads more mechanically -- so a reviewer cloning this repo never hits a blank
section.
"""

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are a financial analyst writing a short read on a public company \
for a reader who understands financial statements.

Rules you must follow:
- Use ONLY the figures provided. Never introduce a number that is not in the data.
- Never calculate anything new. If a figure is not given, do not imply it.
- Describe what the statements show and what it may indicate. Do not predict \
prices, and do not give investment advice or a buy/sell view.
- Write plainly. No hype, no hedging filler, no bullet lists.
- Three short paragraphs, roughly 180 words total: what happened, what it \
suggests, and what a reader should check next.
"""


def _load_api_key():
    key = os.environ.get("GROQ_API_KEY")
    if key:
        return key
    # Fall back to a local .env so the pipeline runs without exported vars.
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("GROQ_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def build_prompt(facts):
    """Turn the computed analysis into the fact block the model gets."""
    lines = [
        f"Company: {facts['company']} ({facts['ticker']})",
        f"Fiscal year: FY{facts['fy']} (ended {facts['period_end']})",
        "",
        "HEADLINE FIGURES",
        f"- Revenue: {facts['revenue']} ({facts['revenue_growth']} year over year)",
        f"- Gross margin: {facts['gross_margin']} (prior year {facts['prior_gross_margin']})",
        f"- Operating margin: {facts['operating_margin']}",
        f"- Net income: {facts['net_income']}",
        f"- Operating cash flow: {facts['operating_cash_flow']}",
        f"- Free cash flow: {facts['free_cash_flow']}",
        "",
        "HEALTH SCORES",
        f"- Altman Z''-Score: {facts['altman_score']} ({facts['altman_zone']} zone)",
        f"- Piotroski F-Score: {facts['piotroski_score']} of 9 ({facts['piotroski_band']})",
        "",
        "PEER STANDING (percentile within an 8-company apparel and outdoor cohort)",
    ]
    for peer in facts["peer_highlights"]:
        lines.append(f"- {peer['label']}: {peer['value']}, {peer['percentile']} percentile")

    lines.append("")
    if facts["flags"]:
        lines.append("FLAGS RAISED BY THE RULE ENGINE")
        for flag in facts["flags"]:
            lines.append(f"- [{flag['severity']}] {flag['title']}: {flag['summary']}")
    else:
        lines.append("FLAGS RAISED BY THE RULE ENGINE: none this year.")

    return "\n".join(lines)


def _call_groq(api_key, prompt):
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 500,
    }
    request = urllib.request.Request(
        GROQ_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        body = json.loads(response.read())
    return body["choices"][0]["message"]["content"].strip()


def generate(facts):
    """Return {'text', 'source', 'model'} for one company-year."""
    prompt = build_prompt(facts)
    api_key = _load_api_key()

    if api_key:
        try:
            return {
                "text": _call_groq(api_key, prompt),
                "source": "groq",
                "model": GROQ_MODEL,
                "prompt": prompt,
            }
        except (urllib.error.URLError, KeyError, TimeoutError) as err:
            print(f"    LLM call failed ({err}); using template")

    return {
        "text": template_narrative(facts),
        "source": "template",
        "model": None,
        "prompt": prompt,
    }


def template_narrative(facts):
    """Deterministic fallback. Same facts, plainer sentences."""
    direction = "grew" if not facts["revenue_growth"].startswith("-") else "declined"
    paragraphs = []

    paragraphs.append(
        f"{facts['company']} reported revenue of {facts['revenue']} in FY{facts['fy']}, "
        f"which {direction} {facts['revenue_growth'].lstrip('-')} against the prior year. "
        f"Gross margin came in at {facts['gross_margin']} versus {facts['prior_gross_margin']} "
        f"a year earlier, and the business generated {facts['operating_cash_flow']} of "
        f"operating cash flow against {facts['net_income']} of net income."
    )

    flag_count = len(facts["flags"])
    if flag_count:
        titles = ", ".join(f["title"].lower() for f in facts["flags"][:3])
        flag_sentence = f"The rule engine raised {flag_count} flag{'s' if flag_count > 1 else ''} this year: {titles}."
    else:
        flag_sentence = "The rule engine raised no flags this year."

    paragraphs.append(
        f"The Altman Z''-Score of {facts['altman_score']} places the company in the "
        f"{facts['altman_zone']} zone for distress risk, and the Piotroski F-Score of "
        f"{facts['piotroski_score']} of 9 reads as {facts['piotroski_band']} on fundamental "
        f"quality. {flag_sentence}"
    )

    paragraphs.append(
        "Read these as screening signals rather than conclusions. The scores are "
        "published academic models applied to reported figures, and they describe "
        "what the statements show, not what management intends or what the market "
        "expects. The next step is the filing itself, specifically the segment detail "
        "and the discussion of margin drivers."
    )

    return "\n\n".join(paragraphs)
