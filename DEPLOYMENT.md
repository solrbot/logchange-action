# Deployment Guide

This guide explains how to deploy your own version of the Logchange Action to GitHub.

## Self-Hosting Overview

The Logchange Action is designed to be self-hosted. You can fork the repository and publish your own version to:
- **GitHub Container Registry (GHCR)** - Recommended, integrated with GitHub
- **Docker Hub** - Public or private registry
- **Any OCI-compliant container registry** - AWS ECR, Azure ACR, Google GCR, etc.

## Prerequisites

- GitHub account with owner permissions on your fork
- Docker installed locally
- Git installed
- Container registry credentials (GHCR recommended)

## Step 1: Fork the Repository

1. Click "Fork" on the [original repository](https://github.com/solrbot/logchange-action)
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR-USERNAME/logchange-action.git
   cd logchange-action
   ```

## Step 2: Update Configuration

1. **Update `action.yml`** to point to your container registry:
   ```yaml
   runs:
     using: 'docker'
     image: 'docker://ghcr.io/YOUR-USERNAME/logchange-action:latest'
     entrypoint: '/action/src/entrypoint.sh'
   ```

   Replace `YOUR-USERNAME` with your GitHub username. Choose your registry:
   - **GHCR**: `ghcr.io/YOUR-USERNAME/logchange-action`
   - **Docker Hub**: `docker.io/YOUR-USERNAME/logchange-action`
   - **Other**: Use your registry's image path

2. **Commit the change**:
   ```bash
   git add action.yml
   git commit -m "Configure image registry for YOUR-USERNAME"
   git push origin main
   ```

## Step 3: Build and Push Docker Image

### Option A: GitHub Container Registry (GHCR) - Recommended

GHCR is built into GitHub and integrates seamlessly with your repository.

1. **Authenticate with GHCR**:
   ```bash
   # Create a GitHub personal access token with 'write:packages' scope
   # at https://github.com/settings/tokens

   echo $GITHUB_TOKEN | docker login ghcr.io -u YOUR-USERNAME --password-stdin
   ```

2. **Build and tag the image**:
   ```bash
   docker build -t ghcr.io/YOUR-USERNAME/logchange-action:latest .
   docker tag ghcr.io/YOUR-USERNAME/logchange-action:latest ghcr.io/YOUR-USERNAME/logchange-action:v1.0.0
   ```

3. **Push to GHCR**:
   ```bash
   docker push ghcr.io/YOUR-USERNAME/logchange-action:latest
   docker push ghcr.io/YOUR-USERNAME/logchange-action:v1.0.0
   ```

4. **Make package public** (optional, for public reuse):
   - Go to your repository → Packages → logchange-action
   - Click "Package settings"
   - Change visibility to "Public"

### Option B: Docker Hub

1. **Authenticate with Docker Hub**:
   ```bash
   docker login -u YOUR-DOCKERHUB-USERNAME
   ```

2. **Build and tag the image**:
   ```bash
   docker build -t YOUR-DOCKERHUB-USERNAME/logchange-action:latest .
   docker tag YOUR-DOCKERHUB-USERNAME/logchange-action:latest YOUR-DOCKERHUB-USERNAME/logchange-action:v1.0.0
   ```

3. **Push to Docker Hub**:
   ```bash
   docker push YOUR-DOCKERHUB-USERNAME/logchange-action:latest
   docker push YOUR-DOCKERHUB-USERNAME/logchange-action:v1.0.0
   ```

### Option C: Other Registries (AWS ECR, Azure ACR, etc.)

Follow your registry's authentication and push procedures. The build command remains the same:
```bash
docker build -t YOUR-REGISTRY/logchange-action:latest .
docker push YOUR-REGISTRY/logchange-action:latest
```

## Step 4: Create a GitHub Release

1. **Create a Git tag**:
   ```bash
   git tag -a v1.0.0 -m "Initial release: Logchange Action"
   git push origin v1.0.0
   ```

2. **Create a GitHub Release**:
   - Go to your repository → Releases → New release
   - Use the tag `v1.0.0`
   - Add release notes describing features and changes
   - Publish the release

## Step 5: Use Your Action

Now you can use your action in workflows:

```yaml
- uses: YOUR-USERNAME/logchange-action@v1.0.0
  with:
    on-missing-entry: generate
    claude-token: ${{ secrets.CLAUDE_API_KEY }}
```

Or use the latest version:
```yaml
- uses: YOUR-USERNAME/logchange-action@latest
```

Or use the main branch (for development):
```yaml
- uses: YOUR-USERNAME/logchange-action@main
```

## Semantic Versioning

Follow semantic versioning for releases:

- **v1.0.0** - Major version (breaking changes)
- **v1.1.0** - Minor version (new features, backwards compatible)
- **v1.0.1** - Patch version (bug fixes)

## Updating to New Versions

When you want to release a new version:

1. **Update files as needed** (code, documentation, etc.)

2. **Run tests locally**:
   ```bash
   python3 test_action_cli.py validate --sample "title: Test\ntype: added"
   ```

3. **Tag and push a new release**:
   ```bash
   git tag -a v1.1.0 -m "Add feature X, fix bug Y"
   git push origin v1.1.0
   ```

4. **Build and push new Docker images**:
   ```bash
   docker build -t ghcr.io/YOUR-USERNAME/logchange-action:v1.1.0 .
   docker tag ghcr.io/YOUR-USERNAME/logchange-action:v1.1.0 ghcr.io/YOUR-USERNAME/logchange-action:latest
   docker push ghcr.io/YOUR-USERNAME/logchange-action:v1.1.0
   docker push ghcr.io/YOUR-USERNAME/logchange-action:latest
   ```

5. **Create a GitHub Release** with the new tag

## Automated Deployment (Optional)

You can automate Docker image builds with GitHub Actions. See `.github/workflows/docker-build-push.yml` for an example workflow that:
- Builds Docker images on tag pushes
- Pushes to your container registry
- Creates major version tags (e.g., `v1` from `v1.0.0`)

To enable this workflow:
1. Ensure `action.yml` points to your registry
2. Ensure your fork has Actions enabled
3. Push a new tag to trigger the workflow

## Troubleshooting

### Docker push fails with authentication error
- Verify your container registry credentials
- Check that your token has the correct scopes (`write:packages` for GHCR)
- Try re-authenticating: `docker logout && docker login ghcr.io`

### Workflow uses old image
- Ensure `action.yml` points to the correct registry
- Try using a specific version tag instead of `latest`
- Clear Docker cache: `docker image rm <image-id>`

### Image not found in workflow
- Verify the image was successfully pushed: Check your registry's web UI
- Ensure the tag matches exactly in `action.yml`
- Try rebuilding and pushing with verbose output: `docker push -verbose`

## Support

For issues with:
- **Logchange format**: See [logchange documentation](https://logchange.dev/)
- **This action**: Check [CONTRIBUTING.md](CONTRIBUTING.md) and [LOCAL_TESTING.md](LOCAL_TESTING.md)
- **Claude API**: See [Claude documentation](https://docs.anthropic.com/)
