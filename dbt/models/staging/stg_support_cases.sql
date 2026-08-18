SELECT
    case_id,
    customer_id,
    order_id,
    shipment_id,

    customer_segment,
    destination_country,

    carrier_id,
    origin_warehouse_id,
    contact_number,

    case_type,
    root_cause_category,
    priority,
    support_team,
    channel,

    CAST(created_ts AS TIMESTAMP) AS created_ts,
    CAST(created_ts AS DATE) AS case_date,

    CAST(first_response_ts AS TIMESTAMP) AS first_response_ts,
    CAST(resolved_ts AS TIMESTAMP) AS resolved_ts,

    first_response_minutes,
    resolution_hours,

    response_sla_minutes,
    resolution_sla_hours,

    response_sla_met,
    resolution_sla_met,
    support_sla_met,

    escalated_flag,
    reopened_flag,
    csat_score,

    network_load_factor,

    shipment_delayed_flag,
    shipment_no_scan_flag,
    shipment_damaged_flag,
    shipment_lost_flag

FROM {{ source('bronze', 'support_cases') }}
