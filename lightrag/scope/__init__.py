"""
Scope module for LightRAG's Scope Resource Name (SRN) system.

This module provides hierarchical data partitioning beyond workspace-based isolation,
enabling organization by workspace, user, project, thread, and topic.
"""

from .exceptions import (
    SRNError,
    InvalidSRNFormatError,
    InvalidWorkspaceError,
    InvalidSubjectTypeError,
    InvalidIdentifierError,
    ScopeResolutionError,
)
from .srn import SRNComponents, SRNParser, SRNValidator, SubjectType
from .context import ScopeContext, ScopeResolver
from .storage import (
    ScopeAwareStorageMixin,
    ScopeAwareKVStorage,
    ScopeAwareVectorStorage,
    ScopeAwareGraphStorage,
    ScopeMigrationInterface,
)
from .migration import ScopeMigrationTool

# Import concrete implementations
try:
    from .implementations import ScopeAwareJsonKVStorage
    from .postgres_impl import ScopeAwarePGKVStorage
    from .graph_impl import ScopeAwareNetworkXStorage
    from .lightrag_scope import ScopeAwareLightRAG

    IMPLEMENTATIONS_AVAILABLE = True
except ImportError:
    IMPLEMENTATIONS_AVAILABLE = False

__all__ = [
    "SRNError",
    "InvalidSRNFormatError",
    "InvalidWorkspaceError",
    "InvalidSubjectTypeError",
    "InvalidIdentifierError",
    "ScopeResolutionError",
    "SRNComponents",
    "SRNParser",
    "SRNValidator",
    "SubjectType",
    "ScopeContext",
    "ScopeResolver",
    "ScopeAwareStorageMixin",
    "ScopeAwareKVStorage",
    "ScopeAwareVectorStorage",
    "ScopeAwareGraphStorage",
    "ScopeMigrationInterface",
    "ScopeMigrationTool",
]

# Add concrete implementations to exports if available
if IMPLEMENTATIONS_AVAILABLE:
    __all__.extend([
        "ScopeAwareJsonKVStorage",
        "ScopeAwarePGKVStorage",
        "ScopeAwareNetworkXStorage",
        "ScopeAwareLightRAG",
    ])