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
    / "05_commerce_performance.sql"
)


def main():
    print("=" * 72)
    print(
        "AEGIS GOLD COMMERCE PERFORMANCE MART"
    )
    print("=" * 72)

    connection = duckdb.connect(
        str(DATABASE_PATH)
    )

    try:
        print()
        print(
            "Running 05_commerce_performance.sql..."
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

                SUM(orders)
                    AS orders,

                SUM(completed_orders)
                    AS completed_orders,

                SUM(returned_orders)
                    AS returned_orders,

                SUM(cancelled_orders)
                    AS cancelled_orders,

                SUM(pending_orders)
                    AS pending_orders,

                SUM(units)
                    AS units,

                ROUND(
                    SUM(
                        total_order_value_eur
                    ),
                    2
                ) AS order_value,

                ROUND(
                    SUM(
                        completed_revenue_eur
                    ),
                    2
                ) AS completed_revenue,

                ROUND(
                    SUM(
                        returned_value_eur
                    ),
                    2
                ) AS returned_value,

                SUM(
                    reconciliation_mismatch_orders
                ) AS mismatches,

                MIN(report_date)
                    AS min_date,

                MAX(report_date)
                    AS max_date

            FROM gold.commerce_performance
            """
        ).fetchone()

        source = connection.execute(
            """
            SELECT
                COUNT(*),

                SUM(
                    CASE
                        WHEN order_status = 'Completed'
                        THEN 1 ELSE 0
                    END
                ),

                SUM(
                    CASE
                        WHEN order_status = 'Returned'
                        THEN 1 ELSE 0
                    END
                ),

                SUM(
                    CASE
                        WHEN order_status = 'Cancelled'
                        THEN 1 ELSE 0
                    END
                ),

                SUM(
                    CASE
                        WHEN order_status = 'Pending'
                        THEN 1 ELSE 0
                    END
                ),

                SUM(item_units),

                ROUND(
                    SUM(order_total_eur),
                    2
                )

            FROM silver.orders_enriched

            WHERE order_date BETWEEN
                DATE '2025-01-01'
                AND DATE '2025-12-31'
            """
        ).fetchone()

        if summary[1] != source[0]:
            raise AssertionError(
                "Order reconciliation failed."
            )

        if summary[2] != source[1]:
            raise AssertionError(
                "Completed order reconciliation failed."
            )

        if summary[3] != source[2]:
            raise AssertionError(
                "Returned order reconciliation failed."
            )

        if summary[4] != source[3]:
            raise AssertionError(
                "Cancelled order reconciliation failed."
            )

        if summary[5] != source[4]:
            raise AssertionError(
                "Pending order reconciliation failed."
            )

        if summary[6] != source[5]:
            raise AssertionError(
                "Unit reconciliation failed."
            )

        if abs(
            summary[7]
            - source[6]
        ) > 0.01:
            raise AssertionError(
                "Order value reconciliation failed."
            )

        if summary[10] != 0:
            raise AssertionError(
                "Payment reconciliation mismatches detected."
            )

        status_total = (
            summary[2]
            + summary[3]
            + summary[4]
            + summary[5]
        )

        if status_total != summary[1]:
            raise AssertionError(
                "Order status totals do not reconcile."
            )

        print()
        print("=" * 72)
        print(
            "GOLD COMMERCE PERFORMANCE SUMMARY"
        )
        print("=" * 72)

        print()

        print(
            f"Mart rows:             "
            f"{summary[0]:,}"
        )

        print(
            f"Orders:                "
            f"{summary[1]:,}"
        )

        print(
            f"Completed:             "
            f"{summary[2]:,}"
        )

        print(
            f"Returned:              "
            f"{summary[3]:,}"
        )

        print(
            f"Cancelled:             "
            f"{summary[4]:,}"
        )

        print(
            f"Pending:               "
            f"{summary[5]:,}"
        )

        print(
            f"Units:                 "
            f"{summary[6]:,}"
        )

        print()

        print(
            f"Total order value:     "
            f"€{summary[7]:,.2f}"
        )

        print(
            f"Completed revenue:     "
            f"€{summary[8]:,.2f}"
        )

        print(
            f"Returned value:        "
            f"€{summary[9]:,.2f}"
        )

        print()

        print(
            f"Payment mismatches:    "
            f"{summary[10]}"
        )

        print(
            f"Date range:            "
            f"{summary[11]} "
            f"to {summary[12]}"
        )

        print()

        payment = connection.execute(
            """
            SELECT
                ROUND(
                    SUM(paid_payments)
                    * 100.0
                    / NULLIF(
                        SUM(orders),
                        0
                    ),
                    2
                ) AS payment_success_pct,

                ROUND(
                    SUM(completed_revenue_eur)
                    / NULLIF(
                        SUM(completed_orders),
                        0
                    ),
                    2
                ) AS completed_aov

            FROM gold.commerce_performance
            """
        ).fetchone()

        print(
            f"Payment success:       "
            f"{payment[0]:.2f}%"
        )

        print(
            f"Completed AOV:         "
            f"€{payment[1]:,.2f}"
        )

        print()

        print(
            "GOLD COMMERCE CONTRACT: PASSED"
        )

    finally:
        connection.close()


if __name__ == "__main__":
    main()
