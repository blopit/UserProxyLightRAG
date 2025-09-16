"""Tests for scope context management."""

import pytest
from lightrag.scope.context import ScopeContext, ScopeResolver
from lightrag.scope.srn import SRNComponents, SubjectType
from lightrag.scope.exceptions import ScopeResolutionError, InvalidSRNFormatError


class TestScopeContext:
    """Test the ScopeContext class."""

    def test_init_with_srn_string(self):
        """Test initialization with SRN string."""
        srn = "1.abc12345abcd12345abc1234567890ab.user.johndoe"
        context = ScopeContext(srn)

        assert context.version == "1"
        assert context.workspace == "abc12345abcd12345abc1234567890ab"
        assert context.subject_type == SubjectType.USER
        assert context.subject_id == "johndoe"
        assert context.project is None
        assert context.thread is None
        assert context.topic is None

    def test_init_with_srn_components(self):
        """Test initialization with SRNComponents."""
        components = SRNComponents(
            version="1",
            workspace="def67890cdef67890cdef67890cdef67",
            subject_type=SubjectType.AGENT,
            subject_id="chatbot",
            project="research"
        )
        context = ScopeContext(components)

        assert context.version == "1"
        assert context.workspace == "def67890cdef67890cdef67890cdef67"
        assert context.subject_type == SubjectType.AGENT
        assert context.subject_id == "chatbot"
        assert context.project == "research"

    def test_init_with_invalid_type(self):
        """Test initialization with invalid type."""
        with pytest.raises(ValueError) as exc:
            ScopeContext(123)
        assert "must be a string or SRNComponents object" in str(exc.value)

    def test_to_dict(self):
        """Test converting to dictionary."""
        srn = "1.abc12345abcd12345abc1234567890ab.user.johndoe.proj_test"
        context = ScopeContext(srn)
        result = context.to_dict()

        expected = {
            "version": "1",
            "workspace": "abc12345abcd12345abc1234567890ab",
            "subject_type": "user",
            "subject_id": "johndoe",
            "project": "test"
        }
        assert result == expected

    def test_to_filter_dict(self):
        """Test converting to filter dictionary."""
        srn = "1.def67890cdef67890cdef67890cdef67.agent.bot.proj_ai.thr_chat.top_nlp"
        context = ScopeContext(srn)
        result = context.to_filter_dict()

        expected = {
            "workspace": "def67890cdef67890cdef67890cdef67",
            "subject_type": "agent",
            "subject_id": "bot",
            "project": "ai",
            "thread": "chat",
            "topic": "nlp"
        }
        assert result == expected

    def test_to_filter_dict_basic(self):
        """Test filter dictionary for basic SRN."""
        srn = "1.abc12345abcd12345abc1234567890ab.user.johndoe"
        context = ScopeContext(srn)
        result = context.to_filter_dict()

        expected = {
            "workspace": "abc12345abcd12345abc1234567890ab",
            "subject_type": "user",
            "subject_id": "johndoe"
        }
        assert result == expected

    def test_matches_scope(self):
        """Test scope matching."""
        srn1 = "1.abc12345abcd12345abc1234567890ab.user.johndoe"
        srn2 = "1.abc12345abcd12345abc1234567890ab.user.johndoe"
        srn3 = "1.abc12345abcd12345abc1234567890ab.user.janedoe"

        context1 = ScopeContext(srn1)
        context2 = ScopeContext(srn2)
        context3 = ScopeContext(srn3)

        assert context1.matches_scope(context2)
        assert not context1.matches_scope(context3)

    def test_is_parent_of(self):
        """Test parent-child relationship checking."""
        parent_srn = "1.abc12345abcd12345abc1234567890ab.user.johndoe"
        child_srn = "1.abc12345abcd12345abc1234567890ab.user.johndoe.proj_research"
        unrelated_srn = "1.abc12345abcd12345abc1234567890ab.user.janedoe.proj_research"

        parent_context = ScopeContext(parent_srn)
        child_context = ScopeContext(child_srn)
        unrelated_context = ScopeContext(unrelated_srn)

        assert parent_context.is_parent_of(child_context)
        assert not parent_context.is_parent_of(unrelated_context)
        assert not child_context.is_parent_of(parent_context)

    def test_is_child_of(self):
        """Test child-parent relationship checking."""
        parent_srn = "1.abc12345abcd12345abc1234567890ab.user.johndoe"
        child_srn = "1.abc12345abcd12345abc1234567890ab.user.johndoe.proj_research"

        parent_context = ScopeContext(parent_srn)
        child_context = ScopeContext(child_srn)

        assert child_context.is_child_of(parent_context)
        assert not parent_context.is_child_of(child_context)

    def test_get_parent_scope(self):
        """Test getting parent scope."""
        # Test with topic
        topic_srn = "1.abc12345abcd12345abc1234567890ab.user.john.proj_ai.thr_chat.top_nlp"
        topic_context = ScopeContext(topic_srn)
        parent = topic_context.get_parent_scope()

        assert parent is not None
        assert parent.topic is None
        assert parent.thread == "chat"
        assert parent.project == "ai"

        # Test with thread
        thread_srn = "1.abc12345abcd12345abc1234567890ab.user.john.proj_ai.thr_chat"
        thread_context = ScopeContext(thread_srn)
        parent = thread_context.get_parent_scope()

        assert parent is not None
        assert parent.thread is None
        assert parent.project == "ai"

        # Test with project
        project_srn = "1.abc12345abcd12345abc1234567890ab.user.john.proj_ai"
        project_context = ScopeContext(project_srn)
        parent = project_context.get_parent_scope()

        assert parent is not None
        assert parent.project is None

        # Test with base scope
        base_srn = "1.abc12345abcd12345abc1234567890ab.user.john"
        base_context = ScopeContext(base_srn)
        parent = base_context.get_parent_scope()

        assert parent is None

    def test_get_scope_depth(self):
        """Test scope depth calculation."""
        base_srn = "1.abc12345abcd12345abc1234567890ab.user.john"
        project_srn = "1.abc12345abcd12345abc1234567890ab.user.john.proj_ai"
        thread_srn = "1.abc12345abcd12345abc1234567890ab.user.john.proj_ai.thr_chat"
        topic_srn = "1.abc12345abcd12345abc1234567890ab.user.john.proj_ai.thr_chat.top_nlp"

        assert ScopeContext(base_srn).get_scope_depth() == 0
        assert ScopeContext(project_srn).get_scope_depth() == 1
        assert ScopeContext(thread_srn).get_scope_depth() == 2
        assert ScopeContext(topic_srn).get_scope_depth() == 3

    def test_string_representations(self):
        """Test string representations."""
        srn = "1.abc12345abcd12345abc1234567890ab.user.johndoe"
        context = ScopeContext(srn)

        assert str(context) == srn
        assert repr(context) == f"ScopeContext('{srn}')"

    def test_equality_and_hashing(self):
        """Test equality and hashing."""
        srn1 = "1.abc12345abcd12345abc1234567890ab.user.johndoe"
        srn2 = "1.abc12345abcd12345abc1234567890ab.user.johndoe"
        srn3 = "1.abc12345abcd12345abc1234567890ab.user.janedoe"

        context1 = ScopeContext(srn1)
        context2 = ScopeContext(srn2)
        context3 = ScopeContext(srn3)

        assert context1 == context2
        assert context1 != context3
        assert hash(context1) == hash(context2)
        assert hash(context1) != hash(context3)

        # Test with non-ScopeContext object
        assert context1 != "not a scope context"


class TestScopeResolver:
    """Test the ScopeResolver class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.resolver = ScopeResolver()

    def test_resolve_inheritance(self):
        """Test resolving inheritance chain."""
        full_srn = "1.abc12345abcd12345abc1234567890ab.user.john.proj_ai.thr_chat.top_nlp"
        context = ScopeContext(full_srn)
        inheritance = self.resolver.resolve_inheritance(context)

        assert len(inheritance) == 4
        assert inheritance[0].get_scope_depth() == 3  # Full scope
        assert inheritance[1].get_scope_depth() == 2  # Without topic
        assert inheritance[2].get_scope_depth() == 1  # Without thread
        assert inheritance[3].get_scope_depth() == 0  # Base scope

    def test_find_matching_scopes(self):
        """Test finding scopes with pattern matching."""
        scopes = [
            ScopeContext("1.abc12345abcd12345abc1234567890ab.user.john"),
            ScopeContext("1.abc12345abcd12345abc1234567890ab.user.jane"),
            ScopeContext("1.abc12345abcd12345abc1234567890ab.agent.bot1"),
            ScopeContext("1.def67890cdef67890cdef67890cdef67.user.alice"),
        ]

        # Test wildcard matching
        matches = self.resolver.find_matching_scopes("*.user.*", scopes)
        assert len(matches) == 3

        # Test specific workspace matching
        matches = self.resolver.find_matching_scopes("1.abc12345abcd12345abc1234567890ab.*", scopes)
        assert len(matches) == 3

        # Test exact matching
        matches = self.resolver.find_matching_scopes("1.abc12345abcd12345abc1234567890ab.user.john", scopes)
        assert len(matches) == 1

    def test_get_common_parent(self):
        """Test finding common parent scope."""
        scopes = [
            ScopeContext("1.abc12345abcd12345abc1234567890ab.user.john.proj_ai.thr_chat1"),
            ScopeContext("1.abc12345abcd12345abc1234567890ab.user.john.proj_ai.thr_chat2"),
            ScopeContext("1.abc12345abcd12345abc1234567890ab.user.john.proj_ai.thr_chat3"),
        ]

        common_parent = self.resolver.get_common_parent(scopes)
        assert common_parent is not None
        assert common_parent.project == "ai"
        assert common_parent.thread is None

    def test_get_common_parent_no_common(self):
        """Test finding common parent with no common parent."""
        scopes = [
            ScopeContext("1.abc12345abcd12345abc1234567890ab.user.john"),
            ScopeContext("1.def67890cdef67890cdef67890cdef67.user.jane"),
        ]

        common_parent = self.resolver.get_common_parent(scopes)
        assert common_parent is None

    def test_get_common_parent_single_scope(self):
        """Test finding common parent with single scope."""
        scopes = [
            ScopeContext("1.abc12345abcd12345abc1234567890ab.user.john.proj_ai"),
        ]

        common_parent = self.resolver.get_common_parent(scopes)
        assert common_parent is not None
        assert common_parent.project is None

    def test_merge_scope_filters(self):
        """Test merging scope filters."""
        scopes = [
            ScopeContext("1.abc12345abcd12345abc1234567890ab.user.john.proj_ai"),
            ScopeContext("1.abc12345abcd12345abc1234567890ab.user.jane.proj_ai"),
            ScopeContext("1.abc12345abcd12345abc1234567890ab.user.bob.proj_research"),
        ]

        merged = self.resolver.merge_scope_filters(scopes)

        assert merged["workspace"] == "abc12345abcd12345abc1234567890ab"
        assert merged["subject_type"] == "user"
        assert "subject_id__in" in merged
        assert set(merged["subject_id__in"]) == {"john", "jane", "bob"}
        assert "project__in" in merged
        assert set(merged["project__in"]) == {"ai", "research"}

    def test_merge_scope_filters_single(self):
        """Test merging single scope filter."""
        scopes = [
            ScopeContext("1.abc12345abcd12345abc1234567890ab.user.john.proj_ai"),
        ]

        merged = self.resolver.merge_scope_filters(scopes)
        expected = scopes[0].to_filter_dict()

        assert merged == expected

    def test_create_scope_from_workspace(self):
        """Test creating scope from workspace."""
        workspace = "abc12345abcd12345abc1234567890ab"
        scope = self.resolver.create_scope_from_workspace(workspace)

        assert scope.workspace == workspace
        assert scope.subject_type == SubjectType.SYSTEM
        assert scope.subject_id == "default"

    def test_create_scope_from_workspace_custom(self):
        """Test creating scope from workspace with custom defaults."""
        workspace = "def67890cdef67890cdef67890cdef67"
        scope = self.resolver.create_scope_from_workspace(
            workspace,
            default_subject_type="user",
            default_subject_id="migration"
        )

        assert scope.workspace == workspace
        assert scope.subject_type == SubjectType.USER
        assert scope.subject_id == "migration"

    def test_create_scope_from_workspace_invalid(self):
        """Test creating scope from invalid workspace."""
        with pytest.raises(ScopeResolutionError) as exc:
            self.resolver.create_scope_from_workspace("invalid_workspace")
        assert "Invalid workspace format" in str(exc.value)

    def test_extract_workspace_from_scope(self):
        """Test extracting workspace from scope."""
        workspace = "abc12345abcd12345abc1234567890ab"
        srn = f"1.{workspace}.user.john.proj_ai"
        scope = ScopeContext(srn)

        extracted = self.resolver.extract_workspace_from_scope(scope)
        assert extracted == workspace