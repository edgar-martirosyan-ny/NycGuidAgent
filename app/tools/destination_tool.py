import json
import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

GEOCODE_TOOL = {
    "name": "get_coordinates",
    "description": "Get latitude and longitude for multiple destinations in one call. Pass all destination names at once.",
    "input_schema": {
        "type": "object",
        "properties": {
            "destination_names": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of destination names each concatenated with the city, e.g. ['Central Park, New York', 'Brooklyn Bridge, New York'].",
            }
        },
        "required": ["destination_names"],
    },
}

GET_EXISTING_DESTINATIONS_TOOL = {
    "name": "get_existing_destinations",
    "description": (
        "Fetches the list of tourism destination names already saved in the database "
        "for a given city. You MUST call this tool before suggesting any destinations "
        "to ensure you do not recommend places the user already has."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "city_id": {
                "type": "integer",
                "description": "The numeric city ID to look up saved destinations for.",
            }
        },
        "required": ["city_id"],
    },
}


def handle_tool_call(tool_name: str, tool_input: dict) -> str:
    if tool_name == "get_existing_destinations":
        city_id = tool_input.get("city_id")
        url = f"{settings.BACKEND_BASE_URL}/api/discover-destinations/city/{city_id}/names"
        try:
            response = httpx.get(url, timeout=10.0)
            response.raise_for_status()
            return json.dumps(response.json())
        except httpx.HTTPError as e:
            logger.error("Failed to fetch existing destinations from backend: %s", str(e))
            return json.dumps([])

    if tool_name == "get_coordinates":
        destination_names = tool_input.get("destination_names", [])
        url = f"{settings.BACKEND_BASE_URL}/api/destinations/geocode"
        try:
            response = httpx.post(url, json=destination_names, timeout=10.0)
            response.raise_for_status()
            return json.dumps(response.json())
        except Exception as e:
            logger.error("Geocode API call failed: %s", str(e))
            return json.dumps([])

    return json.dumps([])
