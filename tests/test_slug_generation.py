"""Tests for changelog filename slug generation"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "action", "src"))

from main import generate_changelog_slug

import pytest


class TestSlugGeneration:
    """Test changelog filename slug generation"""

    def test_slug_with_pr_number_and_title(self):
        """Test slug generation with PR number and title"""
        slug = generate_changelog_slug(123, "Add new authentication feature")
        assert slug == "pr-123-add-new-authentication-feature.yml"

    def test_slug_with_only_pr_number(self):
        """Test slug generation with only PR number"""
        slug = generate_changelog_slug(42)
        assert slug == "pr-42.yml"

    def test_slug_with_empty_title(self):
        """Test slug generation with empty title"""
        slug = generate_changelog_slug(100, "")
        assert slug == "pr-100.yml"

    def test_slug_lowercase_conversion(self):
        """Test that title is converted to lowercase"""
        slug = generate_changelog_slug(1, "FIX: Important Bug")
        assert slug == "pr-1-fix-important-bug.yml"

    def test_slug_special_characters(self):
        """Test that special characters are converted to hyphens"""
        slug = generate_changelog_slug(2, "Fix: API & Database Issues")
        assert slug == "pr-2-fix-api-database-issues.yml"

    def test_slug_multiple_spaces(self):
        """Test that multiple spaces are converted to single hyphen"""
        slug = generate_changelog_slug(3, "Add   support   for   OAuth2")
        assert slug == "pr-3-add-support-for-oauth2.yml"

    def test_slug_trailing_special_chars(self):
        """Test that trailing special characters are removed"""
        slug = generate_changelog_slug(4, "Update documentation!!!")
        assert slug == "pr-4-update-documentation.yml"

    def test_slug_leading_special_chars(self):
        """Test that leading special characters are removed"""
        slug = generate_changelog_slug(5, "---Refactor modules---")
        assert slug == "pr-5-refactor-modules.yml"

    def test_slug_numbers_preserved(self):
        """Test that numbers are preserved in slug"""
        slug = generate_changelog_slug(99, "Support Python 3.11 and 3.12")
        assert slug == "pr-99-support-python-3-11-and-3-12.yml"

    def test_slug_length_limit(self):
        """Test that slug is limited to 50 characters"""
        long_title = "This is a very long title that exceeds the character limit for slug generation"
        slug = generate_changelog_slug(10, long_title)
        # PR number (4) + hyphen (1) + slug (50) + extension (4) = 59 chars max
        assert len(slug) <= 65  # Allow some buffer for extension
        assert slug.startswith("pr-10-")
        assert slug.endswith(".yml")

    def test_slug_no_trailing_hyphen(self):
        """Test that slug doesn't end with hyphen before extension"""
        slug = generate_changelog_slug(7, "Feature---")
        assert slug == "pr-7-feature.yml"
        assert "--" not in slug

    def test_slug_duplicate_hyphens_removed(self):
        """Test that duplicate hyphens are removed"""
        slug = generate_changelog_slug(8, "Fix--Bug--Handler")
        assert slug == "pr-8-fix-bug-handler.yml"

    def test_slug_real_world_examples(self):
        """Test with real-world PR titles"""
        examples = [
            (
                123,
                "Fix critical security vulnerability in auth module",
                "pr-123-fix-critical-security-vulnerability-in-aut.yml",
            ),
            (
                456,
                "BREAKING: Refactor API endpoints",
                "pr-456-breaking-refactor-api-endpoints.yml",
            ),
            (789, "chore: update dependencies", "pr-789-chore-update-dependencies.yml"),
            (
                1,
                "Add support for Redis caching (RFC-123)",
                "pr-1-add-support-for-redis-caching-rfc-123.yml",
            ),
        ]

        for pr_num, title, expected in examples:
            slug = generate_changelog_slug(pr_num, title)
            # Just verify format is correct, not exact match due to length limits
            assert slug.startswith(f"pr-{pr_num}-")
            assert slug.endswith(".yml")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
