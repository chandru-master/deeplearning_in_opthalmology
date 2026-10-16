"""Tests for configuration loading."""

import os
import pytest

from config import PipelineConfig


def test_config_from_env():
    """Test loading configuration from environment."""
    os.environ["AWS_REGION"] = "us-west-2"
    os.environ["S3_BUCKET"] = "test-bucket"
    os.environ["SNOWFLAKE_ACCOUNT"] = "test-account"
    os.environ["SNOWFLAKE_USER"] = "test-user"
    os.environ["SNOWFLAKE_PASSWORD"] = "test-password"
    os.environ["SNOWFLAKE_WAREHOUSE"] = "test-warehouse"
    os.environ["SNOWFLAKE_DATABASE"] = "test-db"
    os.environ["SNOWFLAKE_SCHEMA"] = "test-schema"
    os.environ["CSV_EXPECTED_COLUMNS"] = "order_id,customer_id,order_date,amount,status"
    os.environ["VALID_ORDER_STATUSES"] = "pending,completed,cancelled"

    config = PipelineConfig.from_env()

    assert config.aws_region == "us-west-2"
    assert config.s3_bucket == "test-bucket"
    assert config.snowflake_account == "test-account"
    assert config.csv_expected_columns == [
        "order_id",
        "customer_id",
        "order_date",
        "amount",
        "status",
    ]
    assert config.valid_order_statuses == ["pending", "completed", "cancelled"]


def test_config_validate_missing_required():
    """Test validation fails when required config missing."""
    # Create minimal config with missing s3_bucket
    os.environ["SNOWFLAKE_PASSWORD"] = "test-pass"
    
    config = PipelineConfig(
        aws_region="us-east-1",
        aws_profile="default",
        s3_bucket="",  # Empty
        s3_prefix="orders",
        snowflake_account="account",
        snowflake_user="user",
        snowflake_password=os.environ["SNOWFLAKE_PASSWORD"],
        snowflake_warehouse="warehouse",
        snowflake_database="db",
        snowflake_schema="schema",
        snowflake_audit_table="audit",
        csv_expected_columns=[],
        valid_order_statuses=[],
        max_retries=3,
        retry_delay_seconds=5,
        log_level="INFO",
    )

    with pytest.raises(ValueError, match="Missing required configuration: s3_bucket"):
        config.validate()
