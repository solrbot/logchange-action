"""GitHub API client for PR operations"""

import logging
import os
from typing import Any, Dict, List

import requests

logger = logging.getLogger(__name__)


class GitHubClient:
    """Client for GitHub API operations"""

    def __init__(self, token: str, api_url: str, event: Dict[str, Any]):
        """Initialize GitHub client"""
        self.token = token
        self.api_url = api_url.rstrip("/")
        self.event = event
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

        # Extract PR info
        self.repo_owner = os.getenv("GITHUB_REPOSITORY_OWNER", "")
        self.repo_name = (
            os.getenv("GITHUB_REPOSITORY", "").split("/")[-1]
            if os.getenv("GITHUB_REPOSITORY")
            else ""
        )
        self.pr_number = event.get("pull_request", {}).get("number", 0)

    def get_pr_files(self) -> List[str]:
        """Get list of files modified in the PR"""
        if not self.pr_number:
            logger.warning("No PR number found")
            return []

        url = f"{self.api_url}/repos/{self.repo_owner}/{self.repo_name}/pulls/{self.pr_number}/files"
        files = []
        page = 1

        try:
            while True:
                response = self.session.get(url, params={"page": page, "per_page": 100})
                response.raise_for_status()

                batch = response.json()
                if not batch:
                    break

                for file in batch:
                    files.append(file["filename"])

                page += 1

            logger.info(f"Retrieved {len(files)} files from PR")
            return files

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get PR files: {e}")
            return []

    def get_pr_diff(
        self,
        pr_files: List[str],
        max_total_tokens: int = 5000,
        max_per_file: int = 1000,
    ) -> str:
        """Get the diff for the PR, with intelligent truncation"""
        if not self.pr_number:
            logger.warning("No PR number found")
            return ""

        url = f"{self.api_url}/repos/{self.repo_owner}/{self.repo_name}/pulls/{self.pr_number}"

        try:
            response = self.session.get(url)
            response.raise_for_status()

            pr_data = response.json()
            diff_url = pr_data.get("diff_url", "")

            if not diff_url:
                logger.warning("No diff URL found")
                return ""

            # Fetch the diff using session (for consistency and auth)
            diff_response = self.session.get(diff_url)
            diff_response.raise_for_status()
            diff_content = diff_response.text

            # Truncate if necessary
            if len(diff_content) > max_total_tokens:
                diff_content = self._truncate_diff(
                    diff_content, pr_files, max_total_tokens, max_per_file
                )

            logger.info(f"Retrieved PR diff ({len(diff_content)} characters)")
            return diff_content

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get PR diff: {e}")
            return ""

    def _truncate_diff(
        self, diff: str, files: List[str], max_total: int, max_per_file: int
    ) -> str:
        """Intelligently truncate diff to stay within token limits with file list"""
        # Reserve space for file list at the beginning
        file_list_section = self._build_file_list_section(files)
        reserved_for_files = len(file_list_section)
        available_for_diff = max_total - reserved_for_files

        lines = diff.split("\n")
        result_lines = []
        current_file = None
        current_file_lines = 0
        total_chars = 0
        included_files = set()
        skipped_files = set()

        for line in lines:
            # Track which file we're in
            if line.startswith("diff --git"):
                # Extract filename from "diff --git a/path b/path"
                parts = line.split(" ")
                if len(parts) >= 4:
                    current_file = parts[3].lstrip("b/")
                    included_files.add(current_file)
                current_file_lines = 0

            # Check limits
            if total_chars + len(line) + 1 > available_for_diff:
                # Stop if we exceed available limit
                if result_lines and not result_lines[-1].startswith("... "):
                    result_lines.append(
                        "\n... (diff truncated due to size limits) ...\n"
                    )
                break

            if current_file and current_file_lines > max_per_file:
                # Skip this file's remaining lines but track as skipped
                if line.startswith("diff --git"):
                    current_file_lines = 0
                else:
                    skipped_files.add(current_file)
                    continue

            result_lines.append(line)
            total_chars += len(line) + 1
            current_file_lines += 1

        diff_content = "\n".join(result_lines)

        # Build final output with file list and diff
        return file_list_section + diff_content

    def _build_file_list_section(self, files: List[str]) -> str:
        """Build a section listing all edited files for context"""
        if not files:
            return ""

        file_list = "\n".join(f"  - {f}" for f in files)
        return f"""**All edited files in this PR:**
{file_list}

**Changes (may be truncated for size):**

"""

    def comment_on_pr(self, body: str) -> bool:
        """Post a comment on the PR"""
        if not self.pr_number:
            logger.warning("No PR number found, cannot comment")
            return False

        url = f"{self.api_url}/repos/{self.repo_owner}/{self.repo_name}/issues/{self.pr_number}/comments"

        try:
            response = self.session.post(url, json={"body": body})
            response.raise_for_status()
            logger.info("Successfully posted comment on PR")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to comment on PR: {e}")
            return False

    def get_pr_title_and_body(self) -> tuple[str, str]:
        """Get PR title and body"""
        try:
            pr = self.event.get("pull_request", {})
            return pr.get("title", ""), pr.get("body", "")
        except Exception as e:
            logger.error(f"Failed to get PR info: {e}")
            return "", ""

    def has_existing_changelog_suggestion(self) -> bool:
        """
        Check if the action has already posted a changelog suggestion on this PR.
        Looks for comments containing changelog generation suggestions.

        Returns:
            True if a suggestion already exists, False otherwise
        """
        if not self.pr_number:
            logger.warning("No PR number found")
            return False

        url = f"{self.api_url}/repos/{self.repo_owner}/{self.repo_name}/issues/{self.pr_number}/comments"

        try:
            # Get all comments on the PR
            page = 1
            while True:
                response = self.session.get(url, params={"page": page, "per_page": 100})
                response.raise_for_status()

                comments = response.json()
                if not comments:
                    break

                # Check if any comment contains changelog generation markers
                for comment in comments:
                    body = comment.get("body", "")
                    # Look for markers that indicate this is from our action
                    if any(
                        marker in body
                        for marker in [
                            "I've generated a changelog entry",
                            "I've converted the legacy changelog entry",
                            "Found changes to",
                            "changelog entry does not comply",
                            "No changelog entry found",
                            "Legacy changelog entry found",
                        ]
                    ):
                        logger.info(
                            f"Found existing changelog suggestion in comment {comment.get('id')}"
                        )
                        return True

                page += 1

            logger.debug("No existing changelog suggestions found on PR")
            return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to check for existing comments: {e}")
            # If we can't check, assume there are no existing comments
            # (better to post a duplicate than to skip a valid suggestion)
            return False

