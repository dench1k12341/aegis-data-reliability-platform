import duckdb
from pathlib import Path

from src.utils.config import PROJECT_ROOT


DATABASE_PATH = (
    PROJECT_ROOT
    / "data"
    / "warehouse"
    / "aegis.duckdb"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "powerbi"
    / "data"
)


EXPORTS = {
    "executive_daily":
        "gold.executive_daily",

    "logistics_performance":
        "gold.logistics_performance",

    "data_reliability_daily":
        "gold.data_reliability_daily",

    "customer_experience":
        "gold.customer_experience",

    "commerce_performance":
        "gold.commerce_performance",

    "incident_command_center":
        "gold.incident_command_center",
}


def main():
    print("=" * 72)
    print(
        "AEGIS POWER BI EXPORT"
    )
    print("=" * 72)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = duckdb.connect(
        str(DATABASE_PATH),
        read_only=True,
    )

    try:
        total_rows = 0

        for filename, table_name in EXPORTS.items():
            output_path = (
                OUTPUT_DIR
                / f"{filename}.csv"
            )

            row_count = connection.execute(
                f"""
                SELECT COUNT(*)
                FROM {table_name}
                """
            ).fetchone()[0]

            connection.execute(
                f"""
                COPY (
                    SELECT *
                    FROM {table_name}
                )
                TO '{output_path.as_posix()}'
                (
                    HEADER,
                    DELIMITER ','
                )
                """
            )

            total_rows += row_count

            print(
                f"{filename:<30} "
                f"{row_count:>10,} rows"
            )

        print()
        print(
            f"Files exported:        "
            f"{len(EXPORTS)}"
        )

        print(
            f"Rows exported:         "
            f"{total_rows:,}"
        )

        print(
            f"Output directory:      "
            f"{OUTPUT_DIR}"
        )

        print()
        print(
            "POWER BI EXPORT: PASSED"
        )

    finally:
        connection.close()


if __name__ == "__main__":
    main()
