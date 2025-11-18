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

