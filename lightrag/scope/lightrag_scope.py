"""
Scope-aware LightRAG implementation.

This module provides a scope-aware version of the main LightRAG class
that integrates the SRN system for hierarchical data partitioning.
"""

from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field

from lightrag.lightrag import LightRAG
from lightrag.base import QueryParam
from lightrag.utils import logger

from .context import ScopeContext, ScopeResolver
from .srn import SRNParser, SRNComponents
from .exceptions import SRNError, ScopeResolutionError


@dataclass
class ScopeAwareLightRAG:
    """
    Scope-aware version of LightRAG with SRN support.

    This class extends LightRAG functionality with scope-based data partitioning,
    allowing fine-grained organization by workspace, user, project, thread, and topic.
    """

    # Core LightRAG instance
    _lightrag: LightRAG = field(init=False)

    # Scope management
    _current_scope: Optional[ScopeContext] = field(default=None, init=False)
    _scope_resolver: ScopeResolver = field(default_factory=ScopeResolver, init=False)
    _srn_parser: SRNParser = field(default_factory=SRNParser, init=False)

    # Configuration
    enable_scope_inheritance: bool = field(default=True)
    default_workspace: Optional[str] = field(default=None)
    scope_validation_strict: bool = field(default=True)

    def __init__(self, **lightrag_kwargs):
        """
        Initialize scope-aware LightRAG.

        Args:
            **lightrag_kwargs: Arguments passed to the underlying LightRAG instance
        """
        # Extract scope-specific configuration
        self.enable_scope_inheritance = lightrag_kwargs.pop("enable_scope_inheritance", True)
        self.default_workspace = lightrag_kwargs.pop("default_workspace", None)
        self.scope_validation_strict = lightrag_kwargs.pop("scope_validation_strict", True)

        # Initialize core LightRAG
        self._lightrag = LightRAG(**lightrag_kwargs)

        # Initialize scope management
        self._current_scope = None
        self._scope_resolver = ScopeResolver()
        self._srn_parser = SRNParser()

        logger.info("Initialized scope-aware LightRAG with SRN support")

    async def initialize_storages(self):
        """Initialize underlying LightRAG storages."""
        await self._lightrag.initialize_storages()

    async def finalize_storages(self):
        """Finalize underlying LightRAG storages."""
        await self._lightrag.finalize_storages()

    # Scope Management Methods
    def set_scope(self, scope: Union[str, ScopeContext, None]) -> None:
        """
        Set the current scope context.

        Args:
            scope: Scope as SRN string, ScopeContext object, or None to clear

        Raises:
            SRNError: If scope format is invalid and strict validation is enabled
        """
        try:
            if scope is None:
                self._current_scope = None
                logger.debug("Cleared current scope")
            elif isinstance(scope, str):
                components = self._srn_parser.parse(scope)
                self._current_scope = ScopeContext(components)
                logger.debug(f"Set scope to: {self._current_scope}")
            elif isinstance(scope, ScopeContext):
                self._current_scope = scope
                logger.debug(f"Set scope to: {self._current_scope}")
            else:
                raise ValueError("Scope must be a string, ScopeContext object, or None")

            # Apply scope to storage instances if they support it
            self._apply_scope_to_storages()

        except SRNError as e:
            if self.scope_validation_strict:
                raise
            else:
                logger.warning(f"Invalid scope format, ignoring: {str(e)}")
                self._current_scope = None

    def get_scope(self) -> Optional[ScopeContext]:
        """Get the current scope context."""
        return self._current_scope

    def _apply_scope_to_storages(self):
        """Apply current scope to storage instances that support it."""
        scope_aware_storages = []

        # Check each storage type for scope awareness
        for storage_attr in ["vector_storage", "kv_storage", "graph_storage", "doc_status_storage"]:
            storage = getattr(self._lightrag, storage_attr, None)
            if storage and hasattr(storage, "set_scope_context"):
                storage.set_scope_context(self._current_scope)
                scope_aware_storages.append(storage_attr)

        if scope_aware_storages:
            logger.debug(f"Applied scope to storages: {scope_aware_storages}")

    # Enhanced Query Methods
    async def aquery(
        self,
        query: str,
        param: QueryParam = None,
        scope: Optional[Union[str, ScopeContext]] = None,
        include_scope_hierarchy: bool = None
    ) -> str:
        """
        Execute an async query with optional scope context.

        Args:
            query: Query text
            param: Query parameters
            scope: Scope context for this query (overrides current scope)
            include_scope_hierarchy: Whether to include parent scopes in query

        Returns:
            Query response
        """
        # Handle scope for this query
        original_scope = self._current_scope
        query_scope = scope

        if query_scope is not None:
            if isinstance(query_scope, str):
                query_scope = ScopeContext(query_scope)
            self.set_scope(query_scope)

        try:
            # Handle scope hierarchy if requested
            if include_scope_hierarchy is None:
                include_scope_hierarchy = self.enable_scope_inheritance

            if include_scope_hierarchy and self._current_scope:
                return await self._query_with_hierarchy(query, param)
            else:
                return await self._lightrag.aquery(query, param)

        finally:
            # Restore original scope
            if scope is not None:
                self.set_scope(original_scope)

    async def _query_with_hierarchy(self, query: str, param: QueryParam = None) -> str:
        """Execute query with scope hierarchy support."""
        if not self._current_scope:
            return await self._lightrag.aquery(query, param)

        # Get inheritance chain
        inheritance_chain = self._scope_resolver.resolve_inheritance(self._current_scope)

        # For now, just query the most specific scope
        # In a full implementation, this would aggregate results from the hierarchy
        return await self._lightrag.aquery(query, param)

    def query(
        self,
        query: str,
        param: QueryParam = None,
        scope: Optional[Union[str, ScopeContext]] = None,
        include_scope_hierarchy: bool = None
    ) -> str:
        """
        Execute a synchronous query with optional scope context.

        Args:
            query: Query text
            param: Query parameters
            scope: Scope context for this query (overrides current scope)
            include_scope_hierarchy: Whether to include parent scopes in query

        Returns:
            Query response
        """
        import asyncio
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            self.aquery(query, param, scope, include_scope_hierarchy)
        )

    # Enhanced Document Methods
    async def ainsert(
        self,
        string_or_strings: Union[str, List[str]],
        scope: Optional[Union[str, ScopeContext]] = None,
        **kwargs
    ) -> None:
        """
        Insert documents with optional scope context.

        Args:
            string_or_strings: Document(s) to insert
            scope: Scope context for these documents
            **kwargs: Additional arguments passed to LightRAG.ainsert
        """
        # Handle scope for this insertion
        original_scope = self._current_scope

        if scope is not None:
            if isinstance(scope, str):
                scope = ScopeContext(scope)
            self.set_scope(scope)

        try:
            await self._lightrag.ainsert(string_or_strings, **kwargs)
        finally:
            # Restore original scope
            if scope is not None:
                self.set_scope(original_scope)

    def insert(
        self,
        string_or_strings: Union[str, List[str]],
        scope: Optional[Union[str, ScopeContext]] = None,
        **kwargs
    ) -> None:
        """
        Insert documents synchronously with optional scope context.

        Args:
            string_or_strings: Document(s) to insert
            scope: Scope context for these documents
            **kwargs: Additional arguments passed to LightRAG.insert
        """
        import asyncio
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.ainsert(string_or_strings, scope, **kwargs))

    # Scope-specific Methods
    async def list_scopes(self, pattern: Optional[str] = None) -> List[ScopeContext]:
        """
        List available scopes across all storage backends.

        Args:
            pattern: Optional pattern to filter scopes

        Returns:
            List of available scope contexts
        """
        all_scopes = []

        # Collect scopes from scope-aware storages
        for storage_attr in ["vector_storage", "kv_storage", "graph_storage", "doc_status_storage"]:
            storage = getattr(self._lightrag, storage_attr, None)
            if storage and hasattr(storage, "list_scopes"):
                try:
                    storage_scopes = await storage.list_scopes(pattern)
                    all_scopes.extend(storage_scopes)
                except Exception as e:
                    logger.warning(f"Failed to list scopes from {storage_attr}: {str(e)}")

        # Remove duplicates
        unique_scopes = []
        seen_srns = set()

        for scope in all_scopes:
            srn_string = str(scope)
            if srn_string not in seen_srns:
                unique_scopes.append(scope)
                seen_srns.add(srn_string)

        return unique_scopes

    async def migrate_workspace_to_scope(
        self,
        workspace: str,
        target_scope: Union[str, ScopeContext],
        validate_first: bool = True
    ) -> Dict[str, Any]:
        """
        Migrate workspace data to scope format.

        Args:
            workspace: Source workspace identifier
            target_scope: Target scope context
            validate_first: Whether to validate migration before executing

        Returns:
            Migration result with status and details
        """
        if isinstance(target_scope, str):
            target_scope = ScopeContext(target_scope)

        migration_results = {
            "workspace": workspace,
            "target_scope": str(target_scope),
            "storage_results": {},
            "success": True,
            "errors": []
        }

        # Validate migration if requested
        if validate_first:
            validation_errors = await self._validate_workspace_migration(workspace, target_scope)
            if validation_errors:
                migration_results["success"] = False
                migration_results["errors"] = validation_errors
                return migration_results

        # Migrate each storage backend
        for storage_attr in ["vector_storage", "kv_storage", "graph_storage", "doc_status_storage"]:
            storage = getattr(self._lightrag, storage_attr, None)
            if storage and hasattr(storage, "migrate_workspace_data"):
                try:
                    result = await storage.migrate_workspace_data(workspace, target_scope)
                    migration_results["storage_results"][storage_attr] = {
                        "success": result,
                        "error": None
                    }
                    if not result:
                        migration_results["success"] = False
                except Exception as e:
                    error_msg = f"Migration failed for {storage_attr}: {str(e)}"
                    migration_results["storage_results"][storage_attr] = {
                        "success": False,
                        "error": error_msg
                    }
                    migration_results["errors"].append(error_msg)
                    migration_results["success"] = False

        return migration_results

    async def _validate_workspace_migration(
        self,
        workspace: str,
        target_scope: ScopeContext
    ) -> List[str]:
        """Validate that workspace migration is possible."""
        errors = []

        # Check if workspace exists
        workspace_exists = False
        for storage_attr in ["vector_storage", "kv_storage", "graph_storage", "doc_status_storage"]:
            storage = getattr(self._lightrag, storage_attr, None)
            if storage:
                # Check for workspace-based data
                # This is a simplified check - in practice you'd examine storage structure
                workspace_exists = True
                break

        if not workspace_exists:
            errors.append(f"Workspace '{workspace}' not found or has no data")

        # Validate target scope
        try:
            target_scope.to_dict()  # This validates the scope structure
        except Exception as e:
            errors.append(f"Invalid target scope: {str(e)}")

        return errors

    # Utility Methods
    def create_scope_from_workspace(
        self,
        workspace: str,
        subject_type: str = "system",
        subject_id: str = "default"
    ) -> ScopeContext:
        """
        Create a scope context from a workspace identifier.

        Args:
            workspace: Workspace identifier
            subject_type: Subject type for the scope
            subject_id: Subject identifier

        Returns:
            Scope context equivalent to the workspace
        """
        return self._scope_resolver.create_scope_from_workspace(
            workspace, subject_type, subject_id
        )

    def validate_scope(self, scope: str) -> bool:
        """
        Validate an SRN string.

        Args:
            scope: SRN string to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            self._srn_parser.validate(scope)
            return True
        except SRNError:
            return False

    def get_scope_hierarchy(self, scope: Optional[Union[str, ScopeContext]] = None) -> List[ScopeContext]:
        """
        Get the scope hierarchy for a given scope.

        Args:
            scope: Scope to get hierarchy for (uses current scope if None)

        Returns:
            List of scope contexts from most specific to least specific
        """
        target_scope = scope
        if target_scope is None:
            target_scope = self._current_scope

        if target_scope is None:
            return []

        if isinstance(target_scope, str):
            target_scope = ScopeContext(target_scope)

        return self._scope_resolver.resolve_inheritance(target_scope)

    # Property accessors for underlying LightRAG
    @property
    def working_dir(self) -> str:
        """Get the working directory."""
        return self._lightrag.working_dir

    @property
    def vector_storage(self):
        """Get the vector storage instance."""
        return self._lightrag.vector_storage

    @property
    def kv_storage(self):
        """Get the KV storage instance."""
        return self._lightrag.kv_storage

    @property
    def graph_storage(self):
        """Get the graph storage instance."""
        return self._lightrag.graph_storage

    @property
    def doc_status_storage(self):
        """Get the document status storage instance."""
        return self._lightrag.doc_status_storage

    # Delegate other methods to underlying LightRAG
    def __getattr__(self, name):
        """Delegate unknown attributes to the underlying LightRAG instance."""
        return getattr(self._lightrag, name)