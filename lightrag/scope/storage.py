"""
Base storage interfaces with scope support.

This module provides extended storage interfaces that support scope-based
data partitioning through the SRN system.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field

from .context import ScopeContext
from .srn import SRNComponents


class ScopeAwareStorageMixin(ABC):
    """
    Mixin class for adding scope awareness to storage implementations.

    This mixin provides common scope-related functionality that can be
    added to any storage implementation.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._scope_context: Optional[ScopeContext] = None

    def set_scope_context(self, scope: Union[str, ScopeContext, None]) -> None:
        """
        Set the current scope context for this storage instance.

        Args:
            scope: Scope context as string, ScopeContext object, or None to clear
        """
        if scope is None:
            self._scope_context = None
        elif isinstance(scope, str):
            self._scope_context = ScopeContext(scope)
        elif isinstance(scope, ScopeContext):
            self._scope_context = scope
        else:
            raise ValueError("Scope must be a string, ScopeContext object, or None")

    def get_scope_context(self) -> Optional[ScopeContext]:
        """Get the current scope context."""
        return self._scope_context

    def get_scope_filter(self) -> Dict[str, Any]:
        """
        Generate a filter dictionary based on the current scope context.

        Returns:
            Dictionary with scope-based filters, empty if no scope set
        """
        if self._scope_context is None:
            return {}
        return self._scope_context.to_filter_dict()

    def get_scoped_key(self, key: str) -> str:
        """
        Generate a scope-aware key for data storage.

        Args:
            key: Base key

        Returns:
            Scoped key that includes scope information
        """
        if self._scope_context is None:
            return key

        scope_prefix = f"{self._scope_context.workspace}:{self._scope_context.subject_type.value}:{self._scope_context.subject_id}"

        if self._scope_context.project:
            scope_prefix += f":proj_{self._scope_context.project}"
        if self._scope_context.thread:
            scope_prefix += f":thr_{self._scope_context.thread}"
        if self._scope_context.topic:
            scope_prefix += f":top_{self._scope_context.topic}"

        return f"{scope_prefix}:{key}"

    def get_scope_directory_path(self, base_path: str) -> str:
        """
        Generate a scope-aware directory path for file-based storage.

        Args:
            base_path: Base directory path

        Returns:
            Scope-aware directory path
        """
        if self._scope_context is None:
            return base_path

        import os
        path_parts = [
            base_path,
            self._scope_context.workspace,
            self._scope_context.subject_type.value,
            self._scope_context.subject_id
        ]

        if self._scope_context.project:
            path_parts.append(f"proj_{self._scope_context.project}")
        if self._scope_context.thread:
            path_parts.append(f"thr_{self._scope_context.thread}")
        if self._scope_context.topic:
            path_parts.append(f"top_{self._scope_context.topic}")

        return os.path.join(*path_parts)

    def add_scope_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add scope metadata to data object.

        Args:
            data: Original data dictionary

        Returns:
            Data dictionary with scope metadata added
        """
        if self._scope_context is None:
            return data

        # Create a copy to avoid modifying the original
        scoped_data = data.copy()

        # Add scope fields
        scope_metadata = self._scope_context.to_filter_dict()
        scoped_data.update(scope_metadata)

        return scoped_data

    def extract_data_without_scope(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract original data by removing scope metadata.

        Args:
            data: Data dictionary with scope metadata

        Returns:
            Data dictionary without scope metadata
        """
        if data is None:
            return None

        # Create a copy to avoid modifying the original
        clean_data = data.copy()

        # Remove scope fields
        scope_fields = ["workspace", "subject_type", "subject_id", "project", "thread", "topic"]
        for field in scope_fields:
            clean_data.pop(field, None)

        return clean_data

    def filter_by_scope(self, data_list: List[Dict[str, Any]],
                       scope: Optional[ScopeContext] = None) -> List[Dict[str, Any]]:
        """
        Filter a list of data items by scope.

        Args:
            data_list: List of data items to filter
            scope: Scope to filter by (uses current scope if None)

        Returns:
            Filtered list of data items
        """
        if not data_list:
            return []

        target_scope = scope or self._scope_context
        if target_scope is None:
            return data_list

        scope_filter = target_scope.to_filter_dict()
        filtered_data = []

        for item in data_list:
            # Check if item matches all scope criteria
            matches = True
            for key, value in scope_filter.items():
                if key not in item or item[key] != value:
                    matches = False
                    break

            if matches:
                filtered_data.append(item)

        return filtered_data

    @abstractmethod
    async def migrate_workspace_data(self, workspace: str, target_scope: ScopeContext) -> bool:
        """
        Migrate data from workspace-based storage to scope-based storage.

        Args:
            workspace: Source workspace identifier
            target_scope: Target scope context

        Returns:
            True if migration was successful

        Raises:
            NotImplementedError: If migration is not supported
        """
        raise NotImplementedError("Migration must be implemented by storage class")

    @abstractmethod
    async def list_scopes(self, pattern: Optional[str] = None) -> List[ScopeContext]:
        """
        List available scopes in this storage.

        Args:
            pattern: Optional pattern to filter scopes (supports wildcards)

        Returns:
            List of available scope contexts
        """
        raise NotImplementedError("Scope listing must be implemented by storage class")


@dataclass
class ScopeAwareKVStorage(ScopeAwareStorageMixin):
    """Base class for scope-aware key-value storage implementations."""

    @abstractmethod
    async def scope_aware_get(self, key: str, scope: Optional[ScopeContext] = None) -> Any:
        """
        Get value with scope awareness.

        Args:
            key: Key to retrieve
            scope: Scope context (uses current scope if None)

        Returns:
            Value from storage, or None if not found
        """
        pass

    @abstractmethod
    async def scope_aware_set(self, key: str, value: Any, scope: Optional[ScopeContext] = None) -> None:
        """
        Set value with scope awareness.

        Args:
            key: Key to store
            value: Value to store
            scope: Scope context (uses current scope if None)
        """
        pass

    @abstractmethod
    async def scope_aware_delete(self, key: str, scope: Optional[ScopeContext] = None) -> bool:
        """
        Delete value with scope awareness.

        Args:
            key: Key to delete
            scope: Scope context (uses current scope if None)

        Returns:
            True if key was deleted, False if not found
        """
        pass

    @abstractmethod
    async def scope_aware_list_keys(self, scope: Optional[ScopeContext] = None,
                                   pattern: Optional[str] = None) -> List[str]:
        """
        List keys within a scope.

        Args:
            scope: Scope context (uses current scope if None)
            pattern: Optional pattern to filter keys

        Returns:
            List of keys within the scope
        """
        pass


@dataclass
class ScopeAwareVectorStorage(ScopeAwareStorageMixin):
    """Base class for scope-aware vector storage implementations."""

    @abstractmethod
    async def scope_aware_query(self, query: str, top_k: int,
                               scope: Optional[ScopeContext] = None,
                               query_embedding: Optional[List[float]] = None) -> List[Dict[str, Any]]:
        """
        Query vectors with scope awareness.

        Args:
            query: Query string
            top_k: Number of results to return
            scope: Scope context (uses current scope if None)
            query_embedding: Optional pre-computed embedding

        Returns:
            List of matching vectors with scores
        """
        pass

    @abstractmethod
    async def scope_aware_upsert(self, data: Dict[str, Dict[str, Any]],
                                scope: Optional[ScopeContext] = None) -> None:
        """
        Upsert vectors with scope awareness.

        Args:
            data: Vector data to upsert
            scope: Scope context (uses current scope if None)
        """
        pass

    @abstractmethod
    async def scope_aware_delete(self, entity_id: str,
                                scope: Optional[ScopeContext] = None) -> bool:
        """
        Delete vector with scope awareness.

        Args:
            entity_id: Entity ID to delete
            scope: Scope context (uses current scope if None)

        Returns:
            True if entity was deleted, False if not found
        """
        pass


@dataclass
class ScopeAwareGraphStorage(ScopeAwareStorageMixin):
    """Base class for scope-aware graph storage implementations."""

    @abstractmethod
    async def scope_aware_upsert_node(self, node_data: Dict[str, Any],
                                     scope: Optional[ScopeContext] = None) -> None:
        """
        Upsert graph node with scope awareness.

        Args:
            node_data: Node data to upsert
            scope: Scope context (uses current scope if None)
        """
        pass

    @abstractmethod
    async def scope_aware_upsert_edge(self, edge_data: Dict[str, Any],
                                     scope: Optional[ScopeContext] = None) -> None:
        """
        Upsert graph edge with scope awareness.

        Args:
            edge_data: Edge data to upsert
            scope: Scope context (uses current scope if None)
        """
        pass

    @abstractmethod
    async def scope_aware_get_node(self, node_id: str,
                                  scope: Optional[ScopeContext] = None) -> Optional[Dict[str, Any]]:
        """
        Get graph node with scope awareness.

        Args:
            node_id: Node ID to retrieve
            scope: Scope context (uses current scope if None)

        Returns:
            Node data or None if not found
        """
        pass

    @abstractmethod
    async def scope_aware_get_edges(self, source_id: str, target_id: str = None,
                                   scope: Optional[ScopeContext] = None) -> List[Dict[str, Any]]:
        """
        Get graph edges with scope awareness.

        Args:
            source_id: Source node ID
            target_id: Optional target node ID
            scope: Scope context (uses current scope if None)

        Returns:
            List of matching edges
        """
        pass

    @abstractmethod
    async def scope_aware_delete_node(self, node_id: str,
                                     scope: Optional[ScopeContext] = None) -> bool:
        """
        Delete graph node with scope awareness.

        Args:
            node_id: Node ID to delete
            scope: Scope context (uses current scope if None)

        Returns:
            True if node was deleted, False if not found
        """
        pass

    @abstractmethod
    async def scope_aware_delete_edge(self, source_id: str, target_id: str,
                                     scope: Optional[ScopeContext] = None) -> bool:
        """
        Delete graph edge with scope awareness.

        Args:
            source_id: Source node ID
            target_id: Target node ID
            scope: Scope context (uses current scope if None)

        Returns:
            True if edge was deleted, False if not found
        """
        pass


class ScopeMigrationInterface(ABC):
    """Interface for storage migration operations."""

    @abstractmethod
    async def validate_migration(self, workspace: str, target_scope: ScopeContext) -> List[str]:
        """
        Validate that migration from workspace to scope is possible.

        Args:
            workspace: Source workspace
            target_scope: Target scope

        Returns:
            List of validation errors (empty if valid)
        """
        pass

    @abstractmethod
    async def estimate_migration_size(self, workspace: str) -> Dict[str, Any]:
        """
        Estimate the size and complexity of migration.

        Args:
            workspace: Source workspace

        Returns:
            Dictionary with migration estimates (items count, data size, etc.)
        """
        pass

    @abstractmethod
    async def migrate_workspace_to_scope(self, workspace: str, target_scope: ScopeContext,
                                        dry_run: bool = True) -> Dict[str, Any]:
        """
        Migrate workspace data to scope format.

        Args:
            workspace: Source workspace
            target_scope: Target scope
            dry_run: If True, only simulate the migration

        Returns:
            Migration result with status and details
        """
        pass

    @abstractmethod
    async def rollback_migration(self, migration_id: str) -> Dict[str, Any]:
        """
        Rollback a migration operation.

        Args:
            migration_id: Migration identifier

        Returns:
            Rollback result with status and details
        """
        pass