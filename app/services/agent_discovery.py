import json
import logging
import re
import anthropic
from fastapi import HTTPException
from app.config import settings
from app.schemas.destination import DiscoveryItem, DiscoverRequest
from app.tools.destination_tool import GET_EXISTING_DESTINATIONS_TOOL, GEOCODE_TOOL, handle_tool_call
from app.services.pexels_service import fetch_image_url

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are a tourism expert AI assistant.
You will be given city names and asked to find tourist destinations in those cities.
You need to find next most popular/interesting destination unless these destinations are already in tool get_existing_destinations response
You also need to rank destinations by the number from 1 - 10 depending on how popular they are.
the expectation is that you will be returning next post popular destinations that we don`t have in the database.
  

When asked to find destinations in a city:
1. You MUST first call the `get_existing_destinations` tool with the provided city_id to retrieve destinations already saved for that city.
2. Decide on exactly 5 NEW destinations that are NOT in the existing list.
3. Call `get_coordinates` ONCE with all 5 destination names concatenated with the city (e.g. "Central Park, New York") to get their coordinates in a single call.
4. Never repeat destinations provided in the user's "already seen" list.
5. Return ONLY a valid JSON array with no prose, no markdown fences, no extra text.

Each item in the array must have these exact fields:
- name (string)
- short_description (string, 2 sentences)
- wikipedia_url (string — the full Wikipedia article URL for this destination, e.g. https://en.wikipedia.org/wiki/Statue_of_Liberty)
- latitude (string — from get_coordinates result)
- longitude (string — from get_coordinates result)
- interesting_facts (array of 3 strings)
- priority(number in range of 1 - 10 of how populare destination is)
"""



def run_discovery_agent(request: DiscoverRequest) -> list[DiscoveryItem]:
    load_more = bool(request.previous_results)
    user_message = f"Find me tourist destinations in {request.city_name} (city_id: {request.city_id})."

    if load_more:
        seen_names = [d.name for d in request.previous_results]  # type: ignore[union-attr]
        user_message += f" I have already seen these, do not repeat them: {json.dumps(seen_names)}."

    logger.info("=== Discovery Agent START ===")
    logger.info("City: %s (id=%d) | Load More: %s", request.city_name, request.city_id, load_more)
    logger.info("User message → LLM: %s", user_message)

    messages: list = [{"role": "user", "content": user_message}]
    turn = 0

    try:
        while True:
            turn += 1
            logger.info("--- LLM Call #%d ---", turn)
            logger.info("Sending %d message(s) to claude-sonnet-4-6", len(messages))

            # Available models (price per million tokens — input / output):
            # claude-haiku-4-5-20251001  →  $0.80 / $4.00   (cheapest, fastest)
            # claude-sonnet-4-6          →  $3.00 / $15.00  (balanced)
            # claude-opus-4-6            →  $15.00 / $75.00 (most capable, most expensive)
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=[GET_EXISTING_DESTINATIONS_TOOL, GEOCODE_TOOL],  # type: ignore[list-item]
                messages=messages,
            )

            logger.info("LLM response received | stop_reason: %s | input_tokens: %d | output_tokens: %d",
                        response.stop_reason, response.usage.input_tokens, response.usage.output_tokens)

            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})

                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        tool_input = dict(block.input)  # type: ignore[arg-type]
                        logger.info("LLM requested tool: '%s' | input: %s", block.name, json.dumps(tool_input))

                        result = handle_tool_call(block.name, tool_input)

                        existing = json.loads(result)
                        logger.info("Tool result → LLM: %d existing destination(s) found: %s", len(existing), existing)

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })

                messages.append({"role": "user", "content": tool_results})

            elif response.stop_reason == "end_turn":
                text = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        text = block.text
                        break

                logger.info("LLM final response text (first 300 chars): %s", text[:300])
                destinations = _parse_destinations(text)

                # Enrich each destination with an image from Pexels
                logger.info("--- Pexels image fetch START ---")
                enriched = [
                    dest.model_copy(update={"image_url": fetch_image_url(dest.name)})
                    for dest in destinations
                ]
                logger.info("--- Pexels image fetch END ---")

                logger.info("=== Discovery Agent END | returned %d destination(s) ===", len(enriched))
                return enriched

            else:
                logger.error("Unexpected stop_reason from LLM: %s", response.stop_reason)
                raise HTTPException(
                    status_code=502,
                    detail=f"Unexpected response from AI model (stop_reason: {response.stop_reason}).",
                )

    except HTTPException:
        raise
    except anthropic.AuthenticationError:
        logger.error("Anthropic authentication failed — check ANTHROPIC_API_KEY")
        raise HTTPException(status_code=401, detail="Invalid Anthropic API key. Please check your configuration.")
    except anthropic.RateLimitError:
        logger.warning("Anthropic rate limit reached")
        raise HTTPException(status_code=429, detail="Anthropic API rate limit reached. Please try again in a moment.")
    except anthropic.APIConnectionError as e:
        logger.error("Cannot connect to Anthropic API: %s", str(e))
        raise HTTPException(status_code=503, detail="Could not connect to the AI service. Please check your internet connection.")
    except anthropic.APIStatusError as e:
        logger.error("Anthropic API status error %d: %s", e.status_code, e.message)
        raise HTTPException(status_code=502, detail=f"AI service error: {e.message}")
    except json.JSONDecodeError as e:
        logger.error("JSON decode error in discovery agent: %s", str(e))
        raise HTTPException(status_code=502, detail="AI returned an invalid response format. Please try again.")
    except Exception as e:
        logger.exception("Unexpected error in discovery agent")
        raise HTTPException(status_code=500, detail=f"Unexpected error during destination discovery: {str(e)}")


def _parse_destinations(text: str) -> list[DiscoveryItem]:
    text = text.strip()

    # 1. Try markdown fences first (```json ... ```)
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()
    else:
        # 2. Extract the JSON array starting from the first '[' to the last ']'
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            logger.info("Extracted JSON array from mixed-text response (chars %d-%d)", start, end)
            text = text[start:end + 1]

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.error("Failed to parse destinations JSON. Raw text: %s", text[:500])
        raise HTTPException(status_code=502, detail="AI returned malformed JSON for destinations. Please try again.")

    try:
        return [DiscoveryItem(**item) for item in data]
    except Exception as e:
        logger.error("DiscoveryItem validation failed: %s", str(e))
        raise HTTPException(status_code=502, detail=f"AI response had unexpected structure: {str(e)}")
