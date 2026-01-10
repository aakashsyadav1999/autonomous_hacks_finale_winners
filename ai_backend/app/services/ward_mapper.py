"""
Ward Mapper Service for mapping GPS coordinates to Ahmedabad wards.
Uses GeoJSON polygon data with Shapely for point-in-polygon matching.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from shapely.geometry import Point, shape

# Configure logger
logger = logging.getLogger(__name__)

# Path to GeoJSON file
GEOJSON_PATH = Path(__file__).parent.parent / "data" / "wards.geojson"


class WardMapper:
    """Service for mapping GPS coordinates to AMC wards using GeoJSON polygons."""
    
    def __init__(self):
        """Initialize WardMapper by loading GeoJSON data."""
        logger.info("Initializing WardMapper...")
        self.ward_polygons = []
        self._load_geojson()
        logger.info(f"WardMapper initialized with {len(self.ward_polygons)} ward polygons")
    
    def _load_geojson(self):
        """Load ward boundary polygons from GeoJSON file."""
        if not GEOJSON_PATH.exists():
            logger.error(f"GeoJSON file not found at {GEOJSON_PATH}")
            raise FileNotFoundError(f"Ward GeoJSON not found: {GEOJSON_PATH}")
        
        with open(GEOJSON_PATH, 'r') as f:
            data = json.load(f)
        
        for feature in data.get("features", []):
            try:
                geometry = feature.get("geometry")
                properties = feature.get("properties", {})
                ward_name_raw = properties.get("Name", "")
                
                # Parse ward name (format: "48 RAMOL HATHIJAN" -> extract ward number and name)
                parts = ward_name_raw.split(" ", 1)
                ward_no = parts[0] if parts else ""
                ward_name = parts[1] if len(parts) > 1 else ward_name_raw
                
                # Create polygon from geometry
                polygon = shape(geometry)
                
                self.ward_polygons.append({
                    "polygon": polygon,
                    "ward_no": ward_no,
                    "ward_name": ward_name,
                    "raw_name": ward_name_raw
                })
                
            except Exception as e:
                logger.warning(f"Failed to parse ward feature: {e}")
                continue
        
        logger.info(f"Loaded {len(self.ward_polygons)} ward polygons from GeoJSON")
    
    def find_ward(self, latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        """
        Find the ward containing the given GPS coordinates.
        
        Args:
            latitude: GPS latitude coordinate
            longitude: GPS longitude coordinate
            
        Returns:
            Dictionary with ward_no and ward_name, or None if not found
        """
        logger.info(f"Finding ward for coordinates: ({latitude}, {longitude})")
        
        # Create point (GeoJSON uses lon, lat order)
        point = Point(longitude, latitude)
        
        for ward in self.ward_polygons:
            try:
                if ward["polygon"].contains(point):
                    logger.info(f"Found ward: {ward['raw_name']}")
                    return {
                        "ward_no": ward["ward_no"],
                        "ward_name": ward["ward_name"]
                    }
                        
            except Exception as e:
                logger.warning(f"Error checking ward {ward['raw_name']}: {e}")
                continue
        
        logger.warning(f"No ward found for coordinates: ({latitude}, {longitude})")
        return None


# Singleton instance
_ward_mapper: Optional[WardMapper] = None


def get_ward_mapper() -> WardMapper:
    """Get or create singleton WardMapper instance."""
    global _ward_mapper
    if _ward_mapper is None:
        logger.info("Creating new WardMapper instance")
        _ward_mapper = WardMapper()
    return _ward_mapper
