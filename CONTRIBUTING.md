# Contributing

## Setup

```bash
git clone https://github.com/solrbot/logchange-action.git
cd logchange-action
pip install -r action/src/requirements.txt
```

## Testing

```bash
# Run unit tests
python3 -m unittest tests.test_validator -v

# Test validator directly
python3 -c "
import sys
sys.path.insert(0, 'action/src')
from changelog_validator import ChangelogValidator
v = ChangelogValidator()
is_valid, errors = v.validate('title: Test\ntype: added')
print(f'Valid: {is_valid}, Errors: {errors}')
"
```

## Code Style

- Follow PEP 8
- 4 spaces indentation
- Docstrings on public functions
- Type hints where appropriate

## Testing Changes

1. Make your changes
2. Run unit tests: `python3 -m unittest tests.test_validator -v`
3. Test with sample data
4. Commit with clear message

## Docker Build

```bash
docker build -t logchange-action:test .
docker run -e GITHUB_EVENT_NAME=pull_request logchange-action:test
```

## Submitting PRs

- Clear title and description
- Reference related issues
- Keep focused on single feature
- Tests should pass

For security issues, email security@solrbot.dev instead of opening an issue.
