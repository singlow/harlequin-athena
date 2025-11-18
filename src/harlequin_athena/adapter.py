from __future__ import annotations

import hashlib
import os
import pickle
import sys
from pathlib import Path
from typing import Any

from harlequin import (
    HarlequinAdapter,
    HarlequinConnection,
    HarlequinCursor,
)
from harlequin.autocomplete.completion import HarlequinCompletion
from harlequin.catalog import Catalog, CatalogItem, InteractiveCatalogItem
from harlequin.exception import HarlequinConnectionError, HarlequinQueryError
from pyathena import connect
from pyathena.connection import Connection
from textual_fastdatatable.backend import AutoBackendType

from harlequin_athena.cli_options import ATHENA_OPTIONS
from harlequin_athena.completions import load_completions


def _get_cache_dir() -> Path | None:
    """
    Get the OS-appropriate cache directory for harlequin-athena.
    Returns None if no suitable cache location is available.
    """
    try:
        if os.name == "nt":  # Windows
            cache_base = os.getenv("LOCALAPPDATA")
            if cache_base:
                cache_dir = Path(cache_base) / "harlequin-athena" / "cache"
            else:
                cache_dir = Path.home() / "harlequin-athena" / "cache"
        elif sys.platform == "darwin":  # macOS
            cache_dir = Path.home() / "Library" / "Caches" / "harlequin-athena"
        else:  # Linux and other Unix-like
            cache_base = os.getenv("XDG_CACHE_HOME")
            if not cache_base:
                cache_base = Path.home() / ".cache"
            else:
                cache_base = Path(cache_base)
            cache_dir = cache_base / "harlequin-athena"
        
        # Try to create the directory (will not fail if it exists)
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir
    except Exception:
        # Gracefully degrade if we can't create the cache directory
        return None


def _get_cache_key(
    catalog: str | None, region: str | None, work_group: str | None, schema: str | None
) -> str:
    """
    Generate a cache key from connection parameters.
    This ensures different connections get different cache entries.
    """
    # Ensure we have string values (handle None cases)
    catalog_str = catalog or "AwsDataCatalog"
    region_str = region or "us-east-1"
    
    key_parts = [catalog_str, region_str]
    if work_group:
        key_parts.append(f"wg:{work_group}")
    if schema:
        key_parts.append(f"schema:{schema}")
    
    key_string = "|".join(key_parts)
    return hashlib.sha256(key_string.encode()).hexdigest()


class HarlequinAthenaCursor(HarlequinCursor):
    def __init__(self, cur: Any) -> None:
        self.cur = cur
        self._limit: int | None = None
        # Preserve description before cursor is closed
        self._description: Any = None
        if self.cur.description is not None:
            self._description = self.cur.description

    def columns(self) -> list[tuple[str, str]]:
        # Use preserved description since cursor may be closed
        description = (
            self._description
            if self._description is not None
            else self.cur.description
        )
        # Some queries (like DDL) don't return a result set, so description can be None
        if description is None:
            return []
        return [(col[0], self._get_short_type(col[1])) for col in description]

    def set_limit(self, limit: int) -> HarlequinAthenaCursor:
        self._limit = limit
        return self

    def fetchall(self) -> AutoBackendType:
        try:
            # Preserve description before fetching (in case it changes)
            if self.cur.description is not None and self._description is None:
                self._description = self.cur.description
            
            if self._limit is None:
                result = self.cur.fetchall()
            else:
                result = self.cur.fetchmany(self._limit)
            
            # Ensure description is preserved after fetch
            if self.cur.description is not None:
                self._description = self.cur.description
            
            return result
        except Exception as e:
            raise HarlequinQueryError(
                msg=str(e),
                title="Harlequin encountered an error while executing your query.",
            ) from e
        finally:
            self.cur.close()

    @staticmethod
    def _get_short_type(type_name: str) -> str:
        MAPPING = {
            "array": "[]",
            "bigint": "##",
            "boolean": "t/f",
            "char": "s",
            "date": "d",
            "decimal": "#.#",
            "double": "#.#",
            "float": "#.#",
            "integer": "#",
            "interval": "|-|",
            "json": "{}",
            "real": "#.#",
            "smallint": "#",
            "string": "t",
            "time": "t",
            "timestamp": "ts",
            "tinyint": "#",
            "varchar": "t",
            "varbinary": "b",
            "struct": "{}",
            "map": "{}",
        }
        # Handle type names with parameters like "varchar(255)" or "decimal(10,2)"
        base_type = type_name.split("(")[0].split(" ")[0].lower()
        return MAPPING.get(base_type, "?")


class LazySchemaItem(InteractiveCatalogItem):
    """Interactive catalog item for schemas that loads tables on demand."""
    
    def __init__(
        self,
        connection: "HarlequinAthenaConnection",
        catalog: str,
        schema: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._connection = connection
        self._catalog = catalog
        self._schema = schema
        self._tables_loaded = False
    
    def fetch_children(self) -> list[CatalogItem]:
        """Load tables for this schema on demand."""
        if self._tables_loaded:
            return self.children
        
        # Load tables for this schema
        relations = self._connection._get_relations(self._catalog, self._schema)
        
        table_items: list[CatalogItem] = []
        for rel, rel_type in relations:
            table_items.append(
                LazyTableItem(
                    connection=self._connection,
                    catalog=self._catalog,
                    schema=self._schema,
                    table=rel,
                    qualified_identifier=f'"{self._catalog}"."{self._schema}"."{rel}"',
                    query_name=f'"{self._catalog}"."{self._schema}"."{rel}"',
                    label=rel,
                    type_label=rel_type,
                    children=[],
                )
            )
        
        self.children = table_items
        self._tables_loaded = True
        return table_items


class LazyTableItem(InteractiveCatalogItem):
    """Interactive catalog item for tables that loads columns on demand."""
    
    def __init__(
        self,
        connection: "HarlequinAthenaConnection",
        catalog: str,
        schema: str,
        table: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._connection = connection
        self._catalog = catalog
        self._schema = schema
        self._table = table
        self._columns_loaded = False
    
    def fetch_children(self) -> list[CatalogItem]:
        """Load columns for this table on demand."""
        if self._columns_loaded:
            return self.children
        
        # Load columns for this table
        cols = self._connection._get_columns(self._catalog, self._schema, self._table)
        
        col_items = [
            CatalogItem(
                qualified_identifier=f'"{self._catalog}"."{self._schema}"."{self._table}"."{col}"',
                query_name=f'"{col}"',
                label=col,
                type_label=self._connection._get_short_col_type(col_type),
            )
            for col, col_type in cols
        ]
        
        self.children = col_items
        self._columns_loaded = True
        return col_items


class HarlequinAthenaConnection(HarlequinConnection):
    def __init__(
        self,
        *_: Any,
        init_message: str = "",
        options: dict[str, Any],
    ) -> None:
        self.init_message = init_message
        modified_options = options.copy()
        
        # Extract Athena-specific options
        s3_staging_dir = modified_options.pop("s3_staging_dir", None)
        if not s3_staging_dir:
            raise HarlequinConnectionError(
                msg="s3_staging_dir is required for Athena connections",
                title="Harlequin could not connect to your database.",
            )
        
        region = modified_options.pop("region", "us-east-1")
        work_group = modified_options.pop("work_group", None)
        schema = modified_options.pop("schema", None)
        catalog = modified_options.pop("catalog", "AwsDataCatalog")
        
        # Polling interval for query status checks (in seconds)
        poll_interval_str = modified_options.pop("poll_interval", "0.5")
        try:
            poll_interval = float(poll_interval_str)
        except (ValueError, TypeError):
            poll_interval = 0.5  # Default to 0.5 seconds if invalid
        
        # AWS credentials
        aws_access_key_id = modified_options.pop("aws_access_key_id", None)
        aws_secret_access_key = modified_options.pop("aws_secret_access_key", None)
        aws_session_token = modified_options.pop("aws_session_token", None)
        profile_name = modified_options.pop("profile_name", None)
        
        self.catalog_filter = catalog
        self.schema_filter = schema
        
        # Store AWS credentials and region for boto3 operations
        self.region = region
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_session_token = aws_session_token
        self.profile_name = profile_name
        self.work_group = work_group
        
        # Set up persistent cache
        self._cache_dir = _get_cache_dir()
        self._cache_key = _get_cache_key(catalog, region, work_group, schema)
        self._cache_file: Path | None = None
        if self._cache_dir:
            self._cache_file = self._cache_dir / f"catalog_{self._cache_key}.pkl"
        
        # Build connection parameters for pyathena
        conn_params: dict[str, Any] = {
            "s3_staging_dir": s3_staging_dir,
            "region_name": region,
            # Polling interval in seconds for query status checks
            "poll_interval": poll_interval,
        }
        
        if work_group:
            conn_params["work_group"] = work_group
        
        if schema:
            conn_params["schema_name"] = schema
        
        if aws_access_key_id and aws_secret_access_key:
            conn_params["aws_access_key_id"] = aws_access_key_id
            conn_params["aws_secret_access_key"] = aws_secret_access_key
            if aws_session_token:
                conn_params["aws_session_token"] = aws_session_token
        
        if profile_name:
            conn_params["profile_name"] = profile_name

        try:
            self.conn: Connection = connect(**conn_params)
        except Exception as e:
            raise HarlequinConnectionError(
                msg=str(e), title="Harlequin could not connect to your database."
            ) from e

        # Initialize in-memory cache for catalog metadata
        # Note: We use InteractiveCatalogItems which can't be pickled,
        # so we only use in-memory caching, not persistent cache
        self._catalog_cache: Catalog | None = None

    def execute(self, query: str) -> HarlequinCursor | None:
        try:
            cur = self.conn.cursor()
            cur.execute(query)
            
            # Invalidate cache if this is a DDL operation that might change the catalog
            query_upper = query.strip().upper()
            ddl_keywords = ("CREATE", "DROP", "ALTER", "TRUNCATE", "RENAME")
            if any(query_upper.startswith(keyword) for keyword in ddl_keywords):
                self.invalidate_catalog_cache()
        except Exception as e:
            raise HarlequinQueryError(
                msg=str(e),
                title="Harlequin encountered an error while executing your query.",
            ) from e
        return HarlequinAthenaCursor(cur)

    def get_catalog(self) -> Catalog:
        # Return cached catalog if available
        # Note: InteractiveCatalogItems can't be pickled, so we rebuild them each time
        # but the schema list is cached in memory
        if self._catalog_cache is not None:
            return self._catalog_cache

        if self.catalog_filter:
            catalogs = [(self.catalog_filter,)]
        else:
            catalogs = self._get_catalogs()

        db_items: list[CatalogItem] = []
        for (catalog,) in catalogs:
            if self.schema_filter:
                schemas = [(self.schema_filter,)]
            else:
                schemas = self._get_schemas(catalog)

            # Use LazySchemaItem for true lazy loading - tables/columns load on demand
            schema_items: list[CatalogItem] = []
            for (schema,) in schemas:
                schema_items.append(
                    LazySchemaItem(
                        connection=self,
                        catalog=catalog,
                        schema=schema,
                        qualified_identifier=f'"{catalog}"."{schema}"',
                        query_name=f'"{catalog}"."{schema}"',
                        label=schema,
                        type_label="s",
                        children=[],  # Will be loaded via fetch_children()
                    )
                )

            db_items.append(
                CatalogItem(
                    qualified_identifier=f'"{catalog}"',
                    query_name=f'"{catalog}"',
                    label=catalog,
                    type_label="c",
                    children=schema_items,
                )
            )
        
        # Cache the catalog (InteractiveCatalogItems will be recreated but that's fine)
        catalog_obj = Catalog(items=db_items)
        self._catalog_cache = catalog_obj
        # Don't save to persistent cache since InteractiveCatalogItems aren't pickleable
        return catalog_obj


    def _load_catalog_cache(self) -> None:
        """Load catalog from persistent cache if available."""
        if not self._cache_file or not self._cache_file.exists():
            return
        
        try:
            with open(self._cache_file, "rb") as f:
                self._catalog_cache = pickle.load(f)
            
            # Detect which schemas were fully loaded (have children/tables)
            if self._catalog_cache:
                for catalog_item in self._catalog_cache.items:
                    for schema_item in catalog_item.children:
                        if schema_item.children:  # Has tables/columns
                            self._loaded_schemas.add(schema_item.label)
        except Exception:
            # Gracefully degrade if cache file is corrupted or unreadable
            # Remove the corrupted cache file
            try:
                self._cache_file.unlink()
            except Exception:
                pass
            self._catalog_cache = None

    def _save_catalog_cache(self, catalog: Catalog) -> None:
        """Save catalog to persistent cache if available."""
        if not self._cache_file:
            return
        
        try:
            with open(self._cache_file, "wb") as f:
                pickle.dump(catalog, f)
        except Exception:
            # Gracefully degrade if we can't write to cache
            # Continue without persistent caching
            pass

    def invalidate_catalog_cache(self) -> None:
        """Invalidate the cached catalog to force a refresh on next get_catalog() call."""  # noqa: E501
        self._catalog_cache = None

    def _get_catalogs(self) -> list[tuple[str]]:
        """
        Get list of catalogs.
        Athena doesn't support SHOW CATALOGS, so we return the default catalog.
        Users can specify custom catalogs via the --catalog CLI option.
        """
        # Athena typically uses AwsDataCatalog as the default catalog.
        # If users have custom catalogs, they should specify them via --catalog.
        return [("AwsDataCatalog",)]

    def _get_schemas(self, catalog: str) -> list[tuple[str]]:
        """
        Get list of schemas (databases) for the given catalog.
        Athena uses SHOW DATABASES to list schemas, and doesn't support
        the IN catalog syntax for SHOW commands.
        """
        cur = self.conn.cursor()
        # Athena uses SHOW DATABASES to list schemas/databases
        # The catalog is set via the connection, not in the SHOW command
        cur.execute("SHOW DATABASES")
        results: list[tuple[str]] = cur.fetchall()
        cur.close()
        return [result for result in results if result[0] != "information_schema"]

    def _get_all_relations(
        self, catalog: str, schemas: list[str]
    ) -> dict[str, list[tuple[str, str]]]:
        """
        Batch fetch all tables for multiple schemas in a single query.
        Returns a dict mapping schema name to list of (table_name, table_type) tuples.
        """
        if not schemas:
            return {}
        
        cur = self.conn.cursor()
        # Build IN clause for schemas, escaping single quotes
        schema_list = ", ".join(
            f"'{s.replace(chr(39), chr(39)+chr(39))}'" for s in schemas
        )
        query = f"""
            SELECT
                table_schema,
                table_name,
                CASE
                    WHEN table_type LIKE '%TABLE' THEN 't'
                    ELSE 'v'
                END AS table_type
            FROM "{catalog}".information_schema.tables
            WHERE table_schema IN ({schema_list})
        """
        cur.execute(query)
        results: list[tuple[str, str, str]] = cur.fetchall()
        cur.close()
        
        # Group by schema
        relations_by_schema: dict[str, list[tuple[str, str]]] = {}
        for schema, table_name, table_type in results:
            if schema not in relations_by_schema:
                relations_by_schema[schema] = []
            relations_by_schema[schema].append((table_name, table_type))
        
        return relations_by_schema

    def _get_relations(self, catalog: str, schema: str) -> list[tuple[str, str]]:
        """Get relations for a single schema (for backward compatibility)."""
        all_relations = self._get_all_relations(catalog, [schema])
        return all_relations.get(schema, [])

    def _get_all_columns(
        self, catalog: str, relations_by_schema: dict[str, list[tuple[str, str]]]
    ) -> dict[tuple[str, str], list[tuple[str, str]]]:
        """
        Batch fetch all columns for all tables across all schemas.
        Returns a dict mapping (schema, table) to list of
        (column_name, data_type) tuples.
        """
        if not relations_by_schema:
            return {}
        
        # Build the WHERE clause with all (schema, table) pairs
        conditions = []
        for schema, relations in relations_by_schema.items():
            for table_name, _ in relations:
                # Escape single quotes in schema and table names
                schema_escaped = schema.replace("'", "''")
                table_escaped = table_name.replace("'", "''")
                conditions.append(
                    f"(table_schema = '{schema_escaped}' "
                    f"AND table_name = '{table_escaped}')"
                )
        
        if not conditions:
            return {}
        
        cur = self.conn.cursor()
        where_clause = " OR ".join(conditions)
        query = f"""
            SELECT
                table_schema,
                table_name,
                column_name,
                data_type
            FROM "{catalog}".information_schema.columns
            WHERE {where_clause}
            ORDER BY table_schema, table_name, ordinal_position
        """
        cur.execute(query)
        results: list[tuple[str, str, str, str]] = cur.fetchall()
        cur.close()
        
        # Group by (schema, table)
        columns_by_table: dict[tuple[str, str], list[tuple[str, str]]] = {}
        for schema, table_name, column_name, data_type in results:
            key = (schema, table_name)
            if key not in columns_by_table:
                columns_by_table[key] = []
            columns_by_table[key].append((column_name, data_type))
        
        return columns_by_table

    def _get_columns(
        self, catalog: str, schema: str, rel: str
    ) -> list[tuple[str, str]]:
        """Get columns for a single table (for backward compatibility)."""
        all_columns = self._get_all_columns(
            catalog, {schema: [(rel, "t")]}  # Assume table type
        )
        return all_columns.get((schema, rel), [])

    @staticmethod
    def _get_short_col_type(type_name: str) -> str:
        MAPPING = {
            "array": "[]",
            "bigint": "##",
            "boolean": "t/f",
            "char": "s",
            "date": "d",
            "decimal": "#.#",
            "double": "#.#",
            "float": "#.#",
            "integer": "#",
            "interval": "|-|",
            "json": "{}",
            "real": "#.#",
            "smallint": "#",
            "string": "t",
            "time": "t",
            "timestamp": "ts",
            "tinyint": "#",
            "varchar": "t",
            "varbinary": "b",
            "struct": "{}",
            "map": "{}",
        }
        # Handle type names with parameters like "varchar(255)" or "decimal(10,2)"
        base_type = type_name.split("(")[0].split(" ")[0].lower()
        return MAPPING.get(base_type, "?")

    def get_completions(self) -> list[HarlequinCompletion]:
        return load_completions()


class HarlequinAthenaAdapter(HarlequinAdapter):
    ADAPTER_OPTIONS = ATHENA_OPTIONS

    def __init__(
        self,
        region: str | None = None,
        s3_staging_dir: str | None = None,
        work_group: str | None = None,
        schema: str | None = None,
        catalog: str | None = None,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_session_token: str | None = None,
        profile_name: str | None = None,
        poll_interval: str | None = None,
        **_: Any,
    ) -> None:
        # Support environment variables as fallback when CLI options are not provided
        # Only for adapter-specific options not covered by standard AWS SDK environment variables
        # AWS SDK automatically handles: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN,
        # AWS_REGION/AWS_DEFAULT_REGION, AWS_PROFILE
        self.options = {
            "region": region,  # AWS SDK handles AWS_REGION/AWS_DEFAULT_REGION automatically
            "s3_staging_dir": s3_staging_dir or os.getenv("HARLEQUIN_ATHENA_S3_STAGING_DIR"),
            "work_group": work_group or os.getenv("HARLEQUIN_ATHENA_WORK_GROUP"),
            "schema": schema or os.getenv("HARLEQUIN_ATHENA_SCHEMA"),
            "catalog": catalog or os.getenv("HARLEQUIN_ATHENA_CATALOG"),
            "aws_access_key_id": aws_access_key_id,  # AWS SDK handles AWS_ACCESS_KEY_ID automatically
            "aws_secret_access_key": aws_secret_access_key,  # AWS SDK handles AWS_SECRET_ACCESS_KEY automatically
            "aws_session_token": aws_session_token,  # AWS SDK handles AWS_SESSION_TOKEN automatically
            "profile_name": profile_name,  # AWS SDK handles AWS_PROFILE automatically
            "poll_interval": poll_interval or os.getenv("HARLEQUIN_ATHENA_POLL_INTERVAL"),
        }

    def connect(self) -> HarlequinAthenaConnection:
        conn = HarlequinAthenaConnection(options=self.options)
        return conn

