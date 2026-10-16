"""Main ETL pipeline orchestration."""
import sys
from datetime import datetime
from etl.logger import setup_logger
from etl.s3_handler import S3Handler
from etl.snowflake_handler import SnowflakeHandler
from etl.schema import validate_schema, standardize_types
from etl.config import config

logger = setup_logger(__name__)


class PipelineExecutor:
    """Orchestrate ETL pipeline execution."""
    
    def __init__(self):
        self.s3_handler = S3Handler()
        self.sf_handler = SnowflakeHandler()
        self.execution_stats = {
            "start_time": None,
            "end_time": None,
            "files_processed": 0,
            "rows_read": 0,
            "rows_valid": 0,
            "rows_rejected": 0,
            "rows_loaded": 0,
            "errors": []
        }
    
    def execute(self) -> int:
        """Execute the complete ETL pipeline.
        
        Returns:
            Exit code (0 for success, 1 for failure)
        """
        self.execution_stats["start_time"] = datetime.utcnow()
        logger.info("="*60)
        logger.info("Starting ETL Pipeline Execution")
        logger.info("="*60)
        
        try:
            # Connect to Snowflake
            self.sf_handler.connect()
            
            # Create rejection table if needed
            self.sf_handler.create_rejection_table()
            
            # Discover CSV files
            csv_files = self.s3_handler.list_csv_files(hours_back=24)
            if not csv_files:
                logger.warning("No CSV files found in S3")
                return 0
            
            # Process each file
            all_valid_records = None
            all_rejection_dicts = []
            
            for s3_key in csv_files:
                logger.info(f"Processing file: {s3_key}")
                try:
                    # Read CSV from S3
                    df = self.s3_handler.read_csv(s3_key)
                    self.execution_stats["files_processed"] += 1
                    self.execution_stats["rows_read"] += len(df)
                    
                    # Validate schema
                    valid_df, validation_errors = validate_schema(df)
                    self.execution_stats["rows_valid"] += len(valid_df)
                    self.execution_stats["rows_rejected"] += len(validation_errors)
                    
                    # Log validation errors
                    if validation_errors:
                        logger.warning(f"Found {len(validation_errors)} invalid records in {s3_key}")
                        for error in validation_errors[:5]:  # Log first 5
                            logger.debug(f"Row {error.row_number}: {error.errors}")
                    
                    # Standardize types
                    if not valid_df.empty:
                        valid_df = standardize_types(valid_df)
                        
                        # Combine with previous batches
                        if all_valid_records is None:
                            all_valid_records = valid_df
                        else:
                            import pandas as pd
                            all_valid_records = pd.concat([all_valid_records, valid_df], ignore_index=True)
                    
                    # Collect rejection dictionaries
                    all_rejection_dicts.extend([e.to_dict() for e in validation_errors])
                    
                    # Mark file as processed
                    self.s3_handler.mark_file_processed(s3_key)
                    logger.info(f"Successfully processed {s3_key}")
                
                except Exception as e:
                    error_msg = f"Error processing {s3_key}: {str(e)}"
                    logger.error(error_msg)
                    self.execution_stats["errors"].append(error_msg)
                    continue
            
            # Load valid records to Snowflake
            if all_valid_records is not None and not all_valid_records.empty:
                rows_loaded = self.sf_handler.truncate_and_load(
                    all_valid_records,
                    config.target_table_name
                )
                self.execution_stats["rows_loaded"] = rows_loaded
            else:
                logger.warning("No valid records to load")
                self.sf_handler.truncate_and_load(
                    __import__('pandas').DataFrame(),
                    config.target_table_name
                )
            
            # Load rejected records
            if all_rejection_dicts:
                rejection_count = self.sf_handler.insert_rejections(all_rejection_dicts)
                logger.info(f"Inserted {rejection_count} rejection records")
            
            # Log execution summary
            self._log_summary()
            return 0
        
        except Exception as e:
            logger.error(f"Pipeline execution failed: {str(e)}", exc_info=True)
            return 1
        
        finally:
            self.sf_handler.disconnect()
            self.execution_stats["end_time"] = datetime.utcnow()
    
    def _log_summary(self) -> None:
        """Log pipeline execution summary."""
        duration = (
            self.execution_stats["end_time"] - self.execution_stats["start_time"]
        ).total_seconds()
        
        logger.info("="*60)
        logger.info("Pipeline Execution Summary")
        logger.info("="*60)
        logger.info(f"Files processed: {self.execution_stats['files_processed']}")
        logger.info(f"Rows read: {self.execution_stats['rows_read']}")
        logger.info(f"Rows valid: {self.execution_stats['rows_valid']}")
        logger.info(f"Rows rejected: {self.execution_stats['rows_rejected']}")
        logger.info(f"Rows loaded: {self.execution_stats['rows_loaded']}")
        logger.info(f"Execution time: {duration:.2f} seconds")
        if self.execution_stats["errors"]:
            logger.warning(f"Errors encountered: {len(self.execution_stats['errors'])}")
            for error in self.execution_stats["errors"]:
                logger.warning(f"  - {error}")
        logger.info("="*60)


def main() -> int:
    """Entry point for pipeline."""
    try:
        executor = PipelineExecutor()
        return executor.execute()
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
