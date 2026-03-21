import json
import logging
import re
import anthropic
from fastapi import HTTPException
from app.config import settings
from app.schemas.destination import DetailItem

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are a professional travel writer and tourism guide.

Return ONLY a valid JSON object with no prose, no markdown fences, no extra text.

The JSON object must have these exact fields:
- name (string — the exact destination name)
- latitude (string — precise coordinates)
- longitude (string — precise coordinates)
- short_description (string — 2 sentences introducing the destination as a tourism guide)
- long_description (string — 3 to 4 paragraphs written as a tourism app audio script, vivid and engaging)"""


def run_detail_agent(city: str, destination_name: str) -> DetailItem:
    logger.info("=== Detail Agent START === destination: '%s' | city: '%s'", destination_name, city)

    try:
        # Available models (price per million tokens — input / output):
        # claude-haiku-4-5-20251001  →  $0.80 / $4.00   (cheapest, fastest)
        # claude-sonnet-4-6          →  $3.00 / $15.00  (balanced)
        # claude-opus-4-6            →  $15.00 / $75.00 (most capable, most expensive)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Give me the full tourism guide details for '{destination_name}' in {city}.",
                }
            ],
        )
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
    except Exception as e:
        logger.exception("Unexpected error in detail agent")
        raise HTTPException(status_code=500, detail=f"Unexpected error fetching destination detail: {str(e)}")

    logger.info("LLM response received | input_tokens: %d | output_tokens: %d",
                response.usage.input_tokens, response.usage.output_tokens)

    text = ""
    for block in response.content:
        if hasattr(block, "text"):
            text = block.text
            break

    logger.info("LLM raw response (first 300 chars): %s", text[:300])
    detail = _parse_detail(text)
    logger.info("=== Detail Agent END === returned detail for '%s'", detail.name)
    return detail


def _parse_detail(text: str) -> DetailItem:
    text = text.strip()

    # 1. Try markdown fences first
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()
    else:
        # 2. Extract JSON object from first '{' to last '}'
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            logger.info("Extracted JSON object from mixed-text response (chars %d-%d)", start, end)
            text = text[start:end + 1]

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.error("Failed to parse detail JSON. Raw text: %s", text[:500])
        raise HTTPException(status_code=502, detail="AI returned malformed JSON for destination detail. Please try again.")

    try:
        return DetailItem(**data)
    except Exception as e:
        logger.error("DetailItem validation failed: %s", str(e))
        raise HTTPException(status_code=502, detail=f"AI response had unexpected structure: {str(e)}")
