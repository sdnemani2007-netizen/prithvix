import math
from typing import Tuple, List, Dict, Any, Optional


def zone_for(lat: float) -> str:
    """Classify agro-climatic zone by latitude."""
    abs_lat = abs(float(lat))
    if abs_lat < 23.5:
        return "trop"
    elif abs_lat < 40.0:
        return "humid"
    else:
        return "temp"


def validate_coordinates(lat: float, lon: float) -> Tuple[float, float]:
    """Validate latitude and longitude ranges."""
    lat_f = float(lat)
    lon_f = float(lon)
    if not (-90.0 <= lat_f <= 90.0):
        raise ValueError(f"Latitude {lat_f} must be between -90 and 90 degrees.")
    if not (-180.0 <= lon_f <= 180.0):
        raise ValueError(f"Longitude {lon_f} must be between -180 and 180 degrees.")
    return lat_f, lon_f


def parse_boundary_to_geojson(boundary: Any, fallback_lat: float, fallback_lon: float) -> Dict[str, Any]:
    """
    Accepts GeoJSON dict, list of points [{'lat':..., 'lng':...}], or list of polygons,
    and returns a standardized GeoJSON Geometry dict.
    """
    if isinstance(boundary, dict):
        if boundary.get("type") in ("Point", "Polygon", "MultiPolygon", "Feature", "FeatureCollection"):
            return boundary

    # If it's a list of coordinate dictionaries or lists
    if isinstance(boundary, list) and len(boundary) > 0:
        # Check if list of polygons [[{lat, lng}, ...], ...]
        if isinstance(boundary[0], list):
            # Take the first polygon for geometry
            coords_ring = []
            for pt in boundary[0]:
                if isinstance(pt, dict) and "lat" in pt and "lng" in pt:
                    coords_ring.append([float(pt["lng"]), float(pt["lat"])])
                elif isinstance(pt, (list, tuple)) and len(pt) >= 2:
                    coords_ring.append([float(pt[0]), float(pt[1])])
            if len(coords_ring) >= 3:
                # Ensure closed ring
                if coords_ring[0] != coords_ring[-1]:
                    coords_ring.append(coords_ring[0])
                return {"type": "Polygon", "coordinates": [coords_ring]}

        # If it's a single polygon list [{lat, lng}, ...]
        if len(boundary) >= 3 and isinstance(boundary[0], dict) and "lat" in boundary[0]:
            coords_ring = [[float(pt["lng"]), float(pt["lat"])] for pt in boundary]
            if coords_ring[0] != coords_ring[-1]:
                coords_ring.append(coords_ring[0])
            return {"type": "Polygon", "coordinates": [coords_ring]}

    # Fallback: Point at farm coordinates
    return {
        "type": "Point",
        "coordinates": [float(fallback_lon), float(fallback_lat)]
    }


def compute_centroid_and_area(geojson: Dict[str, Any], default_lat: float, default_lon: float) -> Tuple[float, float, float]:
    """
    Returns (centroid_lat, centroid_lon, area_km2).
    """
    try:
        from shapely.geometry import shape
        geom = shape(geojson)
        centroid = geom.centroid
        centroid_lat = float(centroid.y)
        centroid_lon = float(centroid.x)

        # Approximate geodesic area in km2
        # 1 deg lat ~ 111 km, 1 deg lon ~ 111 * cos(lat) km
        if geom.geom_type in ("Polygon", "MultiPolygon"):
            cos_lat = math.cos(math.radians(centroid_lat))
            # Shape area is in square degrees
            # (deg_lat * 111.0) * (deg_lon * 111.0 * cos_lat)
            area_deg2 = geom.area
            area_km2 = float(area_deg2 * (111.0 ** 2) * max(0.1, abs(cos_lat)))
        else:
            area_km2 = 0.05  # Point buffer ~500m default
        return centroid_lat, centroid_lon, max(0.01, round(area_km2, 4))
    except Exception:
        return default_lat, default_lon, 0.05
