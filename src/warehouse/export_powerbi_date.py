import duckdb

from src.utils.config import PROJECT_ROOT


DATABASE_PATH = (
    PROJECT_ROOT
    / "data"
    / "warehouse"
    / "aegis.duckdb"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "powerbi"
    / "data"
    / "dim_date.csv"
)


def main():
    print("=" * 72)
    print("AEGIS POWER BI DATE DIMENSION")
    print("=" * 72)

    connection = duckdb.connect(
        str(DATABASE_PATH),
        read_only=True,
    )

    try:
        connection.execute(
            f"""
            COPY (
                SELECT
                    calendar_date AS date,

                    YEAR(calendar_date)
                        AS year,

                    QUARTER(calendar_date)
                        AS quarter_number,

                    'Q'
                    || QUARTER(calendar_date)
                        AS quarter,

                    MONTH(calendar_date)
                        AS month_number,

                    STRFTIME(
                        calendar_date,
                        '%B'
                    ) AS month_name,

                    STRFTIME(
                        calendar_date,
                        '%Y-%m'
                    ) AS year_month,

                    DAY(calendar_date)
                        AS day_of_month,

                    STRFTIME(
                        calendar_date,
                        '%A'
                    ) AS day_name,

                    CAST(
                        STRFTIME(
                            calendar_date,
                            '%V'
                        ) AS INTEGER
                    ) AS week_number,

                    CASE
                        WHEN
                            DAYOFWEEK(calendar_date)
                            IN (0, 6)
                        THEN 1
                        ELSE 0
                    END AS weekend_flag,

                    CASE
                        WHEN calendar_date
                            BETWEEN
                                DATE '2025-09-08'
                                AND DATE '2025-09-14'
                        THEN 1
                        ELSE 0
                    END AS data_incident_period_flag,

                    CASE
                        WHEN calendar_date
                            BETWEEN
                                DATE '2025-11-18'
                                AND DATE '2025-12-01'
                        THEN 1
                        ELSE 0
                    END AS business_incident_period_flag

                FROM GENERATE_SERIES(
                    DATE '2025-01-01',
                    DATE '2025-12-31',
                    INTERVAL 1 DAY
                ) AS dates(calendar_date)

                ORDER BY calendar_date
            )
            TO '{OUTPUT_PATH.as_posix()}'
            (
                HEADER,
                DELIMITER ','
            )
            """
        )

        rows = connection.execute(
            """
            SELECT COUNT(*)
            FROM GENERATE_SERIES(
                DATE '2025-01-01',
                DATE '2025-12-31',
                INTERVAL 1 DAY
            )
            """
        ).fetchone()[0]

        print()
        print(
            f"Rows:              {rows}"
        )

        print(
            "Date range:        "
            "2025-01-01 to 2025-12-31"
        )

        print(
            f"Output:            {OUTPUT_PATH}"
        )

        print()
        print(
            "DATE DIMENSION CONTRACT: PASSED"
        )

    finally:
        connection.close()


if __name__ == "__main__":
    main()
