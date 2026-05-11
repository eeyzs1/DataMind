{{ config(materialized='table') }}

SELECT
    order_id,
    customer_id,
    order_status,
    order_purchase_timestamp::TIMESTAMP AS order_time,
    order_approved_at::TIMESTAMP AS approved_at,
    order_delivered_carrier_date::TIMESTAMP AS delivered_carrier_at,
    order_delivered_customer_date::TIMESTAMP AS delivered_customer_at,
    order_estimated_delivery_date::TIMESTAMP AS estimated_delivery_at,
    _ingested_at,
    _source
FROM {{ source('raw_files', 'olist_orders') }}
WHERE order_id IS NOT NULL
