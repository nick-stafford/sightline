"""Red flag rules.

The scores in scores.py give you a number. These give you a sentence -- the
specific thing in the statements that a person should go look at, and the
figures that triggered it.

Each rule is a function that takes the current and prior year and returns a
flag or None. Adding a rule means writing one function and adding it to RULES.
Thresholds all live in THRESHOLDS so they can be tuned without hunting through
the code.
"""

THRESHOLDS = {
    "growth_gap": 0.10,            # inventory/receivables outgrowing sales by 10pp
    "margin_drop": 0.015,          # 150 bps of gross margin
    "min_interest_coverage": 3.0,  # EBITDA / interest
    "max_net_debt_to_ebitda": 3.0,
    "min_fcf_conversion": 0.50,    # free cash flow / EBITDA
    "min_cash_conversion": 0.80,   # operating cash flow / net income
    "max_accruals": 0.05,
}

HIGH, MEDIUM, LOW = "high", "medium", "low"


def _flag(key, severity, title, summary, evidence):
    return {
        "key": key,
        "severity": severity,
        "title": title,
        "summary": summary,
        "evidence": evidence,
    }


def _pct(value, digits=1):
    return "n/a" if value is None else f"{value * 100:.{digits}f}%"


def _x(value, digits=2):
    return "n/a" if value is None else f"{value:.{digits}f}x"


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

def inventory_outpacing_sales(cur, pri):
    """Inventory building faster than sales is the classic demand-miss signal.

    It usually shows up a quarter or two before the markdowns that follow.
    """
    inv, rev = cur.get("inventory_growth"), cur.get("revenue_growth")
    if None in (inv, rev) or inv - rev <= THRESHOLDS["growth_gap"]:
        return None
    return _flag(
        "inventory_outpacing_sales", HIGH,
        "Inventory growing faster than sales",
        f"Inventory rose {_pct(inv)} while revenue moved {_pct(rev)}, a gap of "
        f"{_pct(inv - rev)}. Stock is building ahead of demand, which typically "
        f"gets resolved through discounting and shows up later as gross margin.",
        [
            {"label": "Inventory growth", "value": _pct(inv)},
            {"label": "Revenue growth", "value": _pct(rev)},
            {"label": "Days inventory", "value": f"{cur.get('days_inventory'):.0f} days"
             if cur.get("days_inventory") else "n/a"},
        ],
    )


def receivables_outpacing_sales(cur, pri):
    """Receivables outrunning revenue means sales are being made on looser terms."""
    rec, rev = cur.get("receivables_growth"), cur.get("revenue_growth")
    if None in (rec, rev) or rec - rev <= THRESHOLDS["growth_gap"]:
        return None
    return _flag(
        "receivables_outpacing_sales", MEDIUM,
        "Receivables growing faster than sales",
        f"Receivables rose {_pct(rec)} against {_pct(rev)} revenue growth. Either "
        f"customers are paying more slowly or terms were loosened to move product. "
        f"Both pull cash out of the business ahead of the income statement.",
        [
            {"label": "Receivables growth", "value": _pct(rec)},
            {"label": "Revenue growth", "value": _pct(rev)},
            {"label": "Days receivables", "value": f"{cur.get('days_receivables'):.0f} days"
             if cur.get("days_receivables") else "n/a"},
        ],
    )


def earnings_ahead_of_cash(cur, pri):
    """Profit that isn't converting to cash."""
    conversion = cur.get("cash_conversion")
    if conversion is None or conversion >= THRESHOLDS["min_cash_conversion"]:
        return None
    if (cur.get("net_income") or 0) <= 0:
        return None  # the ratio isn't meaningful against a loss
    return _flag(
        "earnings_ahead_of_cash", HIGH,
        "Earnings not converting to cash",
        f"Operating cash flow covered only {_x(conversion)} of net income. Reported "
        f"profit is running ahead of the cash actually collected, which is worth "
        f"tracing to working capital.",
        [
            {"label": "Operating cash flow", "value": _money(cur.get("operating_cash_flow"))},
            {"label": "Net income", "value": _money(cur.get("net_income"))},
            {"label": "Conversion", "value": _x(conversion)},
        ],
    )


def gross_margin_compression(cur, pri):
    """A meaningful year-over-year fall in gross margin."""
    if pri is None:
        return None
    cur_gm, pri_gm = cur.get("gross_margin"), pri.get("gross_margin")
    if None in (cur_gm, pri_gm) or pri_gm - cur_gm <= THRESHOLDS["margin_drop"]:
        return None
    return _flag(
        "gross_margin_compression", MEDIUM,
        "Gross margin compressed",
        f"Gross margin fell from {_pct(pri_gm)} to {_pct(cur_gm)}, down "
        f"{(pri_gm - cur_gm) * 10000:.0f} basis points. Worth separating into price, "
        f"input cost and mix before drawing a conclusion.",
        [
            {"label": "Prior gross margin", "value": _pct(pri_gm)},
            {"label": "Current gross margin", "value": _pct(cur_gm)},
        ],
    )


def thin_interest_coverage(cur, pri):
    """EBITDA not comfortably covering interest -- the standard credit test."""
    coverage = cur.get("interest_coverage")
    if coverage is None or coverage >= THRESHOLDS["min_interest_coverage"]:
        return None
    return _flag(
        "thin_interest_coverage", HIGH,
        "Thin interest coverage",
        f"EBITDA covers interest {_x(coverage)}, below the {THRESHOLDS['min_interest_coverage']:.0f}x "
        f"level lenders typically write covenants around. Leaves little room for an "
        f"earnings decline before the capital structure becomes the problem.",
        [
            {"label": "EBITDA", "value": _money(cur.get("ebitda"))},
            {"label": "Coverage", "value": _x(coverage)},
        ],
    )


def elevated_leverage(cur, pri):
    """Net debt large relative to the cash earnings available to service it."""
    ratio = cur.get("net_debt_to_ebitda")
    if ratio is None or ratio <= THRESHOLDS["max_net_debt_to_ebitda"] or ratio < 0:
        return None
    return _flag(
        "elevated_leverage", HIGH,
        "Elevated leverage",
        f"Net debt sits at {_x(ratio)} EBITDA, above the "
        f"{THRESHOLDS['max_net_debt_to_ebitda']:.0f}x level that usually starts to "
        f"constrain what a business can do next.",
        [
            {"label": "Net debt / EBITDA", "value": _x(ratio)},
            {"label": "Net debt", "value": _money(cur.get("net_debt"))},
            {"label": "EBITDA", "value": _money(cur.get("ebitda"))},
        ],
    )


def weak_fcf_conversion(cur, pri):
    """EBITDA that isn't landing as free cash flow after capex and working capital."""
    conversion = cur.get("fcf_conversion")
    if conversion is None or conversion >= THRESHOLDS["min_fcf_conversion"]:
        return None
    if (cur.get("ebitda") or 0) <= 0:
        return None
    return _flag(
        "weak_fcf_conversion", MEDIUM,
        "Weak free cash flow conversion",
        f"Only {_pct(conversion)} of EBITDA reached free cash flow, below the "
        f"{_pct(THRESHOLDS['min_fcf_conversion'], 0)} a business of this type would "
        f"normally convert. The gap is capex and working capital.",
        [
            {"label": "EBITDA", "value": _money(cur.get("ebitda"))},
            {"label": "Free cash flow", "value": _money(cur.get("free_cash_flow"))},
            {"label": "Conversion", "value": _pct(conversion)},
        ],
    )


def negative_free_cash_flow(cur, pri):
    """The business consumed cash after funding its own capex."""
    fcf = cur.get("free_cash_flow")
    if fcf is None or fcf >= 0:
        return None
    return _flag(
        "negative_free_cash_flow", HIGH,
        "Negative free cash flow",
        f"After capital spending the business consumed {_money(abs(fcf))} of cash. "
        f"Sustained, that has to be funded from the balance sheet or from lenders.",
        [
            {"label": "Operating cash flow", "value": _money(cur.get("operating_cash_flow"))},
            {"label": "Free cash flow", "value": _money(fcf)},
        ],
    )


def revenue_contraction(cur, pri):
    """Top line went backwards."""
    growth = cur.get("revenue_growth")
    if growth is None or growth >= 0:
        return None
    return _flag(
        "revenue_contraction", MEDIUM,
        "Revenue declined",
        f"Revenue fell {_pct(abs(growth))} year over year. Check whether the decline "
        f"is volume, price or a discontinued line before treating it as demand.",
        [
            {"label": "Revenue", "value": _money(cur.get("revenue"))},
            {"label": "Change", "value": _pct(growth)},
        ],
    )


def high_accruals(cur, pri):
    """A large accrual component in earnings tends not to persist."""
    accruals = cur.get("accruals_ratio")
    if accruals is None or accruals <= THRESHOLDS["max_accruals"]:
        return None
    return _flag(
        "high_accruals", MEDIUM,
        "High accrual component in earnings",
        f"Accruals ran at {_pct(accruals)} of assets. Research on accruals finds the "
        f"non-cash portion of earnings is the least likely to repeat next year.",
        [{"label": "Accruals / assets", "value": _pct(accruals)}],
    )


# TODO(nick): add a working capital rule here.
#
# The idea: flag when the cash conversion cycle stretches by more than ~15 days
# year over year. That means cash is being tied up in the operating cycle even
# when margins look fine, and it is the sort of thing that only shows up if you
# are looking for it.
#
# cur["cash_conversion_cycle"] and pri["cash_conversion_cycle"] are already
# computed in sql/02_metrics.sql. Write the function the same shape as the ones
# above, add it to RULES, then run: pytest tests/test_flags.py
#
# def cash_cycle_stretching(cur, pri):
#     ...


RULES = [
    inventory_outpacing_sales,
    receivables_outpacing_sales,
    earnings_ahead_of_cash,
    gross_margin_compression,
    thin_interest_coverage,
    elevated_leverage,
    weak_fcf_conversion,
    negative_free_cash_flow,
    revenue_contraction,
    high_accruals,
]

SEVERITY_ORDER = {HIGH: 0, MEDIUM: 1, LOW: 2}


def evaluate(cur, pri):
    """Run every rule against one year. Returns flags sorted by severity."""
    flags = []
    for rule in RULES:
        result = rule(cur, pri)
        if result:
            flags.append(result)
    flags.sort(key=lambda f: SEVERITY_ORDER[f["severity"]])
    return flags


def _money(value):
    if value is None:
        return "n/a"
    if abs(value) >= 1e9:
        return f"${value / 1e9:,.2f}B"
    return f"${value / 1e6:,.0f}M"
