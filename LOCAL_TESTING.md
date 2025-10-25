# Local Testing Guide

This guide explains how to test the Logchange Action locally without requiring a real GitHub PR.

## Quick Start

```bash
# Test validation (no API key needed)
python3 test_action_cli.py validate --sample "title: Test\ntype: added"

# Test generation (requires Claude API key)
export CLAUDE_API_KEY="sk-ant-..."
python3 test_action_cli.py generate --diff changes.diff

# Test metadata extraction
python3 test_action_cli.py extract --diff changes.diff

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

**Basic usage:**

```bash
export CLAUDE_API_KEY="sk-ant-api03-..."
python3 test_action_cli.py generate --diff changes.diff
```

**With PR information:**

```bash
python3 test_action_cli.py generate \
  --diff changes.diff \
  --pr-title "Add authentication feature" \
  --pr-info pr_info.json
```

**With custom validation rules:**

```bash
python3 test_action_cli.py generate \
  --diff changes.diff \
  --mandatory "title,type,authors" \
  --forbidden "draft,internal" \
  --types "added,fixed,security"
```

**With custom language:**

```bash
python3 test_action_cli.py generate \
  --diff changes.diff \
  --language German
```

**With external issue tracker (JIRA):**

```bash
python3 test_action_cli.py generate \
  --diff changes.diff \
  --external-issue-regex "JIRA-(\d+)" \
  --external-issue-url-template "https://jira.example.com/browse/JIRA-{id}"
```

**With custom system prompt:**

```bash
python3 test_action_cli.py generate \
  --diff changes.diff \
  --system-prompt custom_prompt.txt
```

**With verbose logging:**

```bash
python3 test_action_cli.py generate --diff changes.diff --verbose
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

**Basic usage:**

```bash
python3 test_action_cli.py extract --diff changes.diff
```

**With PR information:**

```bash
python3 test_action_cli.py extract --diff changes.diff --pr-info pr_info.json
```

**With external issue tracker:**

```bash
python3 test_action_cli.py extract \
  --diff changes.diff \
  --external-issue-regex "JIRA-(\d+)" \
  --external-issue-url-template "https://jira.example.com/browse/JIRA-{id}"
```

**With GitHub issue detection:**

```bash
python3 test_action_cli.py extract \
  --diff changes.diff \
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

### Sample Diff File

Create `test_changes.diff`:

```diff
diff --git a/src/main.py b/src/main.py
index 1234567..abcdefg 100644
--- a/src/main.py
+++ b/src/main.py
@@ -1,5 +1,10 @@
 def main():
+    """Main entry point"""
+    # Initialize authenticator
+    auth = authenticate()
+    # Process requests
     print("Hello")

-    run()
+    run(auth)
```

### Sample PR Info File

Create `pr_info.json`:

```json
{
  "number": 42,
  "title": "Add authentication support",
  "body": "This PR adds OAuth2 authentication.\n\nFixes #123\nCloses #456\nRelated to JIRA-789",
  "user": {
    "login": "developer-name",
    "html_url": "https://github.com/developer-name"
  }
}
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
# 1. Create a diff file with your changes
cat > test.diff << 'EOF'
diff --git a/api.py b/api.py
+def authenticate(token):
+    """Authenticate user with token"""
+    return validate_token(token)
EOF

# 2. Generate changelog entry
export CLAUDE_API_KEY="sk-ant-..."
python3 test_action_cli.py generate --diff test.diff

# Expected output: YAML changelog entry
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
cat > pr_info.json << 'EOF'
{
  "body": "Fixes #123 and #456\nRelated to JIRA-789\nSee https://example.com/details"
}
EOF

python3 test_action_cli.py extract \
  --pr-info pr_info.json \
  --diff changes.diff \
  --external-issue-regex "JIRA-(\d+)" \
  --external-issue-url-template "https://jira.example.com/browse/JIRA-{id}"

# Expected output: Extracted issues and URLs
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
# More detailed output
python3 test_action_cli.py generate --diff test.diff --verbose

# Change logging level (in code):
# logging.getLogger().setLevel(logging.DEBUG)
```

## Troubleshooting

### "Claude API token not provided"

**Solution:** Set CLAUDE_API_KEY environment variable:

```bash
export CLAUDE_API_KEY="sk-ant-..."
python3 test_action_cli.py generate --diff test.diff
```

### "Failed to load file"

**Solution:** Ensure file path is correct and readable:

```bash
python3 test_action_cli.py generate --diff /path/to/changes.diff
```

### Generation fails silently

**Solution:** Enable verbose logging:

```bash
python3 test_action_cli.py generate --diff test.diff --verbose
```

### "Module not found"

**Solution:** Run from the repository root:

```bash
cd /path/to/logchange-action
python3 test_action_cli.py validate --sample "title: Test\ntype: added"
```

## Tips and Best Practices

1. **Use real diffs:** Test with actual code changes from your project for realistic results

2. **Test validation first:** Before testing generation, ensure your validation rules are correct:
   ```bash
   python3 test_action_cli.py validate --entry entry.yml
   ```

3. **Test metadata extraction:** Verify issues and links are detected correctly:
   ```bash
   python3 test_action_cli.py extract --diff changes.diff --pr-info pr.json
   ```

4. **Check API response:** Use --verbose flag to see Claude's responses:
   ```bash
   python3 test_action_cli.py generate --diff test.diff --verbose
   ```

5. **Save successful outputs:** Keep examples of good changelog entries for reference:
   ```bash
   python3 test_action_cli.py generate --diff test.diff > successful_entry.yml
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
