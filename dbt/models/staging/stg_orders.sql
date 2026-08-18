SELECT
    order_id,
    customer_id,
    destination_country,
    customer_segment,
    sales_channel,
    CAST(order_ts AS TIMESTAMP) AS order_ts,
    CAST(order_ts AS DATE) AS order_date,
    line_count,
    units,
    gross_merchandise_value_eur,
    discount_eur,
    merchandise_revenue_eur,
    shipping_fee_eur,
    order_total_eur,
    order_status

FROM {{ source('bronze', 'orders') }}
