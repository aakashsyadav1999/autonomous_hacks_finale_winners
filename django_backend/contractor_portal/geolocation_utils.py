"""
Geolocation Utility Functions.

Provides functions for calculating distance between coordinates
and verifying if contractor is within acceptable radius of work location.
"""

from math import radians, cos, sin, asin, sqrt
from decimal import Decimal
from typing import Tuple


def haversine_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float
) -> float:
    """
    Calculate the great-circle distance between two points on Earth.
    
    Uses the Haversine formula to calculate distance between two
    GPS coordinates. This is accurate for short distances and
    suitable for civic complaint verification.
    
    Args:
        lat1: Latitude of first point
        lon1: Longitude of first point
        lat2: Latitude of second point
        lon2: Longitude of second point
    
    Returns:
        Distance in meters
    
    Example:
        >>> distance = haversine_distance(12.9716, 77.5946, 12.9716, 77.5956)
        >>> print(f"{distance:.2f} meters")
        85.23 meters
    """
    # Earth's radius in meters
    R = 6371000
    
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    # Distance in meters
    distance = R * c
    
    return distance


def is_within_radius(
    original_lat: Decimal,
    original_lon: Decimal,
    current_lat: Decimal,
    current_lon: Decimal,
    radius_meters: int = 50
) -> Tuple[bool, float]:
    """
    Check if current location is within acceptable radius of original location.
    
    Used to verify that contractor is physically present at the work site
    when uploading completion photo.
    
    Args:
        original_lat: Original complaint latitude
        original_lon: Original complaint longitude
        current_lat: Contractor's current latitude
        current_lon: Contractor's current longitude
        radius_meters: Acceptable radius in meters (default: 50m)
    
    Returns:
        Tuple of (is_within_radius, actual_distance_meters)
        - is_within_radius: True if within acceptable radius
        - actual_distance_meters: Actual distance calculated
    
    Example:
        >>> is_valid, distance = is_within_radius(
        ...     Decimal('12.9716'), Decimal('77.5946'),
        ...     Decimal('12.9717'), Decimal('77.5947'),
        ...     radius_meters=50
        ... )
        >>> print(f"Valid: {is_valid}, Distance: {distance:.2f}m")
        Valid: True, Distance: 14.23m
    """
    # Convert Decimal to float for calculation
    distance = haversine_distance(
        float(original_lat),
        float(original_lon),
        float(current_lat),
        float(current_lon)
    )
    
    is_valid = distance <= radius_meters
    
    return (is_valid, distance)


def format_distance(distance_meters: float) -> str:
    """
    Format distance for display.
    
    Args:
        distance_meters: Distance in meters
    
    Returns:
        Formatted string (e.g., "45.2m" or "1.2km")
    """
    if distance_meters < 1000:
        return f"{distance_meters:.1f}m"
    else:
        return f"{distance_meters / 1000:.2f}km"
