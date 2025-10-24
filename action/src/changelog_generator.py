"""Changelog generation using Claude AI"""

import logging
import re
import requests
import yaml
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class ChangelogGenerator:
    """Generate changelog entries using Claude API"""

    DEFAULT_SYSTEM_PROMPT = """You are an expert software engineer specializing in changelog management.
Your task is to generate a logchange-formatted YAML entry based on the provided pull request information.

Create a changelog entry that:
1. Has a clear, concise title describing the change, most often in a single sentence. If the change is comprehensive or complex, consider including a summary of max 400 characters.
2. Includes the appropriate type (added, changed, fixed, security, dependency_update, etc.)
3. Lists relevant authors
4. Follows the logchange specification

IMPORTANT: If the PR description contradicts the actual code changes (shown in the diff), prioritize the code changes over the description. The diff represents the actual implementation and is more reliable than potentially outdated PR descriptions. Base your title on what the code actually does.

Always output ONLY valid YAML that can be parsed directly, with no additional text or markdown formatting.
The YAML should be a single object with the required fields."""

    DEFAULT_IMPORTANT_NOTES_INSTRUCTION = """
## Important Notes

Consider whether to add an 'important_notes' field to highlight:
- Breaking changes
- Security implications
- Major deprecations
- Migration guidance needed
- Performance impacts
- Database migration requirements

Only include 'important_notes' if the change significantly impacts users or requires attention during upgrades."""

    def __init__(
        self,
        api_key: str,
        model: str = 'claude-3-5-sonnet-20241022',
        system_prompt: Optional[str] = None,
        changelog_language: str = 'English',
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
            'added', 'changed', 'deprecated', 'removed', 'fixed', 'security', 'dependency_update', 'other'
        ]
        self.mandatory_fields = mandatory_fields or ['title']
        self.forbidden_fields = forbidden_fields or []

        # Build system prompt
        lang_instruction = f'Write the entry in {changelog_language}.' if changelog_language != 'English' else ''
        prompt_parts = [system_prompt or self.DEFAULT_SYSTEM_PROMPT]

        # Add important_notes instruction if enabled
        if self.generate_important_notes:
            prompt_parts.append(self.DEFAULT_IMPORTANT_NOTES_INSTRUCTION)

        prompt_parts.append(lang_instruction)
        self.system_prompt = '\n'.join(p for p in prompt_parts if p).strip()

        self.api_url = 'https://api.anthropic.com/v1/messages'
        self._setup_session()

    def _setup_session(self) -> None:
        """Set up HTTP session with authentication headers"""
        self.session = requests.Session()
        self.session.headers.update({
            'x-api-key': self.api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json'
        })

    def generate(self, pr_diff: str, pr_info: Dict[str, Any], custom_prompt: Optional[str] = None) -> Optional[str]:
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
                logger.debug('Using custom prompt for generation')
            else:
                # Extract PR information
                pr_title = pr_info.get('title', '')
                pr_body = pr_info.get('body', '')
                pr_author = pr_info.get('user', {}).get('login', 'unknown')
                pr_author_url = pr_info.get('user', {}).get('html_url', '')
                pr_labels = [label.get('name', '') for label in pr_info.get('labels', [])]

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
                    commit_authors=commit_authors
                )

            logger.debug(f'Sending request to Claude API (model: {self.model})')

            # Call Claude API with session
            response = self.session.post(
                self.api_url,
                json={
                    'model': self.model,
                    'max_tokens': 1024,
                    'system': self.system_prompt,
                    'messages': [{'role': 'user', 'content': user_message}]
                }
            )

            if response.status_code != 200:
                logger.error(f'Claude API error: {response.status_code} - {response.text}')
                return None

            result = response.json()
            generated_text = result['content'][0]['text']

            # Extract YAML from markdown code blocks if present
            generated_text = self._extract_yaml(generated_text)

            # Validate that it's valid YAML
            try:
                yaml.safe_load(generated_text)
                logger.info('Successfully generated and validated changelog entry')
                return generated_text.strip()
            except yaml.YAMLError as e:
                logger.error(f'Generated text is not valid YAML: {e}')
                logger.debug(f'Generated text: {generated_text}')
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f'Failed to call Claude API: {e}')
            return None
        except (KeyError, ValueError) as e:
            logger.error(f'Failed to parse Claude response: {e}')
            return None

    def _extract_yaml(self, text: str) -> str:
        """Extract YAML from markdown code blocks if present"""
        # Try to extract from ```yaml ... ``` or ``` ... ``` block
        match = re.search(r'```(?:yaml)?\s*\n(.*?)\n```', text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Return as-is if no code block found
        return text.strip()

    def _extract_commit_authors(self, pr_info: Dict[str, Any]) -> list:
        """Extract unique authors from commits if available"""
        authors = set()
        commits = pr_info.get('commits', []) if isinstance(pr_info.get('commits'), list) else []

        for commit in commits:
            author_info = commit.get('author', {})
            if author_info and isinstance(author_info, dict):
                login = author_info.get('login')
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
        authors_section = self._build_authors_section(pr_author, commit_authors, pr_author_url)

        # Build language instruction
        language_section = f"Write the changelog entry in {self.changelog_language}." if self.changelog_language != 'English' else ""

        # Build types list
        types_list = ', '.join(self.changelog_types)

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

        return '\n'.join(rules)

    def _build_authors_section(self, primary_author: str, commit_authors: list, author_url: str) -> str:
        """Build authors information section"""
        if not commit_authors:
            return ""

        authors_text = "**Contributors to this PR:**\n"
        all_authors = [primary_author] + [a for a in commit_authors if a != primary_author]
        authors_text += ', '.join(all_authors)

        return authors_text
