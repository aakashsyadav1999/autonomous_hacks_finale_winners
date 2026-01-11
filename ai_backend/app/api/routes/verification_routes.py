"""
API routes for work verification.
"""
import logging
from fastapi import APIRouter
from app.api.schemas.complaint import (
    WorkVerificationRequest,
    WorkVerificationResponse,
)
from app.agents.verification_agent import get_verification_agent

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/verify", tags=["Work Verification"])


@router.post(
    "/completion",
    response_model=WorkVerificationResponse,
    summary="Verify work completion",
    description="Compare before and after images to determine if the contractor has completed the assigned work."
)
async def verify_work_completion(request: WorkVerificationRequest) -> WorkVerificationResponse:
    """
    Verify if the contractor has completed the assigned work.
    
    The API accepts:
    - before_image: Base64 encoded original complaint image
    - after_image: Base64 encoded contractor completion image
    - category: Category of the original complaint
    
    Returns:
    - is_completed: Boolean indicating if the work has been completed
    - error: Error message if verification failed
    """
    logger.info("=" * 80)
    logger.info("API REQUEST - POST /api/v1/verify/completion")
    logger.info("=" * 80)
    
    # Log request details
    before_size = len(request.before_image)
    after_size = len(request.after_image)
    logger.info(f"Request Details:")
    logger.info(f"  - Before image size: {before_size} characters (~{before_size * 3 / 4 / 1024:.2f} KB)")
    logger.info(f"  - After image size: {after_size} characters (~{after_size * 3 / 4 / 1024:.2f} KB)")
    logger.info(f"  - Category: {request.category}")
    
    try:
        # Get verification agent and verify completion
        agent = get_verification_agent()
        logger.info("Calling verification agent...")
        
        result = await agent.verify_completion(
            before_image=request.before_image,
            after_image=request.after_image,
            category=request.category
        )
        
        logger.info("Verification agent returned successfully")
        
        response = WorkVerificationResponse(
            is_completed=result["is_completed"],
            error=result["error"]
        )
        
        # Log response
        logger.info("API Response Summary:")
        logger.info(f"  - is_completed: {response.is_completed}")
        if response.error:
            logger.info(f"  - Error: {response.error}")
        
        logger.info("=" * 80)
        logger.info("API REQUEST - Completed successfully")
        logger.info("=" * 80)
        
        return response
        
    except Exception as e:
        logger.error(f"Exception during work verification: {str(e)}", exc_info=True)
        logger.info("=" * 80)
        logger.info("API REQUEST - Failed with exception")
        logger.info("=" * 80)
        
        return WorkVerificationResponse(
            is_completed=False,
            error=f"Internal processing error: {str(e)}"
        )


@router.get(
    "/health",
    summary="Health check for the verification service",
    description="Returns the health status of the verification service."
)
async def health_check():
    """Health check endpoint for the verification service."""
    logger.debug("Verification health check endpoint called")
    return {"status": "healthy", "service": "work-verification"}
