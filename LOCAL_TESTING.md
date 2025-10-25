# Local Testing Guide

This guide explains how to test the Logchange Action code locally without requiring a real GitHub PR.

## Quick Start

```bash
# Test validation (no API key needed)
python3 test_action_cli.py validate --sample "title: Test\ntype: added"

# Test generation with sample files (requires Claude API key)
export CLAUDE_API_KEY="sk-ant-..."
python3 test_action_cli.py generate --diff examples/test-changes.diff --pr-info examples/test-pr-info.json

# Test metadata extraction with samples
python3 test_action_cli.py extract --diff examples/test-changes.diff --pr-info examples/test-pr-info.json

# Test legacy changelog detection
python3 test_action_cli.py legacy --sample "## [1.0.0]\n### Added\n- Feature"
```

## Installation

The CLI tool is included in the repository. No additional installation needed:

```bash
python3 test_action_cli.py --help
```

## Commands

### 1. GENERATE - Test Changelog Generation

Test the Claude API integration and changelog generation.

**Requirements:**
- CLAUDE_API_KEY environment variable or --token argument
- A diff file showing the code changes

**Basic usage with sample files:**

```bash
export CLAUDE_API_KEY="sk-ant-api03-..."
python3 test_action_cli.py generate --diff examples/test-changes.diff --pr-info examples/test-pr-info.json
```

Sample files are included in the repository:
- `examples/test-changes.diff` - Real-world diff with authentication feature changes
- `examples/test-pr-info.json` - Sample PR info with GitHub issues and external tracker references

**With custom PR information:**

```bash
python3 test_action_cli.py generate \
  --diff examples/test-changes.diff \
  --pr-title "Add custom feature" \
  --pr-info your-pr-info.json
```

**With custom validation rules:**

```bash
python3 test_action_cli.py generate \
  --diff examples/test-changes.diff \
  --pr-info examples/test-pr-info.json \
  --mandatory "title,type,authors" \
  --forbidden "draft,internal" \
  --types "added,fixed,security"
```

**With custom language:**

```bash
python3 test_action_cli.py generate \
  --diff examples/test-changes.diff \
  --pr-info examples/test-pr-info.json \
  --language German
```

**With external issue tracker (JIRA):**

```bash
python3 test_action_cli.py generate \
  --diff examples/test-changes.diff \
  --pr-info examples/test-pr-info.json \
  --external-issue-regex "JIRA-(\d+)" \
  --external-issue-url-template "https://jira.example.com/browse/JIRA-{id}"
```

**With custom system prompt:**

```bash
python3 test_action_cli.py generate \
  --diff examples/test-changes.diff \
  --pr-info examples/test-pr-info.json \
  --system-prompt custom_prompt.txt
```

**With verbose logging:**

```bash
python3 test_action_cli.py generate --diff examples/test-changes.diff --pr-info examples/test-pr-info.json --verbose
```

### 2. VALIDATE - Test Changelog Validation

Test changelog entry validation without generation.

**Basic usage with a file:**

```bash
python3 test_action_cli.py validate --entry changelog_entry.yml
```

**With sample YAML:**

```bash
python3 test_action_cli.py validate --sample "title: Test\ntype: added"
```

**With custom mandatory fields:**

```bash
python3 test_action_cli.py validate \
  --entry changelog_entry.yml \
  --mandatory "title,type,authors"
```

**With forbidden fields:**

```bash
python3 test_action_cli.py validate \
  --entry changelog_entry.yml \
  --forbidden "draft,internal"
```

**With allowed types:**

```bash
python3 test_action_cli.py validate \
  --entry changelog_entry.yml \
  --types "added,fixed,security,dependency_update"
```

### 3. EXTRACT - Test Metadata Extraction

Test extraction of metadata from PR description and diff (issues, links, external trackers).

**Basic usage with sample files:**

```bash
python3 test_action_cli.py extract --diff examples/test-changes.diff --pr-info examples/test-pr-info.json
```

This will extract:
- GitHub issues (#123, #456)
- External issue tracker references (JIRA-789)
- PR metadata (title, author, URL)

**With custom PR information:**

```bash
python3 test_action_cli.py extract --diff your-changes.diff --pr-info your-pr-info.json
```

**With external issue tracker:**

```bash
python3 test_action_cli.py extract \
  --diff examples/test-changes.diff \
  --pr-info examples/test-pr-info.json \
  --external-issue-regex "JIRA-(\d+)" \
  --external-issue-url-template "https://jira.example.com/browse/JIRA-{id}"
```

**With GitHub issue detection:**

```bash
python3 test_action_cli.py extract \
  --diff examples/test-changes.diff \
  --pr-info examples/test-pr-info.json \
  --github-issue-detection true \
  --issue-tracker-url-detection true
```

### 4. LEGACY - Test Legacy Changelog Detection

Test detection of legacy changelog formats (e.g., CHANGELOG.md).

**With a file:**

```bash
python3 test_action_cli.py legacy --entry CHANGELOG.md
```

**With sample content:**

```bash
python3 test_action_cli.py legacy --sample "## [1.0.0]\n### Added\n- Feature"
```

**With custom legacy paths:**

```bash
python3 test_action_cli.py legacy --paths "CHANGELOG.md,HISTORY.txt,NEWS.md"
```

## Creating Test Files

### Sample Files Included

The repository includes ready-to-use sample files:

**Diff file**: `examples/test-changes.diff`
- Contains authentication feature implementation
- Includes new file creation, modifications, and tests
- Realistic code changes with import statements and docstrings

**PR info file**: `examples/test-pr-info.json`
- GitHub issues references (#123, #456)
- External tracker reference (JIRA-789)
- PR title, description, and author info
- Covers all metadata extraction scenarios

Use these to get started immediately:
```bash
python3 test_action_cli.py generate --diff examples/test-changes.diff --pr-info examples/test-pr-info.json
```

### Creating Custom Test Files

To create your own test files, use the included samples as templates:

See `examples/test-changes.diff` and `examples/test-pr-info.json` for reference format and structure.

You can copy and modify these files for your specific testing needs:

```bash
# Copy and customize the sample files
cp examples/test-changes.diff my-custom-changes.diff
cp examples/test-pr-info.json my-custom-pr-info.json

# Edit them with your own code changes and PR data
# Then test:
python3 test_action_cli.py generate --diff my-custom-changes.diff --pr-info my-custom-pr-info.json
```

### Sample Changelog Entry

Create `entry.yml`:

```yaml
title: Add OAuth2 authentication
type: added
authors:
  - name: Developer Name
    nick: dev-nick
    url: https://github.com/developer-name
modules:
  - authentication
  - api
important_notes: |
  This is a breaking change if you're using the old BasicAuth method.
  Update your clients to use OAuth2 tokens instead.
```

## Common Testing Scenarios

### Scenario 1: Test Full Generation Flow

Test that the action can generate a complete changelog entry:

```bash
# Use included sample files to generate a changelog entry
export CLAUDE_API_KEY="sk-ant-..."
python3 test_action_cli.py generate --diff examples/test-changes.diff --pr-info examples/test-pr-info.json

# Expected output: YAML changelog entry with:
# - Title from PR description
# - Type inferred from code changes
# - Authors extracted from PR metadata
# - Issues and references extracted from PR body
```

### Scenario 2: Test Custom Validation Rules

Test that validation enforces your organization's rules:

```bash
# Create an entry that violates rules
cat > bad_entry.yml << 'EOF'
title: Quick fix
type: added
EOF

# Validate with mandatory authors field
python3 test_action_cli.py validate \
  --entry bad_entry.yml \
  --mandatory "title,type,authors"

# Expected result: Validation fails (missing authors)
```

### Scenario 3: Test Metadata Extraction

Test that issues and links are properly extracted:

```bash
python3 test_action_cli.py extract \
  --pr-info examples/test-pr-info.json \
  --diff examples/test-changes.diff \
  --external-issue-regex "JIRA-(\d+)" \
  --external-issue-url-template "https://jira.example.com/browse/JIRA-{id}"

# Expected output:
# PR Number: 42
# GitHub Issues: [123, 456]
# External trackers: JIRA-789
```

### Scenario 4: Test Legacy Format Handling

Test detection of legacy changelog entries:

```bash
cat > CHANGELOG.md << 'EOF'
## [1.0.0] - 2025-10-25
### Added
- Authentication support
- API endpoints

### Fixed
- Login bug
EOF

python3 test_action_cli.py legacy --entry CHANGELOG.md

# Expected result: Detected as legacy format
```

## Environment Variables

### CLAUDE_API_KEY

Required for generation tests. Your Claude API key from Anthropic.

```bash
export CLAUDE_API_KEY="sk-ant-api03-..."
```

### Logging

Control logging verbosity:

```bash
# More detailed output with included samples
python3 test_action_cli.py generate --diff examples/test-changes.diff --pr-info examples/test-pr-info.json --verbose

# Change logging level (in code):
# logging.getLogger().setLevel(logging.DEBUG)
```

## Troubleshooting

### "Claude API token not provided"

**Solution:** Set CLAUDE_API_KEY environment variable:

```bash
export CLAUDE_API_KEY="sk-ant-..."
python3 test_action_cli.py generate --diff examples/test-changes.diff --pr-info examples/test-pr-info.json
```

### "Failed to load file"

**Solution:** Ensure file path is correct and readable. Use the included samples:

```bash
python3 test_action_cli.py generate --diff examples/test-changes.diff --pr-info examples/test-pr-info.json
```

Or use absolute paths if creating custom files:

```bash
python3 test_action_cli.py generate --diff /path/to/changes.diff
```

### Generation fails silently

**Solution:** Enable verbose logging:

```bash
python3 test_action_cli.py generate --diff examples/test-changes.diff --pr-info examples/test-pr-info.json --verbose
```

### "Module not found"

**Solution:** Run from the repository root:

```bash
cd /path/to/logchange-action
python3 test_action_cli.py validate --sample "title: Test\ntype: added"
```

## Tips and Best Practices

1. **Start with included samples:** Use `examples/test-changes.diff` and `examples/test-pr-info.json` to get started quickly, then create your own based on these templates.

2. **Test validation first:** Before testing generation, ensure your validation rules are correct:
   ```bash
   python3 test_action_cli.py validate --entry entry.yml
   ```

3. **Test metadata extraction:** Verify issues and links are detected correctly:
   ```bash
   python3 test_action_cli.py extract --diff examples/test-changes.diff --pr-info examples/test-pr-info.json
   ```

4. **Check API response:** Use --verbose flag to see Claude's responses:
   ```bash
   python3 test_action_cli.py generate --diff examples/test-changes.diff --pr-info examples/test-pr-info.json --verbose
   ```

5. **Save successful outputs:** Keep examples of good changelog entries for reference:
   ```bash
   python3 test_action_cli.py generate --diff examples/test-changes.diff --pr-info examples/test-pr-info.json > successful_entry.yml
   ```

## Integration with Workflow Testing

To fully test the action in a GitHub workflow:

1. Create a test PR in your repository
2. Add a changelog entry in `changelog/unreleased/`
3. Push and watch the PR workflow run
4. Verify the action passes/fails as expected

Use this CLI tool to validate entries locally before pushing:

```bash
# Before committing
python3 test_action_cli.py validate --entry changelog/unreleased/my-feature.yml

# Then push to PR
git push origin feature-branch
```

## See Also

- `TEST_GENERATOR.md` - Older single-purpose generator testing tool
- `CONTRIBUTING.md` - Development setup and workflow
- `CLAUDE.md` - Architecture and component overview
