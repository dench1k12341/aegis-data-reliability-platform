import math

import numpy as np
import pandas as pd

from src.utils.config import (
    PROJECT_ROOT,
    get_simulation_config,
    load_config,
)


def load_source_data():
    raw_dir = PROJECT_ROOT / "data" / "raw"

    orders = pd.read_parquet(
        raw_dir / "orders.parquet"
    )

    warehouses = pd.read_parquet(
        raw_dir / "warehouses.parquet"
    )

    carriers = pd.read_parquet(
        raw_dir / "carriers.parquet"
    )

    orders["order_ts"] = pd.to_datetime(
        orders["order_ts"]
    )

    return orders, warehouses, carriers


def haversine_distance_km(
    lat1,
    lon1,
    lat2,
    lon2,
):
    earth_radius_km = 6371.0

    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a),
    )

    return earth_radius_km * c


def choose_weighted_warehouse(
    rng,
    candidates,
):
    weights = (
        candidates["daily_capacity"].to_numpy()
        * candidates["automation_level"].to_numpy()
        * candidates["baseline_reliability"].to_numpy()
    )

    weights = weights / weights.sum()

    selected_index = rng.choice(
        len(candidates),
        p=weights,
    )

    return candidates.iloc[selected_index]


def choose_route(
    rng,
    warehouses,
    destination_country,
):
    destination_candidates = warehouses[
        warehouses["country"]
        == destination_country
    ]

    if destination_candidates.empty:
        destination_candidates = warehouses

    destination = choose_weighted_warehouse(
        rng,
        destination_candidates,
    )

    domestic_route = (
        rng.random() < 0.18
    )

    if domestic_route:
        origin_candidates = warehouses[
            warehouses["country"]
            == destination["country"]
        ]

        if len(origin_candidates) > 1:
            origin_candidates = origin_candidates[
                origin_candidates["warehouse_id"]
                != destination["warehouse_id"]
            ]
    else:
        origin_candidates = warehouses[
            warehouses["country"]
            != destination["country"]
        ]

    if origin_candidates.empty:
        origin_candidates = warehouses[
            warehouses["warehouse_id"]
            != destination["warehouse_id"]
        ]

    origin = choose_weighted_warehouse(
        rng,
        origin_candidates,
    )

    return origin, destination


def calculate_network_load(
    rng,
    created_ts,
):
    month = created_ts.month
    weekday = created_ts.weekday()

    load = rng.normal(
        0.69,
        0.085,
    )

    if month in [11, 12]:
        load += 0.17

    elif month in [9, 10]:
        load += 0.07

    if weekday == 0:
        load += 0.04

    if weekday >= 5:
        load -= 0.05

    return round(
        float(
            np.clip(
                load,
                0.42,
                1.16,
            )
        ),
        4,
    )


def calculate_sla_hours(
    service_tier,
    distance_km,
):
    base_sla = {
        "Economy": 72,
        "Standard": 48,
        "Premium": 36,
        "Express": 24,
    }

    sla = base_sla[
        service_tier
    ]

    distance_adjustment = (
        distance_km * 0.012
    )

    return round(
        sla + distance_adjustment,
        2,
    )


def calculate_delay_probability(
    network_load,
    carrier_reliability,
    warehouse_reliability,
    distance_km,
    created_ts,
):
    probability = 0.035

    probability += (
        max(
            network_load - 0.75,
            0,
        )
        * 0.30
    )

    probability += (
        1 - carrier_reliability
    ) * 0.50

    probability += (
        1 - warehouse_reliability
    ) * 0.08

    if distance_km > 1200:
        probability += 0.055

    elif distance_km > 700:
        probability += 0.025

    if created_ts.month in [11, 12]:
        probability += 0.03

    if created_ts.weekday() >= 5:
        probability += 0.015

    return float(
        np.clip(
            probability,
            0.02,
            0.45,
        )
    )


def generate_shipments(
    rng,
    orders,
    warehouses,
    carriers,
    shipment_target,
):
    eligible_orders = orders[
        (
            orders["order_status"]
            == "Completed"
        )
        & (
            orders["order_ts"]
            <= pd.Timestamp(
                "2025-12-28 23:59:59"
            )
        )
    ].copy()

    if len(eligible_orders) < shipment_target:
        raise ValueError(
            "Not enough eligible completed orders "
            f"for {shipment_target:,} shipments. "
            f"Available: {len(eligible_orders):,}"
        )

    selected_indices = rng.choice(
        eligible_orders.index.to_numpy(),
        size=shipment_target,
        replace=False,
    )

    selected_orders = (
        eligible_orders
        .loc[selected_indices]
        .sort_values("order_ts")
        .reset_index(drop=True)
    )

    carrier_weights = rng.dirichlet(
        np.ones(len(carriers)) * 3.5
    )

    shipment_records = []

    for idx, order in selected_orders.iterrows():
        carrier_index = rng.choice(
            len(carriers),
            p=carrier_weights,
        )

        carrier = carriers.iloc[
            carrier_index
        ]

        origin, destination = choose_route(
            rng,
            warehouses,
            order["destination_country"],
        )

        distance_km = (
            haversine_distance_km(
                origin["latitude"],
                origin["longitude"],
                destination["latitude"],
                destination["longitude"],
            )
        )

        distance_km = max(
            distance_km,
            25.0,
        )

        pick_pack_hours = float(
            rng.uniform(
                2.0,
                20.0,
            )
        )

        created_ts = (
            order["order_ts"]
            + pd.Timedelta(
                hours=pick_pack_hours
            )
        )

        network_load = (
            calculate_network_load(
                rng,
                created_ts,
            )
        )

        sla_hours = (
            calculate_sla_hours(
                carrier["service_tier"],
                distance_km,
            )
        )

        delay_probability = (
            calculate_delay_probability(
                network_load,
                carrier[
                    "reliability_score"
                ],
                origin[
                    "baseline_reliability"
                ],
                distance_km,
                created_ts,
            )
        )

        delayed_flag = int(
            rng.random()
            < delay_probability
        )

        no_scan_probability = (
            0.008
            + (
                1
                - carrier[
                    "scan_quality_score"
                ]
            ) * 0.18
            + max(
                network_load - 0.85,
                0,
            ) * 0.06
        )

        no_scan_flag = int(
            rng.random()
            < no_scan_probability
        )

        damage_probability = (
            carrier[
                "damage_rate_baseline"
            ]
            + (
                0.003
                if distance_km > 1000
                else 0
            )
            + max(
                network_load - 0.95,
                0,
            ) * 0.015
        )

        damaged_flag = int(
            rng.random()
            < damage_probability
        )

        loss_probability = (
            carrier[
                "loss_rate_baseline"
            ]
            + (
                0.001
                if distance_km > 1300
                else 0
            )
        )

        lost_flag = int(
            rng.random()
            < loss_probability
        )

        if delayed_flag:
            overload_component = (
                max(
                    network_load - 0.80,
                    0,
                )
                * 20
            )

            delay_hours = float(
                rng.gamma(
                    shape=2.1,
                    scale=2.8,
                )
                + overload_component
            )

            actual_transit_hours = (
                sla_hours
                + delay_hours
            )

        else:
            actual_transit_hours = (
                sla_hours
                * float(
                    rng.uniform(
                        0.56,
                        0.94,
                    )
                )
            )

            delay_hours = 0.0

        if lost_flag:
            actual_transit_hours += float(
                rng.uniform(
                    18,
                    60,
                )
            )

        expected_delivery_ts = (
            created_ts
            + pd.Timedelta(
                hours=sla_hours
            )
        )

        final_event_ts = (
            created_ts
            + pd.Timedelta(
                hours=actual_transit_hours
            )
        )

        if lost_flag:
            delivery_ts = pd.NaT
            shipment_status = "Lost"
            sla_met = 0

        else:
            delivery_ts = final_event_ts

            shipment_status = (
                "Delivered"
            )

            sla_met = int(
                delivery_ts
                <= expected_delivery_ts
            )

        cross_border = int(
            origin["country"]
            != destination["country"]
        )

        shipment_records.append(
            {
                "shipment_id":
                    f"SHP{idx + 1:09d}",
                "order_id":
                    order["order_id"],
                "carrier_id":
                    carrier["carrier_id"],
                "carrier_name":
                    carrier["carrier_name"],
                "service_tier":
                    carrier["service_tier"],
                "origin_warehouse_id":
                    origin["warehouse_id"],
                "origin_city":
                    origin["city"],
                "origin_country":
                    origin["country"],
                "destination_warehouse_id":
                    destination[
                        "warehouse_id"
                    ],
                "destination_city":
                    destination["city"],
                "destination_country":
                    destination["country"],
                "shipment_created_ts":
                    created_ts,
                "expected_delivery_ts":
                    expected_delivery_ts,
                "delivery_ts":
                    delivery_ts,
                "distance_km":
                    round(
                        distance_km,
                        1,
                    ),
                "cross_border":
                    cross_border,
                "network_load_factor":
                    network_load,
                "sla_hours":
                    sla_hours,
                "actual_transit_hours":
                    round(
                        actual_transit_hours,
                        2,
                    ),
                "delay_hours":
                    round(
                        max(
                            actual_transit_hours
                            - sla_hours,
                            0,
                        ),
                        2,
                    ),
                "delay_probability":
                    round(
                        delay_probability,
                        4,
                    ),
                "delayed_flag":
                    delayed_flag,
                "sla_met":
                    sla_met,
                "no_scan_flag":
                    no_scan_flag,
                "damaged_flag":
                    damaged_flag,
                "lost_flag":
                    lost_flag,
                "shipment_status":
                    shipment_status,
            }
        )

    return pd.DataFrame(
        shipment_records
    )


def generate_tracking_events(
    rng,
    shipments,
    tracking_target,
):
    event_records = []

    event_counter = 1

    for _, shipment in shipments.iterrows():
        transit_hours = shipment[
            "actual_transit_hours"
        ]

        event_plan = [
            (
                "SHIPMENT_CREATED",
                0.00,
                shipment[
                    "origin_warehouse_id"
                ],
            ),
            (
                "PICKED_UP",
                0.08,
                shipment[
                    "origin_warehouse_id"
                ],
            ),
            (
                "ORIGIN_SCAN",
                0.16,
                shipment[
                    "origin_warehouse_id"
                ],
            ),
            (
                "IN_TRANSIT",
                0.40,
                None,
            ),
            (
                "OUT_FOR_DELIVERY",
                0.84,
                shipment[
                    "destination_warehouse_id"
                ],
            ),
        ]

        if shipment[
            "lost_flag"
        ] == 1:
            final_event = (
                "LOST",
                1.00,
                shipment[
                    "destination_warehouse_id"
                ],
            )
        else:
            final_event = (
                "DELIVERED",
                1.00,
                shipment[
                    "destination_warehouse_id"
                ],
            )

        event_plan.append(
            final_event
        )

        if shipment[
            "no_scan_flag"
        ] == 1:
            event_plan = [
                event
                for event in event_plan
                if event[0]
                != "ORIGIN_SCAN"
            ]

        for sequence, (
            event_type,
            fraction,
            warehouse_id,
        ) in enumerate(
            event_plan,
            start=1,
        ):
            jitter_minutes = 0

            if fraction not in {
                0.00,
                1.00,
            }:
                jitter_minutes = int(
                    rng.integers(
                        -20,
                        21,
                    )
                )

            event_ts = (
                shipment[
                    "shipment_created_ts"
                ]
                + pd.Timedelta(
                    hours=(
                        transit_hours
                        * fraction
                    )
                )
                + pd.Timedelta(
                    minutes=jitter_minutes
                )
            )

            event_records.append(
                {
                    "event_id":
                        f"EVT{event_counter:010d}",
                    "shipment_id":
                        shipment[
                            "shipment_id"
                        ],
                    "event_sequence":
                        sequence,
                    "event_type":
                        event_type,
                    "event_ts":
                        event_ts,
                    "warehouse_id":
                        warehouse_id,
                    "carrier_id":
                        shipment[
                            "carrier_id"
                        ],
                    "scan_source":
                        rng.choice(
                            [
                                "Scanner",
                                "Mobile",
                                "API",
                                "Automated Sorter",
                            ],
                            p=[
                                0.48,
                                0.16,
                                0.22,
                                0.14,
                            ],
                        ),
                }
            )

            event_counter += 1

    events = pd.DataFrame(
        event_records
    )

    missing_events = (
        tracking_target
        - len(events)
    )

    if missing_events < 0:
        raise ValueError(
            "Tracking target is lower than "
            "the mandatory event count."
        )

    if missing_events > len(shipments):
        raise ValueError(
            "Tracking target is too high "
            "for the current event design."
        )

    if missing_events > 0:
        chosen_shipments = (
            shipments.sample(
                n=missing_events,
                random_state=2026,
            )
        )

        extra_records = []

        for _, shipment in (
            chosen_shipments.iterrows()
        ):
            checkpoint_ts = (
                shipment[
                    "shipment_created_ts"
                ]
                + pd.Timedelta(
                    hours=(
                        shipment[
                            "actual_transit_hours"
                        ]
                        * 0.62
                    )
                )
            )

            extra_records.append(
                {
                    "event_id":
                        f"EVT{event_counter:010d}",
                    "shipment_id":
                        shipment[
                            "shipment_id"
                        ],
                    "event_sequence":
                        99,
                    "event_type":
                        "TRANSIT_CHECKPOINT",
                    "event_ts":
                        checkpoint_ts,
                    "warehouse_id":
                        None,
                    "carrier_id":
                        shipment[
                            "carrier_id"
                        ],
                    "scan_source":
                        "Automated Sorter",
                }
            )

            event_counter += 1

        events = pd.concat(
            [
                events,
                pd.DataFrame(
                    extra_records
                ),
            ],
            ignore_index=True,
        )

    events = (
        events
        .sort_values(
            [
                "shipment_id",
                "event_ts",
            ]
        )
        .reset_index(drop=True)
    )

    events[
        "event_sequence"
    ] = (
        events
        .groupby(
            "shipment_id"
        )
        .cumcount()
        + 1
    )

    return events


def validate_logistics_data(
    orders,
    warehouses,
    carriers,
    shipments,
    tracking_events,
    tracking_target,
):
    assert shipments[
        "shipment_id"
    ].is_unique

    assert tracking_events[
        "event_id"
    ].is_unique

    assert shipments[
        "order_id"
    ].isin(
        orders["order_id"]
    ).all()

    assert shipments[
        "origin_warehouse_id"
    ].isin(
        warehouses[
            "warehouse_id"
        ]
    ).all()

    assert shipments[
        "destination_warehouse_id"
    ].isin(
        warehouses[
            "warehouse_id"
        ]
    ).all()

    assert shipments[
        "carrier_id"
    ].isin(
        carriers[
            "carrier_id"
        ]
    ).all()

    assert tracking_events[
        "shipment_id"
    ].isin(
        shipments[
            "shipment_id"
        ]
    ).all()

    assert (
        len(tracking_events)
        == tracking_target
    )

    assert (
        shipments[
            "actual_transit_hours"
        ] > 0
    ).all()

    assert (
        shipments[
            "distance_km"
        ] > 0
    ).all()

    delivered_shipments = shipments[
        shipments[
            "lost_flag"
        ] == 0
    ]

    assert delivered_shipments[
        "delivery_ts"
    ].notna().all()

    lost_shipments = shipments[
        shipments[
            "lost_flag"
        ] == 1
    ]

    assert lost_shipments[
        "delivery_ts"
    ].isna().all()

    missing_origin_scans = set(
        shipments.loc[
            shipments[
                "no_scan_flag"
            ] == 1,
            "shipment_id",
        ]
    )

    actual_origin_scans = set(
        tracking_events.loc[
            tracking_events[
                "event_type"
            ] == "ORIGIN_SCAN",
            "shipment_id",
        ]
    )

    assert missing_origin_scans.isdisjoint(
        actual_origin_scans
    )


def main():
    print("=" * 72)
    print(
        "AEGIS LOGISTICS & TRACKING GENERATOR"
    )
    print("=" * 72)

    config = load_config()

    simulation = get_simulation_config(
        config
    )

    seed = (
        config[
            "project"
        ][
            "random_seed"
        ]
        + 202
    )

    rng = np.random.default_rng(
        seed
    )

    shipment_target = simulation[
        "shipments"
    ]

    tracking_target = simulation[
        "tracking_events"
    ]

    orders, warehouses, carriers = (
        load_source_data()
    )

    print()
    print(
        f"Simulation mode: "
        f"{config['simulation']['mode']}"
    )
    print(
        f"Random seed:     {seed}"
    )
    print(
        f"Shipment target: "
        f"{shipment_target:,}"
    )
    print(
        f"Tracking target: "
        f"{tracking_target:,}"
    )
    print()

    shipments = generate_shipments(
        rng,
        orders,
        warehouses,
        carriers,
        shipment_target,
    )

    tracking_events = (
        generate_tracking_events(
            rng,
            shipments,
            tracking_target,
        )
    )

    validate_logistics_data(
        orders,
        warehouses,
        carriers,
        shipments,
        tracking_events,
        tracking_target,
    )

    output_dir = (
        PROJECT_ROOT
        / "data"
        / "raw"
    )

    shipments.to_parquet(
        output_dir
        / "shipments.parquet",
        index=False,
    )

    tracking_events.to_parquet(
        output_dir
        / "tracking_events.parquet",
        index=False,
    )

    print("=" * 72)
    print(
        "LOGISTICS DATA SUMMARY"
    )
    print("=" * 72)

    print()
    print(
        f"Shipments:         "
        f"{len(shipments):,}"
    )

    print(
        f"Tracking events:   "
        f"{len(tracking_events):,}"
    )

    print(
        f"Routes:            "
        f"{shipments[['origin_warehouse_id', 'destination_warehouse_id']].drop_duplicates().shape[0]:,}"
    )

    print(
        f"Carriers used:     "
        f"{shipments['carrier_id'].nunique():,}"
    )

    print(
        f"Warehouses used:   "
        f"{pd.unique(pd.concat([shipments['origin_warehouse_id'], shipments['destination_warehouse_id']])).size:,}"
    )

    print()

    print(
        f"Cross-border:      "
        f"{shipments['cross_border'].mean() * 100:.2f}%"
    )

    print(
        f"On-time SLA:       "
        f"{shipments['sla_met'].mean() * 100:.2f}%"
    )

    print(
        f"Delayed:           "
        f"{shipments['delayed_flag'].mean() * 100:.2f}%"
    )

    print(
        f"No-scan:           "
        f"{shipments['no_scan_flag'].mean() * 100:.2f}%"
    )

    print(
        f"Damaged:           "
        f"{shipments['damaged_flag'].mean() * 100:.2f}%"
    )

    print(
        f"Lost:              "
        f"{shipments['lost_flag'].mean() * 100:.2f}%"
    )

    print()

    print(
        f"Average distance:  "
        f"{shipments['distance_km'].mean():,.1f} km"
    )

    print(
        f"Average transit:   "
        f"{shipments['actual_transit_hours'].mean():,.2f} h"
    )

    print(
        f"Average load:      "
        f"{shipments['network_load_factor'].mean() * 100:.2f}%"
    )

    print()

    print(
        "Delay rate by load band:"
    )

    load_band = pd.cut(
        shipments[
            "network_load_factor"
        ],
        bins=[
            0,
            0.60,
            0.75,
            0.90,
            1.00,
            np.inf,
        ],
        labels=[
            "<60%",
            "60-75%",
            "75-90%",
            "90-100%",
            ">100%",
        ],
    )

    delay_by_load = (
        shipments
        .assign(
            load_band=load_band
        )
        .groupby(
            "load_band",
            observed=True,
        )[
            "delayed_flag"
        ]
        .mean()
        .mul(100)
        .round(2)
    )

    print(
        delay_by_load.to_string()
    )

    print()
    print(
        "BASELINE LOGISTICS CONTRACT: PASSED"
    )

    print()
    print(
        "Files created:"
    )

    print(
        f"  {output_dir / 'shipments.parquet'}"
    )

    print(
        f"  {output_dir / 'tracking_events.parquet'}"
    )

    print()

    print(
        "AEGIS logistics data generation "
        "completed successfully."
    )


if __name__ == "__main__":
    main()