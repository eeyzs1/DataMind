{{ config(materialized='table') }}

{% if var('detail_layer_mode') == 'passthrough' %}

SELECT
    order_id,
    customer_id,
    order_status,
    order_time,
    approved_at,
    delivered_carrier_at,
    delivered_customer_at,
    estimated_delivery_at
FROM {{ ref('stg_orders') }}

{% else %}

SELECT
    o.order_id,
    o.customer_id,
    c.customer_state,
    c.customer_city,
    o.order_status,
    CASE o.order_status
        WHEN 'delivered' THEN '已完成'
        WHEN 'shipped' THEN '配送中'
        WHEN 'invoiced' THEN '已开票'
        WHEN 'processing' THEN '处理中'
        WHEN 'canceled' THEN '已取消'
        WHEN 'unavailable' THEN '不可用'
        ELSE o.order_status
    END AS order_status_desc,
    o.order_time,
    o.approved_at,
    o.delivered_carrier_at,
    o.delivered_customer_at,
    o.estimated_delivery_at,
    EXTRACT(YEAR FROM o.order_time) AS order_year,
    EXTRACT(MONTH FROM o.order_time) AS order_month,
    EXTRACT(DOW FROM o.order_time) AS order_dow
FROM {{ ref('stg_orders') }} o
LEFT JOIN {{ ref('stg_customers') }} c ON o.customer_id = c.customer_id
WHERE o.order_id IS NOT NULL

{% endif %}
