"""Tests for PR metadata extractor"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'action', 'src'))

from pr_metadata_extractor import PRMetadataExtractor

import pytest


class TestPRMetadataExtractor:
    """Test PR metadata extraction"""

    @pytest.fixture
    def basic_extractor(self):
        """Create basic extractor without external issues"""
        return PRMetadataExtractor()

    @pytest.fixture
    def jira_extractor(self):
        """Create extractor with JIRA support"""
        return PRMetadataExtractor(
            external_issue_regex=r'JIRA-(\d+)',
            external_issue_url_template='https://jira.example.com/browse/JIRA-{id}'
        )

    def test_extract_merge_request_number(self, basic_extractor):
        """Test extracting PR number"""
        pr_info = {'number': 123}
        pr_number = basic_extractor.extract_merge_request_number(pr_info)
        assert pr_number == 123

    def test_extract_merge_request_number_none(self, basic_extractor):
        """Test when PR number is missing"""
        pr_info = {}
        pr_number = basic_extractor.extract_merge_request_number(pr_info)
        assert pr_number is None

    def test_extract_github_issues_simple(self, basic_extractor):
        """Test extracting simple issue references"""
        text = "This fixes #123 and also #456"
        issues = basic_extractor.extract_github_issues(text)
        assert 123 in issues
        assert 456 in issues
        assert len(issues) == 2

    def test_extract_github_issues_with_keywords(self, basic_extractor):
        """Test extracting issues with various keywords"""
        text = """
        Closes #100
        Fixes #200
        Resolves #300
        See #400
        """
        issues = basic_extractor.extract_github_issues(text)
        assert len(issues) == 4
        assert all(i in issues for i in [100, 200, 300, 400])

    def test_extract_github_issues_duplicates(self, basic_extractor):
        """Test that duplicates are removed"""
        text = "Fixes #100 and #100 and also #100"
        issues = basic_extractor.extract_github_issues(text)
        assert issues == [100]

    def test_extract_github_issues_empty(self, basic_extractor):
        """Test extracting from text with no issues"""
        text = "This is a normal text without any issues"
        issues = basic_extractor.extract_github_issues(text)
        assert issues == []

    def test_extract_urls(self, basic_extractor):
        """Test extracting URLs"""
        text = "See https://example.com and http://test.org for more info"
        urls = basic_extractor.extract_urls(text)
        assert 'https://example.com' in urls
        assert 'http://test.org' in urls

    def test_extract_urls_multiple(self, basic_extractor):
        """Test extracting multiple URLs"""
        text = """
        Check https://github.com/user/repo
        And https://docs.example.com/api
        """
        urls = basic_extractor.extract_urls(text)
        assert len(urls) >= 2

    def test_extract_urls_empty(self, basic_extractor):
        """Test extracting when no URLs present"""
        text = "No URLs here"
        urls = basic_extractor.extract_urls(text)
        assert urls == []

    def test_extract_external_issues_jira(self, jira_extractor):
        """Test extracting JIRA issues"""
        text = "Related to JIRA-123 and JIRA-456"
        issues = jira_extractor.extract_external_issues(text)
        assert len(issues) == 2
        assert issues[0][0] == '123'
        assert 'jira.example.com' in issues[0][1]

    def test_extract_external_issues_disabled(self, basic_extractor):
        """Test that external issues not extracted when disabled"""
        text = "Related to JIRA-123"
        issues = basic_extractor.extract_external_issues(text)
        assert issues == []

    def test_extract_external_issues_duplicates(self, jira_extractor):
        """Test that duplicate external issues are removed"""
        text = "JIRA-100 JIRA-100 JIRA-100"
        issues = jira_extractor.extract_external_issues(text)
        assert len(issues) == 1
        assert issues[0][0] == '100'

    def test_extract_all_metadata_complete(self, jira_extractor):
        """Test extracting all metadata together"""
        pr_info = {'number': 42, 'body': 'Fixes #100 Related to JIRA-123'}
        metadata = jira_extractor.extract_all_metadata(pr_info)

        assert metadata['merge_requests'] == [42]
        assert 100 in metadata['issues']
        assert any(issue[0] == '123' for issue in metadata['links'])

    def test_extract_all_metadata_with_additional_text(self, jira_extractor):
        """Test extracting metadata with additional text"""
        pr_info = {'number': 1, 'body': ''}
        additional_text = "Legacy entry mentions #500 and JIRA-200"
        metadata = jira_extractor.extract_all_metadata(pr_info, additional_text)

        assert metadata['merge_requests'] == [1]
        assert 500 in metadata['issues']
        assert any(issue[0] == '200' for issue in metadata['links'])

    def test_extract_all_metadata_empty(self, basic_extractor):
        """Test extracting from empty PR"""
        pr_info = {}
        metadata = basic_extractor.extract_all_metadata(pr_info)

        assert metadata['merge_requests'] == []
        assert metadata['issues'] == []
        assert metadata['links'] == []

    def test_build_metadata_section_complete(self, jira_extractor):
        """Test building metadata section"""
        metadata = {
            'merge_requests': [42],
            'issues': [100, 200],
            'links': [('JIRA-123', 'https://jira.example.com/browse/JIRA-123')]
        }
        section = jira_extractor.build_metadata_section(metadata)

        assert '#42' in section
        assert '#100' in section
        assert '#200' in section
        assert 'JIRA-123' in section

    def test_build_metadata_section_empty(self, basic_extractor):
        """Test building metadata section when empty"""
        metadata = {'merge_requests': [], 'issues': [], 'links': []}
        section = basic_extractor.build_metadata_section(metadata)

        assert 'No additional metadata' in section

    def test_external_issue_regex_invalid(self):
        """Test with invalid regex pattern"""
        extractor = PRMetadataExtractor(
            external_issue_regex='[invalid(regex',
            external_issue_url_template='https://example.com/{id}'
        )
        # Should have compiled_regex = None
        assert extractor.compiled_regex is None

    def test_github_issues_case_insensitive(self, basic_extractor):
        """Test that issue keywords are case insensitive"""
        text = "CLOSES #100 FIXES #200 resolves #300"
        issues = basic_extractor.extract_github_issues(text)
        assert 100 in issues
        assert 200 in issues
        assert 300 in issues

    def test_github_issue_detection_disabled(self):
        """Test that GitHub issues are not extracted when disabled"""
        extractor = PRMetadataExtractor(github_issue_detection=False)
        text = "Fixes #123 and #456"
        issues = extractor.extract_github_issues(text)
        assert issues == []

    def test_issue_tracker_url_detection_disabled(self):
        """Test that URLs are not extracted when detection is disabled"""
        extractor = PRMetadataExtractor(issue_tracker_url_detection=False)
        text = "See https://example.com and https://docs.test.org"
        urls = extractor.extract_urls(text)
        assert urls == []

    def test_issue_tracker_url_detection_enabled(self):
        """Test that URLs are extracted when detection is enabled"""
        extractor = PRMetadataExtractor(issue_tracker_url_detection=True)
        text = "See https://example.com and https://docs.test.org"
        urls = extractor.extract_urls(text)
        assert len(urls) == 2
        assert 'https://example.com' in urls
        assert 'https://docs.test.org' in urls

    def test_extract_all_metadata_with_detection_disabled(self):
        """Test metadata extraction with GitHub issues disabled"""
        extractor = PRMetadataExtractor(github_issue_detection=False)
        pr_info = {'number': 42, 'body': 'Fixes #100 and #200'}
        metadata = extractor.extract_all_metadata(pr_info)

        assert metadata['merge_requests'] == [42]
        assert metadata['issues'] == []  # GitHub issues not extracted

    def test_extract_all_metadata_both_trackers_disabled(self):
        """Test that no tracker URLs extracted when disabled"""
        extractor = PRMetadataExtractor(
            issue_tracker_url_detection=False,
            external_issue_regex=r'JIRA-(\d+)',
            external_issue_url_template='https://jira.example.com/browse/JIRA-{id}'
        )
        pr_info = {'number': 1, 'body': 'Related to JIRA-123 see https://docs.example.com'}
        metadata = extractor.extract_all_metadata(pr_info)

        # External issues still extracted (different flag)
        assert any(issue[0] == '123' for issue in metadata['links'])
        # Generic URLs not extracted when disabled
        assert not any('docs.example.com' in url for _, url in metadata['links'])


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
