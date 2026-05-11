{{ config(materialized='table') }}

SELECT
    o.customer_id,
    c.customer_state,
    c.customer_city,
    COUNT(DISTINCT o.order_id) AS order_count,
    SUM(p.payment_value) AS total_spent,
    AVG(p.payment_value) AS avg_order_value,
    MAX(o.order_time) AS last_order_time,
    CURRENT_DATE - MAX(o.order_time)::DATE AS days_since_last_order,
    CASE
        WHEN CURRENT_DATE - MAX(o.order_time)::DATE > 90 THEN '流失风险'
        WHEN CURRENT_DATE - MAX(o.order_time)::DATE > 30 THEN '沉默'
        WHEN SUM(p.payment_value) > 500 THEN '高价值'
        ELSE '普通'
    END AS customer_segment
FROM {{ ref('int_order_detail') }} o
JOIN {{ ref('int_payment_detail') }} p ON o.order_id = p.order_id
LEFT JOIN {{ ref('stg_customers') }} c ON o.customer_id = c.customer_id
WHERE p.payment_sequential = 1
GROUP BY o.customer_id, c.customer_state, c.customer_city
