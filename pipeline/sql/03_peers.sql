-- Rank each company against the cohort, one fiscal year at a time.
--
-- A 58% gross margin means nothing on its own. Ranked against seven comparable
-- apparel and outdoor businesses in the same year it means something. Ranking
-- within the year also strips out whatever was happening to the whole sector,
-- so the 2022 inventory glut doesn't drag every company down at once.

CREATE OR REPLACE TABLE peer_ranks AS
WITH ranked_metrics AS (
    SELECT ticker, fy, metric, value
    FROM (
        SELECT
            ticker,
            fy,
            revenue_growth,
            gross_margin,
            ebitda_margin,
            operating_margin,
            roic,
            roe,
            asset_turnover,
            net_debt_to_ebitda,
            current_ratio,
            fcf_conversion,
            fcf_margin,
            days_inventory,
            cash_conversion_cycle
        FROM metrics
    )
    UNPIVOT (value FOR metric IN (
        revenue_growth, gross_margin, ebitda_margin, operating_margin, roic, roe,
        asset_turnover, net_debt_to_ebitda, current_ratio, fcf_conversion,
        fcf_margin, days_inventory, cash_conversion_cycle
    ))
),

-- For most of these a bigger number is better, but not all: carrying more
-- leverage, holding inventory longer, or tying up cash in the operating cycle
-- are all worse, so their percentiles get flipped.
direction(metric, higher_is_better) AS (
    VALUES
        ('revenue_growth', TRUE),
        ('gross_margin', TRUE),
        ('ebitda_margin', TRUE),
        ('operating_margin', TRUE),
        ('roic', TRUE),
        ('roe', TRUE),
        ('asset_turnover', TRUE),
        ('current_ratio', TRUE),
        ('fcf_conversion', TRUE),
        ('fcf_margin', TRUE),
        ('net_debt_to_ebitda', FALSE),
        ('days_inventory', FALSE),
        ('cash_conversion_cycle', FALSE)
)

SELECT
    r.ticker,
    r.fy,
    r.metric,
    r.value,
    d.higher_is_better,
    PERCENT_RANK() OVER (PARTITION BY r.fy, r.metric ORDER BY r.value) AS raw_percentile,
    CASE WHEN d.higher_is_better
         THEN PERCENT_RANK() OVER (PARTITION BY r.fy, r.metric ORDER BY r.value)
         ELSE 1 - PERCENT_RANK() OVER (PARTITION BY r.fy, r.metric ORDER BY r.value)
    END AS percentile,
    COUNT(*) OVER (PARTITION BY r.fy, r.metric) AS peers_in_year
FROM ranked_metrics r
JOIN direction d ON d.metric = r.metric
WHERE r.value IS NOT NULL
  AND ISFINITE(r.value)
ORDER BY r.fy, r.metric, r.ticker;
