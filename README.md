# GitHub Action: Arduino Library Deploy

## Overview

This GitHub Action provides a comprehensive and automated solution for managing Arduino library releases. It supports two primary workflows:

1.  **Pull Request Workflow**: Validates `library.properties` on pull requests to ensure versioning and metadata are correct before merging.
2.  **Tag Push Workflow**: Automates the entire release process when a new version tag is pushed. It creates a pull request from a development branch, merges it, and drafts a new GitHub release.

This dual-workflow approach streamlines development, enforces standards, and eliminates manual release steps.

---

## Features

- **Dual Workflow Triggers**: Operates on both `pull_request` events for validation and `push` events (for tags) for full release automation.
- **Automatic PR Creation**: On a tag push, automatically creates a pull request from your development branch (e.g., `develop`) to your main branch.
- **Semantic Version Validation**: Ensures new tags or PR versions follow semantic versioning conventions against the latest release.
- **Automated Merging & Releasing**: Automatically merges the created pull request and drafts a new GitHub release corresponding to the pushed tag.
- **Library Metadata Validation**: Ensures `library.properties` exists.
- **Code Style Enforcement**: Uses `arduino-lint` to validate code style, ensuring consistency with Arduino standards.

---

## Inputs

| Input | Description | Required | Default |
|---|---|---|---|
| `lint-mode` | The library manager mode for `arduino-lint`. Can be `{submit|update|false}`. `submit` runs stricter checks for new libraries. | No | `update` |
| `source-branch` | The source branch for auto-creating PRs on a tag push. | No | `develop` |
| `target-branch` | The target branch for auto-creating PRs on a tag push. | No | `main` |

---

## Environment Variables

| Variable | Description | Required | Default |
|---|---|---|---|
| `GITHUB_TOKEN` | A GitHub token with permissions to create/merge pull requests and create releases. | Yes | `${{ secrets.GITHUB_TOKEN }}` |

---

## Usage

This action can be triggered by a `pull_request` event or a `push` event for tags.

### Example Workflow

Below is an example of a workflow that uses both triggers.

```yaml
name: Validate Library Version and Create Release

on:
  pull_request:
    types: [opened, synchronize, reopened]
  push:
    tags:
      - 'v*.*.*' # Triggers on tags like v1.2.3

jobs:
  validate-and-release:
    name: Validate Library Version and Create Release
    runs-on: ubuntu-latest
    # These permissions are required for creating PRs and releases
    permissions:
      contents: write
      pull-requests: write
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0 # Required to fetch all tags for version comparison

      - name: Arduino Library Deploy
        uses: Suzu-Gears/arduino-library-deploy@main
        with:
          # 'submit' runs stricter checks for new libraries
          lint-mode: 'submit'
          # The branch to create a PR from
          source-branch: 'develop'
          # The branch to merge the PR into
          target-branch: 'main'
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Repository Settings

For the action to have permission to create pull requests, you must configure your repository settings:
1.  Go to **Settings** > **Actions** > **General**.
2.  In the **Workflow permissions** section, select **"Read and write permissions"** and check the box for **"Allow GitHub Actions to create and approve pull requests"**.

---

## Workflow Steps

The action's behavior depends on the event that triggered it.

### On a `push` event with a new tag:

1.  **Detect Tag**: The action confirms the push event is for a new tag.
2.  **Fetch Latest Release**: It retrieves the version number of the latest release on the `target-branch`.
3.  **Validate Version**: The new tag is validated against the latest release version to ensure it's a valid semantic version increment.
4.  **Run Linting**: `library.properties` is checked and `arduino-lint` is run against the codebase.
5.  **Create Pull Request**: A new pull request is automatically created from the `source-branch` to the `target-branch`.
6.  **Merge Pull Request**: The newly created pull request is immediately merged.
7.  **Create Release**: A new GitHub release is drafted with the pushed tag.

### On a `pull_request` event:

1.  **Validate Version**: The action validates the version in `library.properties` against the version in the base branch.
2.  **Run Linting**: `library.properties` is checked and `arduino-lint` is run.
3.  **Merge and Release**: If all checks pass, the pull request is merged and a new release is created.

---

## License

This GitHub Action is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.