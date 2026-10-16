"""In-Snowflake transformation and validation logic."""

import logging
from datetime import datetime
from typing import Optional

from config import PipelineConfig
from snowflake_loader import SnowflakeLoader


class SnowflakeTransformer:
    """Handles SQL-based transformation and quality checks in Snowflake."""

    def __init__(
        self, loader: SnowflakeLoader, config: PipelineConfig, logger: logging.Logger
    ):
        self.loader = loader
        self.config = config
        self.logger = logger

    def transform(self, target_date: datetime) -> int:
        """
        Transform raw data into clean, typed table.
        Returns count of transformed rows.
        """
        # Ensure transformed table exists
        self.loader._execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.config.snowflake_schema}.stg_orders_transformed (
                order_id INTEGER,
                customer_id INTEGER,
                order_date DATE,
                amount NUMERIC(10, 2),
                status VARCHAR(50),
                _load_date DATE,
                _transformed_at TIMESTAMP_NTZ
            )
            """
        )

        # Clear transformed table for this date
        self.loader._execute(
            f"DELETE FROM {self.config.snowflake_schema}.stg_orders_transformed WHERE _load_date = %s",
            [target_date.date()],
        )

        # Transform and load into transformed table
        # Type casting, null handling, business rule validation
        transform_sql = f"""
        INSERT INTO {self.config.snowflake_schema}.stg_orders_transformed
        (order_id, customer_id, order_date, amount, status, _load_date, _transformed_at)
        SELECT
            TRY_CAST(order_id AS INTEGER) as order_id,
            TRY_CAST(customer_id AS INTEGER) as customer_id,
            TRY_CAST(order_date AS DATE) as order_date,
            TRY_CAST(amount AS NUMERIC(10, 2)) as amount,
            UPPER(TRIM(status)) as status,
            %s,
            CURRENT_TIMESTAMP()
        FROM {self.config.snowflake_schema}.stg_orders_raw
        WHERE _load_date = %s
          AND order_id IS NOT NULL
          AND customer_id IS NOT NULL
          AND order_date IS NOT NULL
          AND amount IS NOT NULL
          AND status IS NOT NULL
        """

        self.loader._execute(transform_sql, [target_date.date(), target_date.date()])
        self.loader.conn.commit()

        # Count transformed rows
        count_result = self.loader._execute(
            f"SELECT COUNT(*) FROM {self.config.snowflake_schema}.stg_orders_transformed WHERE _load_date = %s",
            [target_date.date()],
        )
        transformed_count = count_result[0][0] if count_result else 0
        self.logger.info(f"Transformed {transformed_count} rows")
        return transformed_count

    def run_quality_checks(self, target_date: datetime) -> bool:
        """
        Run business rule and data quality checks.
        Returns True if all checks pass, False otherwise.
        """
        checks_passed = True

        # Check 1: No NULL values in transformed table
        null_check = self.loader._execute(
            f"""
            SELECT COUNT(*)
            FROM {self.config.snowflake_schema}.stg_orders_transformed
            WHERE _load_date = %s
              AND (order_id IS NULL OR customer_id IS NULL OR order_date IS NULL
                   OR amount IS NULL OR status IS NULL)
            """,
            [target_date.date()],
        )
        null_count = null_check[0][0] if null_check else 0
        if null_count > 0:
            self.logger.error(f"Quality check failed: {null_count} rows with NULL values")
            checks_passed = False
        else:
            self.logger.info("Quality check passed: No NULL values")

        # Check 2: Amount > 0
        amount_check = self.loader._execute(
            f"""
            SELECT COUNT(*)
            FROM {self.config.snowflake_schema}.stg_orders_transformed
            WHERE _load_date = %s AND amount <= 0
            """,
            [target_date.date()],
        )
        invalid_amount_count = amount_check[0][0] if amount_check else 0
        if invalid_amount_count > 0:
            self.logger.error(f"Quality check failed: {invalid_amount_count} rows with amount <= 0")
            checks_passed = False
        else:
            self.logger.info("Quality check passed: All amounts > 0")

        # Check 3: Valid status values
        status_placeholders = ",".join([f"'{s}'" for s in self.config.valid_order_statuses])
        status_check = self.loader._execute(
            f"""
            SELECT COUNT(*)
            FROM {self.config.snowflake_schema}.stg_orders_transformed
            WHERE _load_date = %s AND status NOT IN ({status_placeholders})
            """,
            [target_date.date()],
        )
        invalid_status_count = status_check[0][0] if status_check else 0
        if invalid_status_count > 0:
            self.logger.error(
                f"Quality check failed: {invalid_status_count} rows with invalid status"
            )
            checks_passed = False
        else:
            self.logger.info("Quality check passed: All statuses valid")

        # Check 4: Order date not in future
        future_check = self.loader._execute(
            f"""
            SELECT COUNT(*)
            FROM {self.config.snowflake_schema}.stg_orders_transformed
            WHERE _load_date = %s AND order_date > CURRENT_DATE()
            """,
            [target_date.date()],
        )
        future_date_count = future_check[0][0] if future_check else 0
        if future_date_count > 0:
            self.logger.error(f"Quality check failed: {future_date_count} rows with future dates")
            checks_passed = False
        else:
            self.logger.info("Quality check passed: No future dates")

        return checks_passed
