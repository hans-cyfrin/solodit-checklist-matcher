from logger_config import setup_logging

# Setup logging first, before any other operations
logger = setup_logging()

import os
import json
import datetime
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl
from dotenv import load_dotenv
from sqlalchemy.sql import text
from contextlib import asynccontextmanager

from database import get_db, init_db, init_engine
from models import ChecklistItem, PendingChange
from embeddings import generate_checklist_item_embedding, semantic_search
from github_integration import fetch_checklist_from_github, create_github_pr
from openrouter import chat_completion
from utils import clean_json_response
from prompts import PROMPTS


# Load environment variables first
load_dotenv(override=True)  # Explicitly override any existing env vars with .env file

# Environment Configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "local")  # 'local' or 'docker'
IS_DOCKER = ENVIRONMENT == "docker"

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/solodit_checklist" if not IS_DOCKER else "postgresql://postgres:postgres@postgres:5432/solodit_checklist"
)

# Configure CORS based on environment
DEFAULT_CORS = "http://localhost:3000" if not IS_DOCKER else "http://localhost"
CORS_ORIGINS = os.getenv("CORS_ORIGINS", DEFAULT_CORS).split(",")

# Initialize database
init_engine(DATABASE_URL)

# Pydantic models for API
class ChecklistItemBase(BaseModel):
    id: str
    category: str
    question: str
    description: str
    remediation: str
    references: List[str]
    score: Optional[float] = None

    class Config:
        from_attributes = True

class GeneratedCheckItem(BaseModel):
    question: str
    description: str
    remediation: str

class MatchResult(BaseModel):
    matches: List[ChecklistItemBase]
    input_text: str
    input_url: Optional[HttpUrl] = None
    generated_items: List[GeneratedCheckItem]
    filtered_items: List[GeneratedCheckItem]
    final_item: GeneratedCheckItem

    class Config:
        from_attributes = True

# Set Huggingface tokenizers parallelism to avoid warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Initialize OpenRouter client
# openrouter_client = create_openrouter_client()
# if not openrouter_client:
#     logger.error("Failed to initialize OpenRouter client. Please check your API key and configuration.")

# Initialize database on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database and sync checklist
    try:
        init_db()
        await sync_checklist()
    except Exception as e:
        print(f"Error during startup: {str(e)}")
        print("Application will continue without database initialization.")
        print("Please make sure the PostgreSQL database is running and accessible.")

    yield  # This is where FastAPI serves requests

    # Shutdown: cleanup resources if needed
    pass

# Create FastAPI app with lifespan
app = FastAPI(title="Solodit Checklist Matcher", lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    max_age=86400,  # 24 hours
)

# Pydantic models
class ChecklistItemModel(BaseModel):
    id: str
    category: str
    question: str
    description: str
    remediation: str
    references: List[str]

class PendingChangeModel(BaseModel):
    checklist_item_id: str
    source_url: HttpUrl

class MatchRequest(BaseModel):
    text: str
    url: Optional[HttpUrl] = None

class PRResponse(BaseModel):
    pr_number: int
    pr_url: str
    num_changes: int

# Endpoints
@app.get("/")
async def root():
    return {"message": "Solodit Checklist Matcher API"}

@app.get("/checklist", response_model=List[ChecklistItemModel])
async def get_checklist(db: Session = Depends(get_db)):
    items = db.query(ChecklistItem).all()
    return [item.to_dict() for item in items]

@app.post("/match")
async def match_text(request: Request, match_request: MatchRequest, db: Session = Depends(get_db)):
    if not match_request.text.strip():
        raise HTTPException(status_code=400, detail="Input text cannot be empty")

    try:
        # Step 1: Generate potential check items using AI
        generated_items = await generate_check_items(match_request.text)
        if not generated_items:
            logger.warning("Failed to generate items")
            raise HTTPException(status_code=500, detail="Failed to generate items")

        # Step 2: Cross-validate and filter items
        filtered_items = await validate_check_items(generated_items, match_request.text)
        if not filtered_items:
            logger.warning("Failed to validate items, using generated items")
            filtered_items = generated_items

        # Step 3: Choose and improve the best item
        final_item = await improve_check_item(filtered_items[0] if filtered_items else None, match_request.text)
        if not final_item:
            logger.warning("Failed to improve item, using first filtered item")
            final_item = filtered_items[0] if filtered_items else generated_items[0]

        # Step 4: Use the final item to find matches
        items = db.query(ChecklistItem).all()
        embeddings = [(item.id, item.embedding) for item in items if item.embedding is not None]

        if not embeddings:
            raise HTTPException(status_code=500, detail="No checklist items with embeddings found")

        # Create a combined text from the final item for matching
        search_text = f"{final_item.question} {final_item.description} {final_item.remediation}"
        matches = semantic_search(search_text, embeddings, top_k=10)

        # Get matched items
        matched_items = []
        for item_id, score in matches:
            item = db.query(ChecklistItem).filter(ChecklistItem.id == item_id).first()
            if item:
                item_dict = item.to_dict()
                item_dict["score"] = score
                matched_items.append(item_dict)

        # Prepare the response
        response_data = {
            "matches": matched_items,
            "input_text": match_request.text,
            "input_url": match_request.url,
            "generated_items": generated_items,
            "filtered_items": filtered_items,
            "final_item": final_item
        }

        return response_data
    except Exception as e:
        logger.error(f"Error in match_text: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error performing semantic search: {str(e)}")

@app.post("/propose-reference")
async def propose_reference(request: Request, changes: List[PendingChangeModel], db: Session = Depends(get_db)):
    # Validate input
    if not changes:
        raise HTTPException(status_code=400, detail="No changes provided")

    # Validate URL format (additional validation beyond Pydantic)
    for change in changes:
        if not change.source_url.startswith("https://"):
            raise HTTPException(status_code=400, detail="Only HTTPS URLs are allowed for security reasons")

    # Validate checklist item IDs
    for change in changes:
        item = db.query(ChecklistItem).filter(ChecklistItem.id == change.checklist_item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail=f"Checklist item {change.checklist_item_id} not found")

    try:
        # Create pending changes within a transaction
        created_changes = []
        for change in changes:
            # Check if this exact change already exists
            existing_change = db.query(PendingChange).filter(
                PendingChange.checklist_item_id == change.checklist_item_id,
                PendingChange.source_url == str(change.source_url),
                PendingChange.status == "pending"
            ).first()

            if existing_change:
                continue  # Skip duplicates

            pending_change = PendingChange(
                checklist_item_id=change.checklist_item_id,
                source_url=str(change.source_url)
            )
            db.add(pending_change)
            created_changes.append(pending_change)

        db.commit()

        # Refresh to get IDs
        for change in created_changes:
            db.refresh(change)

        return {
            "message": f"Created {len(created_changes)} pending changes",
            "changes": [change.to_dict() for change in created_changes]
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create pending changes: {str(e)}")

@app.get("/pending-changes")
async def get_pending_changes(db: Session = Depends(get_db)):
    changes = db.query(PendingChange).filter(PendingChange.status == "pending").all()
    return [change.to_dict() for change in changes]

@app.delete("/pending-changes/{change_id}")
async def delete_pending_change(change_id: int, db: Session = Depends(get_db)):
    """Delete a pending change by ID"""
    # Find the pending change
    change = db.query(PendingChange).filter(
        PendingChange.change_id == change_id,
        PendingChange.status == "pending"
    ).first()

    if not change:
        raise HTTPException(status_code=404, detail=f"Pending change with ID {change_id} not found")

    try:
        # Delete the change
        db.delete(change)
        db.commit()
        return {"message": f"Pending change {change_id} deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete pending change: {str(e)}")

@app.post("/create-pr", response_model=PRResponse)
async def create_pr(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Get pending changes
    pending_changes = db.query(PendingChange).filter(PendingChange.status == "pending").all()

    logger.info(f"Create PR request received with {len(pending_changes)} pending changes")

    if not pending_changes:
        logger.warning("No pending changes found when trying to create PR")
        raise HTTPException(status_code=400, detail="No pending changes found")

    try:
        # Get current checklist
        try:
            logger.info("Fetching checklist from GitHub")
            checklist_data = await fetch_checklist_from_github()
            logger.info(f"Successfully fetched checklist data")
        except Exception as e:
            logger.error(f"Failed to fetch checklist from GitHub: {str(e)}")
            raise HTTPException(status_code=503,
                detail=f"Failed to fetch checklist from GitHub: {str(e)}. Please check your network connection and GitHub API access.")

        # Extract all items from the nested structure
        all_items = []

        def extract_items(data, parent_category=""):
            if not isinstance(data, list):
                return

            for item in data:
                if not isinstance(item, dict):
                    continue

                # If this is a category with nested data
                if "data" in item and isinstance(item["data"], list):
                    category = item.get("category", parent_category)
                    extract_items(item["data"], category)

                # If this is an actual checklist item with an ID
                elif "id" in item:
                    # Add parent category if not present
                    if "category" not in item and parent_category:
                        item["category"] = parent_category
                    all_items.append(item)

        # Process the nested structure
        extract_items(checklist_data)
        logger.info(f"Extracted {len(all_items)} checklist items from the nested structure")

        # Create a map of item IDs to their locations in the nested structure
        item_map = {}

        def map_items(data, path=[]):
            if not isinstance(data, list):
                return

            for i, item in enumerate(data):
                if not isinstance(item, dict):
                    continue

                current_path = path + [i]

                # If this is a category with nested data
                if "data" in item and isinstance(item["data"], list):
                    map_items(item["data"], current_path + ["data"])

                # If this is an actual checklist item with an ID
                elif "id" in item:
                    item_map[item["id"]] = {
                        "path": current_path,
                        "item": item
                    }

        # Create the item map
        map_items(checklist_data)
        logger.info(f"Created map of {len(item_map)} checklist items")

        # Update references in checklist
        changes_applied = 0
        for change in pending_changes:
            logger.debug(f"Processing change for item {change.checklist_item_id}")

            # Find the item in the map
            if change.checklist_item_id in item_map:
                item = item_map[change.checklist_item_id]["item"]

                # Ensure references is a list
                if "references" not in item:
                    item["references"] = []

                # Add URL if not already present
                if change.source_url not in item["references"]:
                    item["references"].append(change.source_url)
                    changes_applied += 1
                    logger.info(f"Added reference {change.source_url} to item {change.checklist_item_id}")
            else:
                logger.warning(f"Checklist item {change.checklist_item_id} not found in GitHub data")

        logger.info(f"Applied {changes_applied} changes to checklist")

        if changes_applied == 0:
            # All changes were already applied, but we'll still update the status
            for change in pending_changes:
                change.status = "approved"
            db.commit()
            logger.info("No new changes to apply, updating status of pending changes to approved")

            return {
                "pr_number": 0,
                "pr_url": "",
                "num_changes": 0
            }

        # Create PR
        try:
            logger.info("Creating GitHub PR")

            # Convert pending changes to dict for PR creation
            pending_changes_dict = []
            for change in pending_changes:
                try:
                    change_dict = change.to_dict()
                    pending_changes_dict.append(change_dict)
                except Exception as e:
                    logger.error(f"Error converting change to dict: {str(e)}")

            logger.info(f"Sending checklist data with {len(pending_changes_dict)} changes to GitHub")

            # Don't log the entire checklist data
            pr_info = create_github_pr(
                updated_checklist=checklist_data,
                pending_changes=pending_changes_dict
            )
            logger.info(f"Successfully created PR: {pr_info}")

            # Update status of pending changes
            for change in pending_changes:
                change.status = "approved"

            db.commit()
            logger.info("Updated status of all pending changes to approved")

            return pr_info
        except Exception as e:
            error_message = str(e)
            logger.error(f"Failed to create PR: {error_message}", exc_info=True)

            if "token" in error_message.lower():
                error_message = "GitHub token is invalid or missing. Please check your configuration."
            elif "permission" in error_message.lower():
                error_message = "GitHub token doesn't have sufficient permissions to create a PR."

            raise HTTPException(status_code=500, detail=f"Failed to create PR: {error_message}")
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error creating PR: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error creating PR: {str(e)}")

@app.post("/resync")
async def resync_checklist(request: Request):
    """Resync checklist from GitHub"""
    try:
        background_tasks = BackgroundTasks()
        background_tasks.add_task(sync_checklist, force_resync=True)
        return {"message": "Checklist resync started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start resync: {str(e)}")

@app.get("/health")
async def health_check():
    """Check if the application is healthy"""
    health_status = {
        "status": "ok",
        "database": "unknown",
        "github_api": "unknown",
        "embeddings_model": "unknown",
        "version": "1.0.0",
        "timestamp": str(datetime.datetime.now())
    }

    # Check database connection
    try:
        db = next(get_db())
        # Check if we can execute a query
        db.execute(text("SELECT 1"))
        # Check if checklist items exist
        item_count = db.query(ChecklistItem).count()
        health_status["database"] = {
            "status": "connected",
            "checklist_items": item_count
        }
    except Exception as e:
        health_status["database"] = {
            "status": "disconnected",
            "error": str(e)
        }
        health_status["status"] = "degraded"

    # Check GitHub API
    try:
        if github_client:
            # Just check if we can access the API
            github_client.get_user().login
            health_status["github_api"] = "connected"
        else:
            health_status["github_api"] = "not_configured"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["github_api"] = {
            "status": "error",
            "error": str(e)
        }
        health_status["status"] = "degraded"

    # Check embeddings model
    try:
        from embeddings import get_model
        model = get_model()
        if model:
            health_status["embeddings_model"] = {
                "status": "loaded",
                "model": model.__class__.__name__
            }
        else:
            health_status["embeddings_model"] = "not_loaded"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["embeddings_model"] = {
            "status": "error",
            "error": str(e)
        }
        health_status["status"] = "degraded"

    return health_status

# Background task to sync checklist
async def sync_checklist(force_resync=True):
    """Sync checklist from GitHub and update database"""
    db = next(get_db())
    start_time = datetime.datetime.now()

    try:
        # Fetch checklist from GitHub
        try:
            checklist_data = await fetch_checklist_from_github()
            logger.debug(f"Fetched checklist data from GitHub at {datetime.datetime.now()}")
        except Exception as e:
            error_msg = f"Failed to fetch checklist from GitHub: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

        if force_resync:
            logger.debug("Force resync enabled - updating all checklist items")

        # Extract all checklist items from the nested structure
        all_items = []

        def extract_items(data, parent_category=""):
            if not isinstance(data, list):
                return

            for item in data:
                if not isinstance(item, dict):
                    continue

                # If this is a category with nested data
                if "data" in item and isinstance(item["data"], list):
                    category = item.get("category", parent_category)
                    extract_items(item["data"], category)

                # If this is an actual checklist item with an ID
                elif "id" in item:
                    # Add parent category if not present
                    if "category" not in item and parent_category:
                        item["category"] = parent_category
                    all_items.append(item)

        # Process the nested structure
        extract_items(checklist_data)
        logger.debug(f"Extracted {len(all_items)} checklist items from the nested structure")

        # Get all existing items in a single query for better performance
        existing_items = {item.id: item for item in db.query(ChecklistItem).all()}
        logger.debug(f"Found {len(existing_items)} existing items in database")

        # Determine which items need embedding generation
        items_to_update = []
        items_to_create = []
        items_needing_embeddings = []

        for item in all_items:
            try:
                item_id = item.get("id")
                if not item_id:
                    logger.warning(f"Item without ID found, skipping: {item}")
                    continue

                # Check if item exists
                existing_item = existing_items.get(item_id)

                if existing_item and not force_resync:
                    # Item exists and we're not forcing a resync, skip
                    continue
                elif existing_item:
                    # Item exists but we're forcing a resync, update it
                    logger.debug(f"Updating existing checklist item: {item_id}")
                    existing_item.category = item.get("category", "")
                    existing_item.question = item.get("question", "")
                    existing_item.description = item.get("description", "")
                    existing_item.remediation = item.get("remediation", "")
                    existing_item.references = item.get("references", [])

                    items_to_update.append((existing_item, item))
                    items_needing_embeddings.append(item)
                else:
                    # Create new item
                    logger.debug(f"Creating new checklist item: {item_id}")
                    new_item = ChecklistItem(
                        id=item_id,
                        category=item.get("category", ""),
                        question=item.get("question", ""),
                        description=item.get("description", ""),
                        remediation=item.get("remediation", ""),
                        references=item.get("references", [])
                    )

                    items_to_create.append((new_item, item))
                    items_needing_embeddings.append(item)
            except Exception as item_error:
                logger.error(f"Error processing item {item.get('id', 'unknown')}: {str(item_error)}")
                continue

        # Generate embeddings in batch if there are items needing embeddings
        if items_needing_embeddings:
            logger.debug(f"Generating embeddings for {len(items_needing_embeddings)} items in batch")

            # Prepare texts for batch embedding
            texts_to_embed = []
            for item in items_needing_embeddings:
                # Combine question and description for better semantic matching
                question = item.get('question', '')
                description = item.get('description', '')
                category = item.get('category', '')
                remediation = item.get('remediation', '')

                # Combine all fields with proper weighting
                combined_text = f"{question} {description} {remediation}"
                if category:
                    combined_text = f"{category}: {combined_text}"

                texts_to_embed.append(combined_text)

            # Generate embeddings in batch
            from embeddings import generate_embeddings_batch
            batch_embeddings = generate_embeddings_batch(texts_to_embed)

            # Create a mapping of item IDs to embeddings
            embedding_map = {}
            for i, item in enumerate(items_needing_embeddings):
                if i < len(batch_embeddings):  # Safety check
                    item_id = item.get('id')
                    if item_id:  # Only add if ID exists
                        embedding_map[item_id] = batch_embeddings[i]

            # Update existing items with embeddings
            for db_item, source_item in items_to_update:
                item_id = source_item.get('id')
                if item_id in embedding_map:
                    db_item.embedding = embedding_map[item_id]

            # Add embeddings to new items
            for db_item, source_item in items_to_create:
                item_id = source_item.get('id')
                if item_id in embedding_map:
                    db_item.embedding = embedding_map[item_id]

        # Commit changes in batches to avoid long transactions
        batch_size = 50

        # First commit all updates
        if items_to_update:
            db.commit()
            logger.info(f"Updated {len(items_to_update)} existing items")

        # Then add and commit new items in batches
        total_batches = (len(items_to_create) + batch_size - 1) // batch_size

        for i in range(0, len(items_to_create), batch_size):
            batch = items_to_create[i:i+batch_size]
            for db_item, _ in batch:
                db.add(db_item)
            db.commit()
            logger.info(f"Committed batch {i//batch_size + 1}/{total_batches} with {len(batch)} new items")

        end_time = datetime.datetime.now()
        duration = (end_time - start_time).total_seconds()

        logger.info(f"Checklist sync completed successfully in {duration:.2f} seconds")
        return {
            "message": "Checklist synced successfully",
            "stats": {
                "total_items": len(all_items),
                "new_items": len(items_to_create),
                "updated_items": len(items_to_update),
                "duration_seconds": duration
            }
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error syncing checklist: {str(e)}")
        return {"error": f"Failed to sync checklist: {str(e)}"}
    finally:
        db.close()

async def generate_check_items(text: str) -> List[GeneratedCheckItem]:
    """Generate search text using AI to better match against checklist items"""
    try:
        user_prompt = PROMPTS['generate'] + f"\n```\n{text}\n```"
        logger.info(f"Sending generate prompt:\n{user_prompt}")

        response = chat_completion(
            user_prompt,
            model="anthropic/claude-3.7-sonnet"
        )
        if not response:
            logger.error("Failed to get response from OpenRouter")
            return []

        logger.info(f"Received generate response:\n{response}")

        try:
            # Clean the response - remove any markdown code block markers
            cleaned_response = clean_json_response(response)
            cleaned_response = cleaned_response.replace('```json', '').replace('```', '').strip()
            logger.info(f"Cleaned response:\n{cleaned_response}")

            parsed_response = json.loads(cleaned_response)
            logger.info(f"Parsed response type: {type(parsed_response)}")
            logger.info(f"Parsed response content:\n{json.dumps(parsed_response, indent=2)}")

            # Handle both array and single object responses
            if isinstance(parsed_response, dict):
                items = [parsed_response]
            elif isinstance(parsed_response, list):
                items = parsed_response
            else:
                logger.error(f"Response is neither an object nor an array: {type(parsed_response)}")
                return []

            # Log the items before validation
            logger.info(f"Items before validation:\n{json.dumps(items, indent=2)}")

            result = [GeneratedCheckItem(**item) for item in items]
            logger.info(f"Successfully created {len(result)} GeneratedCheckItem objects")
            return result

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse response: {str(e)}")
            logger.error(f"Response that failed to parse: {response}")
            return []

    except Exception as e:
        logger.error(f"Error generating check items: {str(e)}")
        logger.exception("Full traceback:")
        return []

async def validate_check_items(items: List[GeneratedCheckItem], original_text: str) -> List[GeneratedCheckItem]:
    """Cross-validate generated items with another model"""
    try:
        items_json = json.dumps([item.dict() for item in items])
        user_prompt = f"{PROMPTS['validate']}\n\nItems: {items_json} \n\nFinding: {original_text}"
        logger.info(f"Sending validate prompt:\n{user_prompt}")

        response = chat_completion(
            user_prompt,
            model="anthropic/claude-3-sonnet-20240229"
        )
        if not response:
            logger.error("Failed to get response from OpenRouter")
            return items

        logger.info(f"Received validate response:\n{response}")

        try:
            cleaned_response = clean_json_response(response)
            cleaned_response = cleaned_response.replace('```json', '').replace('```', '').strip()
            logger.info(f"Cleaned validate response:\n{cleaned_response}")

            parsed_response = json.loads(cleaned_response)
            logger.info(f"Parsed validate response type: {type(parsed_response)}")
            logger.info(f"Parsed validate response content:\n{json.dumps(parsed_response, indent=2)}")

            # Handle both array and single object responses
            if isinstance(parsed_response, dict):
                validated_items = [parsed_response]
            elif isinstance(parsed_response, list):
                validated_items = parsed_response
            else:
                logger.error(f"Invalid response format: {type(parsed_response)}")
                return items

            # Log the items before validation
            logger.info(f"Validate items before validation:\n{json.dumps(validated_items, indent=2)}")

            result = [GeneratedCheckItem(**item) for item in validated_items]
            logger.info(f"Successfully created {len(result)} GeneratedCheckItem objects from validation")
            return result
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Error parsing OpenRouter response: {str(e)}")
            logger.error(f"Response that failed to parse: {response}")
            return items
    except Exception as e:
        logger.error(f"Error validating check items: {str(e)}")
        logger.exception("Full traceback:")
        return items

async def improve_check_item(item: Optional[GeneratedCheckItem], original_text: str) -> GeneratedCheckItem:
    """Improve the best candidate item"""
    try:
        if not item:
            # Generate a new item if none provided
            return (await generate_check_items(original_text))[0]

        user_prompt = f"{PROMPTS['improve']}\n\nItems: {json.dumps(item.dict())}"
        logger.info(f"Sending improve prompt:\n{user_prompt}")

        response = chat_completion(
            user_prompt,
            model="anthropic/claude-3-opus-20240229"
        )
        if not response:
            logger.error("Failed to get response from OpenRouter")
            return item

        logger.info(f"Received improve response:\n{response}")

        try:
            cleaned_response = clean_json_response(response)
            cleaned_response = cleaned_response.replace('```json', '').replace('```', '').strip()
            logger.info(f"Cleaned improve response:\n{cleaned_response}")

            parsed_response = json.loads(cleaned_response)
            logger.info(f"Parsed improve response type: {type(parsed_response)}")
            logger.info(f"Parsed improve response content:\n{json.dumps(parsed_response, indent=2)}")

            # Handle both object and array responses
            if isinstance(parsed_response, list) and len(parsed_response) > 0:
                improved_item = parsed_response[0]
            elif isinstance(parsed_response, dict):
                improved_item = parsed_response
            else:
                logger.error(f"Invalid response format: {type(parsed_response)}")
                return item

            # Log the item before validation
            logger.info(f"Improve item before validation:\n{json.dumps(improved_item, indent=2)}")

            result = GeneratedCheckItem(**improved_item)
            logger.info("Successfully created improved GeneratedCheckItem object")
            return result
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Error parsing OpenRouter response: {str(e)}")
            logger.error(f"Response that failed to parse: {response}")
            return item
    except Exception as e:
        logger.error(f"Error improving check item: {str(e)}")
        logger.exception("Full traceback:")
        return item

# Run the application
if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))

    uvicorn.run("main:app", host=host, port=port, reload=True)