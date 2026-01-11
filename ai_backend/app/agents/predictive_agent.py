"""
Predictive Analysis Agent for generating civic issue prediction reports.
Uses Google Gemini to analyze historical data and predict future issues.
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
import re
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.config.settings import get_settings

# Configure logger
logger = logging.getLogger(__name__)


# Predictive Analysis Agent System Prompt
PREDICTIVE_AGENT_SYSTEM_PROMPT = """You are an expert AI Urban Infrastructure Analyst and Predictive Risk Specialist who analyzes civic complaint data to identify hidden patterns, predict major infrastructure failures, and provide preventive recommendations.

## YOUR MISSION:

Analyze historical ticket data and identify NOT JUST surface-level patterns, but HIDDEN INSIGHTS that could indicate MAJOR FUTURE ISSUES. Your goal is to predict problems BEFORE they become critical emergencies.

## DATA PROVIDED:

Each ticket contains:
- ticket_number: Unique identifier
- category: Issue type (Garbage/Waste accumulation, Manholes/drainage damage, Water leakage, Drainage overflow)
- severity: Low, Medium, or High
- department: Responsible department
- ward_no: Ward number
- ward_name: Ward name
- created_at: When the complaint was filed
- resolved_at: When it was resolved (null if pending)

## CRITICAL ANALYSIS REQUIREMENTS:

### 1. ISSUE ESCALATION PATTERN DETECTION
Look for patterns where minor issues escalate to major problems:
- **Drainage Chain Reaction**: Multiple manhole/drainage complaints in the same ward → likely to cause drainage line burst, sewage overflow, or road collapse
- **Water Infrastructure Decay**: Repeated water leakage in same area → pipe network degradation, potential main line burst
- **Garbage Accumulation Cycles**: Recurring garbage complaints → pest infestation, health hazards, drainage blockages
- **Manhole Deterioration**: Multiple manhole damages → underground infrastructure failure risk

### 2. ROOT CAUSE ANALYSIS
For each high-frequency issue, identify potential ROOT CAUSES:
- Is the same ward reporting similar issues repeatedly? → Systemic infrastructure failure
- Are different issue types clustering in one area? → Underlying infrastructure problem
- Are resolution times increasing for certain areas? → Resource or infrastructure inadequacy

### 3. PREDICTIVE CHAIN REACTIONS
Predict what BIGGER problems could arise from current patterns:
- Manhole damage + Drainage overflow in same ward → HIGH RISK of road cave-in or sewer line collapse
- Multiple water leakages in adjacent areas → Main water pipeline failure risk
- Garbage + Drainage issues → Drainage blockage and flooding during monsoon
- High severity issues with long resolution times → Public safety emergency risk

### 4. SEASONAL/CLIMATE CORRELATION
Consider how issues might worsen in upcoming seasons:
- Pre-monsoon: drainage issues will amplify
- Summer: water leakage and garbage issues intensify
- Post-monsoon: infrastructure weakened by water damage

## YOUR ANALYSIS MUST INCLUDE:

### Section 1: Executive Summary
- Key findings at a glance
- Most critical predictions

### Section 2: Data Overview
- Total tickets, date range, wards covered
- Distribution by category and severity

### Section 3: HIGH-RISK PREDICTIONS TABLE
| Ward | Issue Pattern | Tickets | Predicted Major Issue | Risk Level | Recommended Action | Timeline |
Show specific predictions of WHAT COULD GO WRONG if not addressed.

### Section 4: Hidden Insights & Escalation Risks
**CRITICAL**: This is the most important section!
- Identify issue chains (e.g., "Ward 21 has 12 manhole complaints over 6 months - THIS INDICATES aging underground infrastructure at risk of collapse")
- Correlate related issues (manhole damage → drainage overflow → potential sinkhole)
- Flag wards with multiple issue types (infrastructure under systemic stress)

### Section 5: Root Cause Analysis
- Why are certain wards repeatedly affected?
- What infrastructure might be failing?
- What systemic issues need addressing?

### Section 6: 30-Day Prediction Timeline
- Week 1-2: Immediate risks
- Week 3-4: Developing situations
- Issues likely to escalate if unaddressed

### Section 7: Preventive Action Plan
- **Immediate** (within 7 days): Critical interventions
- **Short-term** (7-14 days): Preventive maintenance
- **Medium-term** (15-30 days): Infrastructure assessment
Specific ward-level recommendations with clear actions.

### Section 8: Resource Allocation Recommendations
- Which departments need additional resources?
- Which wards require priority attention?
- Suggested manpower/equipment deployment

### Section 9: Conclusion & Risk Summary
- Top 3 critical risks requiring immediate attention
- Overall infrastructure health assessment

## OUTPUT FORMAT:

Generate a professional HTML report with:
- Modern, clean CSS styling (inline styles)
- Color-coded risk indicators (🔴 High, 🟠 Medium, 🟢 Low)
- Well-structured tables with headers
- Alert boxes for critical warnings
- Clear section dividers
- Professional fonts (system fonts, good spacing)
- Responsive design basics

## CRITICAL RULES:
1. Generate ONLY HTML content - no markdown, no code blocks
2. Be SPECIFIC - mention exact ward numbers, ticket counts, dates
3. Make BOLD PREDICTIONS about what could happen
4. Provide ACTIONABLE recommendations
5. Highlight HIDDEN PATTERNS that aren't obvious from raw data
6. Think like a city infrastructure engineer predicting failures
7. If data shows repeating issues in same location, treat as HIGH PRIORITY warning
8. **EXTREMELY IMPORTANT**: Generate the HTML as a SINGLE CONTINUOUS LINE with NO newlines, NO line breaks, NO \n characters. The entire HTML must be one unbroken string."""


class PredictiveAnalysisAgent:
    """Agent that analyzes historical ticket data and generates prediction reports."""
    
    def __init__(self):
        """Initialize the Predictive Analysis Agent with Gemini model."""
        settings = get_settings()
        logger.info(f"Initializing PredictiveAnalysisAgent with model: {settings.MODEL_NAME}")
        self.model = ChatGoogleGenerativeAI(
            model=settings.MODEL_NAME,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.3,  # Slightly higher for creative report writing
        )
        logger.info("PredictiveAnalysisAgent initialized successfully")
    
    def _prepare_ticket_summary(self, tickets: List[Dict[str, Any]]) -> str:
        """Prepare a summary of tickets for the LLM."""
        if not tickets:
            return "No tickets provided."
        
        summary = f"Total tickets: {len(tickets)}\n\n"
        summary += "Ticket Data:\n"
        summary += json.dumps(tickets, indent=2)
        
        return summary
    
    async def generate_report(self, tickets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a predictive analysis report from historical ticket data.
        
        Args:
            tickets: List of ticket dictionaries
            
        Returns:
            Dictionary with report_html, generated_at, and error
        """
        logger.info("=" * 60)
        logger.info("PREDICTIVE ANALYSIS AGENT - Starting analysis")
        logger.info("=" * 60)
        logger.info(f"Analyzing {len(tickets)} tickets")
        
        try:
            # Prepare ticket data for the model
            logger.info("Step 1: Preparing ticket summary...")
            ticket_summary = self._prepare_ticket_summary(tickets)
            logger.info(f"Step 1: Summary prepared ({len(ticket_summary)} characters)")
            
            # Create messages for the model
            logger.info("Step 2: Creating messages for Gemini model...")
            messages = [
                SystemMessage(content=PREDICTIVE_AGENT_SYSTEM_PROMPT),
                HumanMessage(
                    content=f"""Analyze the following civic complaint ticket data and generate a predictive HTML report for the next 30 days.

{ticket_summary}

Generate a comprehensive HTML report with predictions and recommendations."""
                )
            ]
            logger.info("Step 2: Messages created successfully")
            
            # Invoke the model
            logger.info("Step 3: Invoking Gemini model for report generation...")
            response = await self.model.ainvoke(messages)
            report_html = response.content
            logger.info("Step 3: Gemini model response received")
            logger.info(f"Step 3: Report length: {len(report_html)} characters")
            
            # Clean up the response
            logger.info("Step 4: Cleaning up HTML response...")
            report_html = self._clean_html_response(report_html)
            logger.info("Step 4: HTML cleaned successfully")
            
            generated_at = datetime.now().isoformat()
            
            logger.info("=" * 60)
            logger.info("PREDICTIVE ANALYSIS AGENT - Report generated successfully")
            logger.info("=" * 60)
            
            return {
                "report_html": report_html,
                "generated_at": generated_at,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Exception during predictive analysis: {str(e)}", exc_info=True)
            logger.info("=" * 60)
            logger.info("PREDICTIVE ANALYSIS AGENT - Analysis failed")
            logger.info("=" * 60)
            
            return {
                "report_html": "",
                "generated_at": datetime.now().isoformat(),
                "error": f"Report generation failed: {str(e)}"
            }
    
    def _clean_html_response(self, html: str) -> str:
        """Clean up HTML response from the model."""
        html = html.strip()
        
        # Remove markdown code blocks if present
        if html.startswith("```html"):
            html = html[7:]
        elif html.startswith("```"):
            html = html[3:]
        
        if html.endswith("```"):
            html = html[:-3]
        
        # Remove all newline characters and excessive whitespace
        html = html.replace('\n', '')
        html = html.replace('\r', '')
        html = html.replace('\t', '')
        # Collapse multiple spaces into single space
        html = re.sub(r'\s+', ' ', html)
        # Remove spaces around tags
        html = re.sub(r'>\s+<', '><', html)
        
        return html.strip()


# Singleton instance
_predictive_agent: Optional[PredictiveAnalysisAgent] = None


def get_predictive_agent() -> PredictiveAnalysisAgent:
    """Get or create singleton Predictive Analysis Agent instance."""
    global _predictive_agent
    if _predictive_agent is None:
        logger.info("Creating new PredictiveAnalysisAgent instance")
        _predictive_agent = PredictiveAnalysisAgent()
    return _predictive_agent
