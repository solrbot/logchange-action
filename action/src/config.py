"""
Configuration loading and parsing for Logchange Action
"""

import json
import logging
import os
from typing import Any, Dict, List

from exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class ActionConfig:
    """Loads and validates action configuration from environment variables"""

    def __init__(self):
        """Initialize configuration from environment variables"""
        # GitHub context
        self.github_event = self._load_github_event()
        self.github_token = os.getenv("GITHUB_TOKEN", "")
        self.github_api_url = os.getenv("GITHUB_API_URL", "https://api.github.com")

        # Basic configuration
        self.changelog_path = self._get_input("changelog-path", "changelog/unreleased")
        self.on_missing_entry = self._get_input("on-missing-entry", "fail").lower()
        self.missing_entry_message = self._get_input(
            "missing-entry-message",
            "This pull request is missing a logchange entry in the changelog/unreleased directory",
        )
        self.skip_files_regex = self._get_input("skip-files-regex", "")
        self.skip_changelog_labels = self._parse_list_input("skip-changelog-labels", "")

        # Claude configuration
        self.claude_token = self._get_input("claude-token", "")
        logger.debug(
            f"Claude token: {'***' if self.claude_token else '(not provided)'}"
        )
        self.claude_model = self._get_input("claude-model", "claude-opus-4-1-20250805")
        self.claude_system_prompt = self._get_input("claude-system-prompt", "")
        self.changelog_language = self._get_input("changelog-language", "English")
        self.max_tokens_context = int(self._get_input("max-tokens-context", "5000"))
        self.max_tokens_per_file = int(self._get_input("max-tokens-per-file", "1000"))

        # Validation configuration
        self.changelog_types = self._parse_list_input(
            "changelog-types",
            "added,changed,deprecated,removed,fixed,security,dependency_update,other",
        )
        self.mandatory_fields = self._parse_list_input("mandatory-fields", "title")
        self.forbidden_fields = self._parse_list_input("forbidden-fields", "")
        self.optional_fields = self._parse_list_input("optional-fields", "")

        # Legacy changelog configuration (enabled by default with CHANGELOG.md)
        self.managed_changelog_paths = self._parse_list_input(
            "legacy-changelog-paths", "CHANGELOG.md"
        )
        self.on_managed_entry = self._get_input("on-legacy-entry", "convert").lower()
        self.on_managed_and_logchange = self._get_input(
            "on-legacy-and-logchange", "warn"
        ).lower()
        self.managed_entry_message = self._get_input(
            "legacy-entry-message",
            "I detected a legacy changelog entry. Converting it to logchange format...",
        )
        self.managed_conflict_message = self._get_input(
            "managed-conflict-message",
            "This PR contains both legacy and logchange changelog entries. Please use only logchange format.",
        )

        # Validation messages
        self.validation_fail_message = self._get_input(
            "validation-fail-message",
            "The changelog entry does not comply with the required format",
        )
        self.validation_fail_workflow = (
            self._get_input("validation-fail-workflow", "true").lower() == "true"
        )

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

        # Dry-run mode
        self.dry_run = self._get_input("dry-run", "false").lower() == "true"

        # Validate configuration
        self._validate_config()

    @staticmethod
    def _get_input(input_name: str, default: str = "") -> str:
        """Get input value, trying both hyphenated and underscored versions.

        GitHub Actions passes inputs with hyphens as-is in env vars (e.g., INPUT_ON-MISSING-ENTRY),
        but also provides underscored versions (e.g., INPUT_ON_MISSING_ENTRY).
        We try both for compatibility.

        Args:
            input_name: Input name (with hyphens)
            default: Default value if not found

        Returns:
            Input value from environment or default
        """
        underscored = "INPUT_" + input_name.upper().replace("-", "_")
        hyphenated = "INPUT_" + input_name.upper()

        value = os.getenv(underscored) or os.getenv(hyphenated) or default
        logger.debug(
            f"_get_input({input_name}): underscore={underscored}={os.getenv(underscored)}, "
            f"hyphen={hyphenated}={os.getenv(hyphenated)}, result={value}"
        )
        return value

    @staticmethod
    def _parse_list_input(input_name: str, default: str) -> List[str]:
        """Parse comma-separated input into a list.

        Args:
            input_name: Input name
            default: Default value if not found

        Returns:
            List of parsed items
        """
        value = ActionConfig._get_input(input_name, default)
        if not value:
            return []
        return [item.strip() for item in value.split(",") if item.strip()]

    @staticmethod
    def _load_github_event() -> Dict[str, Any]:
        """Load GitHub event from environment.

        Returns:
            GitHub event data as dictionary, or empty dict if not available
        """
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

    def _validate_config(self) -> None:
        """Validate configuration values.

        Raises:
            ConfigurationError: If configuration is invalid
        """
        # Validate on_missing_entry mode
        if self.on_missing_entry not in ("fail", "warn", "generate"):
            raise ConfigurationError(
                f"Invalid on-missing-entry mode: {self.on_missing_entry}. "
                "Must be one of: fail, warn, generate"
            )

        # Validate on_legacy_entry mode
        if self.on_managed_entry not in ("convert", "warn", "fail", "remove"):
            raise ConfigurationError(
                f"Invalid on-legacy-entry mode: {self.on_managed_entry}. "
                "Must be one of: fail, warn, remove, convert"
            )

        # Validate on_legacy_and_logchange mode
        if self.on_managed_and_logchange not in ("fail", "warn", "ignore"):
            raise ConfigurationError(
                f"Invalid on-legacy-and-logchange mode: {self.on_managed_and_logchange}. "
                "Must be one of: fail, warn, ignore"
            )

        # Warn if generate mode requested but no Claude token
        if self.on_missing_entry == "generate" and not self.claude_token:
            logger.warning(
                "on-missing-entry is set to 'generate' but claude-token is not provided. "
                "Falling back to 'warn' mode."
            )

        # Validate max_tokens values
        if self.max_tokens_context <= 0:
            raise ConfigurationError(
                f"max-tokens-context must be positive, got: {self.max_tokens_context}"
            )

        if self.max_tokens_per_file <= 0:
            raise ConfigurationError(
                f"max-tokens-per-file must be positive, got: {self.max_tokens_per_file}"
            )

        # Validate changelog types
        if not self.changelog_types:
            raise ConfigurationError("changelog-types cannot be empty")

        # Validate mandatory fields
        if not self.mandatory_fields:
            logger.warning("No mandatory fields configured. Using default: title")
            self.mandatory_fields = ["title"]

        logger.info("Configuration validated successfully")

    def get_summary(self) -> str:
        """Get a human-readable summary of the configuration.

        Returns:
            Configuration summary string
        """
        summary_lines = [
            "=== Logchange Action Configuration ===",
            f"Changelog path: {self.changelog_path}",
            f"On missing entry: {self.on_missing_entry}",
            f"Skip files regex: {self.skip_files_regex or '(none)'}",
            f"Skip changelog labels: {', '.join(self.skip_changelog_labels) if self.skip_changelog_labels else '(none)'}",
            f"Validation types: {', '.join(self.changelog_types)}",
            f"Mandatory fields: {', '.join(self.mandatory_fields)}",
            f"Forbidden fields: {', '.join(self.forbidden_fields) if self.forbidden_fields else '(none)'}",
            f"Legacy support: {len(self.managed_changelog_paths)} paths configured",
            f"Dry-run mode: {'enabled' if self.dry_run else 'disabled'}",
            "=" * 40,
        ]
        return "\n".join(summary_lines)
