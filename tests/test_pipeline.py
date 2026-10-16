"""Tests for ETL pipeline execution."""
import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from etl.pipeline import PipelineExecutor
from etl.schema import ValidationError


class TestPipelineExecutor(unittest.TestCase):
    """Test cases for pipeline executor."""
    
    @patch('etl.pipeline.SnowflakeHandler')
    @patch('etl.pipeline.S3Handler')
    def setUp(self, mock_s3, mock_sf):
        """Set up test fixtures."""
        self.mock_s3_class = mock_s3
        self.mock_sf_class = mock_sf
        
        # Mock S3Handler instance
        self.mock_s3 = Mock()
        mock_s3.return_value = self.mock_s3
        
        # Mock SnowflakeHandler instance
        self.mock_sf = Mock()
        mock_sf.return_value = self.mock_sf
    
    @patch('etl.pipeline.SnowflakeHandler')
    @patch('etl.pipeline.S3Handler')
    def test_pipeline_with_no_files_returns_success(self, mock_s3, mock_sf):
        """Test pipeline handles case with no files found."""
        mock_s3_instance = Mock()
        mock_s3.return_value = mock_s3_instance
        mock_s3_instance.list_csv_files.return_value = []
        
        mock_sf_instance = Mock()
        mock_sf.return_value = mock_sf_instance
        
        executor = PipelineExecutor()
        result = executor.execute()
        
        self.assertEqual(result, 0)
        mock_s3_instance.list_csv_files.assert_called_once()
    
    @patch('etl.pipeline.validate_schema')
    @patch('etl.pipeline.standardize_types')
    @patch('etl.pipeline.SnowflakeHandler')
    @patch('etl.pipeline.S3Handler')
    def test_pipeline_processes_single_file(self, mock_s3, mock_sf, mock_standardize, mock_validate):
        """Test pipeline processes a single valid file."""
        # Mock S3
        mock_s3_instance = Mock()
        mock_s3.return_value = mock_s3_instance
        mock_s3_instance.list_csv_files.return_value = ["orders/orders.csv"]
        
        df = pd.DataFrame({
            "order_id": [1, 2],
            "customer_id": [100, 101],
            "order_date": ["2024-01-01", "2024-01-02"],
            "amount": [100.0, 200.0],
            "status": ["pending", "completed"]
        })
        mock_s3_instance.read_csv.return_value = df
        
        # Mock validation
        mock_validate.return_value = (df, [])
        mock_standardize.return_value = df
        
        # Mock Snowflake
        mock_sf_instance = Mock()
        mock_sf.return_value = mock_sf_instance
        mock_sf_instance.truncate_and_load.return_value = 2
        
        executor = PipelineExecutor()
        result = executor.execute()
        
        self.assertEqual(result, 0)
        self.assertEqual(executor.execution_stats["files_processed"], 1)
        self.assertEqual(executor.execution_stats["rows_read"], 2)
        self.assertEqual(executor.execution_stats["rows_valid"], 2)
        self.assertEqual(executor.execution_stats["rows_rejected"], 0)
        mock_sf_instance.truncate_and_load.assert_called_once()
    
    @patch('etl.pipeline.validate_schema')
    @patch('etl.pipeline.standardize_types')
    @patch('etl.pipeline.SnowflakeHandler')
    @patch('etl.pipeline.S3Handler')
    def test_pipeline_handles_validation_errors(self, mock_s3, mock_sf, mock_standardize, mock_validate):
        """Test pipeline handles records that fail validation."""
        # Mock S3
        mock_s3_instance = Mock()
        mock_s3.return_value = mock_s3_instance
        mock_s3_instance.list_csv_files.return_value = ["orders/orders.csv"]
        
        df = pd.DataFrame({
            "order_id": [1, 2],
            "customer_id": [100, 101],
            "order_date": ["2024-01-01", "2024-01-02"],
            "amount": [100.0, 200.0],
            "status": ["pending", "invalid"]
        })
        mock_s3_instance.read_csv.return_value = df
        
        # Mock validation: 1 valid, 1 invalid
        valid_df = df.iloc[[0]]
        error = ValidationError(2, df.iloc[1].to_dict(), ["Invalid status"])
        mock_validate.return_value = (valid_df, [error])
        mock_standardize.return_value = valid_df
        
        # Mock Snowflake
        mock_sf_instance = Mock()
        mock_sf.return_value = mock_sf_instance
        mock_sf_instance.truncate_and_load.return_value = 1
        mock_sf_instance.insert_rejections.return_value = 1
        
        executor = PipelineExecutor()
        result = executor.execute()
        
        self.assertEqual(result, 0)
        self.assertEqual(executor.execution_stats["rows_read"], 2)
        self.assertEqual(executor.execution_stats["rows_valid"], 1)
        self.assertEqual(executor.execution_stats["rows_rejected"], 1)
        mock_sf_instance.insert_rejections.assert_called_once()
    
    @patch('etl.pipeline.SnowflakeHandler')
    @patch('etl.pipeline.S3Handler')
    def test_pipeline_returns_error_on_connection_failure(self, mock_s3, mock_sf):
        """Test pipeline returns error on Snowflake connection failure."""
        # Mock S3
        mock_s3_instance = Mock()
        mock_s3.return_value = mock_s3_instance
        
        # Mock Snowflake connection failure
        mock_sf_instance = Mock()
        mock_sf.return_value = mock_sf_instance
        mock_sf_instance.connect.side_effect = Exception("Connection failed")
        
        executor = PipelineExecutor()
        result = executor.execute()
        
        self.assertEqual(result, 1)
    
    @patch('etl.pipeline.SnowflakeHandler')
    @patch('etl.pipeline.S3Handler')
    def test_pipeline_disconnects_on_completion(self, mock_s3, mock_sf):
        """Test pipeline disconnects from Snowflake after execution."""
        # Mock S3
        mock_s3_instance = Mock()
        mock_s3.return_value = mock_s3_instance
        mock_s3_instance.list_csv_files.return_value = []
        
        # Mock Snowflake
        mock_sf_instance = Mock()
        mock_sf.return_value = mock_sf_instance
        
        executor = PipelineExecutor()
        executor.execute()
        
        mock_sf_instance.disconnect.assert_called_once()


if __name__ == "__main__":
    unittest.main()
