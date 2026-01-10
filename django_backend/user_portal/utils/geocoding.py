"""
Geocoding utilities for reverse geocoding coordinates to addresses.

This module uses geopy with Nominatim (OpenStreetMap) to convert
GPS coordinates to human-readable addresses. Focused on Ahmedabad,
Gujarat, India region.
"""

import logging
from typing import Dict, Optional
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError


logger = logging.getLogger(__name__)


class GeocodeService:
    """
    Service for converting GPS coordinates to address components.
    
    Uses OpenStreetMap's Nominatim geocoding service (free tier).
    Implements retry logic for transient failures.
    """
    
    def __init__(self):
        """
        Initialize geocoder with user agent.
        
        Nominatim requires a unique user agent to identify your application.
        """
        self.geocoder = Nominatim(
            user_agent="civic_complaint_system_ahmedabad_v1.0",
            timeout=10
        )
    
    def reverse_geocode(
        self,
        latitude: float,
        longitude: float,
        max_retries: int = 3
    ) -> Optional[Dict[str, str]]:
        """
        Convert coordinates to address components.
        
        Args:
            latitude: GPS latitude coordinate
            longitude: GPS longitude coordinate
            max_retries: Maximum retry attempts for API failures
        
        Returns:
            Dictionary with address components:
            {
                'street': '132 Feet Ring Road',
                'area': 'Satellite',
                'postal_code': '380015',
                'city': 'Ahmedabad',
                'state': 'Gujarat',
                'country': 'India'
            }
            Returns None if geocoding fails after retries.
        
        Note:
            Nominatim is a free service with usage limits.
            For production, consider:
            - Caching results
            - Rate limiting requests
            - Using paid geocoding services for higher reliability
        """
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Query Nominatim with coordinates
                location = self.geocoder.reverse(
                    f"{latitude}, {longitude}",
                    language='en',
                    addressdetails=True
                )
                
                if location is None:
                    logger.warning(
                        f"No address found for coordinates: {latitude}, {longitude}"
                    )
                    return None
                
                # Extract address components
                address = location.raw.get('address', {})
                
                # Parse address components with fallbacks
                street = self._extract_street(address)
                area = self._extract_area(address)
                postal_code = address.get('postcode', '')
                
                result = {
                    'street': street,
                    'area': area,
                    'postal_code': postal_code,
                    'city': address.get('city', 'Ahmedabad'),
                    'state': address.get('state', 'Gujarat'),
                    'country': address.get('country', 'India')
                }
                
                logger.info(
                    f"Geocoded coordinates ({latitude}, {longitude}) "
                    f"to: {area}, {result['city']}"
                )
                
                return result
            
            except GeocoderTimedOut:
                retry_count += 1
                logger.warning(
                    f"Geocoding timeout (attempt {retry_count}/{max_retries})"
                )
                
                if retry_count >= max_retries:
                    logger.error(
                        f"Geocoding failed after {max_retries} attempts "
                        f"for coordinates: {latitude}, {longitude}"
                    )
                    return None
            
            except GeocoderServiceError as e:
                logger.error(f"Geocoding service error: {str(e)}")
                return None
            
            except Exception as e:
                logger.error(f"Unexpected geocoding error: {str(e)}")
                return None
        
        return None
    
    def _extract_street(self, address: Dict) -> str:
        """
        Extract street address from Nominatim address components.
        
        Tries multiple fields in priority order:
        road > neighbourhood > suburb > residential
        """
        street_fields = ['road', 'neighbourhood', 'suburb', 'residential']
        
        for field in street_fields:
            if field in address and address[field]:
                return address[field]
        
        return ''
    
    def _extract_area(self, address: Dict) -> str:
        """
        Extract area/locality from Nominatim address components.
        
        Tries multiple fields in priority order:
        neighbourhood > suburb > city_district > residential
        """
        area_fields = ['neighbourhood', 'suburb', 'city_district', 'residential']
        
        for field in area_fields:
            if field in address and address[field]:
                return address[field]
        
        # Fallback to city if no area found
        return address.get('city', 'Ahmedabad')


# Singleton instance for reuse
_geocode_service = None


def get_geocode_service() -> GeocodeService:
    """
    Get or create singleton GeocodeService instance.
    
    Returns:
        GeocodeService instance
    """
    global _geocode_service
    
    if _geocode_service is None:
        _geocode_service = GeocodeService()
    
    return _geocode_service


def geocode_coordinates(latitude: float, longitude: float) -> Optional[Dict[str, str]]:
    """
    Convenience function for reverse geocoding.
    
    Args:
        latitude: GPS latitude
        longitude: GPS longitude
    
    Returns:
        Address dictionary or None if geocoding fails
    """
    service = get_geocode_service()
    return service.reverse_geocode(latitude, longitude)
