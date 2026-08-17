CREATE OR REPLACE TABLE silver.shipments_enriched AS

SELECT
    s.*,

    CAST(
        s.shipment_created_ts
        AS DATE
    ) AS shipment_date,

    o.customer_id,
    o.customer_segment AS order_customer_segment,
    o.sales_channel,
    o.order_status,
    o.order_total_eur,
    o.payment_status,

    ow.warehouse_type
        AS origin_warehouse_type,
    ow.daily_capacity
        AS origin_daily_capacity,
    ow.automation_level
        AS origin_automation_level,
    ow.baseline_reliability
        AS origin_baseline_reliability,

    dw.warehouse_type
        AS destination_warehouse_type,
    dw.daily_capacity
        AS destination_daily_capacity,
    dw.automation_level
        AS destination_automation_level,
    dw.baseline_reliability
        AS destination_baseline_reliability,

    c.reliability_score
        AS carrier_reliability_score,
    c.scan_quality_score
        AS carrier_scan_quality_score,
    c.damage_rate_baseline
        AS carrier_damage_rate_baseline,
    c.loss_rate_baseline
        AS carrier_loss_rate_baseline,

    s.origin_city
        || ' → '
        || s.destination_city
        AS route_name,

    CASE
        WHEN s.cross_border = 1
        THEN 'Cross-border'
        ELSE 'Domestic'
    END AS route_scope,

    CASE
        WHEN s.network_load_factor < 0.60
        THEN '<60%'

        WHEN s.network_load_factor < 0.75
        THEN '60-75%'

        WHEN s.network_load_factor < 0.90
        THEN '75-90%'

        WHEN s.network_load_factor <= 1.00
        THEN '90-100%'

        ELSE '>100%'
    END AS network_load_bucket,

    CASE
        WHEN s.lost_flag = 1
        THEN 'Lost'

        WHEN s.damaged_flag = 1
        THEN 'Damaged'

        WHEN s.no_scan_flag = 1
        THEN 'No Scan'

        WHEN s.delayed_flag = 1
        THEN 'Delayed'

        ELSE 'Normal'
    END AS primary_issue_category,

    CASE
        WHEN (
            s.delayed_flag
            + s.no_scan_flag
            + s.damaged_flag
            + s.lost_flag
        ) > 0
        THEN 1
        ELSE 0
    END AS any_issue_flag

FROM bronze.shipments AS s

LEFT JOIN silver.orders_enriched AS o
    ON s.order_id = o.order_id

LEFT JOIN bronze.warehouses AS ow
    ON s.origin_warehouse_id
    = ow.warehouse_id

LEFT JOIN bronze.warehouses AS dw
    ON s.destination_warehouse_id
    = dw.warehouse_id

LEFT JOIN bronze.carriers AS c
    ON s.carrier_id = c.carrier_id
;
