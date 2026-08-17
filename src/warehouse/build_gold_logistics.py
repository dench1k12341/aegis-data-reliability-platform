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
    / "02_logistics_performance.sql"
)


def main():
    print("=" * 72)
    print(
        "AEGIS GOLD LOGISTICS PERFORMANCE MART"
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
            "Running 02_logistics_performance.sql..."
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

                SUM(
                    shipment_touches
                ) AS shipment_touches,

                SUM(
                    shipments
                ) AS grouped_shipments,

                MIN(
                    report_date
                ) AS min_date,

                MAX(
                    report_date
                ) AS max_date,

                COUNT(
                    DISTINCT warehouse_id
                ) AS warehouses,

                COUNT(
                    DISTINCT carrier_id
                ) AS carriers,

                COUNT(
                    DISTINCT route_name
                ) AS routes,

                SUM(
                    CASE
                        WHEN business_incident_flag = 1
                        THEN shipment_touches
                        ELSE 0
                    END
                ) AS incident_touches,

                SUM(
                    CASE
                        WHEN business_incident_flag = 1
                             AND city = 'Warsaw'
                        THEN shipment_touches
                        ELSE 0
                    END
                ) AS warsaw_incident_touches

            FROM gold.logistics_performance
            """
        ).fetchone()

        source_shipments = (
            connection.execute(
                """
                SELECT COUNT(*)
                FROM silver.shipments_enriched
                """
            )
            .fetchone()[0]
        )

        expected_touches = (
            source_shipments
            * 2
        )

        if (
            summary[1]
            != expected_touches
        ):
            raise AssertionError(
                "Warehouse shipment touch "
                "reconciliation failed."
            )

        source_date_range = (
            connection.execute(
                """
                SELECT
                    MIN(shipment_date),
                    MAX(shipment_date)
                FROM silver.shipments_enriched
                WHERE shipment_date BETWEEN
                    DATE '2025-01-01'
                    AND DATE '2025-12-31'
                """
            )
            .fetchone()
        )

        if summary[3] != source_date_range[0]:
            raise AssertionError(
                "Gold minimum report date does not "
                "match Silver shipment source."
            )

        if summary[4] != source_date_range[1]:
            raise AssertionError(
                "Gold maximum report date does not "
                "match Silver shipment source."
            )

        if summary[8] <= 0:
            raise AssertionError(
                "Business incident not visible "
                "in Gold logistics mart."
            )

        if summary[9] <= 0:
            raise AssertionError(
                "Warsaw incident not visible "
                "in Gold logistics mart."
            )

        print()
        print("=" * 72)
        print(
            "GOLD LOGISTICS MART SUMMARY"
        )
        print("=" * 72)

        print()

        print(
            f"Mart rows:             "
            f"{summary[0]:,}"
        )

        print(
            f"Shipment touches:      "
            f"{summary[1]:,}"
        )

        print(
            f"Source shipments:      "
            f"{source_shipments:,}"
        )

        print(
            f"Expected touches:      "
            f"{expected_touches:,}"
        )

        print(
            f"Date range:            "
            f"{summary[3]} "
            f"to {summary[4]}"
        )

        print()

        print(
            f"Warehouses:            "
            f"{summary[5]:,}"
        )

        print(
            f"Carriers:              "
            f"{summary[6]:,}"
        )

        print(
            f"Routes:                "
            f"{summary[7]:,}"
        )

        print()

        print(
            f"Incident touches:      "
            f"{summary[8]:,}"
        )

        print(
            f"Warsaw incident touches:"
            f" {summary[9]:,}"
        )

        print()

        print(
            "WARSAW INCIDENT SNAPSHOT"
        )

        print(
            "-" * 72
        )

        snapshot = connection.execute(
            """
            SELECT
                city,
                country,

                MIN(report_date)
                    AS first_visible_date,

                MAX(report_date)
                    AS last_visible_date,

                SUM(shipment_touches)
                    AS shipment_touches,

                ROUND(
                    SUM(delayed_shipments)
                    * 100.0
                    / NULLIF(
                        SUM(shipments),
                        0
                    ),
                    2
                ) AS delay_rate_pct,

                ROUND(
                    SUM(sla_met_shipments)
                    * 100.0
                    / NULLIF(
                        SUM(shipments),
                        0
                    ),
                    2
                ) AS delivery_sla_pct,

                ROUND(
                    SUM(
                        avg_network_load_pct
                        * shipments
                    )
                    / NULLIF(
                        SUM(shipments),
                        0
                    ),
                    2
                ) AS avg_network_load_pct,

                MAX(anomaly_score)
                    AS max_anomaly_score

            FROM gold.logistics_performance

            WHERE
                business_incident_flag = 1
                AND city = 'Warsaw'

            GROUP BY
                city,
                country
            """
        ).fetchone()

        print(
            f"Location:              "
            f"{snapshot[0]}, "
            f"{snapshot[1]}"
        )

        print(
            f"Visible window:        "
            f"{snapshot[2]} "
            f"to {snapshot[3]}"
        )

        print(
            f"Shipment touches:      "
            f"{snapshot[4]:,}"
        )

        print(
            f"Delay rate:            "
            f"{snapshot[5]:.2f}%"
        )

        print(
            f"Delivery SLA:          "
            f"{snapshot[6]:.2f}%"
        )

        print(
            f"Network load:          "
            f"{snapshot[7]:.2f}%"
        )

        print(
            f"Max anomaly score:     "
            f"{snapshot[8]:.2f}"
        )

        print()
        print(
            "GOLD LOGISTICS CONTRACT: PASSED"
        )

    finally:
        connection.close()


if __name__ == "__main__":
    main()
