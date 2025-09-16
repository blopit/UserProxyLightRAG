"""
Scope-aware storage implementations.

This module provides concrete implementations of scope-aware storage
that extend the base LightRAG storage classes with SRN support.
"""

import os
import glob
import fnmatch
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, final

from lightrag.base import BaseKVStorage
from lightrag.utils import load_json, write_json, logger
from lightrag.exceptions import StorageNotInitializedError

from .context import ScopeContext, ScopeResolver
from .storage import ScopeAwareStorageMixin, ScopeAwareKVStorage
from .exceptions import ScopeResolutionError


@final
@dataclass
class ScopeAwareJsonKVStorage(BaseKVStorage, ScopeAwareStorageMixin):
    """
    JSON-based key-value storage with scope awareness.

    This implementation extends the base JSON KV storage to support
    scope-based data partitioning using directory hierarchies.
    """

    def __post_init__(self):
        # Call parent post_init first
        BaseKVStorage.__post_init__(self)
        ScopeAwareStorageMixin.__init__(self)

        working_dir = self.global_config["working_dir"]

        # Handle backward compatibility with workspace
        if self.workspace:
            self.final_namespace = f"{self.workspace}_{self.namespace}"
            # For scope-aware storage, workspace can be used as fallback
            self._fallback_workspace = self.workspace
        else:
            self.final_namespace = self.namespace
            self._fallback_workspace = "_"
            self.workspace = "_"

        # Initialize storage paths
        self._base_working_dir = working_dir
        self._scope_aware_mode = True
        self._data = None
        self._storage_lock = None
        self.storage_updated = None

    def _get_storage_path(self, scope: Optional[ScopeContext] = None) -> str:
        """
        Get the storage path for a given scope.

        Args:
            scope: Scope context (uses current scope if None)

        Returns:
            Full path to the storage file
        """
        target_scope = scope or self._scope_context

        if target_scope is None:
            # Fall back to workspace-based storage
            if self._fallback_workspace and self._fallback_workspace != "_":
                workspace_dir = os.path.join(self._base_working_dir, self._fallback_workspace)
            else:
                workspace_dir = self._base_working_dir
            os.makedirs(workspace_dir, exist_ok=True)
            return os.path.join(workspace_dir, f"kv_store_{self.namespace}.json")

        # Use scope-aware directory structure
        scope_dir = self.get_scope_directory_path(self._base_working_dir)
        os.makedirs(scope_dir, exist_ok=True)
        return os.path.join(scope_dir, f"kv_store_{self.namespace}.json")

    def _get_scoped_namespace(self, scope: Optional[ScopeContext] = None) -> str:
        """
        Get namespace with scope information.

        Args:
            scope: Scope context (uses current scope if None)

        Returns:
            Scoped namespace string
        """
        target_scope = scope or self._scope_context

        if target_scope is None:
            return self.final_namespace

        return f"{target_scope.workspace}_{target_scope.subject_type.value}_{target_scope.subject_id}_{self.namespace}"

    async def initialize(self):
        """Initialize storage data with scope awareness."""
        from lightrag.kg.shared_storage import (
            get_storage_lock,
            get_data_init_lock,
            get_update_flag,
            get_namespace_data,
            try_initialize_namespace,
        )

        # Get the appropriate namespace
        namespace = self._get_scoped_namespace()

        self._storage_lock = get_storage_lock()
        self.storage_updated = await get_update_flag(namespace)

        async with get_data_init_lock():
            need_init = await try_initialize_namespace(namespace)
            self._data = await get_namespace_data(namespace)

            if need_init:
                file_path = self._get_storage_path()
                loaded_data = load_json(file_path) or {}

                async with self._storage_lock:
                    # Apply scope filtering if in scope mode
                    if self._scope_context is not None:
                        loaded_data = self._filter_data_by_scope(loaded_data)

                    self._data.update(loaded_data)
                    data_count = len(loaded_data)

                    scope_info = f"scope={self._scope_context}" if self._scope_context else f"workspace={self.workspace}"
                    logger.info(
                        f"[{scope_info}] Process {os.getpid()} KV load {self.namespace} with {data_count} records"
                    )

    def _filter_data_by_scope(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Filter data to only include items matching current scope."""
        if self._scope_context is None:
            return data

        filtered_data = {}
        scope_filter = self._scope_context.to_filter_dict()

        for key, value in data.items():
            if isinstance(value, dict):
                # Check if this item matches the scope
                matches = True
                for scope_key, scope_value in scope_filter.items():
                    if scope_key not in value or value[scope_key] != scope_value:
                        matches = False
                        break

                if matches:
                    # Remove scope metadata from the actual data
                    clean_value = self.extract_data_without_scope(value)
                    filtered_data[key] = clean_value
            else:
                # Non-dict values are included as-is for backward compatibility
                filtered_data[key] = value

        return filtered_data

    async def index_done_callback(self) -> None:
        """Commit storage operations with scope awareness."""
        async with self._storage_lock:
            if self.storage_updated.value:
                data_dict = (
                    dict(self._data) if hasattr(self._data, "_getvalue") else self._data
                )

                # Add scope metadata to all items if in scope mode
                if self._scope_context is not None:
                    scoped_data = {}
                    for key, value in data_dict.items():
                        if isinstance(value, dict):
                            scoped_value = self.add_scope_metadata(value)
                            scoped_data[key] = scoped_value
                        else:
                            scoped_data[key] = value
                    data_dict = scoped_data

                data_count = len(data_dict)
                file_path = self._get_storage_path()

                write_json(data_dict, file_path)

                scope_info = f"scope={self._scope_context}" if self._scope_context else f"workspace={self.workspace}"
                logger.info(
                    f"[{scope_info}] Process {os.getpid()} KV save {self.namespace} with {data_count} records"
                )

                self.storage_updated.value = False

    async def finalize(self):
        """Finalize storage operations."""
        # Ensure data is persisted
        await self.index_done_callback()

    async def drop(self) -> Dict[str, str]:
        """Drop all data from scope-aware storage."""
        try:
            if self._data is not None:
                self._data.clear()

            file_path = self._get_storage_path()
            if os.path.exists(file_path):
                os.remove(file_path)

            # Also remove parent directories if they're empty
            parent_dir = os.path.dirname(file_path)
            try:
                os.rmdir(parent_dir)
            except OSError:
                pass  # Directory not empty or doesn't exist

            scope_info = f"scope={self._scope_context}" if self._scope_context else f"workspace={self.workspace}"
            logger.info(f"[{scope_info}] Dropped KV storage {self.namespace}")

            return {"status": "success", "message": "data dropped"}

        except Exception as e:
            error_msg = f"Failed to drop storage: {str(e)}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}

    # BaseKVStorage interface implementation
    async def get_by_id(self, id: str) -> Any:
        """Get value by ID from current scope."""
        if self._data is None:
            raise StorageNotInitializedError("Storage not initialized")

        return self._data.get(id)

    async def get_by_ids(self, ids: List[str]) -> List[Any]:
        """Get multiple values by IDs from current scope."""
        if self._data is None:
            raise StorageNotInitializedError("Storage not initialized")

        return [self._data.get(id) for id in ids]

    async def filter_keys(self, keys: List[str]) -> List[str]:
        """Filter keys that exist in current scope."""
        if self._data is None:
            raise StorageNotInitializedError("Storage not initialized")

        return [key for key in keys if key in self._data]

    async def upsert(self, data: Dict[str, Any]):
        """Upsert data into current scope."""
        if self._data is None:
            raise StorageNotInitializedError("Storage not initialized")

        async with self._storage_lock:
            self._data.update(data)
            self.storage_updated.value = True

    async def delete(self, id: str) -> bool:
        """Delete item by ID from current scope."""
        if self._data is None:
            raise StorageNotInitializedError("Storage not initialized")

        if id in self._data:
            async with self._storage_lock:
                del self._data[id]
                self.storage_updated.value = True
            return True
        return False

    # ScopeAwareStorageMixin interface implementation
    async def scope_aware_get(self, key: str, scope: Optional[ScopeContext] = None) -> Any:
        """Get value with explicit scope."""
        if scope is not None:
            # Temporarily switch scope
            original_scope = self._scope_context
            self.set_scope_context(scope)
            try:
                # Reinitialize with new scope if needed
                await self.initialize()
                result = await self.get_by_id(key)
                return result
            finally:
                self.set_scope_context(original_scope)
        else:
            return await self.get_by_id(key)

    async def scope_aware_set(self, key: str, value: Any, scope: Optional[ScopeContext] = None) -> None:
        """Set value with explicit scope."""
        if scope is not None:
            # Temporarily switch scope
            original_scope = self._scope_context
            self.set_scope_context(scope)
            try:
                await self.initialize()
                await self.upsert({key: value})
                await self.index_done_callback()
            finally:
                self.set_scope_context(original_scope)
        else:
            await self.upsert({key: value})

    async def scope_aware_delete(self, key: str, scope: Optional[ScopeContext] = None) -> bool:
        """Delete value with explicit scope."""
        if scope is not None:
            # Temporarily switch scope
            original_scope = self._scope_context
            self.set_scope_context(scope)
            try:
                await self.initialize()
                result = await self.delete(key)
                await self.index_done_callback()
                return result
            finally:
                self.set_scope_context(original_scope)
        else:
            return await self.delete(key)

    async def scope_aware_list_keys(self, scope: Optional[ScopeContext] = None,
                                   pattern: Optional[str] = None) -> List[str]:
        """List keys within a scope."""
        if scope is not None:
            # Temporarily switch scope
            original_scope = self._scope_context
            self.set_scope_context(scope)
            try:
                await self.initialize()
                keys = list(self._data.keys())
            finally:
                self.set_scope_context(original_scope)
        else:
            if self._data is None:
                raise StorageNotInitializedError("Storage not initialized")
            keys = list(self._data.keys())

        # Apply pattern filtering if specified
        if pattern:
            keys = [key for key in keys if fnmatch.fnmatch(key, pattern)]

        return keys

    async def list_scopes(self, pattern: Optional[str] = None) -> List[ScopeContext]:
        """List available scopes in this storage."""
        scopes = []
        resolver = ScopeResolver()

        # Scan directory structure for scope-based storage
        if os.path.exists(self._base_working_dir):
            # Look for workspace directories (32 hex chars)
            for workspace_dir in os.listdir(self._base_working_dir):
                workspace_path = os.path.join(self._base_working_dir, workspace_dir)
                if not os.path.isdir(workspace_path):
                    continue

                # Check if this looks like a workspace (32 hex chars)
                if len(workspace_dir) == 32 and all(c in '0123456789abcdef' for c in workspace_dir.lower()):
                    # This is a scope-based structure
                    await self._scan_scope_directory(workspace_path, workspace_dir, scopes)
                elif workspace_dir != "_":
                    # This might be a legacy workspace - convert to scope
                    try:
                        legacy_scope = resolver.create_scope_from_workspace(workspace_dir)
                        scopes.append(legacy_scope)
                    except Exception:
                        pass  # Skip invalid workspace directories

        # Apply pattern filtering if specified
        if pattern:
            scopes = [scope for scope in scopes if fnmatch.fnmatch(str(scope), pattern)]

        return scopes

    async def _scan_scope_directory(self, workspace_path: str, workspace: str, scopes: List[ScopeContext]):
        """Recursively scan scope directory structure."""
        from lightrag.scope.srn import SubjectType

        # Look for subject type directories
        for subject_type_dir in os.listdir(workspace_path):
            subject_type_path = os.path.join(workspace_path, subject_type_dir)
            if not os.path.isdir(subject_type_path):
                continue

            try:
                subject_type = SubjectType(subject_type_dir)
            except ValueError:
                continue  # Skip invalid subject types

            # Look for subject ID directories
            for subject_id_dir in os.listdir(subject_type_path):
                subject_id_path = os.path.join(subject_type_path, subject_id_dir)
                if not os.path.isdir(subject_id_path):
                    continue

                # Create base scope
                try:
                    base_scope = ScopeContext(f"1.{workspace}.{subject_type_dir}.{subject_id_dir}")
                    scopes.append(base_scope)

                    # Recursively scan for project/thread/topic subdirectories
                    await self._scan_optional_scope_components(
                        subject_id_path, base_scope, scopes
                    )
                except Exception:
                    continue  # Skip invalid scope combinations

    async def _scan_optional_scope_components(self, base_path: str, base_scope: ScopeContext,
                                            scopes: List[ScopeContext]):
        """Scan for optional scope components (project, thread, topic)."""
        for item in os.listdir(base_path):
            item_path = os.path.join(base_path, item)
            if not os.path.isdir(item_path):
                continue

            # Check for project directories
            if item.startswith("proj_"):
                project = item[5:]  # Remove "proj_" prefix
                try:
                    project_scope = ScopeContext(f"{base_scope}.proj_{project}")
                    scopes.append(project_scope)

                    # Look for thread directories under project
                    await self._scan_thread_components(item_path, project_scope, scopes)
                except Exception:
                    continue

    async def _scan_thread_components(self, project_path: str, project_scope: ScopeContext,
                                    scopes: List[ScopeContext]):
        """Scan for thread and topic components."""
        for item in os.listdir(project_path):
            item_path = os.path.join(project_path, item)
            if not os.path.isdir(item_path):
                continue

            # Check for thread directories
            if item.startswith("thr_"):
                thread = item[4:]  # Remove "thr_" prefix
                try:
                    thread_scope = ScopeContext(f"{project_scope}.thr_{thread}")
                    scopes.append(thread_scope)

                    # Look for topic directories under thread
                    await self._scan_topic_components(item_path, thread_scope, scopes)
                except Exception:
                    continue

    async def _scan_topic_components(self, thread_path: str, thread_scope: ScopeContext,
                                   scopes: List[ScopeContext]):
        """Scan for topic components."""
        for item in os.listdir(thread_path):
            item_path = os.path.join(thread_path, item)
            if not os.path.isdir(item_path):
                continue

            # Check for topic directories
            if item.startswith("top_"):
                topic = item[4:]  # Remove "top_" prefix
                try:
                    topic_scope = ScopeContext(f"{thread_scope}.top_{topic}")
                    scopes.append(topic_scope)
                except Exception:
                    continue

    async def migrate_workspace_data(self, workspace: str, target_scope: ScopeContext) -> bool:
        """Migrate data from workspace-based storage to scope-based storage."""
        try:
            # Find workspace-based storage file
            workspace_dir = os.path.join(self._base_working_dir, workspace)
            workspace_file = os.path.join(workspace_dir, f"kv_store_{self.namespace}.json")

            if not os.path.exists(workspace_file):
                logger.warning(f"No workspace data found at {workspace_file}")
                return True  # Nothing to migrate

            # Load workspace data
            workspace_data = load_json(workspace_file) or {}
            if not workspace_data:
                logger.info(f"No data to migrate from workspace {workspace}")
                return True

            # Set target scope and initialize
            original_scope = self._scope_context
            self.set_scope_context(target_scope)

            try:
                await self.initialize()

                # Add scope metadata to all items and upsert
                scoped_data = {}
                for key, value in workspace_data.items():
                    if isinstance(value, dict):
                        scoped_value = self.add_scope_metadata(value)
                        scoped_data[key] = scoped_value
                    else:
                        scoped_data[key] = value

                await self.upsert(scoped_data)
                await self.index_done_callback()

                logger.info(f"Migrated {len(workspace_data)} items from workspace {workspace} to scope {target_scope}")
                return True

            finally:
                self.set_scope_context(original_scope)

        except Exception as e:
            logger.error(f"Failed to migrate workspace {workspace} to scope {target_scope}: {str(e)}")
            return False