{{ config(materialized='table') }}

SELECT
    DATE_TRUNC('month', order_time)::DATE AS order_month,
    COUNT(DISTINCT o.order_id) AS order_count,
    SUM(payment_value) AS total_revenue,
    AVG(payment_value) AS avg_order_value,
    COUNT(DISTINCT customer_id) AS unique_customers
FROM {{ ref('int_payment_detail') }} p
JOIN {{ ref('int_order_detail') }} o ON p.order_id = o.order_id
WHERE p.payment_sequential = 1
GROUP BY 1
