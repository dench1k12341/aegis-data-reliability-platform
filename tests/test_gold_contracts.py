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


def test_gold_tables_exist(connection):
    expected_tables = {
        "executive_daily",
        "logistics_performance",
        "data_reliability_daily",
        "customer_experience",
        "commerce_performance",
        "incident_command_center",
    }

    actual_tables = {
        row[0]
        for row in connection.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'gold'
            """
        ).fetchall()
    }

    assert expected_tables.issubset(
        actual_tables
    )


def test_executive_daily_contract(connection):
    result = connection.execute(
        """
        SELECT
            COUNT(*),
            COUNT(DISTINCT report_date),
            SUM(orders),
            SUM(shipments),
            SUM(data_incident_flag)

        FROM gold.executive_daily
        """
    ).fetchone()

    assert result[0] == 365
    assert result[1] == 365
    assert result[2] == 25000
    assert result[3] == 22000
    assert result[4] == 7


def test_data_incident_contract(connection):
    result = connection.execute(
        """
        SELECT
            MIN(report_date),
            MAX(report_date),
            SUM(expected_purchase_count),
            SUM(observed_purchase_count),
            SUM(missing_purchase_events),
            SUM(purchase_value_null_count)

        FROM gold.data_reliability_daily

        WHERE data_incident_flag = 1
        """
    ).fetchone()

    assert str(result[0]) == "2025-09-08"
    assert str(result[1]) == "2025-09-14"
    assert result[2] == 523
    assert result[3] == 304
    assert result[4] == 219
    assert result[5] == 136


def test_warsaw_business_incident_contract(
    connection,
):
    result = connection.execute(
        """
        SELECT
            SUM(lp.shipment_touches),

            ROUND(
                SUM(lp.delayed_shipments)
                * 100.0
                / SUM(lp.shipment_touches),
                2
            ),

            ROUND(
                SUM(lp.sla_met_shipments)
                * 100.0
                / SUM(lp.shipment_touches),
                2
            ),

            ROUND(
                SUM(
                    lp.avg_network_load_pct
                    * lp.shipment_touches
                )
                / SUM(lp.shipment_touches),
                2
            )

        FROM gold.logistics_performance AS lp

        INNER JOIN bronze.warehouses AS w
            ON lp.warehouse_id = w.warehouse_id

        WHERE
            lp.business_incident_flag = 1
            AND w.city = 'Warsaw'
            AND w.country = 'Poland'
        """
    ).fetchone()

    assert result[0] == 27
    assert result[1] == 100.00
    assert result[2] == 0.00
    assert result[3] == pytest.approx(
        109.31,
        abs=0.02,
    )

def test_customer_impact_contract(
    connection,
):
    result = connection.execute(
        """
        SELECT
            SUM(support_cases),

            ROUND(
                SUM(
                    support_sla_pct
                    * support_cases
                )
                / SUM(support_cases),
                2
            ),

            ROUND(
                SUM(
                    avg_csat
                    * support_cases
                )
                / SUM(support_cases),
                2
            )

        FROM gold.customer_experience

        WHERE business_incident_flag = 1
        """
    ).fetchone()

    assert result[0] == 4
    assert result[1] == 0.00
    assert result[2] == 3.25


def test_commerce_reconciliation_contract(
    connection,
):
    result = connection.execute(
        """
        SELECT
            SUM(orders),
            SUM(completed_orders),
            SUM(returned_orders),
            SUM(cancelled_orders),
            SUM(pending_orders),
            SUM(reconciliation_mismatch_orders)

        FROM gold.commerce_performance
        """
    ).fetchone()

    assert result[0] == 25000
    assert result[1] == 23354
    assert result[2] == 625
    assert result[3] == 636
    assert result[4] == 385
    assert result[5] == 0


def test_incident_command_center_contract(
    connection,
):
    summary = connection.execute(
        """
        SELECT
            COUNT(*),

            SUM(
                CASE
                    WHEN classification = 'DATA_INCIDENT'
                    THEN 1
                    ELSE 0
                END
            ),

            SUM(
                CASE
                    WHEN classification = 'BUSINESS_INCIDENT'
                    THEN 1
                    ELSE 0
                END
            ),

            SUM(
                CASE
                    WHEN data_trust_status = 'FAILED'
                    THEN 1
                    ELSE 0
                END
            ),

            SUM(
                CASE
                    WHEN data_trust_status = 'PASSED'
                    THEN 1
                    ELSE 0
                END
            )

        FROM gold.incident_command_center
        """
    ).fetchone()

    assert summary == (
        2,
        1,
        1,
        1,
        1,
    )
