import json
import logging
import re
import anthropic
from fastapi import HTTPException
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.config import settings
from app.models.destination import TourGuideResponse

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an expert travel storyteller creating audio scripts for a tourism app.

Given a destination and a list of facts, write a narration that sounds like a skilled local guide speaking to a curious traveler.

The user will provide:
- a destination
- a list of specific facts or themes to include

The script should:
- begin with an engaging hook, never with “Welcome to…”
- give a short, clear sense of the destination’s history
- explain its cultural, historical, or practical importance
- include the user’s facts naturally and smoothly
- mention what visitors can see, do, or experience nearby
- feel vivid, human, and easy to listen to aloud
- use storytelling, atmosphere, and curiosity to hold attention
- avoid lists, headings, and stiff textbook language
- never fabricate details

Style:
- conversational and polished
- descriptive but not overly long
- suitable for text-to-speech narration
- interesting for both casual tourists and curious learners

Output rules:
- return only valid JSON
- use exactly this structure:
{{
  "tour_guide": "..."
}}
"""

_model = ChatAnthropic(
    model="claude-haiku-4-5-20251001",
    api_key=settings.ANTHROPIC_API_KEY,
    max_tokens=2048,
)

_chain = (
    ChatPromptTemplate.from_messages([
        ("system", _SYSTEM_PROMPT),
        ("human", "{user_message}"),
    ])
    | _model
    | StrOutputParser()
)


def regenerate_description(city: str, destination_name: str, selected_facts: list[str]) -> TourGuideResponse:
    logger.info("=== Tour Guide Agent START === destination: '%s' | city: '%s' | facts: %d",
                destination_name, city, len(selected_facts))

    facts_text = "\n".join(f"- {f}" for f in selected_facts)
    user_message = (
        f"Write a tour guide for '{destination_name}' in {city} "
        f"focused on these specific facts:\n{facts_text}"
    )

    try:
        text = _chain.invoke({"user_message": user_message})
    except anthropic.AuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid Anthropic API key.")
    except anthropic.RateLimitError:
        raise HTTPException(status_code=429, detail="Anthropic API rate limit reached. Please try again.")
    except anthropic.APIConnectionError:
        raise HTTPException(status_code=503, detail="Could not connect to the AI service.")
    except anthropic.APIStatusError as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {e.message}")
    except Exception as e:
        logger.exception("Unexpected error in tour guide agent")
        raise HTTPException(status_code=500, detail=f"Unexpected error generating tour guide: {str(e)}")

    logger.info("Tour Guide LLM response (first 300 chars): %s", text[:300])

    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start:end + 1]

    try:
        data = json.loads(text)
        result = TourGuideResponse(tour_guide=data["tour_guide"])
        logger.info("=== Tour Guide Agent END ===")
        return result
    except (json.JSONDecodeError, KeyError) as e:
        logger.error("Failed to parse tour guide response: %s", e)
        raise HTTPException(status_code=502, detail="AI returned malformed tour guide response. Please try again.")
