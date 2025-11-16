import os
import requests
import semver
import sys
import re
from pathlib import Path
import subprocess

# --- Get Inputs ---
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
LINT_MODE = os.getenv('INPUT_LINT-MODE')
SOURCE_BRANCH = os.getenv('INPUT_SOURCE-BRANCH')
TARGET_BRANCH = os.getenv('INPUT_TARGET-BRANCH')

GITHUB_EVENT_NAME = os.getenv('GITHUB_EVENT_NAME')
GITHUB_REPOSITORY = os.getenv('GITHUB_REPOSITORY')
GITHUB_REF = os.getenv('GITHUB_REF')

# --- API Configuration ---
GITHUB_API_URL = f'https://api.github.com/repos/{GITHUB_REPOSITORY}'
HEADERS = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json',
}

# --- Validation Functions ---

def validate_library_metadata():
    if not Path("library.properties").exists():
        print("Error: library.properties file is missing.")
        sys.exit(1)
    print("library.properties found.")

def validate_code_style():
    try:
        result = subprocess.run(
            ["arduino-lint", "--library-manager", LINT_MODE],
            capture_output=True, text=True, check=True
        )
        print("Code style validation passed.")
        if result.stdout:
            print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("Error: Code style validation failed.")
        if e.stdout:
            print(f"stdout:\n{e.stdout}")
        if e.stderr:
            print(f"stderr:\n{e.stderr}")
        sys.exit(1)

def validate_version(new_version, old_version):
    try:
        new_v = semver.VersionInfo.parse(new_version.lstrip('v'))
        old_v = semver.VersionInfo.parse(old_version.lstrip('v'))
    except ValueError as e:
        print(f"Error: Invalid semantic version. {e}")
        sys.exit(1)

    if new_v.prerelease is not None:
        print(f"Warning: New version '{new_version}' is a pre-release.")

    if new_v <= old_v:
        print(f"Error: New version '{new_version}' is not greater than old version '{old_version}'.")
        sys.exit(1)
    
    print(f"Version validation passed: {old_version} -> {new_version}")

# --- GitHub API Functions ---

def get_latest_release_version():
    """Fetches the latest release version from the target branch."""
    url = f"{GITHUB_API_URL}/releases/latest"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 404:
        print("No releases found. Assuming initial version 0.0.0.")
        return "0.0.0"
    response.raise_for_status()
    return response.json()['tag_name']

def create_pr(new_version):
    """Creates a pull request from the source branch to the target branch."""
    url = f"{GITHUB_API_URL}/pulls"
    data = {
        'title': f'Release: {new_version}',
        'head': SOURCE_BRANCH,
        'base': TARGET_BRANCH,
        'body': f'Automated release for version {new_version}.',
    }
    response = requests.post(url, headers=HEADERS, json=data)
    if response.status_code == 201:
        pr = response.json()
        print(f"Successfully created PR #{pr['number']}.")
        return pr['number']
    else:
        print(f"Error creating PR: {response.status_code} {response.text}")
        # Check if PR already exists
        if "A pull request already exists" in response.text:
            print("A PR already exists for this branch. Attempting to find and merge it.")
            # This part is complex, for now we exit. A more robust solution would find the existing PR.
            sys.exit(0) 
        sys.exit(1)

def merge_pr(pr_number):
    """Merges the specified pull request."""
    url = f"{GITHUB_API_URL}/pulls/{pr_number}/merge"
    data = {'merge_method': 'squash'}
    response = requests.put(url, headers=HEADERS, json=data)
    if response.status_code == 200:
        print(f"Successfully merged PR #{pr_number}.")
    else:
        print(f"Error merging PR #{pr_number}: {response.status_code} {response.text}")
        sys.exit(1)

def create_release(version):
    """Creates a new GitHub release."""
    url = f"{GITHUB_API_URL}/releases"
    tag = f"v{version.lstrip('v')}"
    data = {
        'tag_name': tag,
        'name': f'Release {tag}',
        'body': f'Automated release for version {tag}.',
        'draft': False,
        'prerelease': semver.VersionInfo.parse(version.lstrip('v')).prerelease is not None,
    }
    response = requests.post(url, headers=HEADERS, json=data)
    if response.status_code == 201:
        print(f"Successfully created release {tag}.")
    else:
        print(f"Error creating release: {response.status_code} {response.text}")
        sys.exit(1)

# --- Workflow Handlers ---

def handle_pull_request():
    """Handles the workflow when triggered by a pull request."""
    print("-- Handling Pull Request --")
    pr_version = os.getenv('pr_version')
    main_version = os.getenv('main_version')
    pr_number = os.getenv('PR_NUMBER')

    if not all([pr_version, main_version, pr_number]):
        print("Error: Missing pr_version, main_version, or PR_NUMBER env variables.")
        sys.exit(1)

    validate_version(pr_version, main_version)
    validate_library_metadata()
    validate_code_style()
    
    merge_pr(pr_number)
    create_release(pr_version)
    print("-- Pull Request Handled Successfully --")

def handle_tag_push():
    """Handles the workflow when triggered by a tag push."""
    print("-- Handling Tag Push --")
    if not GITHUB_REF or not GITHUB_REF.startswith('refs/tags/'):
        print("This push is not a tag push. Skipping.")
        return

    new_tag = GITHUB_REF.replace('refs/tags/', '')
    print(f"Detected new tag: {new_tag}")

    latest_version = get_latest_release_version()
    print(f"Latest release version on '{TARGET_BRANCH}' is '{latest_version}'.")

    validate_version(new_tag, latest_version)
    validate_library_metadata()
    validate_code_style()

    print(f"Creating PR from '{SOURCE_BRANCH}' to '{TARGET_BRANCH}'...")
    pr_number = create_pr(new_tag)
    
    merge_pr(pr_number)
    create_release(new_tag)
    print("-- Tag Push Handled Successfully --")

# --- Main Function ---

def main():
    if GITHUB_EVENT_NAME == 'pull_request':
        handle_pull_request()
    elif GITHUB_EVENT_NAME == 'push':
        handle_tag_push()
    else:
        print(f"Warning: Unsupported event type '{GITHUB_EVENT_NAME}'. Skipping.")

if __name__ == "__main__":
    main()