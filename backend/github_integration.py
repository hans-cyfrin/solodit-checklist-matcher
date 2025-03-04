import os
import json
import httpx
from github import Github
from dotenv import load_dotenv
import logging

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
    logger = logging.getLogger(__name__)

    if not github_client:
        logger.error("GitHub token not configured")
        raise ValueError("GitHub token not configured")

    # Validate input data
    if not isinstance(updated_checklist, list):
        logger.error(f"updated_checklist must be a list, got {type(updated_checklist)}")
        raise ValueError(f"updated_checklist must be a list, got {type(updated_checklist)}")

    if not isinstance(pending_changes, list):
        logger.error(f"pending_changes must be a list, got {type(pending_changes)}")
        raise ValueError(f"pending_changes must be a list, got {type(pending_changes)}")

    # Skip validation of checklist items - they can be nested and top-level items might not have IDs

    # Validate each pending change has required fields
    for i, change in enumerate(pending_changes):
        if not isinstance(change, dict):
            logger.error(f"Pending change at index {i} is not a dictionary: {change}")
            raise ValueError(f"Pending change at index {i} is not a dictionary")

        if "checklist_item_id" not in change:
            logger.error(f"Pending change at index {i} is missing 'checklist_item_id' field: {change}")
            raise ValueError(f"Pending change at index {i} is missing 'checklist_item_id' field")

        if "source_url" not in change:
            logger.error(f"Pending change at index {i} is missing 'source_url' field: {change}")
            raise ValueError(f"Pending change at index {i} is missing 'source_url' field")

    try:
        # Get repository
        logger.info(f"Getting repository {GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}")
        repo = github_client.get_repo(f"{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}")

        # Get default branch
        default_branch = repo.default_branch
        logger.info(f"Default branch is {default_branch}")

        # Create new branch from default branch
        try:
            # Check if branch exists
            repo.get_branch(GITHUB_PR_BRANCH)
            # If it exists, use a timestamp to create a unique branch name
            import time
            timestamp = int(time.time())
            branch_name = f"{GITHUB_PR_BRANCH}-{timestamp}"
            logger.info(f"Branch {GITHUB_PR_BRANCH} exists, using {branch_name} instead")
        except:
            # Branch doesn't exist, use the configured name
            branch_name = GITHUB_PR_BRANCH
            logger.info(f"Using branch name {branch_name}")

        # Get reference to default branch
        sb = repo.get_branch(default_branch)
        logger.info(f"Got reference to default branch {default_branch}")

        # Create new branch
        logger.info(f"Creating new branch {branch_name} from {default_branch}")
        repo.create_git_ref(f"refs/heads/{branch_name}", sb.commit.sha)

        # Get checklist.json file
        logger.info("Getting checklist.json file")
        checklist_file = repo.get_contents("checklist.json", ref=default_branch)

        # Update file content
        logger.info("Preparing updated content")
        # Use ensure_ascii=False to preserve Unicode characters
        # Use indent=2 to maintain the same indentation style
        # Use separators with spaces after colons to match GitHub's formatting
        updated_content = json.dumps(
            updated_checklist,
            indent=2,
            ensure_ascii=False,
            separators=(',', ': ')
        )

        # Create commit
        num_changes = len(pending_changes)
        commit_message = f"Add {num_changes} reference{'s' if num_changes > 1 else ''} via Solodit Matcher"
        logger.info(f"Commit message: {commit_message}")

        # Create or update file
        logger.info(f"Updating file checklist.json in branch {branch_name}")
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

        logger.info(f"Creating PR from {branch_name} to {default_branch}")
        pr = repo.create_pull(
            title=commit_message,
            body=pr_body,
            head=branch_name,
            base=default_branch
        )
        logger.info(f"Created PR #{pr.number}: {pr.html_url}")

        return {
            "pr_number": pr.number,
            "pr_url": pr.html_url,
            "num_changes": num_changes
        }
    except Exception as e:
        logger.error(f"Error creating GitHub PR: {str(e)}", exc_info=True)
        raise