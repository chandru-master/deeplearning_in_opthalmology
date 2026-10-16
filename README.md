# CSV to Snowflake ELT Pipeline

Daily batch pipeline that ingests order data from S3 CSV files, lands into Snowflake staging, transforms, and loads into target table with full observability and error handling.

## How to run this

### 1. Prerequisites

- Python 3.9+
- AWS credentials configured (via IAM role, ~/.aws/credentials, or environment variables)
- Snowflake account with warehouse, database, and schema created
- S3 bucket with daily CSV files at `s3://bucket/orders/YYYY-MM-DD/orders.csv`

### 2. Installing dependencies

```bash
pip install -r requirements.txt
```

### 3. Configuring credentials

Copy `.env.example` to `.env` and fill in real values:

```bash
cp .env.example .env
```

Edit `.env` with actual AWS region, Snowflake account, user credentials, and S3 paths. **Do not commit `.env`** — it is listed in `.gitignore`.

### 4. Running the pipeline

```bash
python src/pipeline.py
```

Optionally, pass a custom date (default: today):

```bash
python src/pipeline.py --date 2025-01-15
```

Pipeline logs execution to stdout and to `logs/pipeline_{timestamp}.log`. Check `SNOWFLAKE_AUDIT_TABLE` for execution history.

## Orchestration

For daily automation:
- **AWS Lambda + EventBridge**: Schedule Lambda to invoke `pipeline.py` daily at e.g. 02:00 UTC.
- **Airflow/dbt**: DAG calls `python src/pipeline.py` as task.
- **Cron**: On compute instance, `0 2 * * * cd /opt/pipeline && python src/pipeline.py >> /var/log/pipeline.log 2>&1`

## Monitoring

Monitor these metrics:
- **Execution logs**: `logs/` directory; last 10 runs retained.
- **Audit table**: `SNOWFLAKE_AUDIT_TABLE` contains row counts (loaded, rejected) and status (SUCCESS, FAILED).
- **Rejected records**: Query `stg_orders_rejected` for malformed rows; includes error reason and raw content.
- **Data validation**: Run `dbt test` (if using dbt) or Snowflake tasks to validate business rules post-load.

## Architecture notes

- **Full load**: CSV is completely reloaded daily; no incremental deduplication.
- **Staging separation**: Raw data isolated in `stg_orders_raw` for audit and debugging.
- **Error isolation**: Malformed records not dropped; retained in `stg_orders_rejected` for investigation.
- **Idempotency**: TRUNCATE + INSERT ensures rerunning same date is safe; no duplicate risk.
- **Cost**: Snowflake compute auto-suspend after inactivity; S3 requests minimal with daily single-file pattern.
