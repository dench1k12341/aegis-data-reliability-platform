CREATE OR REPLACE TABLE silver.orders_enriched AS

WITH item_summary AS (
    SELECT
        order_id,
        COUNT(*) AS item_row_count,
        SUM(quantity) AS item_units,
        ROUND(SUM(gross_value_eur), 2) AS item_gmv_eur,
        ROUND(SUM(discount_value_eur), 2) AS item_discount_eur,
        ROUND(SUM(net_value_eur), 2) AS item_net_value_eur
    FROM bronze.order_items
    GROUP BY order_id
)

SELECT
    o.*,

    CAST(o.order_ts AS DATE) AS order_date,

    c.country AS customer_country,
    c.acquisition_channel,
    c.signup_date,
    c.account_status,

    p.payment_id,
    p.payment_ts,
    p.payment_method,
    p.payment_status,
    p.payment_amount_eur,
    p.fraud_score,

    i.item_row_count,
    i.item_units,
    i.item_gmv_eur,
    i.item_discount_eur,
    i.item_net_value_eur,

    CASE
        WHEN p.payment_status = 'Paid'
        THEN 1 ELSE 0
    END AS payment_paid_flag,

    CASE
        WHEN p.payment_status = 'Refunded'
        THEN 1 ELSE 0
    END AS payment_refunded_flag,

    CASE
        WHEN p.payment_status = 'Failed'
        THEN 1 ELSE 0
    END AS payment_failed_flag,

    CASE
        WHEN o.order_status IN ('Completed', 'Returned')
        THEN 1 ELSE 0
    END AS purchase_realized_flag,

    CASE
        WHEN o.order_status = 'Cancelled'
        THEN 1 ELSE 0
    END AS cancelled_order_flag,

    ROUND(
        p.payment_amount_eur
        - o.order_total_eur,
        2
    ) AS payment_reconciliation_delta_eur

FROM bronze.orders AS o

LEFT JOIN bronze.customers AS c
    ON o.customer_id = c.customer_id

LEFT JOIN bronze.payments AS p
    ON o.order_id = p.order_id

LEFT JOIN item_summary AS i
    ON o.order_id = i.order_id
;
