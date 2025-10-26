"""Legacy changelog detection and conversion handler"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from changelog_generator import ChangelogGenerator

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

    def extract_added_lines_with_positions(
        self, diff_content: str, legacy_file: str
    ) -> List[Tuple[int, str]]:
        """
        Extract changelog lines from diff with their line numbers for suggested edits.

        Args:
            diff_content: The diff output for the changelog file
            legacy_file: The legacy file path (for matching the diff)

        Returns:
            List of tuples (line_number, line_content) for added lines in the new version
        """
        lines = diff_content.split("\n")
        added_lines_with_pos = []
        current_new_line = 0
        in_hunk = False

        for line in lines:
            # Skip lines until we find the hunk header
            if line.startswith("@@"):
                # Parse hunk header: @@ -old_start,old_count +new_start,new_count @@
                try:
                    parts = line.split(" ")
                    new_range = parts[2]  # +new_start,new_count
                    new_start = int(new_range.split(",")[0].lstrip("+"))
                    current_new_line = new_start
                except (IndexError, ValueError):
                    pass
                in_hunk = True
                continue

            if not in_hunk:
                continue

            # Process lines in hunk
            if line.startswith("@@"):
                # New hunk, reset
                continue
            elif line.startswith("-"):
                # Removed line - don't increment new line counter
                pass
            elif line.startswith("+") and not line.startswith("+++"):
                # Added line - record it with position
                content = line[1:]  # Remove '+' prefix
                added_lines_with_pos.append((current_new_line, content))
                current_new_line += 1
            elif not line.startswith("\\"):
                # Context line (unchanged) - increment counter
                current_new_line += 1

        return added_lines_with_pos

    def group_consecutive_lines(
        self, added_lines: List[Tuple[int, str]]
    ) -> List[Tuple[int, int, List[str]]]:
        """
        Group consecutive added lines together for multi-line suggestions.

        Args:
            added_lines: List of tuples (line_number, line_content)

        Returns:
            List of tuples (start_line, end_line, [line_contents]) for each group
        """
        if not added_lines:
            return []

        groups = []
        start_line = added_lines[0][0]
        end_line = added_lines[0][0]
        group_content = [added_lines[0][1]]

        for i in range(1, len(added_lines)):
            current_line, current_content = added_lines[i]
            prev_line = added_lines[i - 1][0]

            # If consecutive, add to group
            if current_line == prev_line + 1:
                end_line = current_line
                group_content.append(current_content)
            else:
                # Gap found, save current group and start new one
                groups.append((start_line, end_line, group_content))
                start_line = current_line
                end_line = current_line
                group_content = [current_content]

        # Add the last group
        groups.append((start_line, end_line, group_content))

        return groups

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
        self,
        entry_text: str,
        pr_info: Dict[str, Any],
        context: Dict[str, Any],
        changelog_types: Optional[List[str]] = None,
        forbidden_fields: Optional[List[str]] = None,
        pr_diff: str = "",
    ) -> str:
        """
        Create a custom user prompt for converting legacy entry to logchange format

        Args:
            entry_text: The legacy changelog entry text
            pr_info: PR information from GitHub
            context: Context about the legacy entry
            changelog_types: List of allowed changelog types (uses defaults if not provided)
            forbidden_fields: List of forbidden fields (from configuration)
            pr_diff: The PR diff to validate relevance (optional)

        Returns:
            The user prompt for Claude
        """
        pr_title = pr_info.get("title", "")
        pr_author = pr_info.get("user", {}).get("login", "unknown")
        entry_type = context.get("type", "unknown")

        # Use provided types or defaults
        if changelog_types is None:
            changelog_types = [
                "added",
                "changed",
                "deprecated",
                "removed",
                "fixed",
                "security",
                "dependency_update",
                "other",
            ]

        # Create a temporary generator to access the validation rules building method
        # We need to pass a dummy API key since we're only using the method, not making API calls
        temp_generator = ChangelogGenerator(
            api_key="dummy",
            changelog_types=changelog_types,
            forbidden_fields=forbidden_fields or [],
        )
        validation_section = temp_generator._build_validation_rules_section(
            changelog_types, forbidden_fields
        )

        validation_check = ""
        if pr_diff:
            validation_check = """
IMPORTANT - RELEVANCE CHECK:
Before conversion, verify that the changelog entry is actually relevant to the PR changes:
- Look at the PR diff to understand what code actually changed
- Check if the entry text describes related changes or is completely unrelated
- If the entry is CLEARLY UNRELATED (e.g., discusses "elephants" when code is about auth),
  REJECT by returning: title: "IRRELEVANT_ENTRY"
- Only convert entries reasonably related to or describing the actual code changes

PR Code Changes (diff):
```
{pr_diff[:1500]}...
```
"""

        prompt = f"""I have extracted a changelog entry from a legacy changelog file.
I need to convert it into logchange-formatted YAML while preserving the original text and intent.

{validation_check}

CONVERSION INSTRUCTIONS:
1. **Validate relevance**: Ensure the entry describes changes actually made in the code (see PR diff above)
2. **Preserve the original text**: Keep the wording and meaning as-is when relevant
3. **Gentle rewriting only**: Only rewrite if it's grammatically incorrect or unclear
4. **Extract metadata**: Look for issue links (#123, JIRA-123, etc.) and additional contributors mentioned in the text
5. **Determine type**: Infer the type from the content. Allowed types: {', '.join(changelog_types)}
6. **Create title**: Use the existing entry text or PR title to create a clear, concise title
7. **Valid YAML**: Ensure the generated YAML is valid and properly formatted
8. **Output format**: Output ONLY the YAML with no additional text, markdown, or comments
9. **Rejection case**: If entry is clearly unrelated to code changes, output: title: "IRRELEVANT_ENTRY"

Legacy Changelog Entry:
```
{entry_text}
```

PR Title: {pr_title}

PR Author: {pr_author}

Entry Type Detected: {entry_type}

{validation_section}

**IMPORTANT: Always include the authors field**
- The authors field is REQUIRED and must include at least the PR author ({pr_author})
- Extract any additional authors from the legacy entry text if mentioned
- Format: authors: [{{name: "Author Name"}}]

Now convert this into logchange format, validating that it's relevant to the code changes:"""

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
