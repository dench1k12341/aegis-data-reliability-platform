SELECT
    order_date AS report_date,
    COUNT(*) AS orders,
    ROUND(SUM(order_total_eur), 2) AS total_order_value_eur,
    ROUND(AVG(order_total_eur), 2) AS avg_order_value_eur

FROM {{ ref('silver_orders') }}

GROUP BY order_date
