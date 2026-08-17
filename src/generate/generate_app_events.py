import numpy as np
import pandas as pd

from src.utils.config import (
    PROJECT_ROOT,
    get_simulation_config,
    load_config,
)


SIMULATION_START = pd.Timestamp(
    "2025-01-01 00:00:00"
)

SIMULATION_END = pd.Timestamp(
    "2025-12-31 23:59:59"
)


def load_source_data():
    raw_dir = PROJECT_ROOT / "data" / "raw"

    customers = pd.read_parquet(
        raw_dir / "customers.parquet"
    )

    orders = pd.read_parquet(
        raw_dir / "orders.parquet"
    )

    products = pd.read_parquet(
        raw_dir / "products.parquet"
    )

    orders["order_ts"] = pd.to_datetime(
        orders["order_ts"]
    )

    return customers, orders, products


def terminal_event_type(
    order_status,
):
    if order_status in {
        "Completed",
        "Returned",
    }:
        return "purchase"

    if order_status == "Cancelled":
        return "payment_failed"

    return "checkout_pending"


def generate_order_funnel_events(
    rng,
    orders,
    products,
):
    product_ids = (
        products["product_id"]
        .to_numpy()
    )

    traffic_sources = [
        "Organic",
        "Paid Search",
        "Social",
        "Email",
        "Referral",
        "Direct",
        "Partner",
    ]

    device_types = [
        "Desktop",
        "Mobile",
        "Tablet",
    ]

    records = []

    event_counter = 1

    for index, order in orders.iterrows():
        session_id = (
            f"SES{index + 1:09d}"
        )

        product_id = rng.choice(
            product_ids
        )

        session_start_ts = (
            order["order_ts"]
            - pd.Timedelta(
                minutes=float(
                    rng.uniform(
                        12,
                        150,
                    )
                )
            )
        )

        product_view_ts = (
            session_start_ts
            + pd.Timedelta(
                minutes=float(
                    rng.uniform(
                        1,
                        8,
                    )
                )
            )
        )

        add_to_cart_ts = (
            product_view_ts
            + pd.Timedelta(
                minutes=float(
                    rng.uniform(
                        1,
                        14,
                    )
                )
            )
        )

        checkout_ts = (
            add_to_cart_ts
            + pd.Timedelta(
                minutes=float(
                    rng.uniform(
                        1,
                        10,
                    )
                )
            )
        )

        final_ts = order[
            "order_ts"
        ]

        traffic_source = rng.choice(
            traffic_sources,
            p=[
                0.27,
                0.20,
                0.13,
                0.11,
                0.10,
                0.13,
                0.06,
            ],
        )

        device_type = rng.choice(
            device_types,
            p=[
                0.36,
                0.57,
                0.07,
            ],
        )

        funnel = [
            (
                "session_start",
                session_start_ts,
                None,
                None,
            ),
            (
                "product_view",
                product_view_ts,
                product_id,
                None,
            ),
            (
                "add_to_cart",
                add_to_cart_ts,
                product_id,
                None,
            ),
            (
                "checkout_started",
                checkout_ts,
                product_id,
                order[
                    "order_total_eur"
                ],
            ),
            (
                terminal_event_type(
                    order[
                        "order_status"
                    ]
                ),
                final_ts,
                product_id,
                order[
                    "order_total_eur"
                ],
            ),
        ]

        for sequence, (
            event_type,
            event_ts,
            event_product_id,
            event_value,
        ) in enumerate(
            funnel,
            start=1,
        ):
            records.append(
                {
                    "event_id":
                        f"EVAPP{event_counter:010d}",
                    "session_id":
                        session_id,
                    "event_sequence":
                        sequence,
                    "event_type":
                        event_type,
                    "event_ts":
                        event_ts,
                    "customer_id":
                        order[
                            "customer_id"
                        ],
                    "order_id":
                        order[
                            "order_id"
                        ],
                    "product_id":
                        event_product_id,
                    "event_value_eur":
                        event_value,
                    "device_type":
                        device_type,
                    "traffic_source":
                        traffic_source,
                    "country":
                        order[
                            "destination_country"
                        ],
                    "authenticated_flag":
                        1,
                }
            )

            event_counter += 1

    return (
        pd.DataFrame(records),
        event_counter,
    )


def generate_ambient_events(
    rng,
    customers,
    products,
    event_count,
    event_counter,
):
    if event_count <= 0:
        return pd.DataFrame()

    customer_indices = rng.integers(
        0,
        len(customers),
        size=event_count,
    )

    selected_customers = (
        customers
        .iloc[
            customer_indices
        ]
        .reset_index(
            drop=True
        )
    )

    product_ids = (
        products[
            "product_id"
        ]
        .to_numpy()
    )

    event_types = rng.choice(
        [
            "session_start",
            "search",
            "category_view",
            "product_view",
        ],
        size=event_count,
        p=[
            0.28,
            0.24,
            0.18,
            0.30,
        ],
    )

    timestamps_seconds = rng.integers(
        SIMULATION_START.value
        // 10**9,
        SIMULATION_END.value
        // 10**9,
        size=event_count,
    )

    timestamps = pd.to_datetime(
        timestamps_seconds,
        unit="s",
    )

    product_id = np.where(
        event_types
        == "product_view",
        rng.choice(
            product_ids,
            size=event_count,
        ),
        None,
    )

    traffic_source = rng.choice(
        [
            "Organic",
            "Paid Search",
            "Social",
            "Email",
            "Referral",
            "Direct",
            "Partner",
        ],
        size=event_count,
        p=[
            0.27,
            0.20,
            0.13,
            0.11,
            0.10,
            0.13,
            0.06,
        ],
    )

    device_type = rng.choice(
        [
            "Desktop",
            "Mobile",
            "Tablet",
        ],
        size=event_count,
        p=[
            0.36,
            0.57,
            0.07,
        ],
    )

    ambient_session_ids = [
        f"AMB{i:09d}"
        for i in range(
            1,
            event_count + 1,
        )
    ]

    ambient = pd.DataFrame(
        {
            "event_id": [
                f"EVAPP{i:010d}"
                for i in range(
                    event_counter,
                    event_counter
                    + event_count,
                )
            ],
            "session_id":
                ambient_session_ids,
            "event_sequence":
                np.ones(
                    event_count,
                    dtype=int,
                ),
            "event_type":
                event_types,
            "event_ts":
                timestamps,
            "customer_id":
                selected_customers[
                    "customer_id"
                ].to_numpy(),
            "order_id":
                [None] * event_count,
            "product_id":
                product_id,
            "event_value_eur":
                [None] * event_count,
            "device_type":
                device_type,
            "traffic_source":
                traffic_source,
            "country":
                selected_customers[
                    "country"
                ].to_numpy(),
            "authenticated_flag":
                rng.choice(
                    [0, 1],
                    size=event_count,
                    p=[
                        0.18,
                        0.82,
                    ],
                ),
        }
    )

    return ambient


def generate_app_events(
    rng,
    customers,
    orders,
    products,
    target_count,
):
    required_funnel_events = (
        len(orders) * 5
    )

    if target_count < required_funnel_events:
        raise ValueError(
            "App event target is too small. "
            f"Need at least "
            f"{required_funnel_events:,} "
            "events for the order funnels."
        )

    funnel_events, next_counter = (
        generate_order_funnel_events(
            rng,
            orders,
            products,
        )
    )

    ambient_count = (
        target_count
        - len(funnel_events)
    )

    ambient_events = (
        generate_ambient_events(
            rng,
            customers,
            products,
            ambient_count,
            next_counter,
        )
    )

    events = pd.concat(
        [
            funnel_events,
            ambient_events,
        ],
        ignore_index=True,
    )

    events = (
        events
        .sort_values(
            [
                "event_ts",
                "event_id",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    return events


def validate_app_events(
    customers,
    orders,
    app_events,
    target_count,
):
    assert (
        len(app_events)
        == target_count
    )

    assert app_events[
        "event_id"
    ].is_unique

    assert app_events[
        "customer_id"
    ].isin(
        customers[
            "customer_id"
        ]
    ).all()

    linked_events = app_events[
        app_events[
            "order_id"
        ].notna()
    ]

    assert linked_events[
        "order_id"
    ].isin(
        orders[
            "order_id"
        ]
    ).all()

    checkout_count = (
        app_events[
            "event_type"
        ]
        .eq(
            "checkout_started"
        )
        .sum()
    )

    assert (
        checkout_count
        == len(orders)
    )

    purchase_orders = orders[
        orders[
            "order_status"
        ].isin(
            [
                "Completed",
                "Returned",
            ]
        )
    ]

    purchase_count = (
        app_events[
            "event_type"
        ]
        .eq(
            "purchase"
        )
        .sum()
    )

    assert (
        purchase_count
        == len(
            purchase_orders
        )
    )

    failed_orders = orders[
        orders[
            "order_status"
        ]
        == "Cancelled"
    ]

    failed_count = (
        app_events[
            "event_type"
        ]
        .eq(
            "payment_failed"
        )
        .sum()
    )

    assert (
        failed_count
        == len(
            failed_orders
        )
    )

    linked_event_counts = (
        linked_events
        .groupby(
            "order_id"
        )
        .size()
    )

    assert (
        linked_event_counts
        == 5
    ).all()


def main():
    print("=" * 72)
    print(
        "AEGIS APP & PRODUCT EVENT GENERATOR"
    )
    print("=" * 72)

    config = load_config()

    simulation = get_simulation_config(
        config
    )

    target_count = simulation[
        "app_events"
    ]

    seed = (
        config[
            "project"
        ][
            "random_seed"
        ]
        + 404
    )

    rng = np.random.default_rng(
        seed
    )

    customers, orders, products = (
        load_source_data()
    )

    print()
    print(
        f"Simulation mode: "
        f"{config['simulation']['mode']}"
    )

    print(
        f"Random seed:     "
        f"{seed}"
    )

    print(
        f"Event target:    "
        f"{target_count:,}"
    )

    print()

    app_events = (
        generate_app_events(
            rng,
            customers,
            orders,
            products,
            target_count,
        )
    )

    validate_app_events(
        customers,
        orders,
        app_events,
        target_count,
    )

    output_dir = (
        PROJECT_ROOT
        / "data"
        / "raw"
    )

    app_events.to_parquet(
        output_dir
        / "app_events.parquet",
        index=False,
    )

    print("=" * 72)
    print(
        "APP EVENT SUMMARY"
    )
    print("=" * 72)

    print()

    print(
        f"Events:             "
        f"{len(app_events):,}"
    )

    print(
        f"Unique customers:   "
        f"{app_events['customer_id'].nunique():,}"
    )

    print(
        f"Unique sessions:    "
        f"{app_events['session_id'].nunique():,}"
    )

    print(
        f"Order-linked events:"
        f" "
        f"{app_events['order_id'].notna().sum():,}"
    )

    print()

    print(
        "Event distribution:"
    )

    print(
        app_events[
            "event_type"
        ]
        .value_counts()
        .to_string()
    )

    print()

    checkout_count = (
        app_events[
            "event_type"
        ]
        .eq(
            "checkout_started"
        )
        .sum()
    )

    purchase_count = (
        app_events[
            "event_type"
        ]
        .eq(
            "purchase"
        )
        .sum()
    )

    conversion_rate = (
        purchase_count
        / checkout_count
        * 100
    )

    print(
        f"Checkout events:    "
        f"{checkout_count:,}"
    )

    print(
        f"Purchase events:    "
        f"{purchase_count:,}"
    )

    print(
        f"Checkout conversion:"
        f" "
        f"{conversion_rate:.2f}%"
    )

    print()

    print(
        "BASELINE EVENT CONTRACT: PASSED"
    )

    print()

    print(
        "File created:"
    )

    print(
        f"  "
        f"{output_dir / 'app_events.parquet'}"
    )

    print()

    print(
        "AEGIS app event generation "
        "completed successfully."
    )


if __name__ == "__main__":
    main()
