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
    / "gold"
)

MODELS = [
    "01_executive_daily.sql",
]


def run_model(
    connection,
    filename,
):
    path = SQL_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f"Missing Gold SQL model: {path}"
        )

    print(
        f"Running {filename}..."
    )

    connection.execute(
        path.read_text(
            encoding="utf-8-sig"
        )
    )


def validate(
    connection,
):
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
            SUM(orders)
                AS orders,
            SUM(shipments)
                AS shipments,
            SUM(purchase_events)
                AS purchase_events,
            SUM(
                data_incident_flag
            ) AS data_incident_days
        FROM gold.executive_daily
        """
    ).fetchone()

    duplicates = connection.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT
                report_date
            FROM gold.executive_daily
            GROUP BY report_date
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()[0]

    bronze_purchases = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM bronze.app_events
            WHERE
                event_type = 'purchase'
                AND CAST(event_ts AS DATE)
                    BETWEEN
                        DATE '2025-01-01'
                        AND DATE '2025-12-31'
            """
        )
        .fetchone()[0]
    )

    if summary[0] != 365:
        raise AssertionError(
            "Gold calendar must contain 365 rows."
        )

    if summary[1] != 365:
        raise AssertionError(
            "Gold report_date must be unique."
        )

    if summary[2] != __import__(
        "datetime"
    ).date(
        2025,
        1,
        1,
    ):
        raise AssertionError(
            "Unexpected Gold start date."
        )

    if summary[3] != __import__(
        "datetime"
    ).date(
        2025,
        12,
        31,
    ):
        raise AssertionError(
            "Unexpected Gold end date."
        )

    if duplicates != 0:
        raise AssertionError(
            "Duplicate Gold dates detected."
        )

    if summary[4] != 25_000:
        raise AssertionError(
            "Gold order total mismatch."
        )

    if summary[5] != 22_000:
        raise AssertionError(
            "Gold shipment total mismatch."
        )

    if summary[6] != bronze_purchases:
        raise AssertionError(
            "Gold purchase total mismatch."
        )

    return {
        "rows":
            int(summary[0]),

        "unique_dates":
            int(summary[1]),

        "min_date":
            summary[2],

        "max_date":
            summary[3],

        "orders":
            int(summary[4]),

        "shipments":
            int(summary[5]),

        "purchases":
            int(summary[6]),

        "data_incident_days":
            int(summary[7]),

        "duplicates":
            int(duplicates),
    }


def main():
    print("=" * 72)
    print(
        "AEGIS GOLD ANALYTICS MARTS"
    )
    print("=" * 72)

    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            "Warehouse database not found."
        )

    connection = duckdb.connect(
        str(
            DATABASE_PATH
        )
    )

    try:
        print()

        for model in MODELS:
            run_model(
                connection,
                model,
            )

        result = validate(
            connection
        )

        print()
        print("=" * 72)
        print(
            "GOLD EXECUTIVE MART SUMMARY"
        )
        print("=" * 72)

        print()

        print(
            f"Rows:                 "
            f"{result['rows']:,}"
        )

        print(
            f"Unique dates:         "
            f"{result['unique_dates']:,}"
        )

        print(
            f"Date range:           "
            f"{result['min_date']} "
            f"to {result['max_date']}"
        )

        print()
        print(
            f"Orders:               "
            f"{result['orders']:,}"
        )

        print(
            f"Shipments:            "
            f"{result['shipments']:,}"
        )

        print(
            f"Purchase events:      "
            f"{result['purchases']:,}"
        )

        print(
            f"Data incident days:   "
            f"{result['data_incident_days']}"
        )

        print(
            f"Duplicate dates:      "
            f"{result['duplicates']}"
        )

        print()

        print(
            "GOLD EXECUTIVE CONTRACT: PASSED"
        )

    finally:
        connection.close()


if __name__ == "__main__":
    main()
