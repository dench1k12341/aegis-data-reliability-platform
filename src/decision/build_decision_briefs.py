import json

import pandas as pd

from src.utils.config import PROJECT_ROOT


def load_registry():
    path = (
        PROJECT_ROOT
        / "artifacts"
        / "incident_registry.csv"
    )

    if not path.exists():
        raise FileNotFoundError(
            "incident_registry.csv not found. "
            "Run the unified incident classifier first."
        )

    registry = pd.read_csv(
        path
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

    return registry


def split_evidence(value):
    if pd.isna(value):
        return []

    return [
        item.strip()
        for item in str(
            value
        ).split("|")
        if item.strip()
    ]


def build_data_brief(row):
    coverage = float(
        row[
            "event_coverage_pct"
        ]
    )

    revenue_capture = float(
        row[
            "revenue_capture_pct"
        ]
    )

    missing_records = int(
        row[
            "missing_records"
        ]
    )

    executive_summary = (
        "A data reliability incident was detected "
        "in purchase telemetry. "
        f"Only {coverage:.2f}% of expected purchase events "
        "were observed and event-based revenue captured "
        f"{revenue_capture:.2f}% of trusted operational revenue. "
        "Operational source records remain available, "
        "so the affected telemetry KPI should not be used "
        "for business decisions until the pipeline is repaired."
    )

    decision = {
        "decision_status":
            "PAUSE_KPI_DECISIONS",

        "decision_label":
            "Do not trust affected telemetry KPI",

        "executive_summary":
            executive_summary,

        "recommended_actions": [
            (
                "Suspend use of purchase-event revenue "
                "for reporting and decision-making "
                "during the affected period."
            ),
            (
                "Investigate event emission, schema changes, "
                "tracking deployment and ingestion pipeline."
            ),
            (
                "Backfill missing purchase events where possible "
                "and rerun reconciliation before restoring trust."
            ),
        ],

        "key_metrics": {
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

            "missing_purchase_events":
                missing_records,
        },
    }

    return decision


def build_business_brief(row):
    executive_summary = (
        "A real operational performance incident was detected "
        f"in {row['location']}. "
        "Logistics Data Quality controls passed, "
        "while delivery performance deteriorated together "
        "with abnormal network load. "
        f"The strongest root-cause hypothesis is "
        f"{row['primary_cause']}."
    )

    decision = {
        "decision_status":
            "ACT_ON_OPERATIONS",

        "decision_label":
            "Operational intervention required",

        "executive_summary":
            executive_summary,

        "recommended_actions": [
            (
                "Activate temporary operational capacity "
                "for the affected hub or network segment."
            ),
            (
                "Rebalance shipment volume across available "
                "warehouses, routes or carrier capacity."
            ),
            (
                "Track SLA, network load, support SLA and CSAT "
                "until metrics return to baseline."
            ),
        ],

        "key_metrics": {
            "anomaly_score":
                (
                    round(
                        float(
                            row[
                                "anomaly_score"
                            ]
                        ),
                        2,
                    )
                    if pd.notna(
                        row[
                            "anomaly_score"
                        ]
                    )
                    else None
                ),

            "affected_shipments":
                int(
                    row[
                        "affected_records"
                    ]
                ),
        },
    }

    return decision


def build_decision_briefs(
    registry,
):
    briefs = []

    for _, row in (
        registry.iterrows()
    ):
        classification = row[
            "classification"
        ]

        if (
            classification
            == "DATA_INCIDENT"
        ):
            decision = (
                build_data_brief(
                    row
                )
            )

        elif (
            classification
            == "BUSINESS_INCIDENT"
        ):
            decision = (
                build_business_brief(
                    row
                )
            )

        else:
            decision = {
                "decision_status":
                    "REVIEW_REQUIRED",

                "decision_label":
                    "Manual review required",

                "executive_summary":
                    (
                        "The incident classification "
                        "requires manual review."
                    ),

                "recommended_actions": [
                    (
                        "Review incident evidence "
                        "before taking action."
                    )
                ],

                "key_metrics": {},
            }

        brief = {
            "incident_id":
                row[
                    "incident_id"
                ],

            "classification":
                classification,

            "severity":
                row[
                    "severity"
                ],

            "domain":
                row[
                    "domain"
                ],

            "location":
                (
                    None
                    if pd.isna(
                        row[
                            "location"
                        ]
                    )
                    else row[
                        "location"
                    ]
                ),

            "detected_window": {
                "start":
                    row[
                        "detected_start_date"
                    ].strftime(
                        "%Y-%m-%d"
                    ),

                "end":
                    row[
                        "detected_end_date"
                    ].strftime(
                        "%Y-%m-%d"
                    ),
            },

            "confidence_score":
                round(
                    float(
                        row[
                            "confidence_score"
                        ]
                    ),
                    2,
                ),

            "data_trust_status":
                row[
                    "data_trust_status"
                ],

            "primary_cause":
                row[
                    "primary_cause"
                ],

            "business_metric":
                row[
                    "business_metric"
                ],

            "business_impact":
                row[
                    "business_impact"
                ],

            "evidence":
                split_evidence(
                    row[
                        "evidence"
                    ]
                ),

            **decision,
        }

        briefs.append(
            brief
        )

    return briefs


def build_markdown(
    briefs,
):
    lines = [
        "# Aegis Decision Intelligence Brief",
        "",
        (
            "Generated from deterministic incident, "
            "Data Quality and RCA outputs."
        ),
        "",
    ]

    for brief in briefs:
        lines.extend(
            [
                (
                    f"## {brief['incident_id']} — "
                    f"{brief['classification']}"
                ),
                "",
                (
                    f"**Severity:** "
                    f"{brief['severity']}"
                ),
                "",
                (
                    f"**Confidence:** "
                    f"{brief['confidence_score']:.2f}%"
                ),
                "",
                (
                    f"**Data Trust:** "
                    f"{brief['data_trust_status']}"
                ),
                "",
                (
                    f"**Primary Cause:** "
                    f"{brief['primary_cause']}"
                ),
                "",
                (
                    f"**Decision:** "
                    f"{brief['decision_label']}"
                ),
                "",
                "### Executive Summary",
                "",
                brief[
                    "executive_summary"
                ],
                "",
                "### Business Impact",
                "",
                brief[
                    "business_impact"
                ],
                "",
                "### Evidence",
                "",
            ]
        )

        for evidence in brief[
            "evidence"
        ]:
            lines.append(
                f"- {evidence}"
            )

        lines.extend(
            [
                "",
                "### Recommended Actions",
                "",
            ]
        )

        for action in brief[
            "recommended_actions"
        ]:
            lines.append(
                f"- {action}"
            )

        lines.extend(
            [
                "",
                "---",
                "",
            ]
        )

    return "\n".join(
        lines
    )


def save_outputs(
    briefs,
):
    artifacts = (
        PROJECT_ROOT
        / "artifacts"
    )

    json_path = (
        artifacts
        / "decision_briefs.json"
    )

    markdown_path = (
        artifacts
        / "decision_briefs.md"
    )

    json_path.write_text(
        json.dumps(
            briefs,
            indent=2,
        ),
        encoding="utf-8",
    )

    markdown_path.write_text(
        build_markdown(
            briefs
        ),
        encoding="utf-8",
    )

    return (
        json_path,
        markdown_path,
    )


def main():
    print("=" * 72)
    print(
        "AEGIS DECISION INTELLIGENCE LAYER"
    )
    print("=" * 72)

    print()
    print(
        "Building deterministic evidence-based "
        "decision briefs."
    )

    print(
        "No LLM is used at this stage."
    )

    registry = (
        load_registry()
    )

    briefs = (
        build_decision_briefs(
            registry
        )
    )

    (
        json_path,
        markdown_path,
    ) = save_outputs(
        briefs
    )

    print()
    print("=" * 72)
    print(
        "DECISION INTELLIGENCE SUMMARY"
    )
    print("=" * 72)

    print()

    print(
        f"Decision briefs created: "
        f"{len(briefs)}"
    )

    for brief in briefs:
        print()

        print(
            brief[
                "incident_id"
            ]
        )

        print(
            "-" * 72
        )

        print(
            f"Classification:    "
            f"{brief['classification']}"
        )

        print(
            f"Severity:          "
            f"{brief['severity']}"
        )

        print(
            f"Confidence:        "
            f"{brief['confidence_score']:.2f}%"
        )

        print(
            f"Data trust:        "
            f"{brief['data_trust_status']}"
        )

        print(
            f"Primary cause:     "
            f"{brief['primary_cause']}"
        )

        print(
            f"Decision:          "
            f"{brief['decision_label']}"
        )

        print()

        print(
            "Executive summary:"
        )

        print(
            brief[
                "executive_summary"
            ]
        )

    print()

    print(
        "Outputs created:"
    )

    print(
        f"  {json_path}"
    )

    print(
        f"  {markdown_path}"
    )

    print()

    print(
        "Decision layer completed successfully."
    )


if __name__ == "__main__":
    main()
