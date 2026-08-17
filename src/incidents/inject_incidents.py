import json
import shutil

import numpy as np
import pandas as pd

from src.utils.config import PROJECT_ROOT, load_config


BUSINESS_START = pd.Timestamp("2025-11-17 00:00:00")
BUSINESS_END = pd.Timestamp("2025-11-30 23:59:59")

DATA_START = pd.Timestamp("2025-09-08 00:00:00")
DATA_END = pd.Timestamp("2025-09-14 23:59:59")


def load_data():
    raw = PROJECT_ROOT / "data" / "raw"

    orders = pd.read_parquet(
        raw / "orders.parquet"
    )

    shipments = pd.read_parquet(
        raw / "shipments.parquet"
    )

    tracking = pd.read_parquet(
        raw / "tracking_events.parquet"
    )

    support = pd.read_parquet(
        raw / "support_cases.parquet"
    )

    app = pd.read_parquet(
        raw / "app_events.parquet"
    )

    for col in [
        "shipment_created_ts",
        "expected_delivery_ts",
        "delivery_ts",
    ]:
        shipments[col] = pd.to_datetime(
            shipments[col]
        )

    tracking["event_ts"] = pd.to_datetime(
        tracking["event_ts"]
    )

    for col in [
        "created_ts",
        "first_response_ts",
        "resolved_ts",
    ]:
        support[col] = pd.to_datetime(
            support[col]
        )

    app["event_ts"] = pd.to_datetime(
        app["event_ts"]
    )

    return (
        raw,
        orders,
        shipments,
        tracking,
        support,
        app,
    )


def inject_business_incident(
    rng,
    shipments,
    tracking,
    support,
):
    shipments = shipments.copy()
    tracking = tracking.copy()
    support = support.copy()

    mask = (
        shipments[
            "shipment_created_ts"
        ].between(
            BUSINESS_START,
            BUSINESS_END,
        )
        & (
            shipments[
                "origin_city"
            ].eq("Warsaw")
            | shipments[
                "destination_city"
            ].eq("Warsaw")
        )
    )

    idx = shipments.index[mask]

    if len(idx) == 0:
        raise ValueError(
            "No Warsaw shipments matched "
            "the business incident window."
        )

    delay = pd.Series(
        rng.uniform(
            10,
            28,
            len(idx),
        ),
        index=idx,
    )

    load = pd.Series(
        rng.uniform(
            1.03,
            1.16,
            len(idx),
        ),
        index=idx,
    )

    shipments.loc[
        idx,
        "network_load_factor",
    ] = np.round(
        np.maximum(
            shipments.loc[
                idx,
                "network_load_factor",
            ].astype(float),
            load,
        ),
        4,
    )

    non_lost_idx = idx[
        shipments.loc[
            idx,
            "lost_flag",
        ]
        .eq(0)
        .to_numpy()
    ]

    non_lost_delay = delay.loc[
        non_lost_idx
    ]

    shipments.loc[
        non_lost_idx,
        "actual_transit_hours",
    ] = np.round(
        shipments.loc[
            non_lost_idx,
            "actual_transit_hours",
        ].astype(float)
        + non_lost_delay,
        2,
    )

    shipments.loc[
        non_lost_idx,
        "delivery_ts",
    ] = (
        shipments.loc[
            non_lost_idx,
            "delivery_ts",
        ]
        + pd.to_timedelta(
            non_lost_delay,
            unit="h",
        )
    )

    shipments.loc[
        non_lost_idx,
        "delay_hours",
    ] = np.round(
        np.maximum(
            shipments.loc[
                non_lost_idx,
                "actual_transit_hours",
            ]
            - shipments.loc[
                non_lost_idx,
                "sla_hours",
            ],
            0,
        ),
        2,
    )

    shipments.loc[
        non_lost_idx,
        "delayed_flag",
    ] = 1

    shipments.loc[
        non_lost_idx,
        "sla_met",
    ] = 0

    delay_by_shipment = dict(
        zip(
            shipments.loc[
                idx,
                "shipment_id",
            ],
            delay.to_numpy(),
        )
    )

    tracking["_delay"] = tracking[
        "shipment_id"
    ].map(
        delay_by_shipment
    )

    factor = tracking[
        "event_type"
    ].map(
        {
            "SHIPMENT_CREATED": 0.00,
            "PICKED_UP": 0.10,
            "ORIGIN_SCAN": 0.15,
            "IN_TRANSIT": 0.55,
            "TRANSIT_CHECKPOINT": 0.70,
            "OUT_FOR_DELIVERY": 0.90,
            "DELIVERED": 1.00,
            "LOST": 1.00,
        }
    ).fillna(
        0.50
    )

    tracking_mask = tracking[
        "_delay"
    ].notna()

    tracking.loc[
        tracking_mask,
        "event_ts",
    ] = (
        tracking.loc[
            tracking_mask,
            "event_ts",
        ]
        + pd.to_timedelta(
            tracking.loc[
                tracking_mask,
                "_delay",
            ]
            * factor.loc[
                tracking_mask
            ],
            unit="h",
        )
    )

    tracking = tracking.drop(
        columns="_delay"
    )

    affected_ids = set(
        shipments.loc[
            idx,
            "shipment_id",
        ]
    )

    support_mask = support[
        "shipment_id"
    ].isin(
        affected_ids
    )

    support_count = int(
        support_mask.sum()
    )

    if support_count:
        response_multiplier = pd.Series(
            rng.uniform(
                1.35,
                1.85,
                support_count,
            ),
            index=support.index[
                support_mask
            ],
        )

        resolution_multiplier = pd.Series(
            rng.uniform(
                1.40,
                2.00,
                support_count,
            ),
            index=support.index[
                support_mask
            ],
        )

        support.loc[
            support_mask,
            "first_response_minutes",
        ] = np.round(
            support.loc[
                support_mask,
                "first_response_minutes",
            ]
            * response_multiplier,
            2,
        )

        support.loc[
            support_mask,
            "resolution_hours",
        ] = np.round(
            support.loc[
                support_mask,
                "resolution_hours",
            ]
            * resolution_multiplier,
            2,
        )

        support.loc[
            support_mask,
            "first_response_ts",
        ] = (
            support.loc[
                support_mask,
                "created_ts",
            ]
            + pd.to_timedelta(
                support.loc[
                    support_mask,
                    "first_response_minutes",
                ],
                unit="m",
            )
        )

        support.loc[
            support_mask,
            "resolved_ts",
        ] = (
            support.loc[
                support_mask,
                "first_response_ts",
            ]
            + pd.to_timedelta(
                support.loc[
                    support_mask,
                    "resolution_hours",
                ],
                unit="h",
            )
        )

        support.loc[
            support_mask,
            "response_sla_met",
        ] = (
            support.loc[
                support_mask,
                "first_response_minutes",
            ]
            <= support.loc[
                support_mask,
                "response_sla_minutes",
            ]
        ).astype(int)

        support.loc[
            support_mask,
            "resolution_sla_met",
        ] = (
            support.loc[
                support_mask,
                "resolution_hours",
            ]
            <= support.loc[
                support_mask,
                "resolution_sla_hours",
            ]
        ).astype(int)

        support.loc[
            support_mask,
            "support_sla_met",
        ] = (
            support.loc[
                support_mask,
                "response_sla_met",
            ].eq(1)
            & support.loc[
                support_mask,
                "resolution_sla_met",
            ].eq(1)
        ).astype(int)

        support.loc[
            support_mask,
            "csat_score",
        ] = np.clip(
            support.loc[
                support_mask,
                "csat_score",
            ]
            - 1,
            1,
            5,
        )

    return (
        shipments,
        tracking,
        support,
        {
            "affected_shipments":
                int(len(idx)),
            "affected_support_cases":
                support_count,
            "avg_injected_delay_hours":
                round(
                    float(
                        delay.mean()
                    ),
                    2,
                ),
        },
    )


def inject_data_incident(
    rng,
    app,
):
    app = app.copy()

    purchase_mask = (
        app[
            "event_ts"
        ].between(
            DATA_START,
            DATA_END,
        )
        & app[
            "event_type"
        ].eq(
            "purchase"
        )
    )

    purchase_idx = app.index[
        purchase_mask
    ].to_numpy()

    if len(purchase_idx) == 0:
        raise ValueError(
            "No purchase events matched "
            "the data incident window."
        )

    drop_count = max(
        1,
        int(
            len(
                purchase_idx
            )
            * 0.42
        ),
    )

    drop_idx = rng.choice(
        purchase_idx,
        size=drop_count,
        replace=False,
    )

    remaining_idx = np.setdiff1d(
        purchase_idx,
        drop_idx,
    )

    null_count = int(
        len(
            remaining_idx
        )
        * 0.45
    )

    if null_count:
        null_idx = rng.choice(
            remaining_idx,
            size=null_count,
            replace=False,
        )
    else:
        null_idx = np.array(
            [],
            dtype=int,
        )

    app.loc[
        null_idx,
        "event_value_eur",
    ] = np.nan

    app = (
        app
        .drop(
            index=drop_idx
        )
        .reset_index(
            drop=True
        )
    )

    return (
        app,
        {
            "baseline_purchase_events":
                int(
                    len(
                        purchase_idx
                    )
                ),
            "purchase_events_dropped":
                int(
                    drop_count
                ),
            "purchase_values_nullified":
                int(
                    len(
                        null_idx
                    )
                ),
            "drop_rate_pct":
                round(
                    drop_count
                    / len(
                        purchase_idx
                    )
                    * 100,
                    2,
                ),
        },
    )


def write_bronze(
    raw,
    shipments,
    tracking,
    support,
    app,
):
    bronze = (
        PROJECT_ROOT
        / "data"
        / "bronze"
    )

    bronze.mkdir(
        parents=True,
        exist_ok=True,
    )

    changed = {
        "shipments.parquet",
        "tracking_events.parquet",
        "support_cases.parquet",
        "app_events.parquet",
    }

    for source in raw.glob(
        "*.parquet"
    ):
        if source.name not in changed:
            shutil.copy2(
                source,
                bronze
                / source.name,
            )

    shipments.to_parquet(
        bronze
        / "shipments.parquet",
        index=False,
    )

    tracking.to_parquet(
        bronze
        / "tracking_events.parquet",
        index=False,
    )

    support.to_parquet(
        bronze
        / "support_cases.parquet",
        index=False,
    )

    app.to_parquet(
        bronze
        / "app_events.parquet",
        index=False,
    )

    return bronze


def save_ground_truth(
    business,
    data,
):
    artifacts = (
        PROJECT_ROOT
        / "artifacts"
    )

    artifacts.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = (
        artifacts
        / "incident_ground_truth.json"
    )

    payload = {
        "warning":
            "Evaluation only. "
            "Detection components "
            "must not read this file.",

        "incidents": [
            {
                "incident_id":
                    "INC-BIZ-001",

                "incident_type":
                    "BUSINESS_INCIDENT",

                "domain":
                    "logistics",

                "start_ts":
                    str(
                        BUSINESS_START
                    ),

                "end_ts":
                    str(
                        BUSINESS_END
                    ),

                "scope":
                    "Shipments involving "
                    "Warsaw hub",

                **business,
            },

            {
                "incident_id":
                    "INC-DATA-001",

                "incident_type":
                    "DATA_INCIDENT",

                "domain":
                    "app_events",

                "start_ts":
                    str(
                        DATA_START
                    ),

                "end_ts":
                    str(
                        DATA_END
                    ),

                "scope":
                    "Purchase tracking",

                **data,
            },
        ],
    }

    path.write_text(
        json.dumps(
            payload,
            indent=2,
        ),
        encoding="utf-8",
    )

    return path


def main():
    print("=" * 72)
    print(
        "AEGIS INCIDENT INJECTION ENGINE"
    )
    print("=" * 72)

    config = load_config()

    seed = (
        config[
            "project"
        ][
            "random_seed"
        ]
        + 505
    )

    rng = np.random.default_rng(
        seed
    )

    (
        raw,
        orders,
        base_shipments,
        base_tracking,
        base_support,
        base_app,
    ) = load_data()

    (
        shipments,
        tracking,
        support,
        business,
    ) = inject_business_incident(
        rng,
        base_shipments,
        base_tracking,
        base_support,
    )

    (
        app,
        data,
    ) = inject_data_incident(
        rng,
        base_app,
    )

    bronze = write_bronze(
        raw,
        shipments,
        tracking,
        support,
        app,
    )

    ground_truth = save_ground_truth(
        business,
        data,
    )

    assert (
        len(shipments)
        == len(
            base_shipments
        )
    )

    assert (
        len(tracking)
        == len(
            base_tracking
        )
    )

    assert shipments[
        "shipment_id"
    ].is_unique

    assert tracking[
        "event_id"
    ].is_unique

    assert support[
        "case_id"
    ].is_unique

    assert app[
        "event_id"
    ].is_unique

    assert tracking[
        "shipment_id"
    ].isin(
        shipments[
            "shipment_id"
        ]
    ).all()

    assert support[
        "shipment_id"
    ].isin(
        shipments[
            "shipment_id"
        ]
    ).all()

    assert (
        len(app)
        < len(
            base_app
        )
    )

    baseline_business_mask = (
        base_shipments[
            "shipment_created_ts"
        ].between(
            BUSINESS_START,
            BUSINESS_END,
        )
        & (
            base_shipments[
                "origin_city"
            ].eq(
                "Warsaw"
            )
            | base_shipments[
                "destination_city"
            ].eq(
                "Warsaw"
            )
        )
    )

    incident_business_mask = (
        shipments[
            "shipment_created_ts"
        ].between(
            BUSINESS_START,
            BUSINESS_END,
        )
        & (
            shipments[
                "origin_city"
            ].eq(
                "Warsaw"
            )
            | shipments[
                "destination_city"
            ].eq(
                "Warsaw"
            )
        )
    )

    baseline_purchase_mask = (
        base_app[
            "event_ts"
        ].between(
            DATA_START,
            DATA_END,
        )
        & base_app[
            "event_type"
        ].eq(
            "purchase"
        )
    )

    incident_purchase_mask = (
        app[
            "event_ts"
        ].between(
            DATA_START,
            DATA_END,
        )
        & app[
            "event_type"
        ].eq(
            "purchase"
        )
    )

    print()
    print(
        "BUSINESS INCIDENT - WARSAW"
    )

    print(
        f"Window:              "
        f"{BUSINESS_START:%Y-%m-%d} "
        f"to "
        f"{BUSINESS_END:%Y-%m-%d}"
    )

    print(
        f"Affected shipments:  "
        f"{business['affected_shipments']:,}"
    )

    print(
        f"Baseline delay rate: "
        f"{base_shipments.loc[baseline_business_mask, 'delayed_flag'].mean() * 100:.2f}%"
    )

    print(
        f"Incident delay rate: "
        f"{shipments.loc[incident_business_mask, 'delayed_flag'].mean() * 100:.2f}%"
    )

    print(
        f"Baseline avg load:   "
        f"{base_shipments.loc[baseline_business_mask, 'network_load_factor'].mean() * 100:.2f}%"
    )

    print(
        f"Incident avg load:   "
        f"{shipments.loc[incident_business_mask, 'network_load_factor'].mean() * 100:.2f}%"
    )

    print(
        f"Support cases hit:   "
        f"{business['affected_support_cases']:,}"
    )

    print(
        f"Avg injected delay:  "
        f"{business['avg_injected_delay_hours']:.2f} h"
    )

    print()
    print(
        "DATA INCIDENT - PURCHASE TRACKING"
    )

    print(
        f"Window:              "
        f"{DATA_START:%Y-%m-%d} "
        f"to "
        f"{DATA_END:%Y-%m-%d}"
    )

    print(
        f"Baseline purchases:  "
        f"{int(baseline_purchase_mask.sum()):,}"
    )

    print(
        f"Observed purchases:  "
        f"{int(incident_purchase_mask.sum()):,}"
    )

    print(
        f"Events dropped:      "
        f"{data['purchase_events_dropped']:,}"
    )

    print(
        f"Drop rate:           "
        f"{data['drop_rate_pct']:.2f}%"
    )

    print(
        f"Values nullified:    "
        f"{data['purchase_values_nullified']:,}"
    )

    print()
    print(
        "INCIDENT LAYER CONTRACT: PASSED"
    )

    print(
        f"Bronze layer: "
        f"{bronze}"
    )

    print(
        f"Ground truth: "
        f"{ground_truth}"
    )

    print(
        "Detection components must NOT "
        "read the ground-truth file."
    )


if __name__ == "__main__":
    main()
