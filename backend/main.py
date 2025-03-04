import os
import json
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl
from dotenv import load_dotenv
from sqlalchemy.sql import text

from database import get_db, init_db
from models import ChecklistItem, PendingChange
from embeddings import generate_checklist_item_embedding, semantic_search
from github_integration import fetch_checklist_from_github, create_github_pr

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(title="Solodit Checklist Matcher")

# Configure CORS
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    try:
        init_db()
        await sync_checklist()
    except Exception as e:
        print(f"Error during startup: {str(e)}")
        print("Application will continue without database initialization.")
        print("Please make sure the PostgreSQL database is running and accessible.")

# Endpoints
@app.get("/")
async def root():
    return {"message": "Solodit Checklist Matcher API"}

@app.get("/checklist", response_model=List[ChecklistItemModel])
async def get_checklist(db: Session = Depends(get_db)):
    items = db.query(ChecklistItem).all()
    return [item.to_dict() for item in items]

@app.post("/match")
async def match_text(request: MatchRequest, db: Session = Depends(get_db)):
    # Get all checklist items with embeddings
    items = db.query(ChecklistItem).all()
    embeddings = [(item.id, item.embedding) for item in items if item.embedding is not None]

    # Perform semantic search
    matches = semantic_search(request.text, embeddings, top_k=5)

    # Get matched items
    matched_items = []
    for item_id, score in matches:
        item = db.query(ChecklistItem).filter(ChecklistItem.id == item_id).first()
        if item:
            item_dict = item.to_dict()
            item_dict["score"] = score
            matched_items.append(item_dict)

    return {
        "matches": matched_items,
        "input_text": request.text,
        "input_url": request.url
    }

@app.post("/propose-reference")
async def propose_reference(changes: List[PendingChangeModel], db: Session = Depends(get_db)):
    # Validate checklist item IDs
    for change in changes:
        item = db.query(ChecklistItem).filter(ChecklistItem.id == change.checklist_item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail=f"Checklist item {change.checklist_item_id} not found")

    # Create pending changes
    created_changes = []
    for change in changes:
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

@app.get("/pending-changes")
async def get_pending_changes(db: Session = Depends(get_db)):
    changes = db.query(PendingChange).filter(PendingChange.status == "pending").all()
    return [change.to_dict() for change in changes]

@app.post("/create-pr", response_model=PRResponse)
async def create_pr(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Get pending changes
    pending_changes = db.query(PendingChange).filter(PendingChange.status == "pending").all()

    if not pending_changes:
        raise HTTPException(status_code=400, detail="No pending changes found")

    # Get current checklist
    checklist_data = await fetch_checklist_from_github()

    # Update references in checklist
    for change in pending_changes:
        for item in checklist_data:
            if item["id"] == change.checklist_item_id:
                # Ensure references is a list
                if "references" not in item:
                    item["references"] = []

                # Add URL if not already present
                if change.source_url not in item["references"]:
                    item["references"].append(change.source_url)

    # Create PR
    try:
        pr_info = create_github_pr(
            updated_checklist=checklist_data,
            pending_changes=[change.to_dict() for change in pending_changes]
        )

        # Update status of pending changes
        for change in pending_changes:
            change.status = "approved"

        db.commit()

        return pr_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create PR: {str(e)}")

@app.post("/resync")
async def resync_checklist():
    """Resync checklist from GitHub"""
    background_tasks = BackgroundTasks()
    background_tasks.add_task(sync_checklist)
    return {"message": "Checklist resync started"}

@app.get("/health")
async def health_check():
    """Check if the application is healthy"""
    try:
        # Try to connect to the database
        db = next(get_db())
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"disconnected: {str(e)}"

    return {
        "status": "ok",
        "database": db_status
    }

# Background task to sync checklist
async def sync_checklist():
    """Sync checklist from GitHub and update database"""
    db = next(get_db())

    try:
        # Fetch checklist from GitHub
        checklist_data = await fetch_checklist_from_github()

        # Process each item
        for item in checklist_data:
            # Check if item exists
            existing_item = db.query(ChecklistItem).filter(ChecklistItem.id == item["id"]).first()

            if existing_item:
                # Item exists, skip
                continue

            # Create new item
            new_item = ChecklistItem(
                id=item["id"],
                category=item.get("category", ""),
                question=item.get("question", ""),
                description=item.get("description", ""),
                remediation=item.get("remediation", ""),
                references=item.get("references", [])
            )

            # Generate embedding
            embedding = generate_checklist_item_embedding(item)
            new_item.embedding = embedding

            # Add to database
            db.add(new_item)

        # Commit changes
        db.commit()

        return {"message": "Checklist synced successfully"}
    except Exception as e:
        db.rollback()
        print(f"Error syncing checklist: {str(e)}")
        return {"error": f"Failed to sync checklist: {str(e)}"}
    finally:
        db.close()

# Run the application
if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))

    uvicorn.run("main:app", host=host, port=port, reload=True)