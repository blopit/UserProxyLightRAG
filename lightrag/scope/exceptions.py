"""
Exception classes for the Scope Resource Name (SRN) system.

This module defines the exception hierarchy for SRN parsing, validation,
and scope resolution operations.
"""

from typing import Optional


class SRNError(Exception):
    """Base exception for all SRN-related errors."""

    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(message)
        self.error_code = error_code


class InvalidSRNFormatError(SRNError):
    """Raised when an SRN string has an invalid format."""

    def __init__(self, message: str, srn_string: Optional[str] = None):
        super().__init__(message, "INVALID_SRN_FORMAT")
        self.srn_string = srn_string


class InvalidWorkspaceError(SRNError):
    """Raised when the workspace component is invalid."""

    def __init__(self, message: str, workspace: Optional[str] = None):
        super().__init__(message, "INVALID_WORKSPACE")
        self.workspace = workspace


class InvalidSubjectTypeError(SRNError):
    """Raised when the subject type is not recognized."""

    def __init__(self, message: str, subject_type: Optional[str] = None):
        super().__init__(message, "INVALID_SUBJECT_TYPE")
        self.subject_type = subject_type


class InvalidIdentifierError(SRNError):
    """Raised when an identifier doesn't meet validation requirements."""

    def __init__(self, message: str, identifier: Optional[str] = None, identifier_type: Optional[str] = None):
        super().__init__(message, "INVALID_IDENTIFIER")
        self.identifier = identifier
        self.identifier_type = identifier_type


class ScopeResolutionError(SRNError):
    """Raised when scope resolution or inheritance fails."""

    def __init__(self, message: str, scope: Optional[str] = None):
        super().__init__(message, "SCOPE_RESOLUTION_ERROR")
        self.scope = scope