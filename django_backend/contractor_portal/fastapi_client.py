"""
FastAPI Integration Utility for AI Analysis.

This module handles communication with the FastAPI backend for:
1. Complaint image analysis (validating civic issues)
2. Work completion verification (before/after image comparison)

Implements retry logic, timeout handling, and error management.
"""

import os
import base64
import requests
from typing import Dict, Any, Optional, Tuple
from decimal import Decimal
from django.conf import settings


class FastAPIError(Exception):
    """Custom exception for FastAPI integration errors."""
    pass


class FastAPIClient:
    """
    Client for communicating with FastAPI AI services.
    
    Handles image encoding, API requests, retries, and error handling
    for both analyze and verify endpoints.
    """
    
    def __init__(self):
        """Initialize FastAPI client with base URL from environment."""
        self.base_url = os.getenv('FASTAPI_BASE_URL', 'http://localhost:8000')
        if not self.base_url:
            raise FastAPIError("FASTAPI_BASE_URL environment variable not set")
        
        # Remove trailing slash
        self.base_url = self.base_url.rstrip('/')
        
        # Configure timeouts (in seconds)
        self.timeout = 60  # AI processing can take time
        self.max_retries = 3
    
    @staticmethod
    def encode_image_to_base64(image_path: str) -> str:
        """
        Convert image file to base64 string for API transmission.
        
        Args:
            image_path: Absolute path to image file
        
        Returns:
            Base64 encoded string of image
        
        Raises:
            FastAPIError: If file not found or encoding fails
        """
        try:
            with open(image_path, 'rb') as image_file:
                encoded = base64.b64encode(image_file.read()).decode('utf-8')
                return encoded
        except FileNotFoundError:
            raise FastAPIError(f"Image file not found: {image_path}")
        except Exception as e:
            raise FastAPIError(f"Failed to encode image: {str(e)}")
    
    @staticmethod
    def encode_image_field_to_base64(image_field) -> str:
        """
        Convert Django ImageField to base64 string.
        
        Args:
            image_field: Django ImageField instance
        
        Returns:
            Base64 encoded string of image
        
        Raises:
            FastAPIError: If encoding fails
        """
        try:
            image_field.seek(0)  # Reset file pointer
            encoded = base64.b64encode(image_field.read()).decode('utf-8')
            return encoded
        except Exception as e:
            raise FastAPIError(f"Failed to encode image field: {str(e)}")
    
    def analyze_complaint(
        self,
        image_path: str,
        street: str,
        area: str,
        postal_code: str,
        latitude: Decimal,
        longitude: Decimal
    ) -> Dict[str, Any]:
        """
        Send complaint image to AI for analysis and validation.
        
        Calls POST /api/v1/analyze/complaint endpoint.
        
        Args:
            image_path: Path to complaint image file
            street: Street address
            area: Area/locality name
            postal_code: PIN/ZIP code
            latitude: GPS latitude
            longitude: GPS longitude
        
        Returns:
            Dictionary with AI analysis results:
            {
                "is_valid": bool,
                "data": [
                    {
                        "category": str,
                        "department": str,
                        "severity": str
                    },
                    ...
                ],
                "error": str or None
            }
        
        Raises:
            FastAPIError: If API call fails after retries
        """
        # Encode image
        image_base64 = self.encode_image_to_base64(image_path)
        
        # Prepare request payload
        payload = {
            "image": image_base64,
            "street": street,
            "area": area,
            "postal_code": postal_code,
            "latitude": float(latitude),
            "longitude": float(longitude)
        }
        
        # Call API with retry logic
        endpoint = f"{self.base_url}/api/v1/analyze/complaint"
        
        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.post(
                    endpoint,
                    json=payload,
                    timeout=self.timeout,
                    headers={'Content-Type': 'application/json'}
                )
                
                # Check status code
                if response.status_code == 200:
                    return response.json()
                else:
                    error_msg = f"API returned status {response.status_code}: {response.text}"
                    
                    # Don't retry for 4xx errors (client errors)
                    if 400 <= response.status_code < 500:
                        raise FastAPIError(error_msg)
                    
                    # Retry for 5xx errors
                    if attempt == self.max_retries:
                        raise FastAPIError(error_msg)
            
            except requests.exceptions.Timeout:
                if attempt == self.max_retries:
                    raise FastAPIError(f"API request timed out after {self.timeout}s")
            
            except requests.exceptions.ConnectionError:
                if attempt == self.max_retries:
                    raise FastAPIError(f"Failed to connect to FastAPI server at {self.base_url}")
            
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries:
                    raise FastAPIError(f"API request failed: {str(e)}")
        
        # Should not reach here, but just in case
        raise FastAPIError("API call failed after retries")
    
    def verify_completion(
        self,
        before_image_path: str,
        after_image_path: str,
        category: str
    ) -> Dict[str, Any]:
        """
        Send before/after images to AI for work completion verification.
        
        Calls POST /api/v1/verify/completion endpoint.
        
        Args:
            before_image_path: Path to original complaint image
            after_image_path: Path to contractor's completion image
            category: Original complaint category
        
        Returns:
            Dictionary with verification results:
            {
                "is_completed": bool,
                "error": str or None
            }
        
        Raises:
            FastAPIError: If API call fails after retries
        """
        # Encode both images
        before_base64 = self.encode_image_to_base64(before_image_path)
        after_base64 = self.encode_image_to_base64(after_image_path)
        
        # Prepare request payload
        payload = {
            "before_image": before_base64,
            "after_image": after_base64,
            "category": category
        }
        
        # Call API with retry logic
        endpoint = f"{self.base_url}/api/v1/verify/completion"
        
        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.post(
                    endpoint,
                    json=payload,
                    timeout=self.timeout,
                    headers={'Content-Type': 'application/json'}
                )
                
                # Check status code
                if response.status_code == 200:
                    return response.json()
                else:
                    error_msg = f"API returned status {response.status_code}: {response.text}"
                    
                    # Don't retry for 4xx errors
                    if 400 <= response.status_code < 500:
                        raise FastAPIError(error_msg)
                    
                    # Retry for 5xx errors
                    if attempt == self.max_retries:
                        raise FastAPIError(error_msg)
            
            except requests.exceptions.Timeout:
                if attempt == self.max_retries:
                    raise FastAPIError(f"API request timed out after {self.timeout}s")
            
            except requests.exceptions.ConnectionError:
                if attempt == self.max_retries:
                    raise FastAPIError(f"Failed to connect to FastAPI server at {self.base_url}")
            
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries:
                    raise FastAPIError(f"API request failed: {str(e)}")
        
        raise FastAPIError("API call failed after retries")


# Convenience functions for easy import
def analyze_complaint_image(
    image_path: str,
    street: str,
    area: str,
    postal_code: str,
    latitude: Decimal,
    longitude: Decimal
) -> Tuple[bool, list, Optional[str]]:
    """
    Convenience function to analyze complaint image.
    
    Returns:
        Tuple of (is_valid, data_list, error_message)
        - is_valid: True if image contains valid civic issue
        - data_list: List of detected issues with category/department/severity
        - error_message: Error string if validation failed, None otherwise
    """
    client = FastAPIClient()
    result = client.analyze_complaint(
        image_path, street, area, postal_code, latitude, longitude
    )
    
    return (
        result.get('is_valid', False),
        result.get('data', []),
        result.get('error')
    )


def verify_work_completion(
    before_image_path: str,
    after_image_path: str,
    category: str
) -> Tuple[bool, Optional[str]]:
    """
    Convenience function to verify work completion.
    
    Returns:
        Tuple of (is_completed, error_message)
        - is_completed: True if AI confirms work is properly completed
        - error_message: Error string if verification failed, None otherwise
    """
    client = FastAPIClient()
    result = client.verify_completion(
        before_image_path, after_image_path, category
    )
    
    return (
        result.get('is_completed', False),
        result.get('error')
    )
