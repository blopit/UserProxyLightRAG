from .lightrag import LightRAG as LightRAG, QueryParam as QueryParam

# Scope system exports
try:
    from .scope import (
        SRNComponents,
        SRNParser,
        ScopeContext,
        ScopeResolver,
        ScopeAwareStorageMixin,
        ScopeAwareLightRAG,
    )
    from .scope.lightrag_scope import ScopeAwareLightRAG
    from .scope.api_integration import integrate_scope_apis, create_scope_aware_api_app

    # Add scope exports to __all__
    __all__ = [
        "LightRAG",
        "QueryParam",
        "SRNComponents",
        "SRNParser",
        "ScopeContext",
        "ScopeResolver",
        "ScopeAwareStorageMixin",
        "ScopeAwareLightRAG",
        "integrate_scope_apis",
        "create_scope_aware_api_app",
    ]

    SCOPE_SUPPORT = True
except ImportError:
    # Scope system not available, fall back to basic exports
    __all__ = ["LightRAG", "QueryParam"]
    SCOPE_SUPPORT = False

__version__ = "1.4.8.2-scope"
__author__ = "Zirui Guo"
__url__ = "https://github.com/HKUDS/LightRAG"
