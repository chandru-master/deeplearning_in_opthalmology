"""Snowflake connection, CSV loading, and target operations."""

import csv
import logging
from datetime import datetime
from typing import Optional, Tuple

import snowflake.connector
from snowflake.connector.errors import ProgrammingError

from config import PipelineConfig
from retry import retry_on_transient_error


class SnowflakeLoader:
    """Manages Snowflake connection and data loading."""

    def __init__(self, config: PipelineConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.conn: Optional[snowflake.connector.SnowflakeConnection] = None

    def connect(self) -> None:
        """Establish Snowflake connection with retries."""
        @retry_on_transient_error(
            max_retries=self.config.max_retries,
            delay_seconds=self.config.retry_delay_seconds,
            logger=self.logger,
        )
        def _connect():
            self.conn = snowflake.connector.connect(
                account=self.config.snowflake_account,
                user=self.config.snowflake_user,
                password=self.config.snowflake_password,
                warehouse=self.config.snowflake_warehouse,
                database=self.config.snowflake_database,
                schema=self.config.snowflake_schema,
            )
            self.logger.info("Connected to Snowflake")

        _connect()

    def disconnect(self) -> None:
        """Close Snowflake connection."""
        if self.conn:
            self.conn.close()
            self.logger.info("Disconnected from Snowflake")

    def _execute(self, sql: str, params: list = None) -> list:
        """Execute SQL and return results with retry logic."""
        @retry_on_transient_error(
            max_retries=self.config.max_retries,
            delay_seconds=self.config.retry_delay_seconds,
            logger=self.logger,
        )
        def _exec():
            cursor = self.conn.cursor()
            try:
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                return cursor.fetchall()
            finally:
                cursor.close()

        return _exec()

    def load_raw_csv(self, csv_path: str, target_date: datetime) -> Tuple[int, int]:
        """
        Load CSV into raw staging table with error handling.
        Returns (loaded_count, rejected_count).
        """
        self.logger.info(f"Loading CSV: {csv_path}")
        loaded_count = 0
        rejected_count = 0

        # Ensure staging tables exist
        self._execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.config.snowflake_schema}.stg_orders_raw (
                order_id VARCHAR,
                customer_id VARCHAR,
                order_date VARCHAR,
                amount VARCHAR,
                status VARCHAR,
                _load_date DATE,
                _loaded_at TIMESTAMP_NTZ
            )
            """
        )

        self._execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.config.snowflake_schema}.stg_orders_rejected (
                order_id VARCHAR,
                customer_id VARCHAR,
                order_date VARCHAR,
                amount VARCHAR,
                status VARCHAR,
                error_reason VARCHAR,
                raw_row VARCHAR,
                rejected_at TIMESTAMP_NTZ,
                _load_date DATE
            )
            """
        )

        # Clear staging for this date (full load)
        self._execute(
            f"DELETE FROM {self.config.snowflake_schema}.stg_orders_raw WHERE _load_date = %s",
            [target_date.date()],
        )
        self._execute(
            f"DELETE FROM {self.config.snowflake_schema}.stg_orders_rejected WHERE _load_date = %s",
            [target_date.date()],
        )

        # Parse and insert CSV
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row_num, row in enumerate(reader, start=2):  # row 1 is header
                    try:
                        # Validate required fields not null
                        for col in self.config.csv_expected_columns:
                            if col not in row or row[col] is None or row[col].strip() == "":
                                raise ValueError(f"Missing required column: {col}")

                        cursor = self.conn.cursor()
                        cursor.execute(
                            f"""
                            INSERT INTO {self.config.snowflake_schema}.stg_orders_raw
                            (order_id, customer_id, order_date, amount, status, _load_date, _loaded_at)
                            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP())
                            """,
                            (
                                row["order_id"].strip(),
                                row["customer_id"].strip(),
                                row["order_date"].strip(),
                                row["amount"].strip(),
                                row["status"].strip(),
                                target_date.date(),
                            ),
                        )
                        cursor.close()
                        loaded_count += 1

                    except Exception as row_error:
                        raw_row = ",".join([str(v) for v in row.values()])
                        cursor = self.conn.cursor()
                        cursor.execute(
                            f"""
                            INSERT INTO {self.config.snowflake_schema}.stg_orders_rejected
                            (order_id, customer_id, order_date, amount, status, error_reason, raw_row, rejected_at, _load_date)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP(), %s)
                            """,
                            (
                                row.get("order_id", ""),
                                row.get("customer_id", ""),
                                row.get("order_date", ""),
                                row.get("amount", ""),
                                row.get("status", ""),
                                f"Row {row_num}: {str(row_error)[:200]}",
                                raw_row[:4000],
                                target_date.date(),
                            ),
                        )
                        cursor.close()
                        rejected_count += 1
                        self.logger.warning(
                            f"Rejected row {row_num}: {str(row_error)[:100]}"
                        )

            self.conn.commit()
            self.logger.info(
                f"Raw load complete: loaded={loaded_count}, rejected={rejected_count}"
            )
            return loaded_count, rejected_count

        except Exception as e:
            self.logger.error(f"Error loading CSV: {e}")
            raise

    def load_target(self, target_date: datetime) -> int:
        """
        Atomically load transformed data into target table.
        Full load: truncate and insert for the day.
        Returns count of rows inserted.
        """
        # Ensure target table exists
        self._execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.config.snowflake_schema}.orders (
                order_id INTEGER NOT NULL PRIMARY KEY,
                customer_id INTEGER NOT NULL,
                order_date DATE NOT NULL,
                amount NUMERIC(10, 2) NOT NULL,
                status VARCHAR(50) NOT NULL,
                _loaded_at TIMESTAMP_NTZ,
                _load_date DATE
            )
            """
        )

        # For full load, remove any existing records for this date
        self._execute(
            f"DELETE FROM {self.config.snowflake_schema}.orders WHERE _load_date = %s",
            [target_date.date()],
        )

        # Insert transformed data
        results = self._execute(
            f"""
            INSERT INTO {self.config.snowflake_schema}.orders
            (order_id, customer_id, order_date, amount, status, _loaded_at, _load_date)
            SELECT
                order_id,
                customer_id,
                order_date,
                amount,
                status,
                CURRENT_TIMESTAMP(),
                %s
            FROM {self.config.snowflake_schema}.stg_orders_transformed
            WHERE _load_date = %s
            """,
            [target_date.date(), target_date.date()],
        )

        # Get count of inserted rows
        count_result = self._execute(
            f"SELECT COUNT(*) FROM {self.config.snowflake_schema}.orders WHERE _load_date = %s",
            [target_date.date()],
        )
        row_count = count_result[0][0] if count_result else 0

        self.conn.commit()
        self.logger.info(f"Target load complete: {row_count} rows")
        return row_count

    def record_execution(
        self,
        execution_id: str,
        target_date: datetime,
        loaded_count: int,
        rejected_count: int,
        transformed_count: int,
        final_count: int,
        status: str,
        error_message: str = None,
    ) -> None:
        """
        Record pipeline execution metrics to audit table.
        """
        self._execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.config.snowflake_schema}.{self.config.snowflake_audit_table} (
                execution_id VARCHAR(100) NOT NULL,
                target_date DATE NOT NULL,
                loaded_count INTEGER,
                rejected_count INTEGER,
                transformed_count INTEGER,
                final_count INTEGER,
                status VARCHAR(50),
                error_message VARCHAR(500),
                executed_at TIMESTAMP_NTZ
            )
            """
        )

        self._execute(
            f"""
            INSERT INTO {self.config.snowflake_schema}.{self.config.snowflake_audit_table}
            (execution_id, target_date, loaded_count, rejected_count, transformed_count, final_count, status, error_message, executed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP())
            """,
            (
                execution_id,
                target_date.date(),
                loaded_count,
                rejected_count,
                transformed_count,
                final_count,
                status,
                error_message,
            ),
        )
        self.conn.commit()
