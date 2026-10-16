# CSV to Snowflake Daily ETL Pipeline

Production-grade ETL pipeline that reads orders from S3 CSV files, validates data, and loads into Snowflake with comprehensive error handling, logging, and rejection management.

## How to run this

### 1. Prerequisites

- Python 3.9 or later
- AWS credentials configured (IAM role with S3 read access, or AWS access keys in environment)
- Snowflake account with active warehouse and database
- `pip` package manager

### 2. Installing dependencies

```bash
pip install -r requirements.txt
```

### 3. Configuring credentials

Copy the example environment file and fill in real values:

```bash
cp .env.example .env
```

Edit `.env` with your actual credentials:
- AWS region and S3 bucket path
- Snowflake account, user, private key or password
- Database and schema names

`.env.example` remains blank and can be safely committed. `.gitignore` already excludes `.env` from version control.

### 4. Running it

```bash
python -m etl.pipeline
```

For local testing with sample CSV:

```bash
python -m pytest tests/ -v
```

## Output

Pipeline logs execution details to `logs/etl_{timestamp}.log` and Snowflake rejection table `stg_orders_rejected`. On success, orders table is truncated and reloaded with valid records.
