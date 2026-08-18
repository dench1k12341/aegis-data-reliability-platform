SELECT
    customer_id,
    country,
    customer_segment,
    acquisition_channel,
    signup_date,
    account_status

FROM {{ source('bronze', 'customers') }}
