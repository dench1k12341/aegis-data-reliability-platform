import duckdb

from src.utils.config import PROJECT_ROOT


DATABASE_PATH = (
    PROJECT_ROOT
    / "data"
    / "warehouse"
    / "aegis.duckdb"
)

SQL_PATH = (
    PROJECT_ROOT
    / "sql"
    / "gold"
    / "03_data_reliability.sql"
)


def main():
    print("=" * 72)
    print(
        "AEGIS GOLD DATA RELIABILITY MART"
    )
    print("=" * 72)

    connection = duckdb.connect(
        str(DATABASE_PATH)
    )

    try:
        print()
        print(
            "Running 03_data_reliability.sql..."
        )

        connection.execute(
            SQL_PATH.read_text(
                encoding="utf-8-sig"
            )
        )

        summary = connection.execute(
            """
            SELECT
                COUNT(*) AS rows,

                COUNT(DISTINCT report_date)
                    AS unique_dates,

                MIN(report_date)
                    AS min_date,

                MAX(report_date)
                    AS max_date,

                SUM(data_incident_flag)
                    AS incident_days

            FROM gold.data_reliability_daily
            """
        ).fetchone()

        incident = connection.execute(
            """
            SELECT
                MIN(report_date)
                    AS incident_start,

                MAX(report_date)
                    AS incident_end,

                SUM(expected_purchase_count)
                    AS expected_purchases,

                SUM(observed_purchase_count)
                    AS observed_purchases,

                SUM(missing_purchase_events)
                    AS missing_purchases,

                SUM(purchase_value_null_count)
                    AS null_values,

                ROUND(
                    SUM(observed_purchase_count)
                    * 100.0
                    / NULLIF(
                        SUM(expected_purchase_count),
                        0
                    ),
                    2
                ) AS event_coverage_pct,

                ROUND(
                    SUM(observed_event_revenue_eur)
                    * 100.0
                    / NULLIF(
                        SUM(expected_revenue_eur),
                        0
                    ),
                    2
                ) AS revenue_capture_pct

            FROM gold.data_reliability_daily

            WHERE
                data_incident_flag = 1
            """
        ).fetchone()

        duplicates = connection.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT
                    report_date
                FROM gold.data_reliability_daily
                GROUP BY report_date
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]

        if summary[0] != 365:
            raise AssertionError(
                "Data Reliability mart "
                "must contain 365 rows."
            )

        if summary[1] != 365:
            raise AssertionError(
                "report_date must be unique."
            )

        if summary[4] != 7:
            raise AssertionError(
                "Expected exactly 7 "
                "data incident days."
            )

        if incident[2] != 523:
            raise AssertionError(
                "Expected purchase count "
                "does not match detected incident."
            )

        if incident[3] != 304:
            raise AssertionError(
                "Observed purchase count "
                "does not match detected incident."
            )

        if incident[4] != 219:
            raise AssertionError(
                "Missing purchase count "
                "does not match detected incident."
            )

        if incident[5] != 136:
            raise AssertionError(
                "Null purchase-value count "
                "does not match detected incident."
            )

        if duplicates != 0:
            raise AssertionError(
                "Duplicate reporting dates detected."
            )

        print()
        print("=" * 72)
        print(
            "GOLD DATA RELIABILITY SUMMARY"
        )
        print("=" * 72)

        print()

        print(
            f"Rows:                  "
            f"{summary[0]:,}"
        )

        print(
            f"Unique dates:          "
            f"{summary[1]:,}"
        )

        print(
            f"Date range:            "
            f"{summary[2]} "
            f"to {summary[3]}"
        )

        print(
            f"Data incident days:    "
            f"{summary[4]}"
        )

        print()
        print(
            "PURCHASE TELEMETRY INCIDENT"
        )

        print(
            "-" * 72
        )

        print(
            f"Detected window:       "
            f"{incident[0]} "
            f"to {incident[1]}"
        )

        print(
            f"Expected purchases:    "
            f"{incident[2]:,}"
        )

        print(
            f"Observed purchases:    "
            f"{incident[3]:,}"
        )

        print(
            f"Missing purchases:     "
            f"{incident[4]:,}"
        )

        print(
            f"Null purchase values:  "
            f"{incident[5]:,}"
        )

        print(
            f"Event coverage:        "
            f"{incident[6]:.2f}%"
        )

        print(
            f"Revenue capture:       "
            f"{incident[7]:.2f}%"
        )

        print()

        print(
            "GOLD DATA RELIABILITY CONTRACT: PASSED"
        )

    finally:
        connection.close()


if __name__ == "__main__":
    main()
