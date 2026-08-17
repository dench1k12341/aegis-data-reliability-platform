import json
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

from src.utils.config import PROJECT_ROOT


ENV_PATH = PROJECT_ROOT / ".env"

PROMPTS_PATH = (
    PROJECT_ROOT
    / "artifacts"
    / "ai_prompt_packs.json"
)

OUTPUT_JSON = (
    PROJECT_ROOT
    / "artifacts"
    / "ai_executive_reports.json"
)

OUTPUT_MD = (
    PROJECT_ROOT
    / "artifacts"
    / "ai_executive_reports.md"
)


def load_environment():
    load_dotenv(ENV_PATH, override=True)

    api_key = os.getenv(
        "OPENAI_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is missing. "
            "Add it to the local .env file."
        )

    model = os.getenv(
        "AEGIS_AI_MODEL",
        "gpt-5.6",
    )

    return (
        api_key,
        model,
    )


def load_prompt_packs():
    if not PROMPTS_PATH.exists():
        raise FileNotFoundError(
            "ai_prompt_packs.json not found. "
            "Run build_grounded_prompts first."
        )

    packs = json.loads(
        PROMPTS_PATH.read_text(
            encoding="utf-8"
        )
    )

    if not packs:
        raise ValueError(
            "No AI prompt packs found."
        )

    return packs


def call_model(
    client,
    model,
    pack,
):
    response = (
        client.responses.create(
            model=model,
            instructions=pack[
                "system_prompt"
            ],
            input=pack[
                "user_prompt"
            ],
            store=False,
        )
    )

    text = (
        response.output_text
        or ""
    ).strip()

    if not text:
        raise RuntimeError(
            "Model returned an empty response."
        )

    return {
        "incident_id":
            pack[
                "incident_id"
            ],

        "model":
            model,

        "response_id":
            response.id,

        "report":
            text,

        "grounded_only":
            pack[
                "guardrails"
            ][
                "grounded_only"
            ],

        "external_knowledge_allowed":
            pack[
                "guardrails"
            ][
                "allow_external_knowledge"
            ],
    }


def validate_report(
    result,
    pack,
):
    report = result[
        "report"
    ].lower()

    required_concepts = [
        "incident",
        "data",
        "root cause",
        "business impact",
        "recommended",
        "confidence",
    ]

    missing = [
        concept
        for concept
        in required_concepts
        if concept
        not in report
    ]

    warnings = []

    if missing:
        warnings.append(
            "Missing expected concepts: "
            + ", ".join(
                missing
            )
        )

    context = pack[
        "evidence_context"
    ]

    classification = context[
        "incident"
    ][
        "classification"
    ]

    trust = context[
        "data_reliability"
    ][
        "data_trust_status"
    ]

    if (
        classification
        == "DATA_INCIDENT"
        and "failed"
        not in report
        and "not trust"
        not in report
        and "unreliable"
        not in report
    ):
        warnings.append(
            "Data incident report may not "
            "clearly communicate failed data trust."
        )

    if (
        classification
        == "BUSINESS_INCIDENT"
        and trust
        == "PASSED"
        and "passed"
        not in report
        and "trustworthy"
        not in report
        and "valid"
        not in report
    ):
        warnings.append(
            "Business incident report may not "
            "clearly communicate passed data trust."
        )

    return warnings


def build_markdown(
    results,
):
    lines = [
        "# Aegis AI Executive Incident Reports",
        "",
        (
            "Generated from deterministic "
            "Aegis evidence packages."
        ),
        "",
        (
            "The LLM does not perform incident "
            "detection or root-cause discovery."
        ),
        "",
        "---",
        "",
    ]

    for result in results:
        lines.extend(
            [
                (
                    f"# "
                    f"{result['incident_id']}"
                ),
                "",
                (
                    f"**Model:** "
                    f"{result['model']}"
                ),
                "",
                result[
                    "report"
                ],
                "",
                "---",
                "",
            ]
        )

    return "\n".join(
        lines
    )


def save_outputs(
    results,
):
    OUTPUT_JSON.write_text(
        json.dumps(
            results,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    OUTPUT_MD.write_text(
        build_markdown(
            results
        ),
        encoding="utf-8",
    )


def main():
    print("=" * 72)
    print(
        "AEGIS AI DECISION ASSISTANT - LIVE LLM"
    )
    print("=" * 72)

    try:
        (
            api_key,
            model,
        ) = load_environment()

        packs = load_prompt_packs()

        client = OpenAI(
            api_key=api_key
        )

        print()
        print(
            f"Model:              "
            f"{model}"
        )

        print(
            f"Grounded incidents: "
            f"{len(packs)}"
        )

        print(
            "External knowledge: DISABLED "
            "by prompt policy"
        )

        print()
        print(
            "Calling model..."
        )

        results = []

        for index, pack in enumerate(
            packs,
            start=1,
        ):
            incident_id = pack[
                "incident_id"
            ]

            print()
            print(
                f"[{index}/{len(packs)}] "
                f"{incident_id}"
            )

            result = call_model(
                client,
                model,
                pack,
            )

            warnings = validate_report(
                result,
                pack,
            )

            result[
                "validation_warnings"
            ] = warnings

            results.append(
                result
            )

            print(
                "Generation:         OK"
            )

            print(
                f"Validation warnings:"
                f" {len(warnings)}"
            )

        save_outputs(
            results
        )

        print()
        print("=" * 72)
        print(
            "LIVE AI SUMMARY"
        )
        print("=" * 72)

        print()

        print(
            f"Reports generated:  "
            f"{len(results)}"
        )

        print(
            f"Model:              "
            f"{model}"
        )

        total_warnings = sum(
            len(
                result[
                    "validation_warnings"
                ]
            )
            for result
            in results
        )

        print(
            f"Validation warnings:"
            f" {total_warnings}"
        )

        for result in results:
            print()
            print(
                result[
                    "incident_id"
                ]
            )

            print(
                "-" * 72
            )

            preview = (
                result[
                    "report"
                ]
                .replace(
                    "\n",
                    " ",
                )
            )

            if len(
                preview
            ) > 500:
                preview = (
                    preview[:500]
                    + "..."
                )

            print(
                preview
            )

        print()

        print(
            "Outputs created:"
        )

        print(
            f"  {OUTPUT_JSON}"
        )

        print(
            f"  {OUTPUT_MD}"
        )

        print()

        print(
            "Live AI Decision Assistant "
            "completed successfully."
        )

    except Exception as exc:
        print()
        print(
            "AEGIS AI CALL FAILED"
        )

        print(
            "-" * 72
        )

        print(
            str(
                exc
            )
        )

        sys.exit(
            1
        )


if __name__ == "__main__":
    main()

