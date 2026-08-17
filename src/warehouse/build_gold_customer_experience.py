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
    / "04_customer_experience.sql"
)


def main():
    print("=" * 72)
    print(
        "AEGIS GOLD CUSTOMER EXPERIENCE MART"
    )
    print("=" * 72)

    connection = duckdb.connect(
        str(DATABASE_PATH)
    )

    try:
        print()
        print(
            "Running 04_customer_experience.sql..."
        )

        connection.execute(
            SQL_PATH.read_text(
                encoding="utf-8-sig"
            )
        )

        summary = connection.execute(
            """
            SELECT
                COUNT(*) AS mart_rows,

                SUM(support_cases)
                    AS support_cases,

                MIN(report_date)
                    AS min_date,

                MAX(report_date)
                    AS max_date,

                COUNT(
                    DISTINCT carrier_id
                ) AS carriers,

                SUM(
                    CASE
                        WHEN business_incident_flag = 1
                        THEN support_cases
                        ELSE 0
                    END
                ) AS incident_support_cases

            FROM gold.customer_experience
            """
        ).fetchone()

        source_cases = (
            connection.execute(
                """
                SELECT COUNT(*)
                FROM silver.support_enriched
                WHERE case_date BETWEEN
                    DATE '2025-01-01'
                    AND DATE '2025-12-31'
                """
            )
            .fetchone()[0]
        )

        incident = connection.execute(
            """
            SELECT
                SUM(support_cases)
                    AS cases,

                ROUND(
                    SUM(
                        support_sla_pct
                        * support_cases
                    )
                    / NULLIF(
                        SUM(support_cases),
                        0
                    ),
                    2
                ) AS support_sla_pct,

                ROUND(
                    SUM(
                        avg_csat
                        * support_cases
                    )
                    / NULLIF(
                        SUM(support_cases),
                        0
                    ),
                    2
                ) AS avg_csat,

                ROUND(
                    SUM(
                        escalation_rate_pct
                        * support_cases
                    )
                    / NULLIF(
                        SUM(support_cases),
                        0
                    ),
                    2
                ) AS escalation_rate_pct,

                MIN(report_date)
                    AS first_case_date,

                MAX(report_date)
                    AS last_case_date

            FROM gold.customer_experience

            WHERE
                business_incident_flag = 1
            """
        ).fetchone()

        baseline = connection.execute(
            """
            SELECT
                ROUND(
                    AVG(support_sla_met)
                    * 100,
                    2
                ) AS support_sla_pct,

                ROUND(
                    AVG(csat_score),
                    2
                ) AS avg_csat,

                ROUND(
                    AVG(escalated_flag)
                    * 100,
                    2
                ) AS escalation_rate_pct

            FROM silver.support_enriched

            WHERE shipment_id NOT IN (
                SELECT DISTINCT
                    s.shipment_id

                FROM silver.shipments_enriched AS s

                INNER JOIN meta.business_incidents AS i

                    ON (
                        s.origin_warehouse_id
                            = i.warehouse_id

                        OR

                        s.destination_warehouse_id
                            = i.warehouse_id
                    )

                    AND s.shipment_date
                        BETWEEN
                            i.start_date
                            AND i.end_date
            )
            """
        ).fetchone()

        if (
            summary[1]
            != source_cases
        ):
            raise AssertionError(
                "Support case reconciliation failed."
            )

        if summary[5] <= 0:
            raise AssertionError(
                "Business incident customer impact "
                "is not visible."
            )

        if incident[0] != 4:
            raise AssertionError(
                "Expected 4 Warsaw incident "
                "support cases."
            )

        print()
        print("=" * 72)
        print(
            "GOLD CUSTOMER EXPERIENCE SUMMARY"
        )
        print("=" * 72)

        print()

        print(
            f"Mart rows:              "
            f"{summary[0]:,}"
        )

        print(
            f"Support cases:          "
            f"{summary[1]:,}"
        )

        print(
            f"Source support cases:   "
            f"{source_cases:,}"
        )

        print(
            f"Date range:             "
            f"{summary[2]} "
            f"to {summary[3]}"
        )

        print(
            f"Carriers:               "
            f"{summary[4]}"
        )

        print()
        print(
            "WARSAW CUSTOMER IMPACT"
        )
        print(
            "-" * 72
        )

        print(
            f"Affected support cases: "
            f"{incident[0]:,}"
        )

        print(
            f"Case date range:        "
            f"{incident[4]} "
            f"to {incident[5]}"
        )

        print(
            f"Support SLA:            "
            f"{incident[1]:.2f}%"
        )

        print(
            f"Average CSAT:           "
            f"{incident[2]:.2f}"
        )

        print(
            f"Escalation rate:        "
            f"{incident[3]:.2f}%"
        )

        print()
        print(
            "NON-INCIDENT BASELINE"
        )
        print(
            "-" * 72
        )

        print(
            f"Support SLA:            "
            f"{baseline[0]:.2f}%"
        )

        print(
            f"Average CSAT:           "
            f"{baseline[1]:.2f}"
        )

        print(
            f"Escalation rate:        "
            f"{baseline[2]:.2f}%"
        )

        print()
        print(
            "GOLD CUSTOMER EXPERIENCE CONTRACT: PASSED"
        )

    finally:
        connection.close()


if __name__ == "__main__":
    main()
