"""Changelog validation module"""

import logging
from typing import Any, Dict, List, Tuple

import yaml

logger = logging.getLogger(__name__)


class ChangelogValidator:
    """Validates changelog entries against logchange specification"""

    # Standard logchange fields
    STANDARD_FIELDS = {
        "title",  # Required
        "authors",
        "modules",
        "merge_requests",
        "issues",
        "type",
        "links",
        "important_notes",
        "configurations",
    }

    # Standard types
    STANDARD_TYPES = {
        "added",
        "changed",
        "deprecated",
        "removed",
        "fixed",
        "security",
        "dependency_update",
        "other",
    }

    def __init__(
        self,
        changelog_types: List[str] = None,
        mandatory_fields: List[str] = None,
        forbidden_fields: List[str] = None,
        optional_fields: List[str] = None,
    ):
        """
        Initialize validator with custom rules

        Args:
            changelog_types: Allowed changelog types
            mandatory_fields: Fields that must be present
            forbidden_fields: Fields that must not be present
            optional_fields: Allowed fields (if empty, all standard fields allowed)
        """
        self.changelog_types = changelog_types or list(self.STANDARD_TYPES)
        self.mandatory_fields = mandatory_fields or ["title"]
        self.forbidden_fields = forbidden_fields or []
        self.optional_fields = (
            optional_fields or []
        )  # Empty means all standard fields allowed

    def validate(self, yaml_content: str) -> Tuple[bool, List[str]]:
        """
        Validate changelog entry YAML

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Try to parse YAML
        try:
            entry = yaml.safe_load(yaml_content)
            if not entry:
                return False, ["YAML is empty"]

            if not isinstance(entry, dict):
                return False, ["YAML must be a dictionary/object"]

        except yaml.YAMLError as e:
            return False, [f"Invalid YAML: {str(e)}"]

        # Validate structure
        errors.extend(self._validate_structure(entry))

        # Validate types if present
        if "type" in entry:
            errors.extend(self._validate_type(entry["type"]))

        # Validate authors if present
        if "authors" in entry:
            errors.extend(self._validate_authors(entry["authors"]))

        # Validate configurations if present
        if "configurations" in entry:
            errors.extend(self._validate_configurations(entry["configurations"]))

        return len(errors) == 0, errors

    def _validate_structure(self, entry: Dict[str, Any]) -> List[str]:
        """Validate entry structure and fields"""
        errors = []

        # Check mandatory fields
        for field in self.mandatory_fields:
            if field not in entry or entry[field] is None:
                errors.append(f"Missing mandatory field: {field}")

        # Check forbidden fields
        for field in self.forbidden_fields:
            if field in entry and entry[field] is not None:
                errors.append(f"Forbidden field present: {field}")

        # Determine allowed fields
        if self.optional_fields:
            # Custom list restricts what's allowed
            allowed_fields = set(self.optional_fields) | set(self.mandatory_fields)
        else:
            # Default: allow all standard fields
            allowed_fields = self.STANDARD_FIELDS | set(self.mandatory_fields)

        # Check for unknown fields (only enforce with custom list)
        if self.optional_fields:
            for field in entry.keys():
                if field not in allowed_fields:
                    errors.append(f"Unknown field: {field}")

        # Validate specific field types
        if "title" in entry and not isinstance(entry["title"], str):
            errors.append("title must be a string")

        return errors

    def _validate_type(self, change_type: Any) -> List[str]:
        """Validate changelog type"""
        errors = []

        if not isinstance(change_type, str):
            errors.append("type must be a string")
            return errors

        if change_type not in self.changelog_types:
            errors.append(
                f'Invalid type "{change_type}". Allowed types: {", ".join(self.changelog_types)}'
            )

        return errors

    def _validate_authors(self, authors: Any) -> List[str]:
        """Validate authors field"""
        errors = []

        if not isinstance(authors, list):
            errors.append("authors must be a list")
            return errors

        for i, author in enumerate(authors):
            if not isinstance(author, dict):
                errors.append(f"authors[{i}] must be a dictionary")
                continue

            # Check for required author fields
            if "name" not in author or not author["name"]:
                errors.append(f'authors[{i}] missing or empty "name" field')

        return errors

    def _validate_configurations(self, configs: Any) -> List[str]:
        """Validate configurations field"""
        errors = []

        if not isinstance(configs, list):
            errors.append("configurations must be a list")
            return errors

        for i, config in enumerate(configs):
            if not isinstance(config, dict):
                errors.append(f"configurations[{i}] must be a dictionary")
                continue

            # Check required fields
            required = ["type", "action", "key"]
            for field in required:
                if field not in config or not config[field]:
                    errors.append(
                        f'configurations[{i}] missing or empty "{field}" field'
                    )

            # Validate action
            if "action" in config and config["action"] not in (
                "add",
                "update",
                "delete",
            ):
                errors.append(
                    f'configurations[{i}] action must be "add", "update", or "delete"'
                )

        return errors

    def generate_template(self) -> str:
        """Generate a template changelog entry YAML"""
        template = {
            "title": "Brief description of the change",
            "type": self.changelog_types[0] if self.changelog_types else "added",
            "authors": [
                {
                    "name": "Author Name",
                    "nick": "author-nick",
                    "url": "https://github.com/author",
                }
            ],
        }

        return yaml.dump(template, default_flow_style=False, sort_keys=False)
