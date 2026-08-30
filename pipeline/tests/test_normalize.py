"""Tests for the XBRL normalizer -- the part most likely to go quietly wrong."""

from datetime import date

from sightline import normalize


def facts(entries, tag="Revenues", unit="USD"):
    """Build a minimal companyfacts structure around some unit entries."""
    return {"facts": {"us-gaap": {tag: {"units": {unit: entries}}}}}


class TestFiscalYear:
    def test_calendar_year_end_maps_to_that_year(self):
        assert normalize.fiscal_year(date(2024, 12, 31)) == 2024

    def test_early_year_end_maps_back_to_prior_year(self):
        # Lululemon's year ending Feb 2025 covers mostly calendar 2024.
        assert normalize.fiscal_year(date(2025, 2, 2)) == 2024

    def test_mid_year_end_maps_to_the_year_it_mostly_covers(self):
        # Nike's year ending May 2025 ran Jun 2024 to May 2025: mostly 2024.
        assert normalize.fiscal_year(date(2025, 5, 31)) == 2024

    def test_late_year_end_maps_to_that_year(self):
        # YETI and Costco style: a year ending Sep 2024 is mostly 2024.
        assert normalize.fiscal_year(date(2024, 9, 28)) == 2024


class TestAnnualFactFiltering:
    def test_keeps_a_full_year_from_a_10k(self):
        data = facts([
            {"start": "2023-01-01", "end": "2023-12-31", "val": 100, "form": "10-K", "filed": "2024-02-01"},
        ])
        result = normalize._annual_facts(data, "Revenues", "duration", "USD")
        assert result == {date(2023, 12, 31): (100, "2024-02-01")}

    def test_drops_quarterly_periods(self):
        data = facts([
            {"start": "2023-10-01", "end": "2023-12-31", "val": 25, "form": "10-K", "filed": "2024-02-01"},
        ])
        assert normalize._annual_facts(data, "Revenues", "duration", "USD") == {}

    def test_drops_non_10k_forms(self):
        data = facts([
            {"start": "2023-01-01", "end": "2023-12-31", "val": 100, "form": "10-Q", "filed": "2024-02-01"},
        ])
        assert normalize._annual_facts(data, "Revenues", "duration", "USD") == {}

    def test_drops_fiscal_year_transition_periods(self):
        """A short stub year from a fiscal-year change isn't comparable to a full one.

        VF Corp and Under Armour both did this. A 90-day 'year' would otherwise
        land in the series and read as a collapse in revenue.
        """
        data = facts([
            {"start": "2023-01-01", "end": "2023-03-31", "val": 25, "form": "10-K", "filed": "2023-05-01"},
        ])
        assert normalize._annual_facts(data, "Revenues", "duration", "USD") == {}

    def test_restatement_wins_over_the_original_filing(self):
        data = facts([
            {"start": "2023-01-01", "end": "2023-12-31", "val": 100, "form": "10-K", "filed": "2024-02-01"},
            {"start": "2023-01-01", "end": "2023-12-31", "val": 95, "form": "10-K", "filed": "2025-02-01"},
        ])
        result = normalize._annual_facts(data, "Revenues", "duration", "USD")
        assert result[date(2023, 12, 31)][0] == 95

    def test_instant_facts_reject_entries_carrying_a_start_date(self):
        data = facts([
            {"start": "2023-01-01", "end": "2023-12-31", "val": 500, "form": "10-K", "filed": "2024-02-01"},
            {"end": "2023-12-31", "val": 600, "form": "10-K", "filed": "2024-02-01"},
        ], tag="Assets")
        result = normalize._annual_facts(data, "Assets", "instant", "USD")
        assert result == {date(2023, 12, 31): (600, "2024-02-01")}


class TestTagPriority:
    def test_lower_priority_tag_only_fills_years_the_first_one_missed(self):
        """Companies switch tags mid-history, so the fallback has to fill gaps.

        It must not overwrite a year the preferred tag already covered, or a
        stale tag could win over the one the company currently reports.
        """
        company_facts = {"facts": {"us-gaap": {
            "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": [
                {"start": "2023-01-01", "end": "2023-12-31", "val": 200, "form": "10-K", "filed": "2024-02-01"},
            ]}},
            "Revenues": {"units": {"USD": [
                {"start": "2023-01-01", "end": "2023-12-31", "val": 999, "form": "10-K", "filed": "2024-02-01"},
                {"start": "2022-01-01", "end": "2022-12-31", "val": 180, "form": "10-K", "filed": "2023-02-01"},
            ]}},
        }}}

        rows = normalize.extract_company(company_facts, "TEST")
        by_year = {r["fy"]: r["value"] for r in rows if r["item"] == "revenue"}

        assert by_year[2023] == 200, "preferred tag must win where it has data"
        assert by_year[2022] == 180, "fallback tag must fill the year that was missing"


class TestDerivedItems:
    def test_gross_profit_is_derived_when_untagged(self):
        items = {"revenue": (1000, "Revenues"), "cogs": (400, "CostOfRevenue")}
        normalize._fill_derived(items)
        assert items["gross_profit"][0] == 600
        assert items["gross_profit"][1].startswith("derived:")

    def test_derivation_does_not_overwrite_a_reported_figure(self):
        items = {
            "revenue": (1000, "Revenues"),
            "cogs": (400, "CostOfRevenue"),
            "gross_profit": (610, "GrossProfit"),
        }
        normalize._fill_derived(items)
        assert items["gross_profit"] == (610, "GrossProfit")
