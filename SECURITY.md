# Security Policy

## Workflow Security

This action uses GitHub Actions' `pull_request_target` event to enable commenting on pull requests from forks. This approach requires careful consideration of security implications.

### Why pull_request_target?

Standard `pull_request` events on fork PRs cannot:
- Comment on the PR
- Create review comments
- Access secrets with full scope

We need these capabilities to provide changelog validation and AI-generated suggestions.

### Security Safeguards

**✅ Safe by design:**

1. **Explicit checkout of PR code**: We check out the PR's actual head commit (`head.sha`), not untrusted base code:
   ```yaml
   ref: ${{ github.event.pull_request.head.sha }}
   ```

2. **Limited token scope**: Workflows only receive `pull-requests:write` permission:
   ```yaml
   permissions:
     contents: read
     pull-requests: write
   ```
   This prevents malicious code from modifying the repository.

3. **Non-destructive validation**: The action reads and validates changelog format—it doesn't execute arbitrary PR code.

4. **Containerized execution**: The action runs in an isolated Docker container.

5. **No secret exfiltration**: Sensitive values (tokens, API keys) are never printed to logs.

### What This Means

- ✅ Fork PRs can receive changelog validation and AI suggestions
- ✅ Malicious PRs cannot modify your repository
- ✅ Malicious PRs cannot access repository secrets with write scope
- ⚠️ Untrusted code from PRs runs in the action's environment (read-only context)

### Recommendations for Repository Owners

**For public projects accepting community PRs:**

1. Keep `pull_request_target` enabled to support fork contributions
2. Trust the validation performed by GitHub Actions (code review is still recommended)
3. Monitor action logs for unusual activity

**For private projects or additional security:**

1. Switch to standard `pull_request` (fork PRs won't get comments, but only internal PRs will run)
2. Use branch protection rules requiring maintainer approval before workflows run
3. Implement manual approval workflows for external contributions

### Reporting Security Issues

If you discover a security vulnerability in this action:

1. **Do not** open a public GitHub issue
2. Report to the repository maintainers privately
3. Include details about the vulnerability and potential impact

## Best Practices When Using This Action

1. **Keep dependencies updated**: Regularly update GitHub Actions and Docker images
2. **Review logs**: Check workflow logs for unexpected behavior
3. **Use specific action versions**: Pin to a specific version tag rather than `@main` or `@latest`
4. **Validate changelog entries**: Even with automation, human review of changelog entries is recommended
5. **Restrict secrets**: Only provide necessary secrets (GITHUB_TOKEN is automatically provided)
