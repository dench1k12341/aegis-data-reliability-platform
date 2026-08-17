import numpy as np
import pandas as pd

from src.utils.config import (
    PROJECT_ROOT,
    get_simulation_config,
    load_config,
)


SIMULATION_START = pd.Timestamp("2025-01-01 00:00:00")
SIMULATION_END = pd.Timestamp("2025-12-31 23:59:59")


def load_master_data():
    raw_dir = PROJECT_ROOT / "data" / "raw"

    customers = pd.read_parquet(raw_dir / "customers.parquet")
    products = pd.read_parquet(raw_dir / "products.parquet")

    customers["signup_date"] = pd.to_datetime(
        customers["signup_date"]
    )

    return customers, products


def generate_orders(rng, customers, order_count):
    customer_indices = rng.integers(
        0,
        len(customers),
        size=order_count,
    )

    selected = (
        customers
        .iloc[customer_indices]
        .reset_index(drop=True)
    )

    lower_dates = selected["signup_date"].copy()

    lower_dates = lower_dates.where(
        lower_dates > SIMULATION_START,
        SIMULATION_START,
    )

    available_seconds = (
        SIMULATION_END - lower_dates
    ).dt.total_seconds()

    random_seconds = (
        rng.random(order_count)
        * available_seconds.to_numpy()
    ).astype(np.int64)

    order_timestamps = (
        lower_dates
        + pd.to_timedelta(random_seconds, unit="s")
    )

    orders = pd.DataFrame(
        {
            "order_id": [
                f"ORD{i:09d}"
                for i in range(1, order_count + 1)
            ],
            "customer_id":
                selected["customer_id"].to_numpy(),
            "destination_country":
                selected["country"].to_numpy(),
            "customer_segment":
                selected["customer_segment"].to_numpy(),
            "sales_channel": rng.choice(
                [
                    "Web",
                    "Mobile App",
                    "Marketplace",
                    "Partner API",
                ],
                size=order_count,
                p=[0.43, 0.39, 0.12, 0.06],
            ),
            "order_ts":
                order_timestamps.to_numpy(),
        }
    )

    return orders


def generate_order_items(
    rng,
    orders,
    products,
):
    item_counts = rng.choice(
        [1, 2, 3, 4, 5],
        size=len(orders),
        p=[0.46, 0.30, 0.14, 0.07, 0.03],
    )

    repeated_orders = np.repeat(
        orders["order_id"].to_numpy(),
        item_counts,
    )

    line_count = len(repeated_orders)

    product_indices = rng.integers(
        0,
        len(products),
        size=line_count,
    )

    selected_products = (
        products
        .iloc[product_indices]
        .reset_index(drop=True)
    )

    quantities = rng.choice(
        [1, 2, 3],
        size=line_count,
        p=[0.82, 0.15, 0.03],
    )

    price_multiplier = rng.uniform(
        0.90,
        1.05,
        size=line_count,
    )

    unit_price = np.round(
        selected_products[
            "list_price_eur"
        ].to_numpy()
        * price_multiplier,
        2,
    )

    discount_flag = (
        rng.random(line_count) < 0.31
    )

    discount_pct = np.where(
        discount_flag,
        rng.uniform(
            0.05,
            0.25,
            size=line_count,
        ),
        0.0,
    )

    gross_value = np.round(
        unit_price * quantities,
        2,
    )

    discount_value = np.round(
        gross_value * discount_pct,
        2,
    )

    net_value = np.round(
        gross_value - discount_value,
        2,
    )

    order_items = pd.DataFrame(
        {
            "order_item_id": [
                f"ITM{i:010d}"
                for i in range(
                    1,
                    line_count + 1,
                )
            ],
            "order_id": repeated_orders,
            "product_id":
                selected_products[
                    "product_id"
                ].to_numpy(),
            "quantity": quantities,
            "unit_price_eur": unit_price,
            "discount_pct":
                np.round(discount_pct, 4),
            "gross_value_eur":
                gross_value,
            "discount_value_eur":
                discount_value,
            "net_value_eur":
                net_value,
        }
    )

    return order_items


def add_order_financials(
    orders,
    order_items,
):
    financials = (
        order_items
        .groupby(
            "order_id",
            as_index=False,
        )
        .agg(
            line_count=(
                "order_item_id",
                "count",
            ),
            units=(
                "quantity",
                "sum",
            ),
            gross_merchandise_value_eur=(
                "gross_value_eur",
                "sum",
            ),
            discount_eur=(
                "discount_value_eur",
                "sum",
            ),
            merchandise_revenue_eur=(
                "net_value_eur",
                "sum",
            ),
        )
    )

    orders = orders.merge(
        financials,
        on="order_id",
        how="left",
        validate="one_to_one",
    )

    orders["shipping_fee_eur"] = np.where(
        orders[
            "merchandise_revenue_eur"
        ] >= 80,
        0.0,
        np.where(
            orders[
                "merchandise_revenue_eur"
            ] >= 40,
            3.99,
            6.99,
        ),
    )

    orders["order_total_eur"] = np.round(
        orders[
            "merchandise_revenue_eur"
        ]
        + orders["shipping_fee_eur"],
        2,
    )

    return orders


def generate_payments(
    rng,
    orders,
):
    payment_status = rng.choice(
        [
            "Paid",
            "Failed",
            "Refunded",
            "Pending",
        ],
        size=len(orders),
        p=[0.935, 0.025, 0.025, 0.015],
    )

    status_map = {
        "Paid": "Completed",
        "Failed": "Cancelled",
        "Refunded": "Returned",
        "Pending": "Pending",
    }

    orders = orders.copy()

    orders["order_status"] = [
        status_map[status]
        for status in payment_status
    ]

    payment_delay = rng.integers(
        1,
        46,
        size=len(orders),
    )

    payment_ts = (
        orders["order_ts"]
        + pd.to_timedelta(
            payment_delay,
            unit="m",
        )
    )

    payments = pd.DataFrame(
        {
            "payment_id": [
                f"PAY{i:09d}"
                for i in range(
                    1,
                    len(orders) + 1,
                )
            ],
            "order_id":
                orders[
                    "order_id"
                ].to_numpy(),
            "payment_ts":
                payment_ts,
            "payment_method":
                rng.choice(
                    [
                        "Card",
                        "PayPal",
                        "Bank Transfer",
                        "Digital Wallet",
                        "Buy Now Pay Later",
                    ],
                    size=len(orders),
                    p=[
                        0.55,
                        0.17,
                        0.10,
                        0.12,
                        0.06,
                    ],
                ),
            "payment_status":
                payment_status,
            "payment_amount_eur":
                orders[
                    "order_total_eur"
                ].to_numpy(),
            "fraud_score":
                np.round(
                    rng.beta(
                        1.5,
                        12,
                        size=len(orders),
                    ),
                    4,
                ),
        }
    )

    return orders, payments


def validate_data(
    customers,
    products,
    orders,
    order_items,
    payments,
):
    assert orders["order_id"].is_unique

    assert order_items[
        "order_item_id"
    ].is_unique

    assert payments[
        "payment_id"
    ].is_unique

    assert orders[
        "customer_id"
    ].isin(
        customers["customer_id"]
    ).all()

    assert order_items[
        "order_id"
    ].isin(
        orders["order_id"]
    ).all()

    assert order_items[
        "product_id"
    ].isin(
        products["product_id"]
    ).all()

    assert payments[
        "order_id"
    ].isin(
        orders["order_id"]
    ).all()

    assert len(payments) == len(orders)

    assert (
        payments[
            "order_id"
        ].nunique()
        == len(orders)
    )

    assert (
        orders[
            "order_total_eur"
        ] >= 0
    ).all()

    assert (
        order_items[
            "net_value_eur"
        ] >= 0
    ).all()

    payment_check = orders[
        [
            "order_id",
            "order_total_eur",
        ]
    ].merge(
        payments[
            [
                "order_id",
                "payment_amount_eur",
            ]
        ],
        on="order_id",
        validate="one_to_one",
    )

    difference = (
        payment_check[
            "order_total_eur"
        ]
        - payment_check[
            "payment_amount_eur"
        ]
    ).abs()

    assert (
        difference <= 0.01
    ).all()

    signup_check = orders[
        [
            "customer_id",
            "order_ts",
        ]
    ].merge(
        customers[
            [
                "customer_id",
                "signup_date",
            ]
        ],
        on="customer_id",
        validate="many_to_one",
    )

    assert (
        signup_check["order_ts"]
        >= signup_check["signup_date"]
    ).all()


def main():
    print("=" * 72)
    print("AEGIS COMMERCE DATA GENERATOR")
    print("=" * 72)

    config = load_config()

    simulation = get_simulation_config(
        config
    )

    seed = (
        config["project"]["random_seed"]
        + 101
    )

    rng = np.random.default_rng(seed)

    order_count = simulation["orders"]

    customers, products = (
        load_master_data()
    )

    print()
    print(
        f"Simulation mode: "
        f"{config['simulation']['mode']}"
    )
    print(f"Random seed:     {seed}")
    print(
        f"Orders target:   "
        f"{order_count:,}"
    )
    print()

    orders = generate_orders(
        rng,
        customers,
        order_count,
    )

    order_items = generate_order_items(
        rng,
        orders,
        products,
    )

    orders = add_order_financials(
        orders,
        order_items,
    )

    orders, payments = (
        generate_payments(
            rng,
            orders,
        )
    )

    validate_data(
        customers,
        products,
        orders,
        order_items,
        payments,
    )

    output_dir = (
        PROJECT_ROOT
        / "data"
        / "raw"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    orders.to_parquet(
        output_dir / "orders.parquet",
        index=False,
    )

    order_items.to_parquet(
        output_dir
        / "order_items.parquet",
        index=False,
    )

    payments.to_parquet(
        output_dir
        / "payments.parquet",
        index=False,
    )

    print("=" * 72)
    print("COMMERCE DATA SUMMARY")
    print("=" * 72)

    print()
    print(
        f"Orders:          "
        f"{len(orders):,}"
    )

    print(
        f"Order items:     "
        f"{len(order_items):,}"
    )

    print(
        f"Payments:        "
        f"{len(payments):,}"
    )

    print()

    print(
        "Order date range: "
        f"{orders['order_ts'].min():%Y-%m-%d}"
        " to "
        f"{orders['order_ts'].max():%Y-%m-%d}"
    )

    print()

    print(
        "Gross merchandise value: "
        f"€{orders['gross_merchandise_value_eur'].sum():,.2f}"
    )

    print(
        "Net order value:          "
        f"€{orders['order_total_eur'].sum():,.2f}"
    )

    print(
        "Average order value:      "
        f"€{orders['order_total_eur'].mean():,.2f}"
    )

    print()
    print("Order status:")

    print(
        orders[
            "order_status"
        ]
        .value_counts()
        .to_string()
    )

    print()
    print("Payment status:")

    print(
        payments[
            "payment_status"
        ]
        .value_counts()
        .to_string()
    )

    print()
    print(
        "BASELINE DATA CONTRACT: PASSED"
    )

    print()

    print(
        "AEGIS commerce data generation "
        "completed successfully."
    )


if __name__ == "__main__":
    main()