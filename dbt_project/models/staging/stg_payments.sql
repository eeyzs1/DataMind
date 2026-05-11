{{ config(materialized='table') }}

SELECT
    order_id,
    payment_sequential,
    payment_type,
    payment_installments,
    payment_value,
    _ingested_at,
    _source
FROM {{ source('raw_files', 'olist_payments') }}
WHERE order_id IS NOT NULL
