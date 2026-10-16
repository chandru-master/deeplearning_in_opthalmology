"""Tests for S3 ingestion."""

import csv
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from config import PipelineConfig
from s3_ingestion import S3Ingester


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    os.environ["SNOWFLAKE_PASSWORD"] = "test-pass"
    
    return PipelineConfig(
        aws_region="us-east-1",
        aws_profile="default",
        s3_bucket="test-bucket",
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
def mock_logger():
    """Create mock logger."""
    return MagicMock()


def test_get_s3_path_format(mock_config, mock_logger):
    """Test S3 path is constructed correctly."""
    ingester = S3Ingester(mock_config, mock_logger)
    target_date = datetime(2025, 1, 15)

    path = ingester._get_s3_path(target_date)

    assert path == "orders/2025-01-15/orders.csv"


def test_validate_csv_schema_success(mock_config, mock_logger, tmp_path):
    """Test schema validation passes with correct columns."""
    csv_file = tmp_path / "orders.csv"
    with open(csv_file, "w") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["order_id", "customer_id", "order_date", "amount", "status"],
        )
        writer.writeheader()
        writer.writerow({
            "order_id": "1",
            "customer_id": "100",
            "order_date": "2025-01-15",
            "amount": "99.99",
            "status": "pending",
        })

    ingester = S3Ingester(mock_config, mock_logger)
    is_valid, error = ingester.validate_csv_schema(str(csv_file))

    assert is_valid is True
    assert error is None


def test_validate_csv_schema_missing_column(mock_config, mock_logger, tmp_path):
    """Test schema validation fails with missing column."""
    csv_file = tmp_path / "orders.csv"
    with open(csv_file, "w") as f:
        writer = csv.DictWriter(f, fieldnames=["order_id", "customer_id", "amount"])
        writer.writeheader()

    ingester = S3Ingester(mock_config, mock_logger)
    is_valid, error = ingester.validate_csv_schema(str(csv_file))

    assert is_valid is False
    assert "missing" in error.lower()


def test_validate_csv_schema_encoding_error(mock_config, mock_logger, tmp_path):
    """Test schema validation fails on encoding error."""
    csv_file = tmp_path / "orders.csv"
    # Write invalid UTF-8
    with open(csv_file, "wb") as f:
        f.write(b"\xff\xfe")

    ingester = S3Ingester(mock_config, mock_logger)
    is_valid, error = ingester.validate_csv_schema(str(csv_file))

    assert is_valid is False
    assert "encoding" in error.lower()
