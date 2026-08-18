SELECT
    payment_id,
    order_id,
    CAST(payment_ts AS TIMESTAMP) AS payment_ts,
    payment_method,
    payment_status,
    payment_amount_eur,
    fraud_score

FROM {{ source('bronze', 'payments') }}
