"""
Vision Analysis Agent for civic complaint image classification.
Uses Google Gemini 2.5 Flash for image analysis.
"""
import base64
import json
import logging
import re
from typing import Any, Dict, List, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.config.settings import get_settings
from app.api.schemas.complaint import (
    DetectedIssue,
    CategoryType,
    DepartmentType,
    SeverityLevel,
    CATEGORY_DEPARTMENT_MAP,
)

# Configure logger
logger = logging.getLogger(__name__)


# Vision Analysis Agent System Prompt
VISION_AGENT_SYSTEM_PROMPT = """You are an expert AI Vision Analyst specialized in identifying civic infrastructure issues from images. Your task is to analyze images and detect civic complaints that fall into specific categories.

## YOUR RESPONSIBILITIES:

1. **IMAGE QUALITY VALIDATION**: First, assess if the image is clear enough for analysis.
   - Reject images that are too blurry, too dark, or too overexposed to identify any objects
   - Reject images that are corrupted or unreadable

2. **CIVIC ISSUE DETECTION**: Identify if the image contains any of these 4 specific civic issues:
   - **Garbage/Waste accumulation**: Piles of garbage, litter, waste dumping, overflowing trash bins, scattered waste materials
   - **Manholes/drainage opening damage**: Broken manhole covers, missing manhole lids, damaged drainage openings, cracked or displaced covers, open manholes
   - **Water leakage**: Leaking water pipes, water main breaks, visible water flowing from infrastructure, wet patches from pipe leaks, burst pipes
   - **Drainage overflow**: Overflowing drains, clogged drainage causing water accumulation, sewage overflow, flooded drains, backed-up storm drains

3. **MULTI-ISSUE DETECTION**: An image may contain MULTIPLE issues. Identify ALL issues present.

4. **SEVERITY ASSESSMENT**: For each detected issue, assess severity based on:
   - **Low**: Minor issue, limited scope, not immediately hazardous (e.g., small amount of litter, minor water drip)
   - **Medium**: Moderate issue requiring attention, potential hazard if left unaddressed (e.g., moderate garbage pile, partial manhole damage)
   - **High**: Severe issue requiring urgent attention, immediate safety hazard (e.g., large garbage dump, completely open manhole, major water leak, significant sewage overflow)

## INVALID IMAGE CRITERIA:
Return is_valid=false if:
- Image is too blurry/low quality to analyze
- Image does not contain ANY of the 4 defined civic issue categories
- Image shows unrelated content (selfies, landscapes without issues, indoor scenes without issues, etc.)
- Image is corrupted or cannot be processed

## OUTPUT FORMAT:
You MUST respond with ONLY a valid JSON object in this exact format, no additional text:

For VALID images with detected issues:
```json
{
  "is_valid": true,
  "issues": [
    {
      "category": "<exact category name from the 4 options>",
      "severity": "<Low|Medium|High>",
      "reasoning": "<brief explanation of why this category and severity>"
    }
  ],
  "error": null
}
```

For INVALID images:
```json
{
  "is_valid": false,
  "issues": [],
  "error": "<specific reason why image is invalid>"
}
```

## CATEGORY NAMES (use exactly as written):
- "Garbage/Waste accumulation"
- "Manholes/drainage opening damage"
- "Water leakage"
- "Drainage overflow"

## SEVERITY LEVELS (use exactly as written):
- "Low"
- "Medium"
- "High"

IMPORTANT: 
- Respond with ONLY the JSON object, no markdown code blocks, no explanations before or after.
- Be precise and accurate in your categorization.
- If you detect multiple issues, include ALL of them in the issues array.
- Each issue should have its own independent severity assessment."""


class VisionAnalysisAgent:
    """Agent that analyzes civic complaint images using Gemini Vision."""
    
    def __init__(self):
        """Initialize the Vision Analysis Agent with Gemini model."""
        settings = get_settings()
        logger.info(f"Initializing VisionAnalysisAgent with model: {settings.MODEL_NAME}")
        self.model = ChatGoogleGenerativeAI(
            model=settings.MODEL_NAME,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.1,  # Low temperature for consistent categorization
        )
        logger.info("VisionAnalysisAgent initialized successfully")
    
    def _parse_base64_image(self, base64_string: str) -> Dict[str, Any]:
        """Parse base64 image string and prepare for Gemini API."""
        # Remove data URL prefix if present
        if "," in base64_string:
            base64_string = base64_string.split(",")[1]
            logger.debug("Removed data URL prefix from base64 image")
        
        # Calculate approximate image size
        image_size_bytes = len(base64_string) * 3 / 4
        logger.info(f"Processing image - Approximate size: {image_size_bytes / 1024:.2f} KB")
        
        # Detect image type from base64 or default to jpeg
        image_data = {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_string}"
            }
        }
        return image_data
    
    def _extract_json_from_response(self, response_text: str) -> Dict[str, Any]:
        """Extract JSON from model response, handling potential formatting issues."""
        text = response_text.strip()
        logger.debug(f"Raw model response (first 500 chars): {text[:500]}...")
        
        # Remove markdown code blocks if present
        if text.startswith("```json"):
            text = text[7:]
            logger.debug("Removed ```json prefix from response")
        elif text.startswith("```"):
            text = text[3:]
            logger.debug("Removed ``` prefix from response")
        
        if text.endswith("```"):
            text = text[:-3]
            logger.debug("Removed ``` suffix from response")
        
        text = text.strip()
        
        try:
            parsed = json.loads(text)
            logger.debug("Successfully parsed JSON from response")
            return parsed
        except json.JSONDecodeError as e:
            logger.warning(f"Initial JSON parse failed: {e}. Attempting regex extraction...")
            # Try to find JSON object in the response
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                try:
                    parsed = json.loads(json_match.group())
                    logger.debug("Successfully extracted JSON using regex")
                    return parsed
                except json.JSONDecodeError:
                    pass
            logger.error(f"Failed to parse JSON response: {e}")
            raise ValueError(f"Failed to parse JSON response: {e}")
    
    def _map_category_to_department(self, category: str) -> str:
        """Map category string to department string."""
        category_mapping = {
            "Garbage/Waste accumulation": DepartmentType.SANITATION.value,
            "Manholes/drainage opening damage": DepartmentType.ROADS_INFRASTRUCTURE.value,
            "Water leakage": DepartmentType.WATER_SUPPLY.value,
            "Drainage overflow": DepartmentType.DRAINAGE.value,
        }
        department = category_mapping.get(category, "Unknown Department")
        logger.debug(f"Mapped category '{category}' -> department '{department}'")
        return department
    
    async def analyze_image(self, base64_image: str) -> Dict[str, Any]:
        """
        Analyze a civic complaint image and return detected issues.
        
        Args:
            base64_image: Base64 encoded image string
            
        Returns:
            Dictionary with is_valid, data (list of issues), and error
        """
        logger.info("=" * 60)
        logger.info("VISION ANALYSIS AGENT - Starting image analysis")
        logger.info("=" * 60)
        
        try:
            # Prepare image for the model
            logger.info("Step 1: Parsing base64 image...")
            image_data = self._parse_base64_image(base64_image)
            logger.info("Step 1: Image parsed successfully")
            
            # Create messages for the model
            logger.info("Step 2: Creating messages for Gemini model...")
            messages = [
                SystemMessage(content=VISION_AGENT_SYSTEM_PROMPT),
                HumanMessage(
                    content=[
                        {"type": "text", "text": "Analyze this image for civic infrastructure issues."},
                        image_data
                    ]
                )
            ]
            logger.info("Step 2: Messages created successfully")
            
            # Invoke the model
            logger.info("Step 3: Invoking Gemini model for image analysis...")
            response = await self.model.ainvoke(messages)
            response_text = response.content
            logger.info("Step 3: Gemini model response received")
            logger.info(f"Raw Response from Gemini:\n{response_text}")
            
            # Parse the JSON response
            logger.info("Step 4: Parsing JSON response...")
            parsed_response = self._extract_json_from_response(response_text)
            logger.info(f"Step 4: Parsed response: {json.dumps(parsed_response, indent=2)}")
            
            # Format the response according to our API schema
            logger.info("Step 5: Formatting response...")
            if parsed_response.get("is_valid", False):
                issues = parsed_response.get("issues", [])
                logger.info(f"Image is VALID - Detected {len(issues)} issue(s)")
                
                detected_issues = []
                for idx, issue in enumerate(issues, 1):
                    category = issue.get("category", "")
                    department = self._map_category_to_department(category)
                    severity = issue.get("severity", "Medium")
                    reasoning = issue.get("reasoning", "N/A")
                    
                    logger.info(f"  Issue {idx}:")
                    logger.info(f"    - Category: {category}")
                    logger.info(f"    - Department: {department}")
                    logger.info(f"    - Severity: {severity}")
                    logger.info(f"    - Reasoning: {reasoning}")
                    
                    detected_issues.append({
                        "category": category,
                        "department": department,
                        "severity": severity
                    })
                
                result = {
                    "is_valid": True,
                    "data": detected_issues,
                    "error": None
                }
                logger.info(f"Step 5: Final response prepared - {len(detected_issues)} issue(s) detected")
                logger.info("=" * 60)
                logger.info("VISION ANALYSIS AGENT - Analysis completed successfully")
                logger.info("=" * 60)
                return result
            else:
                error_msg = parsed_response.get("error", "Image does not contain recognizable civic issues")
                logger.warning(f"Image is INVALID - Reason: {error_msg}")
                
                result = {
                    "is_valid": False,
                    "data": [],
                    "error": error_msg
                }
                logger.info("=" * 60)
                logger.info("VISION ANALYSIS AGENT - Analysis completed (invalid image)")
                logger.info("=" * 60)
                return result
                
        except ValueError as e:
            logger.error(f"ValueError during analysis: {str(e)}")
            logger.info("=" * 60)
            logger.info("VISION ANALYSIS AGENT - Analysis failed (parse error)")
            logger.info("=" * 60)
            return {
                "is_valid": False,
                "data": [],
                "error": f"Failed to parse model response: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Exception during analysis: {str(e)}", exc_info=True)
            logger.info("=" * 60)
            logger.info("VISION ANALYSIS AGENT - Analysis failed (exception)")
            logger.info("=" * 60)
            return {
                "is_valid": False,
                "data": [],
                "error": f"Image analysis failed: {str(e)}"
            }


# Singleton instance
_vision_agent: Optional[VisionAnalysisAgent] = None


def get_vision_agent() -> VisionAnalysisAgent:
    """Get or create singleton Vision Analysis Agent instance."""
    global _vision_agent
    if _vision_agent is None:
        logger.info("Creating new VisionAnalysisAgent instance")
        _vision_agent = VisionAnalysisAgent()
    return _vision_agent
