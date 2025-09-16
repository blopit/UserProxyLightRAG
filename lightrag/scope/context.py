"""
Scope context management for the SRN system.

This module provides classes for managing scope contexts, including scope resolution,
inheritance, and filter generation for storage operations.
"""

from typing import Optional, Dict, Any, List, Union
import fnmatch

from .srn import SRNParser, SRNComponents, SubjectType
from .exceptions import ScopeResolutionError, InvalidSRNFormatError


class ScopeContext:
    """
    Represents a scope context for data partitioning.

    This class encapsulates an SRN and provides methods for accessing
    components, generating filters, and comparing scopes.
    """

    def __init__(self, srn: Union[str, SRNComponents]):
        """
        Initialize scope context.

        Args:
            srn: SRN string or SRNComponents object

        Raises:
            InvalidSRNFormatError: If SRN string is invalid
        """
        if isinstance(srn, str):
            parser = SRNParser()
            self.components = parser.parse(srn)
            self.srn_string = srn.lower().strip()
        elif isinstance(srn, SRNComponents):
            self.components = srn
            parser = SRNParser()
            self.srn_string = parser.to_string(srn)
        else:
            raise ValueError("SRN must be a string or SRNComponents object")

    @property
    def version(self) -> str:
        """Get the SRN version."""
        return self.components.version

    @property
    def workspace(self) -> str:
        """Get the workspace ID."""
        return self.components.workspace

    @property
    def subject_type(self) -> SubjectType:
        """Get the subject type."""
        return self.components.subject_type

    @property
    def subject_id(self) -> str:
        """Get the subject ID."""
        return self.components.subject_id

    @property
    def project(self) -> Optional[str]:
        """Get the project ID."""
        return self.components.project

    @property
    def thread(self) -> Optional[str]:
        """Get the thread ID."""
        return self.components.thread

    @property
    def topic(self) -> Optional[str]:
        """Get the topic ID."""
        return self.components.topic

    def to_dict(self) -> Dict[str, Any]:
        """Convert scope context to dictionary."""
        return self.components.to_dict()

    def to_filter_dict(self) -> Dict[str, str]:
        """
        Generate a filter dictionary for storage queries.

        Returns:
            Dictionary with non-None scope components as key-value pairs
        """
        filter_dict = {
            "workspace": self.workspace,
            "subject_type": self.subject_type.value,
            "subject_id": self.subject_id,
        }

        if self.project:
            filter_dict["project"] = self.project
        if self.thread:
            filter_dict["thread"] = self.thread
        if self.topic:
            filter_dict["topic"] = self.topic

        return filter_dict

    def matches_scope(self, other_scope: 'ScopeContext') -> bool:
        """
        Check if this scope matches another scope exactly.

        Args:
            other_scope: Scope to compare against

        Returns:
            True if scopes match exactly
        """
        return self.srn_string == other_scope.srn_string

    def is_parent_of(self, child_scope: 'ScopeContext') -> bool:
        """
        Check if this scope is a parent of another scope.

        A scope is a parent if the child scope has all the same components
        plus additional optional components.

        Args:
            child_scope: Potential child scope

        Returns:
            True if this scope is a parent of the child scope
        """
        # Must have same base components
        if (self.workspace != child_scope.workspace or
            self.subject_type != child_scope.subject_type or
            self.subject_id != child_scope.subject_id):
            return False

        # Child must have all parent components
        if self.project and child_scope.project != self.project:
            return False
        if self.thread and child_scope.thread != self.thread:
            return False
        if self.topic and child_scope.topic != self.topic:
            return False

        # Child must have at least one additional component
        has_additional = False
        if not self.project and child_scope.project:
            has_additional = True
        if not self.thread and child_scope.thread:
            has_additional = True
        if not self.topic and child_scope.topic:
            has_additional = True

        return has_additional

    def is_child_of(self, parent_scope: 'ScopeContext') -> bool:
        """
        Check if this scope is a child of another scope.

        Args:
            parent_scope: Potential parent scope

        Returns:
            True if this scope is a child of the parent scope
        """
        return parent_scope.is_parent_of(self)

    def get_parent_scope(self) -> Optional['ScopeContext']:
        """
        Get the immediate parent scope by removing the most specific component.

        Returns:
            Parent scope context, or None if this is already the base scope
        """
        if self.topic:
            # Remove topic
            parent_components = SRNComponents(
                version=self.version,
                workspace=self.workspace,
                subject_type=self.subject_type,
                subject_id=self.subject_id,
                project=self.project,
                thread=self.thread,
                topic=None
            )
            return ScopeContext(parent_components)
        elif self.thread:
            # Remove thread
            parent_components = SRNComponents(
                version=self.version,
                workspace=self.workspace,
                subject_type=self.subject_type,
                subject_id=self.subject_id,
                project=self.project,
                thread=None,
                topic=None
            )
            return ScopeContext(parent_components)
        elif self.project:
            # Remove project
            parent_components = SRNComponents(
                version=self.version,
                workspace=self.workspace,
                subject_type=self.subject_type,
                subject_id=self.subject_id,
                project=None,
                thread=None,
                topic=None
            )
            return ScopeContext(parent_components)
        else:
            # Already at base level
            return None

    def get_scope_depth(self) -> int:
        """
        Get the depth of this scope.

        Returns:
            Scope depth (0 = base, 1 = with project, 2 = with thread, 3 = with topic)
        """
        depth = 0
        if self.project:
            depth += 1
        if self.thread:
            depth += 1
        if self.topic:
            depth += 1
        return depth

    def __str__(self) -> str:
        """String representation of the scope context."""
        return self.srn_string

    def __repr__(self) -> str:
        """Detailed representation of the scope context."""
        return f"ScopeContext('{self.srn_string}')"

    def __eq__(self, other) -> bool:
        """Check equality with another scope context."""
        if not isinstance(other, ScopeContext):
            return False
        return self.srn_string == other.srn_string

    def __hash__(self) -> int:
        """Hash function for use in sets and dictionaries."""
        return hash(self.srn_string)


class ScopeResolver:
    """
    Resolver for scope inheritance and pattern matching.

    This class provides utilities for resolving scope hierarchies,
    matching scope patterns, and merging scope contexts.
    """

    def __init__(self):
        self.parser = SRNParser()

    def resolve_inheritance(self, scope: ScopeContext) -> List[ScopeContext]:
        """
        Resolve the inheritance chain for a scope.

        Returns all parent scopes from the given scope up to the base scope.

        Args:
            scope: Scope to resolve inheritance for

        Returns:
            List of scope contexts from most specific to least specific
        """
        inheritance_chain = [scope]
        current_scope = scope

        while True:
            parent_scope = current_scope.get_parent_scope()
            if parent_scope is None:
                break
            inheritance_chain.append(parent_scope)
            current_scope = parent_scope

        return inheritance_chain

    def find_matching_scopes(self, pattern: str, available_scopes: List[ScopeContext]) -> List[ScopeContext]:
        """
        Find scopes that match a given pattern.

        Supports wildcard patterns using fnmatch syntax.

        Args:
            pattern: Pattern to match (supports wildcards like * and ?)
            available_scopes: List of available scopes to match against

        Returns:
            List of matching scope contexts
        """
        matching_scopes = []

        for scope in available_scopes:
            if fnmatch.fnmatch(scope.srn_string, pattern):
                matching_scopes.append(scope)

        return matching_scopes

    def get_common_parent(self, scopes: List[ScopeContext]) -> Optional[ScopeContext]:
        """
        Find the common parent scope of multiple scopes.

        Args:
            scopes: List of scope contexts

        Returns:
            Common parent scope, or None if no common parent exists
        """
        if not scopes:
            return None

        if len(scopes) == 1:
            return scopes[0].get_parent_scope()

        # Start with the first scope's inheritance chain
        common_ancestors = set(self.resolve_inheritance(scopes[0]))

        # Find intersection with other scopes' inheritance chains
        for scope in scopes[1:]:
            scope_ancestors = set(self.resolve_inheritance(scope))
            common_ancestors &= scope_ancestors

        if not common_ancestors:
            return None

        # Return the most specific common ancestor
        return min(common_ancestors, key=lambda s: s.get_scope_depth(), default=None)

    def merge_scope_filters(self, scopes: List[ScopeContext]) -> Dict[str, Any]:
        """
        Merge multiple scopes into a unified filter dictionary.

        This creates a filter that matches any of the provided scopes.

        Args:
            scopes: List of scope contexts to merge

        Returns:
            Merged filter dictionary
        """
        if not scopes:
            return {}

        if len(scopes) == 1:
            return scopes[0].to_filter_dict()

        # Collect all unique values for each field
        merged_filter = {}
        fields = ["workspace", "subject_type", "subject_id", "project", "thread", "topic"]

        for field in fields:
            values = set()
            for scope in scopes:
                scope_dict = scope.to_filter_dict()
                if field in scope_dict:
                    values.add(scope_dict[field])

            if values:
                if len(values) == 1:
                    merged_filter[field] = list(values)[0]
                else:
                    merged_filter[f"{field}__in"] = list(values)

        return merged_filter

    def create_scope_from_workspace(self, workspace: str, default_subject_type: str = "system",
                                   default_subject_id: str = "default") -> ScopeContext:
        """
        Create a scope context from a legacy workspace identifier.

        This is used for backward compatibility with the existing workspace system.

        Args:
            workspace: Workspace identifier
            default_subject_type: Default subject type to use
            default_subject_id: Default subject ID to use

        Returns:
            Scope context equivalent to the workspace

        Raises:
            ScopeResolutionError: If workspace cannot be converted to valid scope
        """
        try:
            # Validate workspace format (should be 32 hex chars)
            if len(workspace) != 32 or not all(c in '0123456789abcdef' for c in workspace.lower()):
                raise ScopeResolutionError(f"Invalid workspace format: {workspace}")

            # Create SRN components
            components = SRNComponents(
                version="1",
                workspace=workspace.lower(),
                subject_type=SubjectType(default_subject_type),
                subject_id=default_subject_id
            )

            return ScopeContext(components)

        except Exception as e:
            raise ScopeResolutionError(f"Failed to create scope from workspace '{workspace}': {str(e)}")

    def extract_workspace_from_scope(self, scope: ScopeContext) -> str:
        """
        Extract the workspace identifier from a scope context.

        This is used for backward compatibility with the existing workspace system.

        Args:
            scope: Scope context

        Returns:
            Workspace identifier
        """
        return scope.workspace