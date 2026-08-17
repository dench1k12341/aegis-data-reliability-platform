import json

from src.utils.config import PROJECT_ROOT


SYSTEM_RULES = [
    (
        "Use only facts contained in the supplied "
        "Aegis evidence package."
    ),
    (
        "Do not invent metrics, causes, dates, "
        "locations or remediation outcomes."
    ),
    (
        "Clearly distinguish DATA_INCIDENT from "
        "BUSINESS_INCIDENT."
    ),
    (
        "If data_trust_status is FAILED, warn that "
        "affected KPIs must not be trusted."
    ),
    (
        "If data_trust_status is PASSED, do not "
        "attribute the business anomaly to bad data "
        "without additional evidence."
    ),
    (
        "Treat confidence_score as model confidence "
        "inside the synthetic Aegis evaluation framework, "
        "not universal real-world accuracy."
    ),
    (
        "Do not claim that recommended actions have "
        "already solved the incident."
    ),
    (
        "If evidence is insufficient, explicitly say "
        "that the evidence is insufficient."
    ),
]


def load_decision_briefs():
    path = (
        PROJECT_ROOT
        / "artifacts"
        / "decision_briefs.json"
    )

    if not path.exists():
        raise FileNotFoundError(
            "decision_briefs.json not found. "
            "Run the Decision Intelligence layer first."
        )

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def validate_brief(
    brief,
):
    required = [
        "incident_id",
        "classification",
        "severity",
        "confidence_score",
        "data_trust_status",
        "primary_cause",
        "business_metric",
        "business_impact",
        "evidence",
        "decision_status",
        "decision_label",
        "executive_summary",
        "recommended_actions",
    ]

    missing = [
        field
        for field in required
        if field not in brief
    ]

    if missing:
        raise ValueError(
            f"{brief.get('incident_id', 'UNKNOWN')}: "
            f"missing required fields: "
            f"{', '.join(missing)}"
        )

    if brief[
        "classification"
    ] not in {
        "DATA_INCIDENT",
        "BUSINESS_INCIDENT",
    }:
        raise ValueError(
            "Unsupported incident classification: "
            f"{brief['classification']}"
        )

    if brief[
        "data_trust_status"
    ] not in {
        "PASSED",
        "FAILED",
    }:
        raise ValueError(
            "Unsupported data trust status: "
            f"{brief['data_trust_status']}"
        )

    confidence = float(
        brief[
            "confidence_score"
        ]
    )

    if not (
        0
        <= confidence
        <= 100
    ):
        raise ValueError(
            "Confidence score must be "
            "between 0 and 100."
        )


def build_grounded_context(
    brief,
):
    return {
        "incident": {
            "incident_id":
                brief[
                    "incident_id"
                ],

            "classification":
                brief[
                    "classification"
                ],

            "severity":
                brief[
                    "severity"
                ],

            "domain":
                brief[
                    "domain"
                ],

            "location":
                brief[
                    "location"
                ],

            "detected_window":
                brief[
                    "detected_window"
                ],

            "confidence_score":
                brief[
                    "confidence_score"
                ],
        },

        "data_reliability": {
            "data_trust_status":
                brief[
                    "data_trust_status"
                ],
        },

        "analysis": {
            "primary_cause":
                brief[
                    "primary_cause"
                ],

            "business_metric":
                brief[
                    "business_metric"
                ],

            "business_impact":
                brief[
                    "business_impact"
                ],

            "key_metrics":
                brief.get(
                    "key_metrics",
                    {},
                ),

            "evidence":
                brief[
                    "evidence"
                ],
        },

        "decision": {
            "decision_status":
                brief[
                    "decision_status"
                ],

            "decision_label":
                brief[
                    "decision_label"
                ],

            "recommended_actions":
                brief[
                    "recommended_actions"
                ],
        },
    }


def build_system_prompt():
    rules = "\n".join(
        f"{index}. {rule}"
        for index, rule
        in enumerate(
            SYSTEM_RULES,
            start=1,
        )
    )

    return (
        "You are Aegis Decision Assistant, "
        "an evidence-grounded analytics assistant.\n\n"
        "Your job is to explain detected incidents "
        "to operations, analytics and management teams.\n\n"
        "STRICT RULES:\n"
        f"{rules}\n\n"
        "RESPONSE STRUCTURE:\n"
        "1. Incident Summary\n"
        "2. What Happened\n"
        "3. Data Trust Assessment\n"
        "4. Likely Root Cause\n"
        "5. Business Impact\n"
        "6. Recommended Actions\n"
        "7. Confidence & Limitations\n"
    )


def build_user_prompt(
    context,
):
    evidence_json = json.dumps(
        context,
        indent=2,
        ensure_ascii=False,
    )

    return (
        "Analyze the following Aegis evidence package.\n\n"
        "Use no information outside this package.\n\n"
        "EVIDENCE PACKAGE:\n"
        f"{evidence_json}\n\n"
        "Produce a concise executive incident brief "
        "following the required response structure."
    )


def build_prompt_pack(
    brief,
):
    validate_brief(
        brief
    )

    context = (
        build_grounded_context(
            brief
        )
    )

    return {
        "incident_id":
            brief[
                "incident_id"
            ],

        "system_prompt":
            build_system_prompt(),

        "user_prompt":
            build_user_prompt(
                context
            ),

        "evidence_context":
            context,

        "guardrails": {
            "grounded_only":
                True,

            "allow_external_knowledge":
                False,

            "allow_metric_invention":
                False,

            "allow_root_cause_invention":
                False,

            "require_data_trust_statement":
                True,

            "require_limitations":
                True,
        },
    }


def build_all_prompt_packs(
    briefs,
):
    return [
        build_prompt_pack(
            brief
        )
        for brief in briefs
    ]


def build_preview_markdown(
    packs,
):
    lines = [
        "# Aegis AI Decision Assistant",
        "",
        "Grounded prompt preview.",
        "",
        (
            "The LLM is restricted to deterministic "
            "Aegis evidence packages."
        ),
        "",
    ]

    for pack in packs:
        context = pack[
            "evidence_context"
        ]

        incident = context[
            "incident"
        ]

        reliability = context[
            "data_reliability"
        ]

        analysis = context[
            "analysis"
        ]

        decision = context[
            "decision"
        ]

        lines.extend(
            [
                (
                    f"## "
                    f"{incident['incident_id']}"
                ),
                "",
                (
                    f"**Classification:** "
                    f"{incident['classification']}"
                ),
                "",
                (
                    f"**Severity:** "
                    f"{incident['severity']}"
                ),
                "",
                (
                    f"**Confidence:** "
                    f"{incident['confidence_score']:.2f}%"
                ),
                "",
                (
                    f"**Data Trust:** "
                    f"{reliability['data_trust_status']}"
                ),
                "",
                (
                    f"**Primary Cause:** "
                    f"{analysis['primary_cause']}"
                ),
                "",
                (
                    f"**Decision:** "
                    f"{decision['decision_label']}"
                ),
                "",
                "### Prompt Guardrails",
                "",
                "- Evidence package only",
                "- No invented metrics",
                "- No invented root causes",
                "- Data trust statement required",
                "- Limitations required",
                "",
                "---",
                "",
            ]
        )

    return "\n".join(
        lines
    )


def save_outputs(
    packs,
):
    artifacts = (
        PROJECT_ROOT
        / "artifacts"
    )

    json_path = (
        artifacts
        / "ai_prompt_packs.json"
    )

    markdown_path = (
        artifacts
        / "ai_prompt_preview.md"
    )

    json_path.write_text(
        json.dumps(
            packs,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    markdown_path.write_text(
        build_preview_markdown(
            packs
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
        "AEGIS AI DECISION ASSISTANT"
    )
    print("=" * 72)

    print()
    print(
        "Building grounded LLM prompt packs."
    )

    print(
        "No external model is called "
        "at this stage."
    )

    briefs = (
        load_decision_briefs()
    )

    packs = (
        build_all_prompt_packs(
            briefs
        )
    )

    (
        json_path,
        markdown_path,
    ) = save_outputs(
        packs
    )

    print()
    print("=" * 72)
    print(
        "AI GROUNDING SUMMARY"
    )
    print("=" * 72)

    print()

    print(
        f"Incidents prepared: "
        f"{len(packs)}"
    )

    print(
        f"Guardrail rules:    "
        f"{len(SYSTEM_RULES)}"
    )

    for pack in packs:
        context = pack[
            "evidence_context"
        ]

        incident = context[
            "incident"
        ]

        reliability = context[
            "data_reliability"
        ]

        analysis = context[
            "analysis"
        ]

        print()
        print(
            incident[
                "incident_id"
            ]
        )

        print(
            "-" * 72
        )

        print(
            f"Classification:    "
            f"{incident['classification']}"
        )

        print(
            f"Severity:          "
            f"{incident['severity']}"
        )

        print(
            f"Confidence:        "
            f"{incident['confidence_score']:.2f}%"
        )

        print(
            f"Data trust:        "
            f"{reliability['data_trust_status']}"
        )

        print(
            f"Grounded cause:    "
            f"{analysis['primary_cause']}"
        )

        print(
            "External knowledge: DISABLED"
        )

        print(
            "Metric invention:   DISABLED"
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
        "AI grounding layer completed successfully."
    )


if __name__ == "__main__":
    main()
