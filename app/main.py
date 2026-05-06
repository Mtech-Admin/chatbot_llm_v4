"""
FastAPI Application - Main entry point
"""

import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.gateway.router import router as chat_router
from app.gateway.v1_chat_router import router as v1_chat_router
from app.gateway.session import session_manager
from app.knowledge.store import policy_store
from app.tools.hrms_client import hrms_client

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Third-party HTTP debug logs are very verbose and add avoidable overhead in production.
if not settings.DEBUG:
    logging.getLogger("httpx").setLevel(logging.INFO)
    logging.getLogger("httpcore").setLevel(logging.INFO)
    logging.getLogger("openai").setLevel(logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager - startup and shutdown"""
    
    # Startup
    logger.info("Starting up DMRC HRMS Chatbot...")
    await session_manager.init()
    policy_store.init_schema()
    logger.info("Redis connection initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down DMRC HRMS Chatbot...")
    await session_manager.close()
    await hrms_client.aclose()
    logger.info("Redis connection closed")

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    debug=settings.DEBUG
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router)
app.include_router(v1_chat_router)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "endpoints": {
            "chat": "/api/chat/message",
            "history": "/v1/chat/history",
            "health": "/api/chat/health",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.DEBUG
    )
