"""Build the analysis and write the JSON the web page reads.

    python build.py

Pipeline: cached SEC filings -> normalize -> DuckDB -> SQL views -> scores and
flags -> written analysis -> web/public/data/*.json

Everything is deterministic apart from the LLM memo, so re-running gives the
same numbers.
"""

import json
import math
import sys
from datetime import datetime, timezone

import duckdb
import pandas as pd

from analysis import flags, narrative, normalize, scores
from analysis.config import (
    CACHE_DIR,
    COHORT,
    DB_PATH,
    DEFAULT_TICKER,
    LINE_ITEMS,
    PIPELINE_DIR,
    SQL_DIR,
    WEB_DATA_DIR,
)


def load_facts():
    """Read every cached filing and normalize it into one long table."""
    rows = []
    for company in COHORT:
        path = CACHE_DIR / f"{company['ticker']}.json"
        if not path.exists():
            sys.exit(f"Missing {path}. Run: python fetch_data.py")
        company_facts = json.loads(path.read_text(encoding="utf-8"))
        rows.extend(normalize.extract_company(company_facts, company["ticker"]))
    return pd.DataFrame(rows)


def build_warehouse(facts_df):
    """Load the facts into DuckDB and run the SQL files in order."""
    if DB_PATH.exists():
        DB_PATH.unlink()

    con = duckdb.connect(str(DB_PATH))
    con.register("facts_df", facts_df)
    con.execute("CREATE TABLE facts AS SELECT * FROM facts_df")
    con.execute("""
        CREATE TABLE companies (ticker VARCHAR, name VARCHAR, brands VARCHAR)
    """)
    con.executemany(
        "INSERT INTO companies VALUES (?, ?, ?)",
        [(c["ticker"], c["name"], c.get("brands", "")) for c in COHORT],
    )

    for sql_file in sorted(SQL_DIR.glob("*.sql")):
        print(f"  running {sql_file.name}")
        con.execute(sql_file.read_text(encoding="utf-8"))

    return con


def rows_for(con, ticker):
    """One dict per fiscal year, raw statement figures joined to the ratios."""
    df = con.execute("""
        SELECT f.*, m.* EXCLUDE (ticker, fy, period_end)
        FROM financials f
        JOIN metrics m USING (ticker, fy)
        WHERE f.ticker = ?
        ORDER BY f.fy
    """, [ticker]).df()

    # NaN has to go before the scores see it: NaN comparisons are always False,
    # so a rule like "is this ratio above the threshold" silently answers no and
    # a missing figure gets treated as a passing one.
    records = clean(df.to_dict("records"))

    # Piotroski scales ROA by opening assets, so each year needs to know the
    # year before it as well as its own prior year.
    for i, row in enumerate(records):
        row["prior_total_assets"] = records[i - 1]["total_assets"] if i > 0 else None

    return records


def analyse(records):
    """Attach the scores and flags to each year."""
    output = []
    for i, row in enumerate(records):
        prior = records[i - 1] if i > 0 else None
        output.append({
            "fy": int(row["fy"]),
            "period_end": row["period_end"],
            "altman": scores.altman_z(row),
            "piotroski": scores.piotroski(row, prior),
            "flags": flags.evaluate(row, prior),
        })
    return output


def peer_table(con, fy):
    """Every company's percentile for the given year."""
    df = con.execute("""
        SELECT p.ticker, c.name, p.metric, p.value, p.percentile, p.higher_is_better
        FROM peer_ranks p
        JOIN companies c USING (ticker)
        WHERE p.fy = ?
        ORDER BY p.metric, p.percentile DESC
    """, [fy]).df()
    return clean(df.to_dict("records"))


PEER_HIGHLIGHTS = [
    ("gross_margin", "Gross margin", "percent"),
    ("ebitda_margin", "EBITDA margin", "percent"),
    ("roic", "ROIC", "percent"),
    ("revenue_growth", "Revenue growth", "percent"),
    ("net_debt_to_ebitda", "Net debt / EBITDA", "multiple"),
    ("fcf_conversion", "FCF conversion", "percent"),
    ("cash_conversion_cycle", "Cash conversion cycle", "days"),
]


def forecast_drivers(records):
    """Starting assumptions for the projection, taken from recent history.

    The page lets the reader move these. Defaults come from the last three
    years so the opening view is the company's own recent behaviour rather than
    a number someone picked.
    """
    recent = records[-3:]

    def avg(key):
        values = [r[key] for r in recent if r.get(key) is not None]
        return round(sum(values) / len(values), 4) if values else None

    latest = records[-1]

    return {
        "base_year": int(latest["fy"]),
        "base_revenue": latest["revenue"],
        "revenue_growth": avg("revenue_growth"),
        "gross_margin": avg("gross_margin"),
        "sga_pct_revenue": avg("sga_pct_revenue"),
        "capex_intensity": avg("capex_intensity"),
        "days_inventory": avg("days_inventory"),
        "days_receivables": avg("days_receivables"),
        "days_payables": avg("days_payables"),
        "da_pct_revenue": round(
            (latest.get("depreciation_amortization") or 0) / latest["revenue"], 4
        ),
        "tax_rate": round(
            (latest.get("tax_expense") or 0) / latest["pretax_income"], 4
        ) if latest.get("pretax_income") else 0.24,
        "opening_cash": latest["cash"],
        "opening_debt": latest["long_term_debt"],
    }


def narrative_facts(company, record, analysis, peers):
    """The fact block handed to the writer. Every figure is pre-computed."""
    def pct(value):
        return "n/a" if value is None else f"{value * 100:.1f}%"

    def money(value):
        if value is None:
            return "n/a"
        return f"${value / 1e9:.2f}B" if abs(value) >= 1e9 else f"${value / 1e6:,.0f}M"

    highlights = []
    by_metric = {p["metric"]: p for p in peers if p["ticker"] == company["ticker"]}
    for key, label, kind in PEER_HIGHLIGHTS:
        peer = by_metric.get(key)
        if not peer:
            continue
        if kind == "percent":
            shown = pct(peer["value"])
        elif kind == "days":
            shown = f"{peer['value']:.0f} days"
        else:
            shown = f"{peer['value']:.2f}x"
        highlights.append({
            "label": label,
            "value": shown,
            "percentile": f"{peer['percentile'] * 100:.0f}th",
        })

    return {
        "company": company["name"],
        "ticker": company["ticker"],
        "fy": analysis["fy"],
        "period_end": analysis["period_end"],
        "revenue": money(record["revenue"]),
        "revenue_growth": pct(record.get("revenue_growth")),
        "gross_margin": pct(record.get("gross_margin")),
        "prior_gross_margin": None,  # filled in by the caller, which has both years
        "operating_margin": pct(record.get("operating_margin")),
        "net_income": money(record["net_income"]),
        "operating_cash_flow": money(record["operating_cash_flow"]),
        "free_cash_flow": money(record.get("free_cash_flow")),
        "altman_score": analysis["altman"]["score"] if analysis["altman"] else "n/a",
        "altman_zone": analysis["altman"]["zone"] if analysis["altman"] else "n/a",
        "piotroski_score": analysis["piotroski"]["score"] if analysis["piotroski"] else "n/a",
        "piotroski_band": analysis["piotroski"]["band"] if analysis["piotroski"] else "n/a",
        "peer_highlights": highlights,
        "flags": analysis["flags"],
    }


def main():
    print("Loading filings...")
    facts_df = load_facts()
    print(f"  {len(facts_df):,} facts across {facts_df.ticker.nunique()} companies")

    print("Building warehouse...")
    con = build_warehouse(facts_df)

    company = next(c for c in COHORT if c["ticker"] == DEFAULT_TICKER)
    records = rows_for(con, DEFAULT_TICKER)
    analysis = analyse(records)
    latest_fy = analysis[-1]["fy"]
    peers = peer_table(con, latest_fy)

    print(f"Writing analysis for {company['name']} FY{latest_fy}...")
    facts_for_writer = narrative_facts(company, records[-1], analysis[-1], peers)
    # The prior year's gross margin is the one comparison the writer needs that
    # isn't in the current year's row.
    prior_gm = records[-2].get("gross_margin") if len(records) > 1 else None
    facts_for_writer["prior_gross_margin"] = (
        "n/a" if prior_gm is None else f"{prior_gm * 100:.1f}%"
    )
    memo = narrative.generate(facts_for_writer)
    print(f"  memo written by: {memo['source']}")

    WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)

    company_payload = {
        "company": company,
        "latest_fy": latest_fy,
        "years": [
            {**{k: v for k, v in record.items() if k != "prior_total_assets"},
             "fy": int(record["fy"])}
            for record in records
        ],
        "analysis": analysis,
        "drivers": forecast_drivers(records),
        "memo": {"text": memo["text"], "source": memo["source"], "model": memo["model"]},
    }
    _write("company.json", company_payload)

    _write("peers.json", {
        "fy": latest_fy,
        "cohort": COHORT,
        "highlights": [{"key": k, "label": l, "format": f} for k, l, f in PEER_HIGHLIGHTS],
        "ranks": peers,
    })

    _write("code.json", {"samples": code_samples()})

    coverage = normalize.coverage_report(
        facts_df[facts_df.ticker == DEFAULT_TICKER].to_dict("records")
    )
    _write("meta.json", {
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "SEC EDGAR XBRL company facts API",
        "line_items_tracked": len(LINE_ITEMS),
        "facts_loaded": len(facts_df),
        "companies": len(COHORT),
        "llm": {"used": memo["source"] == "groq", "model": memo["model"]},
        "coverage": coverage,
    })

    con.close()
    print(f"\nDone. JSON written to {WEB_DATA_DIR}")
    return 0


def extract_block(path, start_marker, stop_prefixes):
    """Pull one function out of a source file, by line.

    The page shows real code from this repo rather than a copy pasted into the
    front end, so the two can't drift apart. Reading it out at build time is the
    simplest way to guarantee that.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    start = next((i for i, line in enumerate(lines) if start_marker in line), None)
    if start is None:
        return f"# could not find {start_marker} in {path.name}"

    end = len(lines)
    for i in range(start + 1, len(lines)):
        if any(lines[i].startswith(prefix) for prefix in stop_prefixes):
            end = i
            break

    return "\n".join(lines[start:end]).rstrip()


def code_samples():
    """The code excerpts shown in the "how this is built" section."""
    pkg = PIPELINE_DIR / "analysis"
    web_src = PIPELINE_DIR.parent / "web" / "src"

    return [
        {
            "key": "sql",
            "label": "SQL — ratio layer",
            "language": "sql",
            "caption": "pipeline/sql/02_metrics.sql — window functions supply the prior "
                       "year so that ratios mixing the balance sheet and income "
                       "statement use average balances.",
            "source": (SQL_DIR / "02_metrics.sql").read_text(encoding="utf-8").strip(),
        },
        {
            "key": "normalize",
            "label": "Python — XBRL normalizer",
            "language": "python",
            "caption": "pipeline/analysis/normalize.py — the filter that reduces every "
                       "filing of a tag to one annual figure per year.",
            "source": extract_block(
                pkg / "normalize.py", "def _annual_facts(", ("def ", "# ---")
            ),
        },
        {
            "key": "scores",
            "label": "Python — Altman Z''",
            "language": "python",
            "caption": "pipeline/analysis/scores.py — the distress model, with the "
                       "reasoning for the variant used.",
            "source": extract_block(pkg / "scores.py", "def altman_z(", ("def ", "# ---")),
        },
        {
            "key": "peers",
            "label": "SQL — peer ranking",
            "language": "sql",
            "caption": "pipeline/sql/03_peers.sql — UNPIVOT to long form, then "
                       "PERCENT_RANK within each fiscal year and metric.",
            "source": (SQL_DIR / "03_peers.sql").read_text(encoding="utf-8").strip(),
        },
        {
            "key": "projection",
            "label": "TypeScript — projection",
            "language": "typescript",
            "caption": "web/src/lib/projection.ts — runs in the browser so the driver "
                       "sliders recompute instantly with no server.",
            "source": extract_block(
                web_src / "lib" / "projection.ts", "export function project(", ("}",)
            ) + "\n}",
        },
    ]


def clean(value):
    """Replace NaN and infinity with None, recursively.

    json.dumps happily writes bare NaN and Infinity, which are not valid JSON --
    the browser's JSON.parse throws on them. Ratios produce both whenever a
    denominator is missing or zero, so everything gets scrubbed on the way out.
    """
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean(v) for v in value]
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def _write(filename, payload):
    path = WEB_DATA_DIR / filename
    path.write_text(json.dumps(clean(payload), indent=2, default=str), encoding="utf-8")
    print(f"  {filename} ({path.stat().st_size / 1000:.0f} KB)")


if __name__ == "__main__":
    sys.exit(main())
