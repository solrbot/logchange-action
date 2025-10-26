"""Tests for legacy changelog handler"""

import os
import sys

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "action", "src"))

import pytest
from managed_changelog_handler import ManagedChangelogHandler


class TestManagedChangelogHandler:
    """Test legacy changelog detection and conversion"""

    @pytest.fixture
    def handler(self):
        """Create handler instance with default paths enabled for testing"""
        return ManagedChangelogHandler(
            [
                "CHANGELOG.md",
                "CHANGELOG.txt",
                "CHANGES.md",
                "CHANGES.txt",
                "HISTORY.md",
                "HISTORY.txt",
                "NEWS.md",
                "NEWS.txt",
                "RELEASES.md",
                "RELEASES.txt",
            ]
        )

    def test_disabled_by_default(self):
        """Test that handler is disabled when initialized with empty paths"""
        handler = ManagedChangelogHandler([])
        assert handler.is_enabled is False

    def test_disabled_handler_returns_empty(self):
        """Test that disabled handler returns no files"""
        handler = ManagedChangelogHandler([])
        pr_files = ["src/main.py", "CHANGELOG.md", "README.md"]
        managed_files = handler.find_managed_changelog_files(pr_files)
        assert managed_files == []

    def test_disabled_handler_with_none(self):
        """Test that handler with None paths is disabled"""
        handler = ManagedChangelogHandler(None)
        assert handler.is_enabled is False
        assert handler.find_managed_changelog_files(["CHANGELOG.md"]) == []

    def test_find_managed_files_exact_match(self, handler):
        """Test finding legacy files with exact name match"""
        pr_files = ["src/main.py", "CHANGELOG.md", "README.md"]
        managed_files = handler.find_managed_changelog_files(pr_files)
        assert "CHANGELOG.md" in managed_files

    def test_find_multiple_managed_files(self, handler):
        """Test finding multiple legacy changelog files"""
        pr_files = ["src/main.py", "CHANGELOG.md", "HISTORY.txt", "README.md"]
        managed_files = handler.find_managed_changelog_files(pr_files)
        assert len(managed_files) == 2
        assert "CHANGELOG.md" in managed_files
        assert "HISTORY.txt" in managed_files

    def test_find_no_managed_files(self, handler):
        """Test when no legacy files are present"""
        pr_files = ["src/main.py", "README.md", "docs/index.md"]
        managed_files = handler.find_managed_changelog_files(pr_files)
        assert len(managed_files) == 0

    def test_find_managed_files_with_paths(self, handler):
        """Test finding legacy files in subdirectories"""
        pr_files = ["src/main.py", "docs/CHANGELOG.md", "docs/README.md"]
        custom_handler = ManagedChangelogHandler(["docs/CHANGELOG.md"])
        managed_files = custom_handler.find_managed_changelog_files(pr_files)
        assert "docs/CHANGELOG.md" in managed_files

    def test_extract_changelog_entry_from_diff(self, handler):
        """Test extracting changelog entry from diff"""
        diff = """diff --git a/CHANGELOG.md b/CHANGELOG.md
index abc123..def456 100644
--- a/CHANGELOG.md
+++ b/CHANGELOG.md
@@ -1,3 +1,7 @@
+## Version 1.2.0 - 2024-10-24
+
+### Added
+- New feature: Webhook support

 ## Version 1.1.0 - 2024-09-10
"""
        entry = handler.extract_changelog_entry_from_diff(diff)
        assert entry is not None
        assert "Version 1.2.0" in entry
        assert "Webhook support" in entry

    def test_extract_changelog_no_added_lines(self, handler):
        """Test when there are no added lines in diff"""
        diff = """diff --git a/CHANGELOG.md b/CHANGELOG.md
index abc123..def456 100644
--- a/CHANGELOG.md
+++ b/CHANGELOG.md
@@ -1,3 +1,3 @@
 ## Version 1.1.0

-Old text
+New text
"""
        entry = handler.extract_changelog_entry_from_diff(diff)
        assert entry is not None
        assert "New text" in entry
        assert "Old text" not in entry

    def test_detect_managed_entry_type_markdown(self, handler):
        """Test detecting markdown-style changelog"""
        entry = "## Version 1.2.0\n### Added\n- New feature"
        entry_type = handler.detect_managed_entry_type(entry)
        assert entry_type == "markdown"

    def test_detect_managed_entry_type_unreleased(self, handler):
        """Test detecting 'Unreleased' section"""
        entry = "## Unreleased\n### Added\n- New feature"
        entry_type = handler.detect_managed_entry_type(entry)
        assert entry_type == "unreleased"

    def test_detect_managed_entry_type_plain_text(self, handler):
        """Test detecting plain text list format"""
        entry = "- Fixed bug in authentication\n- Improved performance\n- Updated docs"
        entry_type = handler.detect_managed_entry_type(entry)
        assert entry_type == "plain_text"

    def test_detect_managed_entry_type_other(self, handler):
        """Test detecting unknown entry type"""
        entry = "Some random text without structure"
        entry_type = handler.detect_managed_entry_type(entry)
        assert entry_type == "other"

    def test_extract_version_and_date_from_managed(self, handler):
        """Test extracting version and date"""
        entry = "## Version 1.2.3 - 2024-10-24\n### Added\n- Feature"
        version, date = handler.extract_version_and_date_from_managed(entry)
        assert version == "1.2.3"
        assert date == "2024-10-24"

    def test_extract_version_without_date(self, handler):
        """Test extracting version without date"""
        entry = "## 1.2.3\n### Added\n- Feature"
        version, date = handler.extract_version_and_date_from_managed(entry)
        assert version == "1.2.3"
        assert date is None

    def test_extract_version_with_prerelease(self, handler):
        """Test extracting version with prerelease"""
        entry = "## 1.2.0-beta.1 - 2024-10-24"
        version, date = handler.extract_version_and_date_from_managed(entry)
        assert version == "1.2.0-beta.1"
        assert date == "2024-10-24"

    def test_extract_version_not_found(self, handler):
        """Test when no version is found"""
        entry = "This is just some text without version"
        version, date = handler.extract_version_and_date_from_managed(entry)
        assert version is None
        assert date is None

    def test_build_managed_context(self, handler):
        """Test building context about legacy entry"""
        entry = "## Version 1.2.0 - 2024-10-24\n\n### Added\n- Feature 1\n- Feature 2"
        context = handler.build_managed_context(entry)

        assert context["type"] == "markdown"
        assert context["version"] == "1.2.0"
        assert context["date"] == "2024-10-24"
        assert context["line_count"] > 0
        assert context["char_count"] > 0
        assert "Version 1.2.0" in context["summary"]

    def test_create_managed_conversion_prompt(self, handler):
        """Test creating conversion prompt"""
        entry = "## Version 1.2.0\n### Added\n- New webhook support"
        pr_info = {"title": "Add webhook integration"}
        context = handler.build_managed_context(entry)

        prompt = handler.create_managed_conversion_prompt(entry, pr_info, context)

        assert "legacy" in prompt.lower()
        assert "convert" in prompt.lower()
        assert "logchange" in prompt.lower()
        assert entry in prompt
        assert "Add webhook integration" in prompt

    def test_should_fail_on_managed_logchange_conflict_true(self, handler):
        """Test conflict detection when both legacy and logchange exist"""
        managed_files = ["CHANGELOG.md"]
        logchange_files = ["changelog/unreleased/change.yml"]

        is_conflict = handler.should_fail_on_managed_logchange_conflict(managed_files, logchange_files)
        assert is_conflict is True

    def test_should_fail_on_managed_logchange_conflict_false_legacy_only(self, handler):
        """Test no conflict when only legacy exists"""
        managed_files = ["CHANGELOG.md"]
        logchange_files = []

        is_conflict = handler.should_fail_on_managed_logchange_conflict(managed_files, logchange_files)
        assert is_conflict is False

    def test_should_fail_on_managed_logchange_conflict_false_logchange_only(self, handler):
        """Test no conflict when only logchange exists"""
        managed_files = []
        logchange_files = ["changelog/unreleased/change.yml"]

        is_conflict = handler.should_fail_on_managed_logchange_conflict(managed_files, logchange_files)
        assert is_conflict is False

    def test_should_fail_on_managed_logchange_conflict_false_neither(self, handler):
        """Test no conflict when neither exists"""
        managed_files = []
        logchange_files = []

        is_conflict = handler.should_fail_on_managed_logchange_conflict(managed_files, logchange_files)
        assert is_conflict is False

    def test_extract_bullet_points(self, handler):
        """Test extracting bullet points from changelog"""
        diff = """diff --git a/CHANGELOG.md b/CHANGELOG.md
@@ -1,5 +1,7 @@
+## Unreleased
+
+- Fixed: Database connection pooling
+- Added: API rate limiting
"""
        entry = handler.extract_changelog_entry_from_diff(diff)
        assert "Database connection pooling" in entry
        assert "API rate limiting" in entry

    def test_entry_context_line_count(self, handler):
        """Test line count in context"""
        entry = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        context = handler.build_managed_context(entry)
        assert context["line_count"] == 5

    def test_entry_context_summary_truncation(self, handler):
        """Test summary truncation"""
        long_entry = "A" * 200  # 200 characters
        context = handler.build_managed_context(long_entry)
        # Summary should be truncated to ~100 chars with ellipsis
        assert len(context["summary"]) < len(long_entry)
        assert context["summary"].endswith("...")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
