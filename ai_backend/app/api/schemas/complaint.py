"""
Pydantic schemas for complaint analysis API.
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class SeverityLevel(str, Enum):
    """Severity levels for detected civic issues."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class CategoryType(str, Enum):
    """Valid civic complaint categories."""
    GARBAGE = "Garbage/Waste accumulation"
    MANHOLE = "Manholes/drainage opening damage"
    WATER_LEAKAGE = "Water leakage"
    DRAINAGE_OVERFLOW = "Drainage overflow"


class DepartmentType(str, Enum):
    """Municipal departments for handling complaints."""
    SANITATION = "Sanitation Department"
    ROADS_INFRASTRUCTURE = "Roads & Infrastructure"
    WATER_SUPPLY = "Water Supply Department"
    DRAINAGE = "Drainage Department"


# Category to Department mapping
CATEGORY_DEPARTMENT_MAP = {
    CategoryType.GARBAGE: DepartmentType.SANITATION,
    CategoryType.MANHOLE: DepartmentType.ROADS_INFRASTRUCTURE,
    CategoryType.WATER_LEAKAGE: DepartmentType.WATER_SUPPLY,
    CategoryType.DRAINAGE_OVERFLOW: DepartmentType.DRAINAGE,
}


class ComplaintAnalysisRequest(BaseModel):
    """Request schema for complaint image analysis."""
    
    image: str = Field(
        ..., 
        description="Base64 encoded image of the civic issue"
    )
    street: str = Field(
        ..., 
        description="Street name where the issue is located"
    )
    area: str = Field(
        ..., 
        description="Area/locality name"
    )
    postal_code: str = Field(
        ..., 
        description="Postal/ZIP code of the location"
    )
    latitude: float = Field(
        ..., 
        description="GPS latitude coordinate"
    )
    longitude: float = Field(
        ..., 
        description="GPS longitude coordinate"
    )


class DetectedIssue(BaseModel):
    """Schema for a single detected civic issue."""
    
    category: str = Field(
        ..., 
        description="Category of the detected civic issue"
    )
    department: str = Field(
        ..., 
        description="Department responsible for handling this issue"
    )
    severity: str = Field(
        ..., 
        description="Severity level: Low, Medium, or High"
    )
    suggested_tools: List[str] = Field(
        default_factory=list,
        description="List of suggested tools to resolve the issue"
    )
    safety_equipment: List[str] = Field(
        default_factory=list,
        description="List of mandatory safety equipment for workers"
    )


class ComplaintAnalysisResponse(BaseModel):
    """Response schema for complaint image analysis."""
    
    is_valid: bool = Field(
        ..., 
        description="Whether the image contains valid civic issues"
    )
    data: List[DetectedIssue] = Field(
        default_factory=list,
        description="List of detected issues with their categories, departments, and severity"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if image is invalid or processing failed"
    )


class ComplaintAnalysisResponseWithWard(BaseModel):
    """Response schema for complaint image analysis with ward mapping."""
    
    is_valid: bool = Field(
        ..., 
        description="Whether the image contains valid civic issues"
    )
    data: List[DetectedIssue] = Field(
        default_factory=list,
        description="List of detected issues with their categories, departments, and severity"
    )
    ward_no: Optional[str] = Field(
        default=None,
        description="Ward number based on GPS coordinates"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if image is invalid or processing failed"
    )


class WorkVerificationRequest(BaseModel):
    """Request schema for work completion verification."""
    
    before_image: str = Field(
        ..., 
        description="Base64 encoded original complaint image"
    )
    after_image: str = Field(
        ..., 
        description="Base64 encoded contractor completion image"
    )
    category: str = Field(
        ..., 
        description="Category of the original complaint (e.g., 'Garbage/Waste accumulation')"
    )


class WorkVerificationResponse(BaseModel):
    """Response schema for work completion verification."""
    
    is_completed: bool = Field(
        ..., 
        description="Whether the work has been completed successfully"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if verification failed"
    )


class TicketData(BaseModel):
    """Schema for historical ticket data used in predictive analysis."""
    
    ticket_number: str = Field(
        ...,
        description="Unique ticket identifier"
    )
    category: str = Field(
        ...,
        description="Category of the civic issue"
    )
    severity: str = Field(
        ...,
        description="Severity level: Low, Medium, or High"
    )
    department: str = Field(
        ...,
        description="Department responsible for handling"
    )
    ward_no: str = Field(
        ...,
        description="Ward number"
    )
    ward_name: str = Field(
        ...,
        description="Ward name"
    )
    created_at: str = Field(
        ...,
        description="Ticket creation timestamp (ISO format)"
    )
    resolved_at: Optional[str] = Field(
        default=None,
        description="Ticket resolution timestamp (ISO format), null if unresolved"
    )


class PredictiveAnalysisRequest(BaseModel):
    """Request schema for predictive analysis."""
    
    tickets: List[TicketData] = Field(
        ...,
        description="List of historical tickets from the past 30 days"
    )


class PredictiveAnalysisResponse(BaseModel):
    """Response schema for predictive analysis."""
    
    report_html: str = Field(
        ...,
        description="HTML formatted predictive analysis report"
    )
    generated_at: str = Field(
        ...,
        description="Report generation timestamp (ISO format)"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if analysis failed"
    )
