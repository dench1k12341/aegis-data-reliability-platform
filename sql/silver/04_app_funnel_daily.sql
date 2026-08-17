CREATE OR REPLACE TABLE silver.app_funnel_daily AS

WITH daily AS (
    SELECT
        CAST(event_ts AS DATE)
            AS event_date,

        COUNT(*)
            AS total_events,

        COUNT(
            DISTINCT session_id
        ) AS sessions,

        COUNT(
            DISTINCT customer_id
        ) AS active_customers,

        SUM(
            CASE
                WHEN event_type = 'session_start'
                THEN 1 ELSE 0
            END
        ) AS session_start_events,

        SUM(
            CASE
                WHEN event_type = 'product_view'
                THEN 1 ELSE 0
            END
        ) AS product_view_events,

        SUM(
            CASE
                WHEN event_type = 'search'
                THEN 1 ELSE 0
            END
        ) AS search_events,

        SUM(
            CASE
                WHEN event_type = 'category_view'
                THEN 1 ELSE 0
            END
        ) AS category_view_events,

        SUM(
            CASE
                WHEN event_type = 'add_to_cart'
                THEN 1 ELSE 0
            END
        ) AS add_to_cart_events,

        SUM(
            CASE
                WHEN event_type = 'checkout_started'
                THEN 1 ELSE 0
            END
        ) AS checkout_events,

        SUM(
            CASE
                WHEN event_type = 'purchase'
                THEN 1 ELSE 0
            END
        ) AS purchase_events,

        SUM(
            CASE
                WHEN event_type = 'payment_failed'
                THEN 1 ELSE 0
            END
        ) AS payment_failed_events,

        SUM(
            CASE
                WHEN event_type = 'checkout_pending'
                THEN 1 ELSE 0
            END
        ) AS checkout_pending_events,

        SUM(
            CASE
                WHEN event_type = 'purchase'
                     AND event_value_eur IS NULL
                THEN 1 ELSE 0
            END
        ) AS purchase_value_null_count,

        ROUND(
            COALESCE(
                SUM(
                    CASE
                        WHEN event_type = 'purchase'
                        THEN event_value_eur
                        ELSE 0
                    END
                ),
                0
            ),
            2
        ) AS purchase_event_revenue_eur

    FROM bronze.app_events

    GROUP BY
        CAST(event_ts AS DATE)
)

SELECT
    *,

    ROUND(
        100.0
        * add_to_cart_events
        / NULLIF(
            product_view_events,
            0
        ),
        2
    ) AS view_to_cart_pct,

    ROUND(
        100.0
        * checkout_events
        / NULLIF(
            add_to_cart_events,
            0
        ),
        2
    ) AS cart_to_checkout_pct,

    ROUND(
        100.0
        * purchase_events
        / NULLIF(
            checkout_events,
            0
        ),
        2
    ) AS checkout_to_purchase_pct,

    ROUND(
        100.0
        * (
            purchase_events
            - purchase_value_null_count
        )
        / NULLIF(
            purchase_events,
            0
        ),
        2
    ) AS purchase_value_completeness_pct

FROM daily
;
