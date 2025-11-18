import os
import sys
from typing import Generator

import pytest
from harlequin.adapter import HarlequinAdapter, HarlequinConnection, HarlequinCursor
from harlequin.catalog import Catalog, CatalogItem
from harlequin.exception import HarlequinQueryError
from harlequin_athena.adapter import HarlequinAthenaAdapter, HarlequinAthenaConnection
from textual_fastdatatable.backend import create_backend

if sys.version_info < (3, 10):
    from importlib_metadata import entry_points  # type: ignore
else:
    from importlib.metadata import entry_points

# Note: Tests marked with @pytest.mark.aws_required need AWS credentials
# Tests marked with @pytest.mark.no_aws can run without credentials


@pytest.fixture
def athena_options() -> dict:
    return {
        "region": "us-east-1",
        "s3_staging_dir": "s3://my-bucket/athena-results/",
        "schema": "default",
    }


@pytest.mark.no_aws  # This test doesn't require AWS credentials
def test_plugin_discovery() -> None:
    PLUGIN_NAME = "athena"
    eps = entry_points(group="harlequin.adapter")
    assert eps[PLUGIN_NAME]
    adapter_cls = eps[PLUGIN_NAME].load()
    assert issubclass(adapter_cls, HarlequinAdapter)
    assert adapter_cls == HarlequinAthenaAdapter


@pytest.mark.aws_required
def test_connect(athena_options: dict) -> None:
    conn = HarlequinAthenaAdapter(**athena_options).connect()
    assert isinstance(conn, HarlequinConnection)


@pytest.mark.aws_required
def test_init_extra_kwargs(athena_options: dict) -> None:
    assert HarlequinAthenaAdapter(**athena_options, foo=1, bar="baz").connect()


@pytest.fixture
def connection(
    athena_options: dict,
) -> Generator[HarlequinAthenaConnection, None, None]:
    # Note: This test requires actual AWS credentials and an Athena setup
    # In a real test environment, you might want to use moto or mock the connection
    conn = HarlequinAthenaAdapter(**athena_options).connect()
    yield conn


@pytest.mark.aws_required
def test_get_catalog(connection: HarlequinAthenaConnection) -> None:
    catalog = connection.get_catalog()
    assert isinstance(catalog, Catalog)
    assert catalog.items
    assert isinstance(catalog.items[0], CatalogItem)


@pytest.mark.aws_required
def test_execute_ddl(connection: HarlequinAthenaConnection) -> None:
    # Note: Athena DDL operations may require specific permissions
    # This test may need to be adjusted based on your test environment
    cur = connection.execute("SHOW TABLES")
    assert cur is not None
    data = cur.fetchall()
    # DDL operations may return empty results
    assert data is not None


@pytest.mark.aws_required
def test_execute_select(connection: HarlequinAthenaConnection) -> None:
    cur = connection.execute("SELECT 1 AS a")
    assert isinstance(cur, HarlequinCursor)
    assert cur.columns() == [("a", "#")]
    data = cur.fetchall()
    backend = create_backend(data)
    assert backend.column_count == 1
    assert backend.row_count == 1


@pytest.mark.aws_required
def test_execute_select_dupe_cols(connection: HarlequinAthenaConnection) -> None:
    cur = connection.execute("SELECT 1 AS a, 2 AS a, 3 AS a")
    assert isinstance(cur, HarlequinCursor)
    assert len(cur.columns()) == 3
    data = cur.fetchall()
    backend = create_backend(data)
    assert backend.column_count == 3
    assert backend.row_count == 1


@pytest.mark.aws_required
def test_set_limit(connection: HarlequinAthenaConnection) -> None:
    cur = connection.execute(
        "SELECT 1 AS a UNION ALL SELECT 2 UNION ALL SELECT 3"
    )
    assert isinstance(cur, HarlequinCursor)
    cur = cur.set_limit(2)
    assert isinstance(cur, HarlequinCursor)
    data = cur.fetchall()
    backend = create_backend(data)
    assert backend.column_count == 1
    assert backend.row_count == 2


@pytest.mark.aws_required
def test_execute_raises_query_error(connection: HarlequinAthenaConnection) -> None:
    with pytest.raises(HarlequinQueryError):
        _ = connection.execute("selec;")


@pytest.mark.no_aws  # This test doesn't require AWS credentials
def test_missing_s3_staging_dir() -> None:
    """Test that missing s3_staging_dir raises an error"""
    with pytest.raises(Exception):  # HarlequinConnectionError
        HarlequinAthenaAdapter(region="us-east-1").connect()

