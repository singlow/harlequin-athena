from __future__ import annotations

from harlequin.options import (
    FlagOption,  # noqa
    ListOption,  # noqa
    PathOption,  # noqa
    SelectOption,  # noqa
    TextOption,
)


def _int_validator(s: str | None) -> tuple[bool, str]:
    if s is None:
        return True, ""
    try:
        _ = int(s)
    except ValueError:
        return False, f"Cannot convert {s} to an int!"
    else:
        return True, ""


def _float_validator(s: str | None) -> tuple[bool, str]:
    if s is None:
        return True, ""
    try:
        val = float(s)
        if val <= 0:
            return False, "Poll interval must be greater than 0"
    except ValueError:
        return False, f"Cannot convert {s} to a float!"
    else:
        return True, ""


region = TextOption(
    name="region",
    description=("AWS region where Athena is located (e.g., us-east-1)"),
    short_decls=["-r", "--region"],
    default="us-east-1",
)

s3_staging_dir = TextOption(
    name="s3_staging_dir",
    description=("S3 staging directory for query results (required)"),
    short_decls=["-s", "--s3-staging-dir"],
)

work_group = TextOption(
    name="work_group",
    description=("Athena work group to use for queries"),
    short_decls=["-w", "--work-group"],
)

schema = TextOption(
    name="schema",
    description=("Default schema (database) to use"),
    short_decls=["-d", "--database", "--schema"],
)

catalog = TextOption(
    name="catalog",
    description=("Catalog name (typically 'AwsDataCatalog')"),
    short_decls=["-c", "--catalog"],
    default="AwsDataCatalog",
)

aws_access_key_id = TextOption(
    name="aws_access_key_id",
    description=("AWS access key ID (if not using default credentials)"),
    short_decls=["--aws-access-key-id"],
)

aws_secret_access_key = TextOption(
    name="aws_secret_access_key",
    description=("AWS secret access key (if not using default credentials)"),
    short_decls=["--aws-secret-access-key"],
)

aws_session_token = TextOption(
    name="aws_session_token",
    description=("AWS session token (for temporary credentials)"),
    short_decls=["--aws-session-token"],
)

profile_name = TextOption(
    name="profile_name",
    description=("AWS profile name to use (from ~/.aws/credentials)"),
    short_decls=["--profile"],
)

poll_interval = TextOption(
    name="poll_interval",
    description=(
        "Polling interval in seconds for checking query status "
        "(default: 0.5, lower = faster polling)"
    ),
    short_decls=["--poll-interval"],
    default="0.5",
    validator=_float_validator,
)

ATHENA_OPTIONS = [
    region,
    s3_staging_dir,
    work_group,
    schema,
    catalog,
    aws_access_key_id,
    aws_secret_access_key,
    aws_session_token,
    profile_name,
    poll_interval,
]

