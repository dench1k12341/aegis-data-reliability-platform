from pathlib import Path

import duckdb

from src.utils.config import PROJECT_ROOT


DATABASE_PATH = (
    PROJECT_ROOT
    / "data"
    / "warehouse"
    / "aegis.duckdb"
)

SQL_DIR = (
    PROJECT_ROOT
    / "sql"
    / "silver"
)

MODELS = [
    "01_orders_enriched.sql",
    "02_shipments_enriched.sql",
    "03_support_enriched.sql",
    "04_app_funnel_daily.sql",
]


def execute_models(
    connection,
):
    results = []

    for filename in MODELS:
        path = SQL_DIR / filename

        if not path.exists():
            raise FileNotFoundError(
                f"Missing SQL model: {path}"
            )

        print(
            f"Running {filename}..."
        )

        sql = path.read_text(
            encoding="utf-8-sig"
        )

        connection.execute(
            sql
        )

        table_name = (
            filename
            .replace(
                ".sql",
                "",
            )
            .split(
                "_",
                1,
            )[1]
        )

        row_count = (
            connection.execute(
                f"""
                SELECT COUNT(*)
                FROM silver.{table_name}
                """
            )
            .fetchone()[0]
        )

        results.append(
            {
                "table":
                    table_name,

                "rows":
                    int(
                        row_count
                    ),
            }
        )

    return results


def validate_models(
    connection,
):
    checks = {}

    checks[
        "orders"
    ] = connection.execute(
        """
        SELECT COUNT(*)
        FROM silver.orders_enriched
        """
    ).fetchone()[0]

    checks[
        "shipments"
    ] = connection.execute(
        """
        SELECT COUNT(*)
        FROM silver.shipments_enriched
        """
    ).fetchone()[0]

    checks[
        "support"
    ] = connection.execute(
        """
        SELECT COUNT(*)
        FROM silver.support_enriched
        """
    ).fetchone()[0]

    checks[
        "order_duplicates"
    ] = connection.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT
                order_id
            FROM silver.orders_enriched
            GROUP BY order_id
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()[0]

    checks[
        "shipment_duplicates"
    ] = connection.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT
                shipment_id
            FROM silver.shipments_enriched
            GROUP BY shipment_id
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()[0]

    checks[
        "case_duplicates"
    ] = connection.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT
                case_id
            FROM silver.support_enriched
            GROUP BY case_id
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()[0]

    checks[
        "payment_mismatches"
    ] = connection.execute(
        """
        SELECT COUNT(*)
        FROM silver.orders_enriched
        WHERE ABS(
            payment_reconciliation_delta_eur
        ) > 0.01
        """
    ).fetchone()[0]

    checks[
        "bronze_purchases"
    ] = connection.execute(
        """
        SELECT COUNT(*)
        FROM bronze.app_events
        WHERE event_type = 'purchase'
        """
    ).fetchone()[0]

    checks[
        "silver_purchases"
    ] = connection.execute(
        """
        SELECT
            COALESCE(
                SUM(
                    purchase_events
                ),
                0
            )
        FROM silver.app_funnel_daily
        """
    ).fetchone()[0]

    if checks["orders"] != 25_000:
        raise AssertionError(
            "orders_enriched row count failed."
        )

    if checks["shipments"] != 22_000:
        raise AssertionError(
            "shipments_enriched row count failed."
        )

    if checks["support"] != 4_000:
        raise AssertionError(
            "support_enriched row count failed."
        )

    if checks["order_duplicates"] != 0:
        raise AssertionError(
            "Duplicate order_id detected."
        )

    if checks["shipment_duplicates"] != 0:
        raise AssertionError(
            "Duplicate shipment_id detected."
        )

    if checks["case_duplicates"] != 0:
        raise AssertionError(
            "Duplicate case_id detected."
        )

    if checks["payment_mismatches"] != 0:
        raise AssertionError(
            "Order/payment reconciliation failed."
        )

    if (
        checks["bronze_purchases"]
        != checks["silver_purchases"]
    ):
        raise AssertionError(
            "App purchase aggregation mismatch."
        )

    return checks


def main():
    print("=" * 72)
    print(
        "AEGIS SILVER SQL TRANSFORMATION LAYER"
    )
    print("=" * 72)

    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            "aegis.duckdb not found. "
            "Run build_warehouse first."
        )

    connection = duckdb.connect(
        str(
            DATABASE_PATH
        )
    )

    try:
        print()

        results = execute_models(
            connection
        )

        checks = validate_models(
            connection
        )

        print()
        print("=" * 72)
        print(
            "SILVER MODEL SUMMARY"
        )
        print("=" * 72)

        print()

        for result in results:
            print(
                f"{result['table']:<30} "
                f"{result['rows']:>10,}"
            )

        print()
        print(
            "CONTRACT CHECKS"
        )

        print(
            f"Order duplicates:       "
            f"{checks['order_duplicates']}"
        )

        print(
            f"Shipment duplicates:    "
            f"{checks['shipment_duplicates']}"
        )

        print(
            f"Support duplicates:     "
            f"{checks['case_duplicates']}"
        )

        print(
            f"Payment mismatches:     "
            f"{checks['payment_mismatches']}"
        )

        print(
            f"Bronze purchases:       "
            f"{checks['bronze_purchases']:,}"
        )

        print(
            f"Silver purchases:       "
            f"{checks['silver_purchases']:,}"
        )

        date_range = (
            connection.execute(
                """
                SELECT
                    MIN(event_date),
                    MAX(event_date),
                    COUNT(*)
                FROM silver.app_funnel_daily
                """
            )
            .fetchone()
        )

        print()
        print(
            f"App funnel date range:  "
            f"{date_range[0]} "
            f"to {date_range[1]}"
        )

        print(
            f"Daily funnel rows:      "
            f"{date_range[2]:,}"
        )

        print()
        print(
            "SILVER CONTRACT: PASSED"
        )

    finally:
        connection.close()


if __name__ == "__main__":
    main()
