# Open tasks

Scoped pieces of work, roughly in order of how much they add. Each one names the files
involved and how to check it worked.

---

## 1. Write the cash conversion cycle rule

**Files:** `pipeline/analysis/flags.py`, `pipeline/tests/test_flags.py`
**Check:** `pytest tests/test_flags.py -q`

There's a `TODO(nick)` in `flags.py` marking where this goes. The rule should fire when
the cash conversion cycle stretches by more than about 15 days year over year — cash
getting tied up in the operating cycle even while margins look fine.

`cur["cash_conversion_cycle"]` and `pri["cash_conversion_cycle"]` are already computed in
`sql/02_metrics.sql`, so this is only the rule function. Follow the shape of the rules
above it, then add it to the `RULES` list.

The tests are already written in `TestCashCycleRule` — remove the `@pytest.mark.skip`
decorator once the function exists. Three currently-skipped tests should turn green.

Watch the two cases the other rules guard against: a `None` on either year must not fire,
and a *shortening* cycle is an improvement, not a flag.

---

## 2. Add inventory turns to the ratio layer

**Files:** `pipeline/sql/02_metrics.sql`, `pipeline/sql/03_peers.sql`
**Check:** `python build.py`, then look for the field in `web/public/data/company.json`

Inventory turns (`cogs / average inventory`) is the standard companion to days inventory
and reads more naturally for a retailer. The `averaged` CTE already computes
`avg_inventory`, so it's one line in the SELECT.

To get it into the peer comparison as well, add it to both the inner SELECT and the
`UNPIVOT` list in `03_peers.sql`, plus a row in the `direction` VALUES clause — higher
turns is better, so `TRUE`.

---

## 3. Add a working capital chart to the page

**Files:** `web/src/components/Charts.tsx`, `web/src/App.tsx`
**Check:** `npm run dev`

The three day-count metrics (`days_inventory`, `days_receivables`, `days_payables`) are
already in the JSON and nothing on the page shows them, even though the FY21 story is
entirely a working capital story.

A three-line chart in the same shape as `MarginChart` is the straightforward version. Use
series slots 1, 2 and 3 — they're defined as CSS variables in `styles.css`, so don't
introduce new hex values. Then drop it into the Trends grid in `App.tsx`.

If you want to go further, a stacked bar showing the cycle building up (inventory +
receivables − payables) tells the story better than three separate lines.

---

## 4. Point it at a different company

**Files:** `pipeline/analysis/config.py`
**Check:** `python build.py`

`DEFAULT_TICKER` selects the company the page is about; the other seven stay as the peer
group. Try `VFC` — VF Corp owns The North Face, Vans and Timberland, and has by far the
most dramatic financials in the cohort: revenue decline, impairments, real leverage, and
a dividend cut. Several flags that stay quiet for YETI fire immediately.

Adding a company entirely means one entry in `COHORT` with its CIK, then
`python fetch_data.py`. Note that the `us-gaap` assumption is load-bearing — foreign
private issuers filing under IFRS won't work without a separate tag mapping.

Anything written into the page copy that assumes YETI (the FY22 note in `MarginChart`,
the slider hints in `Forecast.tsx`) needs updating too.

---

## 5. Turn the AI memo back on

**Files:** `pipeline/.env`
**Check:** `python build.py` — the log should say `memo written by: groq`

The key currently in `.env` came from another project and returns **403 Forbidden**, so
the pipeline is falling back to the deterministic template. Get a fresh free key from
console.groq.com and replace the `GROQ_API_KEY` line.

The page reports which one wrote the memo, so this is visible to anyone reading it.

---

## 6. Deploy

Already live at https://nick-stafford.github.io/yeti-coverage/

`.github/workflows/deploy.yml` rebuilds the page and publishes it to GitHub Pages on
every push to `master`. `web/public/data/*.json` is committed, so a deploy needs no
Python, no database and no API key.

`vercel.json` is also configured if you'd rather serve it from Vercel: it builds `web/`
and serves `web/dist`. The Vite base is set to relative paths, so the same build works
from a domain root or a repo subpath without changing anything.

---

## Ideas beyond this

- **Quarterly data.** The pipeline filters to annual 10-K figures. The same facts file
  carries 10-Q data, which would make the FY22 inventory story visible quarter by quarter
  rather than as one annual step.
- **Segment detail.** YETI reports Drinkware and Coolers & Equipment separately, and the
  margin story differs between them.
- **A second cohort.** The peer group is hardcoded to apparel and outdoor. Sector
  assignment from the SEC's SIC codes would let the tool pick peers automatically.
