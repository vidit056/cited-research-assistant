from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.session import init_db
from app.routes.research import router as research_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    init_db()
    yield

app = FastAPI(
    title="Cited Research Assistant API",
    description="Agentic RAG System with Contradiction Detection & Self-Evaluation",
    version="1.1.0",
    lifespan=lifespan
)

# Enable CORS for local dev and UI integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research_router)

@app.get("/")
def root():
    return {
        "service": "Cited Research Assistant",
        "version": "1.1.0",
        "status": "online",
        "docs_url": "/docs"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}
