#!/usr/bin/env python3
"""
Comprehensive CLI for testing the Logchange Action locally.

This tool allows developers to test most features of the logchange action
without requiring an actual GitHub PR. Useful for:
  - Testing changelog generation with Claude API
  - Testing changelog validation
  - Testing metadata extraction
  - Testing legacy changelog handling
  - Testing various configuration options

The tool mimics the action's behavior and provides detailed logging.

Requirements:
  - CLAUDE_API_KEY environment variable (for generation tests)
  - Python 3.9+

Usage:
    python3 test_action_cli.py <command> [options]

Commands:
    generate    Test changelog generation (requires CLAUDE_API_KEY)
    validate    Test changelog validation
    extract     Test metadata extraction from PR description/diff
    legacy      Test legacy changelog detection and conversion
"""

import argparse
import json
import logging
import os
import sys

sys.path.insert(0, "action/src")

from changelog_generator import ChangelogGenerator
from changelog_validator import ChangelogValidator
from legacy_changelog_handler import LegacyChangelogHandler
from pr_metadata_extractor import PRMetadataExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ActionTestCLI:
    """CLI interface for testing the logchange action"""

    @staticmethod
    def load_file(path: str) -> str:
        """Load text from file"""
        try:
            with open(path, "r") as f:
                return f.read()
        except IOError as e:
            logger.error(f"Failed to load file: {e}")
            sys.exit(1)

    @staticmethod
    def load_json(path: str) -> dict:
        """Load JSON from file"""
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load JSON: {e}")
            sys.exit(1)

    @staticmethod
    def create_sample_pr_info(title: str = "Test PR") -> dict:
        """Create sample PR info object"""
        return {
            "number": 42,
            "title": title,
            "body": "This is a test pull request description",
            "user": {
                "login": "test-developer",
                "html_url": "https://github.com/test-developer",
            },
        }

    def cmd_generate(self, args):
        """Test changelog generation with Claude API"""
        logger.info("Testing changelog GENERATION...")

        # Get token
        token = args.token or os.getenv("CLAUDE_API_KEY")
        if not token:
            logger.error("Claude API token required for generation")
            logger.error("Provide via: --token TOKEN or CLAUDE_API_KEY env var")
            sys.exit(1)

        # Load diff
        logger.info(f"Loading diff from: {args.diff}")
        diff = self.load_file(args.diff)
        logger.info(f"Diff loaded: {len(diff)} characters")

        # Load or create PR info
        if args.pr_info:
            logger.info(f"Loading PR info from: {args.pr_info}")
            pr_info = self.load_json(args.pr_info)
        else:
            logger.info(f"Creating sample PR info: {args.pr_title}")
            pr_info = self.create_sample_pr_info(args.pr_title)

        # Parse config
        changelog_types = (
            [t.strip() for t in args.types.split(",")] if args.types else None
        )
        mandatory_fields = (
            [f.strip() for f in args.mandatory.split(",")] if args.mandatory else None
        )
        forbidden_fields = (
            [f.strip() for f in args.forbidden.split(",")] if args.forbidden else None
        )

        system_prompt = None
        if args.system_prompt:
            logger.info(f"Loading system prompt from: {args.system_prompt}")
            system_prompt = self.load_file(args.system_prompt)

        # Create and run generator
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

        logger.info("=" * 80)
        logger.info("GENERATING CHANGELOG ENTRY")
        logger.info("=" * 80)

        generated = generator.generate(diff, pr_info)

        if generated:
            logger.info("✅ Generation successful")
            print("\n" + "=" * 80)
            print("GENERATED CHANGELOG ENTRY:")
            print("=" * 80)
            print(generated)
            print("=" * 80)
            return 0
        else:
            logger.error("❌ Generation failed")
            return 1

    def cmd_validate(self, args):
        """Test changelog validation"""
        logger.info("Testing changelog VALIDATION...")

        # Load or create entry to validate
        if args.entry:
            logger.info(f"Loading entry from: {args.entry}")
            entry = self.load_file(args.entry)
        else:
            logger.info("Using sample entry")
            entry = (
                args.sample
                or """title: Add authentication support
type: added
authors:
  - name: Test Developer
    nick: test-dev
    url: https://github.com/test-dev
"""
            )

        # Parse config
        mandatory_fields = (
            [f.strip() for f in args.mandatory.split(",")]
            if args.mandatory
            else ["title"]
        )
        forbidden_fields = (
            [f.strip() for f in args.forbidden.split(",")] if args.forbidden else None
        )
        changelog_types = (
            [t.strip() for t in args.types.split(",")] if args.types else None
        )

        # Create and run validator
        logger.info(f"Mandatory fields: {mandatory_fields}")
        if forbidden_fields:
            logger.info(f"Forbidden fields: {forbidden_fields}")

        validator = ChangelogValidator(
            mandatory_fields=mandatory_fields,
            forbidden_fields=forbidden_fields,
            changelog_types=changelog_types,
        )

        logger.info("=" * 80)
        logger.info("VALIDATING CHANGELOG ENTRY")
        logger.info("=" * 80)

        is_valid, errors = validator.validate(entry)

        print("\n" + "=" * 80)
        if is_valid:
            logger.info("✅ Validation successful")
            print("VALIDATION RESULT: ✅ PASSED")
        else:
            logger.error("❌ Validation failed")
            print("VALIDATION RESULT: ❌ FAILED")
            print("\nErrors:")
            for error in errors:
                print(f"  - {error}")

        print("=" * 80)
        return 0 if is_valid else 1

    def cmd_extract(self, args):
        """Test metadata extraction from PR description/diff"""
        logger.info("Testing metadata EXTRACTION...")

        # Load diff and PR description
        logger.info(f"Loading diff from: {args.diff}")
        diff = self.load_file(args.diff)

        # Load or create PR info
        if args.pr_info:
            logger.info(f"Loading PR info from: {args.pr_info}")
            pr_info = self.load_json(args.pr_info)
        else:
            logger.info("Creating sample PR info")
            pr_info = self.create_sample_pr_info()

        # Create extractor
        extractor = PRMetadataExtractor(
            external_issue_regex=args.external_issue_regex,
            external_issue_url_template=args.external_issue_url_template,
            github_issue_detection=args.github_issue_detection,
            issue_tracker_url_detection=args.issue_tracker_url_detection,
        )

        logger.info("=" * 80)
        logger.info("EXTRACTING METADATA")
        logger.info("=" * 80)

        # Extract various metadata
        pr_number = extractor.extract_merge_request_number(pr_info)
        github_issues = extractor.extract_github_issues(
            pr_info.get("body", "") + "\n" + diff
        )
        urls = extractor.extract_urls(pr_info.get("body", ""))
        external_issues = (
            extractor.extract_external_issues(pr_info.get("body", "") + "\n" + diff)
            if args.external_issue_regex
            else {}
        )

        print("\n" + "=" * 80)
        print("EXTRACTED METADATA:")
        print("=" * 80)
        print(f"PR Number: {pr_number}")
        print(f"GitHub Issues: {github_issues if github_issues else 'None'}")
        print(f"URLs: {urls if urls else 'None'}")
        if external_issues:
            print(f"External Issues: {external_issues}")
        print("=" * 80)

        return 0

    def cmd_legacy(self, args):
        """Test legacy changelog detection and conversion"""
        logger.info("Testing legacy changelog DETECTION AND CONVERSION...")

        # Load legacy entry or use sample
        if args.entry:
            logger.info(f"Loading entry from: {args.entry}")
            entry = self.load_file(args.entry)
        else:
            logger.info("Using sample legacy entry")
            entry = (
                args.sample
                or """## [1.0.0] - 2025-10-25
### Added
- Authentication support
- API endpoints
"""
            )

        # Create handler
        legacy_paths = (
            [p.strip() for p in args.paths.split(",")]
            if args.paths
            else ["CHANGELOG.md", "HISTORY.txt"]
        )

        logger.info(f"Legacy changelog paths: {legacy_paths}")

        handler = LegacyChangelogHandler(legacy_changelog_paths=legacy_paths)

        logger.info("=" * 80)
        logger.info("TESTING LEGACY CHANGELOG")
        logger.info("=" * 80)

        # Detect entry type
        entry_type = handler.detect_entry_type(entry)

        print("\n" + "=" * 80)
        print("LEGACY FORMAT DETECTION:")
        print("=" * 80)

        if entry_type == "markdown":
            logger.info("✅ Entry is in Markdown legacy format")
            print(f"Format: {entry_type.upper()} (legacy)")
        elif entry_type == "plain_text":
            logger.info("✅ Entry is in plain text legacy format")
            print(f"Format: {entry_type.upper()} (legacy)")
        elif entry_type == "unreleased":
            logger.info("Entry contains 'Unreleased' section")
            print(f"Format: {entry_type.upper()}")
        else:
            logger.info("Entry type: other")
            print(f"Format: {entry_type.upper()}")

        print("=" * 80)

        return 0


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Test Logchange Action locally",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

  GENERATE (requires CLAUDE_API_KEY):
    export CLAUDE_API_KEY="sk-ant-..."
    python3 test_action_cli.py generate --diff changes.diff
    python3 test_action_cli.py generate --diff changes.diff --pr-info pr.json
    python3 test_action_cli.py generate --diff changes.diff --language German

  VALIDATE:
    python3 test_action_cli.py validate --entry entry.yml
    python3 test_action_cli.py validate --sample "title: Test\\ntype: added"
    python3 test_action_cli.py validate --entry entry.yml --mandatory "title,type,authors"

  EXTRACT:
    python3 test_action_cli.py extract --diff changes.diff
    python3 test_action_cli.py extract --diff changes.diff --pr-info pr.json
    python3 test_action_cli.py extract --diff changes.diff \\
      --external-issue-regex "JIRA-(\\d+)" \\
      --external-issue-url-template "https://jira.example.com/browse/JIRA-{id}"

  LEGACY:
    python3 test_action_cli.py legacy --entry CHANGELOG.md
    python3 test_action_cli.py legacy --sample "## [1.0.0]\\n### Added\\n- Feature"
    python3 test_action_cli.py legacy --paths "CHANGELOG.md,HISTORY.txt"
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # GENERATE command
    gen_parser = subparsers.add_parser("generate", help="Test generation")
    gen_parser.add_argument("--token", help="Claude API token")
    gen_parser.add_argument("--diff", required=True, help="Path to diff file")
    gen_parser.add_argument("--pr-info", help="Path to PR info JSON")
    gen_parser.add_argument("--pr-title", default="Test PR", help="PR title")
    gen_parser.add_argument("--language", default="English", help="Output language")
    gen_parser.add_argument(
        "--model", default="claude-opus-4-1-20250805", help="Claude model"
    )
    gen_parser.add_argument("--types", help="Allowed types (comma-separated)")
    gen_parser.add_argument("--mandatory", help="Mandatory fields (comma-separated)")
    gen_parser.add_argument("--forbidden", help="Forbidden fields (comma-separated)")
    gen_parser.add_argument(
        "--max-tokens", type=int, default=5000, help="Max context tokens"
    )
    gen_parser.add_argument("--system-prompt", help="Custom system prompt file")
    gen_parser.add_argument(
        "--external-issue-regex", help="External issue regex pattern"
    )
    gen_parser.add_argument(
        "--external-issue-url-template", help="External issue URL template"
    )
    gen_parser.add_argument(
        "--generate-important-notes",
        action="store_true",
        help="Generate important notes",
    )

    # VALIDATE command
    val_parser = subparsers.add_parser("validate", help="Test validation")
    val_parser.add_argument("--entry", help="Path to YAML entry file")
    val_parser.add_argument("--sample", help="Sample YAML entry (inline)")
    val_parser.add_argument("--mandatory", help="Mandatory fields (comma-separated)")
    val_parser.add_argument("--forbidden", help="Forbidden fields (comma-separated)")
    val_parser.add_argument("--types", help="Allowed types (comma-separated)")

    # EXTRACT command
    ext_parser = subparsers.add_parser("extract", help="Test extraction")
    ext_parser.add_argument("--diff", required=True, help="Path to diff file")
    ext_parser.add_argument("--pr-info", help="Path to PR info JSON")
    ext_parser.add_argument("--external-issue-regex", help="External issue regex")
    ext_parser.add_argument(
        "--external-issue-url-template", help="External issue URL template"
    )
    ext_parser.add_argument(
        "--github-issue-detection",
        action="store_true",
        default=True,
        help="Enable GitHub issue detection",
    )
    ext_parser.add_argument(
        "--issue-tracker-url-detection",
        action="store_true",
        default=True,
        help="Enable URL detection",
    )

    # LEGACY command
    leg_parser = subparsers.add_parser("legacy", help="Test legacy handling")
    leg_parser.add_argument("--entry", help="Path to legacy entry file")
    leg_parser.add_argument("--sample", help="Sample legacy entry (inline)")
    leg_parser.add_argument("--paths", help="Legacy changelog paths (comma-separated)")

    # Global options
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Run command
    cli = ActionTestCLI()
    command = getattr(cli, f"cmd_{args.command}", None)

    if not command:
        logger.error(f"Unknown command: {args.command}")
        return 1

    try:
        return command(args)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
