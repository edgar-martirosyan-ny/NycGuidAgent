import logging
import httpx
import anthropic
from app.config import settings

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 2
REQUEST_TIMEOUT = 5  # seconds

client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

FALLBACK_IMAGE = "https://placehold.co/400x220?text=No+Image"


def is_image_accessible(url: str) -> bool:
    """Check if an image URL returns a successful HTTP response."""
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT, follow_redirects=True) as http:
            response = http.head(url)
            ok = response.status_code == 200
            if not ok:
                logger.warning("Image URL returned %d: %s", response.status_code, url)
            return ok
    except Exception as e:
        logger.warning("Image URL check failed (%s): %s", type(e).__name__, url)
        return False


def _ask_llm_for_replacement(destination_name: str, bad_url: str, attempt: int) -> str:
    """Ask the LLM to provide a single working replacement image URL."""
    logger.info("  Attempt %d: asking LLM to replace broken URL for '%s'", attempt, destination_name)
    response = client.messages.create(
        # Available models (price per million tokens — input / output):
        # claude-haiku-4-5-20251001  →  $0.80 / $4.00   (cheapest, fastest)
        # claude-sonnet-4-6          →  $3.00 / $15.00  (balanced)
        # claude-opus-4-6            →  $15.00 / $75.00 (most capable, most expensive)
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        messages=[
            {
                "role": "user",
                "content": (
                    f"The image URL '{bad_url}' for '{destination_name}' is not accessible. "
                    f"Provide ONE replacement image URL using this exact format: "
                    f"https://en.wikipedia.org/wiki/Special:FilePath/<ExactFilename> "
                    f"where <ExactFilename> is a real Wikimedia Commons filename you are confident exists "
                    f"(use underscores for spaces, e.g. 'Central_Park_aerial.jpg'). "
                    f"Do NOT use upload.wikimedia.org URLs. Reply with ONLY the URL, nothing else."
                ),
            }
        ],
    )
    url = ""
    for block in response.content:
        if hasattr(block, "text"):
            url = block.text.strip().strip('"').strip("'")
            break
    logger.info("  LLM suggested replacement URL: %s", url)
    return url


def validate_and_fix_image_links(destination_name: str, image_links: list[str]) -> list[str]:
    """
    For each image URL:
      - Check if it is accessible.
      - If not, ask the LLM for a replacement (up to MAX_ATTEMPTS times).
      - If all attempts fail, replace with a placeholder.
    """
    fixed: list[str] = []

    for idx, url in enumerate(image_links):
        logger.info("Checking image %d/%d for '%s': %s", idx + 1, len(image_links), destination_name, url)

        if is_image_accessible(url):
            logger.info("  ✓ Image OK")
            fixed.append(url)
            continue

        # URL is broken — retry up to MAX_ATTEMPTS times
        current_url = url
        resolved = False
        for attempt in range(1, MAX_ATTEMPTS + 1):
            new_url = _ask_llm_for_replacement(destination_name, current_url, attempt)
            if new_url and is_image_accessible(new_url):
                logger.info("  ✓ Replacement accepted on attempt %d: %s", attempt, new_url)
                fixed.append(new_url)
                resolved = True
                break
            current_url = new_url  # pass the last bad URL to next attempt

        if not resolved:
            logger.warning("  ✗ All %d attempts failed for '%s' image %d — using placeholder",
                           MAX_ATTEMPTS, destination_name, idx + 1)
            fixed.append(FALLBACK_IMAGE)

    return fixed
