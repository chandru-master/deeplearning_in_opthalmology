#!/usr/bin/env python3
"""
Daily CSV to Snowflake ELT pipeline.
Ingest orders from S3, land into Snowflake staging, transform, and load.
"""

import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

from config import PipelineConfig
from s3_ingestion import S3Ingester
from snowflake_loader import SnowflakeLoader
from transformation import SnowflakeTransformer


def setup_logging(config: PipelineConfig) -> logging.Logger:
    """Configure logging to file and stdout."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"pipeline_{timestamp}.log"

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    logger = logging.getLogger("pipeline")
    logger.setLevel(getattr(logging, config.log_level))
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def run_pipeline(config: PipelineConfig, target_date: datetime, logger: logging.Logger) -> bool:
    """
    Execute the ELT pipeline for a given date.
    Returns True if successful, False otherwise.
    """
    execution_id = datetime.now().isoformat()
    logger.info(f"Pipeline started | execution_id={execution_id} | target_date={target_date.date()}")

    try:
        # Step 1: Extract from S3
        logger.info("Step 1: Extracting CSV from S3")
        ingester = S3Ingester(config, logger)
        csv_path = ingester.download_csv(target_date)
        if not csv_path:
            logger.error(f"No CSV file found for {target_date.date()}")
            return False
        logger.info(f"CSV downloaded: {csv_path}")

        # Step 2: Load raw data to Snowflake staging
        logger.info("Step 2: Loading raw CSV to Snowflake staging")
        loader = SnowflakeLoader(config, logger)
        loader.connect()
        try:
            loaded_count, rejected_count = loader.load_raw_csv(csv_path, target_date)
            logger.info(
                f"Raw load complete | loaded={loaded_count} | rejected={rejected_count}"
            )

            # Step 3: Validate and transform in Snowflake
            logger.info("Step 3: Transforming data in Snowflake")
            transformer = SnowflakeTransformer(loader, config, logger)
            transformed_count = transformer.transform(target_date)
            logger.info(f"Transform complete | transformed={transformed_count}")

            # Step 4: Quality checks
            logger.info("Step 4: Running quality checks")
            quality_passed = transformer.run_quality_checks(target_date)
            if not quality_passed:
                logger.warning("Quality checks failed; see logs")
                return False

            # Step 5: Load to target table
            logger.info("Step 5: Loading to target table")
            final_count = loader.load_target(target_date)
            logger.info(f"Target load complete | rows={final_count}")

            # Step 6: Record execution
            logger.info("Step 6: Recording execution metrics")
            loader.record_execution(
                execution_id=execution_id,
                target_date=target_date,
                loaded_count=loaded_count,
                rejected_count=rejected_count,
                transformed_count=transformed_count,
                final_count=final_count,
                status="SUCCESS",
            )
            logger.info("Pipeline succeeded")
            return True

        finally:
            loader.disconnect()

    except Exception as e:
        logger.exception(f"Pipeline failed with exception: {e}")
        if loader:
            try:
                loader.record_execution(
                    execution_id=execution_id,
                    target_date=target_date,
                    loaded_count=0,
                    rejected_count=0,
                    transformed_count=0,
                    final_count=0,
                    status="FAILED",
                    error_message=str(e)[:500],
                )
                loader.disconnect()
            except Exception as cleanup_error:
                logger.error(f"Error recording failure: {cleanup_error}")
        return False


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(description="CSV to Snowflake ELT Pipeline")
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Target date (YYYY-MM-DD); default: today",
    )
    args = parser.parse_args()

    if args.date:
        try:
            target_date = datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            print(f"Invalid date format: {args.date}. Use YYYY-MM-DD.")
            sys.exit(1)
    else:
        target_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    config = PipelineConfig.from_env()
    logger = setup_logging(config)

    success = run_pipeline(config, target_date, logger)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
