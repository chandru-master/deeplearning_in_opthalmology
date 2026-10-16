"""Configuration management for ETL pipeline."""
import os
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseSettings, validator

load_dotenv()


class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    # AWS Configuration
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    aws_s3_bucket: str = os.getenv("AWS_S3_BUCKET")
    s3_orders_path: str = os.getenv("S3_ORDERS_PATH", "orders/")
    
    # Snowflake Configuration
    snowflake_account: str = os.getenv("SNOWFLAKE_ACCOUNT")
    snowflake_user: str = os.getenv("SNOWFLAKE_USER")
    snowflake_password: Optional[str] = os.getenv("SNOWFLAKE_PASSWORD")
    snowflake_private_key_path: Optional[str] = os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH")
    snowflake_private_key_passphrase: Optional[str] = os.getenv("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE")
    snowflake_warehouse: str = os.getenv("SNOWFLAKE_WAREHOUSE")
    snowflake_database: str = os.getenv("SNOWFLAKE_DATABASE")
    snowflake_schema: str = os.getenv("SNOWFLAKE_SCHEMA")
    
    # Table Configuration
    target_table_name: str = os.getenv("TARGET_TABLE_NAME", "orders")
    rejection_table_name: str = os.getenv("REJECTION_TABLE_NAME", "stg_orders_rejected")
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    @validator("aws_s3_bucket")
    def validate_s3_bucket(cls, v):
        if not v:
            raise ValueError("AWS_S3_BUCKET must be set")
        return v
    
    @validator("snowflake_account")
    def validate_snowflake_account(cls, v):
        if not v:
            raise ValueError("SNOWFLAKE_ACCOUNT must be set")
        return v
    
    @validator("snowflake_user")
    def validate_snowflake_user(cls, v):
        if not v:
            raise ValueError("SNOWFLAKE_USER must be set")
        return v
    
    class Config:
        case_sensitive = False


config = Settings()
