"""
API endpoints for scope management.

This module provides FastAPI routes for managing scopes, validating SRNs,
and performing migrations from workspace to scope-based data.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field, validator

from lightrag.utils import logger
from .srn import SRNParser, SRNValidator, SRNComponents, SubjectType
from .context import ScopeContext, ScopeResolver
from .migration import ScopeMigrationTool, MigrationPlan
from .exceptions import SRNError, ScopeResolutionError


# Request/Response Models
class SRNValidationRequest(BaseModel):
    """Request model for SRN validation."""
    srn: str = Field(..., description="SRN string to validate")

class SRNValidationResponse(BaseModel):
    """Response model for SRN validation."""
    valid: bool = Field(..., description="Whether the SRN is valid")
    components: Optional[Dict[str, Any]] = Field(None, description="Parsed SRN components if valid")
    error: Optional[str] = Field(None, description="Error message if invalid")

class SRNParseRequest(BaseModel):
    """Request model for SRN parsing."""
    srn: str = Field(..., description="SRN string to parse")

class SRNParseResponse(BaseModel):
    """Response model for SRN parsing."""
    components: Dict[str, Any] = Field(..., description="Parsed SRN components")
    scope_context: Dict[str, Any] = Field(..., description="Scope context information")

class ScopeListRequest(BaseModel):
    """Request model for listing scopes."""
    workspace: Optional[str] = Field(None, description="Filter by workspace")
    subject_type: Optional[str] = Field(None, description="Filter by subject type")
    pattern: Optional[str] = Field(None, description="Pattern to match (supports wildcards)")
    limit: int = Field(100, description="Maximum number of results to return")

class ScopeListResponse(BaseModel):
    """Response model for scope listing."""
    scopes: List[Dict[str, Any]] = Field(..., description="List of available scopes")
    total_count: int = Field(..., description="Total number of scopes found")

class ScopeStatsRequest(BaseModel):
    """Request model for scope statistics."""
    scope: str = Field(..., description="SRN string for the scope")

class ScopeStatsResponse(BaseModel):
    """Response model for scope statistics."""
    scope: str = Field(..., description="SRN string")
    storage_stats: Dict[str, Any] = Field(..., description="Storage statistics by type")
    total_items: int = Field(..., description="Total items across all storage types")
    disk_usage_bytes: int = Field(..., description="Estimated disk usage in bytes")

class MigrationValidationRequest(BaseModel):
    """Request model for migration validation."""
    workspace: str = Field(..., description="Source workspace identifier")
    target_scope: str = Field(..., description="Target SRN string")

class MigrationValidationResponse(BaseModel):
    """Response model for migration validation."""
    valid: bool = Field(..., description="Whether migration is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    plan: Optional[Dict[str, Any]] = Field(None, description="Migration plan if valid")

class MigrationRequest(BaseModel):
    """Request model for workspace migration."""
    workspace: str = Field(..., description="Source workspace identifier")
    target_scope: str = Field(..., description="Target SRN string")
    dry_run: bool = Field(True, description="Whether to perform a dry run")

class MigrationResponse(BaseModel):
    """Response model for migration operation."""
    migration_id: str = Field(..., description="Migration identifier")
    status: str = Field(..., description="Migration status")
    dry_run: bool = Field(..., description="Whether this was a dry run")
    items_migrated: int = Field(0, description="Number of items migrated")
    total_items: int = Field(0, description="Total items to migrate")
    error: Optional[str] = Field(None, description="Error message if failed")

class MigrationStatusResponse(BaseModel):
    """Response model for migration status."""
    migration_id: str = Field(..., description="Migration identifier")
    source_workspace: str = Field(..., description="Source workspace")
    target_scope: str = Field(..., description="Target scope")
    status: str = Field(..., description="Migration status")
    progress_percent: float = Field(..., description="Progress percentage")
    start_time: Optional[str] = Field(None, description="Start time (ISO format)")
    end_time: Optional[str] = Field(None, description="End time (ISO format)")
    items_migrated: int = Field(..., description="Items migrated so far")
    total_items: int = Field(..., description="Total items to migrate")
    error_message: Optional[str] = Field(None, description="Error message if failed")


# Router instance
scope_router = APIRouter(prefix="/scopes", tags=["scope-management"])


# Utility functions
def get_srn_parser() -> SRNParser:
    """Get SRN parser instance."""
    return SRNParser()

def get_scope_resolver() -> ScopeResolver:
    """Get scope resolver instance."""
    return ScopeResolver()

def get_migration_tool() -> ScopeMigrationTool:
    """Get migration tool instance."""
    # This would typically be injected based on configuration
    working_dir = "."  # Should come from app configuration
    return ScopeMigrationTool(working_dir)


# API Endpoints
@scope_router.post("/validate", response_model=SRNValidationResponse)
async def validate_srn(request: SRNValidationRequest, parser: SRNParser = Depends(get_srn_parser)):
    """
    Validate an SRN string.

    This endpoint validates the format and components of an SRN string
    and returns detailed validation information.
    """
    try:
        components = parser.parse(request.srn)
        return SRNValidationResponse(
            valid=True,
            components=components.to_dict()
        )
    except SRNError as e:
        return SRNValidationResponse(
            valid=False,
            error=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error validating SRN: {str(e)}")
        return SRNValidationResponse(
            valid=False,
            error="Internal validation error"
        )


@scope_router.post("/parse", response_model=SRNParseResponse)
async def parse_srn(request: SRNParseRequest, parser: SRNParser = Depends(get_srn_parser)):
    """
    Parse an SRN string into components.

    This endpoint parses a valid SRN string and returns both the
    individual components and a scope context object.
    """
    try:
        components = parser.parse(request.srn)
        context = ScopeContext(components)

        return SRNParseResponse(
            components=components.to_dict(),
            scope_context=context.to_dict()
        )
    except SRNError as e:
        raise HTTPException(status_code=400, detail=f"Invalid SRN: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error parsing SRN: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal parsing error")


@scope_router.post("/list", response_model=ScopeListResponse)
async def list_scopes(request: ScopeListRequest, resolver: ScopeResolver = Depends(get_scope_resolver)):
    """
    List available scopes with optional filtering.

    This endpoint discovers and lists scopes based on the storage
    structure and applies optional filters.
    """
    try:
        # For now, return a placeholder response
        # In a real implementation, this would scan storage backends
        scopes = []

        # Generate some example scopes for demonstration
        if request.workspace:
            example_scope = f"1.{request.workspace}.user.example"
            try:
                context = ScopeContext(example_scope)
                scopes.append(context.to_dict())
            except Exception:
                pass
        else:
            # Generate a few example scopes
            example_scopes = [
                "1.abc12345abcd12345abc1234567890ab.user.johndoe",
                "1.abc12345abcd12345abc1234567890ab.user.janedoe.proj_research",
                "1.def67890cdef67890cdef67890cdef67.agent.chatbot.proj_support.thr_chat1"
            ]

            for srn in example_scopes:
                try:
                    context = ScopeContext(srn)
                    scope_dict = context.to_dict()

                    # Apply filters
                    if request.subject_type and scope_dict["subject_type"] != request.subject_type:
                        continue
                    if request.pattern and not any(request.pattern in str(v) for v in scope_dict.values()):
                        continue

                    scopes.append(scope_dict)
                except Exception:
                    continue

        # Apply limit
        limited_scopes = scopes[:request.limit]

        return ScopeListResponse(
            scopes=limited_scopes,
            total_count=len(scopes)
        )

    except Exception as e:
        logger.error(f"Error listing scopes: {str(e)}")
        raise HTTPException(status_code=500, detail="Error listing scopes")


@scope_router.post("/stats", response_model=ScopeStatsResponse)
async def get_scope_stats(request: ScopeStatsRequest, parser: SRNParser = Depends(get_srn_parser)):
    """
    Get statistics for a specific scope.

    This endpoint analyzes storage usage and item counts for a given scope.
    """
    try:
        # Validate the scope first
        components = parser.parse(request.scope)
        context = ScopeContext(components)

        # For now, return placeholder statistics
        # In a real implementation, this would query actual storage backends
        storage_stats = {
            "kv_storage": {"items": 150, "size_bytes": 1024 * 50},
            "vector_storage": {"items": 75, "size_bytes": 1024 * 200},
            "graph_storage": {"nodes": 45, "edges": 120, "size_bytes": 1024 * 30},
            "doc_status": {"items": 25, "size_bytes": 1024 * 5}
        }

        total_items = sum(
            stats.get("items", 0) + stats.get("nodes", 0)
            for stats in storage_stats.values()
        )

        total_size = sum(
            stats.get("size_bytes", 0)
            for stats in storage_stats.values()
        )

        return ScopeStatsResponse(
            scope=request.scope,
            storage_stats=storage_stats,
            total_items=total_items,
            disk_usage_bytes=total_size
        )

    except SRNError as e:
        raise HTTPException(status_code=400, detail=f"Invalid scope: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting scope stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving scope statistics")


# Migration endpoints
@scope_router.post("/migrations/validate", response_model=MigrationValidationResponse)
async def validate_migration(
    request: MigrationValidationRequest,
    migration_tool: ScopeMigrationTool = Depends(get_migration_tool),
    parser: SRNParser = Depends(get_srn_parser)
):
    """
    Validate a proposed workspace-to-scope migration.

    This endpoint validates that a migration from workspace to scope
    is feasible and returns a migration plan.
    """
    try:
        # Parse and validate target scope
        target_components = parser.parse(request.target_scope)
        target_context = ScopeContext(target_components)

        # Validate the migration
        errors = await migration_tool.validate_migration(request.workspace, target_context)

        if not errors:
            # Create migration plan
            plan = await migration_tool.create_migration_plan(request.workspace, target_context)

            return MigrationValidationResponse(
                valid=True,
                warnings=plan.warnings,
                plan={
                    "storage_types": plan.storage_types,
                    "estimated_items": plan.estimated_items,
                    "estimated_size": plan.estimated_size
                }
            )
        else:
            return MigrationValidationResponse(
                valid=False,
                errors=errors
            )

    except SRNError as e:
        raise HTTPException(status_code=400, detail=f"Invalid target scope: {str(e)}")
    except Exception as e:
        logger.error(f"Error validating migration: {str(e)}")
        raise HTTPException(status_code=500, detail="Error validating migration")


@scope_router.post("/migrations/migrate", response_model=MigrationResponse)
async def migrate_workspace(
    request: MigrationRequest,
    background_tasks: BackgroundTasks,
    migration_tool: ScopeMigrationTool = Depends(get_migration_tool),
    parser: SRNParser = Depends(get_srn_parser)
):
    """
    Migrate workspace data to scope format.

    This endpoint initiates a migration from workspace-based storage
    to scope-based storage. For non-dry-run migrations, the operation
    runs in the background.
    """
    try:
        # Parse and validate target scope
        target_components = parser.parse(request.target_scope)
        target_context = ScopeContext(target_components)

        # Start migration
        result = await migration_tool.migrate_workspace_to_scope(
            request.workspace,
            target_context,
            request.dry_run
        )

        return MigrationResponse(
            migration_id=result["migration_id"],
            status=result["status"],
            dry_run=request.dry_run,
            items_migrated=result.get("items_migrated", 0),
            total_items=result.get("total_items", 0),
            error=result.get("error")
        )

    except SRNError as e:
        raise HTTPException(status_code=400, detail=f"Invalid target scope: {str(e)}")
    except Exception as e:
        logger.error(f"Error starting migration: {str(e)}")
        raise HTTPException(status_code=500, detail="Error starting migration")


@scope_router.get("/migrations/{migration_id}", response_model=MigrationStatusResponse)
async def get_migration_status(
    migration_id: str,
    migration_tool: ScopeMigrationTool = Depends(get_migration_tool)
):
    """
    Get the status of a migration operation.

    This endpoint returns the current status and progress of a
    migration operation by its ID.
    """
    try:
        status = await migration_tool.get_migration_status(migration_id)

        if not status:
            raise HTTPException(status_code=404, detail="Migration not found")

        return MigrationStatusResponse(**status)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting migration status: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving migration status")


@scope_router.get("/migrations", response_model=List[MigrationStatusResponse])
async def list_migrations(migration_tool: ScopeMigrationTool = Depends(get_migration_tool)):
    """
    List all migration operations.

    This endpoint returns a list of all migration operations
    with their current status.
    """
    try:
        migrations = await migration_tool.list_migrations()
        return [MigrationStatusResponse(**migration) for migration in migrations]

    except Exception as e:
        logger.error(f"Error listing migrations: {str(e)}")
        raise HTTPException(status_code=500, detail="Error listing migrations")


@scope_router.post("/migrations/{migration_id}/rollback")
async def rollback_migration(
    migration_id: str,
    migration_tool: ScopeMigrationTool = Depends(get_migration_tool)
):
    """
    Rollback a completed migration.

    This endpoint attempts to rollback a completed migration operation.
    Note that rollback capabilities depend on the storage implementation.
    """
    try:
        result = await migration_tool.rollback_migration(migration_id)

        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])

        return {"message": result["message"]}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rolling back migration: {str(e)}")
        raise HTTPException(status_code=500, detail="Error rolling back migration")