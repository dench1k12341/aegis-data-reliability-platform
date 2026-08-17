import json

import duckdb
import pandas as pd

from src.utils.config import PROJECT_ROOT


DATABASE_PATH = (
    PROJECT_ROOT
    / "data"
    / "warehouse"
    / "aegis.duckdb"
)

ARTIFACTS_DIR = (
    PROJECT_ROOT
    / "artifacts"
)

SQL_PATH = (
    PROJECT_ROOT
    / "sql"
    / "gold"
    / "06_incident_command_center.sql"
)


def load_incident_registry(
    connection,
):
    path = (
        ARTIFACTS_DIR
        / "incident_registry.csv"
    )

    if not path.exists():
        raise FileNotFoundError(
            "incident_registry.csv not found."
        )

    df = pd.read_csv(
        path
    )

    connection.register(
        "incident_registry_df",
        df,
    )

    connection.execute(
        """
        CREATE OR REPLACE TABLE
            meta.incident_registry
        AS
        SELECT *
        FROM incident_registry_df
        """
    )

    connection.unregister(
        "incident_registry_df"
    )

    return len(df)


def load_decision_briefs(
    connection,
):
    path = (
        ARTIFACTS_DIR
        / "decision_briefs.json"
    )

    if not path.exists():
        raise FileNotFoundError(
            "decision_briefs.json not found."
        )

    briefs = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    records = []

    for brief in briefs:
        records.append(
            {
                "incident_id":
                    brief[
                        "incident_id"
                    ],

                "classification":
                    brief[
                        "classification"
                    ],

                "decision_status":
                    brief[
                        "decision_status"
                    ],

                "decision_label":
                    brief[
                        "decision_label"
                    ],

                "executive_summary":
                    brief[
                        "executive_summary"
                    ],

                "recommended_actions":
                    " | ".join(
                        brief[
                            "recommended_actions"
                        ]
                    ),

                "evidence":
                    " | ".join(
                        brief[
                            "evidence"
                        ]
                    ),
            }
        )

    df = pd.DataFrame(
        records
    )

    connection.register(
        "decision_briefs_df",
        df,
    )

    connection.execute(
        """
        CREATE OR REPLACE TABLE
            meta.decision_briefs
        AS
        SELECT *
        FROM decision_briefs_df
        """
    )

    connection.unregister(
        "decision_briefs_df"
    )

    return len(df)


def run_gold_model(
    connection,
):
    connection.execute(
        SQL_PATH.read_text(
            encoding="utf-8-sig"
        )
    )


def validate(
    connection,
):
    summary = connection.execute(
        """
        SELECT
            COUNT(*)
                AS incidents,

            SUM(
                CASE
                    WHEN classification
                        = 'DATA_INCIDENT'
                    THEN 1
                    ELSE 0
                END
            ) AS data_incidents,

            SUM(
                CASE
                    WHEN classification
                        = 'BUSINESS_INCIDENT'
                    THEN 1
                    ELSE 0
                END
            ) AS business_incidents,

            SUM(
                CASE
                    WHEN data_trust_status
                        = 'FAILED'
                    THEN 1
                    ELSE 0
                END
            ) AS failed_data_trust,

            SUM(
                CASE
                    WHEN data_trust_status
                        = 'PASSED'
                    THEN 1
                    ELSE 0
                END
            ) AS passed_data_trust

        FROM gold.incident_command_center
        """
    ).fetchone()

    data_incident = connection.execute(
        """
        SELECT
            incident_id,
            incident_start_date,
            incident_end_date,
            confidence_score,
            primary_cause,
            missing_records,
            event_coverage_pct,
            revenue_capture_pct,
            decision_label,
            command_center_status

        FROM gold.incident_command_center

        WHERE
            classification
            = 'DATA_INCIDENT'
        """
    ).fetchone()

    business_incident = connection.execute(
        """
        SELECT
            incident_id,
            location,
            incident_start_date,
            incident_end_date,
            confidence_score,
            primary_cause,
            affected_records,
            anomaly_score,
            decision_label,
            command_center_status

        FROM gold.incident_command_center

        WHERE
            classification
            = 'BUSINESS_INCIDENT'
        """
    ).fetchone()

    if summary[0] != 2:
        raise AssertionError(
            "Expected exactly 2 incidents."
        )

    if summary[1] != 1:
        raise AssertionError(
            "Expected exactly 1 Data Incident."
        )

    if summary[2] != 1:
        raise AssertionError(
            "Expected exactly 1 Business Incident."
        )

    if summary[3] != 1:
        raise AssertionError(
            "Expected exactly one failed "
            "Data Trust incident."
        )

    if summary[4] != 1:
        raise AssertionError(
            "Expected exactly one passed "
            "Data Trust incident."
        )

    if str(
        data_incident[1]
    ) != "2025-09-08":
        raise AssertionError(
            "Unexpected Data Incident start."
        )

    if str(
        data_incident[2]
    ) != "2025-09-14":
        raise AssertionError(
            "Unexpected Data Incident end."
        )

    if int(
        data_incident[5]
    ) != 219:
        raise AssertionError(
            "Data Incident missing records mismatch."
        )

    if round(
        float(
            data_incident[6]
        ),
        2,
    ) != 58.13:
        raise AssertionError(
            "Data Incident event coverage mismatch."
        )

    if round(
        float(
            data_incident[7]
        ),
        2,
    ) != 29.28:
        raise AssertionError(
            "Data Incident revenue capture mismatch."
        )

    if (
        business_incident[1]
        != "Warsaw, Poland"
    ):
        raise AssertionError(
            "Unexpected Business Incident location."
        )

    if str(
        business_incident[2]
    ) != "2025-11-18":
        raise AssertionError(
            "Unexpected Business Incident start."
        )

    if str(
        business_incident[3]
    ) != "2025-12-01":
        raise AssertionError(
            "Unexpected Business Incident end."
        )

    if int(
        business_incident[6]
    ) != 27:
        raise AssertionError(
            "Business Incident volume mismatch."
        )

    return (
        summary,
        data_incident,
        business_incident,
    )


def main():
    print("=" * 72)
    print(
        "AEGIS GOLD INCIDENT COMMAND CENTER"
    )
    print("=" * 72)

    connection = duckdb.connect(
        str(
            DATABASE_PATH
        )
    )

    try:
        print()
        print(
            "Loading incident metadata..."
        )

        registry_count = (
            load_incident_registry(
                connection
            )
        )

        briefs_count = (
            load_decision_briefs(
                connection
            )
        )

        print(
            f"Incident registry rows: "
            f"{registry_count}"
        )

        print(
            f"Decision briefs:       "
            f"{briefs_count}"
        )

        print()
        print(
            "Running 06_incident_command_center.sql..."
        )

        run_gold_model(
            connection
        )

        (
            summary,
            data_incident,
            business_incident,
        ) = validate(
            connection
        )

        print()
        print("=" * 72)
        print(
            "INCIDENT COMMAND CENTER SUMMARY"
        )
        print("=" * 72)

        print()

        print(
            f"Total incidents:       "
            f"{summary[0]}"
        )

        print(
            f"Data incidents:        "
            f"{summary[1]}"
        )

        print(
            f"Business incidents:    "
            f"{summary[2]}"
        )

        print(
            f"Data Trust FAILED:     "
            f"{summary[3]}"
        )

        print(
            f"Data Trust PASSED:     "
            f"{summary[4]}"
        )

        print()
        print(
            "DATA INCIDENT"
        )
        print(
            "-" * 72
        )

        print(
            f"Incident:              "
            f"{data_incident[0]}"
        )

        print(
            f"Window:                "
            f"{data_incident[1]} "
            f"to {data_incident[2]}"
        )

        print(
            f"Confidence:            "
            f"{data_incident[3]:.2f}%"
        )

        print(
            f"Primary cause:         "
            f"{data_incident[4]}"
        )

        print(
            f"Missing records:       "
            f"{data_incident[5]:,}"
        )

        print(
            f"Event coverage:        "
            f"{data_incident[6]:.2f}%"
        )

        print(
            f"Revenue capture:       "
            f"{data_incident[7]:.2f}%"
        )

        print(
            f"Decision:              "
            f"{data_incident[8]}"
        )

        print(
            f"Command status:        "
            f"{data_incident[9]}"
        )

        print()
        print(
            "BUSINESS INCIDENT"
        )
        print(
            "-" * 72
        )

        print(
            f"Incident:              "
            f"{business_incident[0]}"
        )

        print(
            f"Location:              "
            f"{business_incident[1]}"
        )

        print(
            f"Window:                "
            f"{business_incident[2]} "
            f"to {business_incident[3]}"
        )

        print(
            f"Confidence:            "
            f"{business_incident[4]:.2f}%"
        )

        print(
            f"Primary cause:         "
            f"{business_incident[5]}"
        )

        print(
            f"Affected shipments:    "
            f"{business_incident[6]:,}"
        )

        print(
            f"Anomaly score:         "
            f"{business_incident[7]:.2f}"
        )

        print(
            f"Decision:              "
            f"{business_incident[8]}"
        )

        print(
            f"Command status:        "
            f"{business_incident[9]}"
        )

        print()
        print(
            "GOLD INCIDENT COMMAND CENTER CONTRACT: PASSED"
        )

    finally:
        connection.close()


if __name__ == "__main__":
    main()
