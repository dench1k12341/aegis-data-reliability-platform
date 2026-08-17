from pathlib import Path

import numpy as np
import pandas as pd

from src.utils.config import (
    PROJECT_ROOT,
    get_simulation_config,
    load_config,
)


EUROPEAN_LOCATIONS = [
    ("Germany", "Berlin", 52.5200, 13.4050),
    ("Germany", "Frankfurt", 50.1109, 8.6821),
    ("Germany", "Munich", 48.1351, 11.5820),
    ("Poland", "Warsaw", 52.2297, 21.0122),
    ("Poland", "Krakow", 50.0647, 19.9450),
    ("Poland", "Wroclaw", 51.1079, 17.0385),
    ("France", "Paris", 48.8566, 2.3522),
    ("France", "Lyon", 45.7640, 4.8357),
    ("Netherlands", "Amsterdam", 52.3676, 4.9041),
    ("Netherlands", "Rotterdam", 51.9244, 4.4777),
    ("Belgium", "Brussels", 50.8503, 4.3517),
    ("Austria", "Vienna", 48.2082, 16.3738),
    ("Czech Republic", "Prague", 50.0755, 14.4378),
    ("Slovakia", "Bratislava", 48.1486, 17.1077),
    ("Slovakia", "Kosice", 48.7164, 21.2611),
    ("Hungary", "Budapest", 47.4979, 19.0402),
    ("Italy", "Milan", 45.4642, 9.1900),
    ("Italy", "Rome", 41.9028, 12.4964),
    ("Spain", "Madrid", 40.4168, -3.7038),
    ("Spain", "Barcelona", 41.3874, 2.1686),
    ("Portugal", "Lisbon", 38.7223, -9.1393),
    ("Denmark", "Copenhagen", 55.6761, 12.5683),
    ("Sweden", "Stockholm", 59.3293, 18.0686),
    ("Finland", "Helsinki", 60.1699, 24.9384),
    ("Lithuania", "Vilnius", 54.6872, 25.2797),
    ("Latvia", "Riga", 56.9496, 24.1052),
    ("Estonia", "Tallinn", 59.4370, 24.7536),
    ("Romania", "Bucharest", 44.4268, 26.1025),
    ("Croatia", "Zagreb", 45.8150, 15.9819),
    ("Slovenia", "Ljubljana", 46.0569, 14.5058),
]


CARRIER_NAMES = [
    "AeroParcel",
    "Atlas Freight",
    "BlueRoute",
    "CentralLink",
    "EuroSwift",
    "NorthStar Logistics",
    "PrimeTransit",
    "RapidBridge",
    "TransNova",
    "Vector Express",
]


PRODUCT_CATEGORIES = {
    "Electronics": (25, 1800),
    "Home & Living": (8, 650),
    "Fashion": (5, 300),
    "Sports": (8, 500),
    "Beauty": (4, 180),
    "Books & Media": (3, 120),
    "Automotive": (10, 900),
    "Office": (4, 350),
    "Toys": (5, 280),
    "Pet Supplies": (4, 250),
}


def ensure_output_directory() -> Path:
    output_dir = PROJECT_ROOT / "data" / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def generate_warehouses(
    rng: np.random.Generator,
    warehouse_count: int,
) -> pd.DataFrame:
    if warehouse_count > len(EUROPEAN_LOCATIONS):
        raise ValueError(
            f"Requested {warehouse_count} warehouses, but only "
            f"{len(EUROPEAN_LOCATIONS)} locations are configured."
        )

    locations = EUROPEAN_LOCATIONS[:warehouse_count]

    records = []

    for idx, (country, city, latitude, longitude) in enumerate(
        locations,
        start=1,
    ):
        warehouse_type = rng.choice(
            ["Mega Hub", "National Hub", "Regional Hub"],
            p=[0.15, 0.45, 0.40],
        )

        if warehouse_type == "Mega Hub":
            capacity = int(rng.integers(18000, 30001))
        elif warehouse_type == "National Hub":
            capacity = int(rng.integers(9000, 18001))
        else:
            capacity = int(rng.integers(3500, 9001))

        records.append(
            {
                "warehouse_id": f"WH{idx:03d}",
                "country": country,
                "city": city,
                "latitude": latitude,
                "longitude": longitude,
                "warehouse_type": warehouse_type,
                "daily_capacity": capacity,
                "automation_level": round(
                    float(rng.uniform(0.55, 0.98)),
                    3,
                ),
                "baseline_reliability": round(
                    float(rng.uniform(0.88, 0.99)),
                    3,
                ),
            }
        )

    return pd.DataFrame(records)


def generate_carriers(
    rng: np.random.Generator,
    carrier_count: int,
) -> pd.DataFrame:
    if carrier_count > len(CARRIER_NAMES):
        raise ValueError(
            f"Requested {carrier_count} carriers, but only "
            f"{len(CARRIER_NAMES)} names are configured."
        )

    records = []

    for idx, carrier_name in enumerate(
        CARRIER_NAMES[:carrier_count],
        start=1,
    ):
        service_tier = rng.choice(
            ["Economy", "Standard", "Premium", "Express"],
            p=[0.15, 0.45, 0.25, 0.15],
        )

        records.append(
            {
                "carrier_id": f"CAR{idx:03d}",
                "carrier_name": carrier_name,
                "service_tier": service_tier,
                "reliability_score": round(
                    float(rng.uniform(0.86, 0.98)),
                    3,
                ),
                "scan_quality_score": round(
                    float(rng.uniform(0.88, 0.995)),
                    3,
                ),
                "damage_rate_baseline": round(
                    float(rng.uniform(0.001, 0.012)),
                    4,
                ),
                "loss_rate_baseline": round(
                    float(rng.uniform(0.0003, 0.004)),
                    4,
                ),
            }
        )

    return pd.DataFrame(records)


def generate_products(
    rng: np.random.Generator,
    product_count: int,
) -> pd.DataFrame:
    categories = list(PRODUCT_CATEGORIES.keys())

    selected_categories = rng.choice(
        categories,
        size=product_count,
        replace=True,
        p=[
            0.15,
            0.13,
            0.15,
            0.10,
            0.09,
            0.08,
            0.08,
            0.08,
            0.07,
            0.07,
        ],
    )

    records = []

    for idx, category in enumerate(
        selected_categories,
        start=1,
    ):
        min_price, max_price = PRODUCT_CATEGORIES[category]

        list_price = round(
            float(
                np.exp(
                    rng.uniform(
                        np.log(min_price),
                        np.log(max_price),
                    )
                )
            ),
            2,
        )

        cost_ratio = float(rng.uniform(0.42, 0.78))
        unit_cost = round(list_price * cost_ratio, 2)

        records.append(
            {
                "product_id": f"PRD{idx:06d}",
                "product_name": f"{category} Product {idx:05d}",
                "category": category,
                "list_price_eur": list_price,
                "unit_cost_eur": unit_cost,
                "margin_pct": round(
                    ((list_price - unit_cost) / list_price) * 100,
                    2,
                ),
                "weight_kg": round(
                    float(
                        np.exp(
                            rng.uniform(
                                np.log(0.1),
                                np.log(25),
                            )
                        )
                    ),
                    3,
                ),
                "active_flag": 1,
            }
        )

    return pd.DataFrame(records)


def generate_customers(
    rng: np.random.Generator,
    customer_count: int,
) -> pd.DataFrame:
    unique_countries = sorted(
        {location[0] for location in EUROPEAN_LOCATIONS}
    )

    country_weights = rng.dirichlet(
        np.ones(len(unique_countries)) * 2.5
    )

    countries = rng.choice(
        unique_countries,
        size=customer_count,
        p=country_weights,
    )

    signup_dates = pd.to_datetime(
        rng.integers(
            pd.Timestamp("2022-01-01").value // 10**9,
            pd.Timestamp("2025-12-31").value // 10**9,
            size=customer_count,
        ),
        unit="s",
    ).normalize()

    customer_segments = rng.choice(
        ["Consumer", "SMB", "Enterprise"],
        size=customer_count,
        p=[0.82, 0.15, 0.03],
    )

    acquisition_channels = rng.choice(
        [
            "Organic",
            "Paid Search",
            "Social",
            "Referral",
            "Email",
            "Partner",
        ],
        size=customer_count,
        p=[0.30, 0.22, 0.15, 0.13, 0.12, 0.08],
    )

    records = pd.DataFrame(
        {
            "customer_id": [
                f"CUS{i:08d}"
                for i in range(1, customer_count + 1)
            ],
            "country": countries,
            "customer_segment": customer_segments,
            "acquisition_channel": acquisition_channels,
            "signup_date": signup_dates,
            "account_status": rng.choice(
                ["Active", "Inactive"],
                size=customer_count,
                p=[0.94, 0.06],
            ),
        }
    )

    return records


def save_dataset(
    dataframe: pd.DataFrame,
    output_dir: Path,
    name: str,
) -> None:
    parquet_path = output_dir / f"{name}.parquet"
    csv_path = output_dir / f"{name}.csv"

    dataframe.to_parquet(
        parquet_path,
        index=False,
    )

    dataframe.to_csv(
        csv_path,
        index=False,
    )


def main() -> None:
    print("=" * 72)
    print("AEGIS MASTER DATA GENERATOR")
    print("=" * 72)

    config = load_config()
    simulation = get_simulation_config(config)

    seed = config["project"]["random_seed"]
    rng = np.random.default_rng(seed)

    warehouse_count = config["network"]["warehouses"]
    carrier_count = config["network"]["carriers"]
    product_count = config["network"]["products"]
    customer_count = simulation["customers"]

    output_dir = ensure_output_directory()

    print()
    print(f"Simulation mode: {config['simulation']['mode']}")
    print(f"Random seed:     {seed}")
    print()

    warehouses = generate_warehouses(
        rng,
        warehouse_count,
    )

    carriers = generate_carriers(
        rng,
        carrier_count,
    )

    products = generate_products(
        rng,
        product_count,
    )

    customers = generate_customers(
        rng,
        customer_count,
    )

    save_dataset(
        warehouses,
        output_dir,
        "warehouses",
    )

    save_dataset(
        carriers,
        output_dir,
        "carriers",
    )

    save_dataset(
        products,
        output_dir,
        "products",
    )

    save_dataset(
        customers,
        output_dir,
        "customers",
    )

    print("=" * 72)
    print("MASTER DATA SUMMARY")
    print("=" * 72)

    print()
    print(f"Customers:       {len(customers):,}")
    print(f"Products:        {len(products):,}")
    print(f"Warehouses:      {len(warehouses):,}")
    print(f"Carriers:        {len(carriers):,}")

    print()
    print(
        f"Customer countries: "
        f"{customers['country'].nunique()}"
    )

    print()
    print("Customer segments:")
    print(
        customers["customer_segment"]
        .value_counts()
        .to_string()
    )

    print()
    print("Product categories:")
    print(
        products["category"]
        .value_counts()
        .to_string()
    )

    print()
    print("Warehouse types:")
    print(
        warehouses["warehouse_type"]
        .value_counts()
        .to_string()
    )

    print()
    print("Files created:")
    for dataset in [
        "customers",
        "products",
        "warehouses",
        "carriers",
    ]:
        print(
            f"  {output_dir / (dataset + '.parquet')}"
        )

    print()
    print("AEGIS master data generation completed successfully.")


if __name__ == "__main__":
    main()