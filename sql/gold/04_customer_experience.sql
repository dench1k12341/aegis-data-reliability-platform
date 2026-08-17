CREATE OR REPLACE TABLE gold.customer_experience AS

WITH incident_shipments AS (

    SELECT DISTINCT
        s.shipment_id,

        i.candidate_incident_id,

        i.anomaly_score

    FROM silver.shipments_enriched AS s

    INNER JOIN meta.business_incidents AS i

        ON (
            s.origin_warehouse_id
                = i.warehouse_id

            OR

            s.destination_warehouse_id
                = i.warehouse_id
        )

        AND s.shipment_date
            BETWEEN
                i.start_date
                AND i.end_date
),

support_base AS (

    SELECT
        sc.case_id,
        sc.case_date,
        sc.customer_id,
        sc.customer_segment,
        sc.destination_country,

        sc.order_id,
        sc.shipment_id,

        sc.case_type,
        sc.root_cause_category,
        sc.priority,
        sc.support_team,
        sc.channel,

        sc.first_response_minutes,
        sc.resolution_hours,

        sc.response_sla_met,
        sc.resolution_sla_met,
        sc.support_sla_met,

        sc.escalated_flag,
        sc.reopened_flag,
        sc.csat_score,

        sc.shipment_delayed_flag,
        sc.shipment_no_scan_flag,
        sc.shipment_damaged_flag,
        sc.shipment_lost_flag,

        sc.carrier_id,
        sc.carrier_name,

        sc.shipment_origin_city,
        sc.shipment_origin_country,
        sc.shipment_destination_city,
        sc.shipment_destination_country,

        sc.route_name,
        sc.route_scope,

        sc.network_load_factor,

        CASE
            WHEN i.shipment_id IS NOT NULL
            THEN 1
            ELSE 0
        END AS business_incident_flag,

        i.candidate_incident_id,
        COALESCE(
            i.anomaly_score,
            0
        ) AS anomaly_score

    FROM silver.support_enriched AS sc

    LEFT JOIN incident_shipments AS i
        ON sc.shipment_id
        = i.shipment_id
)

SELECT
    case_date AS report_date,

    customer_segment,
    destination_country,

    carrier_id,
    carrier_name,

    case_type,
    root_cause_category,
    priority,
    support_team,
    channel,

    business_incident_flag,
    candidate_incident_id,

    COUNT(*)
        AS support_cases,

    COUNT(
        DISTINCT customer_id
    ) AS customers_contacting,

    COUNT(
        DISTINCT shipment_id
    ) AS shipments_with_cases,

    ROUND(
        AVG(
            first_response_minutes
        ),
        2
    ) AS avg_first_response_minutes,

    ROUND(
        AVG(
            resolution_hours
        ),
        2
    ) AS avg_resolution_hours,

    ROUND(
        AVG(
            response_sla_met
        ) * 100,
        2
    ) AS response_sla_pct,

    ROUND(
        AVG(
            resolution_sla_met
        ) * 100,
        2
    ) AS resolution_sla_pct,

    ROUND(
        AVG(
            support_sla_met
        ) * 100,
        2
    ) AS support_sla_pct,

    ROUND(
        AVG(
            escalated_flag
        ) * 100,
        2
    ) AS escalation_rate_pct,

    ROUND(
        AVG(
            reopened_flag
        ) * 100,
        2
    ) AS reopen_rate_pct,

    ROUND(
        AVG(
            csat_score
        ),
        2
    ) AS avg_csat,

    SUM(
        shipment_delayed_flag
    ) AS delayed_shipment_cases,

    SUM(
        shipment_no_scan_flag
    ) AS no_scan_cases,

    SUM(
        shipment_damaged_flag
    ) AS damaged_cases,

    SUM(
        shipment_lost_flag
    ) AS lost_cases,

    ROUND(
        AVG(
            network_load_factor
        ) * 100,
        2
    ) AS avg_network_load_pct,

    MAX(
        anomaly_score
    ) AS anomaly_score

FROM support_base

WHERE
    case_date BETWEEN
        DATE '2025-01-01'
        AND DATE '2025-12-31'

GROUP BY
    case_date,
    customer_segment,
    destination_country,

    carrier_id,
    carrier_name,

    case_type,
    root_cause_category,
    priority,
    support_team,
    channel,

    business_incident_flag,
    candidate_incident_id

ORDER BY
    report_date,
    business_incident_flag DESC,
    carrier_name,
    case_type
;
