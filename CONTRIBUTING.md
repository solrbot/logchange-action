# Contributing

## Setup

```bash
git clone https://github.com/solrbot/logchange-action.git
cd logchange-action
pip install -r action/src/requirements.txt
pip install black isort flake8 pytest pytest-cov
```

## Code Style and Formatting

Uses [Black](https://github.com/psf/black), [isort](https://pycqa.github.io/isort/), and [Flake8](https://flake8.pycqa.org/):

```bash
# Format code
black action/src/ tests/ test_action_cli.py
isort action/src/ tests/ test_action_cli.py

# Verify before committing
black --check action/src/ tests/ test_action_cli.py && \
isort --check-only action/src/ tests/ test_action_cli.py && \
flake8 action/src/ tests/ test_action_cli.py
```

## Testing

```bash
# Run all unit tests
python3 -m pytest tests/ -v

# Run tests with coverage
python3 -m pytest tests/ --cov=action/src --cov-report=html

# Run specific test file
python3 -m pytest tests/test_validator.py -v

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

## Code Style Guidelines

- Follow PEP 8 standards
- 4 spaces indentation
- Docstrings on public functions
- Type hints where appropriate
- Use black for code formatting
- Use isort for import organization
- Pass flake8 linting checks

## Development Workflow

When making changes to the codebase:

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** and add tests if necessary

3. **Add a changelog entry**:
   ```bash
   # Create a new entry in the changelog directory
   cat > changelog/unreleased/your-feature.yml << 'EOF'
   title: Brief description of your changes
   type: added
   authors:
     - name: Your Name
       nick: your-github-username
       url: https://github.com/your-github-username
   EOF
   ```

4. **Format your code**:
   ```bash
   black action/src/ tests/ test_action_cli.py
   isort action/src/ tests/ test_action_cli.py
   ```

5. **Run all checks**:
   ```bash
   # Run formatting checks
   black --check action/src/ tests/ test_action_cli.py
   isort --check-only action/src/ tests/ test_action_cli.py
   flake8 action/src/ tests/ test_action_cli.py

   # Run tests
   python3 -m pytest tests/ -v
   ```

6. **Commit with a clear message**:
   ```bash
   git add .
   git commit -m "Description of your changes"
   ```

7. **Push and create a pull request**:
   ```bash
   git push origin feature/your-feature-name
   ```

   The PR will run automated checks (black, isort, flake8, pytest) via GitHub Actions

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

## Security

See [DEPLOYMENT.md](DEPLOYMENT.md#security-considerations) for information about:
- How this action handles fork pull requests securely
- Why we use `pull_request_target` event
- Security safeguards in place
- Best practices for repository owners
