"""
Scope-aware graph storage implementations.

This module provides graph storage implementations with full scope support,
extending the base graph storage classes with SRN-based partitioning.
"""

import asyncio
import json
import networkx as nx
from typing import Any, Dict, List, Optional, Union, final
from dataclasses import dataclass

from lightrag.base import BaseGraphStorage
from lightrag.utils import logger, write_json, load_json
from lightrag.exceptions import StorageNotInitializedError

from .context import ScopeContext, ScopeResolver
from .storage import ScopeAwareStorageMixin
from .exceptions import ScopeResolutionError


@final
@dataclass
class ScopeAwareNetworkXStorage(BaseGraphStorage, ScopeAwareStorageMixin):
    """NetworkX-based graph storage with scope awareness."""

    def __post_init__(self):
        BaseGraphStorage.__post_init__(self)
        ScopeAwareStorageMixin.__init__(self)

        working_dir = self.global_config["working_dir"]
        self._base_working_dir = working_dir
        self._graph = nx.DiGraph()
        self._storage_lock = None

    def _get_graph_file_path(self, scope: Optional[ScopeContext] = None) -> str:
        """Get the file path for the graph storage based on scope."""
        target_scope = scope or self._scope_context

        if target_scope is None:
            # Fall back to workspace-based storage
            if self.workspace and self.workspace != "_":
                import os
                workspace_dir = os.path.join(self._base_working_dir, self.workspace)
                os.makedirs(workspace_dir, exist_ok=True)
                return os.path.join(workspace_dir, f"graph_{self.namespace}.json")
            else:
                import os
                return os.path.join(self._base_working_dir, f"graph_{self.namespace}.json")

        # Use scope-aware file structure
        import os
        scope_dir = self.get_scope_directory_path(self._base_working_dir)
        os.makedirs(scope_dir, exist_ok=True)
        return os.path.join(scope_dir, f"graph_{self.namespace}.json")

    async def initialize(self):
        """Initialize NetworkX graph with scope awareness."""
        from lightrag.kg.shared_storage import get_storage_lock

        self._storage_lock = get_storage_lock()

        # Load existing graph data
        graph_file = self._get_graph_file_path()
        graph_data = load_json(graph_file) or {"nodes": {}, "edges": {}}

        # Filter data by scope if scope is set
        if self._scope_context is not None:
            graph_data = self._filter_graph_data_by_scope(graph_data)

        # Build NetworkX graph
        self._graph.clear()

        # Add nodes with scope metadata
        for node_id, node_data in graph_data.get("nodes", {}).items():
            clean_data = self.extract_data_without_scope(node_data) if isinstance(node_data, dict) else node_data
            self._graph.add_node(node_id, **clean_data)

        # Add edges with scope metadata
        for edge_key, edge_data in graph_data.get("edges", {}).items():
            if isinstance(edge_data, dict) and "source" in edge_data and "target" in edge_data:
                source = edge_data["source"]
                target = edge_data["target"]
                clean_data = self.extract_data_without_scope(edge_data)
                # Remove source/target from edge attributes
                clean_data.pop("source", None)
                clean_data.pop("target", None)
                self._graph.add_edge(source, target, **clean_data)

        scope_info = f"scope={self._scope_context}" if self._scope_context else f"workspace={self.workspace}"
        logger.info(f"[{scope_info}] Initialized NetworkX graph with {len(self._graph.nodes)} nodes, {len(self._graph.edges)} edges")

    def _filter_graph_data_by_scope(self, graph_data: Dict[str, Any]) -> Dict[str, Any]:
        """Filter graph data to only include items matching current scope."""
        if self._scope_context is None:
            return graph_data

        scope_filter = self._scope_context.to_filter_dict()
        filtered_data = {"nodes": {}, "edges": {}}

        # Filter nodes
        for node_id, node_data in graph_data.get("nodes", {}).items():
            if isinstance(node_data, dict):
                matches = True
                for scope_key, scope_value in scope_filter.items():
                    if scope_key not in node_data or node_data[scope_key] != scope_value:
                        matches = False
                        break

                if matches:
                    filtered_data["nodes"][node_id] = node_data

        # Filter edges
        for edge_key, edge_data in graph_data.get("edges", {}).items():
            if isinstance(edge_data, dict):
                matches = True
                for scope_key, scope_value in scope_filter.items():
                    if scope_key not in edge_data or edge_data[scope_key] != scope_value:
                        matches = False
                        break

                if matches:
                    # Only include edge if both source and target nodes are in scope
                    source = edge_data.get("source")
                    target = edge_data.get("target")
                    if source in filtered_data["nodes"] and target in filtered_data["nodes"]:
                        filtered_data["edges"][edge_key] = edge_data

        return filtered_data

    async def finalize(self):
        """Finalize graph storage operations."""
        await self.index_done_callback()

    async def upsert_node(self, node_data: Dict[str, Any]) -> None:
        """Upsert a graph node with scope awareness."""
        if "id" not in node_data:
            raise ValueError("Node data must contain 'id' field")

        node_id = node_data["id"]
        node_attrs = {k: v for k, v in node_data.items() if k != "id"}

        # Add scope metadata
        if self._scope_context is not None:
            node_attrs = self.add_scope_metadata(node_attrs)

        async with self._storage_lock:
            self._graph.add_node(node_id, **node_attrs)

    async def upsert_edge(self, edge_data: Dict[str, Any]) -> None:
        """Upsert a graph edge with scope awareness."""
        if "source" not in edge_data or "target" not in edge_data:
            raise ValueError("Edge data must contain 'source' and 'target' fields")

        source = edge_data["source"]
        target = edge_data["target"]
        edge_attrs = {k: v for k, v in edge_data.items() if k not in ["source", "target"]}

        # Add scope metadata
        if self._scope_context is not None:
            edge_attrs = self.add_scope_metadata(edge_attrs)

        async with self._storage_lock:
            self._graph.add_edge(source, target, **edge_attrs)

    async def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get a graph node with scope awareness."""
        if node_id not in self._graph.nodes:
            return None

        node_data = dict(self._graph.nodes[node_id])
        node_data["id"] = node_id

        # Check scope if scope context is set
        if self._scope_context is not None:
            scope_filter = self._scope_context.to_filter_dict()
            for scope_key, scope_value in scope_filter.items():
                if scope_key not in node_data or node_data[scope_key] != scope_value:
                    return None

        # Remove scope metadata from returned data
        return self.extract_data_without_scope(node_data)

    async def get_edges(self, source_id: str, target_id: str = None) -> List[Dict[str, Any]]:
        """Get graph edges with scope awareness."""
        edges = []

        if target_id:
            # Get specific edge
            if self._graph.has_edge(source_id, target_id):
                edge_data = dict(self._graph.edges[source_id, target_id])
                edge_data["source"] = source_id
                edge_data["target"] = target_id

                # Check scope if scope context is set
                if self._scope_context is not None:
                    scope_filter = self._scope_context.to_filter_dict()
                    matches = True
                    for scope_key, scope_value in scope_filter.items():
                        if scope_key not in edge_data or edge_data[scope_key] != scope_value:
                            matches = False
                            break

                    if matches:
                        edges.append(self.extract_data_without_scope(edge_data))
        else:
            # Get all edges from source
            for target in self._graph.successors(source_id):
                edge_data = dict(self._graph.edges[source_id, target])
                edge_data["source"] = source_id
                edge_data["target"] = target

                # Check scope if scope context is set
                if self._scope_context is not None:
                    scope_filter = self._scope_context.to_filter_dict()
                    matches = True
                    for scope_key, scope_value in scope_filter.items():
                        if scope_key not in edge_data or edge_data[scope_key] != scope_value:
                            matches = False
                            break

                    if not matches:
                        continue

                edges.append(self.extract_data_without_scope(edge_data))

        return edges

    async def delete_node(self, node_id: str) -> bool:
        """Delete a graph node with scope awareness."""
        if node_id not in self._graph.nodes:
            return False

        # Check scope if scope context is set
        node_data = dict(self._graph.nodes[node_id])
        if self._scope_context is not None:
            scope_filter = self._scope_context.to_filter_dict()
            for scope_key, scope_value in scope_filter.items():
                if scope_key not in node_data or node_data[scope_key] != scope_value:
                    return False

        async with self._storage_lock:
            self._graph.remove_node(node_id)

        return True

    async def delete_edge(self, source_id: str, target_id: str) -> bool:
        """Delete a graph edge with scope awareness."""
        if not self._graph.has_edge(source_id, target_id):
            return False

        # Check scope if scope context is set
        edge_data = dict(self._graph.edges[source_id, target_id])
        if self._scope_context is not None:
            scope_filter = self._scope_context.to_filter_dict()
            for scope_key, scope_value in scope_filter.items():
                if scope_key not in edge_data or edge_data[scope_key] != scope_value:
                    return False

        async with self._storage_lock:
            self._graph.remove_edge(source_id, target_id)

        return True

    async def index_done_callback(self) -> None:
        """Commit graph storage operations."""
        async with self._storage_lock:
            # Prepare graph data for serialization
            graph_data = {"nodes": {}, "edges": {}}

            # Serialize nodes with scope metadata
            for node_id, node_attrs in self._graph.nodes(data=True):
                node_data = dict(node_attrs)
                node_data["id"] = node_id

                # Add scope metadata if in scope mode
                if self._scope_context is not None:
                    node_data = self.add_scope_metadata(node_data)

                graph_data["nodes"][node_id] = node_data

            # Serialize edges with scope metadata
            for source, target, edge_attrs in self._graph.edges(data=True):
                edge_key = f"{source}_{target}"
                edge_data = dict(edge_attrs)
                edge_data["source"] = source
                edge_data["target"] = target

                # Add scope metadata if in scope mode
                if self._scope_context is not None:
                    edge_data = self.add_scope_metadata(edge_data)

                graph_data["edges"][edge_key] = edge_data

            # Save to file
            graph_file = self._get_graph_file_path()
            write_json(graph_data, graph_file)

            scope_info = f"scope={self._scope_context}" if self._scope_context else f"workspace={self.workspace}"
            logger.info(f"[{scope_info}] Saved NetworkX graph with {len(graph_data['nodes'])} nodes, {len(graph_data['edges'])} edges")

    async def drop(self) -> Dict[str, str]:
        """Drop all graph data from scope-aware storage."""
        try:
            async with self._storage_lock:
                self._graph.clear()

            graph_file = self._get_graph_file_path()
            import os
            if os.path.exists(graph_file):
                os.remove(graph_file)

                # Also remove parent directories if they're empty
                parent_dir = os.path.dirname(graph_file)
                try:
                    os.rmdir(parent_dir)
                except OSError:
                    pass  # Directory not empty or doesn't exist

            scope_info = f"scope={self._scope_context}" if self._scope_context else f"workspace={self.workspace}"
            logger.info(f"[{scope_info}] Dropped NetworkX graph storage")

            return {"status": "success", "message": "data dropped"}

        except Exception as e:
            error_msg = f"Failed to drop graph storage: {str(e)}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}

    # ScopeAwareStorageMixin implementation
    async def scope_aware_upsert_node(self, node_data: Dict[str, Any],
                                     scope: Optional[ScopeContext] = None) -> None:
        """Upsert graph node with explicit scope."""
        if scope is not None:
            original_scope = self._scope_context
            self.set_scope_context(scope)
            try:
                await self.upsert_node(node_data)
            finally:
                self.set_scope_context(original_scope)
        else:
            await self.upsert_node(node_data)

    async def scope_aware_upsert_edge(self, edge_data: Dict[str, Any],
                                     scope: Optional[ScopeContext] = None) -> None:
        """Upsert graph edge with explicit scope."""
        if scope is not None:
            original_scope = self._scope_context
            self.set_scope_context(scope)
            try:
                await self.upsert_edge(edge_data)
            finally:
                self.set_scope_context(original_scope)
        else:
            await self.upsert_edge(edge_data)

    async def scope_aware_get_node(self, node_id: str,
                                  scope: Optional[ScopeContext] = None) -> Optional[Dict[str, Any]]:
        """Get graph node with explicit scope."""
        if scope is not None:
            original_scope = self._scope_context
            self.set_scope_context(scope)
            try:
                return await self.get_node(node_id)
            finally:
                self.set_scope_context(original_scope)
        else:
            return await self.get_node(node_id)

    async def scope_aware_get_edges(self, source_id: str, target_id: str = None,
                                   scope: Optional[ScopeContext] = None) -> List[Dict[str, Any]]:
        """Get graph edges with explicit scope."""
        if scope is not None:
            original_scope = self._scope_context
            self.set_scope_context(scope)
            try:
                return await self.get_edges(source_id, target_id)
            finally:
                self.set_scope_context(original_scope)
        else:
            return await self.get_edges(source_id, target_id)

    async def scope_aware_delete_node(self, node_id: str,
                                     scope: Optional[ScopeContext] = None) -> bool:
        """Delete graph node with explicit scope."""
        if scope is not None:
            original_scope = self._scope_context
            self.set_scope_context(scope)
            try:
                return await self.delete_node(node_id)
            finally:
                self.set_scope_context(original_scope)
        else:
            return await self.delete_node(node_id)

    async def scope_aware_delete_edge(self, source_id: str, target_id: str,
                                     scope: Optional[ScopeContext] = None) -> bool:
        """Delete graph edge with explicit scope."""
        if scope is not None:
            original_scope = self._scope_context
            self.set_scope_context(scope)
            try:
                return await self.delete_edge(source_id, target_id)
            finally:
                self.set_scope_context(original_scope)
        else:
            return await self.delete_edge(source_id, target_id)

    async def list_scopes(self, pattern: Optional[str] = None) -> List[ScopeContext]:
        """List available scopes in this graph storage."""
        scopes = []
        graph_file = self._get_graph_file_path()
        graph_data = load_json(graph_file) or {"nodes": {}, "edges": {}}

        # Extract unique scope combinations from nodes and edges
        scope_combinations = set()

        for node_data in graph_data.get("nodes", {}).values():
            if isinstance(node_data, dict):
                scope_tuple = self._extract_scope_tuple(node_data)
                if scope_tuple:
                    scope_combinations.add(scope_tuple)

        for edge_data in graph_data.get("edges", {}).values():
            if isinstance(edge_data, dict):
                scope_tuple = self._extract_scope_tuple(edge_data)
                if scope_tuple:
                    scope_combinations.add(scope_tuple)

        # Convert scope tuples to ScopeContext objects
        for scope_tuple in scope_combinations:
            try:
                workspace, subject_type, subject_id, project, thread, topic = scope_tuple

                srn_parts = ["1", workspace, subject_type, subject_id]
                if project:
                    srn_parts.append(f"proj_{project}")
                if thread:
                    srn_parts.append(f"thr_{thread}")
                if topic:
                    srn_parts.append(f"top_{topic}")

                srn_string = ".".join(srn_parts)
                scope = ScopeContext(srn_string)

                # Apply pattern filtering if specified
                if pattern and pattern not in srn_string:
                    continue

                scopes.append(scope)

            except Exception as e:
                logger.warning(f"Failed to create scope from tuple {scope_tuple}: {str(e)}")

        return scopes

    def _extract_scope_tuple(self, data: Dict[str, Any]) -> Optional[tuple]:
        """Extract scope tuple from data dictionary."""
        required_fields = ["workspace", "subject_type", "subject_id"]
        if not all(field in data for field in required_fields):
            return None

        return (
            data["workspace"],
            data["subject_type"],
            data["subject_id"],
            data.get("project"),
            data.get("thread"),
            data.get("topic")
        )

    async def migrate_workspace_data(self, workspace: str, target_scope: ScopeContext) -> bool:
        """Migrate graph data from workspace-based storage to scope-based storage."""
        try:
            # Load workspace-based graph file
            import os
            workspace_dir = os.path.join(self._base_working_dir, workspace)
            workspace_file = os.path.join(workspace_dir, f"graph_{self.namespace}.json")

            if not os.path.exists(workspace_file):
                logger.warning(f"No workspace graph data found at {workspace_file}")
                return True

            # Load workspace graph data
            workspace_data = load_json(workspace_file) or {"nodes": {}, "edges": {}}
            if not workspace_data.get("nodes") and not workspace_data.get("edges"):
                logger.info(f"No graph data to migrate from workspace {workspace}")
                return True

            # Set target scope and initialize
            original_scope = self._scope_context
            self.set_scope_context(target_scope)

            try:
                await self.initialize()

                # Migrate nodes
                for node_id, node_data in workspace_data.get("nodes", {}).items():
                    if isinstance(node_data, dict):
                        scoped_node_data = self.add_scope_metadata(node_data)
                        scoped_node_data["id"] = node_id
                        await self.upsert_node(scoped_node_data)

                # Migrate edges
                for edge_key, edge_data in workspace_data.get("edges", {}).items():
                    if isinstance(edge_data, dict) and "source" in edge_data and "target" in edge_data:
                        scoped_edge_data = self.add_scope_metadata(edge_data)
                        await self.upsert_edge(scoped_edge_data)

                await self.index_done_callback()

                logger.info(f"Migrated {len(workspace_data.get('nodes', {}))} nodes and {len(workspace_data.get('edges', {}))} edges from workspace {workspace} to scope {target_scope}")
                return True

            finally:
                self.set_scope_context(original_scope)

        except Exception as e:
            logger.error(f"Failed to migrate workspace {workspace} to scope {target_scope}: {str(e)}")
            return False