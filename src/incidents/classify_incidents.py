import json

import numpy as np
import pandas as pd

from src.utils.config import PROJECT_ROOT


def load_inputs():
    artifacts = (
        PROJECT_ROOT
        / "artifacts"
    )

    data_incidents_path = (
        artifacts
        / "data_incidents.csv"
    )

    business_incidents_path = (
        artifacts
        / "business_incidents.csv"
    )

    rca_path = (
        artifacts
        / "root_cause_report.json"
    )

    controls_path = (
        artifacts
        / "data_quality_controls.csv"
    )

    data_incidents = (
        pd.read_csv(
            data_incidents_path
        )
        if data_incidents_path.exists()
        else pd.DataFrame()
    )

    business_incidents = (
        pd.read_csv(
            business_incidents_path
        )
        if business_incidents_path.exists()
        else pd.DataFrame()
    )

    controls = (
        pd.read_csv(
            controls_path
        )
        if controls_path.exists()
        else pd.DataFrame()
    )

    if rca_path.exists():
        rca_reports = json.loads(
            rca_path.read_text(
                encoding="utf-8"
            )
        )
    else:
        rca_reports = []

    return (
        artifacts,
        data_incidents,
        business_incidents,
        rca_reports,
        controls,
    )


def data_trust_summary(
    controls,
):
    if controls.empty:
        return {
            "controls_executed": 0,
            "controls_failed": 0,
            "non_app_failures": 0,
        }

    failed = controls[
        controls[
            "status"
        ].eq(
            "FAIL"
        )
    ]

    non_app_failures = failed[
        ~failed[
            "domain"
        ].eq(
            "app_events"
        )
    ]

    return {
        "controls_executed":
            int(
                len(
                    controls
                )
            ),

        "controls_failed":
            int(
                len(
                    failed
                )
            ),

        "non_app_failures":
            int(
                len(
                    non_app_failures
                )
            ),
    }


def score_data_incident(
    row,
    trust,
):
    coverage = float(
        row[
            "observed_vs_expected_pct"
        ]
    )

    revenue_capture = float(
        row[
            "revenue_capture_pct"
        ]
    )

    observed = max(
        float(
            row[
                "observed_purchase_events"
            ]
        ),
        1.0,
    )

    null_values = float(
        row[
            "null_purchase_values"
        ]
    )

    null_rate = (
        null_values
        / observed
        * 100
    )

    coverage_gap = (
        100
        - coverage
    )

    revenue_gap = (
        100
        - revenue_capture
    )

    coverage_score = np.clip(
        coverage_gap
        / 40
        * 100,
        0,
        100,
    )

    revenue_score = np.clip(
        revenue_gap
        / 60
        * 100,
        0,
        100,
    )

    null_score = np.clip(
        null_rate
        / 30
        * 100,
        0,
        100,
    )

    source_consistency_score = (
        100
        if trust[
            "non_app_failures"
        ] == 0
        else 40
    )

    confidence = (
        coverage_score
        * 0.35
        + revenue_score
        * 0.35
        + null_score
        * 0.20
        + source_consistency_score
        * 0.10
    )

    confidence = float(
        np.clip(
            confidence,
            0,
            99,
        )
    )

    return (
        round(
            confidence,
            2,
        ),
        round(
            null_rate,
            2,
        ),
    )


def data_severity(
    coverage,
    revenue_capture,
):
    if (
        revenue_capture < 40
        or coverage < 60
    ):
        return "Critical"

    if (
        revenue_capture < 70
        or coverage < 80
    ):
        return "High"

    return "Medium"


def build_data_records(
    data_incidents,
    controls,
):
    if data_incidents.empty:
        return []

    trust = data_trust_summary(
        controls
    )

    records = []

    for _, row in (
        data_incidents.iterrows()
    ):
        (
            confidence,
            null_rate,
        ) = score_data_incident(
            row,
            trust,
        )

        coverage = float(
            row[
                "observed_vs_expected_pct"
            ]
        )

        revenue_capture = float(
            row[
                "revenue_capture_pct"
            ]
        )

        severity = data_severity(
            coverage,
            revenue_capture,
        )

        records.append(
            {
                "incident_id":
                    None,

                "classification":
                    "DATA_INCIDENT",

                "severity":
                    severity,

                "domain":
                    row[
                        "domain"
                    ],

                "location":
                    None,

                "detected_start_date":
                    row[
                        "start_date"
                    ],

                "detected_end_date":
                    row[
                        "end_date"
                    ],

                "confidence_score":
                    confidence,

                "primary_cause":
                    "Purchase Telemetry Failure",

                "affected_records":
                    int(
                        row[
                            "expected_purchase_events"
                        ]
                    ),

                "missing_records":
                    int(
                        row[
                            "missing_purchase_events"
                        ]
                    ),

                "data_trust_status":
                    "FAILED",

                "anomaly_score":
                    None,

                "event_coverage_pct":
                    round(
                        coverage,
                        2,
                    ),

                "revenue_capture_pct":
                    round(
                        revenue_capture,
                        2,
                    ),

                "null_value_pct":
                    null_rate,

                "business_metric":
                    "Purchase Events / Event Revenue",

                "business_impact":
                    (
                        f"{int(row['missing_purchase_events'])} "
                        "purchase events missing; "
                        f"event revenue captured at "
                        f"{revenue_capture:.2f}% "
                        "of trusted operational revenue."
                    ),

                "recommended_action":
                    (
                        "Do not use affected purchase-event "
                        "revenue for decision-making. "
                        "Investigate telemetry pipeline, "
                        "schema changes and purchase event emission."
                    ),

                "evidence":
                    row[
                        "evidence"
                    ],
            }
        )

    return records


def build_business_records(
    business_incidents,
    rca_reports,
):
    if business_incidents.empty:
        return []

    rca_lookup = {
        report[
            "incident_id"
        ]: report
        for report
        in rca_reports
    }

    records = []

    for _, row in (
        business_incidents.iterrows()
    ):
        candidate_id = row[
            "candidate_incident_id"
        ]

        rca = rca_lookup.get(
            candidate_id,
            {},
        )

        confidence = float(
            rca.get(
                "confidence_score",
                row.get(
                    "anomaly_score",
                    0,
                ),
            )
        )

        shipments = int(
            row[
                "shipments"
            ]
        )

        if (
            confidence >= 90
            and shipments >= 100
        ):
            severity = "Critical"

        elif confidence >= 75:
            severity = "High"

        else:
            severity = "Medium"

        primary_cause = rca.get(
            "primary_root_cause",
            "Operational Performance Degradation",
        )

        incident_metrics = rca.get(
            "incident_metrics",
            {},
        )

        baseline_metrics = rca.get(
            "baseline_metrics",
            {},
        )

        delay_before = (
            baseline_metrics.get(
                "delay_pct"
            )
        )

        delay_after = (
            incident_metrics.get(
                "delay_pct"
            )
        )

        load_before = (
            baseline_metrics.get(
                "avg_load_pct"
            )
        )

        load_after = (
            incident_metrics.get(
                "avg_load_pct"
            )
        )

        support_impact = rca.get(
            "incident_support",
            {},
        )

        support_cases = int(
            support_impact.get(
                "cases",
                row.get(
                    "affected_support_cases",
                    0,
                ),
            )
        )

        business_impact = (
            f"{shipments} shipments evaluated; "
            f"delay rate "
            f"{delay_before:.2f}% → "
            f"{delay_after:.2f}%; "
            f"network load "
            f"{load_before:.2f}% → "
            f"{load_after:.2f}%; "
            f"{support_cases} support cases affected."
        )

        records.append(
            {
                "incident_id":
                    None,

                "classification":
                    "BUSINESS_INCIDENT",

                "severity":
                    severity,

                "domain":
                    "logistics",

                "location":
                    (
                        f"{row['city']}, "
                        f"{row['country']}"
                    ),

                "detected_start_date":
                    row[
                        "start_date"
                    ],

                "detected_end_date":
                    row[
                        "end_date"
                    ],

                "confidence_score":
                    round(
                        confidence,
                        2,
                    ),

                "primary_cause":
                    primary_cause,

                "affected_records":
                    shipments,

                "missing_records":
                    0,

                "data_trust_status":
                    (
                        "PASSED"
                        if rca.get(
                            "data_trust",
                            {}
                        ).get(
                            "trusted",
                            True,
                        )
                        else "FAILED"
                    ),

                "anomaly_score":
                    round(
                        float(
                            row[
                                "anomaly_score"
                            ]
                        ),
                        2,
                    ),

                "event_coverage_pct":
                    None,

                "revenue_capture_pct":
                    None,

                "null_value_pct":
                    None,

                "business_metric":
                    "Delivery SLA / Delay Rate",

                "business_impact":
                    business_impact,

                "recommended_action":
                    (
                        "Investigate warehouse capacity, "
                        "network load and operational throughput. "
                        "Prioritize load balancing and "
                        "temporary capacity mitigation."
                    ),

                "evidence":
                    rca.get(
                        "evidence",
                        [
                            row[
                                "evidence"
                            ]
                        ],
                    ),
            }
        )

    return records


def normalize_evidence(
    value,
):
    if isinstance(
        value,
        list,
    ):
        return " | ".join(
            str(item)
            for item in value
        )

    return str(
        value
    )


def build_registry(
    records,
):
    if not records:
        return pd.DataFrame()

    registry = pd.DataFrame(
        records
    )

    registry[
        "detected_start_date"
    ] = pd.to_datetime(
        registry[
            "detected_start_date"
        ]
    )

    registry[
        "detected_end_date"
    ] = pd.to_datetime(
        registry[
            "detected_end_date"
        ]
    )

    registry = (
        registry
        .sort_values(
            [
                "detected_start_date",
                "classification",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    registry[
        "incident_id"
    ] = [
        f"AEGIS-INC-{i:03d}"
        for i in range(
            1,
            len(
                registry
            )
            + 1,
        )
    ]

    registry[
        "duration_days"
    ] = (
        registry[
            "detected_end_date"
        ]
        - registry[
            "detected_start_date"
        ]
    ).dt.days + 1

    registry[
        "evidence"
    ] = registry[
        "evidence"
    ].apply(
        normalize_evidence
    )

    return registry


def save_outputs(
    registry,
):
    artifacts = (
        PROJECT_ROOT
        / "artifacts"
    )

    registry.to_csv(
        artifacts
        / "incident_registry.csv",
        index=False,
    )

    json_records = (
        registry
        .assign(
            detected_start_date=lambda df:
                df[
                    "detected_start_date"
                ].dt.strftime(
                    "%Y-%m-%d"
                ),

            detected_end_date=lambda df:
                df[
                    "detected_end_date"
                ].dt.strftime(
                    "%Y-%m-%d"
                ),
        )
        .where(
            pd.notna(
                registry
            ),
            None,
        )
        .to_dict(
            orient="records"
        )
    )

    (
        artifacts
        / "incident_registry.json"
    ).write_text(
        json.dumps(
            json_records,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )


def main():
    print("=" * 72)
    print(
        "AEGIS UNIFIED INCIDENT CLASSIFIER"
    )
    print("=" * 72)

    print()
    print(
        "Combining independently detected "
        "Data and Business incidents."
    )

    print(
        "Ground-truth incident metadata "
        "is NOT used."
    )

    (
        artifacts,
        data_incidents,
        business_incidents,
        rca_reports,
        controls,
    ) = load_inputs()

    records = []

    records.extend(
        build_data_records(
            data_incidents,
            controls,
        )
    )

    records.extend(
        build_business_records(
            business_incidents,
            rca_reports,
        )
    )

    registry = build_registry(
        records
    )

    save_outputs(
        registry
    )

    print()
    print("=" * 72)
    print(
        "UNIFIED INCIDENT REGISTRY"
    )
    print("=" * 72)

    print()

    print(
        f"Incidents classified: "
        f"{len(registry)}"
    )

    if registry.empty:
        print(
            "No incidents available."
        )
        return

    for _, row in (
        registry.iterrows()
    ):
        print()

        print(
            f"{row['incident_id']}"
        )

        print(
            "-" * 72
        )

        print(
            f"Classification:    "
            f"{row['classification']}"
        )

        print(
            f"Severity:          "
            f"{row['severity']}"
        )

        print(
            f"Domain:            "
            f"{row['domain']}"
        )

        if pd.notna(
            row[
                "location"
            ]
        ):
            print(
                f"Location:          "
                f"{row['location']}"
            )

        print(
            f"Window:            "
            f"{row['detected_start_date']:%Y-%m-%d} "
            f"to "
            f"{row['detected_end_date']:%Y-%m-%d}"
        )

        print(
            f"Confidence:        "
            f"{row['confidence_score']:.2f}%"
        )

        print(
            f"Primary cause:     "
            f"{row['primary_cause']}"
        )

        print(
            f"Data trust:        "
            f"{row['data_trust_status']}"
        )

        print()

        print(
            "Business impact:"
        )

        print(
            row[
                "business_impact"
            ]
        )

        print()

        print(
            "Recommended action:"
        )

        print(
            row[
                "recommended_action"
            ]
        )

    print()

    print(
        "Registry created:"
    )

    print(
        "  artifacts/incident_registry.csv"
    )

    print(
        "  artifacts/incident_registry.json"
    )

    print()

    print(
        "No ground-truth file was read."
    )


if __name__ == "__main__":
    main()
