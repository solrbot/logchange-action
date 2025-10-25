"""Integration tests for logchange action workflow"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "action", "src"))

import pytest
from changelog_validator import ChangelogValidator


class TestIntegration:
    """Integration tests for complete workflows"""

    def test_workflow_valid_entry_found(self):
        """Test complete workflow when valid entry exists"""
        validator = ChangelogValidator()

        # Simulate finding a valid changelog entry
        changelog_content = """
title: Add authentication support
type: added
authors:
  - name: John Developer
    nick: john
    url: https://github.com/john
"""

        is_valid, errors = validator.validate(changelog_content)

        assert is_valid is True
        assert len(errors) == 0

    def test_workflow_missing_entry(self):
        """Test workflow when changelog entry is missing"""
        validator = ChangelogValidator()

        # Empty or no entry found
        is_valid, errors = validator.validate("")

        assert is_valid is False
        assert any("empty" in str(e).lower() for e in errors)

    def test_workflow_validation_failure(self):
        """Test workflow when entry validation fails"""
        validator = ChangelogValidator(mandatory_fields=["title", "type", "authors"])

        # Missing required fields
        incomplete_entry = """
title: Incomplete entry
type: added
"""

        is_valid, errors = validator.validate(incomplete_entry)

        assert is_valid is False
        assert any("mandatory" in str(e).lower() for e in errors)

    def test_workflow_with_custom_rules(self):
        """Test workflow with custom validation rules"""
        validator = ChangelogValidator(
            mandatory_fields=["title", "type"],
            forbidden_fields=["draft"],
            changelog_types=["feature", "bugfix", "security"],
        )

        # Valid with custom rules
        entry = """
title: Security patch
type: security
"""

        is_valid, errors = validator.validate(entry)
        assert is_valid is True

        # Invalid: forbidden field present
        entry_with_draft = """
title: WIP feature
type: feature
draft: true
"""

        is_valid, errors = validator.validate(entry_with_draft)
        assert is_valid is False
        assert any("forbidden" in str(e).lower() for e in errors)

    def test_workflow_legacy_changelog_detection(self):
        """Test detection of legacy changelog format"""
        from legacy_changelog_handler import LegacyChangelogHandler

        handler = LegacyChangelogHandler(
            legacy_changelog_paths=["CHANGELOG.md", "HISTORY.txt"]
        )

        # Test legacy paths are configured
        assert "CHANGELOG.md" in handler.legacy_changelog_paths
        assert "HISTORY.txt" in handler.legacy_changelog_paths

    def test_pr_metadata_extraction_workflow(self):
        """Test PR metadata extraction in workflow"""
        from pr_metadata_extractor import PRMetadataExtractor

        extractor = PRMetadataExtractor(
            external_issue_regex=r"JIRA-(\d+)",
            external_issue_url_template="https://jira.example.com/browse/JIRA-{id}",
        )

        # Test extracting metadata from PR info
        pr_info = {
            "number": 42,
            "title": "Fix JIRA-123 and JIRA-456",
            "body": "This fixes issues #789 and #790",
        }

        pr_number = extractor.extract_merge_request_number(pr_info)
        assert pr_number == 42

        # Test issue extraction
        issues = extractor.extract_github_issues(pr_info.get("body", ""))
        assert 789 in issues
        assert 790 in issues

    def test_complete_changelog_entry_generation(self):
        """Test complete flow from diff to changelog entry"""
        from changelog_validator import ChangelogValidator

        validator = ChangelogValidator()

        # Simulate a generated changelog entry
        generated_entry = """
title: Add webhook support for external integrations
type: added
authors:
  - name: Alice Developer
    nick: alice-dev
    url: https://github.com/alice-dev
modules:
  - api
  - webhooks
"""

        # Validate the generated entry
        is_valid, errors = validator.validate(generated_entry)

        assert is_valid is True
        assert len(errors) == 0


class TestErrorHandling:
    """Test error handling in workflows"""

    def test_invalid_yaml_handling(self):
        """Test handling of invalid YAML"""
        validator = ChangelogValidator()

        invalid_yaml = """
title: Test
  invalid: indentation:
"""

        is_valid, errors = validator.validate(invalid_yaml)

        assert is_valid is False
        assert any("yaml" in str(e).lower() for e in errors)

    def test_empty_entry_handling(self):
        """Test handling of empty entry"""
        validator = ChangelogValidator()

        is_valid, errors = validator.validate("")

        assert is_valid is False
        assert any("empty" in str(e).lower() for e in errors)

    def test_malformed_authors_handling(self):
        """Test handling of malformed authors field"""
        validator = ChangelogValidator()

        bad_authors = """
title: Test
type: added
authors:
  - just_a_string
"""

        is_valid, errors = validator.validate(bad_authors)

        assert is_valid is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
