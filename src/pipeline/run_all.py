import argparse
import subprocess
import sys
import time
from pathlib import Path

from src.utils.config import PROJECT_ROOT


PIPELINE_STEPS = [
    {
        "name": "Generate master data",
        "module": "src.generate.generate_master_data",
    },
    {
        "name": "Generate commerce data",
        "module": "src.generate.generate_commerce_data",
    },
    {
        "name": "Generate logistics data",
        "module": "src.generate.generate_logistics_data",
    },
    {
        "name": "Generate support data",
        "module": "src.generate.generate_support_data",
    },
    {
        "name": "Generate app events",
        "module": "src.generate.generate_app_events",
    },
    {
        "name": "Inject incidents",
        "module": "src.incidents.inject_incidents",
    },
    {
        "name": "Run data observability",
        "module": "src.quality.run_observability",
    },
    {
        "name": "Run business anomaly detection",
        "module": "src.anomaly.run_business_anomaly",
    },
    {
        "name": "Run root cause analysis",
        "module": "src.rca.run_root_cause_analysis",
    },
    {
        "name": "Classify incidents",
        "module": "src.incidents.classify_incidents",
    },
    {
        "name": "Build decision briefs",
        "module": "src.decision.build_decision_briefs",
    },
    {
        "name": "Build grounded AI prompts",
        "module": "src.ai.build_grounded_prompts",
    },
    {
        "name": "Build DuckDB warehouse",
        "module": "src.warehouse.build_warehouse",
    },
    {
        "name": "Build Silver SQL models",
        "module": "src.warehouse.build_silver_models",
    },
    {
        "name": "Build Gold executive mart",
        "module": "src.warehouse.build_gold_models",
    },
    {
        "name": "Build Gold logistics mart",
        "module": "src.warehouse.build_gold_logistics",
    },
    {
        "name": "Build Gold data reliability mart",
        "module": "src.warehouse.build_gold_data_reliability",
    },
    {
        "name": "Build Gold customer experience mart",
        "module": "src.warehouse.build_gold_customer_experience",
    },
    {
        "name": "Build Gold commerce mart",
        "module": "src.warehouse.build_gold_commerce",
    },
    {
        "name": "Build Gold incident command center",
        "module": "src.warehouse.build_gold_incident_command_center",
    },
]


OPTIONAL_AI_STEP = {
    "name": "Generate live Groq AI reports",
    "module": "src.ai.run_decision_assistant_groq",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Run the complete Aegis "
            "Data Reliability pipeline."
        )
    )

    parser.add_argument(
        "--with-ai",
        action="store_true",
        help=(
            "Also run the live Groq AI "
            "Decision Assistant."
        ),
    )

    parser.add_argument(
        "--from-step",
        type=int,
        default=1,
        help=(
            "Start from a specific pipeline "
            "step number. Default: 1."
        ),
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List available pipeline steps.",
    )

    return parser.parse_args()


def list_steps(
    include_ai=False,
):
    steps = PIPELINE_STEPS.copy()

    if include_ai:
        steps.append(
            OPTIONAL_AI_STEP
        )

    print("=" * 72)
    print(
        "AEGIS PIPELINE STEPS"
    )
    print("=" * 72)

    print()

    for index, step in enumerate(
        steps,
        start=1,
    ):
        print(
            f"{index:02d}. "
            f"{step['name']}"
        )

        print(
            f"    "
            f"{step['module']}"
        )


def run_step(
    index,
    total,
    step,
):
    print()
    print("=" * 72)

    print(
        f"STEP {index}/{total}"
    )

    print(
        step[
            "name"
        ]
    )

    print(
        f"Module: "
        f"{step['module']}"
    )

    print("=" * 72)

    started = time.perf_counter()

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            step[
                "module"
            ],
        ],
        cwd=PROJECT_ROOT,
    )

    elapsed = (
        time.perf_counter()
        - started
    )

    if result.returncode != 0:
        print()
        print(
            "PIPELINE STEP FAILED"
        )

        print(
            "-" * 72
        )

        print(
            f"Step:    "
            f"{index}"
        )

        print(
            f"Name:    "
            f"{step['name']}"
        )

        print(
            f"Module:  "
            f"{step['module']}"
        )

        print(
            f"Exit:    "
            f"{result.returncode}"
        )

        print(
            f"Elapsed: "
            f"{elapsed:.2f} sec"
        )

        raise SystemExit(
            result.returncode
        )

    print()
    print(
        f"STEP {index} PASSED "
        f"in {elapsed:.2f} sec"
    )

    return elapsed


def main():
    args = parse_args()

    if args.list:
        list_steps(
            include_ai=args.with_ai
        )

        return

    steps = PIPELINE_STEPS.copy()

    if args.with_ai:
        steps.append(
            OPTIONAL_AI_STEP
        )

    total = len(
        steps
    )

    if (
        args.from_step < 1
        or args.from_step > total
    ):
        raise SystemExit(
            f"--from-step must be "
            f"between 1 and {total}"
        )

    selected = steps[
        args.from_step - 1:
    ]

    print("=" * 72)
    print(
        "AEGIS END-TO-END PIPELINE"
    )
    print("=" * 72)

    print()

    print(
        f"Project root: "
        f"{PROJECT_ROOT}"
    )

    print(
        f"Python:       "
        f"{sys.executable}"
    )

    print(
        f"Total steps:  "
        f"{total}"
    )

    print(
        f"Starting at:  "
        f"{args.from_step}"
    )

    print(
        f"Live AI:      "
        f"{'ENABLED' if args.with_ai else 'DISABLED'}"
    )

    print()

    print(
        "The default pipeline is fully "
        "deterministic and does not require "
        "an external LLM API."
    )

    total_started = (
        time.perf_counter()
    )

    durations = []

    for absolute_index, step in enumerate(
        selected,
        start=args.from_step,
    ):
        elapsed = run_step(
            absolute_index,
            total,
            step,
        )

        durations.append(
            (
                absolute_index,
                step[
                    "name"
                ],
                elapsed,
            )
        )

    total_elapsed = (
        time.perf_counter()
        - total_started
    )

    print()
    print("=" * 72)
    print(
        "AEGIS PIPELINE SUMMARY"
    )
    print("=" * 72)

    print()

    print(
        f"Steps completed: "
        f"{len(durations)}"
    )

    print(
        f"Total runtime:   "
        f"{total_elapsed:.2f} sec"
    )

    print()

    print(
        "STEP TIMINGS"
    )

    print(
        "-" * 72
    )

    for (
        index,
        name,
        elapsed,
    ) in durations:
        print(
            f"{index:02d}. "
            f"{name:<42} "
            f"{elapsed:>8.2f} sec"
        )

    print()
    print(
        "PIPELINE STATUS: SUCCESS"
    )

    print()

    print(
        "Core outputs are ready for "
        "analytics, testing and BI."
    )


if __name__ == "__main__":
    main()
