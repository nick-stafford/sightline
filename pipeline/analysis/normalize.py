"""Turn raw XBRL company facts into tidy annual rows.

This is the messy part of the project. A companyfacts file is a few thousand
us-gaap tags, each with quarterly and annual values from every filing the
company has ever made, including restatements of the same period. We want one
clean number per company / fiscal year / line item.

The rules, in order:

1. Only annual figures from 10-Ks. Duration facts must cover ~365 days, which
   also filters out the short "transition period" filings companies produce
   when they change their fiscal year end (VF Corp and Under Armour both did).
2. When a period was reported more than once, keep the most recently filed
   version, so restatements win over the original.
3. Walk the candidate tags in priority order and only fill in years the
   higher-priority tags didn't cover, rather than taking one tag wholesale.
"""

from collections import defaultdict
from datetime import date, timedelta

from .config import LINE_ITEMS, START_YEAR

MIN_DAYS = 340
MAX_DAYS = 400


def _parse(value):
    return date.fromisoformat(value)


def fiscal_year(period_end):
    """Label a fiscal year by the calendar year it mostly falls in.

    Companies label fiscal years inconsistently -- Nike's year ending May 2025
    is "FY2025" to Nike, while Lululemon's year ending Feb 2025 is "FY2024" to
    Lululemon. Comparing them on their own labels lines up periods that are a
    year apart in reality. Shifting back six months and taking the year gives
    one consistent rule across the cohort.
    """
    return (period_end - timedelta(days=182)).year


def _units_for(item_key):
    if item_key == "eps_diluted":
        return "USD/shares"
    if item_key == "shares_diluted":
        return "shares"
    return "USD"


def _annual_facts(company_facts, tag, kind, unit):
    """Pull annual 10-K values for one tag as {period_end: (value, filed)}."""
    tag_data = company_facts.get("facts", {}).get("us-gaap", {}).get(tag)
    if not tag_data:
        return {}

    out = {}
    for entry in tag_data.get("units", {}).get(unit, []):
        if entry.get("form") != "10-K":
            continue

        end = _parse(entry["end"])

        if kind == "duration":
            if not entry.get("start"):
                continue
            days = (end - _parse(entry["start"])).days
            if not MIN_DAYS <= days <= MAX_DAYS:
                continue
        else:
            # Balance sheet facts are instants and carry no start date.
            if entry.get("start"):
                continue

        filed = entry.get("filed", "")
        # Later filing of the same period wins (restatements).
        if end not in out or filed > out[end][1]:
            out[end] = (entry["val"], filed)

    return out


def extract_company(company_facts, ticker):
    """Return tidy rows for one company: ticker, fy, period_end, item, value, tag."""
    # period_end -> {item: (value, tag)}
    by_period = defaultdict(dict)

    for item_key, (kind, _label, tags) in LINE_ITEMS.items():
        unit = _units_for(item_key)
        for tag in tags:
            for period_end, (value, _filed) in _annual_facts(company_facts, tag, kind, unit).items():
                # Only fill years a higher-priority tag didn't already cover.
                if item_key not in by_period[period_end]:
                    by_period[period_end][item_key] = (value, tag)

    # A company's fiscal year end is the date it reports revenue through. Use
    # those dates as the spine so a stray balance sheet date can't invent a year.
    year_ends = sorted(pe for pe, items in by_period.items() if "revenue" in items)

    rows = []
    for period_end in year_ends:
        fy = fiscal_year(period_end)
        if fy < START_YEAR:
            continue
        items = dict(by_period[period_end])
        _fill_derived(items)
        for item_key, (value, tag) in items.items():
            rows.append({
                "ticker": ticker,
                "fy": fy,
                "period_end": period_end.isoformat(),
                "item": item_key,
                "value": float(value),
                "source_tag": tag,
            })

    return rows


def _fill_derived(items):
    """Fill line items a company left untagged but that follow from others."""
    def value(key):
        return items[key][0] if key in items else None

    if "gross_profit" not in items and None not in (value("revenue"), value("cogs")):
        items["gross_profit"] = (value("revenue") - value("cogs"), "derived:revenue-cogs")

    if "cogs" not in items and None not in (value("revenue"), value("gross_profit")):
        items["cogs"] = (value("revenue") - value("gross_profit"), "derived:revenue-gross_profit")

    if "pretax_income" not in items and None not in (value("net_income"), value("tax_expense")):
        items["pretax_income"] = (
            value("net_income") + value("tax_expense"),
            "derived:net_income+tax",
        )

    if "total_liabilities" not in items and None not in (value("total_assets"), value("equity")):
        items["total_liabilities"] = (
            value("total_assets") - value("equity"),
            "derived:assets-equity",
        )


def coverage_report(rows):
    """How complete is each company's data? Used as a build-time sanity check."""
    seen = defaultdict(set)
    for row in rows:
        seen[(row["ticker"], row["fy"])].add(row["item"])

    report = []
    for (ticker, fy), items in sorted(seen.items()):
        missing = sorted(set(LINE_ITEMS) - items)
        report.append({
            "ticker": ticker,
            "fy": fy,
            "items": len(items),
            "missing": missing,
        })
    return report
