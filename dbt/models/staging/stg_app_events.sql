SELECT
    event_id,
    session_id,
    event_sequence,
    event_type,
    CAST(event_ts AS TIMESTAMP) AS event_ts,
    CAST(event_ts AS DATE) AS event_date,
    customer_id,
    order_id,
    product_id,
    event_value_eur,
    device_type,
    traffic_source,
    country,
    authenticated_flag

FROM {{ source('bronze', 'app_events') }}
