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
    if not isinstance(pending_changes, list):
        logger.error(f"pending_changes must be a list, got {type(pending_changes)}")
        raise ValueError(f"pending_changes must be a list, got {type(pending_changes)}")

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

        # Get the original file content
        original_content = checklist_file.decoded_content.decode('utf-8')

        # Create a map of item IDs to their locations in the file
        import re

        # Function to find an item by ID in the original content
        def find_item_in_content(content, item_id):
            # Escape special characters in the ID for regex
            escaped_id = re.escape(item_id)
            # Look for the ID pattern in the content
            pattern = f'"id"\\s*:\\s*"{escaped_id}"'
            match = re.search(pattern, content)
            if not match:
                return None

            # Find the start of the item object (looking backwards for '{')
            start_pos = match.start()
            brace_count = 0
            item_start = None

            # Find the opening brace of the item
            for i in range(start_pos, -1, -1):
                if content[i] == '{':
                    brace_count += 1
                    if brace_count == 1:
                        item_start = i
                        break
                elif content[i] == '}':
                    brace_count -= 1

            if item_start is None:
                return None

            # Find the end of the item object (looking forward for '}')
            end_pos = match.end()
            brace_count = 0
            item_end = None

            # Find the closing brace of the item
            for i in range(end_pos, len(content)):
                if content[i] == '{':
                    brace_count += 1
                elif content[i] == '}':
                    brace_count -= 1
                    if brace_count == -1:  # We found the matching closing brace
                        item_end = i + 1
                        break

            if item_end is None:
                return None

            return {
                'start': item_start,
                'end': item_end,
                'content': content[item_start:item_end]
            }

        # Function to add a reference to an item
        def add_reference_to_item(item_content, url):
            # Check if the item already has references
            references_match = re.search(r'"references"\s*:\s*\[([^\]]*)\]', item_content)

            if references_match:
                # Item has references, check if the URL is already there
                references_content = references_match.group(1)
                if url in references_content:
                    return item_content  # URL already exists

                # Add the URL to the existing references
                if references_content.strip():
                    # There are existing references, add a comma and the new URL
                    new_references = references_content.rstrip() + ',\n    "' + url + '"\n  ]'
                else:
                    # Empty references array, just add the URL
                    new_references = '\n    "' + url + '"\n  ]'

                # Replace the old references with the new ones
                new_item_content = item_content.replace(
                    references_match.group(0),
                    f'"references": [{new_references}'
                )
                return new_item_content
            else:
                # Item doesn't have references, add them before the closing brace
                closing_brace_pos = item_content.rfind('}')
                if closing_brace_pos == -1:
                    return item_content  # Can't find closing brace

                # Add references field before the closing brace
                new_item_content = (
                    item_content[:closing_brace_pos] +
                    ',\n  "references": [\n    "' + url + '"\n  ]' +
                    item_content[closing_brace_pos:]
                )
                return new_item_content

        # Apply changes to the original content
        modified_content = original_content
        changes_applied = 0

        for change in pending_changes:
            item_id = change["checklist_item_id"]
            url = change["source_url"]

            # Find the item in the content
            item_location = find_item_in_content(modified_content, item_id)
            if item_location:
                # Add the reference to the item
                new_item_content = add_reference_to_item(item_location['content'], url)

                # Only update if the content changed
                if new_item_content != item_location['content']:
                    # Replace the old item with the new one
                    modified_content = (
                        modified_content[:item_location['start']] +
                        new_item_content +
                        modified_content[item_location['end']:]
                    )
                    changes_applied += 1
                    logger.info(f"Added reference {url} to item {item_id}")
            else:
                logger.warning(f"Could not find item {item_id} in the file content")

        if changes_applied == 0:
            logger.info("No changes applied to the file content")
            return {
                "pr_number": 0,
                "pr_url": "",
                "num_changes": 0
            }

        # Create commit
        num_changes = changes_applied
        item_ids = [change["checklist_item_id"] for change in pending_changes]
        item_id_str = item_ids[0] if len(item_ids) == 1 else f"multiple items ({', '.join(item_ids)})"
        commit_message = f"Add {num_changes} reference{'s' if num_changes > 1 else ''} to {item_id_str} via Solodit Checklist Matcher"
        logger.info(f"Commit message: {commit_message}")

        # Create or update file
        logger.info(f"Updating file checklist.json in branch {branch_name}")
        repo.update_file(
            path="checklist.json",
            message=commit_message,
            content=modified_content,
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