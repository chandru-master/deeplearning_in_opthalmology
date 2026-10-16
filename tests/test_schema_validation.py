"""Tests for schema validation module."""
import unittest
from datetime import datetime
import pandas as pd
from etl.schema import validate_schema, standardize_types, ValidationError


class TestSchemaValidation(unittest.TestCase):
    """Test cases for schema validation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.valid_data = {
            "order_id": [1, 2, 3],
            "customer_id": [100, 101, 102],
            "order_date": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "amount": [100.50, 200.00, 150.75],
            "status": ["pending", "completed", "cancelled"]
        }
    
    def test_valid_data_passes_validation(self):
        """Test that valid data passes validation."""
        df = pd.DataFrame(self.valid_data)
        valid_df, errors = validate_schema(df)
        
        self.assertEqual(len(valid_df), 3)
        self.assertEqual(len(errors), 0)
    
    def test_null_in_required_column_rejected(self):
        """Test that null values in required columns cause rejection."""
        data = self.valid_data.copy()
        data["order_id"] = [1, None, 3]
        df = pd.DataFrame(data)
        
        valid_df, errors = validate_schema(df)
        
        self.assertEqual(len(valid_df), 2)
        self.assertEqual(len(errors), 1)
        self.assertIn("null", errors[0].errors[0].lower())
    
    def test_negative_order_id_rejected(self):
        """Test that negative order_id is rejected."""
        data = self.valid_data.copy()
        data["order_id"] = [1, -2, 3]
        df = pd.DataFrame(data)
        
        valid_df, errors = validate_schema(df)
        
        self.assertEqual(len(valid_df), 2)
        self.assertEqual(len(errors), 1)
        self.assertIn("positive", errors[0].errors[0].lower())
    
    def test_invalid_date_rejected(self):
        """Test that invalid date format is rejected."""
        data = self.valid_data.copy()
        data["order_date"] = ["2024-01-01", "invalid-date", "2024-01-03"]
        df = pd.DataFrame(data)
        
        valid_df, errors = validate_schema(df)
        
        self.assertEqual(len(valid_df), 2)
        self.assertEqual(len(errors), 1)
        self.assertIn("date", errors[0].errors[0].lower())
    
    def test_invalid_status_rejected(self):
        """Test that invalid status value is rejected."""
        data = self.valid_data.copy()
        data["status"] = ["pending", "invalid_status", "cancelled"]
        df = pd.DataFrame(data)
        
        valid_df, errors = validate_schema(df)
        
        self.assertEqual(len(valid_df), 2)
        self.assertEqual(len(errors), 1)
        self.assertIn("status", errors[0].errors[0].lower())
    
    def test_negative_amount_rejected(self):
        """Test that negative amount is rejected."""
        data = self.valid_data.copy()
        data["amount"] = [100.50, -200.00, 150.75]
        df = pd.DataFrame(data)
        
        valid_df, errors = validate_schema(df)
        
        self.assertEqual(len(valid_df), 2)
        self.assertEqual(len(errors), 1)
        self.assertIn("non-negative", errors[0].errors[0].lower())
    
    def test_missing_required_column_raises_error(self):
        """Test that missing required column raises error."""
        data = self.valid_data.copy()
        del data["order_id"]
        df = pd.DataFrame(data)
        
        with self.assertRaises(ValueError) as context:
            validate_schema(df)
        
        self.assertIn("order_id", str(context.exception))
    
    def test_extra_column_raises_error(self):
        """Test that extra columns raise error."""
        data = self.valid_data.copy()
        data["extra_column"] = [1, 2, 3]
        df = pd.DataFrame(data)
        
        with self.assertRaises(ValueError) as context:
            validate_schema(df)
        
        self.assertIn("extra", str(context.exception).lower())
    
    def test_standardize_types_converts_correctly(self):
        """Test that type standardization works correctly."""
        df = pd.DataFrame(self.valid_data)
        standardized = standardize_types(df)
        
        # Check types
        self.assertTrue(pd.api.types.is_integer_dtype(standardized["order_id"]))
        self.assertTrue(pd.api.types.is_integer_dtype(standardized["customer_id"]))
        self.assertTrue(pd.api.types.is_float_dtype(standardized["amount"]))
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(standardized["order_date"]))
    
    def test_standardize_status_to_lowercase(self):
        """Test that status is converted to lowercase."""
        data = self.valid_data.copy()
        data["status"] = ["PENDING", "Completed", "CANCELLED"]
        df = pd.DataFrame(data)
        
        standardized = standardize_types(df)
        
        self.assertTrue(all(s in ["pending", "completed", "cancelled"] for s in standardized["status"]))
    
    def test_validation_error_to_dict(self):
        """Test that ValidationError converts to dictionary correctly."""
        error = ValidationError(
            row_number=5,
            record={"order_id": 1, "status": "invalid"},
            errors=["Invalid status", "Negative amount"]
        )
        
        error_dict = error.to_dict()
        
        self.assertEqual(error_dict["row_number"], 5)
        self.assertIn("Invalid status", error_dict["error_message"])
        self.assertIn("Negative amount", error_dict["error_message"])
        self.assertIsNotNone(error_dict["rejected_at"])
        self.assertIsNotNone(error_dict["source_record"])


if __name__ == "__main__":
    unittest.main()
