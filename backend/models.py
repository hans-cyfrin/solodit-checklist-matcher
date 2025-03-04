from sqlalchemy import Column, String, Text, TIMESTAMP, Integer, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from pgvector.sqlalchemy import Vector

Base = declarative_base()

class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id = Column(String, primary_key=True)  # e.g., "SOL-AM-DOSA-1"
    category = Column(String, nullable=False)
    question = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    remediation = Column(Text, nullable=False)
    references = Column(JSONB, nullable=False, default=list)  # Array of URLs
    embedding = Column(Vector(384), nullable=True)  # Stored embeddings using pgvector

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "question": self.question,
            "description": self.description,
            "remediation": self.remediation,
            "references": self.references
        }

class PendingChange(Base):
    __tablename__ = "pending_changes"

    change_id = Column(Integer, primary_key=True, autoincrement=True)
    checklist_item_id = Column(String, ForeignKey("checklist_items.id"), nullable=False)
    source_url = Column(String, nullable=False)  # Mandatory reference URL
    status = Column(String, default="pending")  # pending/approved/rejected
    created_at = Column(TIMESTAMP, default=func.now())

    def to_dict(self):
        return {
            "change_id": self.change_id,
            "checklist_item_id": self.checklist_item_id,
            "source_url": self.source_url,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }