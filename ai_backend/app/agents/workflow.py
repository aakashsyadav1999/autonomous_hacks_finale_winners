"""
LangGraph workflow for civic complaint analysis.
Orchestrates the Vision Analysis Agent for image processing.
"""
import logging
from typing import TypedDict, Optional, List, Dict, Any
from langgraph.graph import StateGraph, END

from app.agents.vision_agent import get_vision_agent

# Configure logger
logger = logging.getLogger(__name__)


class ComplaintState(TypedDict):
    """State schema for the complaint analysis workflow."""
    # Input
    base64_image: str
    
    # Output
    is_valid: bool
    data: List[Dict[str, Any]]
    error: Optional[str]
    
    # Processing flags
    processed: bool


async def vision_analysis_node(state: ComplaintState) -> ComplaintState:
    """
    Vision Analysis Node - Analyzes the image for civic issues.
    
    This node:
    1. Takes the base64 encoded image from state
    2. Invokes the Vision Analysis Agent
    3. Returns the analysis results
    """
    logger.info("-" * 60)
    logger.info("WORKFLOW NODE: vision_analysis - Starting")
    logger.info("-" * 60)
    
    agent = get_vision_agent()
    logger.info("Retrieved VisionAnalysisAgent instance")
    
    # Log image info (size without exposing content)
    image_preview_len = min(50, len(state["base64_image"]))
    logger.debug(f"Image preview (first {image_preview_len} chars): {state['base64_image'][:image_preview_len]}...")
    
    # Analyze the image
    logger.info("Calling agent.analyze_image()...")
    result = await agent.analyze_image(state["base64_image"])
    logger.info(f"Agent returned: is_valid={result['is_valid']}, issues_count={len(result['data'])}")
    
    # Update state with results
    updated_state = {
        **state,
        "is_valid": result["is_valid"],
        "data": result["data"],
        "error": result["error"],
        "processed": True
    }
    
    logger.info("-" * 60)
    logger.info("WORKFLOW NODE: vision_analysis - Completed")
    logger.info("-" * 60)
    
    return updated_state


def create_complaint_workflow() -> StateGraph:
    """
    Create and compile the LangGraph workflow for complaint analysis.
    
    Workflow Structure:
    START -> Vision Analysis Node -> END
    
    Returns:
        Compiled StateGraph workflow
    """
    logger.info("Creating complaint analysis workflow...")
    
    # Create the workflow graph
    workflow = StateGraph(ComplaintState)
    
    # Add the vision analysis node
    workflow.add_node("vision_analysis", vision_analysis_node)
    logger.debug("Added 'vision_analysis' node to workflow")
    
    # Set entry point
    workflow.set_entry_point("vision_analysis")
    logger.debug("Set 'vision_analysis' as entry point")
    
    # Add edge to END
    workflow.add_edge("vision_analysis", END)
    logger.debug("Added edge from 'vision_analysis' to END")
    
    # Compile and return
    compiled = workflow.compile()
    logger.info("Complaint analysis workflow compiled successfully")
    
    return compiled


# Create singleton workflow instance
_workflow = None


def get_complaint_workflow():
    """Get or create the singleton complaint workflow instance."""
    global _workflow
    if _workflow is None:
        logger.info("Creating new complaint workflow instance")
        _workflow = create_complaint_workflow()
    return _workflow


async def analyze_complaint_image(base64_image: str) -> Dict[str, Any]:
    """
    Main entry point for analyzing a complaint image.
    
    Args:
        base64_image: Base64 encoded image string
        
    Returns:
        Dictionary with is_valid, data, and error fields
    """
    logger.info("=" * 70)
    logger.info("LANGGRAPH WORKFLOW - Starting complaint image analysis")
    logger.info("=" * 70)
    
    workflow = get_complaint_workflow()
    logger.info("Retrieved workflow instance")
    
    # Initialize state
    initial_state: ComplaintState = {
        "base64_image": base64_image,
        "is_valid": False,
        "data": [],
        "error": None,
        "processed": False
    }
    logger.info("Initialized workflow state")
    logger.debug(f"Initial state: is_valid={initial_state['is_valid']}, processed={initial_state['processed']}")
    
    # Run the workflow
    logger.info("Invoking workflow...")
    final_state = await workflow.ainvoke(initial_state)
    logger.info("Workflow execution completed")
    
    # Prepare response
    response = {
        "is_valid": final_state["is_valid"],
        "data": final_state["data"],
        "error": final_state["error"]
    }
    
    logger.info(f"Final Result: is_valid={response['is_valid']}, issues_count={len(response['data'])}, error={response['error']}")
    logger.info("=" * 70)
    logger.info("LANGGRAPH WORKFLOW - Completed")
    logger.info("=" * 70)
    
    return response
