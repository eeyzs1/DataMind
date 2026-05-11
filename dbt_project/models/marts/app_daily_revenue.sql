{{ config(materialized='table') }}

SELECT
    order_date,
    total_revenue,
    order_count,
    avg_order_value,
    LAG(total_revenue) OVER (ORDER BY order_date) AS prev_day_revenue,
    CASE
        WHEN LAG(total_revenue) OVER (ORDER BY order_date) > 0
        THEN ROUND((total_revenue - LAG(total_revenue) OVER (ORDER BY order_date)) / LAG(total_revenue) OVER (ORDER BY order_date) * 100, 2)
        ELSE NULL
    END AS dod_growth_pct
FROM {{ ref('fct_daily_revenue') }}
