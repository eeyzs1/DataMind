{{ config(materialized='table') }}

SELECT
    product_id,
    product_category_name,
    COALESCE(product_name_lenght, 0) AS product_name_length,
    COALESCE(product_description_lenght, 0) AS product_description_length,
    COALESCE(product_photos_qty, 0) AS product_photos_qty,
    COALESCE(product_weight_g, 0) AS product_weight_g,
    COALESCE(product_length_cm, 0) AS product_length_cm,
    COALESCE(product_height_cm, 0) AS product_height_cm,
    COALESCE(product_width_cm, 0) AS product_width_cm,
    _ingested_at,
    _source
FROM {{ source('raw_files', 'olist_products') }}
WHERE product_id IS NOT NULL
