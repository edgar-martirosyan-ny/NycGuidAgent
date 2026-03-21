import json
from sqlalchemy.orm import Session
from app.services.destination_service import get_existing_by_city

GET_EXISTING_DESTINATIONS_TOOL = {
    "name": "get_existing_destinations",
    "description": (
        "Fetches the list of tourism destinations already saved in the database "
        "for a given city. You MUST call this tool before suggesting any destinations "
        "to ensure you do not recommend places the user already has."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "The city name to look up saved destinations for.",
            }
        },
        "required": ["city"],
    },
}


def handle_tool_call(tool_name: str, tool_input: dict, db: Session) -> str:
    if tool_name == "get_existing_destinations":
        city = tool_input.get("city", "")
        existing = get_existing_by_city(city, db)
        return json.dumps(existing)
    return json.dumps([])
