# Sales to Revenue ETL Lambda

Nightly batch ETL that queries yesterday's partition from `sales_table` in RDS MySQL, inserts all rows into `revenue_table`, and logs operation metadata to S3. Triggered by EventBridge cron at 23:00 UTC.

## How to run this

### Prerequisites

- Python 3.9+
- AWS CLI configured with credentials for the target account
- Access to RDS MySQL instance (host, port, database already provisioned)
- Secrets Manager secret created with database credentials
- S3 bucket created for logs
- Lambda execution role with permissions for RDS, Secrets Manager, and S3

### Installing dependencies

```bash
pip install -r requirements.txt
```

### Configuring credentials

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill in real values:
   - `SECRETS_MANAGER_SECRET`: name or ARN of the Secrets Manager secret containing RDS credentials
   - `S3_LOG_BUCKET`: S3 bucket name for logs
   - `S3_LOG_PREFIX`: S3 prefix for logs (optional; defaults to `data-pipeline/sales-revenue`)

3. `.env` is gitignored and never committed. `.env.example` remains blank so it is safe to commit.

### Running it

#### Local testing (requires AWS credentials and RDS access):

```bash
python -m pytest tests/
```

#### Deployment to Lambda:

1. Package the function and dependencies:
   ```bash
   mkdir lambda_package
   pip install -r requirements.txt -t lambda_package/
   cp lambda_function.py lambda_package/
   cd lambda_package && zip -r ../lambda_function.zip . && cd ..
   ```

2. Update the Lambda function code:
   ```bash
   aws lambda update-function-code \
     --function-name sales-to-revenue-etl \
     --zip-file fileb://lambda_function.zip
   ```

3. Set environment variables on the Lambda function:
   ```bash
   aws lambda update-function-configuration \
     --function-name sales-to-revenue-etl \
     --environment Variables="{
       SECRETS_MANAGER_SECRET=your-secret-name,
       S3_LOG_BUCKET=your-bucket,
       S3_LOG_PREFIX=data-pipeline/sales-revenue
     }"
   ```

4. Verify EventBridge rule is active:
   ```bash
   aws events describe-rule --name sales-revenue-nightly
   ```

## Architecture Notes

- **Credentials**: Read from Secrets Manager on every invocation (no caching within Lambda's 15-minute lifetime).
- **Connection timeout**: 10 seconds; if RDS does not respond, the function fails and EventBridge does not retry (by design; manual investigation required).
- **Query scope**: Yesterday's date only, partitioned on the `date` column. Query is bounded and does not scan the entire table.
- **Idempotency**: Re-running the same day will re-insert rows. The table should enforce unique constraints or be designed to allow accumulation.
- **Logging**: JSON logs written to S3 with date prefix (`YYYY/MM/DD/`) and timestamp suffix. Logs include row count, status, and any error message.
- **Error handling**: Connection errors and query failures are logged but do not cause Lambda to retry (that is EventBridge's responsibility if configured). Schema violations are permanent failures and logged without retry.

## Monitoring

- Check CloudWatch Logs for the Lambda function name `sales-to-revenue-etl`.
- Check S3 path `s3://{S3_LOG_BUCKET}/data-pipeline/sales-revenue/` for daily logs.
- Set up a CloudWatch alarm on Lambda error rate or S3 log absence to detect failures.
