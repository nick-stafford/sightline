-- Ratio layer, ordered the way a tearsheet is: growth, margins, returns,
-- leverage, working capital, then the two more involved measures at the end.
--
-- Two mechanics worth pointing out:
--
-- 1. Balance sheet items are point-in-time while income statement items cover a
--    whole year, so any ratio mixing the two (returns, turnover, days
--    outstanding) uses the average of opening and closing balances rather than
--    the closing figure. That needs the prior year, which the LAG window gives.
-- 2. Nike doesn't present an operating income subtotal, so EBIT falls back to
--    pre-tax income plus interest expense, which gets to the same place.

CREATE OR REPLACE TABLE metrics AS
WITH lagged AS (
    SELECT
        *,
        LAG(revenue)          OVER w AS prior_revenue,
        LAG(net_income)       OVER w AS prior_net_income,
        LAG(gross_profit)     OVER w AS prior_gross_profit,
        LAG(total_assets)     OVER w AS prior_total_assets,
        LAG(equity)           OVER w AS prior_equity,
        LAG(inventory)        OVER w AS prior_inventory,
        LAG(receivables)      OVER w AS prior_receivables,
        LAG(accounts_payable) OVER w AS prior_accounts_payable,
        LAG(revenue, 3)       OVER w AS revenue_3y_ago
    FROM financials
    WINDOW w AS (PARTITION BY ticker ORDER BY fy)
),

derived AS (
    SELECT
        *,
        COALESCE(operating_income, pretax_income + COALESCE(interest_expense, 0)) AS ebit,
        operating_cash_flow - capex                                               AS free_cash_flow,
        long_term_debt - cash                                                     AS net_debt,
        -- Invested capital on a capital-employed basis: total assets less the
        -- liabilities that fund themselves (payables, accruals).
        --
        -- The textbook alternative is equity + debt - cash, but that breaks on
        -- a net cash business. YETI has held more cash than debt since 2020, so
        -- netting all of it off shrinks the denominator toward zero and throws
        -- out returns above 100%, which say more about the formula than the
        -- company. Capital employed stays stable through that.
        total_assets - current_liabilities                                        AS invested_capital,
        COALESCE((total_assets + prior_total_assets) / 2, total_assets)           AS avg_assets,
        COALESCE((equity + prior_equity) / 2, equity)                             AS avg_equity,
        COALESCE((inventory + prior_inventory) / 2, inventory)                    AS avg_inventory,
        COALESCE((receivables + prior_receivables) / 2, receivables)              AS avg_receivables,
        COALESCE((accounts_payable + prior_accounts_payable) / 2, accounts_payable) AS avg_payables
    FROM lagged
),

with_ebitda AS (
    SELECT
        *,
        ebit + COALESCE(depreciation_amortization, 0) AS ebitda,
        -- NOPAT is EBIT taxed at the company's own effective rate, so returns
        -- aren't distorted by how the business happens to be financed.
        ebit * (1 - COALESCE(tax_expense / NULLIF(pretax_income, 0), 0.21)) AS nopat
    FROM derived
)

SELECT
    ticker,
    fy,
    period_end,

    -- ---- Scale -----------------------------------------------------------
    revenue,
    gross_profit,
    ebitda,
    ebit,
    net_income,
    eps_diluted,
    operating_cash_flow,
    free_cash_flow,
    total_assets,
    equity,
    net_debt,
    invested_capital,

    -- ---- Growth ----------------------------------------------------------
    revenue      / NULLIF(prior_revenue, 0)      - 1   AS revenue_growth,
    net_income   / NULLIF(prior_net_income, 0)   - 1   AS net_income_growth,
    gross_profit / NULLIF(prior_gross_profit, 0) - 1   AS gross_profit_growth,
    inventory    / NULLIF(prior_inventory, 0)    - 1   AS inventory_growth,
    receivables  / NULLIF(prior_receivables, 0)  - 1   AS receivables_growth,
    POWER(revenue / NULLIF(revenue_3y_ago, 0), 1.0 / 3) - 1 AS revenue_cagr_3y,

    -- ---- Margins ---------------------------------------------------------
    gross_profit / NULLIF(revenue, 0)                  AS gross_margin,
    ebitda       / NULLIF(revenue, 0)                  AS ebitda_margin,
    ebit         / NULLIF(revenue, 0)                  AS operating_margin,
    net_income   / NULLIF(revenue, 0)                  AS net_margin,
    sga          / NULLIF(revenue, 0)                  AS sga_pct_revenue,

    -- ---- Returns ---------------------------------------------------------
    net_income / NULLIF(avg_assets, 0)                 AS roa,
    net_income / NULLIF(avg_equity, 0)                 AS roe,
    -- DuPont: ROE is margin x turnover x leverage, which separates a return
    -- earned in the business from one manufactured on the balance sheet.
    revenue    / NULLIF(avg_assets, 0)                 AS asset_turnover,
    avg_assets / NULLIF(avg_equity, 0)                 AS equity_multiplier,

    -- ---- Leverage and coverage -------------------------------------------
    (long_term_debt - cash) / NULLIF(ebitda, 0)        AS net_debt_to_ebitda,
    long_term_debt / NULLIF(equity, 0)                 AS debt_to_equity,
    ebitda / NULLIF(interest_expense, 0)               AS interest_coverage,
    current_assets / NULLIF(current_liabilities, 0)    AS current_ratio,
    (current_assets - COALESCE(inventory, 0)) / NULLIF(current_liabilities, 0) AS quick_ratio,

    -- ---- Working capital, in days ----------------------------------------
    365 * avg_inventory   / NULLIF(cogs, 0)            AS days_inventory,
    365 * avg_receivables / NULLIF(revenue, 0)         AS days_receivables,
    365 * avg_payables    / NULLIF(cogs, 0)            AS days_payables,
    365 * avg_inventory   / NULLIF(cogs, 0)
      + 365 * avg_receivables / NULLIF(revenue, 0)
      - 365 * avg_payables    / NULLIF(cogs, 0)        AS cash_conversion_cycle,

    -- ---- Cash generation -------------------------------------------------
    free_cash_flow / NULLIF(revenue, 0)                AS fcf_margin,
    free_cash_flow / NULLIF(ebitda, 0)                 AS fcf_conversion,
    capex / NULLIF(revenue, 0)                         AS capex_intensity,
    operating_cash_flow / NULLIF(net_income, 0)        AS cash_conversion,

    -- ---- The two heavier ones --------------------------------------------
    -- ROIC: what the business earns on the capital actually deployed in it.
    -- The one return measure that is not distorted by capital structure, and
    -- the one worth comparing to the cost of that capital.
    nopat / NULLIF(invested_capital, 0)                AS roic,
    -- Accruals: the slice of earnings that did not arrive as cash. Research on
    -- accruals finds this portion is the least likely to repeat next year.
    (net_income - operating_cash_flow) / NULLIF(avg_assets, 0) AS accruals_ratio

FROM with_ebitda
ORDER BY ticker, fy;
