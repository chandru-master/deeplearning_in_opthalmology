import json
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, call
import pytest
import pymysql
from botocore.exceptions import ClientError

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lambda_function import (
    get_db_credentials,
    connect_to_rds,
    query_yesterday_sales,
    get_column_names,
    insert_into_revenue_table,
    write_log_to_s3,
    lambda_handler
)


class TestGetDbCredentials:
    @patch('lambda_function.secrets_client')
    def test_get_db_credentials_success(self, mock_secrets_client):
        mock_secrets_client.get_secret_value.return_value = {
            'SecretString': json.dumps({
                'host': 'mydb.rds.amazonaws.com',
                'username': 'admin',
                'password': 'secret',
                'database': 'sales_db'
            })
        }
        
        creds = get_db_credentials('test-secret')
        assert creds['host'] == 'mydb.rds.amazonaws.com'
        assert creds['username'] == 'admin'
        assert creds['database'] == 'sales_db'
    
    @patch('lambda_function.secrets_client')
    def test_get_db_credentials_not_found(self, mock_secrets_client):
        mock_secrets_client.get_secret_value.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException'}},
            'GetSecretValue'
        )
        
        with pytest.raises(ClientError):
            get_db_credentials('nonexistent-secret')


class TestConnectToRds:
    @patch('lambda_function.pymysql.connect')
    def test_connect_to_rds_success(self, mock_connect):
        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection
        
        credentials = {
            'host': 'mydb.rds.amazonaws.com',
            'username': 'admin',
            'password': 'secret',
            'database': 'sales_db'
        }
        
        conn = connect_to_rds(credentials)
        assert conn == mock_connection
        mock_connect.assert_called_once()
    
    @patch('lambda_function.pymysql.connect')
    def test_connect_to_rds_timeout(self, mock_connect):
        mock_connect.side_effect = pymysql.err.OperationalError("Connection timeout")
        
        credentials = {
            'host': 'mydb.rds.amazonaws.com',
            'username': 'admin',
            'password': 'secret',
            'database': 'sales_db'
        }
        
        with pytest.raises(pymysql.Error):
            connect_to_rds(credentials)


class TestQueryYesterdaysSales:
    @patch('lambda_function.datetime')
    def test_query_yesterday_sales_success(self, mock_datetime):
        # Mock datetime to return a fixed date
        mock_now = MagicMock()
        mock_now.date.return_value = datetime(2024, 1, 15).date()
        mock_datetime.utcnow.return_value = mock_now
        
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [(1, 'A', 100), (2, 'B', 200)]
        
        rows = query_yesterday_sales(mock_connection)
        assert len(rows) == 2
        assert rows[0] == (1, 'A', 100)
    
    @patch('lambda_function.datetime')
    def test_query_yesterday_sales_empty(self, mock_datetime):
        mock_now = MagicMock()
        mock_now.date.return_value = datetime(2024, 1, 15).date()
        mock_datetime.utcnow.return_value = mock_now
        
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        
        rows = query_yesterday_sales(mock_connection)
        assert len(rows) == 0


class TestGetColumnNames:
    def test_get_column_names_success(self):
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            ('id', 'int'),
            ('name', 'varchar(255)'),
            ('amount', 'decimal')
        ]
        
        columns = get_column_names(mock_connection)
        assert columns == ['id', 'name', 'amount']


class TestInsertIntoRevenueTable:
    def test_insert_into_revenue_table_success(self):
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.rowcount = 2
        
        rows = [(1, 'A', 100), (2, 'B', 200)]
        columns = ['id', 'name', 'amount']
        
        inserted = insert_into_revenue_table(mock_connection, rows, columns)
        assert inserted == 2
        mock_connection.commit.assert_called_once()
    
    def test_insert_into_revenue_table_empty(self):
        mock_connection = MagicMock()
        
        rows = []
        columns = ['id', 'name', 'amount']
        
        inserted = insert_into_revenue_table(mock_connection, rows, columns)
        assert inserted == 0
        mock_connection.commit.assert_not_called()
    
    def test_insert_into_revenue_table_failure(self):
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.executemany.side_effect = pymysql.err.OperationalError("Connection lost")
        
        rows = [(1, 'A', 100)]
        columns = ['id', 'name', 'amount']
        
        with pytest.raises(pymysql.Error):
            insert_into_revenue_table(mock_connection, rows, columns)
        
        mock_connection.rollback.assert_called_once()


class TestWriteLogToS3:
    @patch('lambda_function.s3_client')
    def test_write_log_to_s3_success(self, mock_s3_client):
        log_data = {
            'timestamp': '2024-01-14T23:30:00Z',
            'status': 'success',
            'row_count': 100
        }
        
        write_log_to_s3('my-bucket', 'logs', log_data)
        mock_s3_client.put_object.assert_called_once()
        call_kwargs = mock_s3_client.put_object.call_args[1]
        assert call_kwargs['Bucket'] == 'my-bucket'
        assert call_kwargs['ContentType'] == 'application/json'
    
    @patch('lambda_function.s3_client')
    def test_write_log_to_s3_failure(self, mock_s3_client):
        mock_s3_client.put_object.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied'}},
            'PutObject'
        )
        
        log_data = {'status': 'success'}
        
        with pytest.raises(ClientError):
            write_log_to_s3('my-bucket', 'logs', log_data)


class TestLambdaHandler:
    @patch('lambda_function.write_log_to_s3')
    @patch('lambda_function.insert_into_revenue_table')
    @patch('lambda_function.get_column_names')
    @patch('lambda_function.query_yesterday_sales')
    @patch('lambda_function.connect_to_rds')
    @patch('lambda_function.get_db_credentials')
    def test_lambda_handler_success(self, mock_get_creds, mock_connect, mock_query,
                                     mock_get_cols, mock_insert, mock_write_log):
        os.environ['SECRETS_MANAGER_SECRET'] = 'test-secret'
        os.environ['S3_LOG_BUCKET'] = 'test-bucket'
        os.environ['S3_LOG_PREFIX'] = 'logs'
        
        mock_get_creds.return_value = {'host': 'test', 'username': 'test', 'password': 'test', 'database': 'test'}
        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection
        mock_get_cols.return_value = ['id', 'amount']
        mock_query.return_value = [(1, 100), (2, 200)]
        mock_insert.return_value = 2
        
        result = lambda_handler(None, None)
        
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['status'] == 'success'
        assert body['row_count'] == 2
        mock_connection.close.assert_called_once()
        mock_write_log.assert_called_once()
    
    @patch('lambda_function.write_log_to_s3')
    @patch('lambda_function.get_db_credentials')
    def test_lambda_handler_credential_error(self, mock_get_creds, mock_write_log):
        os.environ['SECRETS_MANAGER_SECRET'] = 'test-secret'
        os.environ['S3_LOG_BUCKET'] = 'test-bucket'
        
        mock_get_creds.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException'}},
            'GetSecretValue'
        )
        
        result = lambda_handler(None, None)
        
        assert result['statusCode'] == 500
        body = json.loads(result['body'])
        assert body['status'] == 'failed'
        assert body['error'] is not None
