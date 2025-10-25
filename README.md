# Logchange Action

GitHub Action to enforce [logchange](https://logchange.dev/) changelog entries in PRs, with optional AI generation via Claude.

## Features

- PR workflow detection with file change analysis
- Three modes: `fail`, `warn`, or `generate` (via Claude)
- Validates entries against logchange specification
- Custom validation rules (types, mandatory/forbidden fields)
- Intelligent diff truncation for token optimization
- Automatic PR metadata extraction (merge requests, issues, links)
- External issue tracker support (JIRA, Azure DevOps, Linear, etc.)
- AI-guided important notes generation
- Posts PR comments with suggestions

## Quick Start

Add this to your workflow file (e.g., `.github/workflows/changelog-check.yml`):

**Basic (fail on missing entry):**
```yaml
- uses: actions/checkout@v4
- uses: solrbot/logchange-action@v1
```

**With AI generation (requires Claude API key):**
```yaml
- uses: solrbot/logchange-action@v1
  with:
    on-missing-entry: generate
    claude-token: ${{ secrets.CLAUDE_API_KEY }}
```

**With warnings only:**
```yaml
- uses: solrbot/logchange-action@v1
  with:
    on-missing-entry: warn
```

## Configuration

### Common Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `changelog-path` | `changelog/unreleased` | Path to changelog directory |
| `on-missing-entry` | `fail` | Action: `fail`, `warn`, or `generate` |
| `skip-files-regex` | (empty) | Skip changelog if all files match pattern |
| `claude-token` | (empty) | Claude API key for generation |
| `claude-model` | `claude-3-5-sonnet-20241022` | Claude model to use |
| `changelog-language` | `English` | Language for generated entries |

### Validation Rules

| Input | Default | Description |
|-------|---------|-------------|
| `changelog-types` | (all default logchange types) | Allowed types |
| `mandatory-fields` | `title` | Fields that must be present |
| `forbidden-fields` | (empty) | Fields that must not be present |
| `optional-fields` | (empty) | Restrict to specific fields (empty = all allowed) |

### PR Metadata Extraction

| Input | Default | Description |
|-------|---------|-------------|
| `external-issue-regex` | (empty) | Regex to detect external issues (e.g., `JIRA-(\d+)`) |
| `external-issue-url-template` | (empty) | URL template with {id} placeholder (e.g., `https://jira.example.com/browse/{id}`) |
| `generate-important-notes` | `true` | Instruct AI to generate important_notes field |
| `github-issue-detection` | `true` | Detect GitHub issue references (#123) in PR description |
| `issue-tracker-url-detection` | `true` | Detect issue tracker URLs via LLM filtering (only configured trackers added as links) |

### Advanced

| Input | Default | Description |
|-------|---------|-------------|
| `max-tokens-context` | `5000` | Max tokens to send to LLM for PR diff |
| `max-tokens-per-file` | `1000` | Max tokens per file |
| `claude-system-prompt` | (built-in) | Custom AI instructions |

## Examples

**Skip changelog for docs-only changes:**
```yaml
- uses: solrbot/logchange-action@v1
  with:
    skip-files-regex: '^(README\.md|docs/|\.github/)'
```

**Strict enterprise rules:**
```yaml
- uses: solrbot/logchange-action@v1
  with:
    on-missing-entry: generate
    claude-token: ${{ secrets.CLAUDE_API_KEY }}
    changelog-types: feature,bugfix,security
    mandatory-fields: title,type,authors
    optional-fields: title,type,authors,modules,issues
```

**German language generation:**
```yaml
- uses: solrbot/logchange-action@v1
  with:
    on-missing-entry: generate
    claude-token: ${{ secrets.CLAUDE_API_KEY }}
    changelog-language: German
```

**With external issue tracker (JIRA):**
```yaml
- uses: solrbot/logchange-action@v1
  with:
    on-missing-entry: generate
    claude-token: ${{ secrets.CLAUDE_API_KEY }}
    external-issue-regex: 'JIRA-(\d+)'
    external-issue-url-template: 'https://jira.example.com/browse/JIRA-{id}'
```

**With multiple external issue trackers (Azure DevOps):**
```yaml
- uses: solrbot/logchange-action@v1
  with:
    on-missing-entry: generate
    claude-token: ${{ secrets.CLAUDE_API_KEY }}
    external-issue-regex: 'AB#(\d+)'
    external-issue-url-template: 'https://dev.azure.com/myorg/myproject/_workitems/edit/{id}'
```

**Disable important notes generation:**
```yaml
- uses: solrbot/logchange-action@v1
  with:
    on-missing-entry: generate
    claude-token: ${{ secrets.CLAUDE_API_KEY }}
    generate-important-notes: false
```

**Disable GitHub issue detection:**
```yaml
- uses: solrbot/logchange-action@v1
  with:
    on-missing-entry: generate
    claude-token: ${{ secrets.CLAUDE_API_KEY }}
    github-issue-detection: false
```

## Changelog File Naming

When the action generates a changelog entry suggestion, it creates a well-structured slug-formatted filename based on the PR number and title.

**Examples:**
- PR #123 with title "Add authentication" → `pr-123-add-authentication.yml`
- PR #456 with title "Fix: Critical bug in API" → `pr-456-fix-critical-bug-in-api.yml`
- PR #789 with no title → `pr-789.yml`

## Outputs

- `changelog-found` - Whether a changelog entry was found
- `changelog-valid` - Whether it's valid
- `changelog-generated` - Whether one was generated
- `generation-error` - Error message if generation failed

## Logchange Format

Minimal entry:
```yaml
title: Brief description of change
type: added
authors:
  - name: Author Name
    nick: nickname
    url: https://github.com/author
```

### Metadata Fields (Auto-populated by Action)

When using AI generation with metadata extraction, the action automatically populates:

- **merge_requests**: PR number(s) from the GitHub context
  ```yaml
  merge_requests:
    - 123
  ```

- **issues**: GitHub issues referenced in the PR description
  ```yaml
  issues:
    - 456
    - 789
  ```

- **links**: External issue trackers (JIRA, Azure DevOps, etc.) and URLs found in PR description
  ```yaml
  links:
    - name: JIRA-123
      url: https://jira.example.com/browse/JIRA-123
    - name: Documentation
      url: https://docs.example.com/feature-guide
  ```

### Important Notes (AI-Guided)

When `generate-important-notes: true` (default), the AI is instructed to include an `important_notes` field if the change:
- Contains breaking changes
- Has security implications
- Introduces major deprecations
- Requires migration guidance
- Impacts performance
- Needs database changes

```yaml
important_notes: |
  Breaking change: The authentication API now requires OAuth2.
  Existing API key authentication will stop working on 2025-12-01.
```

See [logchange docs](https://logchange.dev/) for complete specification and additional fields.

## Deployment

### Publishing Your Own Version

This action is designed to be self-hosted. To publish your own version:

1. **Fork the repository** on GitHub
2. **Update the Docker image reference** in `action.yml` to point to your container registry
3. **Follow the deployment guide** in [DEPLOYMENT.md](DEPLOYMENT.md) for building and pushing Docker images
4. **Create a GitHub Release** with semantic versioning (e.g., `v1.0.0`)
5. **Use your version** in workflows with: `uses: YOUR-USERNAME/logchange-action@v1`

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions on:
- Building and pushing Docker images to your container registry
- Creating GitHub Releases
- Semantic versioning strategy
- Local testing with the CLI tool

### Local Testing

Use the included testing CLI tool to validate the action locally without running a full GitHub workflow:

```bash
# Test changelog validation
python3 test_action_cli.py validate --sample "title: Test\ntype: added"

# Test changelog generation (requires Claude API key)
export CLAUDE_API_KEY="sk-ant-..."
python3 test_action_cli.py generate --diff changes.diff

# See LOCAL_TESTING.md for comprehensive examples
```

## Credits

This action was created by [Jan Høydahl](https://github.com/janhoy) with assistance from [Claude Code](https://claude.com/claude-code).

 Special thanks to the [logchange](https://logchange.dev/) project team, particularly [Peter Zmilczak](https://github.com/marwin1991) (@marwin1991) for being incredibly responsive in fixing bugs, accepting feature requests, and providing excellent guidance. This work was inspired by the [Apache Solr](https://solr.apache.org/) project's needs for structured changelog management.

## License

Apache 2.0, see the `LICENSE` file.