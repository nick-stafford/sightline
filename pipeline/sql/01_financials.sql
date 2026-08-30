-- Pivot the tidy fact table into one row per company-year.
--
-- The facts table is long (ticker, fy, item, value) because that's the shape
-- XBRL comes in and it makes adding a line item a config change. But every
-- ratio downstream wants the wide shape, so we pivot once here and build
-- everything else on top of this view.

CREATE OR REPLACE VIEW financials AS
SELECT
    ticker,
    fy,
    MAX(period_end) AS period_end,

    -- Income statement
    MAX(CASE WHEN item = 'revenue'                   THEN value END) AS revenue,
    MAX(CASE WHEN item = 'cogs'                      THEN value END) AS cogs,
    MAX(CASE WHEN item = 'gross_profit'              THEN value END) AS gross_profit,
    MAX(CASE WHEN item = 'sga'                       THEN value END) AS sga,
    MAX(CASE WHEN item = 'operating_income'          THEN value END) AS operating_income,
    MAX(CASE WHEN item = 'interest_expense'          THEN value END) AS interest_expense,
    MAX(CASE WHEN item = 'pretax_income'             THEN value END) AS pretax_income,
    MAX(CASE WHEN item = 'tax_expense'               THEN value END) AS tax_expense,
    MAX(CASE WHEN item = 'net_income'                THEN value END) AS net_income,
    MAX(CASE WHEN item = 'eps_diluted'               THEN value END) AS eps_diluted,
    MAX(CASE WHEN item = 'shares_diluted'            THEN value END) AS shares_diluted,

    -- Balance sheet
    MAX(CASE WHEN item = 'cash'                      THEN value END) AS cash,
    MAX(CASE WHEN item = 'receivables'               THEN value END) AS receivables,
    MAX(CASE WHEN item = 'inventory'                 THEN value END) AS inventory,
    MAX(CASE WHEN item = 'current_assets'            THEN value END) AS current_assets,
    MAX(CASE WHEN item = 'ppe_net'                   THEN value END) AS ppe_net,
    MAX(CASE WHEN item = 'total_assets'              THEN value END) AS total_assets,
    MAX(CASE WHEN item = 'accounts_payable'          THEN value END) AS accounts_payable,
    MAX(CASE WHEN item = 'current_liabilities'       THEN value END) AS current_liabilities,
    MAX(CASE WHEN item = 'total_liabilities'         THEN value END) AS total_liabilities,
    MAX(CASE WHEN item = 'retained_earnings'         THEN value END) AS retained_earnings,
    MAX(CASE WHEN item = 'equity'                    THEN value END) AS equity,

    -- A company with no borrowings simply doesn't tag the concept, so an
    -- absent debt or dividend figure genuinely means zero. That is not true of
    -- the other line items, which stay NULL when missing so a gap in the data
    -- never gets silently reported as a real zero.
    COALESCE(MAX(CASE WHEN item = 'long_term_debt'   THEN value END), 0) AS long_term_debt,
    COALESCE(MAX(CASE WHEN item = 'dividends_paid'   THEN value END), 0) AS dividends_paid,

    -- Cash flow
    MAX(CASE WHEN item = 'operating_cash_flow'       THEN value END) AS operating_cash_flow,
    MAX(CASE WHEN item = 'capex'                     THEN value END) AS capex,
    MAX(CASE WHEN item = 'depreciation_amortization' THEN value END) AS depreciation_amortization

FROM facts
GROUP BY ticker, fy;
