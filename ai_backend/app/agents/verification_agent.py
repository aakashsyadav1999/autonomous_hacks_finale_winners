"""
Work Verification Agent for comparing before/after images.
Uses Google Gemini 2.5 Flash to verify if contractor completed the work.
"""
import json
import logging
import re
from typing import Any, Dict, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.config.settings import get_settings

# Configure logger
logger = logging.getLogger(__name__)


# Work Verification Agent System Prompt
VERIFICATION_AGENT_SYSTEM_PROMPT = """You are an expert AI Work Verification Analyst specialized in comparing before and after images of civic infrastructure issues to determine if the assigned work has been completed.

## YOUR TASK:

You will receive TWO images and a CATEGORY:
1. **BEFORE IMAGE**: The original complaint image showing the civic issue
2. **AFTER IMAGE**: The image taken by the contractor after completing the work
3. **CATEGORY**: The type of issue that was reported (e.g., "Garbage/Waste accumulation")

## YOUR RESPONSIBILITIES:

1. **Analyze the BEFORE image**: Identify the civic issue based on the provided category
2. **Analyze the AFTER image**: Check if the issue has been resolved
3. **Compare both images**: Determine if the work has been completed

## CATEGORY-SPECIFIC VERIFICATION CRITERIA:

### Garbage/Waste accumulation
- COMPLETED: Area is clean, garbage/waste has been removed, no visible litter or waste piles
- NOT COMPLETED: Garbage/waste is still visible, area is not clean

### Manholes/drainage opening damage
- COMPLETED: Manhole cover is properly installed, no damage visible, cover is secure and level
- NOT COMPLETED: Cover is still missing, damaged, cracked, or improperly placed

### Water leakage
- COMPLETED: No visible water leaking, pipes appear repaired, no wet patches from active leaks
- NOT COMPLETED: Water still leaking, wet patches visible, pipe damage still present

### Drainage overflow
- COMPLETED: Drainage is clear, no overflow, no water accumulation, drain is functioning
- NOT COMPLETED: Drainage still overflowing, water still accumulated, drain still blocked

## OUTPUT FORMAT:
You MUST respond with ONLY a valid JSON object in this exact format, no additional text:

If work is COMPLETED:
```json
{
  "is_completed": true,
  "error": null
}
```

If work is NOT COMPLETED:
```json
{
  "is_completed": false,
  "error": null
}
```

If there's an ERROR (e.g., cannot analyze images, images are unclear):
```json
{
  "is_completed": false,
  "error": "<specific error message>"
}
```

IMPORTANT:
- Respond with ONLY the JSON object, no markdown code blocks, no explanations.
- Focus on whether the SPECIFIC issue (category) has been resolved.
- If you cannot clearly determine completion, return is_completed: false."""


class WorkVerificationAgent:
    """Agent that verifies work completion by comparing before/after images."""
    
    def __init__(self):
        """Initialize the Work Verification Agent with Gemini model."""
        settings = get_settings()
        logger.info(f"Initializing WorkVerificationAgent with model: {settings.MODEL_NAME}")
        self.model = ChatGoogleGenerativeAI(
            model=settings.MODEL_NAME,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.1,
        )
        logger.info("WorkVerificationAgent initialized successfully")
    
    def _parse_base64_image(self, base64_string: str, image_label: str) -> Dict[str, Any]:
        """Parse base64 image string and prepare for Gemini API."""
        if "," in base64_string:
            base64_string = base64_string.split(",")[1]
            logger.debug(f"Removed data URL prefix from {image_label}")
        
        image_size_bytes = len(base64_string) * 3 / 4
        logger.info(f"Processing {image_label} - Approximate size: {image_size_bytes / 1024:.2f} KB")
        
        image_data = {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_string}"
            }
        }
        return image_data
    
    def _extract_json_from_response(self, response_text: str) -> Dict[str, Any]:
        """Extract JSON from model response."""
        text = response_text.strip()
        logger.debug(f"Raw model response (first 500 chars): {text[:500]}...")
        
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        
        if text.endswith("```"):
            text = text[:-3]
        
        text = text.strip()
        
        try:
            parsed = json.loads(text)
            logger.debug("Successfully parsed JSON from response")
            return parsed
        except json.JSONDecodeError as e:
            logger.warning(f"Initial JSON parse failed: {e}. Attempting regex extraction...")
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
    
    async def verify_completion(
        self, 
        before_image: str, 
        after_image: str, 
        category: str
    ) -> Dict[str, Any]:
        """
        Verify if work has been completed by comparing before/after images.
        
        Args:
            before_image: Base64 encoded original complaint image
            after_image: Base64 encoded contractor completion image
            category: Category of the original complaint
            
        Returns:
            Dictionary with is_completed and error fields
        """
        logger.info("=" * 60)
        logger.info("WORK VERIFICATION AGENT - Starting verification")
        logger.info("=" * 60)
        logger.info(f"Category to verify: {category}")
        
        try:
            # Parse both images
            logger.info("Step 1: Parsing before image...")
            before_image_data = self._parse_base64_image(before_image, "BEFORE image")
            
            logger.info("Step 2: Parsing after image...")
            after_image_data = self._parse_base64_image(after_image, "AFTER image")
            
            # Create messages for the model
            logger.info("Step 3: Creating messages for Gemini model...")
            messages = [
                SystemMessage(content=VERIFICATION_AGENT_SYSTEM_PROMPT),
                HumanMessage(
                    content=[
                        {"type": "text", "text": f"Compare these two images to verify if the work for category '{category}' has been completed.\n\nBEFORE IMAGE (original complaint):"},
                        before_image_data,
                        {"type": "text", "text": "\n\nAFTER IMAGE (contractor's completion photo):"},
                        after_image_data,
                        {"type": "text", "text": f"\n\nCategory: {category}\n\nDetermine if the {category} issue has been resolved."}
                    ]
                )
            ]
            
            # Invoke the model
            logger.info("Step 4: Invoking Gemini model for verification...")
            response = await self.model.ainvoke(messages)
            response_text = response.content
            logger.info("Step 4: Gemini model response received")
            logger.info(f"Raw Response from Gemini:\n{response_text}")
            
            # Parse the JSON response
            logger.info("Step 5: Parsing JSON response...")
            parsed_response = self._extract_json_from_response(response_text)
            logger.info(f"Step 5: Parsed response: {json.dumps(parsed_response, indent=2)}")
            
            is_completed = parsed_response.get("is_completed", False)
            error = parsed_response.get("error", None)
            
            logger.info(f"Verification Result: is_completed={is_completed}")
            if error:
                logger.info(f"Error: {error}")
            
            logger.info("=" * 60)
            logger.info("WORK VERIFICATION AGENT - Verification completed")
            logger.info("=" * 60)
            
            return {
                "is_completed": is_completed,
                "error": error
            }
            
        except ValueError as e:
            logger.error(f"ValueError during verification: {str(e)}")
            return {
                "is_completed": False,
                "error": f"Failed to parse model response: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Exception during verification: {str(e)}", exc_info=True)
            return {
                "is_completed": False,
                "error": f"Verification failed: {str(e)}"
            }


# Singleton instance
_verification_agent: Optional[WorkVerificationAgent] = None


def get_verification_agent() -> WorkVerificationAgent:
    """Get or create singleton Work Verification Agent instance."""
    global _verification_agent
    if _verification_agent is None:
        logger.info("Creating new WorkVerificationAgent instance")
        _verification_agent = WorkVerificationAgent()
    return _verification_agent
