#!/usr/bin/env python3
"""
Developer utility to test the changelog generator locally.

The Claude API token can be provided via:
  1. Environment variable: CLAUDE_API_KEY
  2. Command-line argument: --token (overrides env var)

Usage:
    export CLAUDE_API_KEY="sk-ant-api03-..."
    python3 test_generator.py --diff <PATH_TO_DIFF> [OPTIONS]

    OR with command-line token:
    python3 test_generator.py --token sk-ant-api03-... --diff <PATH_TO_DIFF> [OPTIONS]

Examples:
    # Basic test
    export CLAUDE_API_KEY="sk-ant-api03-..."
    python3 test_generator.py --diff example_diff.txt

    # With language and types
    python3 test_generator.py \\
        --diff example_diff.txt \\
        --language German \\
        --types feature,bugfix,security

    # With external issue tracker (JIRA)
    python3 test_generator.py \\
        --diff example_diff.txt \\
        --external-issue-regex 'JIRA-(\\d+)' \\
        --external-issue-url-template 'https://jira.example.com/browse/JIRA-{id}'

    # Disable GitHub issue detection
    python3 test_generator.py \\
        --diff example_diff.txt \\
        --github-issue-detection false
"""

import sys
import os
import argparse
import json
import logging
from pathlib import Path

sys.path.insert(0, 'action/src')

from changelog_generator import ChangelogGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_diff(diff_path: str) -> str:
    """Load diff from file"""
    try:
        with open(diff_path, 'r') as f:
            return f.read()
    except IOError as e:
        logger.error(f"Failed to load diff file: {e}")
        sys.exit(1)


def load_pr_info(info_path: str) -> dict:
    """Load PR info from JSON file"""
    try:
        with open(info_path, 'r') as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        logger.error(f"Failed to load PR info: {e}")
        sys.exit(1)


def create_default_pr_info(title: str = "Test PR") -> dict:
    """Create a minimal PR info object"""
    return {
        "title": title,
        "body": "This is a test pull request",
        "user": {
            "login": "test-developer",
            "html_url": "https://github.com/test-developer"
        },
        "labels": [{"name": "feature"}],
        "commits": []
    }


def main():
    parser = argparse.ArgumentParser(
        description='Test the changelog generator with Claude API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using environment variable (recommended for security)
  export CLAUDE_API_KEY="sk-ant-api03-..."
  python3 test_generator.py --diff test.diff

  # Using command-line argument (overrides env var)
  python3 test_generator.py --token sk-ant-api03-... --diff test.diff

  # With custom configuration
  python3 test_generator.py \\
    --diff test.diff \\
    --language German \\
    --types "feature,bugfix,security" \\
    --mandatory "title,type,authors" \\
    --forbidden "internal,draft"

  # With PR info file
  python3 test_generator.py \\
    --diff test.diff \\
    --pr-info pr_info.json

  # With external issue tracker (JIRA)
  python3 test_generator.py \\
    --diff test.diff \\
    --external-issue-regex "JIRA-(\\d+)" \\
    --external-issue-url-template "https://jira.example.com/browse/JIRA-{id}"

  # Disable GitHub issue detection
  python3 test_generator.py \\
    --diff test.diff \\
    --github-issue-detection false

  # With all metadata options
  python3 test_generator.py \\
    --diff test.diff \\
    --pr-info pr_info.json \\
    --external-issue-regex "JIRA-(\\d+)" \\
    --external-issue-url-template "https://jira.example.com/browse/JIRA-{id}" \\
    --github-issue-detection true \\
    --issue-tracker-url-detection true \\
    --generate-important-notes true \\
    --verbose
        """
    )

    parser.add_argument(
        '--token', required=False, default=None,
        help='Claude API token (sk-ant-api03-...). If not provided, reads from CLAUDE_API_KEY environment variable'
    )
    parser.add_argument(
        '--diff', required=True,
        help='Path to diff file to test'
    )
    parser.add_argument(
        '--pr-info', default=None,
        help='Path to PR info JSON file (optional, creates default if not provided)'
    )
    parser.add_argument(
        '--pr-title', default='Test Pull Request',
        help='PR title (if not using --pr-info)'
    )
    parser.add_argument(
        '--language', default='English',
        help='Language for generated entry (default: English)'
    )
    parser.add_argument(
        '--model', default='claude-opus-4-1-20250805',
        help='Claude model to use'
    )
    parser.add_argument(
        '--types', default=None,
        help='Comma-separated list of allowed types (default: standard logchange types)'
    )
    parser.add_argument(
        '--mandatory', default=None,
        help='Comma-separated list of mandatory fields'
    )
    parser.add_argument(
        '--forbidden', default=None,
        help='Comma-separated list of forbidden fields'
    )
    parser.add_argument(
        '--max-tokens', type=int, default=5000,
        help='Max tokens for context (default: 5000)'
    )
    parser.add_argument(
        '--system-prompt', default=None,
        help='Custom system prompt file'
    )
    parser.add_argument(
        '--external-issue-regex', default=None,
        help='Regex pattern to detect external issues (e.g., JIRA-(\\d+))'
    )
    parser.add_argument(
        '--external-issue-url-template', default=None,
        help='URL template for external issues (e.g., https://jira.example.com/browse/{id})'
    )
    parser.add_argument(
        '--github-issue-detection', type=lambda x: x.lower() == 'true', default=True,
        help='Enable GitHub issue detection (#123) (default: true)'
    )
    parser.add_argument(
        '--issue-tracker-url-detection', type=lambda x: x.lower() == 'true', default=True,
        help='Enable issue tracker URL detection (default: true)'
    )
    parser.add_argument(
        '--generate-important-notes', type=lambda x: x.lower() == 'true', default=True,
        help='Enable AI generation of important_notes (default: true)'
    )
    parser.add_argument(
        '--verbose', action='store_true',
        help='Enable verbose output'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Get Claude API token from command-line or environment variable
    token = args.token or os.getenv('CLAUDE_API_KEY')

    if not token:
        logger.error("Claude API token not provided.")
        logger.error("Please provide token via:")
        logger.error("  1. Command-line: --token sk-ant-api03-...")
        logger.error("  2. Environment variable: export CLAUDE_API_KEY='sk-ant-api03-...'")
        sys.exit(1)

    if not token.startswith('sk-ant-'):
        logger.warning("Token does not start with 'sk-ant-'. This may be invalid.")

    logger.info("Using Claude API token from " + ("command-line argument" if args.token else "CLAUDE_API_KEY environment variable"))

    # Load diff
    logger.info(f"Loading diff from: {args.diff}")
    pr_diff = load_diff(args.diff)
    logger.info(f"Diff loaded: {len(pr_diff)} characters")

    # Load or create PR info
    if args.pr_info:
        logger.info(f"Loading PR info from: {args.pr_info}")
        pr_info = load_pr_info(args.pr_info)
    else:
        logger.info(f"Creating default PR info with title: {args.pr_title}")
        pr_info = create_default_pr_info(args.pr_title)

    # Parse optional configuration
    changelog_types = None
    if args.types:
        changelog_types = [t.strip() for t in args.types.split(',')]
        logger.info(f"Using types: {changelog_types}")

    mandatory_fields = None
    if args.mandatory:
        mandatory_fields = [f.strip() for f in args.mandatory.split(',')]
        logger.info(f"Mandatory fields: {mandatory_fields}")

    forbidden_fields = None
    if args.forbidden:
        forbidden_fields = [f.strip() for f in args.forbidden.split(',')]
        logger.info(f"Forbidden fields: {forbidden_fields}")

    system_prompt = None
    if args.system_prompt:
        try:
            with open(args.system_prompt, 'r') as f:
                system_prompt = f.read()
            logger.info(f"Loaded custom system prompt ({len(system_prompt)} chars)")
        except IOError as e:
            logger.error(f"Failed to load system prompt: {e}")
            sys.exit(1)

    # Log metadata extraction configuration
    if args.external_issue_regex:
        logger.info(f"External issue regex: {args.external_issue_regex}")
        logger.info(f"External issue URL template: {args.external_issue_url_template}")
    logger.info(f"GitHub issue detection: {args.github_issue_detection}")
    logger.info(f"Issue tracker URL detection: {args.issue_tracker_url_detection}")
    logger.info(f"Generate important notes: {args.generate_important_notes}")

    # Create generator
    logger.info(f"Initializing generator (model: {args.model})")
    generator = ChangelogGenerator(
        api_key=token,
        model=args.model,
        system_prompt=system_prompt,
        changelog_language=args.language,
        max_tokens_context=args.max_tokens,
        changelog_types=changelog_types,
        mandatory_fields=mandatory_fields,
        forbidden_fields=forbidden_fields,
        generate_important_notes=args.generate_important_notes,
        external_issue_regex=args.external_issue_regex,
        external_issue_url_template=args.external_issue_url_template,
    )

    # Generate
    logger.info("=" * 80)
    logger.info("GENERATING CHANGELOG ENTRY")
    logger.info("=" * 80)

    generated = generator.generate(pr_diff, pr_info)

    if generated:
        logger.info("=" * 80)
        logger.info("✅ GENERATION SUCCESSFUL")
        logger.info("=" * 80)
        print("\n" + "=" * 80)
        print("GENERATED CHANGELOG ENTRY:")
        print("=" * 80)
        print(generated)
        print("=" * 80)
        return 0
    else:
        logger.error("=" * 80)
        logger.error("❌ GENERATION FAILED")
        logger.error("=" * 80)
        print("Failed to generate changelog entry. Check logs above for details.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
