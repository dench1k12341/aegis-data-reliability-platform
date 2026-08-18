SELECT
    shipment_date AS report_date,

    COUNT(*) AS shipments,

    ROUND(
        AVG(delayed_flag) * 100,
        2
    ) AS delay_rate_pct,

    ROUND(
        AVG(sla_met) * 100,
        2
    ) AS delivery_sla_pct,

    ROUND(
        AVG(network_load_factor) * 100,
        2
    ) AS avg_network_load_pct

FROM {{ ref('silver_shipments') }}

GROUP BY shipment_date
