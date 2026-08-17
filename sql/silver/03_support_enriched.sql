CREATE OR REPLACE TABLE silver.support_enriched AS

SELECT
    sc.*,

    CAST(
        sc.created_ts
        AS DATE
    ) AS case_date,

    sh.carrier_name,
    sh.service_tier,

    sh.origin_city
        AS shipment_origin_city,

    sh.origin_country
        AS shipment_origin_country,

    sh.destination_city
        AS shipment_destination_city,

    sh.destination_country
        AS shipment_destination_country,

    sh.route_name,
    sh.route_scope,
    sh.network_load_bucket,

    sh.sla_met
        AS shipment_sla_met,

    sh.actual_transit_hours,
    sh.delay_hours,

    sh.order_total_eur,
    sh.order_status,
    sh.payment_status,

    CASE
        WHEN sc.priority IN ('Critical', 'High')
        THEN 1
        ELSE 0
    END AS high_priority_flag,

    CASE
        WHEN sc.support_sla_met = 0
        THEN 1
        ELSE 0
    END AS support_sla_breach_flag,

    CASE
        WHEN (
            sc.escalated_flag = 1
            OR sc.reopened_flag = 1
        )
        THEN 1
        ELSE 0
    END AS complex_case_flag

FROM bronze.support_cases AS sc

LEFT JOIN silver.shipments_enriched AS sh
    ON sc.shipment_id = sh.shipment_id
;
