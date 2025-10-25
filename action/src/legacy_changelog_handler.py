"""Legacy changelog detection and conversion handler"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class LegacyChangelogHandler:
    """Detect and handle legacy changelog entries"""

    def __init__(self, legacy_changelog_paths: Optional[List[str]] = None):
        """
        Initialize legacy changelog handler

        Args:
            legacy_changelog_paths: List of file paths/patterns to check for legacy changelogs.
                                   If empty/None, legacy changelog detection is DISABLED.
                                   Examples: ['CHANGELOG.md', 'HISTORY.txt', 'docs/CHANGES.md']
        """
        self.legacy_changelog_paths = legacy_changelog_paths or []
        self.is_enabled = len(self.legacy_changelog_paths) > 0

        if self.is_enabled:
            logger.info(
                f"Initialized legacy changelog handler with {len(self.legacy_changelog_paths)} paths"
            )
        else:
            logger.info("Legacy changelog detection is DISABLED (no paths configured)")

    def find_legacy_changelog_files(self, pr_files: List[str]) -> List[str]:
        """
        Find legacy changelog files in PR

        Args:
            pr_files: List of all files modified in PR

        Returns:
            List of legacy changelog file paths found in PR (empty if detection disabled)
        """
        if not self.is_enabled:
            logger.debug("Legacy changelog detection is disabled, skipping search")
            return []

        legacy_files = []
        for pr_file in pr_files:
            # Check if file matches any legacy changelog pattern
            for legacy_path in self.legacy_changelog_paths:
                # Support exact matches and patterns like 'docs/CHANGELOG.md'
                if pr_file.endswith(legacy_path) or pr_file == legacy_path:
                    legacy_files.append(pr_file)
                    break

        logger.info(f"Found {len(legacy_files)} legacy changelog file(s) in PR")
        return legacy_files

    def extract_changelog_entry_from_diff(self, diff_content: str) -> Optional[str]:
        """
        Extract the changelog entry text from a diff

        Looks for added lines (starting with '+') that appear to be changelog content.

        Args:
            diff_content: The diff output for the changelog file

        Returns:
            Extracted changelog entry text or None if not found
        """
        lines = diff_content.split("\n")
        added_lines = []
        in_hunk = False

        for line in lines:
            # Track when we're in a hunk
            if line.startswith("@@"):
                in_hunk = True
                continue

            if in_hunk:
                # Only capture added lines (starting with '+' but not '+++')
                if line.startswith("+") and not line.startswith("+++"):
                    # Remove the '+' prefix
                    added_lines.append(line[1:])

        if added_lines:
            entry_text = "\n".join(added_lines).strip()
            logger.debug(f"Extracted changelog entry: {len(entry_text)} characters")
            return entry_text

        return None

    def detect_entry_type(self, entry_text: str) -> str:
        """
        Detect what type of changelog entry this is

        Args:
            entry_text: The changelog entry text

        Returns:
            Type: 'markdown', 'plain_text', 'unreleased', or 'other'
        """
        lower_text = entry_text.lower()

        # Check for "Unreleased" or "Upcoming" sections FIRST (before markdown)
        if any(
            keyword in lower_text
            for keyword in ["unreleased", "upcoming", "next release", "in development"]
        ):
            return "unreleased"

        # Check for markdown-style entries (## Version, ### Section)
        if re.search(r"^#+\s+", entry_text, re.MULTILINE):
            return "markdown"

        # Check for bullet point lists (typical changelog format)
        if re.search(r"^[\s]*[-*+]\s+", entry_text, re.MULTILINE):
            return "plain_text"

        return "other"

    def extract_version_and_date(
        self, entry_text: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract version number and date from changelog entry

        Args:
            entry_text: The changelog entry text

        Returns:
            Tuple of (version, date) or (None, None) if not found
        """
        # Pattern: ## 1.2.3 - 2024-10-24
        version_pattern = r"(?:##|###)?\s*(?:v?(\d+\.\d+(?:\.\d+)?(?:-\w+\.\d+)?))(?:\s*[-–]\s*(\d{4}-\d{2}-\d{2}))?"
        match = re.search(version_pattern, entry_text)

        if match:
            version = match.group(1)
            date = match.group(2) if match.lastindex >= 2 else None
            logger.debug(f"Extracted version: {version}, date: {date}")
            return version, date

        return None, None

    def build_legacy_context(self, entry_text: str) -> Dict[str, Any]:
        """
        Build context information about a legacy changelog entry

        Args:
            entry_text: The changelog entry text

        Returns:
            Dictionary with: type, version, date, summary, line_count
        """
        entry_type = self.detect_entry_type(entry_text)
        version, date = self.extract_version_and_date(entry_text)

        # Create a brief summary (first 100 chars)
        summary = entry_text[:100].replace("\n", " ").strip()
        if len(entry_text) > 100:
            summary += "..."

        return {
            "type": entry_type,
            "version": version,
            "date": date,
            "summary": summary,
            "line_count": len(entry_text.split("\n")),
            "char_count": len(entry_text),
        }

    def create_conversion_prompt(
        self, entry_text: str, pr_info: Dict[str, Any], context: Dict[str, Any]
    ) -> str:
        """
        Create a custom user prompt for converting legacy entry to logchange format

        Args:
            entry_text: The legacy changelog entry text
            pr_info: PR information from GitHub
            context: Context about the legacy entry

        Returns:
            The user prompt for Claude
        """
        pr_title = pr_info.get("title", "")
        entry_type = context.get("type", "unknown")

        prompt = f"""I have extracted a changelog entry that was carefully written by the author.
I need to convert it into logchange-formatted YAML while preserving the original text and intent.

IMPORTANT: This is the author's own writing. Preserve it as closely as possible.

CONVERSION INSTRUCTIONS:
1. **Preserve the original text**: The changelog entry was written by the author. Keep the wording and meaning as-is.
2. **Gentle rewriting only**: Only rewrite if it's grammatically incorrect or unclear compared to the actual changes.
3. **Extract metadata**: Look for issue links (#123, JIRA-123, etc.) and additional contributors mentioned in the text.
4. **Determine type**: Infer the type (added, changed, fixed, security, dependency_update, etc.) from the content.
5. **Create title**: Use the existing entry text or PR title to create a clear, concise title if one doesn't exist.
6. **Valid YAML**: Ensure the generated YAML is valid and properly formatted.
7. **Output format**: Output ONLY the YAML with no additional text, markdown, or comments.

Legacy Changelog Entry:
```
{entry_text}
```

PR Title: {pr_title}

Entry Type Detected: {entry_type}

Now convert this into logchange format while preserving the author's original text:"""

        return prompt

    def should_fail_on_conflict(
        self, legacy_files: List[str], logchange_files: List[str]
    ) -> bool:
        """
        Determine if having both legacy and logchange entries is a conflict

        Args:
            legacy_files: List of legacy changelog files with entries
            logchange_files: List of logchange files with entries

        Returns:
            True if both types are present (conflict), False otherwise
        """
        has_legacy = len(legacy_files) > 0
        has_logchange = len(logchange_files) > 0
        is_conflict = has_legacy and has_logchange

        if is_conflict:
            logger.warning(
                f"Conflict detected: {len(legacy_files)} legacy files and {len(logchange_files)} logchange files"
            )

        return is_conflict
