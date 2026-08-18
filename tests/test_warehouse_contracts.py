import duckdb
import pytest

from src.utils.config import PROJECT_ROOT


DATABASE_PATH = (
    PROJECT_ROOT
    / "data"
    / "warehouse"
    / "aegis.duckdb"
)


@pytest.fixture(scope="module")
def connection():
    conn = duckdb.connect(
        str(DATABASE_PATH),
        read_only=True,
    )

    yield conn

    conn.close()


def test_expected_schemas_exist(connection):
    schemas = {
        row[0]
        for row in connection.execute(
            """
            SELECT schema_name
            FROM information_schema.schemata
            """
        ).fetchall()
    }

    assert "bronze" in schemas
    assert "silver" in schemas
    assert "gold" in schemas
    assert "meta" in schemas


def test_bronze_table_inventory(connection):
    expected = {
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

    actual = {
        row[0]
        for row in connection.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'bronze'
            """
        ).fetchall()
    }

    assert expected.issubset(actual)


def test_bronze_row_counts(connection):
    expected_counts = {
        "customers": 10000,
        "products": 5000,
        "warehouses": 30,
        "carriers": 10,
        "orders": 25000,
        "order_items": 47983,
        "payments": 25000,
        "shipments": 22000,
        "tracking_events": 150000,
        "support_cases": 4000,
        "app_events": 199781,
    }

    for table_name, expected_count in expected_counts.items():
        actual_count = connection.execute(
            f"""
            SELECT COUNT(*)
            FROM bronze.{table_name}
            """
        ).fetchone()[0]

        assert actual_count == expected_count


def test_silver_tables_exist(connection):
    expected = {
        "orders_enriched",
        "shipments_enriched",
        "support_enriched",
        "app_funnel_daily",
        "daily_purchase_reconciliation",
        "warehouse_anomaly_windows",
    }

    actual = {
        row[0]
        for row in connection.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'silver'
            """
        ).fetchall()
    }

    assert expected.issubset(actual)


def test_silver_business_keys_are_unique(connection):
    checks = {
        "orders_enriched": "order_id",
        "shipments_enriched": "shipment_id",
        "support_enriched": "case_id",
    }

    for table_name, key_name in checks.items():
        duplicate_count = connection.execute(
            f"""
            SELECT COUNT(*)
            FROM (
                SELECT
                    {key_name}
                FROM silver.{table_name}
                GROUP BY {key_name}
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]

        assert duplicate_count == 0


def test_orders_payment_reconciliation(connection):
    result = connection.execute(
        """
        SELECT COUNT(*)
        FROM silver.orders_enriched
        WHERE ABS(payment_reconciliation_delta_eur) > 0.01
        """
    ).fetchone()[0]

    assert result == 0


def test_app_purchase_reconciliation(connection):
    bronze_purchases = connection.execute(
        """
        SELECT COUNT(*)
        FROM bronze.app_events
        WHERE event_type = 'purchase'
        """
    ).fetchone()[0]

    silver_purchases = connection.execute(
        """
        SELECT SUM(purchase_events)
        FROM silver.app_funnel_daily
        """
    ).fetchone()[0]

    assert bronze_purchases == 23760
    assert silver_purchases == 23760


def test_purchase_reconciliation_detects_incident(
    connection,
):
    result = connection.execute(
        """
        SELECT
            COUNT(*),
            SUM(expected_purchase_count),
            SUM(observed_purchase_count),
            SUM(
                expected_purchase_count
                - observed_purchase_count
            )

        FROM silver.daily_purchase_reconciliation

        WHERE incident_flag = 1
        """
    ).fetchone()

    assert result[0] == 7
    assert result[1] == 523
    assert result[2] == 304
    assert result[3] == 219


def test_business_anomaly_candidate_exists(
    connection,
):
    result = connection.execute(
        """
        SELECT
            COUNT(*),
            MAX(waw.anomaly_score)

        FROM silver.warehouse_anomaly_windows AS waw

        INNER JOIN bronze.warehouses AS w
            ON waw.warehouse_id = w.warehouse_id

        WHERE
            w.city = 'Warsaw'
            AND w.country = 'Poland'
            AND waw.anomaly_score >= 75
            AND waw.delay_delta_pp >= 18
            AND waw.load_delta_pp >= 20
        """
    ).fetchone()

    assert result[0] > 0
    assert result[1] >= 98.0

def test_pipeline_metadata_exists(connection):
    result = connection.execute(
        """
        SELECT COUNT(*)
        FROM meta.pipeline_runs
        """
    ).fetchone()[0]

    assert result > 0
