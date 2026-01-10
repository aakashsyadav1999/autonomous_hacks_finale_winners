"""
FastAPI Application - Smart Civic Complaint Management System AI Backend.
"""
import logging
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import get_settings
from app.api.routes import complaint_routes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Set log levels for different modules
logging.getLogger("app").setLevel(logging.INFO)
logging.getLogger("app.agents").setLevel(logging.INFO)
logging.getLogger("app.api").setLevel(logging.INFO)

# Reduce noise from third-party libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Initialize settings
settings = get_settings()

# Create FastAPI application
app = FastAPI(
    title="Smart Civic Complaint Management System - AI Backend",
    description="AI-powered image analysis for civic complaint categorization and routing",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    complaint_routes.router,
    prefix=settings.API_V1_PREFIX,
)

logger.info("=" * 80)
logger.info("SMART CIVIC COMPLAINT MANAGEMENT SYSTEM - AI BACKEND")
logger.info("=" * 80)
logger.info(f"API Version: 1.0.0")
logger.info(f"API Prefix: {settings.API_V1_PREFIX}")
logger.info(f"Model: {settings.MODEL_NAME}")
logger.info(f"Debug Mode: {settings.DEBUG}")
logger.info("=" * 80)


@app.on_event("startup")
async def startup_event():
    """Log application startup."""
    logger.info("Application startup complete - Ready to accept requests")


@app.on_event("shutdown")
async def shutdown_event():
    """Log application shutdown."""
    logger.info("Application shutting down...")


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    logger.debug("Root endpoint called")
    return {
        "message": "Smart Civic Complaint Management System - AI Backend",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Global health check endpoint."""
    logger.debug("Global health check endpoint called")
    return {
        "status": "healthy",
        "service": "ai-backend",
        "version": "1.0.0"
    }
