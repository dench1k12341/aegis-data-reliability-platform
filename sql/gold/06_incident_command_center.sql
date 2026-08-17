CREATE OR REPLACE TABLE gold.incident_command_center AS

SELECT
    i.incident_id,

    i.classification,
    i.severity,
    i.domain,
    i.location,

    CAST(
        i.detected_start_date
        AS DATE
    ) AS incident_start_date,

    CAST(
        i.detected_end_date
        AS DATE
    ) AS incident_end_date,

    i.duration_days,

    ROUND(
        i.confidence_score,
        2
    ) AS confidence_score,

    i.primary_cause,

    i.data_trust_status,

    i.business_metric,
    i.business_impact,

    i.affected_records,
    i.missing_records,

    i.anomaly_score,

    i.event_coverage_pct,
    i.revenue_capture_pct,
    i.null_value_pct,

    d.decision_status,
    d.decision_label,

    d.executive_summary,

    d.recommended_actions,

    d.evidence,

    CASE
        WHEN i.classification
            = 'DATA_INCIDENT'
        THEN 'Data Reliability'

        WHEN i.classification
            = 'BUSINESS_INCIDENT'
        THEN 'Operations'

        ELSE 'Other'
    END AS incident_family,

    CASE
        WHEN i.severity = 'Critical'
        THEN 4

        WHEN i.severity = 'High'
        THEN 3

        WHEN i.severity = 'Medium'
        THEN 2

        ELSE 1
    END AS severity_rank,

    CASE
        WHEN i.data_trust_status = 'FAILED'
        THEN 'Do Not Trust KPI'

        WHEN i.classification
            = 'BUSINESS_INCIDENT'
        THEN 'Business Action Required'

        ELSE 'Monitor'
    END AS command_center_status,

    CASE
        WHEN i.classification
            = 'DATA_INCIDENT'
            AND i.data_trust_status = 'FAILED'
        THEN 'Investigate Data Pipeline'

        WHEN i.classification
            = 'BUSINESS_INCIDENT'
            AND i.data_trust_status = 'PASSED'
        THEN 'Investigate Business Operations'

        ELSE 'Manual Review'
    END AS investigation_path

FROM meta.incident_registry AS i

LEFT JOIN meta.decision_briefs AS d
    ON i.incident_id
    = d.incident_id

ORDER BY
    severity_rank DESC,
    incident_start_date
;
