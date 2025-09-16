"""
Scope Resource Name (SRN) parser and validator.

This module provides parsing, validation, and canonicalization of SRN strings
according to the format: 1.<ws32>.<subject_type>.<subject_id>[.proj_<project>][.thr_<thread>][.top_<topic>]
"""

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any

from .exceptions import (
    InvalidSRNFormatError,
    InvalidWorkspaceError,
    InvalidSubjectTypeError,
    InvalidIdentifierError,
)


class SubjectType(str, Enum):
    """Valid subject types for SRN."""
    USER = "user"
    AGENT = "agent"
    WORKSPACE = "workspace"
    CONTACT = "contact"
    PROJECT = "project"
    SYSTEM = "system"


@dataclass
class SRNComponents:
    """Parsed components of an SRN string."""
    version: str
    workspace: str
    subject_type: SubjectType
    subject_id: str
    project: Optional[str] = None
    thread: Optional[str] = None
    topic: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert components to dictionary."""
        result = {
            "version": self.version,
            "workspace": self.workspace,
            "subject_type": self.subject_type.value,
            "subject_id": self.subject_id,
        }
        if self.project:
            result["project"] = self.project
        if self.thread:
            result["thread"] = self.thread
        if self.topic:
            result["topic"] = self.topic
        return result


class SRNValidator:
    """Validator for SRN components."""

    # Regex patterns for validation
    WORKSPACE_PATTERN = re.compile(r'^[a-f0-9]{32}$')
    IDENTIFIER_PATTERN = re.compile(r'^[a-z0-9_-]{1,63}$')
    VALID_VERSIONS = {"1"}

    @classmethod
    def validate_version(cls, version: str) -> bool:
        """Validate SRN version."""
        if version not in cls.VALID_VERSIONS:
            raise InvalidSRNFormatError(
                f"Invalid version '{version}'. Supported versions: {', '.join(cls.VALID_VERSIONS)}"
            )
        return True

    @classmethod
    def validate_workspace_uuid(cls, workspace: str) -> bool:
        """Validate workspace UUID format (32 hex characters)."""
        if not cls.WORKSPACE_PATTERN.match(workspace):
            raise InvalidWorkspaceError(
                f"Workspace must be exactly 32 lowercase hexadecimal characters, got: '{workspace}'"
            )
        return True

    @classmethod
    def validate_subject_type(cls, subject_type: str) -> bool:
        """Validate subject type against allowed values."""
        try:
            SubjectType(subject_type)
        except ValueError:
            valid_types = [t.value for t in SubjectType]
            raise InvalidSubjectTypeError(
                f"Invalid subject type '{subject_type}'. Valid types: {', '.join(valid_types)}"
            )
        return True

    @classmethod
    def validate_identifier(cls, identifier: str, identifier_type: str = "identifier") -> bool:
        """Validate identifier format (alphanumeric, underscore, hyphen, 1-63 chars)."""
        if not identifier:
            raise InvalidIdentifierError(f"{identifier_type} cannot be empty")

        if not cls.IDENTIFIER_PATTERN.match(identifier):
            raise InvalidIdentifierError(
                f"Invalid {identifier_type} '{identifier}'. Must be 1-63 characters, "
                f"containing only lowercase letters, numbers, underscore, and hyphen"
            )
        return True

    @classmethod
    def validate_segment_length(cls, segment: str, segment_type: str = "segment") -> bool:
        """Validate that a segment doesn't exceed maximum length."""
        if len(segment) > 63:
            raise InvalidIdentifierError(
                f"{segment_type} '{segment}' exceeds maximum length of 63 characters"
            )
        return True


class SRNParser:
    """Parser for SRN strings."""

    # Regex pattern for parsing complete SRN
    SRN_PATTERN = re.compile(
        r'^(?P<version>\d+)\.'
        r'(?P<workspace>[a-f0-9]{32})\.'
        r'(?P<subject_type>user|agent|workspace|contact|project|system)\.'
        r'(?P<subject_id>[a-z0-9_-]{1,63})'
        r'(?:\.proj_(?P<project>[a-z0-9_-]{1,63}))?'
        r'(?:\.thr_(?P<thread>[a-z0-9_-]{1,63}))?'
        r'(?:\.top_(?P<topic>[a-z0-9_-]{1,63}))?$'
    )

    def __init__(self):
        self.validator = SRNValidator()

    def canonicalize(self, srn_string: str) -> str:
        """
        Canonicalize SRN string by normalizing Unicode and converting to lowercase.

        Args:
            srn_string: Raw SRN string

        Returns:
            Canonicalized SRN string
        """
        if not srn_string:
            raise InvalidSRNFormatError("SRN string cannot be empty")

        # Normalize Unicode to NFC (Canonical Composition)
        normalized = unicodedata.normalize('NFC', srn_string)

        # Convert to lowercase and strip whitespace
        canonicalized = normalized.lower().strip()

        if not canonicalized:
            raise InvalidSRNFormatError("SRN string cannot be empty after canonicalization")

        return canonicalized

    def parse(self, srn_string: str) -> SRNComponents:
        """
        Parse SRN string into components.

        Args:
            srn_string: SRN string to parse

        Returns:
            Parsed SRN components

        Raises:
            InvalidSRNFormatError: If SRN format is invalid
            InvalidWorkspaceError: If workspace format is invalid
            InvalidSubjectTypeError: If subject type is invalid
            InvalidIdentifierError: If any identifier is invalid
        """
        # Canonicalize the input
        canonical_srn = self.canonicalize(srn_string)

        # Match against pattern
        match = self.SRN_PATTERN.match(canonical_srn)
        if not match:
            raise InvalidSRNFormatError(f"Invalid SRN format: '{srn_string}'", srn_string)

        groups = match.groupdict()

        # Validate components
        self.validator.validate_version(groups['version'])
        self.validator.validate_workspace_uuid(groups['workspace'])
        self.validator.validate_subject_type(groups['subject_type'])
        self.validator.validate_identifier(groups['subject_id'], "subject_id")

        # Validate optional components
        if groups.get('project'):
            self.validator.validate_identifier(groups['project'], "project")
        if groups.get('thread'):
            self.validator.validate_identifier(groups['thread'], "thread")
        if groups.get('topic'):
            self.validator.validate_identifier(groups['topic'], "topic")

        # Create components object
        return SRNComponents(
            version=groups['version'],
            workspace=groups['workspace'],
            subject_type=SubjectType(groups['subject_type']),
            subject_id=groups['subject_id'],
            project=groups.get('project'),
            thread=groups.get('thread'),
            topic=groups.get('topic')
        )

    def to_string(self, components: SRNComponents) -> str:
        """
        Convert SRN components back to string format.

        Args:
            components: SRN components to convert

        Returns:
            SRN string
        """
        # Build base SRN
        srn = f"{components.version}.{components.workspace}.{components.subject_type.value}.{components.subject_id}"

        # Add optional components in the correct order
        if components.project:
            srn += f".proj_{components.project}"
        if components.thread:
            srn += f".thr_{components.thread}"
        if components.topic:
            srn += f".top_{components.topic}"

        return srn

    def validate(self, srn_string: str) -> bool:
        """
        Validate an SRN string without parsing it.

        Args:
            srn_string: SRN string to validate

        Returns:
            True if valid

        Raises:
            Various SRN exceptions if invalid
        """
        self.parse(srn_string)
        return True

    def parse_partial(self, srn_string: str) -> SRNComponents:
        """
        Parse a potentially partial SRN string.

        This allows parsing SRNs that may be missing optional components
        or may be provided in a shortened format for queries.

        Args:
            srn_string: Partial SRN string to parse

        Returns:
            Parsed SRN components (with None for missing optional parts)
        """
        # For now, use the same logic as parse
        # In the future, this could be extended to handle partial patterns
        return self.parse(srn_string)