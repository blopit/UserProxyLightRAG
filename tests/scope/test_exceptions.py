"""Tests for SRN exception classes."""

import pytest
from lightrag.scope.exceptions import (
    SRNError,
    InvalidSRNFormatError,
    InvalidWorkspaceError,
    InvalidSubjectTypeError,
    InvalidIdentifierError,
    ScopeResolutionError,
)


class TestSRNError:
    """Test the base SRN exception class."""

    def test_basic_exception(self):
        """Test basic SRN exception creation."""
        error = SRNError("Test error")
        assert str(error) == "Test error"
        assert error.error_code is None

    def test_exception_with_error_code(self):
        """Test SRN exception with error code."""
        error = SRNError("Test error", "TEST_CODE")
        assert str(error) == "Test error"
        assert error.error_code == "TEST_CODE"


class TestInvalidSRNFormatError:
    """Test the InvalidSRNFormatError exception."""

    def test_basic_format_error(self):
        """Test basic format error creation."""
        error = InvalidSRNFormatError("Invalid format")
        assert str(error) == "Invalid format"
        assert error.error_code == "INVALID_SRN_FORMAT"
        assert error.srn_string is None

    def test_format_error_with_srn_string(self):
        """Test format error with SRN string."""
        srn = "invalid.srn.string"
        error = InvalidSRNFormatError("Invalid format", srn)
        assert str(error) == "Invalid format"
        assert error.error_code == "INVALID_SRN_FORMAT"
        assert error.srn_string == srn


class TestInvalidWorkspaceError:
    """Test the InvalidWorkspaceError exception."""

    def test_basic_workspace_error(self):
        """Test basic workspace error creation."""
        error = InvalidWorkspaceError("Invalid workspace")
        assert str(error) == "Invalid workspace"
        assert error.error_code == "INVALID_WORKSPACE"
        assert error.workspace is None

    def test_workspace_error_with_workspace(self):
        """Test workspace error with workspace value."""
        workspace = "invalid_workspace"
        error = InvalidWorkspaceError("Invalid workspace", workspace)
        assert str(error) == "Invalid workspace"
        assert error.error_code == "INVALID_WORKSPACE"
        assert error.workspace == workspace


class TestInvalidSubjectTypeError:
    """Test the InvalidSubjectTypeError exception."""

    def test_basic_subject_type_error(self):
        """Test basic subject type error creation."""
        error = InvalidSubjectTypeError("Invalid subject type")
        assert str(error) == "Invalid subject type"
        assert error.error_code == "INVALID_SUBJECT_TYPE"
        assert error.subject_type is None

    def test_subject_type_error_with_type(self):
        """Test subject type error with type value."""
        subject_type = "invalid_type"
        error = InvalidSubjectTypeError("Invalid subject type", subject_type)
        assert str(error) == "Invalid subject type"
        assert error.error_code == "INVALID_SUBJECT_TYPE"
        assert error.subject_type == subject_type


class TestInvalidIdentifierError:
    """Test the InvalidIdentifierError exception."""

    def test_basic_identifier_error(self):
        """Test basic identifier error creation."""
        error = InvalidIdentifierError("Invalid identifier")
        assert str(error) == "Invalid identifier"
        assert error.error_code == "INVALID_IDENTIFIER"
        assert error.identifier is None
        assert error.identifier_type is None

    def test_identifier_error_with_details(self):
        """Test identifier error with identifier and type."""
        identifier = "invalid@id"
        identifier_type = "subject_id"
        error = InvalidIdentifierError("Invalid identifier", identifier, identifier_type)
        assert str(error) == "Invalid identifier"
        assert error.error_code == "INVALID_IDENTIFIER"
        assert error.identifier == identifier
        assert error.identifier_type == identifier_type


class TestScopeResolutionError:
    """Test the ScopeResolutionError exception."""

    def test_basic_resolution_error(self):
        """Test basic scope resolution error creation."""
        error = ScopeResolutionError("Resolution failed")
        assert str(error) == "Resolution failed"
        assert error.error_code == "SCOPE_RESOLUTION_ERROR"
        assert error.scope is None

    def test_resolution_error_with_scope(self):
        """Test scope resolution error with scope value."""
        scope = "1.abc123.user.john"
        error = ScopeResolutionError("Resolution failed", scope)
        assert str(error) == "Resolution failed"
        assert error.error_code == "SCOPE_RESOLUTION_ERROR"
        assert error.scope == scope


class TestExceptionInheritance:
    """Test exception inheritance hierarchy."""

    def test_all_exceptions_inherit_from_srn_error(self):
        """Test that all exceptions inherit from SRNError."""
        assert issubclass(InvalidSRNFormatError, SRNError)
        assert issubclass(InvalidWorkspaceError, SRNError)
        assert issubclass(InvalidSubjectTypeError, SRNError)
        assert issubclass(InvalidIdentifierError, SRNError)
        assert issubclass(ScopeResolutionError, SRNError)

    def test_srn_error_inherits_from_exception(self):
        """Test that SRNError inherits from Exception."""
        assert issubclass(SRNError, Exception)