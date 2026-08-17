CREATE OR REPLACE TABLE gold.executive_daily AS

WITH calendar AS (
    SELECT
        CAST(generate_series AS DATE) AS report_date
    FROM generate_series(
        DATE '2025-01-01',
        DATE '2025-12-31',
        INTERVAL 1 DAY
    )
),

commerce AS (
    SELECT
        order_date AS report_date,

        COUNT(*) AS orders,

        SUM(
            purchase_realized_flag
        ) AS realized_orders,

        SUM(
            cancelled_order_flag
        ) AS cancelled_orders,

        ROUND(
            SUM(
                CASE
                    WHEN purchase_realized_flag = 1
                    THEN order_total_eur
                    ELSE 0
                END
            ),
            2
        ) AS realized_revenue_eur,

        ROUND(
            AVG(order_total_eur),
            2
        ) AS avg_order_value_eur

    FROM silver.orders_enriched

    WHERE order_date BETWEEN
        DATE '2025-01-01'
        AND DATE '2025-12-31'

    GROUP BY order_date
),

logistics AS (
    SELECT
        shipment_date AS report_date,

        COUNT(*) AS shipments,

        SUM(delayed_flag)
            AS delayed_shipments,

        ROUND(
            AVG(sla_met) * 100,
            2
        ) AS delivery_sla_pct,

        ROUND(
            AVG(delayed_flag) * 100,
            2
        ) AS delay_rate_pct,

        ROUND(
            AVG(network_load_factor) * 100,
            2
        ) AS avg_network_load_pct,

        ROUND(
            AVG(actual_transit_hours),
            2
        ) AS avg_transit_hours,

        SUM(no_scan_flag)
            AS no_scan_shipments,

        SUM(damaged_flag)
            AS damaged_shipments,

        SUM(lost_flag)
            AS lost_shipments

    FROM silver.shipments_enriched

    WHERE shipment_date BETWEEN
        DATE '2025-01-01'
        AND DATE '2025-12-31'

    GROUP BY shipment_date
),

support AS (
    SELECT
        case_date AS report_date,

        COUNT(*) AS support_cases,

        ROUND(
            AVG(support_sla_met) * 100,
            2
        ) AS support_sla_pct,

        ROUND(
            AVG(csat_score),
            2
        ) AS avg_csat,

        ROUND(
            AVG(escalated_flag) * 100,
            2
        ) AS escalation_rate_pct,

        ROUND(
            AVG(reopened_flag) * 100,
            2
        ) AS reopen_rate_pct

    FROM silver.support_enriched

    WHERE case_date BETWEEN
        DATE '2025-01-01'
        AND DATE '2025-12-31'

    GROUP BY case_date
),

app AS (
    SELECT
        event_date AS report_date,

        total_events,
        sessions,
        active_customers,
        product_view_events,
        add_to_cart_events,
        checkout_events,
        purchase_events,
        payment_failed_events,
        purchase_value_null_count,
        purchase_event_revenue_eur,
        checkout_to_purchase_pct,
        purchase_value_completeness_pct

    FROM silver.app_funnel_daily

    WHERE event_date BETWEEN
        DATE '2025-01-01'
        AND DATE '2025-12-31'
),

reconciliation AS (
    SELECT
        CAST(date AS DATE)
            AS report_date,

        expected_purchase_count,
        observed_purchase_count,
        expected_revenue_eur,
        observed_revenue_eur,
        missing_purchase_pct,
        purchase_value_null_pct,

        ROUND(
            purchase_count_ratio * 100,
            2
        ) AS purchase_event_coverage_pct,

        ROUND(
            revenue_ratio * 100,
            2
        ) AS revenue_capture_pct,

        incident_flag
            AS data_incident_flag

    FROM silver.daily_purchase_reconciliation
)

SELECT
    c.report_date,

    COALESCE(
        co.orders,
        0
    ) AS orders,

    COALESCE(
        co.realized_orders,
        0
    ) AS realized_orders,

    COALESCE(
        co.cancelled_orders,
        0
    ) AS cancelled_orders,

    COALESCE(
        co.realized_revenue_eur,
        0
    ) AS realized_revenue_eur,

    co.avg_order_value_eur,

    COALESCE(
        l.shipments,
        0
    ) AS shipments,

    COALESCE(
        l.delayed_shipments,
        0
    ) AS delayed_shipments,

    l.delivery_sla_pct,
    l.delay_rate_pct,
    l.avg_network_load_pct,
    l.avg_transit_hours,

    COALESCE(
        l.no_scan_shipments,
        0
    ) AS no_scan_shipments,

    COALESCE(
        l.damaged_shipments,
        0
    ) AS damaged_shipments,

    COALESCE(
        l.lost_shipments,
        0
    ) AS lost_shipments,

    COALESCE(
        s.support_cases,
        0
    ) AS support_cases,

    s.support_sla_pct,
    s.avg_csat,
    s.escalation_rate_pct,
    s.reopen_rate_pct,

    COALESCE(
        a.total_events,
        0
    ) AS app_events,

    COALESCE(
        a.sessions,
        0
    ) AS sessions,

    COALESCE(
        a.active_customers,
        0
    ) AS active_customers,

    COALESCE(
        a.product_view_events,
        0
    ) AS product_view_events,

    COALESCE(
        a.add_to_cart_events,
        0
    ) AS add_to_cart_events,

    COALESCE(
        a.checkout_events,
        0
    ) AS checkout_events,

    COALESCE(
        a.purchase_events,
        0
    ) AS purchase_events,

    COALESCE(
        a.payment_failed_events,
        0
    ) AS payment_failed_events,

    COALESCE(
        a.purchase_value_null_count,
        0
    ) AS purchase_value_null_count,

    COALESCE(
        a.purchase_event_revenue_eur,
        0
    ) AS purchase_event_revenue_eur,

    a.checkout_to_purchase_pct,
    a.purchase_value_completeness_pct,

    r.expected_purchase_count,
    r.observed_purchase_count,
    r.expected_revenue_eur,
    r.observed_revenue_eur,
    r.missing_purchase_pct,
    r.purchase_value_null_pct,
    r.purchase_event_coverage_pct,
    r.revenue_capture_pct,

    COALESCE(
        r.data_incident_flag,
        0
    ) AS data_incident_flag,

    CASE
        WHEN COALESCE(
            r.data_incident_flag,
            0
        ) = 1
        THEN 'FAILED'

        ELSE 'PASSED'
    END AS data_trust_status

FROM calendar AS c

LEFT JOIN commerce AS co
    ON c.report_date
    = co.report_date

LEFT JOIN logistics AS l
    ON c.report_date
    = l.report_date

LEFT JOIN support AS s
    ON c.report_date
    = s.report_date

LEFT JOIN app AS a
    ON c.report_date
    = a.report_date

LEFT JOIN reconciliation AS r
    ON c.report_date
    = r.report_date

ORDER BY
    c.report_date
;
