"""Pipeline configuration from environment variables."""

import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv

load_dotenv()


@dataclass
class PipelineConfig:
    """Configuration loaded from environment."""

    # AWS
    aws_region: str
    aws_profile: str
    s3_bucket: str
    s3_prefix: str

    # Snowflake
    snowflake_account: str
    snowflake_user: str
    snowflake_password: str
    snowflake_warehouse: str
    snowflake_database: str
    snowflake_schema: str
    snowflake_audit_table: str

    # CSV schema and validation
    csv_expected_columns: List[str]
    valid_order_statuses: List[str]

    # Pipeline behavior
    max_retries: int
    retry_delay_seconds: int
    log_level: str

    @classmethod
    def from_env(cls) -> "PipelineConfig":
        """Load configuration from environment."""
        csv_columns = os.getenv("CSV_EXPECTED_COLUMNS", "")
        csv_expected_columns = [c.strip() for c in csv_columns.split(",")] if csv_columns else []

        valid_statuses = os.getenv("VALID_ORDER_STATUSES", "")
        valid_order_statuses = [s.strip() for s in valid_statuses.split(",")] if valid_statuses else []

        return cls(
            aws_region=os.getenv("AWS_REGION", "us-east-1"),
            aws_profile=os.getenv("AWS_PROFILE", "default"),
            s3_bucket=os.getenv("S3_BUCKET", ""),
            s3_prefix=os.getenv("S3_PREFIX", "orders"),
            snowflake_account=os.getenv("SNOWFLAKE_ACCOUNT", ""),
            snowflake_user=os.getenv("SNOWFLAKE_USER", ""),
            snowflake_password=os.getenv("SNOWFLAKE_PASSWORD", ""),
            snowflake_warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", ""),
            snowflake_database=os.getenv("SNOWFLAKE_DATABASE", ""),
            snowflake_schema=os.getenv("SNOWFLAKE_SCHEMA", ""),
            snowflake_audit_table=os.getenv("SNOWFLAKE_AUDIT_TABLE", "audit_pipeline_execution"),
            csv_expected_columns=csv_expected_columns,
            valid_order_statuses=valid_order_statuses,
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            retry_delay_seconds=int(os.getenv("RETRY_DELAY_SECONDS", "5")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )

    def validate(self) -> None:
        """Validate required configuration is present."""
        required = [
            "s3_bucket",
            "snowflake_account",
            "snowflake_user",
            "snowflake_password",
            "snowflake_warehouse",
            "snowflake_database",
            "snowflake_schema",
        ]
        for field in required:
            if not getattr(self, field):
                raise ValueError(f"Missing required configuration: {field}")
