from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd

from src.utils.config import PROJECT_ROOT


WAREHOUSE_DIR = (
    PROJECT_ROOT
    / "data"
    / "warehouse"
)

DATABASE_PATH = (
    WAREHOUSE_DIR
    / "aegis.duckdb"
)

BRONZE_DIR = (
    PROJECT_ROOT
    / "data"
    / "bronze"
)

SILVER_DIR = (
    PROJECT_ROOT
    / "data"
    / "silver"
)


EXPECTED_BRONZE_TABLES = {
    "customers",
    "products",
    "warehouses",
    "carriers",
    "orders",
    "order_items",
    "payments",
    "shipments",
    "tracking_events",
    "support_cases",
    "app_events",
}


EXPECTED_SILVER_TABLES = {
    "daily_purchase_reconciliation",
    "warehouse_anomaly_windows",
}


def sql_path(
    path: Path,
):
    return str(
        path.resolve()
    ).replace(
        "'",
        "''",
    )


def connect():
    WAREHOUSE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = duckdb.connect(
        str(
            DATABASE_PATH
        )
    )

    connection.execute(
        "SET preserve_insertion_order = false"
    )

    return connection


def create_schemas(
    connection,
):
    for schema in [
        "bronze",
        "silver",
        "gold",
        "meta",
    ]:
        connection.execute(
            f"CREATE SCHEMA IF NOT EXISTS {schema}"
        )


def parquet_tables(
    directory,
):
    if not directory.exists():
        return {}

    return {
        path.stem: path
        for path
        in sorted(
            directory.glob(
                "*.parquet"
            )
        )
    }


def validate_expected_sources(
    source_tables,
    expected_tables,
    layer,
):
    missing = (
        expected_tables
        - set(
            source_tables
        )
    )

    if missing:
        raise FileNotFoundError(
            f"{layer}: missing expected "
            "Parquet datasets: "
            + ", ".join(
                sorted(
                    missing
                )
            )
        )


def load_parquet_table(
    connection,
    schema,
    table,
    path,
):
    source_path = sql_path(
        path
    )

    connection.execute(
        f"""
        CREATE OR REPLACE TABLE
            {schema}.{table}
        AS
        SELECT *
        FROM read_parquet(
            '{source_path}'
        )
        """
    )

    row_count = connection.execute(
        f"""
        SELECT COUNT(*)
        FROM {schema}.{table}
        """
    ).fetchone()[0]

    column_count = len(
        connection.execute(
            f"""
            DESCRIBE {schema}.{table}
            """
        ).fetchall()
    )

    return {
        "schema_name":
            schema,

        "table_name":
            table,

        "source_path":
            str(path),

        "row_count":
            int(
                row_count
            ),

        "column_count":
            int(
                column_count
            ),
    }


def load_layer(
    connection,
    schema,
    directory,
    expected_tables,
):
    sources = parquet_tables(
        directory
    )

    validate_expected_sources(
        sources,
        expected_tables,
        schema,
    )

    inventory = []

    for table, path in (
        sources.items()
    ):
        inventory.append(
            load_parquet_table(
                connection,
                schema,
                table,
                path,
            )
        )

    return inventory


def create_metadata_tables(
    connection,
):
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS
        meta.pipeline_runs (
            run_id VARCHAR,
            run_ts TIMESTAMP,
            pipeline_name VARCHAR,
            status VARCHAR,
            bronze_tables INTEGER,
            silver_tables INTEGER,
            total_rows BIGINT
        )
        """
    )

    connection.execute(
        """
        CREATE OR REPLACE TABLE
        meta.table_inventory (
            schema_name VARCHAR,
            table_name VARCHAR,
            source_path VARCHAR,
            row_count BIGINT,
            column_count INTEGER,
            loaded_at TIMESTAMP
        )
        """
    )


def save_inventory(
    connection,
    inventory,
):
    inventory_df = pd.DataFrame(
        inventory
    )

    inventory_df[
        "loaded_at"
    ] = datetime.now(
        timezone.utc
    ).replace(
        tzinfo=None
    )

    connection.register(
        "inventory_df",
        inventory_df,
    )

    connection.execute(
        """
        INSERT INTO
            meta.table_inventory
        SELECT *
        FROM inventory_df
        """
    )

    connection.unregister(
        "inventory_df"
    )


def save_pipeline_run(
    connection,
    inventory,
):
    now = datetime.now(
        timezone.utc
    )

    run_id = (
        "WAREHOUSE-"
        + now.strftime(
            "%Y%m%dT%H%M%SZ"
        )
    )

    bronze_tables = sum(
        item[
            "schema_name"
        ]
        == "bronze"
        for item
        in inventory
    )

    silver_tables = sum(
        item[
            "schema_name"
        ]
        == "silver"
        for item
        in inventory
    )

    total_rows = sum(
        item[
            "row_count"
        ]
        for item
        in inventory
    )

    connection.execute(
        """
        INSERT INTO
            meta.pipeline_runs
        VALUES (
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?
        )
        """,
        [
            run_id,
            now.replace(
                tzinfo=None
            ),
            "build_warehouse",
            "SUCCESS",
            bronze_tables,
            silver_tables,
            total_rows,
        ],
    )

    return {
        "run_id":
            run_id,

        "bronze_tables":
            bronze_tables,

        "silver_tables":
            silver_tables,

        "total_rows":
            total_rows,
    }


def validate_warehouse(
    connection,
):
    checks = {}

    checks[
        "orders"
    ] = connection.execute(
        """
        SELECT COUNT(*)
        FROM bronze.orders
        """
    ).fetchone()[0]

    checks[
        "shipments"
    ] = connection.execute(
        """
        SELECT COUNT(*)
        FROM bronze.shipments
        """
    ).fetchone()[0]

    checks[
        "tracking_events"
    ] = connection.execute(
        """
        SELECT COUNT(*)
        FROM bronze.tracking_events
        """
    ).fetchone()[0]

    checks[
        "support_cases"
    ] = connection.execute(
        """
        SELECT COUNT(*)
        FROM bronze.support_cases
        """
    ).fetchone()[0]

    checks[
        "app_events"
    ] = connection.execute(
        """
        SELECT COUNT(*)
        FROM bronze.app_events
        """
    ).fetchone()[0]

    if checks[
        "orders"
    ] != 25_000:
        raise AssertionError(
            "Unexpected bronze.orders count."
        )

    if checks[
        "shipments"
    ] != 22_000:
        raise AssertionError(
            "Unexpected bronze.shipments count."
        )

    if checks[
        "tracking_events"
    ] != 150_000:
        raise AssertionError(
            "Unexpected tracking event count."
        )

    if checks[
        "support_cases"
    ] != 4_000:
        raise AssertionError(
            "Unexpected support case count."
        )

    if checks[
        "app_events"
    ] >= 200_000:
        raise AssertionError(
            "Expected app-event incident "
            "to remove purchase events "
            "from Bronze."
        )

    return checks


def print_inventory(
    inventory,
):
    inventory_df = pd.DataFrame(
        inventory
    )

    display = (
        inventory_df[
            [
                "schema_name",
                "table_name",
                "row_count",
                "column_count",
            ]
        ]
        .sort_values(
            [
                "schema_name",
                "table_name",
            ]
        )
    )

    print(
        display.to_string(
            index=False
        )
    )


def main():
    print("=" * 72)
    print(
        "AEGIS DUCKDB ANALYTICS WAREHOUSE"
    )
    print("=" * 72)

    connection = connect()

    try:
        create_schemas(
            connection
        )

        create_metadata_tables(
            connection
        )

        print()
        print(
            "Loading Bronze layer..."
        )

        bronze_inventory = (
            load_layer(
                connection,
                "bronze",
                BRONZE_DIR,
                EXPECTED_BRONZE_TABLES,
            )
        )

        print(
            "Loading Silver layer..."
        )

        silver_inventory = (
            load_layer(
                connection,
                "silver",
                SILVER_DIR,
                EXPECTED_SILVER_TABLES,
            )
        )

        inventory = (
            bronze_inventory
            + silver_inventory
        )

        save_inventory(
            connection,
            inventory,
        )

        run = save_pipeline_run(
            connection,
            inventory,
        )

        checks = validate_warehouse(
            connection
        )

        print()
        print("=" * 72)
        print(
            "WAREHOUSE INVENTORY"
        )
        print("=" * 72)
        print()

        print_inventory(
            inventory
        )

        print()
        print("=" * 72)
        print(
            "WAREHOUSE SUMMARY"
        )
        print("=" * 72)
        print()

        print(
            f"Database:            "
            f"{DATABASE_PATH}"
        )

        print(
            f"Run ID:              "
            f"{run['run_id']}"
        )

        print(
            f"Bronze tables:       "
            f"{run['bronze_tables']}"
        )

        print(
            f"Silver tables:       "
            f"{run['silver_tables']}"
        )

        print(
            f"Rows loaded:         "
            f"{run['total_rows']:,}"
        )

        print()
        print(
            "Key Bronze checks:"
        )

        print(
            f"Orders:              "
            f"{checks['orders']:,}"
        )

        print(
            f"Shipments:           "
            f"{checks['shipments']:,}"
        )

        print(
            f"Tracking events:     "
            f"{checks['tracking_events']:,}"
        )

        print(
            f"Support cases:       "
            f"{checks['support_cases']:,}"
        )

        print(
            f"App events:          "
            f"{checks['app_events']:,}"
        )

        print()
        print(
            "Schemas:"
        )

        print(
            "  bronze  - source-aligned incident data"
        )

        print(
            "  silver  - validated analytical datasets"
        )

        print(
            "  gold    - business marts (next step)"
        )

        print(
            "  meta    - warehouse lineage and run metadata"
        )

        print()
        print(
            "WAREHOUSE CONTRACT: PASSED"
        )

    finally:
        connection.close()


if __name__ == "__main__":
    main()
