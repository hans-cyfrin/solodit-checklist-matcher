import os
import json
import httpx
from github import Github
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# GitHub configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO_OWNER = os.getenv("GITHUB_REPO_OWNER", "Cyfrin")
GITHUB_REPO_NAME = os.getenv("GITHUB_REPO_NAME", "audit-checklist")
GITHUB_PR_BRANCH = os.getenv("GITHUB_PR_BRANCH", "solodit-matcher-updates")

# GitHub API client
github_client = Github(GITHUB_TOKEN) if GITHUB_TOKEN else None

async def fetch_checklist_from_github():
    """
    Fetch the latest checklist from GitHub.

    Returns:
        list: List of checklist items
    """
    checklist_url = f"https://raw.githubusercontent.com/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/main/checklist.json"

    async with httpx.AsyncClient() as client:
        response = await client.get(checklist_url)
        response.raise_for_status()

        # Parse JSON response
        checklist_data = response.json()

        return checklist_data

def create_github_pr(updated_checklist, pending_changes):
    """
    Create a GitHub PR with updated checklist references.

    Args:
        updated_checklist (list): Updated checklist items
        pending_changes (list): List of pending changes

    Returns:
        dict: PR information
    """
    if not github_client:
        raise ValueError("GitHub token not configured")

    # Get repository
    repo = github_client.get_repo(f"{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}")

    # Get default branch
    default_branch = repo.default_branch

    # Create new branch from default branch
    try:
        # Check if branch exists
        repo.get_branch(GITHUB_PR_BRANCH)
        # If it exists, use a timestamp to create a unique branch name
        import time
        timestamp = int(time.time())
        branch_name = f"{GITHUB_PR_BRANCH}-{timestamp}"
    except:
        # Branch doesn't exist, use the configured name
        branch_name = GITHUB_PR_BRANCH

    # Get reference to default branch
    sb = repo.get_branch(default_branch)

    # Create new branch
    repo.create_git_ref(f"refs/heads/{branch_name}", sb.commit.sha)

    # Get checklist.json file
    checklist_file = repo.get_contents("checklist.json", ref=default_branch)

    # Update file content
    updated_content = json.dumps(updated_checklist, indent=2)

    # Create commit
    num_changes = len(pending_changes)
    commit_message = f"Add {num_changes} reference{'s' if num_changes > 1 else ''} via Solodit Matcher"

    # Create or update file
    repo.update_file(
        path="checklist.json",
        message=commit_message,
        content=updated_content,
        sha=checklist_file.sha,
        branch=branch_name
    )

    # Create PR
    pr_body = "This PR adds the following references to the checklist:\n\n"
    for change in pending_changes:
        pr_body += f"- Added {change['source_url']} to item {change['checklist_item_id']}\n"

    pr = repo.create_pull(
        title=commit_message,
        body=pr_body,
        head=branch_name,
        base=default_branch
    )

    return {
        "pr_number": pr.number,
        "pr_url": pr.html_url,
        "num_changes": num_changes
    }