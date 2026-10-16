"""AWS S3 file handling."""
from typing import Optional
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError
import pandas as pd
from etl.config import config
from etl.logger import setup_logger

logger = setup_logger(__name__)


class S3Handler:
    """Handle S3 operations for CSV ingestion."""
    
    def __init__(self):
        self.s3_client = boto3.client("s3", region_name=config.aws_region)
        self.bucket = config.aws_s3_bucket
        self.path_prefix = config.s3_orders_path
    
    def list_csv_files(self, hours_back: int = 24) -> list[str]:
        """List CSV files modified in the last N hours.
        
        Args:
            hours_back: Number of hours to look back (default 24 for daily)
            
        Returns:
            List of S3 object keys
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
            paginator = self.s3_client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self.bucket, Prefix=self.path_prefix)
            
            csv_files = []
            for page in pages:
                if "Contents" not in page:
                    continue
                for obj in page["Contents"]:
                    if obj["Key"].endswith(".csv") and obj["LastModified"].replace(tzinfo=None) >= cutoff_time:
                        csv_files.append(obj["Key"])
            
            logger.info(f"Found {len(csv_files)} CSV files in S3 from last {hours_back} hours")
            return csv_files
        except ClientError as e:
            logger.error(f"Error listing S3 files: {e}")
            raise
    
    def read_csv(self, s3_key: str) -> pd.DataFrame:
        """Read CSV file from S3.
        
        Args:
            s3_key: S3 object key
            
        Returns:
            Pandas DataFrame
        """
        try:
            logger.info(f"Reading CSV from s3://{self.bucket}/{s3_key}")
            obj = self.s3_client.get_object(Bucket=self.bucket, Key=s3_key)
            df = pd.read_csv(obj["Body"], dtype=str, keep_default_na=False)
            logger.info(f"Successfully read {len(df)} rows from {s3_key}")
            return df
        except ClientError as e:
            logger.error(f"Error reading CSV from S3: {e}")
            raise
        except pd.errors.ParserError as e:
            logger.error(f"Error parsing CSV: {e}")
            raise
    
    def mark_file_processed(self, s3_key: str) -> None:
        """Add metadata tag to file to mark as processed.
        
        Args:
            s3_key: S3 object key
        """
        try:
            self.s3_client.put_object_tagging(
                Bucket=self.bucket,
                Key=s3_key,
                Tagging={
                    "TagSet": [
                        {"Key": "processed", "Value": "true"},
                        {"Key": "processed_at", "Value": datetime.utcnow().isoformat()}
                    ]
                }
            )
            logger.info(f"Marked {s3_key} as processed")
        except ClientError as e:
            logger.error(f"Error tagging file: {e}")
            raise
