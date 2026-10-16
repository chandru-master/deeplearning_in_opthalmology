"""Tests for transformation logic."""

import os
from datetime import datetime
from unittest.mock import MagicMock, call

import pytest

from config import PipelineConfig
from transformation import SnowflakeTransformer


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    os.environ["SNOWFLAKE_PASSWORD"] = "test-pass"
    
    return PipelineConfig(
        aws_region="us-east-1",
        aws_profile="default",
        s3_bucket="bucket",
        s3_prefix="orders",
        snowflake_account="account",
        snowflake_user="user",
        snowflake_password=os.environ["SNOWFLAKE_PASSWORD"],
        snowflake_warehouse="warehouse",
        snowflake_database="db",
        snowflake_schema="schema",
        snowflake_audit_table="audit",
        csv_expected_columns=["order_id", "customer_id", "order_date", "amount", "status"],
        valid_order_statuses=["pending", "completed", "cancelled"],
        max_retries=3,
        retry_delay_seconds=5,
        log_level="INFO",
    )


@pytest.fixture
def mock_loader():
    """Create mock loader."""
    return MagicMock()


@pytest.fixture
def mock_logger():
    """Create mock logger."""
    return MagicMock()


def test_transform_creates_table_and_transforms_data(mock_config, mock_loader, mock_logger):
    """Test transform creates staging table and loads data."""
    transformer = SnowflakeTransformer(mock_loader, mock_config, mock_logger)
    target_date = datetime(2025, 1, 15)

    # Mock _execute to return transformed count
    mock_loader._execute.side_effect = [
        None,  # CREATE TABLE
        None,  # DELETE
        None,  # INSERT
        [(10,)],  # COUNT result
    ]

    result = transformer.transform(target_date)

    assert result == 10
    assert mock_loader._execute.call_count == 4
    mock_loader.conn.commit.assert_called_once()


def test_quality_checks_pass_when_valid_data(mock_config, mock_loader, mock_logger):
    """Test quality checks pass with valid transformed data."""
    transformer = SnowflakeTransformer(mock_loader, mock_config, mock_logger)
    target_date = datetime(2025, 1, 15)

    # Mock all quality check queries to return 0 (pass)
    mock_loader._execute.side_effect = [
        [(0,)],  # null check
        [(0,)],  # amount check
        [(0,)],  # status check
        [(0,)],  # future date check
    ]

    result = transformer.run_quality_checks(target_date)

    assert result is True
    assert mock_logger.info.call_count >= 4  # At least one info per check


def test_quality_checks_fail_on_null_values(mock_config, mock_loader, mock_logger):
    """Test quality checks fail when NULLs detected."""
    transformer = SnowflakeTransformer(mock_loader, mock_config, mock_logger)
    target_date = datetime(2025, 1, 15)

    # Mock null check to return failures
    mock_loader._execute.return_value = [(5,)]

    result = transformer.run_quality_checks(target_date)

    assert result is False
    mock_logger.error.assert_called_once()
