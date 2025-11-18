# Publishing to PyPI

This guide will help you publish `harlequin-athena` to PyPI.

## Quick Start: GitHub Actions (Recommended)

The easiest way to publish is using the GitHub Actions workflow:

1. **Set up PyPI API Token**:
   - Go to https://pypi.org/manage/account/token/
   - Create a new API token
   - Add it as a secret in GitHub: **Settings** → **Secrets and variables** → **Actions** → **New repository secret**
   - Name: `PYPI_API_TOKEN`, Value: your token

2. **Publish via Release**:
   ```bash
   # Update version
   poetry version patch  # or minor, major
   
   # Commit and push
   git add pyproject.toml
   git commit -m "Bump version to X.Y.Z"
   git push
   
   # Create a GitHub release with tag vX.Y.Z
   # The workflow will automatically publish to PyPI
   ```

See `.github/workflows/README.md` for more details.

## Manual Publishing

If you prefer to publish manually, follow the steps below.

## Prerequisites

1. **PyPI Account**: Create an account at https://pypi.org/account/register/
2. **TestPyPI Account** (optional but recommended): Create an account at https://test.pypi.org/account/register/
3. **Poetry**: Make sure Poetry is installed and configured

## Before Publishing

### 1. Update Metadata in `pyproject.toml`

Update the following fields with your actual information:

- `authors`: Replace `"Your Name <your.email@example.com>"` with your name and email
- `repository`: Replace `"https://github.com/yourusername/harlequin-athena"` with your actual GitHub repository URL
- `documentation`: Update if your documentation is hosted elsewhere

### 2. Verify Package Name Availability

Check if `harlequin-athena` is available on PyPI:
- Visit https://pypi.org/project/harlequin-athena/
- If it's taken, you'll need to choose a different name

### 3. Build and Test Locally

```bash
# Build the package
poetry build

# This creates dist/harlequin_athena-0.1.0.tar.gz and dist/harlequin_athena-0.1.0-py3-none-any.whl
```

### 4. Test on TestPyPI (Recommended)

First, configure Poetry to use TestPyPI:

```bash
# Set TestPyPI as a repository
poetry config repositories.testpypi https://test.pypi.org/legacy/

# Publish to TestPyPI
poetry publish --repository testpypi

# You'll be prompted for your TestPyPI credentials:
# Username: your-testpypi-username
# Password: your-testpypi-password (or API token)
```

Test the installation from TestPyPI:

```bash
pip install --index-url https://test.pypi.org/simple/ harlequin-athena
```

## Publishing to PyPI

### Option 1: Using Poetry (Recommended)

```bash
# Make sure you're logged in (or Poetry will prompt you)
poetry publish

# You'll be prompted for your PyPI credentials:
# Username: your-pypi-username
# Password: your-pypi-password (or API token)
```

### Option 2: Using API Token (More Secure)

1. Generate an API token on PyPI:
   - Go to https://pypi.org/manage/account/token/
   - Create a new API token
   - Copy the token (starts with `pypi-`)

2. Configure Poetry to use the token:

```bash
poetry config pypi-token.pypi your-api-token-here
```

3. Publish:

```bash
poetry publish
```

### Option 3: Using twine (Alternative)

```bash
# Install twine if not already installed
pip install twine

# Build the package
poetry build

# Upload to PyPI
twine upload dist/*

# You'll be prompted for credentials or can use environment variables
```

## After Publishing

1. **Verify Installation**: Test that the package can be installed:
   ```bash
   pip install harlequin-athena
   ```

2. **Check PyPI Page**: Visit https://pypi.org/project/harlequin-athena/ to see your published package

3. **Update Version**: For future releases, update the version in `pyproject.toml`:
   ```toml
   version = "0.1.1"  # or use semantic versioning
   ```

4. **Create Git Tag**: Tag the release in git:
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

## Version Management

Follow semantic versioning (semver):
- **MAJOR.MINOR.PATCH** (e.g., 1.2.3)
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

Update version in `pyproject.toml` before each release.

## Troubleshooting

- **"Package already exists"**: The version number is already published. Increment the version.
- **"Invalid credentials"**: Check your username/password or API token.
- **"Package name taken"**: Choose a different package name or contact the current owner.

## Additional Resources

- [Poetry Publishing Documentation](https://python-poetry.org/docs/cli/#publish)
- [PyPI Help](https://pypi.org/help/)
- [Python Packaging User Guide](https://packaging.python.org/)

