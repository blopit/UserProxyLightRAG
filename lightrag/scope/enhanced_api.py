"""
Enhanced API models and utilities with scope support.

This module provides enhanced versions of existing API models and utilities
that include scope-based filtering and operations.
"""

from typing import Any, Dict, List, Literal, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, validator

from lightrag.base import QueryParam
from lightrag.utils import logger

from .srn import SRNParser
from .context import ScopeContext
from .exceptions import SRNError


class ScopeAwareQueryRequest(BaseModel):
    """Enhanced query request model with scope support."""

    query: str = Field(
        min_length=1,
        description="The query text",
    )

    mode: Literal["local", "global", "hybrid", "naive", "mix", "bypass"] = Field(
        default="mix",
        description="Query mode",
    )

    scope: Optional[str] = Field(
        default=None,
        description="SRN string to scope the query to a specific context",
    )

    only_need_context: Optional[bool] = Field(
        default=None,
        description="If True, only returns the retrieved context without generating a response.",
    )

    only_need_prompt: Optional[bool] = Field(
        default=None,
        description="If True, only returns the generated prompt without producing a response.",
    )

    response_type: Optional[str] = Field(
        min_length=1,
        default=None,
        description="Defines the response format. Examples: 'Multiple Paragraphs', 'Single Paragraph', 'Bullet Points'.",
    )

    top_k: Optional[int] = Field(
        ge=1,
        default=None,
        description="Number of top items to retrieve. Represents entities in 'local' mode and relationships in 'global' mode.",
    )

    include_scope_hierarchy: Optional[bool] = Field(
        default=False,
        description="If True, includes data from parent scopes in the hierarchy",
    )

    @validator('scope')
    def validate_scope_format(cls, v):
        """Validate SRN format if scope is provided."""
        if v is not None:
            try:
                parser = SRNParser()
                parser.parse(v)  # This will raise an exception if invalid
            except SRNError as e:
                raise ValueError(f"Invalid SRN format: {str(e)}")
        return v


class ScopeAwareQueryResponse(BaseModel):
    """Enhanced query response model with scope information."""

    response: str = Field(
        description="The generated response to the query"
    )

    scope_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Information about the scope used for the query"
    )

    scope_hierarchy_used: Optional[List[str]] = Field(
        default=None,
        description="List of scopes in the hierarchy that were queried"
    )

    sources_by_scope: Optional[Dict[str, List[Dict[str, Any]]]] = Field(
        default=None,
        description="Sources organized by scope"
    )

    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata about the query execution"
    )


class ScopeAwareDocumentRequest(BaseModel):
    """Enhanced document request model with scope support."""

    content: str = Field(
        description="Document content to index"
    )

    scope: Optional[str] = Field(
        default=None,
        description="SRN string to scope the document to a specific context"
    )

    file_path: Optional[str] = Field(
        default=None,
        description="Original file path of the document"
    )

    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional metadata for the document"
    )

    @validator('scope')
    def validate_scope_format(cls, v):
        """Validate SRN format if scope is provided."""
        if v is not None:
            try:
                parser = SRNParser()
                parser.parse(v)
            except SRNError as e:
                raise ValueError(f"Invalid SRN format: {str(e)}")
        return v


class ScopeAwareDocumentResponse(BaseModel):
    """Enhanced document response model with scope information."""

    success: bool = Field(description="Whether the document was indexed successfully")

    document_id: Optional[str] = Field(
        default=None,
        description="Unique identifier for the indexed document"
    )

    scope_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Scope context where the document was indexed"
    )

    message: Optional[str] = Field(
        default=None,
        description="Status message or error details"
    )


class ScopeQueryFilter(BaseModel):
    """Filter for scope-based queries."""

    workspace: Optional[str] = Field(None, description="Filter by workspace")
    subject_type: Optional[str] = Field(None, description="Filter by subject type")
    subject_id: Optional[str] = Field(None, description="Filter by subject ID")
    project: Optional[str] = Field(None, description="Filter by project")
    thread: Optional[str] = Field(None, description="Filter by thread")
    topic: Optional[str] = Field(None, description="Filter by topic")

    def to_scope_filter(self) -> Dict[str, str]:
        """Convert to scope filter dictionary."""
        filter_dict = {}
        for field in ["workspace", "subject_type", "subject_id", "project", "thread", "topic"]:
            value = getattr(self, field)
            if value is not None:
                filter_dict[field] = value
        return filter_dict


def create_scope_aware_router() -> APIRouter:
    """Create a router with scope-aware endpoints."""
    router = APIRouter(prefix="/scoped", tags=["scope-aware-query"])

    @router.post("/query", response_model=ScopeAwareQueryResponse)
    async def scoped_query(request: ScopeAwareQueryRequest):
        """
        Execute a query within a specific scope context.

        This endpoint extends the standard query functionality with scope-based
        filtering, allowing queries to be constrained to specific workspaces,
        users, projects, threads, or topics.
        """
        try:
            # Parse scope if provided
            scope_context = None
            scope_hierarchy = []

            if request.scope:
                parser = SRNParser()
                components = parser.parse(request.scope)
                scope_context = ScopeContext(components)

                # Build hierarchy if requested
                if request.include_scope_hierarchy:
                    from .context import ScopeResolver
                    resolver = ScopeResolver()
                    inheritance_chain = resolver.resolve_inheritance(scope_context)
                    scope_hierarchy = [str(scope) for scope in inheritance_chain]

            # For now, return a mock response
            # In a real implementation, this would:
            # 1. Set the scope context on the RAG instance
            # 2. Execute the query with scope filtering
            # 3. Aggregate results from scope hierarchy if requested

            response_text = f"Mock response for query: '{request.query}'"
            if scope_context:
                response_text += f" within scope: {scope_context}"

            metadata = {
                "query_mode": request.mode,
                "scope_applied": scope_context is not None,
                "hierarchy_depth": len(scope_hierarchy) if scope_hierarchy else 0
            }

            return ScopeAwareQueryResponse(
                response=response_text,
                scope_context=scope_context.to_dict() if scope_context else None,
                scope_hierarchy_used=scope_hierarchy if scope_hierarchy else None,
                metadata=metadata
            )

        except SRNError as e:
            raise HTTPException(status_code=400, detail=f"Invalid scope: {str(e)}")
        except Exception as e:
            logger.error(f"Error executing scoped query: {str(e)}")
            raise HTTPException(status_code=500, detail="Error executing query")

    @router.post("/documents", response_model=ScopeAwareDocumentResponse)
    async def insert_scoped_document(request: ScopeAwareDocumentRequest):
        """
        Insert a document with scope context.

        This endpoint allows documents to be indexed within a specific scope,
        enabling fine-grained data partitioning and access control.
        """
        try:
            # Parse scope if provided
            scope_context = None

            if request.scope:
                parser = SRNParser()
                components = parser.parse(request.scope)
                scope_context = ScopeContext(components)

            # For now, return a mock response
            # In a real implementation, this would:
            # 1. Set the scope context on the RAG instance
            # 2. Index the document with scope metadata
            # 3. Store the document in scope-aware storage

            document_id = f"doc_{abs(hash(request.content))}"

            return ScopeAwareDocumentResponse(
                success=True,
                document_id=document_id,
                scope_context=scope_context.to_dict() if scope_context else None,
                message="Document indexed successfully"
            )

        except SRNError as e:
            raise HTTPException(status_code=400, detail=f"Invalid scope: {str(e)}")
        except Exception as e:
            logger.error(f"Error indexing scoped document: {str(e)}")
            raise HTTPException(status_code=500, detail="Error indexing document")

    @router.get("/documents")
    async def list_scoped_documents(
        scope: str,
        include_children: bool = False,
        limit: int = 100
    ):
        """
        List documents within a scope.

        This endpoint returns documents that belong to a specific scope,
        with optional inclusion of documents from child scopes.
        """
        try:
            # Parse and validate scope
            parser = SRNParser()
            components = parser.parse(scope)
            scope_context = ScopeContext(components)

            # For now, return a mock response
            # In a real implementation, this would query scope-aware storage

            documents = [
                {
                    "document_id": f"doc_001_{scope_context.workspace}",
                    "title": "Example Document 1",
                    "scope": str(scope_context),
                    "indexed_at": "2024-01-15T10:30:00Z"
                },
                {
                    "document_id": f"doc_002_{scope_context.workspace}",
                    "title": "Example Document 2",
                    "scope": str(scope_context),
                    "indexed_at": "2024-01-15T11:45:00Z"
                }
            ]

            return {
                "documents": documents,
                "scope": str(scope_context),
                "total_count": len(documents),
                "include_children": include_children
            }

        except SRNError as e:
            raise HTTPException(status_code=400, detail=f"Invalid scope: {str(e)}")
        except Exception as e:
            logger.error(f"Error listing scoped documents: {str(e)}")
            raise HTTPException(status_code=500, detail="Error listing documents")

    @router.delete("/documents/{document_id}")
    async def delete_scoped_document(document_id: str, scope: str):
        """
        Delete a document from a specific scope.

        This endpoint removes a document from scope-aware storage,
        ensuring proper cleanup of all associated data.
        """
        try:
            # Parse and validate scope
            parser = SRNParser()
            components = parser.parse(scope)
            scope_context = ScopeContext(components)

            # For now, return a mock response
            # In a real implementation, this would:
            # 1. Verify the document exists in the specified scope
            # 2. Remove document from scope-aware storage
            # 3. Clean up associated vectors, graph data, etc.

            return {
                "success": True,
                "document_id": document_id,
                "scope": str(scope_context),
                "message": "Document deleted successfully"
            }

        except SRNError as e:
            raise HTTPException(status_code=400, detail=f"Invalid scope: {str(e)}")
        except Exception as e:
            logger.error(f"Error deleting scoped document: {str(e)}")
            raise HTTPException(status_code=500, detail="Error deleting document")

    return router


# Utility functions for scope-aware API integration
async def validate_and_parse_scope(scope: Optional[str]) -> Optional[ScopeContext]:
    """
    Validate and parse a scope string.

    Args:
        scope: Optional SRN string

    Returns:
        Parsed scope context or None if no scope provided

    Raises:
        HTTPException: If scope format is invalid
    """
    if not scope:
        return None

    try:
        parser = SRNParser()
        components = parser.parse(scope)
        return ScopeContext(components)
    except SRNError as e:
        raise HTTPException(status_code=400, detail=f"Invalid scope: {str(e)}")


async def apply_scope_to_query_param(query_param: QueryParam, scope: Optional[ScopeContext]) -> QueryParam:
    """
    Apply scope context to query parameters.

    This function can be used to modify query parameters based on scope context,
    such as adjusting retrieval strategies for hierarchical scopes.

    Args:
        query_param: Original query parameters
        scope: Scope context to apply

    Returns:
        Modified query parameters
    """
    if scope is None:
        return query_param

    # For now, return the original parameters
    # In a real implementation, this might:
    # - Adjust top_k based on scope depth
    # - Modify mode based on scope type
    # - Set scope-specific retrieval preferences

    return query_param


def get_scope_metadata(scope: Optional[ScopeContext]) -> Dict[str, Any]:
    """
    Get metadata about a scope for API responses.

    Args:
        scope: Scope context

    Returns:
        Metadata dictionary
    """
    if scope is None:
        return {"scope_applied": False}

    return {
        "scope_applied": True,
        "scope_depth": scope.get_scope_depth(),
        "workspace": scope.workspace,
        "subject_type": scope.subject_type.value,
        "subject_id": scope.subject_id,
        "has_project": scope.project is not None,
        "has_thread": scope.thread is not None,
        "has_topic": scope.topic is not None
    }