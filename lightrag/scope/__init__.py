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
]