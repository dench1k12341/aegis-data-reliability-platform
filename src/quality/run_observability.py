import json

import numpy as np
import pandas as pd

from src.utils.config import PROJECT_ROOT


TABLE_SPECS = {
    "orders": {
        "pk": "order_id",
        "required": [
            "order_id",
            "customer_id",
            "order_ts",
            "order_total_eur",
            "order_status",
        ],
        "critical": [
            "order_id",
            "customer_id",
            "order_ts",
            "order_total_eur",
            "order_status",
        ],
    },
    "payments": {
        "pk": "payment_id",
        "required": [
            "payment_id",
            "order_id",
            "payment_ts",
            "payment_status",
            "payment_amount_eur",
        ],
        "critical": [
            "payment_id",
            "order_id",
            "payment_ts",
            "payment_status",
            "payment_amount_eur",
        ],
    },
    "shipments": {
        "pk": "shipment_id",
        "required": [
            "shipment_id",
            "order_id",
            "carrier_id",
            "origin_warehouse_id",
            "destination_warehouse_id",
            "shipment_created_ts",
            "expected_delivery_ts",
            "shipment_status",
        ],
        "critical": [
            "shipment_id",
            "order_id",
            "carrier_id",
            "origin_warehouse_id",
            "destination_warehouse_id",
            "shipment_created_ts",
            "expected_delivery_ts",
            "shipment_status",
        ],
    },
    "tracking_events": {
        "pk": "event_id",
        "required": [
            "event_id",
            "shipment_id",
            "event_type",
            "event_ts",
            "carrier_id",
        ],
        "critical": [
            "event_id",
            "shipment_id",
            "event_type",
            "event_ts",
            "carrier_id",
        ],
    },
    "support_cases": {
        "pk": "case_id",
        "required": [
            "case_id",
            "customer_id",
            "order_id",
            "shipment_id",
            "created_ts",
            "first_response_ts",
            "resolved_ts",
        ],
        "critical": [
            "case_id",
            "customer_id",
            "order_id",
            "shipment_id",
            "created_ts",
            "first_response_ts",
            "resolved_ts",
        ],
    },
    "app_events": {
        "pk": "event_id",
        "required": [
            "event_id",
            "session_id",
            "event_type",
            "event_ts",
            "customer_id",
        ],
        "critical": [
            "event_id",
            "session_id",
            "event_type",
            "event_ts",
            "customer_id",
        ],
    },
}


SEVERITY_WEIGHT = {
    "Low": 1,
    "Medium": 2,
    "High": 3,
    "Critical": 5,
}


def load_bronze():
    bronze = (
        PROJECT_ROOT
        / "data"
        / "bronze"
    )

    datasets = {}

    for name in TABLE_SPECS:
        path = bronze / f"{name}.parquet"

        if not path.exists():
            raise FileNotFoundError(
                f"Missing Bronze dataset: {path}"
            )

        datasets[name] = (
            pd.read_parquet(path)
        )

    datetime_columns = {
        "orders": [
            "order_ts",
        ],
        "payments": [
            "payment_ts",
        ],
        "shipments": [
            "shipment_created_ts",
            "expected_delivery_ts",
            "delivery_ts",
        ],
        "tracking_events": [
            "event_ts",
        ],
        "support_cases": [
            "created_ts",
            "first_response_ts",
            "resolved_ts",
        ],
        "app_events": [
            "event_ts",
        ],
    }

    for dataset_name, columns in (
        datetime_columns.items()
    ):
        for column in columns:
            if (
                column
                in datasets[
                    dataset_name
                ].columns
            ):
                datasets[
                    dataset_name
                ][column] = pd.to_datetime(
                    datasets[
                        dataset_name
                    ][column]
                )

    return bronze, datasets


def add_control(
    controls,
    control_id,
    domain,
    check_type,
    status,
    severity,
    observed,
    threshold,
    details,
):
    controls.append(
        {
            "control_id": control_id,
            "domain": domain,
            "check_type": check_type,
            "status": status,
            "severity": severity,
            "observed": observed,
            "threshold": threshold,
            "details": details,
        }
    )


def run_table_contracts(
    datasets,
    controls,
):
    for name, spec in TABLE_SPECS.items():
        df = datasets[name]

        missing_columns = [
            column
            for column
            in spec["required"]
            if column
            not in df.columns
        ]

        schema_status = (
            "PASS"
            if not missing_columns
            else "FAIL"
        )

        add_control(
            controls,
            f"{name.upper()}_SCHEMA",
            name,
            "Schema",
            schema_status,
            "High",
            len(missing_columns),
            0,
            (
                "Required schema present"
                if not missing_columns
                else (
                    "Missing columns: "
                    + ", ".join(
                        missing_columns
                    )
                )
            ),
        )

        if spec["pk"] in df.columns:
            duplicate_count = int(
                df[
                    spec["pk"]
                ].duplicated().sum()
            )

            add_control(
                controls,
                f"{name.upper()}_PK",
                name,
                "Uniqueness",
                (
                    "PASS"
                    if duplicate_count == 0
                    else "FAIL"
                ),
                "High",
                duplicate_count,
                0,
                (
                    f"Duplicate "
                    f"{spec['pk']} values"
                ),
            )

        available_critical = [
            column
            for column
            in spec["critical"]
            if column in df.columns
        ]

        null_count = int(
            df[
                available_critical
            ]
            .isna()
            .sum()
            .sum()
        )

        add_control(
            controls,
            f"{name.upper()}_CRITICAL_NULLS",
            name,
            "Completeness",
            (
                "PASS"
                if null_count == 0
                else "FAIL"
            ),
            "High",
            null_count,
            0,
            "Null values in critical fields",
        )


def run_fk_check(
    controls,
    child,
    child_column,
    parent,
    parent_column,
    child_name,
    parent_name,
):
    invalid_count = int(
        (
            ~child[
                child_column
            ].isin(
                parent[
                    parent_column
                ]
            )
        ).sum()
    )

    add_control(
        controls,
        (
            f"{child_name.upper()}_"
            f"{parent_name.upper()}_FK"
        ),
        child_name,
        "Referential Integrity",
        (
            "PASS"
            if invalid_count == 0
            else "FAIL"
        ),
        "High",
        invalid_count,
        0,
        (
            f"{child_column} must exist "
            f"in {parent_name}."
            f"{parent_column}"
        ),
    )


def run_referential_integrity(
    datasets,
    controls,
):
    orders = datasets["orders"]
    payments = datasets["payments"]
    shipments = datasets["shipments"]
    tracking = datasets[
        "tracking_events"
    ]
    support = datasets[
        "support_cases"
    ]
    app = datasets["app_events"]

    run_fk_check(
        controls,
        payments,
        "order_id",
        orders,
        "order_id",
        "payments",
        "orders",
    )

    run_fk_check(
        controls,
        shipments,
        "order_id",
        orders,
        "order_id",
        "shipments",
        "orders",
    )

    run_fk_check(
        controls,
        tracking,
        "shipment_id",
        shipments,
        "shipment_id",
        "tracking_events",
        "shipments",
    )

    run_fk_check(
        controls,
        support,
        "shipment_id",
        shipments,
        "shipment_id",
        "support_cases",
        "shipments",
    )

    linked_app = app[
        app["order_id"].notna()
    ]

    run_fk_check(
        controls,
        linked_app,
        "order_id",
        orders,
        "order_id",
        "app_events",
        "orders",
    )


def run_payment_reconciliation(
    datasets,
    controls,
):
    orders = datasets["orders"]
    payments = datasets["payments"]

    reconciliation = orders[
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
        how="inner",
        validate="one_to_one",
    )

    difference = (
        reconciliation[
            "order_total_eur"
        ]
        - reconciliation[
            "payment_amount_eur"
        ]
    ).abs()

    mismatch_count = int(
        (difference > 0.01).sum()
    )

    add_control(
        controls,
        "ORDER_PAYMENT_AMOUNT_RECON",
        "commerce",
        "Cross-System Reconciliation",
        (
            "PASS"
            if mismatch_count == 0
            else "FAIL"
        ),
        "Critical",
        mismatch_count,
        0,
        "Order total must reconcile to payment amount.",
    )


def run_tracking_consistency(
    datasets,
    controls,
):
    shipments = datasets["shipments"]
    tracking = datasets[
        "tracking_events"
    ]

    terminal = tracking[
        tracking[
            "event_type"
        ].isin(
            [
                "DELIVERED",
                "LOST",
            ]
        )
    ]

    terminal_map = (
        terminal
        .groupby(
            "shipment_id"
        )[
            "event_type"
        ]
        .last()
    )

    delivered_ids = shipments.loc[
        shipments[
            "lost_flag"
        ].eq(0),
        "shipment_id",
    ]

    lost_ids = shipments.loc[
        shipments[
            "lost_flag"
        ].eq(1),
        "shipment_id",
    ]

    delivered_missing = int(
        (
            terminal_map
            .reindex(
                delivered_ids
            )
            .ne(
                "DELIVERED"
            )
        ).sum()
    )

    lost_missing = int(
        (
            terminal_map
            .reindex(
                lost_ids
            )
            .ne(
                "LOST"
            )
        ).sum()
    )

    issue_count = (
        delivered_missing
        + lost_missing
    )

    add_control(
        controls,
        "SHIPMENT_TERMINAL_EVENT_RECON",
        "logistics",
        "Cross-System Reconciliation",
        (
            "PASS"
            if issue_count == 0
            else "FAIL"
        ),
        "Critical",
        issue_count,
        0,
        (
            "Delivered/Lost shipment state "
            "must match terminal tracking event."
        ),
    )


def run_support_chronology(
    datasets,
    controls,
):
    support = datasets[
        "support_cases"
    ]

    invalid = (
        (
            support[
                "first_response_ts"
            ]
            < support[
                "created_ts"
            ]
        )
        | (
            support[
                "resolved_ts"
            ]
            < support[
                "first_response_ts"
            ]
        )
    )

    issue_count = int(
        invalid.sum()
    )

    add_control(
        controls,
        "SUPPORT_CHRONOLOGY",
        "support_cases",
        "Validity",
        (
            "PASS"
            if issue_count == 0
            else "FAIL"
        ),
        "High",
        issue_count,
        0,
        (
            "created_ts <= "
            "first_response_ts <= resolved_ts"
        ),
    )


def build_purchase_reconciliation(
    datasets,
):
    orders = datasets["orders"].copy()
    app = datasets[
        "app_events"
    ].copy()

    expected = orders[
        orders[
            "order_status"
        ].isin(
            [
                "Completed",
                "Returned",
            ]
        )
    ].copy()

    expected[
        "date"
    ] = expected[
        "order_ts"
    ].dt.normalize()

    expected_daily = (
        expected
        .groupby(
            "date",
            as_index=False,
        )
        .agg(
            expected_purchase_count=(
                "order_id",
                "count",
            ),
            expected_revenue_eur=(
                "order_total_eur",
                "sum",
            ),
        )
    )

    observed = app[
        app[
            "event_type"
        ].eq(
            "purchase"
        )
    ].copy()

    observed[
        "date"
    ] = observed[
        "event_ts"
    ].dt.normalize()

    observed_daily = (
        observed
        .groupby(
            "date",
            as_index=False,
        )
        .agg(
            observed_purchase_count=(
                "event_id",
                "count",
            ),
            observed_revenue_eur=(
                "event_value_eur",
                "sum",
            ),
            purchase_value_null_count=(
                "event_value_eur",
                lambda series:
                    int(
                        series
                        .isna()
                        .sum()
                    ),
            ),
        )
    )

    daily = expected_daily.merge(
        observed_daily,
        on="date",
        how="left",
    )

    for column in [
        "observed_purchase_count",
        "observed_revenue_eur",
        "purchase_value_null_count",
    ]:
        daily[column] = (
            daily[column]
            .fillna(0)
        )

    daily[
        "observed_purchase_count"
    ] = daily[
        "observed_purchase_count"
    ].astype(int)

    daily[
        "purchase_value_null_count"
    ] = daily[
        "purchase_value_null_count"
    ].astype(int)

    daily[
        "purchase_count_ratio"
    ] = (
        daily[
            "observed_purchase_count"
        ]
        / daily[
            "expected_purchase_count"
        ]
    )

    daily[
        "missing_purchase_pct"
    ] = (
        (
            daily[
                "expected_purchase_count"
            ]
            - daily[
                "observed_purchase_count"
            ]
        )
        / daily[
            "expected_purchase_count"
        ]
        * 100
    ).clip(
        lower=0
    )

    daily[
        "purchase_value_null_pct"
    ] = np.where(
        daily[
            "observed_purchase_count"
        ] > 0,
        (
            daily[
                "purchase_value_null_count"
            ]
            / daily[
                "observed_purchase_count"
            ]
            * 100
        ),
        100.0,
    )

    daily[
        "revenue_ratio"
    ] = np.where(
        daily[
            "expected_revenue_eur"
        ] > 0,
        (
            daily[
                "observed_revenue_eur"
            ]
            / daily[
                "expected_revenue_eur"
            ]
        ),
        1.0,
    )

    daily[
        "incident_flag"
    ] = (
        (
            daily[
                "expected_purchase_count"
            ] >= 20
        )
        & (
            (
                daily[
                    "purchase_count_ratio"
                ] < 0.85
            )
            | (
                daily[
                    "purchase_value_null_pct"
                ] > 20
            )
            | (
                daily[
                    "revenue_ratio"
                ] < 0.70
            )
        )
    ).astype(int)

    return daily


def evaluate_purchase_reconciliation(
    daily,
    controls,
):
    flagged = daily[
        daily["incident_flag"].eq(1)
    ]

    if flagged.empty:
        add_control(
            controls,
            "APP_PURCHASE_RECONCILIATION",
            "app_events",
            "Cross-System Reconciliation",
            "PASS",
            "Critical",
            "0 anomalous days",
            (
                "count ratio >= 0.85; "
                "null rate <= 20%; "
                "revenue ratio >= 0.70"
            ),
            (
                "Purchase tracking agrees "
                "with operational orders."
            ),
        )

        return None

    start_date = flagged["date"].min()
    end_date = flagged["date"].max()

    expected_count = int(
        flagged[
            "expected_purchase_count"
        ].sum()
    )

    observed_count = int(
        flagged[
            "observed_purchase_count"
        ].sum()
    )

    missing_count = (
        expected_count
        - observed_count
    )

    total_nulls = int(
        flagged[
            "purchase_value_null_count"
        ].sum()
    )

    avg_count_ratio = float(
        observed_count
        / expected_count
    )

    observed_revenue = float(
        flagged[
            "observed_revenue_eur"
        ].sum()
    )

    expected_revenue = float(
        flagged[
            "expected_revenue_eur"
        ].sum()
    )

    revenue_ratio = (
        observed_revenue
        / expected_revenue
    )

    add_control(
        controls,
        "APP_PURCHASE_RECONCILIATION",
        "app_events",
        "Cross-System Reconciliation",
        "FAIL",
        "Critical",
        f"{len(flagged)} anomalous days",
        (
            "count ratio >= 0.85; "
            "null rate <= 20%; "
            "revenue ratio >= 0.70"
        ),
        (
            "Purchase tracking disagrees "
            "with operational order records."
        ),
    )

    incident = {
        "candidate_incident_id":
            "DQ-CAND-001",

        "classification":
            "DATA_INCIDENT_CANDIDATE",

        "domain":
            "app_events",

        "control":
            "APP_PURCHASE_RECONCILIATION",

        "start_date":
            str(start_date.date()),

        "end_date":
            str(end_date.date()),

        "anomalous_days":
            int(len(flagged)),

        "expected_purchase_events":
            expected_count,

        "observed_purchase_events":
            observed_count,

        "missing_purchase_events":
            int(missing_count),

        "observed_vs_expected_pct":
            round(
                avg_count_ratio * 100,
                2,
            ),

        "null_purchase_values":
            total_nulls,

        "expected_revenue_eur":
            round(
                expected_revenue,
                2,
            ),

        "observed_event_revenue_eur":
            round(
                observed_revenue,
                2,
            ),

        "revenue_capture_pct":
            round(
                revenue_ratio * 100,
                2,
            ),

        "evidence": (
            "Operational orders remain present "
            "while purchase telemetry is missing "
            "and/or incomplete."
        ),
    }

    return incident


def calculate_health_score(
    controls,
):
    total_weight = 0
    passed_weight = 0

    for control in controls:
        weight = SEVERITY_WEIGHT[
            control[
                "severity"
            ]
        ]

        total_weight += weight

        if (
            control[
                "status"
            ]
            == "PASS"
        ):
            passed_weight += weight

    if total_weight == 0:
        return 100.0

    return round(
        (
            passed_weight
            / total_weight
            * 100
        ),
        2,
    )


def save_outputs(
    controls,
    daily,
    incident,
    health_score,
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

    daily.to_parquet(
        silver
        / "daily_purchase_reconciliation.parquet",
        index=False,
    )

    controls_df = pd.DataFrame(
        controls
    )

    controls_df.to_csv(
        artifacts
        / "data_quality_controls.csv",
        index=False,
    )

    incidents = []

    if incident is not None:
        incidents.append(
            incident
        )

    pd.DataFrame(
        incidents
    ).to_csv(
        artifacts
        / "data_incidents.csv",
        index=False,
    )

    summary = {
        "data_health_score":
            health_score,

        "controls_executed":
            len(
                controls
            ),

        "controls_passed":
            sum(
                control[
                    "status"
                ] == "PASS"
                for control
                in controls
            ),

        "controls_failed":
            sum(
                control[
                    "status"
                ] == "FAIL"
                for control
                in controls
            ),

        "data_incident_candidates":
            len(
                incidents
            ),
    }

    (
        artifacts
        / "observability_summary.json"
    ).write_text(
        json.dumps(
            summary,
            indent=2,
        ),
        encoding="utf-8",
    )

    return (
        controls_df,
        summary,
    )


def main():
    print("=" * 72)
    print(
        "AEGIS DATA OBSERVABILITY ENGINE"
    )
    print("=" * 72)

    print()
    print(
        "Reading Bronze layer only."
    )

    print(
        "Ground-truth incident metadata "
        "is NOT used."
    )

    bronze, datasets = (
        load_bronze()
    )

    controls = []

    run_table_contracts(
        datasets,
        controls,
    )

    run_referential_integrity(
        datasets,
        controls,
    )

    run_payment_reconciliation(
        datasets,
        controls,
    )

    run_tracking_consistency(
        datasets,
        controls,
    )

    run_support_chronology(
        datasets,
        controls,
    )

    daily = (
        build_purchase_reconciliation(
            datasets
        )
    )

    incident = (
        evaluate_purchase_reconciliation(
            daily,
            controls,
        )
    )

    health_score = (
        calculate_health_score(
            controls
        )
    )

    controls_df, summary = (
        save_outputs(
            controls,
            daily,
            incident,
            health_score,
        )
    )

    print()
    print("=" * 72)
    print(
        "OBSERVABILITY SUMMARY"
    )
    print("=" * 72)

    print()

    print(
        f"Bronze datasets:       "
        f"{len(datasets)}"
    )

    print(
        f"Controls executed:     "
        f"{summary['controls_executed']}"
    )

    print(
        f"Controls passed:       "
        f"{summary['controls_passed']}"
    )

    print(
        f"Controls failed:       "
        f"{summary['controls_failed']}"
    )

    print(
        f"Data Health Score:     "
        f"{health_score:.2f}%"
    )

    print()

    failed = controls_df[
        controls_df[
            "status"
        ].eq(
            "FAIL"
        )
    ]

    if failed.empty:
        print(
            "No Data Quality incidents detected."
        )

    else:
        print(
            "FAILED CONTROLS:"
        )

        print(
            failed[
                [
                    "control_id",
                    "domain",
                    "severity",
                    "observed",
                ]
            ]
            .to_string(
                index=False
            )
        )

    if incident is not None:
        print()
        print(
            "DATA INCIDENT CANDIDATE"
        )
        print(
            "-" * 72
        )

        print(
            f"Domain:               "
            f"{incident['domain']}"
        )

        print(
            f"Detected window:      "
            f"{incident['start_date']} "
            f"to "
            f"{incident['end_date']}"
        )

        print(
            f"Anomalous days:       "
            f"{incident['anomalous_days']}"
        )

        print(
            f"Expected purchases:   "
            f"{incident['expected_purchase_events']:,}"
        )

        print(
            f"Observed purchases:   "
            f"{incident['observed_purchase_events']:,}"
        )

        print(
            f"Missing purchases:    "
            f"{incident['missing_purchase_events']:,}"
        )

        print(
            f"Event coverage:       "
            f"{incident['observed_vs_expected_pct']:.2f}%"
        )

        print(
            f"Null purchase values: "
            f"{incident['null_purchase_values']:,}"
        )

        print(
            f"Revenue capture:      "
            f"{incident['revenue_capture_pct']:.2f}%"
        )

        print()
        print(
            "Classification:"
        )

        print(
            "DATA_INCIDENT_CANDIDATE"
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
        "Observability outputs created successfully."
    )

    print(
        "No ground-truth file was read."
    )


if __name__ == "__main__":
    main()
