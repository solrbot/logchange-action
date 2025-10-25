#!/usr/bin/env python3
"""
Logchange GitHub Action - Ensure changelog entries in pull requests
"""

import logging
import os
import re
import sys
from typing import List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add src directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from changelog_generator import ChangelogGenerator
from changelog_validator import ChangelogValidator
from config import ActionConfig
from exceptions import ConfigurationError, GenerationError
from github_client import GitHubClient
from legacy_changelog_handler import LegacyChangelogHandler
from pr_metadata_extractor import PRMetadataExtractor


def generate_changelog_slug(pr_number: int, title: str = "") -> str:
    """
    Generate a slug-formatted filename for changelog entries

    Args:
        pr_number: Pull request number (used as prefix)
        title: Optional title to generate slug from

    Returns:
        Slug in format: pr-{number}-{slug}.yml or pr-{number}.yml if no title
    """
    slug = ""
    if title:
        # Convert title to slug: lowercase, replace spaces/special chars with hyphens
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        # Remove duplicate hyphens
        slug = re.sub(r"-+", "-", slug)
        # Limit to 50 characters to keep filenames reasonable
        slug = slug[:50].rstrip("-")

    if slug:
        return f"pr-{pr_number}-{slug}.yml"
    else:
        return f"pr-{pr_number}.yml"


class LogchangeAction:
    """Main action class handling the workflow"""

    def __init__(self):
        """Initialize the action with configuration"""
        try:
            # Load configuration from environment
            self.config = ActionConfig()

            # Log configuration summary if debug mode
            logger.debug(self.config.get_summary())

            # Assign configuration attributes for backward compatibility
            self.changelog_path = self.config.changelog_path
            self.on_missing_entry = self.config.on_missing_entry
            self.missing_entry_message = self.config.missing_entry_message
            self.skip_files_regex = self.config.skip_files_regex
            self.skip_changelog_labels = self.config.skip_changelog_labels
            self.dry_run = self.config.dry_run
            self.claude_token = self.config.claude_token
            self.claude_model = self.config.claude_model
            self.claude_system_prompt = self.config.claude_system_prompt
            self.changelog_language = self.config.changelog_language
            self.max_tokens_context = self.config.max_tokens_context
            self.max_tokens_per_file = self.config.max_tokens_per_file
            self.changelog_types = self.config.changelog_types
            self.mandatory_fields = self.config.mandatory_fields
            self.forbidden_fields = self.config.forbidden_fields
            self.optional_fields = self.config.optional_fields
            self.legacy_changelog_paths = self.config.legacy_changelog_paths
            self.on_legacy_entry = self.config.on_legacy_entry
            self.on_legacy_and_logchange = self.config.on_legacy_and_logchange
            self.legacy_entry_message = self.config.legacy_entry_message
            self.legacy_conflict_message = self.config.legacy_conflict_message
            self.validation_fail_message = self.config.validation_fail_message
            self.validation_fail_workflow = self.config.validation_fail_workflow
            self.external_issue_regex = self.config.external_issue_regex
            self.external_issue_url_template = self.config.external_issue_url_template
            self.generate_important_notes = self.config.generate_important_notes
            self.github_issue_detection = self.config.github_issue_detection
            self.issue_tracker_url_detection = self.config.issue_tracker_url_detection

            # GitHub context
            self.github_event = self.config.github_event
            self.github_token = self.config.github_token
            self.github_api_url = self.config.github_api_url

            # Initialize clients
            self.github_client = GitHubClient(
                self.github_token, self.github_api_url, self.github_event
            )
            self.validator = ChangelogValidator(
                changelog_types=self.changelog_types,
                mandatory_fields=self.mandatory_fields,
                forbidden_fields=self.forbidden_fields,
                optional_fields=self.optional_fields,
            )
            self.legacy_handler = LegacyChangelogHandler(self.legacy_changelog_paths)
            self.metadata_extractor = PRMetadataExtractor(
                external_issue_regex=(
                    self.external_issue_regex if self.external_issue_regex else None
                ),
                external_issue_url_template=(
                    self.external_issue_url_template
                    if self.external_issue_url_template
                    else None
                ),
                github_issue_detection=self.github_issue_detection,
                issue_tracker_url_detection=self.issue_tracker_url_detection,
            )
            self.generator = self._initialize_generator()

        except ConfigurationError as e:
            logger.error(f"Configuration error: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize action: {e}", exc_info=True)
            raise

    def _initialize_generator(self) -> ChangelogGenerator:
        """Initialize Claude changelog generator with graceful degradation.

        Returns:
            ChangelogGenerator instance if generation is enabled, None otherwise
        """
        if self.on_missing_entry != "generate":
            return None

        if not self.claude_token:
            logger.warning(
                "on-missing-entry is 'generate' but claude-token not provided. "
                "Will degrade to 'warn' mode."
            )
            return None

        try:
            return ChangelogGenerator(
                api_key=self.claude_token,
                model=self.claude_model,
                system_prompt=self.claude_system_prompt,
                changelog_language=self.changelog_language,
                max_tokens_context=self.max_tokens_context,
                max_tokens_per_file=self.max_tokens_per_file,
                changelog_types=self.changelog_types,
                mandatory_fields=self.mandatory_fields,
                forbidden_fields=self.forbidden_fields,
                generate_important_notes=self.generate_important_notes,
                external_issue_regex=(
                    self.external_issue_regex if self.external_issue_regex else None
                ),
                external_issue_url_template=(
                    self.external_issue_url_template
                    if self.external_issue_url_template
                    else None
                ),
            )
        except Exception as e:
            logger.error(f"Failed to initialize Claude generator: {e}", exc_info=True)
            return None

    def set_output(self, name: str, value: str) -> None:
        """Set GitHub Actions output (respects dry-run mode)"""
        if self.dry_run:
            logger.info(f"[DRY-RUN] Output: {name}={value}")
            return

        output_file = os.getenv("GITHUB_OUTPUT")
        if output_file:
            with open(output_file, "a") as f:
                f.write(f"{name}={value}\n")
        logger.info(f"Output: {name}={value}")

    def _post_comment(self, message: str) -> None:
        """Post a comment on the PR (respects dry-run mode)"""
        if self.dry_run:
            logger.info(f"[DRY-RUN] Would post comment:\n{message}")
            return

        self.github_client.comment_on_pr(message)

    def run(self) -> int:
        """Main action execution"""
        try:
            # Check if this is a PR workflow
            if not self._is_pr_workflow():
                logger.info("Not a PR workflow, skipping changelog check")
                return 0

            logger.info("Starting logchange action")

            # Early exit: if generation is enabled, check for existing suggestion before
            # doing expensive file operations
            if (
                self.on_missing_entry == "generate"
                and self._has_existing_suggestion()
            ):
                logger.info(
                    "Changelog suggestion already exists on this PR, skipping all operations"
                )
                self.set_output("changelog-found", "false")
                self.set_output("changelog-generated", "false")
                return 0

            # Get PR files
            pr_files = self.github_client.get_pr_files()
            logger.info(f"Found {len(pr_files)} files in PR")

            # Check if we should skip changelog requirement
            if self._should_skip_changelog(pr_files):
                logger.info(
                    "All files match skip pattern, skipping changelog requirement"
                )
                return 0

            # Check for legacy changelog entries
            legacy_files = self.legacy_handler.find_legacy_changelog_files(pr_files)
            if legacy_files:
                logger.info(f"Found {len(legacy_files)} legacy changelog file(s)")
                # Continue checking for logchange files to detect conflicts

            # Get edited files in changelog path
            changelog_files = self._get_changelog_files(pr_files)
            logger.info(f"Found {len(changelog_files)} logchange file(s) in PR")

            # Check for conflict (both legacy and logchange present)
            if self.legacy_handler.should_fail_on_conflict(
                legacy_files, changelog_files
            ):
                return self._handle_legacy_conflict(legacy_files, changelog_files)

            if changelog_files:
                return self._handle_existing_changelog(changelog_files)
            elif legacy_files:
                return self._handle_legacy_changelog(legacy_files, pr_files)
            else:
                return self._handle_missing_changelog(pr_files)

        except Exception as e:
            logger.error(f"Action failed with error: {e}", exc_info=True)
            self.set_output("generation-error", str(e))
            return 1

    def _is_pr_workflow(self) -> bool:
        """Check if running in a PR workflow"""
        event_name = os.getenv("GITHUB_EVENT_NAME", "")
        is_pr_event = event_name in ["pull_request", "pull_request_target"] and bool(
            self.github_event.get("pull_request")
        )

        if is_pr_event:
            logger.info(f"Running on {event_name} event")

        return is_pr_event

    def _has_existing_suggestion(self) -> bool:
        """
        Check if the action has already posted a changelog suggestion on this PR.
        This prevents duplicate suggestions when the PR is updated with new commits.

        Returns:
            True if a suggestion already exists, False otherwise
        """
        return self.github_client.has_existing_changelog_suggestion()

    def _should_skip_changelog(self, pr_files: List[str]) -> bool:
        """Check if changelog should be skipped based on files or labels"""
        # Check label-based skipping
        if self._should_skip_by_label():
            logger.info("PR has label that skips changelog requirement")
            return True

        # Check file-based skipping
        if not self.skip_files_regex:
            return False

        try:
            pattern = re.compile(self.skip_files_regex)
            return all(pattern.match(f) for f in pr_files)
        except re.error as e:
            logger.warning(f"Invalid skip regex pattern: {e}")
            return False

    def _should_skip_by_label(self) -> bool:
        """Check if PR has any labels that skip changelog requirement"""
        if not self.skip_changelog_labels:
            return False

        pr_info = self.github_event.get("pull_request", {})
        pr_labels = [label.get("name", "") for label in pr_info.get("labels", [])]

        if not pr_labels:
            return False

        for configured_label in self.skip_changelog_labels:
            if configured_label in pr_labels:
                logger.info(
                    f"Found skip-changelog label: {configured_label} in PR labels"
                )
                return True

        return False

    def _get_changelog_files(self, pr_files: List[str]) -> List[str]:
        """Get changelog files edited in PR"""
        changelog_files = []
        for file in pr_files:
            if self.changelog_path in file and file.endswith((".yml", ".yaml")):
                changelog_files.append(file)
        return changelog_files

    def _handle_existing_changelog(self, changelog_files: List[str]) -> int:
        """Handle case where changelog entry already exists"""
        logger.info(f"Validating {len(changelog_files)} changelog file(s)")

        all_valid = True
        for file_path in changelog_files:
            logger.info(f"Validating {file_path}")
            try:
                with open(file_path, "r") as f:
                    content = f.read()

                is_valid, errors = self.validator.validate(content)
                if not is_valid:
                    all_valid = False
                    self._report_validation_error(
                        file_path, errors, "Changelog validation failed", "parsing"
                    )
                    if self.validation_fail_workflow:
                        return 1

            except Exception as e:
                all_valid = False
                error_msg = f"Failed to validate {file_path}: {e}"
                logger.error(error_msg)

                emoji = "❌" if self.validation_fail_workflow else "⚠️"
                level = "failed" if self.validation_fail_workflow else "warning"
                self.github_client.comment_on_pr(
                    f"{emoji} **Changelog {level}**: {file_path}\n\n{str(e)}"
                )

                if self.validation_fail_workflow:
                    return 1

        self.set_output("changelog-found", "true")
        self.set_output("changelog-valid", str(all_valid).lower())

        return 0 if all_valid or not self.validation_fail_workflow else 1

    def _report_validation_error(
        self, file_path: str, errors: List[str], title: str, error_type: str
    ) -> None:
        """Report validation errors to PR comment"""
        logger.error(
            f"{error_type.capitalize()} failed for {file_path}: " + ", ".join(errors)
        )

        emoji = "❌" if self.validation_fail_workflow else "⚠️"
        level = "failed" if self.validation_fail_workflow else "warning"
        errors_text = "\n".join(f"- {e}" for e in errors)

        self.github_client.comment_on_pr(
            f"{emoji} **{title}**: {self.validation_fail_message}\n\n"
            f"**File**: {file_path}\n"
            f'**{level.capitalize() + ("s" if level == "warning" else "")}**:\n{errors_text}'
        )

    def _generate_and_validate(
        self,
        input_text: str,
        custom_prompt: Optional[str] = None,
        context_name: str = "changelog entry",
    ) -> Optional[str]:
        """
        Common workflow for generating and validating changelog entries.

        Handles:
        - Calling generate_with_validation
        - Checking for generation failures
        - Checking for validation failures
        - Posting error comments
        - Setting error outputs

        Args:
            input_text: The PR diff or entry text to generate from
            custom_prompt: Optional custom prompt override
            context_name: Name of what's being generated (for logging/messages)

        Returns:
            Generated entry string if successful, None if failed
        """
        if not self.generator:
            logger.warning(f"Generator not available for {context_name}")
            self.github_client.comment_on_pr(
                "⚠️ Changelog generation is currently unavailable.\n\n"
                "Please try again with your next commit."
            )
            self.set_output("generation-error", "Generator not available")
            return None

        try:
            logger.info(f"Generating {context_name}...")
            pr_info = self.github_event.get("pull_request", {})

            (
                generated_entry,
                is_valid,
                validation_message,
            ) = self.generator.generate_with_validation(
                input_text,
                pr_info,
                self.validator,
                custom_prompt=custom_prompt,
            )

            if not generated_entry:
                logger.warning(
                    f"{context_name} generation failed: {validation_message}"
                )
                self.github_client.comment_on_pr(
                    "⚠️ Changelog generation encountered some issues.\n\n"
                    "No worries! Please try again with your next commit."
                )
                self.set_output("generation-error", validation_message)
                return None

            if not is_valid:
                logger.error(f"Generated {context_name} invalid: {validation_message}")
                self.github_client.comment_on_pr(
                    "⚠️ Changelog generation encountered some issues.\n\n"
                    "No worries! Please try again with your next commit."
                )
                self.set_output("generation-error", "Validation failed")
                return None

            logger.info(f"{context_name} generated and validated successfully")
            return generated_entry

        except GenerationError as e:
            logger.warning(f"{context_name} generation error: {e}")
            self.github_client.comment_on_pr(
                "⚠️ Changelog generation encountered some issues.\n\n"
                "No worries! Please try again with your next commit."
            )
            self.set_output("generation-error", str(e))
            return None

    def _handle_missing_changelog(self, pr_files: List[str]) -> int:
        """Handle case where changelog entry is missing"""
        logger.info(f"No changelog entry found, action: {self.on_missing_entry}")

        if self.on_missing_entry == "fail":
            logger.error(self.missing_entry_message)
            self.github_client.comment_on_pr(f"❌ {self.missing_entry_message}")
            self.set_output("changelog-found", "false")
            return 1

        elif self.on_missing_entry == "warn":
            logger.warning(self.missing_entry_message)
            self.github_client.comment_on_pr(f"⚠️ {self.missing_entry_message}")
            self.set_output("changelog-found", "false")
            return 0

        elif self.on_missing_entry == "generate":
            # Get PR diff
            pr_diff = self.github_client.get_pr_diff(pr_files)
            logger.info(f"PR diff size: {len(pr_diff)} characters")

            # Generate and validate using consolidated helper
            generated_entry = self._generate_and_validate(
                pr_diff, context_name="changelog entry"
            )

            if generated_entry:
                # Post as suggestion (respect dry-run mode)
                suggestion_comment = self._format_suggestion_comment(generated_entry)
                if not self.dry_run:
                    self.github_client.comment_on_pr(suggestion_comment)
                else:
                    logger.info(
                        f"[DRY-RUN] Would post suggestion:\n{suggestion_comment}"
                    )

                self.set_output("changelog-generated", "true")

            self.set_output("changelog-found", "false")
            return 0

        self.set_output("changelog-found", "false")
        return 0

    def _format_suggestion_comment(self, generated_entry: str) -> str:
        """Format the generated changelog as a suggestion comment"""
        # Get PR number and title for filename
        pr_info = self.github_event.get("pull_request", {})
        pr_number = pr_info.get("number", 0)
        pr_title = pr_info.get("title", "")

        # Generate slug-formatted filename
        filename = generate_changelog_slug(pr_number, pr_title)
        file_path = f"{self.changelog_path}/{filename}"

        return f"""✨ **I've generated a changelog entry for you!**

Here's the suggested entry for `{file_path}`:

```yaml
{generated_entry}
```

**To use this:**
1. Create a new file at `{file_path}`
2. Copy the YAML above into it
3. Feel free to edit before merging
"""

    def _handle_legacy_conflict(
        self, legacy_files: List[str], changelog_files: List[str]
    ) -> int:
        """Handle case where both legacy and logchange entries exist"""
        logger.warning(
            f"Conflict: {len(legacy_files)} legacy files and {len(changelog_files)} logchange files found"
        )

        if self.on_legacy_and_logchange == "fail":
            self.github_client.comment_on_pr(f"❌ {self.legacy_conflict_message}")
            self.set_output("legacy-conflict", "true")
            return 1
        elif self.on_legacy_and_logchange == "warn":
            self.github_client.comment_on_pr(f"⚠️ {self.legacy_conflict_message}")
            self.set_output("legacy-conflict", "true")
            # Continue to validate the logchange entries
            return self._handle_existing_changelog(changelog_files)
        else:  # ignore
            logger.info("Ignoring legacy/logchange conflict as configured")
            self.set_output("legacy-conflict", "true")
            return self._handle_existing_changelog(changelog_files)

    def _handle_legacy_changelog(
        self, legacy_files: List[str], pr_files: List[str]
    ) -> int:
        """Handle case where legacy changelog entry exists but no logchange entry"""
        logger.info(f"Handling {len(legacy_files)} legacy changelog file(s)")
        self.set_output("legacy-entry-found", "true")

        if self.on_legacy_entry == "warn":
            logger.warning("Legacy changelog entry found, warning as configured")
            self.github_client.comment_on_pr(f"⚠️ {self.legacy_entry_message}")
            return 0

        elif self.on_legacy_entry == "fail":
            logger.error("Legacy changelog entry found, failing as configured")
            self.github_client.comment_on_pr(f"❌ {self.legacy_entry_message}")
            return 1

        elif self.on_legacy_entry == "convert":
            # Attempt to convert legacy entry to logchange format
            if not self.generator:
                logger.error(
                    "Legacy conversion requested but no Claude API token provided"
                )
                self.github_client.comment_on_pr(
                    "❌ Legacy changelog conversion failed: No Claude API token provided"
                )
                self.set_output("generation-error", "No Claude API token provided")
                return 1

            return self._convert_legacy_to_logchange(legacy_files[0], pr_files)

        self.set_output("legacy-entry-found", "false")
        return 0

    def _convert_legacy_to_logchange(
        self, legacy_file: str, pr_files: List[str]
    ) -> int:
        """Convert a legacy changelog entry to logchange format"""
        try:
            logger.info(f"Converting legacy changelog: {legacy_file}")

            # Get the diff for the legacy file
            pr_diff = self.github_client.get_pr_diff([legacy_file])
            if not pr_diff:
                logger.error(f"Could not get diff for legacy file: {legacy_file}")
                self.github_client.comment_on_pr(
                    f"❌ Could not extract changelog entry from {legacy_file}"
                )
                return 1

            # Extract the changelog entry from the diff
            entry_text = self.legacy_handler.extract_changelog_entry_from_diff(pr_diff)
            if not entry_text:
                logger.error(
                    f"Could not extract changelog entry from diff of {legacy_file}"
                )
                self.github_client.comment_on_pr(
                    f"⚠️ Found changes to {legacy_file} but could not extract changelog entry"
                )
                return 0  # Don't fail, just warn

            logger.info(f"Extracted {len(entry_text)} characters from legacy changelog")

            # Extract line numbers for suggested removal
            added_lines = self.legacy_handler.extract_added_lines_with_positions(
                pr_diff, legacy_file
            )
            logger.info(
                f"Found {len(added_lines)} added lines in legacy changelog diff"
            )

            # Build context about the legacy entry
            context = self.legacy_handler.build_legacy_context(entry_text)
            logger.info(f"Legacy entry context: {context}")

            # Create custom prompt for conversion
            pr_info = self.github_event.get("pull_request", {})
            conversion_prompt = self.legacy_handler.create_conversion_prompt(
                entry_text,
                pr_info,
                context,
                changelog_types=self.changelog_types,
                forbidden_fields=self.forbidden_fields,
            )

            # Generate and validate using consolidated helper
            generated_entry = self._generate_and_validate(
                entry_text,
                custom_prompt=conversion_prompt,
                context_name="legacy changelog conversion",
            )

            if not generated_entry:
                # Conversion failed - helper already posted error comment
                return 0

            # Post review comments with suggested removal of legacy changelog lines
            commit_sha = pr_info.get("head", {}).get("sha", "")
            if added_lines and commit_sha:
                # Group consecutive lines for multi-line suggestions
                line_groups = self.legacy_handler.group_consecutive_lines(added_lines)
                logger.info(
                    f"Creating {len(line_groups)} review comment(s) for removal suggestions"
                )

                for start_line, end_line, group_content in line_groups:
                    is_single_line = start_line == end_line

                    if is_single_line:
                        # For single-line removals, use GitHub's suggestion syntax
                        suggestion_body = (
                            "This was converted to logchange format. Let's remove it.\n\n"
                            "```suggestion\n"
                            "```"
                        )
                        self.github_client.create_review_comment_with_suggestion(
                            commit_sha=commit_sha,
                            file_path=legacy_file,
                            line=end_line,
                            body=suggestion_body,
                        )
                    else:
                        # For multi-line removals, post a regular comment on the last line
                        # (GitHub's multi-line suggestion API has limitations)
                        suggestion_body = (
                            f"Lines {start_line}-{end_line}: This was converted to logchange format. "
                            "Please remove these lines."
                        )
                        self.github_client.create_review_comment_with_suggestion(
                            commit_sha=commit_sha,
                            file_path=legacy_file,
                            line=end_line,
                            body=suggestion_body,
                        )

            # Post the converted entry as a regular comment
            suggestion_comment = self._format_legacy_conversion_comment(
                generated_entry, legacy_file
            )
            self.github_client.comment_on_pr(suggestion_comment)

            self.set_output("legacy-converted", "true")
            logger.info("Legacy changelog successfully converted to logchange format")
            return 0

        except Exception as e:
            logger.error(f"Legacy conversion failed: {e}", exc_info=True)
            error_msg = f"Legacy changelog conversion failed: {str(e)}"
            self.github_client.comment_on_pr(f"❌ {error_msg}")
            self.set_output("generation-error", str(e))
            return 1

    def _format_legacy_conversion_comment(
        self, generated_entry: str, legacy_file: str
    ) -> str:
        """Format the converted legacy changelog entry as a suggestion comment"""
        # Get PR number and title for filename
        pr_info = self.github_event.get("pull_request", {})
        pr_number = pr_info.get("number", 0)
        pr_title = pr_info.get("title", "")

        # Generate slug-formatted filename
        filename = generate_changelog_slug(pr_number, pr_title)
        file_path = f"{self.changelog_path}/{filename}"

        return f"""🔄 **I've converted the changelog entry to logchange format!**

I detected changes to `{legacy_file}` and converted them to the logchange format below.

**Suggested Logchange Entry** for `{file_path}`:

```yaml
{generated_entry}
```

**What to do next:**

1. ✅ **Create** the logchange entry:
   - Create a new file at `{file_path}`
   - Copy the YAML above into it

2. ⚠️ **Remove** the original entry:
   - I've added suggested edits to remove the lines you added to `{legacy_file}`
   - Review the suggestions in the PR review and accept them

3. 📝 **Review** before merging:
   - Check the generated entry is accurate
   - Adjust if needed
   - Feel free to edit the logchange YAML

**Why?**
This project uses logchange format for changelog entries. Using logchange ensures consistency and better tooling support across all changelog entries.
"""


def main():
    """Entry point"""
    action = LogchangeAction()
    exit_code = action.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
