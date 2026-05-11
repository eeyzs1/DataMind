{{ config(materialized='table') }}

SELECT
    review_id,
    order_id,
    review_score,
    review_comment_title,
    review_comment_message,
    review_creation_date::TIMESTAMP AS review_created_at,
    review_answer_timestamp::TIMESTAMP AS review_answered_at,
    _ingested_at,
    _source
FROM {{ source('raw_files', 'olist_reviews') }}
WHERE order_id IS NOT NULL
