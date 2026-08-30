"""Financial health scores and red flag rules.

Two published models plus a set of plain-language checks:

- Altman Z''-Score  -- distress risk
- Piotroski F-Score -- 9-point fundamental quality
- Red flags         -- divergences that are worth a human looking at

These are deliberately kept in Python rather than SQL. Each one is a small
function over two years of numbers, which is easy to unit test against a known
case, and the flags in particular read better as prose-shaped code.
"""


def safe_div(numerator, denominator):
    """Divide, returning None instead of blowing up on zero or missing data."""
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def _pct(value, digits=1):
    return None if value is None else round(value * 100, digits)


# ---------------------------------------------------------------------------
# Altman Z''-Score
# ---------------------------------------------------------------------------

def altman_z(row):
    """Altman Z''-Score, the variant built for non-manufacturers.

    Z'' = 6.56*A + 3.26*B + 6.72*C + 1.05*D

        A = working capital / total assets
        B = retained earnings / total assets
        C = EBIT / total assets
        D = book equity / total liabilities

    The original 1968 Z-Score has a fifth term (sales / total assets), which
    Altman dropped here because asset turnover varies so much by industry that
    it made cross-sector comparison meaningless. That matters for a retailer
    like YETI, whose turnover would distort the original model.

    Note there is also an emerging-markets version that adds a constant of
    +3.25. YETI is a US filer, so it does not apply -- adding it would push
    every company in the cohort a full zone toward "safe".

    Zones: above 2.6 safe, 1.1 to 2.6 grey, below 1.1 distress.
    """
    total_assets = row.get("total_assets")
    if not total_assets:
        return None

    working_capital = None
    if row.get("current_assets") is not None and row.get("current_liabilities") is not None:
        working_capital = row["current_assets"] - row["current_liabilities"]

    a = safe_div(working_capital, total_assets)
    b = safe_div(row.get("retained_earnings"), total_assets)
    c = safe_div(row.get("ebit"), total_assets)
    d = safe_div(row.get("equity"), row.get("total_liabilities"))

    if None in (a, b, c, d):
        return None

    score = 6.56 * a + 3.26 * b + 6.72 * c + 1.05 * d

    if score > 2.6:
        zone = "safe"
    elif score >= 1.1:
        zone = "grey"
    else:
        zone = "distress"

    return {
        "score": round(score, 2),
        "zone": zone,
        "components": [
            {"key": "working_capital_to_assets", "label": "Working Capital / Assets",
             "value": round(a, 4), "weight": 6.56, "contribution": round(6.56 * a, 2)},
            {"key": "retained_earnings_to_assets", "label": "Retained Earnings / Assets",
             "value": round(b, 4), "weight": 3.26, "contribution": round(3.26 * b, 2)},
            {"key": "ebit_to_assets", "label": "EBIT / Assets",
             "value": round(c, 4), "weight": 6.72, "contribution": round(6.72 * c, 2)},
            {"key": "equity_to_liabilities", "label": "Equity / Total Liabilities",
             "value": round(d, 4), "weight": 1.05, "contribution": round(1.05 * d, 2)},
        ],
    }


# ---------------------------------------------------------------------------
# Piotroski F-Score
# ---------------------------------------------------------------------------

def piotroski(current, prior):
    """Piotroski F-Score: nine pass/fail tests, one point each.

    Piotroski scales by *beginning* of year total assets rather than the
    average, so ROA here is computed against the prior year's closing balance
    on purpose -- it won't match the ROA in the metrics table, which uses the
    average. 8-9 is strong, 0-2 is weak.
    """
    if prior is None:
        return None

    opening_assets = prior.get("total_assets")

    roa = safe_div(current.get("net_income"), opening_assets)
    prior_roa = safe_div(prior.get("net_income"), prior.get("prior_total_assets"))
    cfo_to_assets = safe_div(current.get("operating_cash_flow"), opening_assets)

    leverage = safe_div(current.get("long_term_debt"), current.get("total_assets"))
    prior_leverage = safe_div(prior.get("long_term_debt"), prior.get("total_assets"))

    current_ratio = safe_div(current.get("current_assets"), current.get("current_liabilities"))
    prior_current_ratio = safe_div(prior.get("current_assets"), prior.get("current_liabilities"))

    gross_margin = safe_div(current.get("gross_profit"), current.get("revenue"))
    prior_gross_margin = safe_div(prior.get("gross_profit"), prior.get("revenue"))

    turnover = safe_div(current.get("revenue"), opening_assets)
    prior_turnover = safe_div(prior.get("revenue"), prior.get("prior_total_assets"))

    shares = current.get("shares_diluted")
    prior_shares = prior.get("shares_diluted")

    signals = [
        _signal("roa_positive", "Profitability", "Return on assets is positive",
                roa is not None and roa > 0, f"ROA {_pct(roa)}%" if roa is not None else "n/a"),
        _signal("cfo_positive", "Profitability", "Operating cash flow is positive",
                (current.get("operating_cash_flow") or 0) > 0,
                _money(current.get("operating_cash_flow"))),
        _signal("roa_improving", "Profitability", "Return on assets improved",
                None not in (roa, prior_roa) and roa > prior_roa,
                f"{_pct(prior_roa)}% to {_pct(roa)}%" if None not in (roa, prior_roa) else "n/a"),
        _signal("accruals_clean", "Profitability", "Cash flow exceeds net income",
                None not in (cfo_to_assets, roa) and cfo_to_assets > roa,
                "Earnings backed by cash" if None not in (cfo_to_assets, roa) and cfo_to_assets > roa
                else "Earnings running ahead of cash"),
        _signal("leverage_falling", "Leverage", "Long-term debt ratio did not rise",
                None not in (leverage, prior_leverage) and leverage <= prior_leverage,
                f"{_pct(prior_leverage)}% to {_pct(leverage)}% of assets"
                if None not in (leverage, prior_leverage) else "n/a"),
        _signal("liquidity_rising", "Leverage", "Current ratio improved",
                None not in (current_ratio, prior_current_ratio) and current_ratio > prior_current_ratio,
                f"{prior_current_ratio:.2f}x to {current_ratio:.2f}x"
                if None not in (current_ratio, prior_current_ratio) else "n/a"),
        _signal("no_dilution", "Leverage", "No net new shares issued",
                None not in (shares, prior_shares) and shares <= prior_shares * 1.01,
                f"{prior_shares/1e6:.1f}M to {shares/1e6:.1f}M diluted shares"
                if None not in (shares, prior_shares) else "n/a"),
        _signal("margin_rising", "Efficiency", "Gross margin expanded",
                None not in (gross_margin, prior_gross_margin) and gross_margin > prior_gross_margin,
                f"{_pct(prior_gross_margin)}% to {_pct(gross_margin)}%"
                if None not in (gross_margin, prior_gross_margin) else "n/a"),
        _signal("turnover_rising", "Efficiency", "Asset turnover improved",
                None not in (turnover, prior_turnover) and turnover > prior_turnover,
                f"{prior_turnover:.2f}x to {turnover:.2f}x"
                if None not in (turnover, prior_turnover) else "n/a"),
    ]

    score = sum(1 for s in signals if s["passed"])

    if score >= 8:
        band = "strong"
    elif score >= 5:
        band = "moderate"
    else:
        band = "weak"

    return {"score": score, "max": 9, "band": band, "signals": signals}


def _signal(key, category, label, passed, detail):
    return {
        "key": key,
        "category": category,
        "label": label,
        "passed": bool(passed),
        "detail": detail,
    }


def _money(value):
    if value is None:
        return "n/a"
    return f"${value/1e6:,.0f}M"
