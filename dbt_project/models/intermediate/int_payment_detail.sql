{{ config(materialized='table') }}

{% if var('detail_layer_mode') == 'passthrough' %}

SELECT
    order_id,
    payment_sequential,
    payment_type,
    payment_installments,
    payment_value
FROM {{ ref('stg_payments') }}

{% else %}

SELECT
    p.order_id,
    p.payment_sequential,
    p.payment_type,
    CASE p.payment_type
        WHEN 'credit_card' THEN '信用卡'
        WHEN 'boleto' THEN 'Boleto'
        WHEN 'voucher' THEN '代金券'
        WHEN 'debit_card' THEN '借记卡'
        WHEN 'not_defined' THEN '未定义'
        ELSE p.payment_type
    END AS payment_type_desc,
    p.payment_installments,
    p.payment_value,
    pay_summary.total_payment,
    pay_summary.payment_count
FROM {{ ref('stg_payments') }} p
LEFT JOIN (
    SELECT
        order_id,
        SUM(payment_value) AS total_payment,
        COUNT(*) AS payment_count
    FROM {{ ref('stg_payments') }}
    GROUP BY order_id
) pay_summary ON p.order_id = pay_summary.order_id

{% endif %}
