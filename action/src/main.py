#!/usr/bin/env python3
"""
Logchange GitHub Action - Ensure changelog entries in pull requests
"""

import json
import logging
import os
import re
import sys
from typing import Any, Dict, List

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add src directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from changelog_generator import ChangelogGenerator
from changelog_validator import ChangelogValidator
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

    @staticmethod
    def _get_input(input_name: str, default: str = "") -> str:
        """Get input value, trying both hyphenated and underscored versions.

        GitHub Actions passes inputs with hyphens as-is in env vars (e.g., INPUT_ON-MISSING-ENTRY),
        but also provides underscored versions (e.g., INPUT_ON_MISSING_ENTRY).
        We try both for compatibility.
        """
        underscored = "INPUT_" + input_name.upper().replace("-", "_")
        hyphenated = "INPUT_" + input_name.upper()

        value = os.getenv(underscored) or os.getenv(hyphenated) or default
        logger.debug(
            f"_get_input({input_name}): underscore={underscored}={os.getenv(underscored)}, "
            f"hyphen={hyphenated}={os.getenv(hyphenated)}, result={value}"
        )
        return value

    def __init__(self):
        """Initialize the action with environment variables"""
        # GitHub context
        self.github_event = self._load_github_event()
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.github_api_url = os.getenv("GITHUB_API_URL", "https://api.github.com")

        # Action inputs
        self.changelog_path = self._get_input("changelog-path", "changelog/unreleased")
        self.on_missing_entry = self._get_input("on-missing-entry", "fail").lower()
        self.missing_entry_message = self._get_input(
            "missing-entry-message",
            "This pull request is missing a logchange entry in the changelog/unreleased directory",
        )
        self.skip_files_regex = self._get_input("skip-files-regex", "")
        self.claude_token = self._get_input("claude-token", "")
        logger.debug(
            f"Claude token: {'***' if self.claude_token else '(not provided)'}"
        )
        self.claude_model = self._get_input("claude-model", "claude-opus-4-1-20250805")
        self.claude_system_prompt = self._get_input("claude-system-prompt", "")
        self.changelog_language = self._get_input("changelog-language", "English")
        self.max_tokens_context = int(self._get_input("max-tokens-context", "5000"))
        self.max_tokens_per_file = int(self._get_input("max-tokens-per-file", "1000"))

        # Parse configuration
        self.changelog_types = self._parse_list_input(
            "changelog-types",
            "added,changed,deprecated,removed,fixed,security,dependency_update,other",
        )
        self.mandatory_fields = self._parse_list_input("mandatory-fields", "title")
        self.forbidden_fields = self._parse_list_input("forbidden-fields", "")
        self.optional_fields = self._parse_list_input("optional-fields", "")

        # Legacy changelog configuration (disabled by default)
        self.legacy_changelog_paths = self._parse_list_input(
            "legacy-changelog-paths", ""
        )
        self.on_legacy_entry = self._get_input("on-legacy-entry", "convert").lower()
        self.on_legacy_and_logchange = self._get_input(
            "on-legacy-and-logchange", "warn"
        ).lower()
        self.legacy_entry_message = self._get_input(
            "legacy-entry-message",
            "I detected a legacy changelog entry. Converting it to logchange format...",
        )
        self.legacy_conflict_message = self._get_input(
            "legacy-conflict-message",
            "This PR contains both legacy and logchange changelog entries. Please use only logchange format.",
        )

        self.validation_fail_message = self._get_input(
            "validation-fail-message",
            "The changelog entry does not comply with the required format",
        )
        self.validation_fail_workflow = (
            self._get_input("validation-fail-workflow", "true").lower() == "true"
        )

        # Comment mode configuration
        self.comment_mode = self._get_input("comment-mode", "review-comment").lower()
        logger.info(f"Comment mode: {self.comment_mode}")

        # Metadata extraction configuration
        self.external_issue_regex = self._get_input("external-issue-regex", "")
        self.external_issue_url_template = self._get_input(
            "external-issue-url-template", ""
        )
        self.generate_important_notes = (
            self._get_input("generate-important-notes", "true").lower() == "true"
        )
        self.github_issue_detection = (
            self._get_input("github-issue-detection", "true").lower() == "true"
        )
        self.issue_tracker_url_detection = (
            self._get_input("issue-tracker-url-detection", "true").lower() == "true"
        )

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
        self.generator = None
        if self.on_missing_entry == "generate" and self.claude_token:
            self.generator = ChangelogGenerator(
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

    def _load_github_event(self) -> Dict[str, Any]:
        """Load GitHub event from environment"""
        event_path = os.getenv("GITHUB_EVENT_PATH")
        if not event_path or not os.path.exists(event_path):
            logger.warning("GITHUB_EVENT_PATH not found or not set")
            return {}

        try:
            with open(event_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load GitHub event: {e}")
            return {}

    def _parse_list_input(self, input_name: str, default: str) -> List[str]:
        """Parse comma-separated input into a list"""
        value = self._get_input(input_name, default)
        if not value:
            return []
        return [item.strip() for item in value.split(",") if item.strip()]

    def set_output(self, name: str, value: str) -> None:
        """Set GitHub Actions output"""
        output_file = os.getenv("GITHUB_OUTPUT")
        if output_file:
            with open(output_file, "a") as f:
                f.write(f"{name}={value}\n")
        logger.info(f"Output: {name}={value}")

    def run(self) -> int:
        """Main action execution"""
        try:
            # Check if this is a PR workflow
            if not self._is_pr_workflow():
                logger.info("Not a PR workflow, skipping changelog check")
                return 0

            logger.info("Starting logchange action")

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

    def _should_skip_changelog(self, pr_files: List[str]) -> bool:
        """Check if all files match skip pattern"""
        if not self.skip_files_regex:
            return False

        try:
            pattern = re.compile(self.skip_files_regex)
            return all(pattern.match(f) for f in pr_files)
        except re.error as e:
            logger.warning(f"Invalid skip regex pattern: {e}")
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
                self.github_client.comment_or_review(
                    f"{emoji} **Changelog {level}**: {file_path}\n\n{str(e)}",
                    mode=self.comment_mode,
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

        self.github_client.comment_or_review(
            f"{emoji} **{title}**: {self.validation_fail_message}\n\n"
            f"**File**: {file_path}\n"
            f'**{level.capitalize() + ("s" if level == "warning" else "")}**:\n{errors_text}',
            mode=self.comment_mode,
        )

    def _handle_missing_changelog(self, pr_files: List[str]) -> int:
        """Handle case where changelog entry is missing"""
        logger.info(f"No changelog entry found, action: {self.on_missing_entry}")

        if self.on_missing_entry == "fail":
            logger.error(self.missing_entry_message)
            self.github_client.comment_or_review(
                f"❌ {self.missing_entry_message}", mode=self.comment_mode
            )
            self.set_output("changelog-found", "false")
            return 1

        elif self.on_missing_entry == "warn":
            logger.warning(self.missing_entry_message)
            self.github_client.comment_or_review(
                f"⚠️ {self.missing_entry_message}", mode=self.comment_mode
            )
            self.set_output("changelog-found", "false")
            return 0

        elif self.on_missing_entry == "generate":
            if not self.generator:
                logger.error("Claude generation requested but no API token provided")
                self.github_client.comment_or_review(
                    "❌ Changelog generation failed: No Claude API token provided",
                    mode=self.comment_mode,
                )
                self.set_output("generation-error", "No Claude API token provided")
                return 1

            try:
                # Get PR diff
                pr_diff = self.github_client.get_pr_diff(pr_files)
                logger.info(f"PR diff size: {len(pr_diff)} characters")

                # Generate changelog
                logger.info("Generating changelog with Claude...")
                generated_entry = self.generator.generate(
                    pr_diff, self.github_event.get("pull_request", {})
                )

                if not generated_entry:
                    logger.error("Failed to generate changelog")
                    self.github_client.comment_or_review(
                        "❌ Changelog generation failed: Could not generate valid entry",
                        mode=self.comment_mode,
                    )
                    self.set_output(
                        "generation-error", "Could not generate valid entry"
                    )
                    return 1

                # Post as suggestion
                suggestion_comment = self._format_suggestion_comment(generated_entry)
                self.github_client.comment_or_review(
                    suggestion_comment, mode=self.comment_mode
                )

                self.set_output("changelog-found", "false")
                self.set_output("changelog-generated", "true")
                logger.info("Changelog generated successfully")
                return 0

            except Exception as e:
                logger.error(f"Generation failed: {e}", exc_info=True)
                error_msg = f"Changelog generation failed: {str(e)}"
                self.github_client.comment_or_review(
                    f"❌ {error_msg}", mode=self.comment_mode
                )
                self.set_output("generation-error", str(e))
                return 1

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

Or let me know if you'd like me to adjust anything!
"""

    def _handle_legacy_conflict(
        self, legacy_files: List[str], changelog_files: List[str]
    ) -> int:
        """Handle case where both legacy and logchange entries exist"""
        logger.warning(
            f"Conflict: {len(legacy_files)} legacy files and {len(changelog_files)} logchange files found"
        )

        if self.on_legacy_and_logchange == "fail":
            self.github_client.comment_or_review(
                f"❌ {self.legacy_conflict_message}", mode=self.comment_mode
            )
            self.set_output("legacy-conflict", "true")
            return 1
        elif self.on_legacy_and_logchange == "warn":
            self.github_client.comment_or_review(
                f"⚠️ {self.legacy_conflict_message}", mode=self.comment_mode
            )
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
            self.github_client.comment_or_review(
                f"⚠️ {self.legacy_entry_message}", mode=self.comment_mode
            )
            return 0

        elif self.on_legacy_entry == "fail":
            logger.error("Legacy changelog entry found, failing as configured")
            self.github_client.comment_or_review(
                f"❌ {self.legacy_entry_message}", mode=self.comment_mode
            )
            return 1

        elif self.on_legacy_entry == "convert":
            # Attempt to convert legacy entry to logchange format
            if not self.generator:
                logger.error(
                    "Legacy conversion requested but no Claude API token provided"
                )
                self.github_client.comment_or_review(
                    "❌ Legacy changelog conversion failed: No Claude API token provided",
                    mode=self.comment_mode,
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
                self.github_client.comment_or_review(
                    f"❌ Could not extract changelog entry from {legacy_file}",
                    mode=self.comment_mode,
                )
                return 1

            # Extract the changelog entry from the diff
            entry_text = self.legacy_handler.extract_changelog_entry_from_diff(pr_diff)
            if not entry_text:
                logger.error(
                    f"Could not extract changelog entry from diff of {legacy_file}"
                )
                self.github_client.comment_or_review(
                    f"⚠️ Found changes to {legacy_file} but could not extract changelog entry",
                    mode=self.comment_mode,
                )
                return 0  # Don't fail, just warn

            logger.info(f"Extracted {len(entry_text)} characters from legacy changelog")

            # Build context about the legacy entry
            context = self.legacy_handler.build_legacy_context(entry_text)
            logger.info(f"Legacy entry context: {context}")

            # Create custom prompt for conversion
            pr_info = self.github_event.get("pull_request", {})
            conversion_prompt = self.legacy_handler.create_conversion_prompt(
                entry_text, pr_info, context
            )

            # Generate logchange entry from legacy entry
            logger.info("Sending legacy entry to Claude for conversion...")
            generated_entry = self.generator.generate(
                entry_text, pr_info, custom_prompt=conversion_prompt
            )

            if not generated_entry:
                logger.error("Failed to convert legacy changelog entry")
                self.github_client.comment_or_review(
                    "❌ Could not convert legacy changelog entry to logchange format",
                    mode=self.comment_mode,
                )
                self.set_output("generation-error", "Failed to convert legacy entry")
                return 1

            # Post the converted entry as a suggestion
            suggestion_comment = self._format_legacy_conversion_comment(
                generated_entry, legacy_file
            )
            self.github_client.comment_or_review(
                suggestion_comment, mode=self.comment_mode
            )

            self.set_output("legacy-converted", "true")
            logger.info("Legacy changelog successfully converted to logchange format")
            return 0

        except Exception as e:
            logger.error(f"Legacy conversion failed: {e}", exc_info=True)
            error_msg = f"Legacy changelog conversion failed: {str(e)}"
            self.github_client.comment_or_review(
                f"❌ {error_msg}", mode=self.comment_mode
            )
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

        return f"""🔄 **I've converted the legacy changelog entry to logchange format!**

I detected a change to `{legacy_file}` and converted it to the logchange format below.

**Suggested Logchange Entry** for `{file_path}`:

```yaml
{generated_entry}
```

**What to do next:**

1. ✅ **Create** the logchange entry:
   - Create a new file at `{file_path}`
   - Copy the YAML above into it

2. ⚠️ **Revert** the legacy change:
   - Remove or revert your changes to `{legacy_file}`
   - OR update `{legacy_file}` to not include this entry (if it has multiple)

3. 📝 **Review** before merging:
   - Check the generated entry is accurate
   - Adjust if needed
   - Feel free to edit the logchange YAML

**Why?**
This project uses logchange format for changelog entries, not the traditional {legacy_file} format. Using logchange ensures consistency and better tooling support.

Let me know if you'd like me to adjust the conversion!
"""


def main():
    """Entry point"""
    action = LogchangeAction()
    exit_code = action.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
