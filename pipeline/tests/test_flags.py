"""Tests for the red flag rules.

The important cases are the negative ones: a rule that fires on everything is
noise, and a rule that treats missing data as a passing value is worse than no
rule at all.
"""

import pytest

from analysis import flags


def year(**overrides):
    """A clean year that trips none of the rules."""
    base = {
        "revenue": 1_800_000_000.0,
        "revenue_growth": 0.08,
        "inventory_growth": 0.06,
        "receivables_growth": 0.07,
        "gross_margin": 0.575,
        "net_income": 170_000_000.0,
        "operating_cash_flow": 240_000_000.0,
        "cash_conversion": 1.41,
        "ebitda": 290_000_000.0,
        "free_cash_flow": 210_000_000.0,
        "fcf_conversion": 0.72,
        "interest_coverage": 25.0,
        "net_debt_to_ebitda": -0.5,
        "net_debt": -145_000_000.0,
        "accruals_ratio": -0.04,
        "days_inventory": 120.0,
        "days_receivables": 22.0,
        "cash_conversion_cycle": 95.0,
    }
    base.update(overrides)
    return base


class TestCleanYear:
    def test_a_healthy_year_raises_nothing(self):
        assert flags.evaluate(year(), year()) == []


class TestInventoryRule:
    def test_fires_when_inventory_outruns_sales(self):
        result = flags.inventory_outpacing_sales(
            year(inventory_growth=1.276, revenue_growth=0.292), year()
        )
        assert result is not None
        assert result["severity"] == "high"
        assert "127.6%" in result["summary"]

    def test_silent_when_the_gap_is_within_tolerance(self):
        assert flags.inventory_outpacing_sales(
            year(inventory_growth=0.14, revenue_growth=0.08), year()
        ) is None

    def test_silent_when_inventory_grows_more_slowly_than_sales(self):
        assert flags.inventory_outpacing_sales(
            year(inventory_growth=0.02, revenue_growth=0.20), year()
        ) is None

    def test_missing_data_does_not_fire(self):
        """A missing figure must never be read as a passing one."""
        assert flags.inventory_outpacing_sales(
            year(inventory_growth=None), year()
        ) is None


class TestMarginRule:
    def test_fires_on_a_material_compression(self):
        result = flags.gross_margin_compression(
            year(gross_margin=0.479), year(gross_margin=0.578)
        )
        assert result is not None
        assert "990 basis points" in result["summary"]

    def test_silent_on_a_small_move(self):
        assert flags.gross_margin_compression(
            year(gross_margin=0.573), year(gross_margin=0.581)
        ) is None

    def test_silent_when_margin_expands(self):
        assert flags.gross_margin_compression(
            year(gross_margin=0.60), year(gross_margin=0.50)
        ) is None

    def test_needs_a_prior_year(self):
        assert flags.gross_margin_compression(year(), None) is None


class TestCashRules:
    def test_earnings_ahead_of_cash_fires(self):
        result = flags.earnings_ahead_of_cash(year(cash_conversion=0.69), year())
        assert result is not None
        assert result["severity"] == "high"

    def test_conversion_ratio_ignored_against_a_loss(self):
        """OCF/NI is meaningless when net income is negative -- the ratio flips
        sign and would fire on a company generating perfectly good cash."""
        assert flags.earnings_ahead_of_cash(
            year(cash_conversion=-2.0, net_income=-50_000_000.0), year()
        ) is None

    def test_negative_free_cash_flow_fires(self):
        result = flags.negative_free_cash_flow(year(free_cash_flow=-40_000_000.0), year())
        assert result is not None

    def test_weak_conversion_fires_below_half_of_ebitda(self):
        result = flags.weak_fcf_conversion(year(fcf_conversion=0.29), year())
        assert result is not None


class TestLeverageRules:
    def test_thin_coverage_fires(self):
        result = flags.thin_interest_coverage(year(interest_coverage=1.8), year())
        assert result is not None
        assert result["severity"] == "high"

    def test_net_cash_business_does_not_trip_the_leverage_rule(self):
        """Net debt is negative when a company holds more cash than debt. That
        must not read as low leverage passing a threshold by accident."""
        assert flags.elevated_leverage(year(net_debt_to_ebitda=-0.98), year()) is None

    def test_high_leverage_fires(self):
        result = flags.elevated_leverage(year(net_debt_to_ebitda=4.4), year())
        assert result is not None


class TestOrdering:
    def test_high_severity_sorts_first(self):
        result = flags.evaluate(
            year(
                inventory_growth=1.276,   # high
                revenue_growth=0.292,
                gross_margin=0.40,        # medium, vs prior below
                accruals_ratio=0.072,     # medium
            ),
            year(gross_margin=0.578),
        )
        severities = [f["severity"] for f in result]
        assert severities == sorted(severities, key=lambda s: flags.SEVERITY_ORDER[s])
        assert severities[0] == "high"

    def test_every_flag_carries_evidence(self):
        result = flags.evaluate(
            year(inventory_growth=1.276, revenue_growth=0.292), year()
        )
        for flag in result:
            assert flag["evidence"], f"{flag['key']} has no evidence"
            assert all("label" in e and "value" in e for e in flag["evidence"])


@pytest.mark.skip(reason="TODO(nick): implement cash_cycle_stretching in flags.py")
class TestCashCycleRule:
    """Waiting on the rule described in the TODO in flags.py.

    Remove the skip marker once it's written and these should pass.
    """

    def test_fires_when_the_cycle_stretches_materially(self):
        rule = getattr(flags, "cash_cycle_stretching")
        result = rule(year(cash_conversion_cycle=118.0), year(cash_conversion_cycle=95.0))
        assert result is not None
        assert "23" in result["summary"]

    def test_silent_on_a_small_change(self):
        rule = getattr(flags, "cash_cycle_stretching")
        assert rule(year(cash_conversion_cycle=99.0), year(cash_conversion_cycle=95.0)) is None

    def test_silent_when_the_cycle_shortens(self):
        rule = getattr(flags, "cash_cycle_stretching")
        assert rule(year(cash_conversion_cycle=70.0), year(cash_conversion_cycle=95.0)) is None
