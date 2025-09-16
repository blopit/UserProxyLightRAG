"""
Scope-aware PostgreSQL storage implementations.

This module provides PostgreSQL-based storage implementations with full
scope support, extending the base PostgreSQL implementations.
"""

import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional, Union, final
from dataclasses import dataclass

import asyncpg
from lightrag.base import BaseKVStorage, BaseVectorStorage, BaseGraphStorage
from lightrag.utils import logger
from lightrag.exceptions import StorageNotInitializedError

from .context import ScopeContext, ScopeResolver
from .storage import ScopeAwareStorageMixin
from .exceptions import ScopeResolutionError


@final
@dataclass
class ScopeAwarePGKVStorage(BaseKVStorage, ScopeAwareStorageMixin):
    """PostgreSQL-based key-value storage with scope awareness."""

    def __post_init__(self):
        BaseKVStorage.__post_init__(self)
        ScopeAwareStorageMixin.__init__(self)

        # PostgreSQL connection configuration
        self.db_config = {
            "host": self.global_config.get("pg_host", "localhost"),
            "port": self.global_config.get("pg_port", 5432),
            "database": self.global_config.get("pg_database", "lightrag"),
            "user": self.global_config.get("pg_user", "postgres"),
            "password": self.global_config.get("pg_password", "password"),
        }

        self.pool: Optional[asyncpg.Pool] = None
        self._table_name = f"kv_{self.namespace}"

    async def initialize(self):
        """Initialize PostgreSQL connection and create scope-aware tables."""
        try:
            self.pool = await asyncpg.create_pool(**self.db_config, min_size=1, max_size=10)

            # Create scope-aware table
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self._table_name} (
                        id VARCHAR(255) PRIMARY KEY,
                        data JSONB NOT NULL,
                        workspace VARCHAR(32),
                        subject_type VARCHAR(50),
                        subject_id VARCHAR(63),
                        project VARCHAR(63),
                        thread VARCHAR(63),
                        topic VARCHAR(63),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Create scope-based indexes
                scope_columns = ["workspace", "subject_type", "subject_id", "project", "thread", "topic"]
                for col in scope_columns:
                    await conn.execute(f"""
                        CREATE INDEX IF NOT EXISTS idx_{self._table_name}_{col}
                        ON {self._table_name} ({col})
                        WHERE {col} IS NOT NULL
                    """)

                # Create composite index for common scope queries
                await conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self._table_name}_scope_composite
                    ON {self._table_name} (workspace, subject_type, subject_id, project, thread, topic)
                """)

                logger.info(f"Initialized scope-aware PostgreSQL KV storage: {self._table_name}")

        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL KV storage: {str(e)}")
            raise StorageNotInitializedError(f"PostgreSQL initialization failed: {str(e)}")

    async def finalize(self):
        """Close PostgreSQL connections."""
        if self.pool:
            await self.pool.close()

    async def get_by_id(self, id: str) -> Any:
        """Get value by ID from current scope."""
        if not self.pool:
            raise StorageNotInitializedError("Storage not initialized")

        scope_filter = self._build_scope_where_clause()

        async with self.pool.acquire() as conn:
            query = f"SELECT data FROM {self._table_name} WHERE id = $1 {scope_filter['clause']}"
            params = [id] + scope_filter['params']

            result = await conn.fetchval(query, *params)
            return result

    async def get_by_ids(self, ids: List[str]) -> List[Any]:
        """Get multiple values by IDs from current scope."""
        if not self.pool:
            raise StorageNotInitializedError("Storage not initialized")

        if not ids:
            return []

        scope_filter = self._build_scope_where_clause()

        async with self.pool.acquire() as conn:
            placeholders = ",".join(f"${i+2}" for i in range(len(ids)))
            query = f"SELECT data FROM {self._table_name} WHERE id = ANY(ARRAY[{placeholders}]) {scope_filter['clause']} ORDER BY id"
            params = [None] + ids + scope_filter['params']

            results = await conn.fetch(query, *params[1:])  # Skip the first None
            return [row['data'] for row in results]

    async def filter_keys(self, keys: List[str]) -> List[str]:
        """Filter keys that exist in current scope."""
        if not self.pool:
            raise StorageNotInitializedError("Storage not initialized")

        if not keys:
            return []

        scope_filter = self._build_scope_where_clause()

        async with self.pool.acquire() as conn:
            placeholders = ",".join(f"${i+2}" for i in range(len(keys)))
            query = f"SELECT id FROM {self._table_name} WHERE id = ANY(ARRAY[{placeholders}]) {scope_filter['clause']}"
            params = [None] + keys + scope_filter['params']

            results = await conn.fetch(query, *params[1:])
            return [row['id'] for row in results]

    async def upsert(self, data: Dict[str, Any]):
        """Upsert data into current scope."""
        if not self.pool:
            raise StorageNotInitializedError("Storage not initialized")

        if not data:
            return

        scope_values = self._get_scope_values()

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for key, value in data.items():
                    # Add scope metadata to the stored data
                    scoped_value = self.add_scope_metadata(value) if isinstance(value, dict) else value

                    await conn.execute(f"""
                        INSERT INTO {self._table_name}
                        (id, data, workspace, subject_type, subject_id, project, thread, topic, updated_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, CURRENT_TIMESTAMP)
                        ON CONFLICT (id) DO UPDATE SET
                        data = EXCLUDED.data,
                        workspace = EXCLUDED.workspace,
                        subject_type = EXCLUDED.subject_type,
                        subject_id = EXCLUDED.subject_id,
                        project = EXCLUDED.project,
                        thread = EXCLUDED.thread,
                        topic = EXCLUDED.topic,
                        updated_at = CURRENT_TIMESTAMP
                    """, key, json.dumps(scoped_value), *scope_values)

    async def delete(self, id: str) -> bool:
        """Delete item by ID from current scope."""
        if not self.pool:
            raise StorageNotInitializedError("Storage not initialized")

        scope_filter = self._build_scope_where_clause()

        async with self.pool.acquire() as conn:
            query = f"DELETE FROM {self._table_name} WHERE id = $1 {scope_filter['clause']}"
            params = [id] + scope_filter['params']

            result = await conn.execute(query, *params)
            return result != "DELETE 0"

    async def drop(self) -> Dict[str, str]:
        """Drop all data from scope-aware storage."""
        try:
            if not self.pool:
                return {"status": "error", "message": "Storage not initialized"}

            scope_filter = self._build_scope_where_clause()

            async with self.pool.acquire() as conn:
                if scope_filter['clause']:
                    # Delete only scope-specific data
                    query = f"DELETE FROM {self._table_name} {scope_filter['clause']}"
                    await conn.execute(query, *scope_filter['params'])
                else:
                    # Delete all data if no scope set
                    await conn.execute(f"DELETE FROM {self._table_name}")

            scope_info = f"scope={self._scope_context}" if self._scope_context else "all data"
            logger.info(f"Dropped PostgreSQL KV storage data for {scope_info}")

            return {"status": "success", "message": "data dropped"}

        except Exception as e:
            error_msg = f"Failed to drop storage: {str(e)}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}

    def _build_scope_where_clause(self) -> Dict[str, Any]:
        """Build WHERE clause for scope filtering."""
        if not self._scope_context:
            return {"clause": "", "params": []}

        conditions = []
        params = []
        param_index = 2  # Start from $2 since $1 is usually the id

        scope_filter = self._scope_context.to_filter_dict()

        for field, value in scope_filter.items():
            if value is not None:
                conditions.append(f"{field} = ${param_index}")
                params.append(value)
                param_index += 1

        if conditions:
            clause = "AND " + " AND ".join(conditions)
        else:
            clause = ""

        return {"clause": clause, "params": params}

    def _get_scope_values(self) -> tuple:
        """Get scope values for database operations."""
        if not self._scope_context:
            return (None, None, None, None, None, None)

        return (
            self._scope_context.workspace,
            self._scope_context.subject_type.value,
            self._scope_context.subject_id,
            self._scope_context.project,
            self._scope_context.thread,
            self._scope_context.topic
        )

    # ScopeAwareStorageMixin implementation
    async def scope_aware_get(self, key: str, scope: Optional[ScopeContext] = None) -> Any:
        """Get value with explicit scope."""
        if scope is not None:
            original_scope = self._scope_context
            self.set_scope_context(scope)
            try:
                return await self.get_by_id(key)
            finally:
                self.set_scope_context(original_scope)
        else:
            return await self.get_by_id(key)

    async def scope_aware_set(self, key: str, value: Any, scope: Optional[ScopeContext] = None) -> None:
        """Set value with explicit scope."""
        if scope is not None:
            original_scope = self._scope_context
            self.set_scope_context(scope)
            try:
                await self.upsert({key: value})
            finally:
                self.set_scope_context(original_scope)
        else:
            await self.upsert({key: value})

    async def scope_aware_delete(self, key: str, scope: Optional[ScopeContext] = None) -> bool:
        """Delete value with explicit scope."""
        if scope is not None:
            original_scope = self._scope_context
            self.set_scope_context(scope)
            try:
                return await self.delete(key)
            finally:
                self.set_scope_context(original_scope)
        else:
            return await self.delete(key)

    async def scope_aware_list_keys(self, scope: Optional[ScopeContext] = None,
                                   pattern: Optional[str] = None) -> List[str]:
        """List keys within a scope."""
        if not self.pool:
            raise StorageNotInitializedError("Storage not initialized")

        target_scope = scope or self._scope_context
        original_scope = self._scope_context

        if target_scope != original_scope:
            self.set_scope_context(target_scope)

        try:
            scope_filter = self._build_scope_where_clause()

            async with self.pool.acquire() as conn:
                if pattern:
                    query = f"SELECT id FROM {self._table_name} WHERE id LIKE $1 {scope_filter['clause']}"
                    params = [pattern.replace('*', '%')] + scope_filter['params']
                else:
                    query = f"SELECT id FROM {self._table_name} WHERE TRUE {scope_filter['clause']}"
                    params = scope_filter['params']

                results = await conn.fetch(query, *params)
                return [row['id'] for row in results]

        finally:
            if target_scope != original_scope:
                self.set_scope_context(original_scope)

    async def list_scopes(self, pattern: Optional[str] = None) -> List[ScopeContext]:
        """List available scopes in this storage."""
        if not self.pool:
            raise StorageNotInitializedError("Storage not initialized")

        scopes = []

        async with self.pool.acquire() as conn:
            query = f"""
                SELECT DISTINCT workspace, subject_type, subject_id, project, thread, topic
                FROM {self._table_name}
                WHERE workspace IS NOT NULL AND subject_type IS NOT NULL AND subject_id IS NOT NULL
            """

            results = await conn.fetch(query)

            for row in results:
                try:
                    # Build SRN string
                    srn_parts = [
                        "1",
                        row['workspace'],
                        row['subject_type'],
                        row['subject_id']
                    ]

                    if row['project']:
                        srn_parts.append(f"proj_{row['project']}")
                    if row['thread']:
                        srn_parts.append(f"thr_{row['thread']}")
                    if row['topic']:
                        srn_parts.append(f"top_{row['topic']}")

                    srn_string = ".".join(srn_parts)
                    scope = ScopeContext(srn_string)

                    # Apply pattern filtering if specified
                    if pattern and not any(pattern in str(v) for v in [srn_string] + list(row.values())):
                        continue

                    scopes.append(scope)

                except Exception as e:
                    logger.warning(f"Failed to create scope from row {row}: {str(e)}")

        return scopes

    async def migrate_workspace_data(self, workspace: str, target_scope: ScopeContext) -> bool:
        """Migrate data from workspace-based storage to scope-based storage."""
        if not self.pool:
            raise StorageNotInitializedError("Storage not initialized")

        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    # Find all data with the old workspace format
                    old_data = await conn.fetch(f"""
                        SELECT id, data FROM {self._table_name}
                        WHERE workspace IS NULL OR workspace = $1
                    """, workspace)

                    if not old_data:
                        logger.info(f"No workspace data found for {workspace}")
                        return True

                    scope_values = (
                        target_scope.workspace,
                        target_scope.subject_type.value,
                        target_scope.subject_id,
                        target_scope.project,
                        target_scope.thread,
                        target_scope.topic
                    )

                    # Update each record with scope information
                    for row in old_data:
                        await conn.execute(f"""
                            UPDATE {self._table_name} SET
                            workspace = $2,
                            subject_type = $3,
                            subject_id = $4,
                            project = $5,
                            thread = $6,
                            topic = $7,
                            updated_at = CURRENT_TIMESTAMP
                            WHERE id = $1
                        """, row['id'], *scope_values)

                    logger.info(f"Migrated {len(old_data)} items from workspace {workspace} to scope {target_scope}")
                    return True

        except Exception as e:
            logger.error(f"Failed to migrate workspace {workspace} to scope {target_scope}: {str(e)}")
            return False

    async def index_done_callback(self) -> None:
        """Callback after indexing operations (no-op for PostgreSQL)."""
        pass