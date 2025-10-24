"""Extract metadata from PR for changelog generation"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class PRMetadataExtractor:
    """Extract PR metadata for changelog entries"""

    def __init__(
        self,
        external_issue_regex: Optional[str] = None,
        external_issue_url_template: Optional[str] = None,
        github_issue_detection: bool = True,
        issue_tracker_url_detection: bool = True,
    ):
        r"""
        Initialize metadata extractor

        Args:
            external_issue_regex: Regex with capture group to find external issue IDs
                                 Example: r'JIRA-(\d+)'
            external_issue_url_template: URL template with {id} placeholder
                                        Example: 'https://jira.example.com/browse/{id}'
            github_issue_detection: Whether to detect GitHub issues (#123 references)
            issue_tracker_url_detection: Whether to detect issue tracker URLs (via LLM analysis)
        """
        self.external_issue_regex = external_issue_regex
        self.external_issue_url_template = external_issue_url_template
        self.github_issue_detection = github_issue_detection
        self.issue_tracker_url_detection = issue_tracker_url_detection

        if external_issue_regex:
            try:
                self.compiled_regex = re.compile(external_issue_regex)
                logger.info(f'External issue regex compiled: {external_issue_regex}')
            except re.error as e:
                logger.error(f'Invalid external issue regex: {e}')
                self.compiled_regex = None
        else:
            self.compiled_regex = None

    def extract_merge_request_number(self, pr_info: Dict[str, Any]) -> Optional[int]:
        """
        Extract merge request number from PR

        Args:
            pr_info: PR information from GitHub event

        Returns:
            PR number or None
        """
        pr_number = pr_info.get('number')
        if pr_number:
            logger.debug(f'Extracted PR number: {pr_number}')
        return pr_number

    def extract_github_issues(self, text: str) -> List[int]:
        """
        Extract GitHub issue numbers referenced in text

        Looks for patterns like:
        - #123
        - fixes #123
        - closes #456
        - resolves #789

        Args:
            text: Text to search (PR description, etc.)

        Returns:
            List of unique issue numbers found
        """
        if not text or not self.github_issue_detection:
            return []

        # Pattern: #number or words like "fixes #123"
        pattern = r'(?:closes|closes|fixes|fixed|resolves|resolved|references|refs|see|issue|issues)?\s*#(\d+)'
        matches = re.findall(pattern, text, re.IGNORECASE)
        issues = list(set(int(m) for m in matches))

        if issues:
            logger.debug(f'Extracted GitHub issues: {issues}')

        return sorted(issues)

    def extract_urls(self, text: str) -> List[str]:
        """
        Extract URLs from text (only returns URLs if tracker detection disabled)

        Note: When issue_tracker_url_detection is enabled, URLs are filtered by LLM
        and only issue tracker URLs are added to links. Generic documentation URLs
        require explicit issue tracker configuration.

        Args:
            text: Text to search

        Returns:
            List of unique URLs found (empty if detection is disabled)
        """
        if not text or not self.issue_tracker_url_detection:
            return []

        # Simple URL pattern
        url_pattern = r'https?://[^\s\)>\]<]+'
        urls = list(set(re.findall(url_pattern, text)))

        if urls:
            logger.debug(f'Extracted URLs: {urls}')

        return urls

    def extract_external_issues(self, text: str) -> List[Tuple[str, str]]:
        """
        Extract external issue references (e.g., JIRA-123)

        Args:
            text: Text to search

        Returns:
            List of (short_id, url) tuples
        """
        if not self.compiled_regex or not self.external_issue_url_template or not text:
            return []

        matches = self.compiled_regex.findall(text)
        if not matches:
            return []

        # Handle both single captures and multiple captures
        issues = []
        for match in matches:
            if isinstance(match, tuple):
                # Multiple capture groups - use first non-empty
                short_id = next((m for m in match if m), None)
            else:
                # Single capture group
                short_id = match

            if short_id:
                url = self.external_issue_url_template.format(id=short_id)
                issues.append((short_id, url))

        # Remove duplicates while preserving order
        seen = set()
        unique_issues = []
        for issue in issues:
            if issue[0] not in seen:
                unique_issues.append(issue)
                seen.add(issue[0])

        if unique_issues:
            logger.debug(f'Extracted external issues: {unique_issues}')

        return unique_issues

    def extract_all_metadata(
        self,
        pr_info: Dict[str, Any],
        additional_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract all metadata from PR

        Args:
            pr_info: PR information from GitHub event
            additional_text: Additional text to search (e.g., legacy changelog entry)

        Returns:
            Dictionary with extracted metadata:
            - merge_requests: List of PR numbers
            - issues: List of GitHub issue numbers
            - links: List of (name, url) tuples
        """
        # Combine PR description and additional text
        text_to_search = pr_info.get('body', '') or ''
        if additional_text:
            text_to_search = f'{text_to_search}\n{additional_text}'

        metadata = {
            'merge_requests': [],
            'issues': [],
            'links': [],
        }

        # Extract PR number (merge request)
        pr_number = self.extract_merge_request_number(pr_info)
        if pr_number:
            metadata['merge_requests'] = [pr_number]

        # Extract GitHub issues
        github_issues = self.extract_github_issues(text_to_search)
        if github_issues:
            metadata['issues'] = github_issues

        # Extract external issues as links
        external_issues = self.extract_external_issues(text_to_search)
        if external_issues:
            metadata['links'].extend(external_issues)

        # Extract other URLs
        urls = self.extract_urls(text_to_search)
        # Filter out JIRA URLs (already handled as links)
        jira_urls = set(url for _, url in external_issues)
        for url in urls:
            if url not in jira_urls:
                # Use domain as name if no better option
                name = url.split('/')[-1] or url.split('/')[-2]
                metadata['links'].append((name, url))

        logger.debug(f'Extracted metadata: {metadata}')
        return metadata

    def build_metadata_section(self, metadata: Dict[str, Any]) -> str:
        """
        Build a text section describing extracted metadata

        Useful for including in prompts to show Claude what was found

        Args:
            metadata: Extracted metadata

        Returns:
            Formatted metadata description
        """
        sections = []

        if metadata.get('merge_requests'):
            mr_list = ', '.join(f'#{mr}' for mr in metadata['merge_requests'])
            sections.append(f'Merge Requests: {mr_list}')

        if metadata.get('issues'):
            issue_list = ', '.join(f'#{issue}' for issue in metadata['issues'])
            sections.append(f'Related Issues: {issue_list}')

        if metadata.get('links'):
            link_list = ', '.join(
                f'[{name}]({url})' for name, url in metadata['links']
            )
            sections.append(f'Links: {link_list}')

        if not sections:
            return 'No additional metadata found.'

        return '\n'.join(f'- {s}' for s in sections)
