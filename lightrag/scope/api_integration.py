"""
API integration utilities for scope system.

This module provides utilities to integrate scope endpoints with existing
LightRAG API routers and create scope-aware instances.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, FastAPI

from lightrag.utils import logger
from .api import scope_router
from .enhanced_api import create_scope_aware_router


def integrate_scope_apis(app: FastAPI, prefix: str = "/api/v1") -> None:
    """
    Integrate scope management APIs into a FastAPI application.

    Args:
        app: FastAPI application instance
        prefix: API prefix for scope endpoints
    """
    # Add scope management router
    app.include_router(scope_router, prefix=prefix)

    # Add enhanced scope-aware query router
    enhanced_router = create_scope_aware_router()
    app.include_router(enhanced_router, prefix=prefix)

    logger.info(f"Integrated scope APIs with prefix: {prefix}")


def create_scope_aware_api_app(
    lightrag_config: Optional[Dict[str, Any]] = None,
    scope_config: Optional[Dict[str, Any]] = None
) -> FastAPI:
    """
    Create a FastAPI application with scope-aware LightRAG integration.

    Args:
        lightrag_config: Configuration for LightRAG instance
        scope_config: Configuration for scope system

    Returns:
        Configured FastAPI application
    """
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    # Create FastAPI app
    app = FastAPI(
        title="LightRAG with Scope Support",
        description="Enhanced LightRAG API with hierarchical scope-based data partitioning",
        version="1.4.8.2-scope"
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Integrate scope APIs
    integrate_scope_apis(app, "/api/v1")

    # Add health check endpoint
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "scope_support": True,
            "version": "1.4.8.2-scope"
        }

    logger.info("Created scope-aware FastAPI application")
    return app


def get_scope_dependency():
    """Dependency injection for scope context in API endpoints."""
    # This would be used in FastAPI endpoints to inject scope context
    # Implementation depends on how scope is passed (header, query param, etc.)
    pass


def create_backward_compatible_router() -> APIRouter:
    """
    Create a router that provides backward compatibility with existing APIs.

    This router ensures that existing API calls continue to work while
    providing enhanced functionality when scope parameters are provided.
    """
    from fastapi import APIRouter, Query, Header
    from typing import Optional

    router = APIRouter(tags=["backward-compatible"])

    @router.post("/query")
    async def backward_compatible_query(
        query: str,
        mode: str = "mix",
        scope: Optional[str] = Query(None, description="Optional SRN scope"),
        x_scope: Optional[str] = Header(None, alias="X-Scope", description="Optional SRN scope in header")
    ):
        """
        Backward compatible query endpoint with optional scope support.

        This endpoint maintains compatibility with existing query API while
        adding optional scope support through query parameters or headers.
        """
        # Use scope from header if not provided in query params
        effective_scope = scope or x_scope

        # For now, return a mock response
        # In real implementation, this would use ScopeAwareLightRAG
        response = {
            "response": f"Mock response for: {query}",
            "mode": mode,
            "scope_applied": effective_scope is not None,
            "scope": effective_scope,
            "backward_compatible": True
        }

        return response

    @router.post("/documents")
    async def backward_compatible_insert(
        content: str,
        scope: Optional[str] = Query(None, description="Optional SRN scope"),
        x_scope: Optional[str] = Header(None, alias="X-Scope", description="Optional SRN scope in header")
    ):
        """
        Backward compatible document insertion with optional scope support.
        """
        effective_scope = scope or x_scope

        # Mock response
        return {
            "success": True,
            "message": "Document inserted successfully",
            "scope_applied": effective_scope is not None,
            "scope": effective_scope,
            "backward_compatible": True
        }

    return router


# Configuration helpers
def get_default_scope_config() -> Dict[str, Any]:
    """Get default configuration for scope system."""
    return {
        "enable_scope_inheritance": True,
        "scope_validation_strict": True,
        "default_workspace": None,
        "migration_batch_size": 1000,
        "scope_cache_size": 10000,
        "scope_cache_ttl": 3600,  # 1 hour
    }


def merge_scope_config(
    base_config: Dict[str, Any],
    override_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Merge scope configuration with overrides.

    Args:
        base_config: Base configuration
        override_config: Configuration overrides

    Returns:
        Merged configuration
    """
    if override_config is None:
        return base_config.copy()

    merged = base_config.copy()
    merged.update(override_config)
    return merged


# Environment variable helpers
def get_scope_config_from_env() -> Dict[str, Any]:
    """Get scope configuration from environment variables."""
    import os

    config = {}

    # Boolean settings
    bool_settings = {
        "SCOPE_ENABLE_INHERITANCE": "enable_scope_inheritance",
        "SCOPE_VALIDATION_STRICT": "scope_validation_strict",
    }

    for env_key, config_key in bool_settings.items():
        value = os.getenv(env_key)
        if value is not None:
            config[config_key] = value.lower() in ("true", "1", "yes", "on")

    # String settings
    string_settings = {
        "SCOPE_DEFAULT_WORKSPACE": "default_workspace",
    }

    for env_key, config_key in string_settings.items():
        value = os.getenv(env_key)
        if value:
            config[config_key] = value

    # Integer settings
    int_settings = {
        "SCOPE_MIGRATION_BATCH_SIZE": "migration_batch_size",
        "SCOPE_CACHE_SIZE": "scope_cache_size",
        "SCOPE_CACHE_TTL": "scope_cache_ttl",
    }

    for env_key, config_key in int_settings.items():
        value = os.getenv(env_key)
        if value:
            try:
                config[config_key] = int(value)
            except ValueError:
                logger.warning(f"Invalid integer value for {env_key}: {value}")

    return config


# Factory functions for common configurations
def create_development_scope_config() -> Dict[str, Any]:
    """Create scope configuration optimized for development."""
    config = get_default_scope_config()
    config.update({
        "scope_validation_strict": False,  # More lenient for dev
        "migration_batch_size": 100,  # Smaller batches for dev
        "scope_cache_ttl": 300,  # Shorter cache for dev
    })
    return config


def create_production_scope_config() -> Dict[str, Any]:
    """Create scope configuration optimized for production."""
    config = get_default_scope_config()
    config.update({
        "scope_validation_strict": True,  # Strict validation for prod
        "migration_batch_size": 10000,  # Larger batches for efficiency
        "scope_cache_size": 50000,  # Larger cache for prod
        "scope_cache_ttl": 7200,  # Longer cache for prod
    })
    return config


# Middleware for scope context
class ScopeContextMiddleware:
    """
    Middleware to extract and validate scope context from requests.

    This middleware can extract scope information from various sources:
    - Query parameters
    - Headers
    - JWT tokens
    - Request path
    """

    def __init__(self, app, scope_header: str = "X-Scope"):
        self.app = app
        self.scope_header = scope_header

    async def __call__(self, scope, receive, send):
        """Process request and extract scope context."""
        # This is a simplified middleware implementation
        # In practice, you'd extract scope from headers, validate it,
        # and make it available to endpoint handlers

        # For now, just pass through to the application
        await self.app(scope, receive, send)