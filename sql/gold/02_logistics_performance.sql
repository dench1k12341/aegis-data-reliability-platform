CREATE OR REPLACE TABLE gold.logistics_performance AS

WITH shipment_hubs AS (

    SELECT
        shipment_date AS report_date,
        shipment_id,
        order_id,

        origin_warehouse_id
            AS warehouse_id,

        'Origin'
            AS warehouse_role,

        carrier_id,
        carrier_name,
        service_tier,

        route_name,
        route_scope,

        distance_km,
        network_load_factor,
        actual_transit_hours,
        delay_hours,

        delayed_flag,
        sla_met,
        no_scan_flag,
        damaged_flag,
        lost_flag,
        any_issue_flag,

        order_total_eur

    FROM silver.shipments_enriched

    UNION ALL

    SELECT
        shipment_date AS report_date,
        shipment_id,
        order_id,

        destination_warehouse_id
            AS warehouse_id,

        'Destination'
            AS warehouse_role,

        carrier_id,
        carrier_name,
        service_tier,

        route_name,
        route_scope,

        distance_km,
        network_load_factor,
        actual_transit_hours,
        delay_hours,

        delayed_flag,
        sla_met,
        no_scan_flag,
        damaged_flag,
        lost_flag,
        any_issue_flag,

        order_total_eur

    FROM silver.shipments_enriched
),

incident_dates AS (

    SELECT
        warehouse_id,

        CAST(
            incident_date
            AS DATE
        ) AS report_date,

        MAX(
            anomaly_score
        ) AS anomaly_score

    FROM (
        SELECT
            warehouse_id,
            anomaly_score,
            gs AS incident_date

        FROM
            meta.business_incidents,

            generate_series(
                start_date,
                end_date,
                INTERVAL 1 DAY
            ) AS generated(gs)

        WHERE
            classification
            = 'BUSINESS_INCIDENT_CANDIDATE'
    )

    GROUP BY
        warehouse_id,
        CAST(
            incident_date
            AS DATE
        )
),

aggregated AS (

    SELECT
        h.report_date,

        h.warehouse_id,

        w.city,
        w.country,
        w.warehouse_type,
        w.daily_capacity,
        w.automation_level,
        w.baseline_reliability,

        h.warehouse_role,

        h.carrier_id,
        h.carrier_name,
        h.service_tier,

        h.route_name,
        h.route_scope,

        COUNT(*)
            AS shipment_touches,

        COUNT(
            DISTINCT h.shipment_id
        ) AS shipments,

        SUM(
            h.delayed_flag
        ) AS delayed_shipments,

        SUM(
            h.sla_met
        ) AS sla_met_shipments,

        SUM(
            h.no_scan_flag
        ) AS no_scan_shipments,

        SUM(
            h.damaged_flag
        ) AS damaged_shipments,

        SUM(
            h.lost_flag
        ) AS lost_shipments,

        SUM(
            h.any_issue_flag
        ) AS issue_shipments,

        ROUND(
            AVG(
                h.sla_met
            ) * 100,
            2
        ) AS delivery_sla_pct,

        ROUND(
            AVG(
                h.delayed_flag
            ) * 100,
            2
        ) AS delay_rate_pct,

        ROUND(
            AVG(
                h.network_load_factor
            ) * 100,
            2
        ) AS avg_network_load_pct,

        ROUND(
            AVG(
                h.actual_transit_hours
            ),
            2
        ) AS avg_transit_hours,

        ROUND(
            AVG(
                h.delay_hours
            ),
            2
        ) AS avg_delay_hours,

        ROUND(
            AVG(
                h.distance_km
            ),
            1
        ) AS avg_distance_km,

        ROUND(
            SUM(
                h.order_total_eur
            ),
            2
        ) AS handled_order_value_eur,

        CASE
            WHEN i.report_date IS NOT NULL
            THEN 1
            ELSE 0
        END AS business_incident_flag,

        COALESCE(
            i.anomaly_score,
            0
        ) AS anomaly_score

    FROM shipment_hubs AS h

    LEFT JOIN bronze.warehouses AS w
        ON h.warehouse_id
        = w.warehouse_id

    LEFT JOIN incident_dates AS i
        ON h.warehouse_id
        = i.warehouse_id

        AND h.report_date
        = i.report_date

    WHERE
        h.report_date BETWEEN
            DATE '2025-01-01'
            AND DATE '2025-12-31'

    GROUP BY
        h.report_date,
        h.warehouse_id,

        w.city,
        w.country,
        w.warehouse_type,
        w.daily_capacity,
        w.automation_level,
        w.baseline_reliability,

        h.warehouse_role,

        h.carrier_id,
        h.carrier_name,
        h.service_tier,

        h.route_name,
        h.route_scope,

        i.report_date,
        i.anomaly_score
)

SELECT
    *,

    CASE
        WHEN business_incident_flag = 1
        THEN 'Business Incident'

        WHEN avg_network_load_pct > 100
        THEN 'Over Capacity'

        WHEN delay_rate_pct >= 30
        THEN 'Performance Risk'

        ELSE 'Normal'
    END AS operational_status

FROM aggregated

ORDER BY
    report_date,
    warehouse_id,
    carrier_id,
    route_name
;
