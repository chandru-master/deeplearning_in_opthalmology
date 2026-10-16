"""S3 CSV ingestion and file management."""

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Set, Tuple

import boto3

from config import PipelineConfig


class S3Ingester:
    """Handles S3 CSV download and validation."""

    def __init__(self, config: PipelineConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.s3_client = boto3.client(
            "s3",
            region_name=config.aws_region,
            profile_name=config.aws_profile if config.aws_profile != "default" else None,
        )

    def _get_s3_path(self, target_date: datetime) -> str:
        """Construct S3 path for target date: s3://bucket/prefix/YYYY-MM-DD/orders.csv"""
        date_str = target_date.strftime("%Y-%m-%d")
        return f"{self.config.s3_prefix}/{date_str}/orders.csv"

    def download_csv(self, target_date: datetime) -> Optional[str]:
        """
        Download CSV from S3 for target date.
        Returns local file path if successful, None if file not found.
        """
        s3_key = self._get_s3_path(target_date)
        local_dir = Path("data/input")
        local_dir.mkdir(parents=True, exist_ok=True)

        date_str = target_date.strftime("%Y%m%d")
        local_path = local_dir / f"orders_{date_str}.csv"

        try:
            self.s3_client.head_object(Bucket=self.config.s3_bucket, Key=s3_key)
        except self.s3_client.exceptions.NoSuchKey:
            self.logger.warning(f"S3 key not found: s3://{self.config.s3_bucket}/{s3_key}")
            return None
        except Exception as e:
            self.logger.error(f"Error checking S3 object: {e}")
            raise

        try:
            self.s3_client.download_file(
                self.config.s3_bucket, s3_key, str(local_path)
            )
            self.logger.info(f"Downloaded s3://{self.config.s3_bucket}/{s3_key} to {local_path}")
            return str(local_path)
        except Exception as e:
            self.logger.error(f"Error downloading CSV from S3: {e}")
            raise

    def validate_csv_schema(self, csv_path: str) -> Tuple[bool, Optional[str]]:
        """
        Validate CSV has expected columns.
        Returns (is_valid, error_message).
        """
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    return False, "CSV is empty or malformed"

                expected_set = set(self.config.csv_expected_columns)
                actual_set = set(reader.fieldnames)

                if expected_set != actual_set:
                    missing = expected_set - actual_set
                    extra = actual_set - expected_set
                    msg = f"Schema mismatch"
                    if missing:
                        msg += f" | missing: {missing}"
                    if extra:
                        msg += f" | extra: {extra}"
                    return False, msg

            return True, None
        except UnicodeDecodeError as e:
            return False, f"Encoding error: {e}"
        except Exception as e:
            return False, f"CSV validation error: {e}"
