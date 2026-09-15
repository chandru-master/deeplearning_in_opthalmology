import json
import logging
import os
from datetime import datetime, timedelta
import boto3
import pymysql
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

secrets_client = boto3.client('secretsmanager')
s3_client = boto3.client('s3')


def get_db_credentials(secret_name: str) -> dict:
    """
    Retrieve RDS credentials from Secrets Manager.
    Raises ClientError if secret cannot be retrieved.
    """
    try:
        response = secrets_client.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])
    except ClientError as e:
        logger.error(f"Failed to retrieve secret {secret_name}: {e}")
        raise


def connect_to_rds(credentials: dict, timeout: int = 10) -> pymysql.Connection:
    """
    Establish a connection to RDS MySQL.
    Raises pymysql.Error if connection fails.
    """
    try:
        connection = pymysql.connect(
            host=credentials['host'],
            user=credentials['username'],
            password=credentials['password'],
            database=credentials['database'],
            connect_timeout=timeout,
            read_timeout=timeout,
            write_timeout=timeout
        )
        return connection
    except pymysql.Error as e:
        logger.error(f"Failed to connect to RDS: {e}")
        raise


def query_yesterday_sales(connection: pymysql.Connection) -> list:
    """
    Query sales_table for yesterday's date.
    Returns list of tuples; raises pymysql.Error on failure.
    """
    yesterday = (datetime.utcnow() - timedelta(days=1)).date()
    query = f"SELECT * FROM sales_table WHERE DATE(date) = %s"
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, (yesterday,))
            rows = cursor.fetchall()
            logger.info(f"Retrieved {len(rows)} rows from sales_table for date {yesterday}")
            return rows
    except pymysql.Error as e:
        logger.error(f"Query failed: {e}")
        raise


def get_column_names(connection: pymysql.Connection) -> list:
    """
    Retrieve column names from sales_table to validate schema.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("DESCRIBE sales_table")
            columns = [row[0] for row in cursor.fetchall()]
            logger.info(f"sales_table columns: {columns}")
            return columns
    except pymysql.Error as e:
        logger.error(f"Failed to describe sales_table: {e}")
        raise


def insert_into_revenue_table(connection: pymysql.Connection, rows: list, columns: list) -> int:
    """
    Insert rows into revenue_table.
    Returns the number of rows inserted.
    """
    if not rows:
        logger.info("No rows to insert")
        return 0
    
    column_list = ', '.join(columns)
    placeholders = ', '.join(['%s'] * len(columns))
    insert_query = f"INSERT INTO revenue_table ({column_list}) VALUES ({placeholders})"
    
    try:
        with connection.cursor() as cursor:
            cursor.executemany(insert_query, rows)
            connection.commit()
            logger.info(f"Inserted {cursor.rowcount} rows into revenue_table")
            return cursor.rowcount
    except pymysql.Error as e:
        connection.rollback()
        logger.error(f"Insert failed: {e}")
        raise


def write_log_to_s3(bucket: str, prefix: str, log_data: dict) -> None:
    """
    Write JSON log to S3 with date-based prefix.
    """
    timestamp = datetime.utcnow().isoformat() + 'Z'
    date_prefix = datetime.utcnow().strftime('%Y/%m/%d')
    key = f"{prefix}/{date_prefix}/log_{timestamp.replace(':', '-')}.json"
    
    try:
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(log_data, indent=2, default=str),
            ContentType='application/json'
        )
        logger.info(f"Log written to s3://{bucket}/{key}")
    except ClientError as e:
        logger.error(f"Failed to write log to S3: {e}")
        raise


def lambda_handler(event, context):
    """
    Main Lambda handler.
    """
    secret_name = os.environ.get('SECRETS_MANAGER_SECRET')
    s3_bucket = os.environ.get('S3_LOG_BUCKET')
    s3_prefix = os.environ.get('S3_LOG_PREFIX', 'data-pipeline/sales-revenue')
    
    log_entry = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'function': 'sales_to_revenue_etl',
        'status': 'pending',
        'row_count': 0,
        'error': None
    }
    
    connection = None
    try:
        # Retrieve credentials
        credentials = get_db_credentials(secret_name)
        
        # Connect to RDS
        connection = connect_to_rds(credentials)
        
        # Get schema
        columns = get_column_names(connection)
        
        # Query yesterday's data
        rows = query_yesterday_sales(connection)
        
        # Insert into revenue_table
        inserted_count = insert_into_revenue_table(connection, rows, columns)
        
        log_entry['status'] = 'success'
        log_entry['row_count'] = inserted_count
        logger.info(f"ETL completed successfully. Rows inserted: {inserted_count}")
        
    except (ClientError, pymysql.Error) as e:
        log_entry['status'] = 'failed'
        log_entry['error'] = str(e)
        logger.error(f"ETL failed: {e}", exc_info=True)
        
    finally:
        if connection:
            connection.close()
        
        # Write log to S3
        try:
            write_log_to_s3(s3_bucket, s3_prefix, log_entry)
        except ClientError as e:
            logger.error(f"Failed to write log: {e}")
        
        # Return result
        return {
            'statusCode': 200 if log_entry['status'] == 'success' else 500,
            'body': json.dumps(log_entry)
        }
