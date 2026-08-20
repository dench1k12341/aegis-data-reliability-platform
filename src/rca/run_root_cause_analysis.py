import json

import numpy as np
import pandas as pd

from src.utils.config import PROJECT_ROOT


BASELINE_DAYS = 60


def load_inputs():
    bronze = PROJECT_ROOT / "data" / "bronze"
    artifacts = PROJECT_ROOT / "artifacts"

    shipments = pd.read_parquet(
        bronze / "shipments.parquet"
    )

    support = pd.read_parquet(
        bronze / "support_cases.parquet"
    )

    incidents = pd.read_csv(
        artifacts / "business_incidents.csv"
    )

    controls = pd.read_csv(
        artifacts / "data_quality_controls.csv"
    )

    shipments["shipment_created_ts"] = pd.to_datetime(
        shipments["shipment_created_ts"]
    )

    support["created_ts"] = pd.to_datetime(
        support["created_ts"]
    )

    incidents["start_date"] = pd.to_datetime(
        incidents["start_date"]
    )

    incidents["end_date"] = pd.to_datetime(
        incidents["end_date"]
    )

    return (
        shipments,
        support,
        incidents,
        controls,
    )


def pct(series):
    if len(series) == 0:
        return np.nan

    return float(
        series.mean() * 100
    )


def logistics_data_trust(
    controls,
):
    relevant = controls[
        controls["domain"].isin(
            [
                "shipments",
                "tracking_events",
                "logistics",
            ]
        )
    ]

    failures = relevant[
        relevant["status"].eq(
            "FAIL"
        )
    ]

    return {
        "checks":
            int(len(relevant)),

        "failures":
            int(len(failures)),

        "trusted":
            bool(failures.empty),
    }


def shipment_scope(
    shipments,
    warehouse_id,
):
    return shipments[
        (
            shipments[
                "origin_warehouse_id"
            ].eq(
                warehouse_id
            )
        )
        | (
            shipments[
                "destination_warehouse_id"
            ].eq(
                warehouse_id
            )
        )
    ].copy()


def build_periods(
    scoped,
    start,
    end,
):
    incident_end = (
        end
        + pd.Timedelta(
            days=1
        )
        - pd.Timedelta(
            microseconds=1
        )
    )

    incident = scoped[
        scoped[
            "shipment_created_ts"
        ].between(
            start,
            incident_end,
        )
    ].copy()

    baseline_start = (
        start
        - pd.Timedelta(
            days=BASELINE_DAYS
        )
    )

    baseline_end = (
        start
        - pd.Timedelta(
            microseconds=1
        )
    )

    baseline = scoped[
        scoped[
            "shipment_created_ts"
        ].between(
            baseline_start,
            baseline_end,
        )
    ].copy()

    return (
        baseline,
        incident,
        baseline_start,
        baseline_end,
    )


def period_metrics(
    df,
):
    if df.empty:
        return {}

    return {
        "shipments":
            int(len(df)),

        "delay_pct":
            pct(
                df["delayed_flag"]
            ),

        "sla_pct":
            pct(
                df["sla_met"]
            ),

        "avg_load_pct":
            float(
                df[
                    "network_load_factor"
                ].mean()
                * 100
            ),

        "avg_transit_hours":
            float(
                df[
                    "actual_transit_hours"
                ].mean()
            ),

        "avg_distance_km":
            float(
                df[
                    "distance_km"
                ].mean()
            ),

        "cross_border_pct":
            pct(
                df[
                    "cross_border"
                ]
            ),

        "carriers":
            int(
                df[
                    "carrier_id"
                ].nunique()
            ),
    }


def carrier_analysis(
    baseline,
    incident,
):
    base = (
        baseline
        .groupby(
            [
                "carrier_id",
                "carrier_name",
            ],
            as_index=False,
        )
        .agg(
            baseline_shipments=(
                "shipment_id",
                "count",
            ),
            baseline_delay_pct=(
                "delayed_flag",
                lambda x:
                    float(
                        x.mean()
                        * 100
                    ),
            ),
        )
    )

    inc = (
        incident
        .groupby(
            [
                "carrier_id",
                "carrier_name",
            ],
            as_index=False,
        )
        .agg(
            incident_shipments=(
                "shipment_id",
                "count",
            ),
            incident_delay_pct=(
                "delayed_flag",
                lambda x:
                    float(
                        x.mean()
                        * 100
                    ),
            ),
        )
    )

    analysis = inc.merge(
        base,
        on=[
            "carrier_id",
            "carrier_name",
        ],
        how="left",
    )

    analysis[
        "baseline_delay_pct"
    ] = analysis[
        "baseline_delay_pct"
    ].fillna(
        baseline[
            "delayed_flag"
        ].mean()
        * 100
    )

    analysis[
        "delay_delta_pp"
    ] = (
        analysis[
            "incident_delay_pct"
        ]
        - analysis[
            "baseline_delay_pct"
        ]
    )

    analysis[
        "incident_share_pct"
    ] = (
        analysis[
            "incident_shipments"
        ]
        / analysis[
            "incident_shipments"
        ].sum()
        * 100
    )

    material = analysis[
        analysis[
            "delay_delta_pp"
        ] >= 25
    ]

    spread_ratio = (
        len(material)
        / len(analysis)
        if len(analysis)
        else 0
    )

    max_share = (
        float(
            analysis[
                "incident_share_pct"
            ].max()
        )
        if len(analysis)
        else 0
    )

    max_delta = (
        float(
            analysis[
                "delay_delta_pp"
            ].max()
        )
        if len(analysis)
        else 0
    )

    return (
        analysis
        .sort_values(
            "incident_shipments",
            ascending=False,
        ),
        spread_ratio,
        max_share,
        max_delta,
    )


def support_metrics(
    support,
    shipment_ids,
):
    cases = support[
        support[
            "shipment_id"
        ].isin(
            shipment_ids
        )
    ]

    if cases.empty:
        return {
            "cases": 0,
            "sla_pct": None,
            "avg_csat": None,
            "escalation_pct": None,
        }

    return {
        "cases":
            int(len(cases)),

        "sla_pct":
            round(
                pct(
                    cases[
                        "support_sla_met"
                    ]
                ),
                2,
            ),

        "avg_csat":
            round(
                float(
                    cases[
                        "csat_score"
                    ].mean()
                ),
                2,
            ),

        "escalation_pct":
            round(
                pct(
                    cases[
                        "escalated_flag"
                    ]
                ),
                2,
            ),
    }


def network_seasonality(
    shipments,
    start,
    end,
):
    incident_end = (
        end
        + pd.Timedelta(
            days=1
        )
        - pd.Timedelta(
            microseconds=1
        )
    )

    incident = shipments[
        shipments[
            "shipment_created_ts"
        ].between(
            start,
            incident_end,
        )
    ]

    baseline = shipments[
        shipments[
            "shipment_created_ts"
        ].between(
            start
            - pd.Timedelta(
                days=BASELINE_DAYS
            ),
            start
            - pd.Timedelta(
                microseconds=1
            ),
        )
    ]

    if (
        incident.empty
        or baseline.empty
    ):
        return 0.0

    return float(
        (
            incident[
                "delayed_flag"
            ].mean()
            - baseline[
                "delayed_flag"
            ].mean()
        )
        * 100
    )


def score_root_causes(
    baseline_metrics,
    incident_metrics,
    spread_ratio,
    max_carrier_share,
    max_carrier_delta,
    network_delay_delta,
    dq_trusted,
):
    load_delta = (
        incident_metrics[
            "avg_load_pct"
        ]
        - baseline_metrics[
            "avg_load_pct"
        ]
    )

    delay_delta = (
        incident_metrics[
            "delay_pct"
        ]
        - baseline_metrics[
            "delay_pct"
        ]
    )

    distance_delta = (
        incident_metrics[
            "avg_distance_km"
        ]
        - baseline_metrics[
            "avg_distance_km"
        ]
    )

    cross_border_delta = (
        incident_metrics[
            "cross_border_pct"
        ]
        - baseline_metrics[
            "cross_border_pct"
        ]
    )

    load_score = np.clip(
        load_delta
        / 30
        * 100,
        0,
        100,
    )

    delay_score = np.clip(
        delay_delta
        / 50
        * 100,
        0,
        100,
    )

    systemic_score = np.clip(
        spread_ratio
        * 100,
        0,
        100,
    )

    dq_score = (
        100
        if dq_trusted
        else 0
    )

    congestion_score = (
        load_score
        * 0.45
        + systemic_score
        * 0.25
        + delay_score
        * 0.20
        + dq_score
        * 0.10
    )

    concentration_score = np.clip(
        (
            max_carrier_share
            - 25
        )
        / 50
        * 100,
        0,
        100,
    )

    carrier_delta_score = np.clip(
        max_carrier_delta
        / 70
        * 100,
        0,
        100,
    )

    carrier_score = (
        concentration_score
        * 0.45
        + carrier_delta_score
        * 0.30
        + (
            100
            - systemic_score
        )
        * 0.25
    )

    distance_score = np.clip(
        abs(
            distance_delta
        )
        / 500
        * 100,
        0,
        100,
    )

    cross_border_score = np.clip(
        abs(
            cross_border_delta
        )
        / 25
        * 100,
        0,
        100,
    )

    route_mix_score = (
        distance_score
        * 0.65
        + cross_border_score
        * 0.35
    )

    seasonality_score = np.clip(
        network_delay_delta
        / 15
        * 100,
        0,
        100,
    )

    scores = {
        "Network Congestion / Warehouse Overload":
            round(
                float(
                    congestion_score
                ),
                2,
            ),

        "Carrier-Specific Performance":
            round(
                float(
                    carrier_score
                ),
                2,
            ),

        "Route / Distance Mix":
            round(
                float(
                    route_mix_score
                ),
                2,
            ),

        "Network Seasonality":
            round(
                float(
                    seasonality_score
                ),
                2,
            ),
    }

    return (
        scores,
        {
            "load_delta_pp":
                round(
                    float(
                        load_delta
                    ),
                    2,
                ),

            "delay_delta_pp":
                round(
                    float(
                        delay_delta
                    ),
                    2,
                ),

            "distance_delta_km":
                round(
                    float(
                        distance_delta
                    ),
                    1,
                ),

            "cross_border_delta_pp":
                round(
                    float(
                        cross_border_delta
                    ),
                    2,
                ),

            "network_delay_delta_pp":
                round(
                    float(
                        network_delay_delta
                    ),
                    2,
                ),
        },
    )


def confidence_score(
    scores,
    dq_trusted,
):
    ordered = sorted(
        scores.values(),
        reverse=True,
    )

    primary = ordered[0]

    second = (
        ordered[1]
        if len(ordered) > 1
        else 0
    )

    margin = (
        primary
        - second
    )

    confidence = (
        primary
        * 0.65
        + (
            100
            if dq_trusted
            else 0
        )
        * 0.20
        + min(
            margin * 2,
            100,
        )
        * 0.15
    )

    return round(
        float(
            np.clip(
                confidence,
                0,
                99,
            )
        ),
        2,
    )


def build_report(
    shipments,
    support,
    incident,
    controls,
):
    warehouse_id = (
        incident[
            "warehouse_id"
        ]
    )

    start = incident[
        "start_date"
    ]

    end = incident[
        "end_date"
    ]

    scoped = shipment_scope(
        shipments,
        warehouse_id,
    )

    (
        baseline,
        affected,
        baseline_start,
        baseline_end,
    ) = build_periods(
        scoped,
        start,
        end,
    )

    if baseline.empty:
        raise ValueError(
            "RCA baseline contains no shipments."
        )

    if affected.empty:
        raise ValueError(
            "RCA incident window contains no shipments."
        )

    baseline_metrics = (
        period_metrics(
            baseline
        )
    )

    incident_metrics = (
        period_metrics(
            affected
        )
    )

    (
        carrier_table,
        spread_ratio,
        max_carrier_share,
        max_carrier_delta,
    ) = carrier_analysis(
        baseline,
        affected,
    )

    data_health = (
        logistics_data_trust(
            controls
        )
    )

    network_delta = (
        network_seasonality(
            shipments,
            start,
            end,
        )
    )

    (
        scores,
        deltas,
    ) = score_root_causes(
        baseline_metrics,
        incident_metrics,
        spread_ratio,
        max_carrier_share,
        max_carrier_delta,
        network_delta,
        data_health[
            "trusted"
        ],
    )

    primary_cause = max(
        scores,
        key=scores.get,
    )

    confidence = (
        confidence_score(
            scores,
            data_health[
                "trusted"
            ],
        )
    )

    baseline_support = (
        support_metrics(
            support,
            baseline[
                "shipment_id"
            ],
        )
    )

    incident_support = (
        support_metrics(
            support,
            affected[
                "shipment_id"
            ],
        )
    )

    report = {
        "incident_id":
            incident[
                "candidate_incident_id"
            ],

        "classification":
            "BUSINESS_INCIDENT",

        "location":
            (
                f"{incident['city']}, "
                f"{incident['country']}"
            ),

        "warehouse_id":
            warehouse_id,

        "detected_window":
            {
                "start":
                    str(
                        start.date()
                    ),

                "end":
                    str(
                        end.date()
                    ),
            },

        "baseline_window":
            {
                "start":
                    str(
                        baseline_start.date()
                    ),

                "end":
                    str(
                        baseline_end.date()
                    ),
            },

        "primary_root_cause":
            primary_cause,

        "confidence_score":
            confidence,

        "data_trust":
            data_health,

        "baseline_metrics":
            baseline_metrics,

        "incident_metrics":
            incident_metrics,

        "metric_deltas":
            deltas,

        "root_cause_scores":
            scores,

        "carrier_spread_pct":
            round(
                spread_ratio
                * 100,
                2,
            ),

        "baseline_support":
            baseline_support,

        "incident_support":
            incident_support,

        "evidence": [
            (
                "Warehouse/network load "
                f"increased by "
                f"{deltas['load_delta_pp']:+.2f} pp."
            ),
            (
                "Delay rate changed by "
                f"{deltas['delay_delta_pp']:+.2f} pp."
            ),
            (
                f"{spread_ratio * 100:.1f}% "
                "of carriers present in the incident "
                "showed material delay deterioration."
            ),
            (
                "Logistics Data Quality controls "
                + (
                    "passed."
                    if data_health[
                        "trusted"
                    ]
                    else "did not pass."
                )
            ),
        ],
    }

    return (
        report,
        carrier_table,
    )


def save_outputs(
    reports,
    carrier_tables,
):
    artifacts = (
        PROJECT_ROOT
        / "artifacts"
    )

    artifacts.mkdir(
        parents=True,
        exist_ok=True,
    )

    (
        artifacts
        / "root_cause_report.json"
    ).write_text(
        json.dumps(
            reports,
            indent=2,
        ),
        encoding="utf-8",
    )

    all_carriers = []

    for incident_id, table in carrier_tables:
        temp = table.copy()

        temp[
            "incident_id"
        ] = incident_id

        all_carriers.append(
            temp
        )

    if all_carriers:
        pd.concat(
            all_carriers,
            ignore_index=True,
        ).to_csv(
            artifacts
            / "root_cause_carrier_analysis.csv",
            index=False,
        )


def main():
    print("=" * 72)
    print(
        "AEGIS ROOT CAUSE ANALYSIS ENGINE"
    )
    print("=" * 72)

    print()
    print(
        "Business incident candidates "
        "are analyzed independently."
    )

    print(
        "Ground-truth incident metadata "
        "is NOT used."
    )

    (
        shipments,
        support,
        incidents,
        controls,
    ) = load_inputs()

    if incidents.empty:
        print()
        print(
            "No business incident candidates "
            "available for RCA."
        )
        return

    reports = []
    carrier_tables = []

    for _, incident in (
        incidents.iterrows()
    ):
        (
            report,
            carrier_table,
        ) = build_report(
            shipments,
            support,
            incident,
            controls,
        )

        reports.append(
            report
        )

        carrier_tables.append(
            (
                report[
                    "incident_id"
                ],
                carrier_table,
            )
        )

    save_outputs(
        reports,
        carrier_tables,
    )

    print()
    print("=" * 72)
    print(
        "ROOT CAUSE ANALYSIS SUMMARY"
    )
    print("=" * 72)

    for report in reports:
        print()

        print(
            f"Incident:          "
            f"{report['incident_id']}"
        )

        print(
            f"Classification:    "
            f"{report['classification']}"
        )

        print(
            f"Location:          "
            f"{report['location']}"
        )

        print(
            f"Detected window:   "
            f"{report['detected_window']['start']} "
            f"to "
            f"{report['detected_window']['end']}"
        )

        print()

        print(
            f"Primary cause:     "
            f"{report['primary_root_cause']}"
        )

        print(
            f"Confidence:        "
            f"{report['confidence_score']:.2f}%"
        )

        print()

        print(
            "ROOT CAUSE SCORES"
        )

        for cause, score in sorted(
            report[
                "root_cause_scores"
            ].items(),
            key=lambda item:
                item[1],
            reverse=True,
        ):
            print(
                f"{cause:<38} "
                f"{score:>6.2f}"
            )

        print()

        baseline = report[
            "baseline_metrics"
        ]

        incident = report[
            "incident_metrics"
        ]

        print(
            "OPERATIONAL EVIDENCE"
        )

        print(
            f"Delay rate:        "
            f"{baseline['delay_pct']:.2f}% "
            f"-> "
            f"{incident['delay_pct']:.2f}%"
        )

        print(
            f"SLA rate:          "
            f"{baseline['sla_pct']:.2f}% "
            f"-> "
            f"{incident['sla_pct']:.2f}%"
        )

        print(
            f"Average load:      "
            f"{baseline['avg_load_pct']:.2f}% "
            f"-> "
            f"{incident['avg_load_pct']:.2f}%"
        )

        print(
            f"Transit time:      "
            f"{baseline['avg_transit_hours']:.2f} h "
            f"-> "
            f"{incident['avg_transit_hours']:.2f} h"
        )

        print()

        print(
            f"Multi-carrier spread: "
            f"{report['carrier_spread_pct']:.2f}%"
        )

        print(
            f"Logistics DQ passed: "
            f"{report['data_trust']['trusted']}"
        )

        support_before = report[
            "baseline_support"
        ]

        support_after = report[
            "incident_support"
        ]

        print()
        print(
            "CUSTOMER IMPACT"
        )

        print(
            f"Support cases:     "
            f"{support_after['cases']}"
        )

        if (
            support_before[
                "sla_pct"
            ] is not None
            and support_after[
                "sla_pct"
            ] is not None
        ):
            print(
                f"Support SLA:       "
                f"{support_before['sla_pct']:.2f}% "
                f"-> "
                f"{support_after['sla_pct']:.2f}%"
            )

        if (
            support_before[
                "avg_csat"
            ] is not None
            and support_after[
                "avg_csat"
            ] is not None
        ):
            print(
                f"Average CSAT:      "
                f"{support_before['avg_csat']:.2f} "
                f"-> "
                f"{support_after['avg_csat']:.2f}"
            )

        print()
        print(
            "EVIDENCE-BASED CONCLUSION"
        )

        print(
            f"{report['primary_root_cause']} "
            f"is the strongest explanatory factor."
        )

        print(
            "The anomaly is treated as operational "
            "because logistics Data Quality controls "
            "remain valid."
        )

        print(
            "-" * 72
        )

    print()
    print(
        "RCA outputs created:"
    )

    print(
        "  artifacts/root_cause_report.json"
    )

    print(
        "  artifacts/root_cause_carrier_analysis.csv"
    )

    print()

    print(
        "No ground-truth file was read."
    )


if __name__ == "__main__":
    main()
