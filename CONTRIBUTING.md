# Contributing

## Setup

```bash
git clone https://github.com/solrbot/logchange-action.git
cd logchange-action
pip install -r action/src/requirements.txt
pip install black isort flake8 pytest pytest-cov
```

## Code Style and Formatting

This project uses automated code formatting tools to ensure consistent code style:

### Black (Code Formatting)

[Black](https://github.com/psf/black) is used for automatic code formatting following PEP 8 conventions.

```bash
# Check formatting without making changes
black --check action/src/ tests/ test_generator.py

# Auto-format all Python files
black action/src/ tests/ test_generator.py
```

### isort (Import Sorting)

[isort](https://pycqa.github.io/isort/) organizes and sorts imports according to PEP 8.

```bash
# Check import sorting without making changes
isort --check-only action/src/ tests/ test_generator.py

# Auto-sort imports in all Python files
isort action/src/ tests/ test_generator.py
```

### Flake8 (Linting)

[Flake8](https://flake8.pycqa.org/) checks for code style and logical errors.

```bash
# Run flake8 linting
flake8 action/src/ tests/ test_generator.py \
  --max-complexity=10 --max-line-length=127
```

### Format Everything at Once

```bash
# Auto-format and sort in one command
black action/src/ tests/ test_generator.py && isort action/src/ tests/ test_generator.py
```

### Pre-commit Check

Before committing, verify all formatting and linting checks pass:

```bash
black --check action/src/ tests/ test_generator.py && \
isort --check-only action/src/ tests/ test_generator.py && \
flake8 action/src/ tests/ test_generator.py
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

3. **Format your code**:
   ```bash
   black action/src/ tests/ test_generator.py
   isort action/src/ tests/ test_generator.py
   ```

4. **Run all checks**:
   ```bash
   # Run formatting checks
   black --check action/src/ tests/ test_generator.py
   isort --check-only action/src/ tests/ test_generator.py
   flake8 action/src/ tests/ test_generator.py

   # Run tests
   python3 -m pytest tests/ -v
   ```

5. **Commit with a clear message**:
   ```bash
   git add .
   git commit -m "Description of your changes"
   ```

6. **Push and create a pull request**:
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

For security issues, email security@solrbot.dev instead of opening an issue.
