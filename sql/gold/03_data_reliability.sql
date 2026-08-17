CREATE OR REPLACE TABLE gold.data_reliability_daily AS

SELECT
    CAST(date AS DATE)
        AS report_date,

    expected_purchase_count,

    observed_purchase_count,

    (
        expected_purchase_count
        - observed_purchase_count
    ) AS missing_purchase_events,

    ROUND(
        purchase_count_ratio * 100,
        2
    ) AS purchase_event_coverage_pct,

    purchase_value_null_count,

    ROUND(
        purchase_value_null_pct,
        2
    ) AS purchase_value_null_pct,

    ROUND(
        expected_revenue_eur,
        2
    ) AS expected_revenue_eur,

    ROUND(
        observed_revenue_eur,
        2
    ) AS observed_event_revenue_eur,

    ROUND(
        revenue_ratio * 100,
        2
    ) AS revenue_capture_pct,

    ROUND(
        missing_purchase_pct,
        2
    ) AS missing_purchase_pct,

    incident_flag
        AS data_incident_flag,

    CASE
        WHEN incident_flag = 1
        THEN 'FAILED'
        ELSE 'PASSED'
    END AS data_trust_status,

    CASE
        WHEN
            purchase_count_ratio < 0.60
            OR revenue_ratio < 0.40
        THEN 'Critical'

        WHEN incident_flag = 1
        THEN 'High'

        ELSE 'Normal'
    END AS reliability_status,

    CASE
        WHEN incident_flag = 1
        THEN
            'Purchase telemetry does not reconcile '
            || 'with trusted operational records'

        ELSE
            'Purchase telemetry reconciles '
            || 'with operational records'
    END AS reliability_message

FROM silver.daily_purchase_reconciliation

WHERE
    CAST(date AS DATE)
    BETWEEN
        DATE '2025-01-01'
        AND DATE '2025-12-31'

ORDER BY
    report_date
;
