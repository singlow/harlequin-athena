# harlequin-athena

This repo provides the Harlequin adapter for Amazon Athena.

## Installation

`harlequin-athena` depends on `harlequin`, so installing this package will also install Harlequin.

### Using pip

To install this adapter into an activated virtual environment:
```bash
pip install harlequin-athena
```

### Using poetry

```bash
poetry add harlequin-athena
```

### Using pipx

If you do not already have Harlequin installed:

```bash
pip install harlequin-athena
```

If you would like to add the Athena adapter to an existing Harlequin installation:

```bash
pipx inject harlequin harlequin-athena
```

### As an Extra
Alternatively, you can install Harlequin with the `athena` extra:

```bash
pip install harlequin[athena]
```

```bash
poetry add harlequin[athena]
```

```bash
pipx install harlequin[athena]
```

## Usage and Configuration

For a minimum connection you are going to need:
- `s3_staging_dir` (required): S3 bucket path for query results
- `region` (optional, default: us-east-1): AWS region

```bash
harlequin -a athena -s s3://my-bucket/athena-results/ -r us-east-1
```

### Environment Variables

Adapter-specific options can be configured via environment variables. Environment variables are used as fallbacks when CLI options are not provided. The environment variable names follow the pattern `HARLEQUIN_ATHENA_<OPTION_NAME>` (uppercase with underscores):

- `HARLEQUIN_ATHENA_S3_STAGING_DIR`: S3 staging directory (required)
- `HARLEQUIN_ATHENA_WORK_GROUP`: Athena work group
- `HARLEQUIN_ATHENA_SCHEMA`: Default schema (database)
- `HARLEQUIN_ATHENA_CATALOG`: Catalog name
- `HARLEQUIN_ATHENA_POLL_INTERVAL`: Polling interval in seconds

**Note:** AWS credentials and region can be configured using standard AWS SDK environment variables (automatically handled by boto3/pyathena):
- `AWS_ACCESS_KEY_ID`: AWS access key ID
- `AWS_SECRET_ACCESS_KEY`: AWS secret access key
- `AWS_SESSION_TOKEN`: AWS session token (for temporary credentials)
- `AWS_REGION` or `AWS_DEFAULT_REGION`: AWS region
- `AWS_PROFILE`: AWS profile name

Example using environment variables:
```bash
# Standard AWS SDK environment variables
export AWS_REGION="us-east-1"
export AWS_PROFILE="my-profile"

# Adapter-specific environment variables
export HARLEQUIN_ATHENA_S3_STAGING_DIR="s3://my-bucket/athena-results/"
export HARLEQUIN_ATHENA_WORK_GROUP="my-workgroup"

harlequin -a athena
```

### AWS Credentials

The adapter supports multiple methods for AWS authentication:

1. **Default credentials** (environment variables, ~/.aws/credentials, or IAM role):
   ```bash
   harlequin -a athena -s s3://my-bucket/athena-results/
   ```

2. **AWS Profile**:
   ```bash
   harlequin -a athena -s s3://my-bucket/athena-results/ --profile my-profile
   ```

3. **Explicit credentials**:
   ```bash
   harlequin -a athena -s s3://my-bucket/athena-results/ \
     --aws-access-key-id AKIA... \
     --aws-secret-access-key ...
   ```

### Additional Options

- `--work-group` or `-w`: Athena work group to use
- `--schema` or `-d` or `--database`: Default schema (database) to use
- `--catalog` or `-c`: Catalog name (default: AwsDataCatalog)
- `--poll-interval`: Polling interval in seconds for checking query status (default: 0.5, lower = faster polling)

Example with all options:
```bash
harlequin -a athena \
  -s s3://my-bucket/athena-results/ \
  -r us-east-1 \
  -w my-workgroup \
  -d my_database \
  -c AwsDataCatalog
```

Many more options are available; to see the full list, run:

```bash
harlequin --help
```

For more information, see the [Harlequin Docs](https://harlequin.sh/docs/).

## Development

### Setup

```bash
git clone https://github.com/yourusername/harlequin-athena.git
cd harlequin-athena
poetry install
```

### Running Tests

```bash
poetry run pytest
```

Note: Tests require AWS credentials and an Athena setup. You may want to use mocking for CI/CD.

## License

MIT

