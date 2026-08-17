import json
import os
import sys

from dotenv import load_dotenv
from groq import Groq

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
    / "ai_executive_reports_groq.json"
)

OUTPUT_MD = (
    PROJECT_ROOT
    / "artifacts"
    / "ai_executive_reports_groq.md"
)


PREFERRED_MODELS = [
    "openai/gpt-oss-120b",
    "qwen/qwen3-32b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]


def load_environment():
    load_dotenv(
        ENV_PATH,
        override=True,
    )

    api_key = os.getenv(
        "GROQ_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is missing. "
            "Add it to the local .env file."
        )

    requested_model = (
        os.getenv(
            "GROQ_MODEL",
            "",
        )
        .strip()
    )

    return (
        api_key,
        requested_model,
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


def get_available_models(
    client,
):
    response = (
        client.models.list()
    )

    models = sorted(
        model.id
        for model
        in response.data
    )

    return models


def select_model(
    available_models,
    requested_model,
):
    if requested_model:
        if (
            requested_model
            not in available_models
        ):
            raise RuntimeError(
                f"Requested GROQ_MODEL "
                f"'{requested_model}' "
                "is not available."
            )

        return requested_model

    for model in PREFERRED_MODELS:
        if model in available_models:
            return model

    if not available_models:
        raise RuntimeError(
            "Groq returned no available models."
        )

    return available_models[0]


def call_model(
    client,
    model,
    pack,
):
    response = (
        client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content":
                        pack[
                            "system_prompt"
                        ],
                },
                {
                    "role": "user",
                    "content":
                        pack[
                            "user_prompt"
                        ],
                },
            ],
            temperature=0.0,
            max_tokens=1200,
        )
    )

    text = (
        response
        .choices[0]
        .message
        .content
        or ""
    ).strip()

    if not text:
        raise RuntimeError(
            "Groq model returned "
            "an empty response."
        )

    return {
        "incident_id":
            pack[
                "incident_id"
            ],

        "provider":
            "Groq",

        "model":
            model,

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
    import re
    from datetime import date

    report_original = result["report"]

    translation_table = str.maketrans(
        {
            "\u2010": "-",
            "\u2011": "-",
            "\u2012": "-",
            "\u2013": "-",
            "\u2014": "-",
            "\u2212": "-",
            "\u00a0": " ",
            "\u202f": " ",
        }
    )

    report_normalized = (
        report_original
        .translate(
            translation_table
        )
    )

    report = (
        report_normalized
        .lower()
    )

    warnings = []

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

    classification = incident[
        "classification"
    ]

    trust = reliability[
        "data_trust_status"
    ]

    incident_id = incident[
        "incident_id"
    ]

    primary_cause = analysis[
        "primary_cause"
    ]

    start_date = incident[
        "detected_window"
    ][
        "start"
    ]

    end_date = incident[
        "detected_window"
    ][
        "end"
    ]

    # -------------------------------------------------
    # Required grounded facts
    # -------------------------------------------------

    if incident_id.lower() not in report:
        warnings.append(
            "Incident ID is missing from report."
        )

    classification_variants = {
        classification.lower(),
        classification.lower().replace(
            "_",
            " ",
        ),
    }

    if not any(
        value in report
        for value
        in classification_variants
    ):
        warnings.append(
            "Incident classification is missing "
            "or not stated clearly."
        )

    if (
        primary_cause.lower()
        not in report
    ):
        warnings.append(
            "Grounded primary root cause "
            "is missing from report."
        )

    if start_date not in report_normalized:
        warnings.append(
            "Detected incident start date "
            "is missing from report."
        )

    if end_date not in report_normalized:
        warnings.append(
            "Detected incident end date "
            "is missing from report."
        )

    # -------------------------------------------------
    # Data Trust validation
    # -------------------------------------------------

    if (
        classification
        == "DATA_INCIDENT"
        and trust
        == "FAILED"
    ):
        trust_language = [
            "failed",
            "unreliable",
            "not trust",
            "should not be trusted",
            "cannot be trusted",
            "do not trust",
        ]

        if not any(
            phrase in report
            for phrase
            in trust_language
        ):
            warnings.append(
                "DATA_INCIDENT does not clearly "
                "communicate failed data trust."
            )

    if (
        classification
        == "BUSINESS_INCIDENT"
        and trust
        == "PASSED"
    ):
        trust_language = [
            "passed",
            "trustworthy",
            "data is valid",
            "data remain valid",
            "data remains valid",
            "data quality controls passed",
        ]

        if not any(
            phrase in report
            for phrase
            in trust_language
        ):
            warnings.append(
                "BUSINESS_INCIDENT does not clearly "
                "communicate passed data trust."
            )

    # -------------------------------------------------
    # Confidence validation
    # -------------------------------------------------

    expected_confidence = float(
        incident[
            "confidence_score"
        ]
    )

    confidence_text = (
        f"{expected_confidence:.0f}"
    )

    if confidence_text not in report:
        warnings.append(
            "Expected confidence score "
            "is not clearly stated."
        )

    # -------------------------------------------------
    # Duration hallucination detection
    # -------------------------------------------------

    start_obj = date.fromisoformat(
        start_date
    )

    end_obj = date.fromisoformat(
        end_date
    )

    expected_days = (
        end_obj
        - start_obj
    ).days + 1

    word_numbers = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "eleven": 11,
        "twelve": 12,
        "thirteen": 13,
        "fourteen": 14,
        "fifteen": 15,
        "sixteen": 16,
        "seventeen": 17,
        "eighteen": 18,
        "nineteen": 19,
        "twenty": 20,
    }

    numeric_matches = re.findall(
        r"\b(\d+)[-\s]?day(?:s)?\s+"
        r"(?:window|period)\b",
        report,
    )

    for value in numeric_matches:
        stated_days = int(
            value
        )

        if stated_days != expected_days:
            warnings.append(
                "Incorrect incident duration: "
                f"report says {stated_days} days, "
                f"evidence implies {expected_days} days."
            )

    word_pattern = (
        r"\b("
        + "|".join(
            word_numbers.keys()
        )
        + r")[-\s]day\s+"
        r"(?:window|period)\b"
    )

    word_matches = re.findall(
        word_pattern,
        report,
    )

    for value in word_matches:
        stated_days = (
            word_numbers[
                value
            ]
        )

        if stated_days != expected_days:
            warnings.append(
                "Incorrect incident duration: "
                f"report says {stated_days} days, "
                f"evidence implies {expected_days} days."
            )

    # -------------------------------------------------
    # Unsupported certainty language
    # -------------------------------------------------

    dangerous_phrases = [
        "guaranteed",
        "proven with certainty",
        "100% certain",
        "definitively proven",
    ]

    for phrase in dangerous_phrases:
        if phrase in report:
            warnings.append(
                "Unsupported certainty language: "
                f"'{phrase}'."
            )

    return warnings


def correct_report(
    client,
    model,
    pack,
    original_report,
    warnings,
):
    warning_text = "\n".join(
        f"- {warning}"
        for warning in warnings
    )

    correction_prompt = (
        "You previously generated the executive incident "
        "report shown below.\n\n"
        "The deterministic Aegis factual validator found "
        "the following issues:\n\n"
        f"{warning_text}\n\n"
        "ORIGINAL REPORT:\n"
        f"{original_report}\n\n"
        "Revise the report using ONLY the supplied Aegis "
        "evidence package.\n\n"
        "CORRECTION RULES:\n"
        "1. Correct every validator issue.\n"
        "2. Do not introduce new facts or metrics.\n"
        "3. Preserve the required seven-section structure.\n"
        "4. Preserve the incident classification.\n"
        "5. Preserve the data-trust assessment.\n"
        "6. Preserve grounded root-cause conclusions.\n"
        "7. If mentioning duration, calculate calendar days "
        "inclusively from the supplied start and end dates.\n\n"
        f"{pack['user_prompt']}"
    )

    response = (
        client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        pack["system_prompt"]
                        + "\n\n"
                        "You are performing a factual "
                        "correction pass. Fix only issues "
                        "identified by the validator and "
                        "remain fully grounded."
                    ),
                },
                {
                    "role": "user",
                    "content":
                        correction_prompt,
                },
            ],
            temperature=0.0,
            max_tokens=1200,
        )
    )

    text = (
        response
        .choices[0]
        .message
        .content
        or ""
    ).strip()

    if not text:
        raise RuntimeError(
            "Groq correction pass returned "
            "an empty response."
        )

    return text


def build_markdown(
    results,
):
    lines = [
        "# Aegis AI Executive Incident Reports",
        "",
        "**Provider:** Groq",
        "",
        (
            "Reports are generated only from "
            "deterministic Aegis evidence packages."
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
        "AEGIS AI DECISION ASSISTANT - GROQ"
    )
    print("=" * 72)

    try:
        (
            api_key,
            requested_model,
        ) = load_environment()

        packs = (
            load_prompt_packs()
        )

        client = Groq(
            api_key=api_key
        )

        print()
        print(
            "Checking available Groq models..."
        )

        available_models = (
            get_available_models(
                client
            )
        )

        print(
            f"Models available:    "
            f"{len(available_models)}"
        )

        model = select_model(
            available_models,
            requested_model,
        )

        print(
            f"Selected model:      "
            f"{model}"
        )

        print(
            f"Grounded incidents:  "
            f"{len(packs)}"
        )

        print(
            "External knowledge:  DISABLED "
            "by prompt policy"
        )

        print()
        print(
            "Calling Groq..."
        )

        results = []

        for index, pack in enumerate(
            packs,
            start=1,
        ):
            incident_id = (
                pack[
                    "incident_id"
                ]
            )

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

            original_report = (
                result[
                    "report"
                ]
            )

            initial_warnings = (
                validate_report(
                    result,
                    pack,
                )
            )

            result[
                "original_report"
            ] = original_report

            result[
                "initial_validation_warnings"
            ] = initial_warnings

            result[
                "self_correction_attempted"
            ] = False

            print(
                "Generation:          OK"
            )

            print(
                f"Initial warnings:   "
                f"{len(initial_warnings)}"
            )

            if initial_warnings:
                print(
                    "Self-correction:    RUNNING"
                )

                corrected_report = (
                    correct_report(
                        client,
                        model,
                        pack,
                        original_report,
                        initial_warnings,
                    )
                )

                result[
                    "report"
                ] = corrected_report

                result[
                    "self_correction_attempted"
                ] = True

                final_warnings = (
                    validate_report(
                        result,
                        pack,
                    )
                )

                print(
                    "Self-correction:    COMPLETED"
                )

            else:
                final_warnings = []

                print(
                    "Self-correction:    NOT REQUIRED"
                )

            result[
                "validation_warnings"
            ] = final_warnings

            results.append(
                result
            )

            print(
                f"Final warnings:     "
                f"{len(final_warnings)}"
            )

        save_outputs(
            results
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

        print()
        print("=" * 72)
        print(
            "GROQ AI SUMMARY"
        )
        print("=" * 72)

        print()

        print(
            f"Reports generated:   "
            f"{len(results)}"
        )

        print(
            f"Provider:            "
            f"Groq"
        )

        print(
            f"Model:               "
            f"{model}"
        )

        print(
            f"Validation warnings: "
            f"{total_warnings}"
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
                    " "
                )
            )

            if len(preview) > 500:
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
            "Groq AI Decision Assistant "
            "completed successfully."
        )

    except Exception as exc:
        print()
        print(
            "AEGIS GROQ CALL FAILED"
        )

        print(
            "-" * 72
        )

        print(
            str(exc)
        )

        sys.exit(1)


if __name__ == "__main__":
    main()

