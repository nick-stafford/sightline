# Sightline

Financial statement analysis of **YETI Holdings (NYSE: YETI)**, built from SEC filings.

Nine fiscal years of 10-K data run through a standard investment banking metric stack,
two published financial health models, and a rule engine that looks for divergences
between the income statement and the balance sheet.

**Live:** _(add your deployed URL here)_

<!-- Add a screenshot at docs/screenshot.png and this will render -->
<!-- ![Sightline](docs/screenshot.png) -->

---

## What it found

In **FY2021**, inventory grew **127.6%** while revenue grew **29.2%**. The rule engine
flagged the gap as stock building ahead of demand.

The following year, gross margin fell **990 basis points**, from 57.8% to 47.9%, as that
inventory was cleared through discounting alongside a product recall.

The signal was sitting in the balance sheet a full year before it reached the income
statement. That is the case for reading working capital rather than only margins, and
it's the reason the flag rules compare the two against each other rather than scoring
each in isolation.

---

## Stack

| Layer | Tool | What it does |
|---|---|---|
| Ingestion | Python | Pulls raw XBRL company facts from the SEC EDGAR API and caches them |
| Normalization | Python | Maps ~1,800 us-gaap tags to 27 line items across 8 companies |
| Warehouse | DuckDB / SQL | Pivots to one row per company-year, then builds ratios and peer ranks |
| Scoring | Python | Altman Z''-Score, Piotroski F-Score, 10 red flag rules |
| Narrative | Groq (Llama 3.3 70B) | Writes the analysis over pre-computed figures |
| Front end | React + TypeScript + Recharts | Single page, static, no backend |

The pipeline runs **offline** and publishes static JSON. The page reads that JSON, so
there is no server, no database and no API keys at runtime. It loads instantly and costs
nothing to host.

---

## Running it

```bash
# 1. Pull the filings (~28 MB, cached locally)
cd pipeline
pip install -r requirements.txt
python fetch_data.py

# 2. Build the analysis -> web/public/data/*.json
python build.py
pytest tests/ -q

# 3. Run the page
cd ../web
npm install
npm run dev
```

The LLM memo is optional. Put a `GROQ_API_KEY` in `pipeline/.env` to have the analysis
written by a model; without one the pipeline falls back to a deterministic template built
from the same facts, so the page never renders an empty section.

---

## Design decisions

Most of the work in this project was in the data layer, not the charts.

**Companies tag the same concept differently, and change tags over time.** Nike tags
inventory as `InventoryFinishedGoodsNetOfReserves` rather than `InventoryNet`. VF Corp
uses `PaymentsForCapitalImprovements` for capex. Several companies moved to the combined
PP&E-plus-finance-lease tag after the 2019 lease standard. Each line item therefore maps
to a list of candidate tags in priority order, and lower-priority tags fill only the
years the preferred one missed.

**Fiscal years don't line up.** Nike's year ending May 2025 is "FY2025" to Nike;
Lululemon's year ending February 2025 is "FY2024" to Lululemon. Comparing companies on
their own labels lines up periods a year apart. Every year is relabelled by the calendar
year it mostly falls in.

**Restatements and transition periods.** The same period gets reported in multiple
filings, so the most recently filed version wins. Duration facts must cover ~365 days,
which also filters out the short stub years companies file when they change their fiscal
year end — VF Corp and Under Armour both did, and an unfiltered 90-day "year" would read
as a collapse in revenue.

**ROIC on a capital-employed basis.** The textbook denominator is equity + debt − cash,
which breaks on a net cash business: YETI has held more cash than debt since 2020, so
netting all of it off shrinks the denominator toward zero and produced returns above
100%. Capital employed (total assets − current liabilities) stays stable through that.

**The Altman variant matters.** This uses the Z''-Score built for non-manufacturers,
which drops the sales/assets term because asset turnover varies too much by industry.
The commonly quoted +3.25 constant belongs to the *emerging markets* variant and is not
applied here — including it for a US filer would lift essentially every company into the
safe zone.

**The model doesn't do arithmetic.** Every figure is computed in SQL or Python first and
handed to the LLM as a structured block of facts. The prose can be wrong about emphasis;
it cannot be wrong about a number.

**Missing means missing.** A company with no borrowings simply doesn't tag the concept,
so absent debt and dividends are treated as zero. Everything else stays null rather than
silently becoming a real zero, and NaN is scrubbed before serialization because
`JSON.parse` rejects it.

---

## Tests

```
pytest tests/ -q
47 passed, 3 skipped
```

The skipped three are waiting on a rule that hasn't been written yet (see `TASKS.md`).

The tests that matter are the negative cases: that a missing figure never reads as a
passing one, that a fiscal-year transition stub is excluded, that a lower-priority tag
doesn't overwrite a year the preferred tag already covered, and that the leverage rule
doesn't fire on a company holding net cash.

---

## Data source and limitations

All figures come from the [SEC EDGAR XBRL company facts API](https://www.sec.gov/edgar/sec-api-documentation),
as reported by the companies, with no adjustment for one-time items. Peer comparison
covers eight apparel and outdoor companies: Nike, Deckers, Lululemon, VF Corp, Columbia,
Under Armour, Crocs and YETI.

Arc'teryx and On Holding were considered and excluded: their parents report under IFRS
rather than US GAAP and carry no `us-gaap` tags, so they would need a separate mapping.

The Altman Z''-Score and Piotroski F-Score are published academic models applied to
reported figures. They are screening measures, not verdicts. Nothing here is investment
advice.
