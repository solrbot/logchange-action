"""Changelog generation using Claude AI"""

import logging
import os
import re
from typing import Any, Dict, Optional

import requests
import yaml

logger = logging.getLogger(__name__)


def _load_template(template_name: str) -> str:
    """Load a prompt template from file.

    Args:
        template_name: Name of template file (without .txt extension)

    Returns:
        Template contents as string
    """
    template_path = os.path.join(
        os.path.dirname(__file__), "prompts", f"{template_name}.txt"
    )

    try:
        with open(template_path, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        logger.warning(f"Template file not found: {template_path}")
        return ""
    except IOError as e:
        logger.error(f"Failed to load template {template_name}: {e}")
        return ""


class ChangelogGenerator:
    """Generate changelog entries using Claude API"""

    @staticmethod
    def _get_default_system_prompt() -> str:
        """Get default system prompt, loading from template if available."""
        template = _load_template("default_system_prompt")
        if template:
            return template
        # Fallback to inline version if template not found
        logger.warning("Using fallback system prompt")
        return """You are an expert software engineer specializing in changelog management.
Your task is to generate a logchange-formatted YAML entry based on the provided pull request information.

Create a changelog entry that:
1. Has a clear, concise title describing the change, most often in a single sentence. If the change is comprehensive or complex, consider including a summary of max 400 characters. Break long titles (>80 chars) using YAML line continuation syntax.
2. Includes the MOST SPECIFIC and ACCURATE type (added, changed, fixed, security, dependency_update, removed, etc.)
3. Lists relevant authors with proper structure
4. Extracts issue numbers from PR description (Fixes #123, closes #456, etc.) as 'issues' field with numbers only (no '#')
5. Follows the logchange specification EXACTLY - only use valid fields

IMPORTANT: If the PR description contradicts the actual code changes (shown in the diff), prioritize the code changes over the description. The diff represents the actual implementation and is more reliable than potentially outdated PR descriptions. Base your title on what the code actually does.

CRITICAL: Only use valid logchange fields. Never hallucinate fields like 'references', 'contributors', or 'fixes'. Always verify your output is valid YAML.

Always output ONLY valid YAML that can be parsed directly, with no additional text or markdown formatting.
The YAML should be a single object with the required fields."""

    @staticmethod
    def _get_important_notes_instruction() -> str:
        """Get important notes instruction, loading from template if available."""
        template = _load_template("important_notes_instruction")
        if template:
            return template
        # Fallback to inline version if template not found
        logger.warning("Using fallback important notes instruction")
        return """## Important Notes

Consider whether to add an 'important_notes' field to highlight:
- Breaking changes
- Security implications
- Major deprecations
- Migration guidance needed
- Performance impacts
- Database migration requirements

Only include 'important_notes' if the change significantly impacts users or requires attention during upgrades."""

    def _build_validation_rules_section(
        self, changelog_types: list, forbidden_fields: Optional[list] = None
    ) -> str:
        """
        Build validation and self-inspection section with configured changelog types

        Args:
            changelog_types: List of allowed changelog types from configuration
            forbidden_fields: List of fields that must not be used (from configuration)

        Returns:
            Validation rules section as a string
        """
        types_list = ", ".join(changelog_types)
        forbidden_fields = forbidden_fields or []

        # Standard fields that are always invalid (common mistakes/hallucinations)
        invalid_fields_lines = [
            "- references (not a valid logchange field)",
            "- contributors (use authors instead)",
            "- fixes (use issues instead)",
        ]

        # Add user-configured forbidden fields
        for field in forbidden_fields:
            invalid_fields_lines.append(f"- {field} (forbidden by configuration)")

        # Build invalid fields section only if there are fields to list
        invalid_fields_section = ""
        if invalid_fields_lines:
            invalid_fields_text = "\n".join(invalid_fields_lines)
            invalid_fields_section = f"""
INVALID FIELDS - DO NOT USE:
{invalid_fields_text}
"""

        return f"""## YAML Field Validation Rules

VALID LOGCHANGE FIELDS (only these allowed):
- title (required, string, max 200 chars, break long titles at ~80 chars with YAML continuation)
- type (required, must be one of: {types_list})
- description (optional, string)
- authors (required, list of {{name, nick?, url?}})
- modules (optional, list of strings)
- issues (optional, list of NUMBERS ONLY, no '#' symbol. Extract from PR description and legacy text)
- links (optional, list of {{name, url}})
- important_notes (optional, string)
- merge_requests (optional, list of numbers){invalid_fields_section}
## Self-Inspection Before Output

BEFORE outputting the YAML, verify:
1. title: Is it under 200 characters? If >80 chars, break it using YAML line continuation (|, >, or multi-line)
2. type: Is it exactly one of the allowed types ({types_list})? NOT just "changed" for everything - be precise
3. authors: Is it a list? Each entry has 'name' field? No extra/invalid fields?
4. issues: Contains ONLY numbers (e.g., 123, not "#123")? Extracted from text like "Fixes #123" or "(#111)"?
5. All fields: NO hallucinated fields or forbidden fields?
6. YAML syntax: Valid YAML that parses without errors?

If you find any violations, CORRECT THEM before outputting the final YAML.

## Type Detection Guidelines

Use the MOST SPECIFIC type from the allowed list above. Examples for common types:
- "removed" for deletions, deprecations of features
- "fixed" for bug fixes, corrections
- "security" for security issues
- "dependency_update" for dependency changes
- "added" for new features only
- "changed" for modifications that aren't fixes"""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-opus-4-1-20250805",
        system_prompt: Optional[str] = None,
        changelog_language: str = "English",
        max_tokens_context: int = 5000,
        max_tokens_per_file: int = 1000,
        changelog_types: Optional[list] = None,
        mandatory_fields: Optional[list] = None,
        forbidden_fields: Optional[list] = None,
        generate_important_notes: bool = True,
        external_issue_regex: Optional[str] = None,
        external_issue_url_template: Optional[str] = None,
    ):
        """
        Initialize changelog generator

        Args:
            api_key: Claude API key
            model: Claude model to use
            system_prompt: Custom system prompt
            changelog_language: Language for the changelog entry
            max_tokens_context: Maximum tokens for context
            max_tokens_per_file: Maximum tokens per file in diff
            changelog_types: Allowed changelog types
            mandatory_fields: Fields that must be present in generated entry
            forbidden_fields: Fields that must not be present in generated entry
            generate_important_notes: Whether to instruct AI to generate important_notes
            external_issue_regex: Regex to detect external issues
            external_issue_url_template: URL template for external issues
        """
        self.api_key = api_key
        self.model = model
        self.changelog_language = changelog_language
        self.max_tokens_context = max_tokens_context
        self.max_tokens_per_file = max_tokens_per_file
        self.generate_important_notes = generate_important_notes
        self.external_issue_regex = external_issue_regex
        self.external_issue_url_template = external_issue_url_template
        self.changelog_types = changelog_types or [
            "added",
            "changed",
            "deprecated",
            "removed",
            "fixed",
            "security",
            "dependency_update",
            "other",
        ]
        self.mandatory_fields = mandatory_fields or ["title"]
        self.forbidden_fields = forbidden_fields or []

        # Build system prompt
        lang_instruction = (
            f"Write the entry in {changelog_language}."
            if changelog_language != "English"
            else ""
        )

        # Determine if using custom system prompt
        using_custom_prompt = system_prompt is not None

        prompt_parts = []

        # Always add base prompt (either custom or default)
        if using_custom_prompt:
            prompt_parts.append(system_prompt)
        else:
            prompt_parts.append(self._get_default_system_prompt())

        # Add configuration-based sections only if using default prompt
        # If user provides custom prompt, they need to handle these themselves
        if not using_custom_prompt:
            # Add validation and self-inspection guidelines with configured types and forbidden fields
            prompt_parts.append(
                self._build_validation_rules_section(
                    self.changelog_types, self.forbidden_fields
                )
            )

            # Add important_notes instruction if enabled
            if self.generate_important_notes:
                prompt_parts.append(self._get_important_notes_instruction())

        # Always add language instruction (even with custom prompt)
        prompt_parts.append(lang_instruction)

        self.system_prompt = "\n".join(p for p in prompt_parts if p).strip()

        self.api_url = "https://api.anthropic.com/v1/messages"
        self._setup_session()

    def _setup_session(self) -> None:
        """Set up HTTP session with authentication headers"""
        self.session = requests.Session()
        self.session.headers.update(
            {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
        )

    def generate(
        self, pr_diff: str, pr_info: Dict[str, Any], custom_prompt: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate a changelog entry

        Args:
            pr_diff: The PR diff content
            pr_info: PR information from GitHub event
            custom_prompt: Optional custom user prompt (overrides default message building)

        Returns:
            Generated YAML changelog entry or None if generation failed
        """
        try:
            # Use custom prompt if provided, otherwise build from PR info
            if custom_prompt:
                user_message = custom_prompt
                logger.debug("Using custom prompt for generation")
            else:
                # Extract PR information
                pr_title = pr_info.get("title", "")
                pr_body = pr_info.get("body", "")
                pr_author = pr_info.get("user", {}).get("login", "unknown")
                pr_author_url = pr_info.get("user", {}).get("html_url", "")
                pr_labels = [
                    label.get("name", "") for label in pr_info.get("labels", [])
                ]

                # Extract commit authors if available
                commit_authors = self._extract_commit_authors(pr_info)

                # Build the user message
                user_message = self._build_user_message(
                    pr_title=pr_title,
                    pr_body=pr_body,
                    pr_author=pr_author,
                    pr_author_url=pr_author_url,
                    pr_labels=pr_labels,
                    pr_diff=pr_diff,
                    commit_authors=commit_authors,
                )

            logger.debug(f"Sending request to Claude API (model: {self.model})")

            # Call Claude API with session
            response = self.session.post(
                self.api_url,
                json={
                    "model": self.model,
                    "max_tokens": 1024,
                    "system": self.system_prompt,
                    "messages": [{"role": "user", "content": user_message}],
                },
            )

            if response.status_code != 200:
                logger.error(
                    f"Claude API error: {response.status_code} - {response.text}"
                )
                return None

            result = response.json()
            generated_text = result["content"][0]["text"]

            # Extract YAML from markdown code blocks if present
            generated_text = self._extract_yaml(generated_text)

            # Validate that it's valid YAML
            try:
                yaml.safe_load(generated_text)
                logger.info("Successfully generated and validated changelog entry")
                return generated_text.strip()
            except yaml.YAMLError as e:
                logger.error(f"Generated text is not valid YAML: {e}")
                logger.debug(f"Generated text: {generated_text}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to call Claude API: {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"Failed to parse Claude response: {e}")
            return None

    def generate_with_validation(
        self,
        pr_diff: str,
        pr_info: Dict[str, Any],
        validator: Any,
        custom_prompt: Optional[str] = None,
    ) -> tuple[Optional[str], bool, str]:
        """
        Generate a changelog entry and validate it against configured rules.
        Retries up to 2 times if validation fails.

        Args:
            pr_diff: The PR diff content
            pr_info: PR information from GitHub event
            validator: ChangelogValidator instance with configured rules
            custom_prompt: Optional custom user prompt

        Returns:
            Tuple of (generated_entry, is_valid, message)
            - generated_entry: The YAML string or None
            - is_valid: Whether entry passed validation
            - message: Human-readable message about the result or validation errors
        """
        max_retries = 2
        attempt = 0
        validation_errors = []

        while attempt <= max_retries:
            attempt += 1
            logger.info(
                f"Generating changelog entry (attempt {attempt}/{max_retries + 1})"
            )

            # Generate entry
            if attempt == 1:
                # First attempt: use provided prompt
                generated_entry = self.generate(pr_diff, pr_info, custom_prompt)
            else:
                # Retry attempts: use enhanced prompt with validation context
                retry_prompt = self._build_retry_prompt(
                    custom_prompt, validation_errors, pr_diff, pr_info
                )
                generated_entry = self.generate(pr_diff, pr_info, retry_prompt)

            if not generated_entry:
                logger.error(f"Generation failed on attempt {attempt}")
                if attempt <= max_retries:
                    logger.info(f"Retrying... (attempt {attempt + 1})")
                    continue
                else:
                    return None, False, "Failed to generate valid YAML after retries"

            # Validate the generated entry
            is_valid, validation_errors = validator.validate(generated_entry)

            if is_valid:
                logger.info(f"Entry passed validation on attempt {attempt}")
                return (
                    generated_entry,
                    True,
                    "Entry generated and validated successfully",
                )

            # Entry invalid - log errors and retry if attempts remain
            error_message = "; ".join(validation_errors)
            logger.warning(f"Validation failed on attempt {attempt}: {error_message}")

            if attempt <= max_retries:
                logger.info(
                    f"Retrying with validation feedback... (attempt {attempt + 1})"
                )
                continue
            else:
                # All retries exhausted
                logger.error(
                    f"Entry failed validation after {max_retries + 1} attempts"
                )
                return None, False, f"Entry failed validation: {error_message}"

        # Should not reach here, but just in case
        return None, False, "Unexpected error in generate_with_validation"

    def _build_retry_prompt(
        self,
        original_prompt: Optional[str],
        validation_errors: list,
        pr_diff: str,
        pr_info: Dict[str, Any],
    ) -> str:
        """
        Build a retry prompt that includes validation feedback.

        Args:
            original_prompt: The original custom prompt if provided
            validation_errors: List of validation error messages
            pr_diff: The PR diff
            pr_info: PR information

        Returns:
            Enhanced prompt with validation context
        """
        errors_text = "\n".join(f"  - {error}" for error in validation_errors)

        retry_context = f"""Your previous generated changelog entry had validation errors. Please fix these issues:

{errors_text}

Try again, ensuring your output addresses each validation error above."""

        if original_prompt:
            # If there was a custom prompt, append retry context to it
            return f"{original_prompt}\n\n{retry_context}"
        else:
            # Otherwise, build a complete prompt with the diff and retry context
            pr_title = pr_info.get("title", "")
            pr_body = pr_info.get("body", "")
            pr_author = pr_info.get("user", {}).get("login", "unknown")

            return f"""Generate a logchange-formatted YAML changelog entry for this PR.

PR Title: {pr_title}

PR Description:
{pr_body}

Author: {pr_author}

Changes:
```diff
{pr_diff}
```

{retry_context}

Output ONLY the corrected YAML with no additional text."""

    def _extract_yaml(self, text: str) -> str:
        """Extract YAML from markdown code blocks if present"""
        # Try to extract from ```yaml ... ``` or ``` ... ``` block
        match = re.search(r"```(?:yaml)?\s*\n(.*?)\n```", text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Return as-is if no code block found
        return text.strip()

    def _extract_commit_authors(self, pr_info: Dict[str, Any]) -> list:
        """Extract unique authors from commits if available"""
        authors = set()
        commits = (
            pr_info.get("commits", [])
            if isinstance(pr_info.get("commits"), list)
            else []
        )

        for commit in commits:
            author_info = commit.get("author", {})
            if author_info and isinstance(author_info, dict):
                login = author_info.get("login")
                if login:
                    authors.add(login)

        return sorted(list(authors))

    def _build_user_message(
        self,
        pr_title: str,
        pr_body: str,
        pr_author: str,
        pr_author_url: str,
        pr_labels: list,
        pr_diff: str,
        commit_authors: list = None,
    ) -> str:
        """Build the user message for Claude"""
        if commit_authors is None:
            commit_authors = []

        # Build validation rules section
        rules_section = self._build_validation_rules()

        # Build authors section
        authors_section = self._build_authors_section(
            pr_author, commit_authors, pr_author_url
        )

        # Build language instruction
        language_section = (
            f"Write the changelog entry in {self.changelog_language}."
            if self.changelog_language != "English"
            else ""
        )

        # Build types list
        types_list = ", ".join(self.changelog_types)

        message = f"""Generate a logchange changelog entry for the following pull request:

**PR Title:** {pr_title}

**PR Description:**
{pr_body if pr_body else '(No description provided)'}

**Primary Author:** {pr_author}
{f'**Author URL:** {pr_author_url}' if pr_author_url else ''}

{authors_section}

**Labels:** {', '.join(pr_labels) if pr_labels else 'None'}

**Allowed entry types:**
{types_list}

**Language:**
{language_section if language_section else 'English (default)'}

**Validation Rules:**
{rules_section}

**Changes:**
```diff
{pr_diff}
```

Based on the above information, generate a valid logchange YAML entry that accurately describes this change.
Make sure the generated YAML is valid and can be parsed directly. Output ONLY the YAML with no additional text."""

        return message

    def _build_validation_rules(self) -> str:
        """Build validation rules section for the prompt"""
        rules = []

        if self.mandatory_fields:
            rules.append(f"- REQUIRED fields: {', '.join(self.mandatory_fields)}")

        if self.forbidden_fields:
            rules.append(f"- FORBIDDEN fields: {', '.join(self.forbidden_fields)}")

        if not rules:
            rules.append("- Standard logchange format (title, type, authors)")

        return "\n".join(rules)

    def _build_authors_section(
        self, primary_author: str, commit_authors: list, author_url: str
    ) -> str:
        """Build authors information section"""
        if not commit_authors:
            return ""

        authors_text = "**Contributors to this PR:**\n"
        all_authors = [primary_author] + [
            a for a in commit_authors if a != primary_author
        ]
        authors_text += ", ".join(all_authors)

        return authors_text
