"""Tests for SRN parser and validator."""

import pytest
import unicodedata
from lightrag.scope.srn import SRNParser, SRNValidator, SRNComponents, SubjectType
from lightrag.scope.exceptions import (
    InvalidSRNFormatError,
    InvalidWorkspaceError,
    InvalidSubjectTypeError,
    InvalidIdentifierError,
)


class TestSubjectType:
    """Test the SubjectType enum."""

    def test_all_subject_types(self):
        """Test all valid subject types."""
        assert SubjectType.USER == "user"
        assert SubjectType.AGENT == "agent"
        assert SubjectType.WORKSPACE == "workspace"
        assert SubjectType.CONTACT == "contact"
        assert SubjectType.PROJECT == "project"
        assert SubjectType.SYSTEM == "system"

    def test_subject_type_from_string(self):
        """Test creating SubjectType from string."""
        assert SubjectType("user") == SubjectType.USER
        assert SubjectType("agent") == SubjectType.AGENT


class TestSRNComponents:
    """Test the SRNComponents dataclass."""

    def test_basic_components(self):
        """Test basic SRN components creation."""
        components = SRNComponents(
            version="1",
            workspace="abc12345abcd12345abc1234567890ab",
            subject_type=SubjectType.USER,
            subject_id="johndoe"
        )
        assert components.version == "1"
        assert components.workspace == "abc12345abcd12345abc1234567890ab"
        assert components.subject_type == SubjectType.USER
        assert components.subject_id == "johndoe"
        assert components.project is None
        assert components.thread is None
        assert components.topic is None

    def test_full_components(self):
        """Test SRN components with all optional fields."""
        components = SRNComponents(
            version="1",
            workspace="def67890cdef67890cdef67890cdef67",
            subject_type=SubjectType.AGENT,
            subject_id="chatbot_v2",
            project="research",
            thread="discussion1",
            topic="ai_models"
        )
        assert components.project == "research"
        assert components.thread == "discussion1"
        assert components.topic == "ai_models"

    def test_to_dict(self):
        """Test converting components to dictionary."""
        components = SRNComponents(
            version="1",
            workspace="abc12345abcd12345abc1234567890ab",
            subject_type=SubjectType.USER,
            subject_id="johndoe",
            project="test"
        )
        result = components.to_dict()
        expected = {
            "version": "1",
            "workspace": "abc12345abcd12345abc1234567890ab",
            "subject_type": "user",
            "subject_id": "johndoe",
            "project": "test"
        }
        assert result == expected


class TestSRNValidator:
    """Test the SRN validator."""

    def test_validate_version_valid(self):
        """Test valid version validation."""
        assert SRNValidator.validate_version("1") is True

    def test_validate_version_invalid(self):
        """Test invalid version validation."""
        with pytest.raises(InvalidSRNFormatError) as exc:
            SRNValidator.validate_version("2")
        assert "Invalid version '2'" in str(exc.value)

    def test_validate_workspace_valid(self):
        """Test valid workspace validation."""
        valid_workspace = "abc12345abcd12345abc1234567890ab"
        assert SRNValidator.validate_workspace_uuid(valid_workspace) is True

    def test_validate_workspace_invalid_length(self):
        """Test workspace validation with invalid length."""
        with pytest.raises(InvalidWorkspaceError) as exc:
            SRNValidator.validate_workspace_uuid("short")
        assert "32 lowercase hexadecimal characters" in str(exc.value)

    def test_validate_workspace_invalid_characters(self):
        """Test workspace validation with invalid characters."""
        with pytest.raises(InvalidWorkspaceError) as exc:
            SRNValidator.validate_workspace_uuid("xyz12345abcd12345abc1234567890ab")
        assert "32 lowercase hexadecimal characters" in str(exc.value)

    def test_validate_subject_type_valid(self):
        """Test valid subject type validation."""
        for subject_type in ["user", "agent", "workspace", "contact", "project", "system"]:
            assert SRNValidator.validate_subject_type(subject_type) is True

    def test_validate_subject_type_invalid(self):
        """Test invalid subject type validation."""
        with pytest.raises(InvalidSubjectTypeError) as exc:
            SRNValidator.validate_subject_type("invalid")
        assert "Invalid subject type 'invalid'" in str(exc.value)

    def test_validate_identifier_valid(self):
        """Test valid identifier validation."""
        valid_identifiers = [
            "johndoe",
            "user_123",
            "test-id",
            "a",
            "1",
            "_",
            "-",
            "a" * 63  # Maximum length
        ]
        for identifier in valid_identifiers:
            assert SRNValidator.validate_identifier(identifier) is True

    def test_validate_identifier_empty(self):
        """Test empty identifier validation."""
        with pytest.raises(InvalidIdentifierError) as exc:
            SRNValidator.validate_identifier("")
        assert "cannot be empty" in str(exc.value)

    def test_validate_identifier_too_long(self):
        """Test identifier that's too long."""
        long_identifier = "a" * 64  # Too long
        with pytest.raises(InvalidIdentifierError) as exc:
            SRNValidator.validate_identifier(long_identifier)
        assert "1-63 characters" in str(exc.value)

    def test_validate_identifier_invalid_characters(self):
        """Test identifier with invalid characters."""
        invalid_identifiers = [
            "user@domain",
            "user.name",
            "user name",
            "user#123",
            "USER",  # Uppercase not allowed
        ]
        for identifier in invalid_identifiers:
            with pytest.raises(InvalidIdentifierError):
                SRNValidator.validate_identifier(identifier)


class TestSRNParser:
    """Test the SRN parser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = SRNParser()

    def test_canonicalize_basic(self):
        """Test basic canonicalization."""
        result = self.parser.canonicalize("Test.String")
        assert result == "test.string"

    def test_canonicalize_unicode(self):
        """Test Unicode canonicalization."""
        # Test with Unicode normalization
        unicode_str = "café"  # e with acute accent
        result = self.parser.canonicalize(unicode_str)
        assert result == unicode_str.lower()
        assert unicodedata.is_normalized('NFC', result)

    def test_canonicalize_whitespace(self):
        """Test whitespace handling in canonicalization."""
        result = self.parser.canonicalize("  test.string  ")
        assert result == "test.string"

    def test_canonicalize_empty(self):
        """Test canonicalization with empty string."""
        with pytest.raises(InvalidSRNFormatError) as exc:
            self.parser.canonicalize("")
        assert "cannot be empty" in str(exc.value)

    def test_parse_basic_srn(self):
        """Test parsing a basic SRN."""
        srn = "1.abc12345abcd12345abc1234567890ab.user.johndoe"
        components = self.parser.parse(srn)

        assert components.version == "1"
        assert components.workspace == "abc12345abcd12345abc1234567890ab"
        assert components.subject_type == SubjectType.USER
        assert components.subject_id == "johndoe"
        assert components.project is None
        assert components.thread is None
        assert components.topic is None

    def test_parse_full_srn(self):
        """Test parsing a full SRN with all optional components."""
        srn = "1.def67890cdef67890cdef67890cdef67.agent.chatbot_v2.proj_research.thr_discussion1.top_ai_models"
        components = self.parser.parse(srn)

        assert components.version == "1"
        assert components.workspace == "def67890cdef67890cdef67890cdef67"
        assert components.subject_type == SubjectType.AGENT
        assert components.subject_id == "chatbot_v2"
        assert components.project == "research"
        assert components.thread == "discussion1"
        assert components.topic == "ai_models"

    def test_parse_partial_srn_with_project(self):
        """Test parsing SRN with only project component."""
        srn = "1.123456789012345678901234567890ab.user.alice.proj_research"
        components = self.parser.parse(srn)

        assert components.project == "research"
        assert components.thread is None
        assert components.topic is None

    def test_parse_partial_srn_with_project_and_thread(self):
        """Test parsing SRN with project and thread components."""
        srn = "1.fedcba0987654321fedcba0987654321.user.bob.proj_dev.thr_sprint1"
        components = self.parser.parse(srn)

        assert components.project == "dev"
        assert components.thread == "sprint1"
        assert components.topic is None

    def test_parse_case_insensitive(self):
        """Test that parsing is case insensitive."""
        srn = "1.ABC12345ABCD12345ABC1234567890AB.USER.JOHNDOE"
        components = self.parser.parse(srn)

        # Should be converted to lowercase
        assert components.workspace == "abc12345abcd12345abc1234567890ab"
        assert components.subject_type == SubjectType.USER
        assert components.subject_id == "johndoe"

    def test_parse_invalid_format(self):
        """Test parsing with invalid format."""
        invalid_srns = [
            "",
            "invalid",
            "1.short.user.john",  # Invalid workspace
            "2.abc12345abcd12345abc1234567890ab.user.john",  # Invalid version
            "1.abc12345abcd12345abc1234567890ab.invalid.john",  # Invalid subject type
            "1.abc12345abcd12345abc1234567890ab.user.",  # Empty subject_id
            "1.abc12345abcd12345abc1234567890ab.user.john.invalid_segment",  # Invalid segment format
        ]

        for srn in invalid_srns:
            with pytest.raises((InvalidSRNFormatError, InvalidWorkspaceError, InvalidSubjectTypeError, InvalidIdentifierError)):
                self.parser.parse(srn)

    def test_to_string_basic(self):
        """Test converting components to string."""
        components = SRNComponents(
            version="1",
            workspace="abc12345abcd12345abc1234567890ab",
            subject_type=SubjectType.USER,
            subject_id="johndoe"
        )
        result = self.parser.to_string(components)
        expected = "1.abc12345abcd12345abc1234567890ab.user.johndoe"
        assert result == expected

    def test_to_string_full(self):
        """Test converting full components to string."""
        components = SRNComponents(
            version="1",
            workspace="def67890cdef67890cdef67890cdef67",
            subject_type=SubjectType.AGENT,
            subject_id="chatbot_v2",
            project="research",
            thread="discussion1",
            topic="ai_models"
        )
        result = self.parser.to_string(components)
        expected = "1.def67890cdef67890cdef67890cdef67.agent.chatbot_v2.proj_research.thr_discussion1.top_ai_models"
        assert result == expected

    def test_to_string_partial(self):
        """Test converting partial components to string."""
        components = SRNComponents(
            version="1",
            workspace="123456789012345678901234567890ab",
            subject_type=SubjectType.USER,
            subject_id="alice",
            project="research"
        )
        result = self.parser.to_string(components)
        expected = "1.123456789012345678901234567890ab.user.alice.proj_research"
        assert result == expected

    def test_roundtrip_conversion(self):
        """Test that parsing and converting back yields the same result."""
        original_srns = [
            "1.abc12345abcd12345abc1234567890ab.user.johndoe",
            "1.def67890cdef67890cdef67890cdef67.agent.chatbot_v2.proj_research",
            "1.123456789012345678901234567890ab.user.alice.proj_research.thr_discussion1",
            "1.fedcba0987654321fedcba0987654321.user.bob.proj_dev.thr_sprint1.top_nlp"
        ]

        for srn in original_srns:
            components = self.parser.parse(srn)
            result = self.parser.to_string(components)
            assert result == srn

    def test_validate_valid_srn(self):
        """Test validation of valid SRN."""
        valid_srn = "1.abc12345abcd12345abc1234567890ab.user.johndoe"
        assert self.parser.validate(valid_srn) is True

    def test_validate_invalid_srn(self):
        """Test validation of invalid SRN."""
        invalid_srn = "invalid.srn.format"
        with pytest.raises(InvalidSRNFormatError):
            self.parser.validate(invalid_srn)

    def test_parse_partial_method(self):
        """Test the parse_partial method."""
        srn = "1.abc12345abcd12345abc1234567890ab.user.johndoe.proj_test"
        components = self.parser.parse_partial(srn)

        assert components.version == "1"
        assert components.workspace == "abc12345abcd12345abc1234567890ab"
        assert components.subject_type == SubjectType.USER
        assert components.subject_id == "johndoe"
        assert components.project == "test"