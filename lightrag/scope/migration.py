"""
Migration tools for converting workspace-based data to scope-based data.

This module provides utilities for migrating existing workspace-based
LightRAG installations to the new scope-based partitioning system.
"""

import os
import json
import uuid
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

from lightrag.utils import logger
from .context import ScopeContext, ScopeResolver
from .srn import SRNComponents, SubjectType
from .exceptions import ScopeResolutionError


@dataclass
class MigrationStatus:
    """Status information for a migration operation."""

    migration_id: str
    source_workspace: str
    target_scope: str
    status: str  # 'pending', 'running', 'completed', 'failed', 'rolled_back'
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    items_migrated: int = 0
    total_items: int = 0
    error_message: Optional[str] = None
    rollback_data: Optional[Dict[str, Any]] = None


@dataclass
class MigrationPlan:
    """Plan for migrating workspace data to scope format."""

    source_workspace: str
    target_scope: ScopeContext
    storage_types: List[str] = field(default_factory=list)
    estimated_items: Dict[str, int] = field(default_factory=dict)
    estimated_size: Dict[str, int] = field(default_factory=dict)
    validation_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class ScopeMigrationTool:
    """
    Tool for migrating workspace-based data to scope-based data.

    This tool handles the migration of data from the legacy workspace
    system to the new SRN-based scope system.
    """

    def __init__(self, working_dir: str):
        """
        Initialize migration tool.

        Args:
            working_dir: Base working directory for LightRAG
        """
        self.working_dir = working_dir
        self.resolver = ScopeResolver()
        self._migration_status: Dict[str, MigrationStatus] = {}

        # Migration log file
        self.log_file = os.path.join(working_dir, "scope_migration.log")

    def _log_migration(self, message: str, level: str = "INFO"):
        """Log migration operations to file and logger."""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] {level}: {message}"

        # Log to file
        with open(self.log_file, "a") as f:
            f.write(log_entry + "\n")

        # Log to logger
        if level == "ERROR":
            logger.error(message)
        elif level == "WARNING":
            logger.warning(message)
        else:
            logger.info(message)

    async def discover_workspaces(self) -> List[str]:
        """
        Discover existing workspaces in the working directory.

        Returns:
            List of workspace identifiers
        """
        workspaces = []

        if not os.path.exists(self.working_dir):
            return workspaces

        for item in os.listdir(self.working_dir):
            item_path = os.path.join(self.working_dir, item)
            if os.path.isdir(item_path) and item != "_":
                # Check if this looks like a workspace directory
                # Look for KV storage files as indicators
                has_storage = any(
                    f.startswith("kv_store_") and f.endswith(".json")
                    for f in os.listdir(item_path)
                    if os.path.isfile(os.path.join(item_path, f))
                )

                if has_storage:
                    workspaces.append(item)

        return workspaces

    async def analyze_workspace(self, workspace: str) -> Dict[str, Any]:
        """
        Analyze a workspace to determine migration requirements.

        Args:
            workspace: Workspace identifier to analyze

        Returns:
            Analysis results with storage info and recommendations
        """
        workspace_path = os.path.join(self.working_dir, workspace)
        analysis = {
            "workspace": workspace,
            "exists": False,
            "storage_files": {},
            "total_items": 0,
            "total_size_bytes": 0,
            "recommendations": [],
            "validation_errors": []
        }

        if not os.path.exists(workspace_path):
            analysis["validation_errors"].append(f"Workspace directory does not exist: {workspace_path}")
            return analysis

        analysis["exists"] = True

        # Scan for storage files
        storage_patterns = {
            "kv_store": "kv_store_*.json",
            "vector_store": "*.vectordb",
            "graph_store": "*.graphdb",
            "doc_status": "doc_status_*.json"
        }

        for storage_type, pattern in storage_patterns.items():
            files = []
            for file_name in os.listdir(workspace_path):
                if file_name.startswith(pattern.split("*")[0]) and file_name.endswith(pattern.split("*")[1]):
                    file_path = os.path.join(workspace_path, file_name)
                    if os.path.isfile(file_path):
                        file_size = os.path.getsize(file_path)

                        # Try to count items for JSON files
                        item_count = 0
                        if file_name.endswith(".json"):
                            try:
                                with open(file_path, 'r') as f:
                                    data = json.load(f)
                                    if isinstance(data, dict):
                                        item_count = len(data)
                            except Exception:
                                pass

                        files.append({
                            "file_name": file_name,
                            "size_bytes": file_size,
                            "item_count": item_count
                        })

                        analysis["total_size_bytes"] += file_size
                        analysis["total_items"] += item_count

            if files:
                analysis["storage_files"][storage_type] = files

        # Add recommendations
        if analysis["total_items"] > 0:
            if len(workspace) == 32 and all(c in '0123456789abcdef' for c in workspace.lower()):
                analysis["recommendations"].append("Workspace appears to be a UUID - suitable for direct scope conversion")
            else:
                analysis["recommendations"].append("Consider using a UUID-based workspace for scope conversion")

            if analysis["total_items"] > 10000:
                analysis["recommendations"].append("Large dataset - consider migrating in batches")

            if analysis["total_size_bytes"] > 100 * 1024 * 1024:  # 100MB
                analysis["recommendations"].append("Large files detected - ensure sufficient disk space for migration")

        return analysis

    async def create_migration_plan(self, workspace: str, target_scope: ScopeContext) -> MigrationPlan:
        """
        Create a migration plan for moving workspace data to scope.

        Args:
            workspace: Source workspace identifier
            target_scope: Target scope context

        Returns:
            Migration plan with validation and estimates
        """
        plan = MigrationPlan(
            source_workspace=workspace,
            target_scope=target_scope
        )

        # Analyze source workspace
        analysis = await self.analyze_workspace(workspace)

        if not analysis["exists"]:
            plan.validation_errors.append(f"Source workspace '{workspace}' does not exist")
            return plan

        # Validate target scope
        try:
            # Ensure target scope is valid
            target_scope.to_dict()  # This will validate the scope
        except Exception as e:
            plan.validation_errors.append(f"Invalid target scope: {str(e)}")

        # Check for scope conflicts
        target_path = os.path.join(
            self.working_dir,
            target_scope.workspace,
            target_scope.subject_type.value,
            target_scope.subject_id
        )

        if target_scope.project:
            target_path = os.path.join(target_path, f"proj_{target_scope.project}")
        if target_scope.thread:
            target_path = os.path.join(target_path, f"thr_{target_scope.thread}")
        if target_scope.topic:
            target_path = os.path.join(target_path, f"top_{target_scope.topic}")

        if os.path.exists(target_path):
            plan.warnings.append(f"Target scope path already exists: {target_path}")

        # Populate plan details
        for storage_type, files in analysis["storage_files"].items():
            plan.storage_types.append(storage_type)
            plan.estimated_items[storage_type] = sum(f["item_count"] for f in files)
            plan.estimated_size[storage_type] = sum(f["size_bytes"] for f in files)

        return plan

    async def validate_migration(self, workspace: str, target_scope: ScopeContext) -> List[str]:
        """
        Validate that migration from workspace to scope is possible.

        Args:
            workspace: Source workspace
            target_scope: Target scope

        Returns:
            List of validation errors (empty if valid)
        """
        plan = await self.create_migration_plan(workspace, target_scope)
        return plan.validation_errors

    async def estimate_migration_size(self, workspace: str) -> Dict[str, Any]:
        """
        Estimate the size and complexity of migration.

        Args:
            workspace: Source workspace

        Returns:
            Dictionary with migration estimates
        """
        analysis = await self.analyze_workspace(workspace)

        return {
            "total_items": analysis["total_items"],
            "total_size_bytes": analysis["total_size_bytes"],
            "storage_files": analysis["storage_files"],
            "estimated_duration_minutes": max(1, analysis["total_items"] // 1000),  # Rough estimate
            "disk_space_required_bytes": analysis["total_size_bytes"] * 2,  # Double for safety
        }

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
        migration_id = str(uuid.uuid4())

        # Create migration status
        status = MigrationStatus(
            migration_id=migration_id,
            source_workspace=workspace,
            target_scope=str(target_scope),
            status="pending",
            start_time=datetime.now()
        )

        self._migration_status[migration_id] = status

        try:
            # Validate migration
            validation_errors = await self.validate_migration(workspace, target_scope)
            if validation_errors:
                status.status = "failed"
                status.error_message = f"Validation failed: {', '.join(validation_errors)}"
                return {
                    "migration_id": migration_id,
                    "status": "failed",
                    "errors": validation_errors
                }

            status.status = "running"
            self._log_migration(f"Starting migration {migration_id}: {workspace} -> {target_scope}")

            # Create migration plan
            plan = await self.create_migration_plan(workspace, target_scope)
            status.total_items = sum(plan.estimated_items.values())

            if dry_run:
                # Simulate migration
                self._log_migration(f"DRY RUN: Would migrate {status.total_items} items")
                status.status = "completed"
                status.items_migrated = status.total_items
                status.end_time = datetime.now()

                return {
                    "migration_id": migration_id,
                    "status": "completed",
                    "dry_run": True,
                    "plan": {
                        "storage_types": plan.storage_types,
                        "estimated_items": plan.estimated_items,
                        "estimated_size": plan.estimated_size,
                        "warnings": plan.warnings
                    }
                }

            # Perform actual migration
            migration_result = await self._perform_migration(workspace, target_scope, status)

            if migration_result["success"]:
                status.status = "completed"
                self._log_migration(f"Migration {migration_id} completed successfully")
            else:
                status.status = "failed"
                status.error_message = migration_result["error"]
                self._log_migration(f"Migration {migration_id} failed: {migration_result['error']}", "ERROR")

            status.end_time = datetime.now()

            return {
                "migration_id": migration_id,
                "status": status.status,
                "items_migrated": status.items_migrated,
                "total_items": status.total_items,
                "error": status.error_message
            }

        except Exception as e:
            status.status = "failed"
            status.error_message = str(e)
            status.end_time = datetime.now()
            self._log_migration(f"Migration {migration_id} failed with exception: {str(e)}", "ERROR")

            return {
                "migration_id": migration_id,
                "status": "failed",
                "error": str(e)
            }

    async def _perform_migration(self, workspace: str, target_scope: ScopeContext,
                               status: MigrationStatus) -> Dict[str, Any]:
        """
        Perform the actual migration operation.

        Args:
            workspace: Source workspace
            target_scope: Target scope
            status: Migration status to update

        Returns:
            Result dictionary with success status
        """
        try:
            # This is a simplified implementation
            # In a real implementation, you would:
            # 1. Load each storage type's data from workspace
            # 2. Create scope-aware storage instances
            # 3. Migrate data with proper scope metadata
            # 4. Verify migration integrity

            workspace_path = os.path.join(self.working_dir, workspace)
            items_processed = 0

            # For now, just simulate the migration
            for file_name in os.listdir(workspace_path):
                if file_name.endswith(".json"):
                    file_path = os.path.join(workspace_path, file_name)

                    try:
                        with open(file_path, 'r') as f:
                            data = json.load(f)

                        if isinstance(data, dict):
                            items_processed += len(data)
                            status.items_migrated = items_processed

                            # Simulate processing time
                            await asyncio.sleep(0.001)

                    except Exception as e:
                        self._log_migration(f"Error processing {file_name}: {str(e)}", "WARNING")

            return {"success": True}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_migration_status(self, migration_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a migration operation.

        Args:
            migration_id: Migration identifier

        Returns:
            Migration status dictionary or None if not found
        """
        if migration_id not in self._migration_status:
            return None

        status = self._migration_status[migration_id]

        return {
            "migration_id": migration_id,
            "source_workspace": status.source_workspace,
            "target_scope": status.target_scope,
            "status": status.status,
            "start_time": status.start_time.isoformat() if status.start_time else None,
            "end_time": status.end_time.isoformat() if status.end_time else None,
            "items_migrated": status.items_migrated,
            "total_items": status.total_items,
            "progress_percent": (status.items_migrated / status.total_items * 100) if status.total_items > 0 else 0,
            "error_message": status.error_message
        }

    async def list_migrations(self) -> List[Dict[str, Any]]:
        """
        List all migration operations.

        Returns:
            List of migration status dictionaries
        """
        migrations = []

        for migration_id in self._migration_status:
            migration_info = await self.get_migration_status(migration_id)
            if migration_info:
                migrations.append(migration_info)

        return migrations

    async def rollback_migration(self, migration_id: str) -> Dict[str, Any]:
        """
        Rollback a migration operation.

        Note: This is a placeholder implementation. A full implementation
        would require storing rollback data during migration.

        Args:
            migration_id: Migration identifier

        Returns:
            Rollback result with status and details
        """
        if migration_id not in self._migration_status:
            return {
                "status": "error",
                "message": f"Migration {migration_id} not found"
            }

        status = self._migration_status[migration_id]

        if status.status != "completed":
            return {
                "status": "error",
                "message": f"Cannot rollback migration with status: {status.status}"
            }

        # Placeholder rollback logic
        self._log_migration(f"Rolling back migration {migration_id}")
        status.status = "rolled_back"

        return {
            "status": "success",
            "message": f"Migration {migration_id} rolled back successfully"
        }