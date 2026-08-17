import numpy as np
import pandas as pd

from src.utils.config import (
    PROJECT_ROOT,
    get_simulation_config,
    load_config,
)


SUPPORT_SOURCE_END = pd.Timestamp(
    "2025-12-20 23:59:59"
)


def load_source_data():
    raw_dir = PROJECT_ROOT / "data" / "raw"

    orders = pd.read_parquet(
        raw_dir / "orders.parquet"
    )

    shipments = pd.read_parquet(
        raw_dir / "shipments.parquet"
    )

    datetime_columns = [
        "order_ts",
    ]

    for column in datetime_columns:
        orders[column] = pd.to_datetime(
            orders[column]
        )

    shipment_datetime_columns = [
        "shipment_created_ts",
        "expected_delivery_ts",
        "delivery_ts",
    ]

    for column in shipment_datetime_columns:
        shipments[column] = pd.to_datetime(
            shipments[column]
        )

    source = shipments.merge(
        orders[
            [
                "order_id",
                "customer_id",
                "customer_segment",
                "sales_channel",
            ]
        ],
        on="order_id",
        how="left",
        validate="one_to_one",
    )

    return orders, shipments, source


def determine_case_type(
    row,
    rng,
):
    if row["lost_flag"] == 1:
        return "Lost Shipment"

    if row["damaged_flag"] == 1:
        return "Damaged Parcel"

    if row["no_scan_flag"] == 1:
        return "Tracking / No Scan"

    if row["delayed_flag"] == 1:
        return "Late Delivery"

    return rng.choice(
        [
            "Delivery Question",
            "Address Change",
            "Proof of Delivery",
            "General Inquiry",
        ],
        p=[
            0.38,
            0.17,
            0.25,
            0.20,
        ],
    )


def determine_root_cause(
    row,
    case_type,
):
    if case_type == "Lost Shipment":
        return "Chain of Custody"

    if case_type == "Damaged Parcel":
        return "Handling Damage"

    if case_type == "Tracking / No Scan":
        return "Scan Quality"

    if case_type == "Late Delivery":
        if (
            row["network_load_factor"]
            >= 0.90
        ):
            return "Network Congestion"

        return "Carrier Performance"

    if case_type == "Address Change":
        return "Customer Request"

    if case_type == "Proof of Delivery":
        return "Delivery Confirmation"

    return "General Service"


def determine_priority(
    case_type,
):
    if case_type == "Lost Shipment":
        return "Critical"

    if case_type == "Damaged Parcel":
        return "High"

    if case_type in {
        "Late Delivery",
        "Tracking / No Scan",
    }:
        return "Medium"

    return "Low"


def determine_team(
    case_type,
):
    mapping = {
        "Lost Shipment": "Claims",
        "Damaged Parcel": "Claims",
        "Tracking / No Scan": "Tracking",
        "Late Delivery": "Delivery Support",
        "Delivery Question": "Delivery Support",
        "Proof of Delivery": "Delivery Support",
        "Address Change": "Customer Care",
        "General Inquiry": "Customer Care",
    }

    return mapping[case_type]


def base_case_timestamp(
    row,
    case_type,
    rng,
):
    if case_type == "Lost Shipment":
        return (
            row["expected_delivery_ts"]
            + pd.Timedelta(
                hours=float(
                    rng.uniform(12, 36)
                )
            )
        )

    if case_type == "Damaged Parcel":
        base = (
            row["delivery_ts"]
            if pd.notna(row["delivery_ts"])
            else row["expected_delivery_ts"]
        )

        return (
            base
            + pd.Timedelta(
                hours=float(
                    rng.uniform(0.5, 12)
                )
            )
        )

    if case_type == "Tracking / No Scan":
        return (
            row["shipment_created_ts"]
            + pd.Timedelta(
                hours=(
                    min(
                        row[
                            "actual_transit_hours"
                        ]
                        * 0.45,
                        30,
                    )
                    + float(
                        rng.uniform(2, 12)
                    )
                )
            )
        )

    if case_type == "Late Delivery":
        return (
            row["expected_delivery_ts"]
            + pd.Timedelta(
                hours=float(
                    rng.uniform(1, 18)
                )
            )
        )

    return (
        row["shipment_created_ts"]
        + pd.Timedelta(
            hours=(
                row[
                    "actual_transit_hours"
                ]
                * float(
                    rng.uniform(
                        0.25,
                        0.85,
                    )
                )
            )
        )
    )


def generate_support_cases(
    rng,
    source,
    target_count,
):
    eligible = source[
        source["expected_delivery_ts"]
        <= SUPPORT_SOURCE_END
    ].copy()

    issue_weight = (
        1.0
        + eligible["delayed_flag"] * 5.0
        + eligible["no_scan_flag"] * 4.0
        + eligible["damaged_flag"] * 9.0
        + eligible["lost_flag"] * 14.0
        + (
            eligible[
                "network_load_factor"
            ]
            >= 0.90
        ).astype(int) * 2.0
    )

    unique_case_count = int(
        target_count * 0.90
    )

    unique_case_count = min(
        unique_case_count,
        len(eligible),
    )

    probabilities = (
        issue_weight
        / issue_weight.sum()
    )

    selected_positions = rng.choice(
        np.arange(len(eligible)),
        size=unique_case_count,
        replace=False,
        p=probabilities.to_numpy(),
    )

    selected = (
        eligible
        .iloc[selected_positions]
        .copy()
        .reset_index(drop=True)
    )

    repeat_count = (
        target_count
        - unique_case_count
    )

    if repeat_count > 0:
        repeat_weights = (
            1.0
            + selected["delayed_flag"] * 2.0
            + selected["no_scan_flag"] * 2.0
            + selected["damaged_flag"] * 3.0
            + selected["lost_flag"] * 4.0
        )

        repeat_probabilities = (
            repeat_weights
            / repeat_weights.sum()
        )

        repeated_positions = rng.choice(
            np.arange(len(selected)),
            size=repeat_count,
            replace=True,
            p=repeat_probabilities.to_numpy(),
        )

        repeated = (
            selected
            .iloc[repeated_positions]
            .copy()
        )

        sampled = pd.concat(
            [
                selected,
                repeated,
            ],
            ignore_index=True,
        )

    else:
        sampled = selected

    sampled[
        "contact_number"
    ] = (
        sampled
        .groupby("shipment_id")
        .cumcount()
        + 1
    )

    response_sla_minutes = {
        "Critical": 30,
        "High": 120,
        "Medium": 360,
        "Low": 720,
    }

    resolution_sla_hours = {
        "Critical": 12,
        "High": 24,
        "Medium": 48,
        "Low": 72,
    }

    records = []

    for idx, row in sampled.iterrows():
        case_type = determine_case_type(
            row,
            rng,
        )

        priority = determine_priority(
            case_type
        )

        root_cause = determine_root_cause(
            row,
            case_type,
        )

        support_team = determine_team(
            case_type
        )

        created_ts = base_case_timestamp(
            row,
            case_type,
            rng,
        )

        if row["contact_number"] > 1:
            created_ts += pd.Timedelta(
                hours=(
                    float(
                        rng.uniform(
                            12,
                            60,
                        )
                    )
                    * (
                        row[
                            "contact_number"
                        ]
                        - 1
                    )
                )
            )

        response_target = (
            response_sla_minutes[
                priority
            ]
        )

        resolution_target = (
            resolution_sla_hours[
                priority
            ]
        )

        load_multiplier = (
            1.0
            + max(
                row[
                    "network_load_factor"
                ]
                - 0.80,
                0,
            )
            * 1.8
        )

        severity_multiplier = {
            "Lost Shipment": 1.45,
            "Damaged Parcel": 1.25,
            "Tracking / No Scan": 1.10,
            "Late Delivery": 1.10,
        }.get(
            case_type,
            0.90,
        )

        first_response_minutes = max(
            2.0,
            response_target
            * float(
                rng.lognormal(
                    mean=-0.80,
                    sigma=0.65,
                )
            )
            * load_multiplier,
        )

        resolution_hours = max(
            0.25,
            resolution_target
            * float(
                rng.lognormal(
                    mean=-0.60,
                    sigma=0.70,
                )
            )
            * load_multiplier
            * severity_multiplier,
        )

        first_response_ts = (
            created_ts
            + pd.Timedelta(
                minutes=(
                    first_response_minutes
                )
            )
        )

        resolved_ts = (
            first_response_ts
            + pd.Timedelta(
                hours=resolution_hours
            )
        )

        response_sla_met = int(
            first_response_minutes
            <= response_target
        )

        resolution_sla_met = int(
            resolution_hours
            <= resolution_target
        )

        overall_sla_met = int(
            response_sla_met == 1
            and resolution_sla_met == 1
        )

        severe_issue = int(
            case_type
            in {
                "Lost Shipment",
                "Damaged Parcel",
            }
        )

        escalation_probability = (
            0.04
            + severe_issue * 0.16
            + (
                1 - overall_sla_met
            ) * 0.22
            + (
                row["contact_number"] > 1
            ) * 0.12
        )

        escalated_flag = int(
            rng.random()
            < min(
                escalation_probability,
                0.75,
            )
        )

        reopened_probability = (
            0.035
            + severe_issue * 0.05
            + (
                1 - overall_sla_met
            ) * 0.07
            + (
                row["contact_number"] > 1
            ) * 0.18
        )

        reopened_flag = int(
            rng.random()
            < min(
                reopened_probability,
                0.45,
            )
        )

        csat = 4.65

        if severe_issue:
            csat -= 0.55

        if overall_sla_met == 0:
            csat -= 0.85

        if escalated_flag:
            csat -= 0.35

        if row["contact_number"] > 1:
            csat -= 0.35

        csat += float(
            rng.normal(
                0,
                0.50,
            )
        )

        csat_score = int(
            np.clip(
                round(csat),
                1,
                5,
            )
        )

        channel = rng.choice(
            [
                "Chat",
                "Email",
                "Phone",
                "Web Form",
            ],
            p=[
                0.34,
                0.30,
                0.25,
                0.11,
            ],
        )

        records.append(
            {
                "case_id":
                    f"CASE{idx + 1:08d}",
                "customer_id":
                    row["customer_id"],
                "order_id":
                    row["order_id"],
                "shipment_id":
                    row["shipment_id"],
                "customer_segment":
                    row["customer_segment"],
                "destination_country":
                    row[
                        "destination_country"
                    ],
                "carrier_id":
                    row["carrier_id"],
                "origin_warehouse_id":
                    row[
                        "origin_warehouse_id"
                    ],
                "contact_number":
                    int(
                        row[
                            "contact_number"
                        ]
                    ),
                "case_type":
                    case_type,
                "root_cause_category":
                    root_cause,
                "priority":
                    priority,
                "support_team":
                    support_team,
                "channel":
                    channel,
                "created_ts":
                    created_ts,
                "first_response_ts":
                    first_response_ts,
                "resolved_ts":
                    resolved_ts,
                "first_response_minutes":
                    round(
                        first_response_minutes,
                        2,
                    ),
                "resolution_hours":
                    round(
                        resolution_hours,
                        2,
                    ),
                "response_sla_minutes":
                    response_target,
                "resolution_sla_hours":
                    resolution_target,
                "response_sla_met":
                    response_sla_met,
                "resolution_sla_met":
                    resolution_sla_met,
                "support_sla_met":
                    overall_sla_met,
                "escalated_flag":
                    escalated_flag,
                "reopened_flag":
                    reopened_flag,
                "csat_score":
                    csat_score,
                "network_load_factor":
                    row[
                        "network_load_factor"
                    ],
                "shipment_delayed_flag":
                    row["delayed_flag"],
                "shipment_no_scan_flag":
                    row["no_scan_flag"],
                "shipment_damaged_flag":
                    row["damaged_flag"],
                "shipment_lost_flag":
                    row["lost_flag"],
            }
        )

    return pd.DataFrame(records)


def validate_support_data(
    orders,
    shipments,
    support_cases,
    target_count,
):
    assert (
        len(support_cases)
        == target_count
    )

    assert support_cases[
        "case_id"
    ].is_unique

    assert support_cases[
        "order_id"
    ].isin(
        orders["order_id"]
    ).all()

    assert support_cases[
        "shipment_id"
    ].isin(
        shipments[
            "shipment_id"
        ]
    ).all()

    assert (
        support_cases[
            "first_response_ts"
        ]
        >= support_cases[
            "created_ts"
        ]
    ).all()

    assert (
        support_cases[
            "resolved_ts"
        ]
        >= support_cases[
            "first_response_ts"
        ]
    ).all()

    assert (
        support_cases[
            "first_response_minutes"
        ]
        > 0
    ).all()

    assert (
        support_cases[
            "resolution_hours"
        ]
        > 0
    ).all()

    assert support_cases[
        "csat_score"
    ].between(
        1,
        5,
    ).all()


def main():
    print("=" * 72)
    print(
        "AEGIS CUSTOMER SUPPORT GENERATOR"
    )
    print("=" * 72)

    config = load_config()

    simulation = get_simulation_config(
        config
    )

    target_count = simulation[
        "support_cases"
    ]

    seed = (
        config[
            "project"
        ][
            "random_seed"
        ]
        + 303
    )

    rng = np.random.default_rng(
        seed
    )

    orders, shipments, source = (
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
        f"Cases target:    "
        f"{target_count:,}"
    )
    print()

    support_cases = (
        generate_support_cases(
            rng,
            source,
            target_count,
        )
    )

    validate_support_data(
        orders,
        shipments,
        support_cases,
        target_count,
    )

    output_dir = (
        PROJECT_ROOT
        / "data"
        / "raw"
    )

    support_cases.to_parquet(
        output_dir
        / "support_cases.parquet",
        index=False,
    )

    print("=" * 72)
    print(
        "CUSTOMER SUPPORT SUMMARY"
    )
    print("=" * 72)

    print()

    print(
        f"Cases:                  "
        f"{len(support_cases):,}"
    )

    print(
        f"Unique customers:       "
        f"{support_cases['customer_id'].nunique():,}"
    )

    print(
        f"Unique shipments:       "
        f"{support_cases['shipment_id'].nunique():,}"
    )

    print(
        f"Repeat contacts:        "
        f"{(support_cases['contact_number'] > 1).mean() * 100:.2f}%"
    )

    print()

    print(
        f"Support SLA compliance: "
        f"{support_cases['support_sla_met'].mean() * 100:.2f}%"
    )

    print(
        f"Escalation rate:        "
        f"{support_cases['escalated_flag'].mean() * 100:.2f}%"
    )

    print(
        f"Reopen rate:            "
        f"{support_cases['reopened_flag'].mean() * 100:.2f}%"
    )

    print(
        f"Avg first response:     "
        f"{support_cases['first_response_minutes'].mean():.1f} min"
    )

    print(
        f"Avg resolution time:    "
        f"{support_cases['resolution_hours'].mean():.1f} h"
    )

    print(
        f"Average CSAT:           "
        f"{support_cases['csat_score'].mean():.2f} / 5"
    )

    print()
    print(
        "Cases by type:"
    )

    print(
        support_cases[
            "case_type"
        ]
        .value_counts()
        .to_string()
    )

    print()
    print(
        "Root causes:"
    )

    print(
        support_cases[
            "root_cause_category"
        ]
        .value_counts()
        .to_string()
    )

    print()
    print(
        "BASELINE SUPPORT CONTRACT: PASSED"
    )

    print()
    print(
        "File created:"
    )

    print(
        f"  {output_dir / 'support_cases.parquet'}"
    )

    print()
    print(
        "AEGIS customer support generation "
        "completed successfully."
    )


if __name__ == "__main__":
    main()
