"""Snowflake database operations."""
from typing import Dict, Any, List
from pathlib import Path
import pandas as pd
from snowflake.connector import connect, DictCursor
from snowflake.connector.errors import DatabaseError, ProgrammingError
from etl.config import config
from etl.logger import setup_logger

logger = setup_logger(__name__)


class SnowflakeHandler:
    """Handle Snowflake operations."""
    
    def __init__(self):
        self.config = {
            "account": config.snowflake_account,
            "user": config.snowflake_user,
            "warehouse": config.snowflake_warehouse,
            "database": config.snowflake_database,
            "schema": config.snowflake_schema,
        }
        
        # Use private key auth if available, otherwise password
        if config.snowflake_private_key_path:
            private_key_path = Path(config.snowflake_private_key_path)
            if not private_key_path.exists():
                raise FileNotFoundError(f"Private key not found: {config.snowflake_private_key_path}")
            with open(private_key_path, "rb") as key_file:
                self.config["private_key_content"] = key_file.read()
            if config.snowflake_private_key_passphrase:
                self.config["private_key_passphrase"] = config.snowflake_private_key_passphrase
        elif config.snowflake_password:
            self.config["password"] = config.snowflake_password
        else:
            raise ValueError("Either SNOWFLAKE_PASSWORD or SNOWFLAKE_PRIVATE_KEY_PATH must be set")
        
        self.conn = None
    
    def connect(self) -> None:
        """Establish Snowflake connection."""
        try:
            self.conn = connect(**self.config)
            logger.info(f"Connected to Snowflake: {config.snowflake_account}/{config.snowflake_database}.{config.snowflake_schema}")
        except DatabaseError as e:
            logger.error(f"Failed to connect to Snowflake: {e}")
            raise
    
    def disconnect(self) -> None:
        """Close Snowflake connection."""
        if self.conn:
            self.conn.close()
            logger.info("Disconnected from Snowflake")
    
    def table_exists(self, table_name: str) -> bool:
        """Check if table exists."""
        try:
            cursor = self.conn.cursor(DictCursor)
            query = f"SHOW TABLES LIKE '{table_name}'"
            cursor.execute(query)
            result = cursor.fetchone()
            return result is not None
        finally:
            cursor.close()
    
    def truncate_and_load(self, df: pd.DataFrame, table_name: str) -> int:
        """Truncate table and load DataFrame (full replacement).
        
        Args:
            df: DataFrame to load
            table_name: Target table name
            
        Returns:
            Number of rows loaded
        """
        try:
            cursor = self.conn.cursor()
            
            # Truncate table
            logger.info(f"Truncating {table_name}")
            cursor.execute(f"TRUNCATE TABLE {table_name}")
            
            # Prepare data for insert
            if df.empty:
                logger.info(f"No rows to load into {table_name}")
                return 0
            
            # Build INSERT statement
            columns = ", ".join(df.columns)
            placeholders = ", ".join(["?" for _ in df.columns])
            insert_sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
            
            # Convert DataFrame to list of tuples
            records = [tuple(row) for row in df.values]
            
            # Batch insert
            batch_size = 1000
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                cursor.executemany(insert_sql, batch)
            
            self.conn.commit()
            logger.info(f"Successfully loaded {len(df)} rows into {table_name}")
            return len(df)
        
        except (DatabaseError, ProgrammingError) as e:
            self.conn.rollback()
            logger.error(f"Error loading data: {e}")
            raise
        finally:
            cursor.close()
    
    def create_rejection_table(self) -> None:
        """Create rejection table if it doesn't exist."""
        try:
            table_name = config.rejection_table_name
            if not self.table_exists(table_name):
                cursor = self.conn.cursor()
                create_sql = f"""
                CREATE TABLE {table_name} (
                    rejection_id INTEGER AUTOINCREMENT,
                    execution_date DATE DEFAULT CURRENT_DATE(),
                    row_number INTEGER,
                    error_message VARCHAR(8192),
                    rejected_at TIMESTAMP_NTZ,
                    source_record VARCHAR(8192)
                )
                """
                cursor.execute(create_sql)
                self.conn.commit()
                logger.info(f"Created rejection table: {table_name}")
                cursor.close()
        except (DatabaseError, ProgrammingError) as e:
            logger.error(f"Error creating rejection table: {e}")
            raise
    
    def insert_rejections(self, rejections: List[Dict[str, Any]]) -> int:
        """Insert rejected records into rejection table.
        
        Args:
            rejections: List of rejection dictionaries
            
        Returns:
            Number of rejection records inserted
        """
        if not rejections:
            return 0
        
        try:
            cursor = self.conn.cursor()
            table_name = config.rejection_table_name
            
            insert_sql = f"""
            INSERT INTO {table_name} (row_number, error_message, rejected_at, source_record)
            VALUES (?, ?, ?, ?)
            """
            
            records = [(r["row_number"], r["error_message"], r["rejected_at"], r["source_record"]) 
                       for r in rejections]
            
            cursor.executemany(insert_sql, records)
            self.conn.commit()
            logger.info(f"Inserted {len(rejections)} rejection records")
            return len(rejections)
        
        except (DatabaseError, ProgrammingError) as e:
            self.conn.rollback()
            logger.error(f"Error inserting rejections: {e}")
            raise
        finally:
            cursor.close()
    
    def get_row_count(self, table_name: str) -> int:
        """Get row count for table."""
        try:
            cursor = self.conn.cursor(DictCursor)
            cursor.execute(f"SELECT COUNT(*) as cnt FROM {table_name}")
            result = cursor.fetchone()
            return result["CNT"] if result else 0
        finally:
            cursor.close()
