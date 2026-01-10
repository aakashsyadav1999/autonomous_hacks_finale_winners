"""
API routes for complaint analysis.
"""
import logging
from fastapi import APIRouter, HTTPException
from app.api.schemas.complaint import (
    ComplaintAnalysisRequest,
    ComplaintAnalysisResponseWithWard,
    DetectedIssue,
)
from app.agents.workflow import analyze_complaint_image
from app.services.ward_mapper import get_ward_mapper

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyze", tags=["Complaint Analysis"])


@router.post(
    "/complaint",
    response_model=ComplaintAnalysisResponseWithWard,
    summary="Analyze a civic complaint image",
    description="Upload a Base64 encoded image of a civic issue to get automatic categorization, department assignment, severity assessment, and ward mapping."
)
async def analyze_complaint(request: ComplaintAnalysisRequest) -> ComplaintAnalysisResponseWithWard:
    """
    Analyze a civic complaint image and return detected issues with ward info.
    
    The API accepts:
    - image: Base64 encoded image of the civic issue
    - street: Street name of the location
    - area: Area/locality name
    - postal_code: Postal/ZIP code
    - latitude: GPS latitude
    - longitude: GPS longitude
    
    Returns:
    - is_valid: Boolean indicating if valid civic issues were detected
    - data: List of detected issues with category, department, severity, tools, and safety
    - ward_info: Ward information based on GPS coordinates
    - error: Error message if image is invalid or processing failed
    """
    logger.info("=" * 80)
    logger.info("API REQUEST - POST /api/v1/analyze/complaint")
    logger.info("=" * 80)
    
    # Log request details (without full image content)
    image_size = len(request.image)
    logger.info(f"Request Details:")
    logger.info(f"  - Image size: {image_size} characters (~{image_size * 3 / 4 / 1024:.2f} KB)")
    logger.info(f"  - Street: {request.street}")
    logger.info(f"  - Area: {request.area}")
    logger.info(f"  - Postal Code: {request.postal_code}")
    logger.info(f"  - Coordinates: ({request.latitude}, {request.longitude})")
    
    try:
        # Analyze the image using LangGraph workflow
        logger.info("Calling analyze_complaint_image workflow...")
        result = await analyze_complaint_image(request.image)
        logger.info("Workflow returned successfully")
        
        # Convert to response model
        detected_issues = [
            DetectedIssue(
                category=issue["category"],
                department=issue["department"],
                severity=issue["severity"],
                suggested_tools=issue.get("suggested_tools", []),
                safety_equipment=issue.get("safety_equipment", [])
            )
            for issue in result["data"]
        ]
        
        # Map coordinates to ward (only if image is valid)
        ward_no = None
        if result["is_valid"]:
            logger.info("Mapping coordinates to ward...")
            try:
                ward_mapper = get_ward_mapper()
                ward_data = ward_mapper.find_ward(request.latitude, request.longitude)
                
                if ward_data:
                    ward_no = ward_data["ward_no"]
                    logger.info(f"Ward found: No. {ward_no}")
                else:
                    logger.warning("No ward found for the given coordinates")
            except Exception as e:
                logger.error(f"Ward mapping failed: {str(e)}")
                # Continue without ward info - don't fail the whole request
        
        response = ComplaintAnalysisResponseWithWard(
            is_valid=result["is_valid"],
            data=detected_issues,
            ward_no=ward_no,
            error=result["error"]
        )
        
        # Log response summary
        logger.info("API Response Summary:")
        logger.info(f"  - is_valid: {response.is_valid}")
        logger.info(f"  - Issues detected: {len(response.data)}")
        for idx, issue in enumerate(response.data, 1):
            logger.info(f"    Issue {idx}: {issue.category} -> {issue.department} (Severity: {issue.severity})")
        if response.ward_no:
            logger.info(f"  - Ward No: {response.ward_no}")
        if response.error:
            logger.info(f"  - Error: {response.error}")
        
        logger.info("=" * 80)
        logger.info("API REQUEST - Completed successfully")
        logger.info("=" * 80)
        
        return response
        
    except Exception as e:
        logger.error(f"Exception during complaint analysis: {str(e)}", exc_info=True)
        logger.info("=" * 80)
        logger.info("API REQUEST - Failed with exception")
        logger.info("=" * 80)
        
        # Return error in the expected format
        return ComplaintAnalysisResponseWithWard(
            is_valid=False,
            data=[],
            ward_info=None,
            error=f"Internal processing error: {str(e)}"
        )


@router.get(
    "/health",
    summary="Health check for the analysis service",
    description="Returns the health status of the analysis service."
)
async def health_check():
    """Health check endpoint for the analysis service."""
    logger.debug("Health check endpoint called")
    return {"status": "healthy", "service": "complaint-analysis"}
