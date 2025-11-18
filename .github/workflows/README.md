# GitHub Actions Workflows

This repository includes GitHub Actions workflows for CI/CD.

## Workflows

### CI (`ci.yml`)

Runs on every push and pull request to main/master:
- Linting with ruff
- Type checking with mypy
- Running tests with pytest
- Building the package to verify it builds correctly

### Publish (`publish.yml`)

Publishes the package to PyPI. Triggers:

1. **Automatic on Release**: When you create a GitHub release, it automatically publishes to PyPI
2. **Manual**: You can manually trigger the workflow from the Actions tab

## Setup for Publishing

### 0. Create GitHub Environment (Optional but Recommended)

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Environments**
3. Click **New environment**
4. Name it `pypi`
5. (Optional) Add protection rules:
   - **Required reviewers**: Require approval before publishing
   - **Wait timer**: Add a delay before deployment
   - **Deployment branches**: Restrict to specific branches

This adds an extra layer of security and control over PyPI publishing.

### 1. Create PyPI API Tokens

**Option A: API Token (Simpler)**
1. Go to https://pypi.org/manage/account/token/
2. Create a new API token (scope: "Entire account" or project-specific)
3. Copy the token (starts with `pypi-`)

**Option B: Trusted Publishing (More Secure, Recommended)**
1. Go to https://pypi.org/manage/account/publishing/
2. Add a new pending publisher
3. Owner: Your PyPI username
4. Project name: `harlequin-athena`
5. Workflow filename: `.github/workflows/publish.yml`
6. Environment name: (leave empty or use `release`)
7. After adding, approve the publisher from the pending list

If using trusted publishing, you don't need to add the `PYPI_API_TOKEN` secret - the workflow will use OIDC authentication automatically.

### 2. Create TestPyPI API Token (Optional)

1. Go to https://test.pypi.org/manage/account/token/
2. Create a new API token
3. Copy the token

### 3. Add Secrets to GitHub

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Add the following secrets:
   - `PYPI_API_TOKEN`: Your PyPI API token
   - `TEST_PYPI_API_TOKEN`: Your TestPyPI API token (optional)

## Publishing a Release

### Method 1: Create a GitHub Release (Recommended)

1. Update the version in `pyproject.toml`:
   ```bash
   poetry version patch  # or minor, major
   ```

2. Commit and push the version change:
   ```bash
   git add pyproject.toml
   git commit -m "Bump version to X.Y.Z"
   git push
   ```

3. Create a GitHub release:
   - Go to **Releases** → **Draft a new release**
   - Create a new tag (e.g., `v0.1.0`) matching the version in `pyproject.toml`
   - Fill in release notes
   - Click **Publish release**
   - The workflow will automatically publish to PyPI

### Method 2: Manual Workflow Dispatch

1. Go to **Actions** → **Publish to PyPI**
2. Click **Run workflow**
3. Enter the version number (e.g., `0.1.0`)
4. Choose whether to publish to TestPyPI first
5. Click **Run workflow**

## Notes

- **Prereleases**: If you create a prerelease on GitHub, it will publish to TestPyPI instead of PyPI
- **Version Matching**: When publishing via release, the tag version must match the version in `pyproject.toml`
- **Trusted Publishing**: The workflow uses PyPI's trusted publishing feature (no password needed if configured)

