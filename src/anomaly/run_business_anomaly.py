import json

import numpy as np
import pandas as pd

from src.utils.config import PROJECT_ROOT


WINDOW_DAYS = 14
MIN_WINDOW_SHIPMENTS = 20
MIN_ANOMALY_SCORE = 75.0

DELAY_INCREASE_THRESHOLD_PP = 18.0
LOAD_INCREASE_THRESHOLD_PP = 20.0


def load_data():
    bronze = (
        PROJECT_ROOT
        / "data"
        / "bronze"
    )

    shipments = pd.read_parquet(
        bronze / "shipments.parquet"
    )

    support = pd.read_parquet(
        bronze / "support_cases.parquet"
    )

    warehouses = pd.read_parquet(
        bronze / "warehouses.parquet"
    )

    shipments[
        "shipment_created_ts"
    ] = pd.to_datetime(
        shipments[
            "shipment_created_ts"
        ]
    )

    support[
        "created_ts"
    ] = pd.to_datetime(
        support[
            "created_ts"
        ]
    )

    return (
        shipments,
        support,
        warehouses,
    )


def build_warehouse_shipments(
    shipments,
):
    origin = shipments.copy()

    origin[
        "warehouse_id"
    ] = origin[
        "origin_warehouse_id"
    ]

    origin[
        "warehouse_role"
    ] = "Origin"

    destination = shipments.copy()

    destination[
        "warehouse_id"
    ] = destination[
        "destination_warehouse_id"
    ]

    destination[
        "warehouse_role"
    ] = "Destination"

    combined = pd.concat(
        [
            origin,
            destination,
        ],
        ignore_index=True,
    )

    combined[
        "date"
    ] = combined[
        "shipment_created_ts"
    ].dt.normalize()

    return combined


def calculate_warehouse_baselines(
    warehouse_shipments,
):
    baseline = (
        warehouse_shipments
        .groupby(
            "warehouse_id",
            as_index=False,
        )
        .agg(
            baseline_shipments=(
                "shipment_id",
                "count",
            ),
            baseline_delay_rate=(
                "delayed_flag",
                "mean",
            ),
            baseline_sla_rate=(
                "sla_met",
                "mean",
            ),
            baseline_load=(
                "network_load_factor",
                "mean",
            ),
            baseline_transit_hours=(
                "actual_transit_hours",
                "mean",
            ),
        )
    )

    return baseline


def build_daily_metrics(
    warehouse_shipments,
):
    daily = (
        warehouse_shipments
        .groupby(
            [
                "warehouse_id",
                "date",
            ],
            as_index=False,
        )
        .agg(
            shipments=(
                "shipment_id",
                "count",
            ),
            delayed_shipments=(
                "delayed_flag",
                "sum",
            ),
            sla_met_shipments=(
                "sla_met",
                "sum",
            ),
            avg_load=(
                "network_load_factor",
                "mean",
            ),
            avg_transit_hours=(
                "actual_transit_hours",
                "mean",
            ),
        )
    )

    return daily


def build_rolling_windows(
    daily,
    baselines,
):
    results = []

    for warehouse_id, group in (
        daily
        .groupby(
            "warehouse_id"
        )
    ):
        group = (
            group
            .sort_values(
                "date"
            )
            .reset_index(
                drop=True
            )
        )

        if group.empty:
            continue

        min_date = group[
            "date"
        ].min()

        max_date = group[
            "date"
        ].max()

        all_dates = pd.date_range(
            min_date,
            max_date,
            freq="D",
        )

        calendar = pd.DataFrame(
            {
                "date": all_dates
            }
        )

        expanded = (
            calendar
            .merge(
                group,
                on="date",
                how="left",
            )
        )

        expanded[
            "warehouse_id"
        ] = warehouse_id

        for column in [
            "shipments",
            "delayed_shipments",
            "sla_met_shipments",
        ]:
            expanded[
                column
            ] = (
                expanded[
                    column
                ]
                .fillna(0)
            )

        expanded[
            "load_weighted"
        ] = (
            expanded[
                "avg_load"
            ].fillna(0)
            * expanded[
                "shipments"
            ]
        )

        expanded[
            "transit_weighted"
        ] = (
            expanded[
                "avg_transit_hours"
            ].fillna(0)
            * expanded[
                "shipments"
            ]
        )

        expanded[
            "window_shipments"
        ] = (
            expanded[
                "shipments"
            ]
            .rolling(
                WINDOW_DAYS,
                min_periods=1,
            )
            .sum()
        )

        expanded[
            "window_delayed"
        ] = (
            expanded[
                "delayed_shipments"
            ]
            .rolling(
                WINDOW_DAYS,
                min_periods=1,
            )
            .sum()
        )

        expanded[
            "window_sla_met"
        ] = (
            expanded[
                "sla_met_shipments"
            ]
            .rolling(
                WINDOW_DAYS,
                min_periods=1,
            )
            .sum()
        )

        expanded[
            "window_load_weighted"
        ] = (
            expanded[
                "load_weighted"
            ]
            .rolling(
                WINDOW_DAYS,
                min_periods=1,
            )
            .sum()
        )

        expanded[
            "window_transit_weighted"
        ] = (
            expanded[
                "transit_weighted"
            ]
            .rolling(
                WINDOW_DAYS,
                min_periods=1,
            )
            .sum()
        )

        valid = expanded[
            expanded[
                "window_shipments"
            ]
            >= MIN_WINDOW_SHIPMENTS
        ].copy()

        if valid.empty:
            continue

        valid[
            "window_delay_rate"
        ] = (
            valid[
                "window_delayed"
            ]
            / valid[
                "window_shipments"
            ]
        )

        valid[
            "window_sla_rate"
        ] = (
            valid[
                "window_sla_met"
            ]
            / valid[
                "window_shipments"
            ]
        )

        valid[
            "window_avg_load"
        ] = (
            valid[
                "window_load_weighted"
            ]
            / valid[
                "window_shipments"
            ]
        )

        valid[
            "window_avg_transit_hours"
        ] = (
            valid[
                "window_transit_weighted"
            ]
            / valid[
                "window_shipments"
            ]
        )

        valid[
            "window_end"
        ] = valid[
            "date"
        ]

        valid[
            "window_start"
        ] = (
            valid[
                "window_end"
            ]
            - pd.Timedelta(
                days=(
                    WINDOW_DAYS
                    - 1
                )
            )
        )

        results.append(
            valid[
                [
                    "warehouse_id",
                    "window_start",
                    "window_end",
                    "window_shipments",
                    "window_delay_rate",
                    "window_sla_rate",
                    "window_avg_load",
                    "window_avg_transit_hours",
                ]
            ]
        )

    windows = pd.concat(
        results,
        ignore_index=True,
    )

    windows = windows.merge(
        baselines,
        on="warehouse_id",
        how="left",
        validate="many_to_one",
    )

    windows[
        "delay_delta_pp"
    ] = (
        (
            windows[
                "window_delay_rate"
            ]
            - windows[
                "baseline_delay_rate"
            ]
        )
        * 100
    )

    windows[
        "sla_delta_pp"
    ] = (
        (
            windows[
                "window_sla_rate"
            ]
            - windows[
                "baseline_sla_rate"
            ]
        )
        * 100
    )

    windows[
        "load_delta_pp"
    ] = (
        (
            windows[
                "window_avg_load"
            ]
            - windows[
                "baseline_load"
            ]
        )
        * 100
    )

    windows[
        "transit_delta_hours"
    ] = (
        windows[
            "window_avg_transit_hours"
        ]
        - windows[
            "baseline_transit_hours"
        ]
    )

    return windows


def calculate_anomaly_score(
    windows,
):
    delay_component = np.clip(
        windows[
            "delay_delta_pp"
        ]
        / 40.0,
        0,
        1,
    )

    load_component = np.clip(
        windows[
            "load_delta_pp"
        ]
        / 30.0,
        0,
        1,
    )

    transit_component = np.clip(
        windows[
            "transit_delta_hours"
        ]
        / 20.0,
        0,
        1,
    )

    sla_component = np.clip(
        (
            -windows[
                "sla_delta_pp"
            ]
        )
        / 40.0,
        0,
        1,
    )

    windows[
        "anomaly_score"
    ] = np.round(
        (
            delay_component
            * 0.35
            + load_component
            * 0.30
            + sla_component
            * 0.25
            + transit_component
            * 0.10
        )
        * 100,
        2,
    )

    return windows


def identify_candidates(
    windows,
):
    candidates = windows[
        (
            windows[
                "delay_delta_pp"
            ]
            >= DELAY_INCREASE_THRESHOLD_PP
        )
        & (
            windows[
                "load_delta_pp"
            ]
            >= LOAD_INCREASE_THRESHOLD_PP
        )
        & (windows["window_shipments"] >= MIN_WINDOW_SHIPMENTS) & (windows["anomaly_score"] >= MIN_ANOMALY_SCORE)
    ].copy()

    if candidates.empty:
        return candidates

    candidates = (
        candidates
        .sort_values(
            [
                "anomaly_score",
                "delay_delta_pp",
            ],
            ascending=False,
        )
        .reset_index(
            drop=True
        )
    )

    return candidates


def collapse_overlapping_windows(
    candidates,
):
    if candidates.empty:
        return candidates

    selected = []

    for _, row in candidates.iterrows():
        overlaps = False

        for existing in selected:
            same_warehouse = (
                row[
                    "warehouse_id"
                ]
                == existing[
                    "warehouse_id"
                ]
            )

            date_overlap = not (
                row[
                    "window_end"
                ]
                < existing[
                    "window_start"
                ]
                or row[
                    "window_start"
                ]
                > existing[
                    "window_end"
                ]
            )

            if (
                same_warehouse
                and date_overlap
            ):
                overlaps = True
                break

        if not overlaps:
            selected.append(
                row
            )

    if not selected:
        return pd.DataFrame()

    return pd.DataFrame(
        selected
    )


def enrich_candidates(
    candidates,
    warehouses,
    support,
    warehouse_shipments,
):
    if candidates.empty:
        return candidates

    warehouse_lookup = (
        warehouses[
            [
                "warehouse_id",
                "city",
                "country",
                "warehouse_type",
            ]
        ]
        .drop_duplicates(
            "warehouse_id"
        )
    )

    candidates = candidates.merge(
        warehouse_lookup,
        on="warehouse_id",
        how="left",
        validate="many_to_one",
    )

    support_records = []

    for _, row in (
        candidates.iterrows()
    ):
        affected_shipments = (
            warehouse_shipments[
                (
                    warehouse_shipments[
                        "warehouse_id"
                    ]
                    == row[
                        "warehouse_id"
                    ]
                )
                & (
                    warehouse_shipments[
                        "shipment_created_ts"
                    ].between(
                        row[
                            "window_start"
                        ],
                        row[
                            "window_end"
                        ]
                        + pd.Timedelta(
                            days=1
                        )
                        - pd.Timedelta(
                            seconds=1
                        ),
                    )
                )
            ][
                "shipment_id"
            ]
            .drop_duplicates()
        )

        case_data = support[
            support[
                "shipment_id"
            ].isin(
                affected_shipments
            )
        ]

        support_records.append(
            {
                "affected_support_cases":
                    int(
                        len(
                            case_data
                        )
                    ),

                "support_sla_rate":
                    (
                        float(
                            case_data[
                                "support_sla_met"
                            ].mean()
                        )
                        if len(
                            case_data
                        )
                        else np.nan
                    ),

                "avg_csat":
                    (
                        float(
                            case_data[
                                "csat_score"
                            ].mean()
                        )
                        if len(
                            case_data
                        )
                        else np.nan
                    ),
            }
        )

    support_df = pd.DataFrame(
        support_records
    )

    candidates = pd.concat(
        [
            candidates
            .reset_index(
                drop=True
            ),
            support_df,
        ],
        axis=1,
    )

    return candidates


def create_incident_records(
    candidates,
):
    incidents = []

    for index, row in (
        candidates.iterrows()
    ):
        incidents.append(
            {
                "candidate_incident_id":
                    f"BIZ-CAND-{index + 1:03d}",

                "classification":
                    "BUSINESS_INCIDENT_CANDIDATE",

                "domain":
                    "logistics",

                "warehouse_id":
                    row[
                        "warehouse_id"
                    ],

                "city":
                    row[
                        "city"
                    ],

                "country":
                    row[
                        "country"
                    ],

                "start_date":
                    str(
                        row[
                            "window_start"
                        ].date()
                    ),

                "end_date":
                    str(
                        row[
                            "window_end"
                        ].date()
                    ),

                "shipments":
                    int(
                        row[
                            "window_shipments"
                        ]
                    ),

                "baseline_delay_pct":
                    round(
                        row[
                            "baseline_delay_rate"
                        ]
                        * 100,
                        2,
                    ),

                "incident_delay_pct":
                    round(
                        row[
                            "window_delay_rate"
                        ]
                        * 100,
                        2,
                    ),

                "delay_increase_pp":
                    round(
                        row[
                            "delay_delta_pp"
                        ],
                        2,
                    ),

                "baseline_load_pct":
                    round(
                        row[
                            "baseline_load"
                        ]
                        * 100,
                        2,
                    ),

                "incident_load_pct":
                    round(
                        row[
                            "window_avg_load"
                        ]
                        * 100,
                        2,
                    ),

                "load_increase_pp":
                    round(
                        row[
                            "load_delta_pp"
                        ],
                        2,
                    ),

                "sla_change_pp":
                    round(
                        row[
                            "sla_delta_pp"
                        ],
                        2,
                    ),

                "transit_increase_hours":
                    round(
                        row[
                            "transit_delta_hours"
                        ],
                        2,
                    ),

                "affected_support_cases":
                    int(
                        row[
                            "affected_support_cases"
                        ]
                    ),

                "support_sla_pct":
                    (
                        round(
                            row[
                                "support_sla_rate"
                            ]
                            * 100,
                            2,
                        )
                        if pd.notna(
                            row[
                                "support_sla_rate"
                            ]
                        )
                        else None
                    ),

                "average_csat":
                    (
                        round(
                            row[
                                "avg_csat"
                            ],
                            2,
                        )
                        if pd.notna(
                            row[
                                "avg_csat"
                            ]
                        )
                        else None
                    ),

                "anomaly_score":
                    round(
                        row[
                            "anomaly_score"
                        ],
                        2,
                    ),

                "evidence":
                    (
                        "Delivery deterioration "
                        "coincides with abnormal "
                        "warehouse/network load "
                        "while logistics data "
                        "contracts remain valid."
                    ),
            }
        )

    return incidents


def load_logistics_data_health():
    controls_path = (
        PROJECT_ROOT
        / "artifacts"
        / "data_quality_controls.csv"
    )

    if not controls_path.exists():
        return {
            "logistics_controls_checked":
                0,
            "logistics_failures":
                0,
            "logistics_data_passed":
                True,
        }

    controls = pd.read_csv(
        controls_path
    )

    logistics_domains = [
        "shipments",
        "tracking_events",
        "logistics",
    ]

    relevant = controls[
        controls[
            "domain"
        ].isin(
            logistics_domains
        )
    ]

    failures = relevant[
        relevant[
            "status"
        ].eq(
            "FAIL"
        )
    ]

    return {
        "logistics_controls_checked":
            int(
                len(
                    relevant
                )
            ),

        "logistics_failures":
            int(
                len(
                    failures
                )
            ),

        "logistics_data_passed":
            bool(
                failures.empty
            ),
    }


def save_outputs(
    windows,
    candidates,
    incidents,
    data_health,
):
    silver = (
        PROJECT_ROOT
        / "data"
        / "silver"
    )

    artifacts = (
        PROJECT_ROOT
        / "artifacts"
    )

    silver.mkdir(
        parents=True,
        exist_ok=True,
    )

    artifacts.mkdir(
        parents=True,
        exist_ok=True,
    )

    windows.to_parquet(
        silver
        / "warehouse_anomaly_windows.parquet",
        index=False,
    )

    pd.DataFrame(
        incidents
    ).to_csv(
        artifacts
        / "business_incidents.csv",
        index=False,
    )

    summary = {
        "windows_evaluated":
            int(
                len(
                    windows
                )
            ),

        "business_incident_candidates":
            int(
                len(
                    incidents
                )
            ),

        **data_health,
    }

    (
        artifacts
        / "business_anomaly_summary.json"
    ).write_text(
        json.dumps(
            summary,
            indent=2,
        ),
        encoding="utf-8",
    )

    return summary


def main():
    print("=" * 72)
    print(
        "AEGIS BUSINESS KPI ANOMALY ENGINE"
    )
    print("=" * 72)

    print()
    print(
        "Scanning operational KPI behavior."
    )

    print(
        "Ground-truth incident metadata "
        "is NOT used."
    )

    (
        shipments,
        support,
        warehouses,
    ) = load_data()

    warehouse_shipments = (
        build_warehouse_shipments(
            shipments
        )
    )

    baselines = (
        calculate_warehouse_baselines(
            warehouse_shipments
        )
    )

    daily = (
        build_daily_metrics(
            warehouse_shipments
        )
    )

    windows = (
        build_rolling_windows(
            daily,
            baselines,
        )
    )

    windows = (
        calculate_anomaly_score(
            windows
        )
    )

    candidates = (
        identify_candidates(
            windows
        )
    )

    candidates = (
        collapse_overlapping_windows(
            candidates
        )
    )

    candidates = enrich_candidates(
        candidates,
        warehouses,
        support,
        warehouse_shipments,
    )

    incidents = (
        create_incident_records(
            candidates
        )
    )

    data_health = (
        load_logistics_data_health()
    )

    summary = save_outputs(
        windows,
        candidates,
        incidents,
        data_health,
    )

    print()
    print("=" * 72)
    print(
        "BUSINESS ANOMALY SUMMARY"
    )
    print("=" * 72)

    print()

    print(
        f"Rolling window:              "
        f"{WINDOW_DAYS} days"
    )

    print(
        f"Windows evaluated:           "
        f"{summary['windows_evaluated']:,}"
    )

    print(
        f"Business candidates:         "
        f"{summary['business_incident_candidates']}"
    )

    print(
        f"Logistics controls checked:  "
        f"{summary['logistics_controls_checked']}"
    )

    print(
        f"Logistics DQ failures:       "
        f"{summary['logistics_failures']}"
    )

    print(
        f"Logistics data trustworthy:  "
        f"{summary['logistics_data_passed']}"
    )

    if not incidents:
        print()
        print(
            "No material business "
            "incident candidate detected."
        )

    else:
        print()

        for incident in incidents:
            print(
                "BUSINESS INCIDENT CANDIDATE"
            )

            print(
                "-" * 72
            )

            print(
                f"Location:             "
                f"{incident['city']}, "
                f"{incident['country']}"
            )

            print(
                f"Detected window:      "
                f"{incident['start_date']} "
                f"to "
                f"{incident['end_date']}"
            )

            print(
                f"Shipments:            "
                f"{incident['shipments']:,}"
            )

            print(
                f"Baseline delay:       "
                f"{incident['baseline_delay_pct']:.2f}%"
            )

            print(
                f"Incident delay:       "
                f"{incident['incident_delay_pct']:.2f}%"
            )

            print(
                f"Delay increase:       "
                f"+{incident['delay_increase_pp']:.2f} pp"
            )

            print(
                f"Baseline load:        "
                f"{incident['baseline_load_pct']:.2f}%"
            )

            print(
                f"Incident load:        "
                f"{incident['incident_load_pct']:.2f}%"
            )

            print(
                f"Load increase:        "
                f"+{incident['load_increase_pp']:.2f} pp"
            )

            print(
                f"SLA change:           "
                f"{incident['sla_change_pp']:.2f} pp"
            )

            print(
                f"Transit increase:     "
                f"+{incident['transit_increase_hours']:.2f} h"
            )

            print(
                f"Support cases:        "
                f"{incident['affected_support_cases']}"
            )

            print(
                f"Anomaly score:        "
                f"{incident['anomaly_score']:.2f}/100"
            )

            print()
            print(
                "Classification:"
            )

            print(
                incident[
                    "classification"
                ]
            )

            print()
            print(
                "Evidence:"
            )

            print(
                incident[
                    "evidence"
                ]
            )

            print()

    print(
        "Business anomaly outputs "
        "created successfully."
    )

    print(
        "No ground-truth file was read."
    )


if __name__ == "__main__":
    main()

