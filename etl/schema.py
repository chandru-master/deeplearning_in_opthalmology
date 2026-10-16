"""Schema definitions and validation for orders data."""
from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd


# Define expected schema with types
EXPECTED_SCHEMA = {
    "order_id": "int64",
    "customer_id": "int64",
    "order_date": "object",
    "amount": "float64",
    "status": "object"
}

# Define required columns
REQUIRED_COLUMNS = ["order_id", "customer_id", "order_date", "amount", "status"]

# Define nullable columns
NULLABLE_COLUMNS = {"amount"}


class ValidationError:
    """Represents a validation error for a record."""
    
    def __init__(self, row_number: int, record: Dict[str, Any], errors: List[str]):
        self.row_number = row_number
        self.record = record
        self.errors = errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for storage."""
        return {
            "row_number": self.row_number,
            "error_message": "; ".join(self.errors),
            "rejected_at": datetime.utcnow().isoformat(),
            "source_record": str(self.record)
        }


def validate_schema(df: pd.DataFrame) -> tuple[pd.DataFrame, List[ValidationError]]:
    """Validate DataFrame schema and return valid records and errors.
    
    Args:
        df: Input DataFrame
        
    Returns:
        Tuple of (valid_records_df, validation_errors_list)
    """
    errors = []
    invalid_indices = []
    
    # Check for required columns
    missing_columns = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")
    
    # Check for extra columns not in schema
    extra_columns = set(df.columns) - set(EXPECTED_SCHEMA.keys())
    if extra_columns:
        raise ValueError(f"Unexpected columns in CSV: {extra_columns}")
    
    # Validate each row
    for idx, row in df.iterrows():
        row_errors = []
        
        # Check for null values in non-nullable columns
        for col in REQUIRED_COLUMNS:
            if col not in NULLABLE_COLUMNS and pd.isna(row[col]):
                row_errors.append(f"Column '{col}' is null but required")
        
        # Validate order_id is positive integer
        if not pd.isna(row["order_id"]):
            try:
                order_id = int(row["order_id"])
                if order_id <= 0:
                    row_errors.append("order_id must be positive")
            except (ValueError, TypeError):
                row_errors.append("order_id must be a valid integer")
        
        # Validate customer_id is positive integer
        if not pd.isna(row["customer_id"]):
            try:
                customer_id = int(row["customer_id"])
                if customer_id <= 0:
                    row_errors.append("customer_id must be positive")
            except (ValueError, TypeError):
                row_errors.append("customer_id must be a valid integer")
        
        # Validate order_date format
        if not pd.isna(row["order_date"]):
            try:
                datetime.fromisoformat(str(row["order_date"]).replace(" ", "T"))
            except ValueError:
                row_errors.append("order_date must be valid ISO format (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)")
        
        # Validate amount is positive number
        if not pd.isna(row["amount"]):
            try:
                amount = float(row["amount"])
                if amount < 0:
                    row_errors.append("amount must be non-negative")
            except (ValueError, TypeError):
                row_errors.append("amount must be a valid number")
        
        # Validate status is from allowed values
        valid_statuses = {"pending", "completed", "cancelled"}
        if not pd.isna(row["status"]):
            if str(row["status"]).lower() not in valid_statuses:
                row_errors.append(f"status must be one of {valid_statuses}")
        
        if row_errors:
            errors.append(ValidationError(idx + 2, row.to_dict(), row_errors))  # +2 for header and 0-indexing
            invalid_indices.append(idx)
    
    # Return valid rows and errors
    valid_df = df.drop(invalid_indices) if invalid_indices else df
    return valid_df.reset_index(drop=True), errors


def standardize_types(df: pd.DataFrame) -> pd.DataFrame:
    """Convert DataFrame columns to expected types."""
    df_copy = df.copy()
    
    # Convert to integer
    df_copy["order_id"] = pd.to_numeric(df_copy["order_id"], errors="coerce").astype("Int64")
    df_copy["customer_id"] = pd.to_numeric(df_copy["customer_id"], errors="coerce").astype("Int64")
    
    # Convert to float
    df_copy["amount"] = pd.to_numeric(df_copy["amount"], errors="coerce").astype("float64")
    
    # Normalize status to lowercase
    df_copy["status"] = df_copy["status"].astype(str).str.lower()
    
    # Ensure order_date is datetime
    df_copy["order_date"] = pd.to_datetime(df_copy["order_date"], errors="coerce")
    
    return df_copy
