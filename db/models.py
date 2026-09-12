from datetime import datetime
import uuid
from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

def generate_uuid() -> str:
    return str(uuid.uuid4())

class Run(Base):
    __tablename__ = "runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    question = Column(Text, nullable=False)
    status = Column(String(50), default="pending", nullable=False)
    report_md = Column(Text, default="", nullable=False)
    sub_questions_json = Column(Text, default="[]", nullable=False)
    contradictions_json = Column(Text, default="[]", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    sources = relationship("Source", back_populates="run", cascade="all, delete-orphan")
    citations = relationship("Citation", back_populates="run", cascade="all, delete-orphan")
    eval_scores = relationship("EvalScore", back_populates="run", cascade="all, delete-orphan")

class Source(Base):
    __tablename__ = "sources"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    run_id = Column(String(36), ForeignKey("runs.id"), nullable=False, index=True)
    url = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    domain = Column(String(255), nullable=False)
    published_date = Column(String(100), nullable=True)
    raw_text = Column(Text, nullable=False)
    citation_num = Column(Integer, nullable=False)

    run = relationship("Run", back_populates="sources")
    citations = relationship("Citation", back_populates="source", cascade="all, delete-orphan")

class Citation(Base):
    __tablename__ = "citations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    run_id = Column(String(36), ForeignKey("runs.id"), nullable=False, index=True)
    source_id = Column(String(36), ForeignKey("sources.id"), nullable=False, index=True)
    quote = Column(Text, nullable=False)
    char_span = Column(String(100), default="", nullable=False)  # Stored as "start:end" or empty
    status = Column(String(50), default="verified", nullable=False)  # "verified" or "unverified"

    run = relationship("Run", back_populates="citations")
    source = relationship("Source", back_populates="citations")

class EvalScore(Base):
    __tablename__ = "eval_scores"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    run_id = Column(String(36), ForeignKey("runs.id"), nullable=False, index=True)
    faithfulness = Column(Float, nullable=False)
    citation_acc = Column(Float, nullable=False)
    retrieval_rel = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    run = relationship("Run", back_populates="eval_scores")

class CacheEntry(Base):
    __tablename__ = "cache_entries"

    key = Column(String(64), primary_key=True)  # SHA-256 hex digest
    provider = Column(String(50), nullable=False)  # "tavily" or "scrape"
    value = Column(Text, nullable=False)  # JSON string
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)
