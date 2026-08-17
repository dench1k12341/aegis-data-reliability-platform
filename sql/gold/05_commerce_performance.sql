CREATE OR REPLACE TABLE gold.commerce_performance AS

SELECT
    order_date AS report_date,

    customer_segment,
    sales_channel,
    destination_country,
    payment_method,

    COUNT(*)
        AS orders,

    COUNT(
        DISTINCT customer_id
    ) AS customers,

    SUM(
        item_units
    ) AS units,

    SUM(
        CASE
            WHEN order_status = 'Completed'
            THEN 1 ELSE 0
        END
    ) AS completed_orders,

    SUM(
        CASE
            WHEN order_status = 'Returned'
            THEN 1 ELSE 0
        END
    ) AS returned_orders,

    SUM(
        CASE
            WHEN order_status = 'Cancelled'
            THEN 1 ELSE 0
        END
    ) AS cancelled_orders,

    SUM(
        CASE
            WHEN order_status = 'Pending'
            THEN 1 ELSE 0
        END
    ) AS pending_orders,

    ROUND(
        SUM(
            gross_merchandise_value_eur
        ),
        2
    ) AS gross_merchandise_value_eur,

    ROUND(
        SUM(
            discount_eur
        ),
        2
    ) AS discount_eur,

    ROUND(
        SUM(
            order_total_eur
        ),
        2
    ) AS total_order_value_eur,

    ROUND(
        SUM(
            CASE
                WHEN order_status = 'Completed'
                THEN order_total_eur
                ELSE 0
            END
        ),
        2
    ) AS completed_revenue_eur,

    ROUND(
        SUM(
            CASE
                WHEN order_status = 'Returned'
                THEN order_total_eur
                ELSE 0
            END
        ),
        2
    ) AS returned_value_eur,

    ROUND(
        SUM(
            CASE
                WHEN order_status = 'Cancelled'
                THEN order_total_eur
                ELSE 0
            END
        ),
        2
    ) AS cancelled_value_eur,

    ROUND(
        AVG(
            order_total_eur
        ),
        2
    ) AS avg_order_value_eur,

    SUM(
        CASE
            WHEN payment_status = 'Paid'
            THEN 1 ELSE 0
        END
    ) AS paid_payments,

    SUM(
        CASE
            WHEN payment_status = 'Refunded'
            THEN 1 ELSE 0
        END
    ) AS refunded_payments,

    SUM(
        CASE
            WHEN payment_status = 'Failed'
            THEN 1 ELSE 0
        END
    ) AS failed_payments,

    ROUND(
        SUM(
            CASE
                WHEN payment_status = 'Paid'
                THEN payment_amount_eur
                ELSE 0
            END
        ),
        2
    ) AS paid_payment_value_eur,

    ROUND(
        SUM(
            CASE
                WHEN payment_status = 'Refunded'
                THEN payment_amount_eur
                ELSE 0
            END
        ),
        2
    ) AS refunded_payment_value_eur,

    ROUND(
        AVG(
            fraud_score
        ),
        4
    ) AS avg_fraud_score,

    ROUND(
        AVG(
            payment_paid_flag
        ) * 100,
        2
    ) AS payment_success_rate_pct,

    SUM(
        CASE
            WHEN ABS(
                payment_reconciliation_delta_eur
            ) > 0.01
            THEN 1
            ELSE 0
        END
    ) AS reconciliation_mismatch_orders

FROM silver.orders_enriched

WHERE
    order_date BETWEEN
        DATE '2025-01-01'
        AND DATE '2025-12-31'

GROUP BY
    order_date,
    customer_segment,
    sales_channel,
    destination_country,
    payment_method

ORDER BY
    report_date,
    customer_segment,
    sales_channel,
    destination_country
;
