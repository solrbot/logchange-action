# Deployment Guide

This guide explains how to deploy the Logchange Action to GitHub.

## Prerequisites

1. GitHub account with owner permissions for the organization/user (we use `solrbot` as example)
2. Docker Hub account (for publishing Docker image) - optional but recommended
3. Git installed locally

## Step 1: Publish to GitHub

### Initial Setup

1. **Ensure you're on the main branch**:
   ```bash
   git checkout main
   git pull origin main
   ```

2. **Create a release tag**:
   ```bash
   git tag -a v1.0.0 -m "Initial release: Logchange GitHub Action"
   git push origin v1.0.0
   ```

3. **Create a GitHub Release**:
   - Go to https://github.com/solrbot/logchange-action/releases
   - Click "Create a new release"
   - Tag: `v1.0.0`
   - Title: "Logchange Action v1.0.0"
   - Description:
     ```
     Initial release of the Logchange GitHub Action

     Features:
     - Enforce changelog entries in PRs
     - Validate against logchange specification
     - AI-powered changelog generation with Claude
     - Flexible configuration options
     - PR commenting and suggestions

     See README.md for usage instructions.
     ```
   - Publish release

## Step 2: Set Up Docker Image (Optional)

### Push to Docker Hub

1. **Build the Docker image**:
   ```bash
   docker build -t logchange-action:latest .
   docker tag logchange-action:latest docker.io/solrbot/logchange-action:latest
   docker tag logchange-action:latest docker.io/solrbot/logchange-action:v1.0.0
   ```

2. **Push to Docker Hub**:
   ```bash
   docker login
   docker push docker.io/solrbot/logchange-action:latest
   docker push docker.io/solrbot/logchange-action:v1.0.0
   ```

### Update action.yml for Docker Hub

If using Docker Hub, update `action.yml`:
```yaml
runs:
  using: 'docker'
  image: 'docker://solrbot/logchange-action:v1.0.0'
```

## Step 3: Testing the Action

### Test with a Real PR

1. **Create a test repository** in the solrbot organization
2. **Set up a test workflow** (`.github/workflows/test.yml`):
   ```yaml
   name: Test Logchange Action

   on:
     pull_request:
       types: [opened, synchronize, reopened]

   jobs:
     test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: solrbot/logchange-action@v1.0.0
           with:
             on-missing-entry: warn
   ```

3. **Create a test PR** without a changelog entry
4. **Verify the action runs** and posts a comment

### Test with Different Configurations

Test each major feature:
1. **Fail mode**: PR without entry should fail
2. **Warn mode**: PR without entry should warn but pass
3. **Generate mode** (with Claude token):
   - PR without entry should generate suggestion
   - Verify generated YAML is valid

## Step 4: Version Management

### Versioning Strategy

Use semantic versioning:
- `v1.0.0` - Initial release
- `v1.1.0` - Minor feature additions
- `v1.0.1` - Bug fixes
- `v2.0.0` - Breaking changes

### Creating New Releases

For each release:

1. **Update version number** in documentation if needed
2. **Create and push tag**:
   ```bash
   git tag -a v1.1.0 -m "Feature: Add support for custom validators"
   git push origin v1.1.0
   ```

3. **Create GitHub Release** with changelog
4. **Update Docker images**:
   ```bash
   docker build -t solrbot/logchange-action:v1.1.0 .
   docker push solrbot/logchange-action:v1.1.0
   docker tag solrbot/logchange-action:v1.1.0 solrbot/logchange-action:latest
   docker push solrbot/logchange-action:latest
   ```

## Step 5: Update Action.yml for Release

After each release, users can reference specific versions:

```yaml
# Latest stable version
- uses: solrbot/logchange-action@v1.0.0

# Latest in minor version series
- uses: solrbot/logchange-action@v1.0

# Latest version
- uses: solrbot/logchange-action@latest

# Development version
- uses: solrbot/logchange-action@main
```

## Step 6: Publish to GitHub Marketplace (Future)

To publish on GitHub Marketplace:

1. **Ensure requirements are met**:
   - Action.yml has proper branding
   - README.md is comprehensive
   - LICENSE file is present
   - No sensitive data in repo

2. **Go to GitHub Marketplace settings**:
   - https://github.com/solrbot/logchange-action/settings/actions
   - Click "Publish this action to GitHub Marketplace"

3. **Fill out the form**:
   - Category: Utilities
   - Description: (from action.yml)
   - Primary Language: Python

## Monitoring

### Check Action Usage

Track usage metrics:
- GitHub Insights tab shows workflow runs
- Check for issues or feature requests
- Monitor for error patterns in logs

### Troubleshooting

If users report issues:

1. **Check logs**: Review action logs in their workflows
2. **Create fix**: Make necessary changes in main branch
3. **Release patch**: Tag and release as `v1.0.1`, etc.
4. **Notify users**: Update README with any workarounds

## Maintenance Plan

1. **Weekly**: Check for issues and PRs
2. **Monthly**: Review usage metrics
3. **Quarterly**: Consider feature enhancements
4. **As needed**: Security updates and bug fixes

## Rollback Plan

If a release has critical issues:

1. **Identify the issue** through user reports or testing
2. **Revert to previous version**:
   ```bash
   # Tag the issue version as broken
   git tag -a v1.0.0-broken -m "Broken release"
   git push origin v1.0.0-broken

   # Update release documentation
   ```

3. **Release hotfix**:
   ```bash
   git tag -a v1.0.1 -m "Hotfix for critical issue"
   git push origin v1.0.1
   ```

4. **Update users**: Post notice in releases

## Security Considerations for Deployment

1. **API Tokens**:
   - Never commit credentials
   - Use GitHub Secrets for Claude token
   - Rotate tokens regularly

2. **Docker Image**:
   - Keep dependencies up to date
   - Scan for vulnerabilities
   - Use specific Python version tags

3. **Access Control**:
   - Only maintainers can push releases
   - Require reviews for main branch
   - Use branch protection rules

## Support Resources

- **Documentation**: README.md and ARCHITECTURE.md
- **Examples**: examples/ directory with sample workflows
- **Tests**: tests/ directory with unit tests
- **Issues**: GitHub Issues for bug reports and features

---

For questions or issues, please open a GitHub issue.
