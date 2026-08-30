"""Tests for the Altman and Piotroski implementations.

The Altman cases are checked against hand-computed values rather than against
whatever the code currently returns, so a changed coefficient fails the test.
"""

import pytest

from sightline import scores


def company(**overrides):
    """A healthy baseline company. Tests override one thing at a time."""
    base = {
        "total_assets": 1000.0,
        "current_assets": 600.0,
        "current_liabilities": 300.0,
        "retained_earnings": 400.0,
        "ebit": 150.0,
        "equity": 650.0,
        "total_liabilities": 350.0,
        "revenue": 1200.0,
        "gross_profit": 600.0,
        "net_income": 100.0,
        "operating_cash_flow": 120.0,
        "long_term_debt": 100.0,
        "shares_diluted": 87_000_000.0,
        "prior_total_assets": 900.0,
    }
    base.update(overrides)
    return base


class TestAltmanZ:
    def test_matches_a_hand_computed_score(self):
        """Z'' = 6.56*A + 3.26*B + 6.72*C + 1.05*D

        A = (600 - 300) / 1000 = 0.30  -> 1.968
        B = 400 / 1000         = 0.40  -> 1.304
        C = 150 / 1000         = 0.15  -> 1.008
        D = 650 / 350          = 1.857 -> 1.950
                                          -----
                                          6.230
        """
        result = scores.altman_z(company())
        assert result["score"] == pytest.approx(6.23, abs=0.01)
        assert result["zone"] == "safe"

    def test_does_not_include_the_emerging_markets_constant(self):
        """The +3.25 constant belongs to the emerging-markets variant only.

        Including it for a US filer would lift essentially every company into
        the safe zone and make the score meaningless.
        """
        result = scores.altman_z(company())
        assert result["score"] < 7.0

    def test_components_sum_to_the_score(self):
        result = scores.altman_z(company())
        total = sum(c["contribution"] for c in result["components"])
        assert total == pytest.approx(result["score"], abs=0.02)

    def test_distressed_balance_sheet_lands_in_the_distress_zone(self):
        result = scores.altman_z(company(
            current_assets=200.0,      # negative working capital
            current_liabilities=400.0,
            retained_earnings=-300.0,  # accumulated deficit
            ebit=-50.0,                # operating loss
            equity=50.0,
            total_liabilities=950.0,
        ))
        assert result["zone"] == "distress"
        assert result["score"] < 1.1

    def test_zone_boundaries(self):
        assert scores.altman_z(company())["zone"] == "safe"
        # Tuned to land between the 1.1 and 2.6 cutoffs:
        # 6.56(0.10) + 3.26(0.10) + 6.72(0.04) + 1.05(0.25) = 1.51
        grey = scores.altman_z(company(
            current_assets=400.0,
            current_liabilities=300.0,
            retained_earnings=100.0,
            ebit=40.0,
            equity=200.0,
            total_liabilities=800.0,
        ))
        assert grey["zone"] == "grey", f"expected grey, got {grey['score']}"

    def test_returns_none_when_the_balance_sheet_is_missing(self):
        assert scores.altman_z(company(total_assets=None)) is None
        assert scores.altman_z(company(retained_earnings=None)) is None


class TestPiotroski:
    def test_first_year_has_no_score(self):
        assert scores.piotroski(company(), None) is None

    def test_a_clean_year_scores_nine(self):
        prior = company(
            total_assets=900.0,
            net_income=60.0,
            operating_cash_flow=70.0,
            gross_profit=430.0,
            revenue=1000.0,
            long_term_debt=150.0,
            current_assets=500.0,
            current_liabilities=300.0,
            shares_diluted=87_000_000.0,
            prior_total_assets=800.0,
        )
        result = scores.piotroski(company(), prior)
        failed = [s["label"] for s in result["signals"] if not s["passed"]]
        assert result["score"] == 9, f"expected 9/9, these failed: {failed}"
        assert result["band"] == "strong"

    def test_roa_uses_opening_assets_not_average(self):
        """Piotroski scales by beginning-of-year assets, which is the paper's
        definition and differs from the ROA in the metrics table."""
        prior = company(total_assets=500.0, net_income=10.0, prior_total_assets=500.0)
        result = scores.piotroski(company(net_income=100.0), prior)
        roa_signal = next(s for s in result["signals"] if s["key"] == "roa_positive")
        # 100 / 500 = 20%, not 100 / ((1000+500)/2) = 13.3%
        assert "20.0%" in roa_signal["detail"]

    def test_share_issuance_fails_the_dilution_test(self):
        prior = company(shares_diluted=80_000_000.0)
        result = scores.piotroski(company(shares_diluted=95_000_000.0), prior)
        signal = next(s for s in result["signals"] if s["key"] == "no_dilution")
        assert not signal["passed"]

    def test_small_buyback_still_passes_the_dilution_test(self):
        prior = company(shares_diluted=90_000_000.0)
        result = scores.piotroski(company(shares_diluted=87_000_000.0), prior)
        signal = next(s for s in result["signals"] if s["key"] == "no_dilution")
        assert signal["passed"]

    def test_earnings_ahead_of_cash_fails_the_accruals_test(self):
        prior = company(total_assets=1000.0)
        # Net income well above operating cash flow.
        result = scores.piotroski(
            company(net_income=200.0, operating_cash_flow=50.0), prior
        )
        signal = next(s for s in result["signals"] if s["key"] == "accruals_clean")
        assert not signal["passed"]

    def test_score_never_exceeds_nine(self):
        prior = company(total_assets=100.0, net_income=1.0, operating_cash_flow=1.0,
                        gross_profit=1.0, revenue=10.0, long_term_debt=500.0,
                        current_assets=10.0, current_liabilities=100.0,
                        shares_diluted=99_000_000.0, prior_total_assets=100.0)
        result = scores.piotroski(company(), prior)
        assert 0 <= result["score"] <= 9


class TestSafeDiv:
    def test_returns_none_rather_than_raising_on_zero(self):
        assert scores.safe_div(10, 0) is None

    def test_returns_none_when_either_side_is_missing(self):
        assert scores.safe_div(None, 5) is None
        assert scores.safe_div(5, None) is None

    def test_divides_normally(self):
        assert scores.safe_div(10, 4) == 2.5
