# Changelog Generator Testing Utility

A developer utility to test the changelog generator locally without needing a real GitHub pull request.

## Overview

The `test_generator.py` script allows you to:
- Test changelog generation with your own Claude API token
- Provide custom PR diffs to see how the AI handles them
- Configure validation rules (mandatory fields, forbidden fields, allowed types)
- Test multi-language output
- Test with custom system prompts
- See the full prompt sent to Claude for debugging

## Installation

No special installation needed. Just ensure you have the dependencies:

```bash
pip install pyyaml requests
```

## Basic Usage

### Using Environment Variable (Recommended for Security)

The recommended and most secure approach is to use the `CLAUDE_API_KEY` environment variable:

```bash
export CLAUDE_API_KEY="sk-ant-api03-..."
python3 test_generator.py --diff path/to/your.diff
```

This avoids exposing your API token in shell history or process listings.

### Using Command-Line Argument

Alternatively, you can pass the token directly (useful for CI/CD):

```bash
python3 test_generator.py \
  --token sk-ant-api03-... \
  --diff path/to/your.diff
```

The command-line argument will override the environment variable if both are present.

### Simplest Test

```bash
export CLAUDE_API_KEY="sk-ant-api03-..."
python3 test_generator.py --diff example_diff.txt
```

This will:
1. Load the diff file
2. Create a default PR info object
3. Generate a changelog entry
4. Display the result

## All Available Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--token` | string | (env var) | Claude API token (overrides `CLAUDE_API_KEY` env var) |
| `--diff` | path | (required) | Path to diff file to test |
| `--pr-info` | path | (optional) | Path to PR info JSON file |
| `--pr-title` | string | "Test Pull Request" | PR title for default PR info |
| `--language` | string | English | Language for generated entry |
| `--model` | string | claude-opus-4-1-20250805 | Claude model to use |
| `--types` | string | (default types) | Comma-separated allowed types |
| `--mandatory` | string | (none) | Comma-separated mandatory fields |
| `--forbidden` | string | (none) | Comma-separated forbidden fields |
| `--max-tokens` | integer | 5000 | Max tokens for PR diff context |
| `--system-prompt` | path | (built-in) | Custom system prompt file |
| `--external-issue-regex` | string | (none) | Regex for external issues (e.g., `JIRA-(\d+)`) |
| `--external-issue-url-template` | string | (none) | URL template for external issues |
| `--github-issue-detection` | boolean | true | Detect GitHub issues (#123) |
| `--issue-tracker-url-detection` | boolean | true | Detect issue tracker URLs |
| `--generate-important-notes` | boolean | true | Generate important_notes field |
| `--verbose` | flag | false | Enable detailed logging |

## Advanced Options

### Language Testing

Generate changelog entries in different languages:

```bash
export CLAUDE_API_KEY="sk-ant-api03-..."
python3 test_generator.py \
  --diff changes.diff \
  --language German \
  --pr-title "Feature: Add webhook support"
```

Supports any language: `English`, `German`, `French`, `Spanish`, `Japanese`, etc.

### Custom Types

Test with a restricted set of changelog types:

```bash
export CLAUDE_API_KEY="sk-ant-api03-..."
python3 test_generator.py \
  --diff changes.diff \
  --types "feature,bugfix,security" \
  --pr-title "Fix security vulnerability"
```

The AI will be constrained to choose from only these types.

### Validation Rules

Test with custom mandatory and forbidden fields:

```bash
export CLAUDE_API_KEY="sk-ant-api03-..."
python3 test_generator.py \
  --diff changes.diff \
  --mandatory "title,type,authors,modules" \
  --forbidden "internal,draft" \
  --pr-title "Feature: Add webhook support"
```

The generated entry will be instructed to:
- Include: title, type, authors, modules
- Exclude: internal, draft

### Custom PR Info

Instead of using defaults, provide a JSON file with PR information:

```bash
export CLAUDE_API_KEY="sk-ant-api03-..."
python3 test_generator.py \
  --diff changes.diff \
  --pr-info pr_info.json
```

PR info JSON format:

```json
{
  "title": "Add webhook support",
  "body": "Implements webhook endpoints for external integrations",
  "user": {
    "login": "alice-dev",
    "html_url": "https://github.com/alice-dev"
  },
  "labels": [
    {"name": "feature"},
    {"name": "api"}
  ],
  "commits": [
    {
      "author": {
        "login": "alice-dev"
      }
    },
    {
      "author": {
        "login": "bob-dev"
      }
    }
  ]
}
```

### Custom System Prompt

Test with a custom system prompt:

```bash
export CLAUDE_API_KEY="sk-ant-api03-..."
python3 test_generator.py \
  --diff changes.diff \
  --system-prompt custom_prompt.txt
```

### Verbose Debugging

Enable detailed logging to see what's sent to Claude:

```bash
export CLAUDE_API_KEY="sk-ant-api03-..."
python3 test_generator.py \
  --diff changes.diff \
  --verbose
```

This shows:
- Full prompt sent to Claude
- API request/response details
- Generation step-by-step

### Model Selection

Use a different Claude model:

```bash
export CLAUDE_API_KEY="sk-ant-api03-..."
python3 test_generator.py \
  --diff changes.diff \
  --model claude-3-5-haiku-20241022
```

Available models:
- `claude-opus-4-1-20250805` (default)
- `claude-3-5-sonnet-20241022`
- `claude-3-5-haiku-20241022`
- etc.

## Metadata Extraction Options

### External Issue Tracker Configuration

Test with JIRA or other external issue tracking systems:

```bash
export CLAUDE_API_KEY="sk-ant-api03-..."
python3 test_generator.py \
  --diff changes.diff \
  --external-issue-regex "JIRA-(\d+)" \
  --external-issue-url-template "https://jira.example.com/browse/JIRA-{id}" \
  --pr-title "Fix JIRA-123 and JIRA-456"
```

This will:
- Extract JIRA issue references from PR title/description
- Add them to the changelog metadata as links
- Support custom regex patterns for different trackers

**Other tracker examples:**

Azure DevOps:
```bash
python3 test_generator.py \
  --diff changes.diff \
  --external-issue-regex "AB#(\d+)" \
  --external-issue-url-template "https://dev.azure.com/myorg/myproject/_workitems/edit/{id}"
```

### GitHub Issue Detection

By default, the tool detects GitHub issues (#123 references). To disable:

```bash
export CLAUDE_API_KEY="sk-ant-api03-..."
python3 test_generator.py \
  --diff changes.diff \
  --github-issue-detection false
```

GitHub issue detection recognizes keywords:
- `fixes #123`, `fixed #456`
- `closes #789`, `closed #100`
- `resolves #200`, `resolved #300`
- `references #400`, `refs #500`
- `see #600`, `issue #700`, `issues #800`

### Issue Tracker URL Detection

By default, the tool detects URLs that match configured issue trackers. To disable:

```bash
export CLAUDE_API_KEY="sk-ant-api03-..."
python3 test_generator.py \
  --diff changes.diff \
  --issue-tracker-url-detection false
```

When enabled, only URLs matching your configured external issue trackers are added as metadata links. Generic documentation URLs are not included.

### Important Notes Generation

By default, the AI is instructed to generate `important_notes` for breaking changes, security updates, etc. To disable:

```bash
export CLAUDE_API_KEY="sk-ant-api03-..."
python3 test_generator.py \
  --diff changes.diff \
  --generate-important-notes false
```

The AI will generate `important_notes` when the change includes:
- Breaking changes
- Security implications
- Major deprecations
- Migration guidance needed
- Performance impacts
- Database changes

### Combined Metadata Example

Test all metadata extraction features together:

```bash
export CLAUDE_API_KEY="sk-ant-api03-..."
python3 test_generator.py \
  --diff webhook_changes.diff \
  --pr-info webhook_pr.json \
  --pr-title "Add webhook support (fixes #123, relates to JIRA-456)" \
  --external-issue-regex "JIRA-(\d+)" \
  --external-issue-url-template "https://jira.example.com/browse/JIRA-{id}" \
  --github-issue-detection true \
  --issue-tracker-url-detection true \
  --generate-important-notes true \
  --verbose
```

This will:
1. Extract PR number and add to `merge_requests`
2. Find `#123` and add to `issues`
3. Find `JIRA-456` and add to `links` with URL
4. Include AI-generated `important_notes` if applicable
5. Show verbose output for debugging

## Complete Example

```bash
export CLAUDE_API_KEY="sk-ant-api03-..."
python3 test_generator.py \
  --diff webhook_feature.diff \
  --pr-info webhook_pr.json \
  --language German \
  --types "feature,bugfix,security" \
  --mandatory "title,type,authors" \
  --forbidden "internal,draft" \
  --external-issue-regex "JIRA-(\d+)" \
  --external-issue-url-template "https://jira.example.com/browse/JIRA-{id}" \
  --github-issue-detection true \
  --issue-tracker-url-detection true \
  --generate-important-notes true \
  --model claude-opus-4-1-20250805 \
  --max-tokens 5000 \
  --verbose
```

This comprehensive example tests:
- Custom PR info from JSON file
- German language output
- Restricted changelog types
- Mandatory and forbidden fields
- JIRA issue tracking with custom regex
- GitHub issue detection
- URL tracking for issue trackers
- Important notes generation
- Verbose debugging output

## Output

Successful generation:

```
================================================================================
GENERATED CHANGELOG ENTRY:
================================================================================
title: Add webhook registration feature
type: added
authors:
  - name: test-developer
    url: https://github.com/test-developer
================================================================================
```

Failed generation shows error details in the logs.

## Creating Test Diffs

### Sample Diff File

```diff
diff --git a/src/api.py b/src/api.py
index abc123..def456 100644
--- a/src/api.py
+++ b/src/api.py
@@ -1,5 +1,20 @@
 """API module"""

+async def register_webhook(url: str, events: List[str]) -> Dict:
+    """Register a new webhook for events"""
+    if not url or not events:
+        raise ValueError("URL and events required")
+
+    webhook = {
+        "url": url,
+        "events": events,
+        "active": True
+    }
+    return webhook
+
 def process_request(data):
     return {
         "status": "received"
```

You can extract real diffs from GitHub:

```bash
# Get a diff from a GitHub URL
curl -L https://github.com/owner/repo/pull/123.diff > pr_123.diff

# Or use git
git diff main...feature-branch > changes.diff
```

## Tips

1. **Test with your actual diffs** - Use real code changes to ensure the generator works with your codebase style
2. **Create reusable PR info files** - Store JSON examples for different project types
3. **Use verbose mode for debugging** - See exactly what prompt Claude receives
4. **Test your validation rules** - Ensure mandatory/forbidden fields work as expected
5. **Try different models** - Haiku is faster/cheaper for testing, Opus is more capable

## Troubleshooting

### "API Token Invalid"
- Verify your token starts with `sk-ant-api03-`
- Check token hasn't expired
- Verify in Claude dashboard it's still active

### "No YAML Generated"
- Check the diff file exists and is readable
- Use `--verbose` to see what prompt was sent
- Try with a simpler diff
- Check logs for specific error messages

### "Forbidden Fields Not Working"
- Ensure field names exactly match (case-sensitive)
- Remember this is a hint to the AI, not a guarantee
- For strict enforcement, use in production workflow validation

### "Language Not Working"
- The AI will make a best effort, but may not always generate in exact language
- Use verbose mode to see the system prompt
- Try with `--mandatory` to force specific structure

## Environment Variables

### Claude API Token

The most important environment variable is `CLAUDE_API_KEY`. This is the recommended way to provide your API token:

```bash
export CLAUDE_API_KEY="sk-ant-api03-..."
python3 test_generator.py --diff changes.diff
```

The token can still be overridden with `--token` if needed:

```bash
python3 test_generator.py --token sk-ant-api03-other... --diff changes.diff
```

**Security Note**: Using environment variables keeps your API token out of:
- Shell history
- Process listings
- Script files
- Git repositories

This is the recommended approach for all security-sensitive credentials.

## Integration with CI/CD

Use this in your CI pipeline to validate generated changelogs:

```bash
#!/bin/bash
python3 test_generator.py \
  --token $CLAUDE_TOKEN \
  --diff $DIFF_FILE \
  --pr-info $PR_INFO \
  --mandatory "title,type,authors" \
  || exit 1
```

## Performance

- **Generation time**: ~3-5 seconds per request
- **Token usage**: ~500-1000 tokens per generation (depends on diff size)
- **Cost**: ~$0.01-0.02 per generation with standard models

## Support

For issues or questions:
1. Check the logs with `--verbose`
2. Review the prompt sent to Claude (in verbose output)
3. Consult the main README.md for configuration details
4. Check changelog_generator.py source code for implementation details
