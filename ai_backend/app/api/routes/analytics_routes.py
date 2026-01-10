"""
API routes for analytics and predictions.
"""
import logging
from fastapi import APIRouter
from app.api.schemas.complaint import (
    PredictiveAnalysisRequest,
    PredictiveAnalysisResponse,
)
from app.agents.predictive_agent import get_predictive_agent

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics & Predictions"])


@router.post(
    "/predict",
    response_model=PredictiveAnalysisResponse,
    summary="Generate predictive analysis report",
    description="Analyze historical ticket data from the past 30 days and generate a predictive report for the next 30 days."
)
async def generate_predictive_report(request: PredictiveAnalysisRequest) -> PredictiveAnalysisResponse:
    """
    Generate a predictive civic issue analysis report.
    
    The API accepts:
    - tickets: List of historical tickets with ticket_number, category, severity, 
               department, ward_no, ward_name, created_at, resolved_at
    
    Returns:
    - report_html: HTML formatted predictive analysis report
    - generated_at: Report generation timestamp
    - error: Error message if analysis failed
    """
    logger.info("=" * 80)
    logger.info("API REQUEST - POST /api/v1/analytics/predict")
    logger.info("=" * 80)
    
    # Log request summary
    logger.info(f"Request Summary:")
    logger.info(f"  - Total tickets: {len(request.tickets)}")
    
    if request.tickets:
        # Count by category
        categories = {}
        wards = {}
        for ticket in request.tickets:
            cat = ticket.category
            categories[cat] = categories.get(cat, 0) + 1
            ward = ticket.ward_name
            wards[ward] = wards.get(ward, 0) + 1
        
        logger.info(f"  - Categories: {categories}")
        logger.info(f"  - Wards: {wards}")
    
    try:
        # Get predictive agent and generate report
        agent = get_predictive_agent()
        logger.info("Calling predictive analysis agent...")
        
        # Convert Pydantic models to dicts
        tickets_data = [ticket.model_dump() for ticket in request.tickets]
        
        result = await agent.generate_report(tickets_data)
        logger.info("Predictive analysis agent returned successfully")
        
        response = PredictiveAnalysisResponse(
            report_html=result["report_html"],
            generated_at=result["generated_at"],
            error=result["error"]
        )
        
        # Log response summary
        logger.info("API Response Summary:")
        logger.info(f"  - Report length: {len(response.report_html)} characters")
        logger.info(f"  - Generated at: {response.generated_at}")
        if response.error:
            logger.info(f"  - Error: {response.error}")
        
        logger.info("=" * 80)
        logger.info("API REQUEST - Completed successfully")
        logger.info("=" * 80)
        
        return response
        
    except Exception as e:
        logger.error(f"Exception during predictive analysis: {str(e)}", exc_info=True)
        logger.info("=" * 80)
        logger.info("API REQUEST - Failed with exception")
        logger.info("=" * 80)
        
        from datetime import datetime
        return PredictiveAnalysisResponse(
            report_html="",
            generated_at=datetime.now().isoformat(),
            error=f"Internal processing error: {str(e)}"
        )


@router.get(
    "/health",
    summary="Health check for the analytics service",
    description="Returns the health status of the analytics service."
)
async def health_check():
    """Health check endpoint for the analytics service."""
    logger.debug("Analytics health check endpoint called")
    return {"status": "healthy", "service": "predictive-analytics"}
