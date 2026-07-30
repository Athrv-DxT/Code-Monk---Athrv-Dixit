import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.graph.neo4j_client import init_db
from app.config import settings
from app.core.logging_setup import setup_logging

# Configure logging
logger = setup_logging()

app = FastAPI(
    title="Project Meridian API",
    description="Enterprise-grade document simplification and semantic representation pipeline.",
    version="1.0.0"
)

# Set CORS origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, lock this down to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router)

@app.on_event("startup")
def on_startup():
    logger.info("Project Meridian API booting up...")
    # Initialize Neo4j constraints
    init_db()

@app.get("/")
def read_root():
    return {
        "name": "Project Meridian API",
        "status": "online",
        "description": "Auditable document adaptation and semantic representation pipeline."
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
