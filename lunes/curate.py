import json
import logging
import re
from typing import Optional

import anthropic

import config

logger = logging.getLogger(__name__)

# Core keys that must always be present in the curation response
REQUIRED_KEYS = {"subject", "tldr", "lead", "radar", "ai", "try_this"}


def _format_articles(articles: list[dict]) -> str:
    """Format fetched articles into the prompt input, grouped by section."""
    by_section: dict[str, list[dict]] = {}
    for a in articles:
        by_section.setdefault(a["section"], []).append(a)

    section_labels = {
        "diseño":    "DISEÑO",
        "ia":        "IA",
        "awwwards":  "AWWWARDS — Sites of the Day (ubicar en sección awwwards del output)",
    }

    blocks = []
    counter = 1
    for section_key in ("diseño", "ia", "awwwards"):
        items = by_section.get(section_key, [])
        if not items:
            continue
        label = section_labels.get(section_key, section_key.upper())
        blocks.append(f"=== {label} ({len(items)} ítems) ===")
        for a in items:
            date_str = (a.get("date") or "")[:10] or "sin fecha"
            image_line = f"\n   Imagen: {a['image']}" if a.get("image") else ""
            blocks.append(
                f"{counter}. {a['source']} | {date_str}\n"
                f"   {a['title']}\n"
                f"   {a['summary'][:400]}\n"
                f"   URL: {a['url']}"
                f"{image_line}"
            )
            counter += 1
        blocks.append("")  # blank line between sections

    return "\n\n".join(blocks)


def _extract_json(text: str) -> str:
    """Strip markdown fences and return the JSON string."""
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        return fenced.group(1)
    brace = re.search(r"\{.*\}", text, re.DOTALL)
    if brace:
        return brace.group(0)
    return text


def _safe_list_len(val: Optional[object]) -> int:
    return len(val) if isinstance(val, list) else 0


def curate(articles: list[dict]) -> dict:
    """Send articles to Claude and return structured curation dict.

    Returns dict matching the schema in config.CURATION_PROMPT.
    Rotative sections (type_pick, craft, opportunity, spotted, awwwards) may be null.
    Raises ValueError on unparseable or structurally incomplete response.
    """
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    user_content = _format_articles(articles)

    n_diseno  = sum(1 for a in articles if a["section"] == "diseño")
    n_ia      = sum(1 for a in articles if a["section"] == "ia")
    n_aww     = sum(1 for a in articles if a["section"] == "awwwards")
    logger.info(
        "Calling Claude %s — diseño:%d  ia:%d  awwwards:%d",
        config.ANTHROPIC_MODEL, n_diseno, n_ia, n_aww,
    )

    message = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=4096,
        system=config.CURATION_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    raw = message.content[0].text.strip()
    logger.debug("Raw response (%d chars): %.200s…", len(raw), raw)

    json_str = _extract_json(raw)

    try:
        result = json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Claude returned invalid JSON.\n\nRaw response:\n{raw[:800]}\n\nError: {exc}"
        ) from exc

    missing = REQUIRED_KEYS - set(result.keys())
    if missing:
        raise ValueError(
            f"Response missing required keys: {missing}\n\nGot: {list(result.keys())}"
        )

    if len(result.get("tldr", [])) != 4:
        logger.warning("TL;DR has %d bullets (expected 4)", len(result.get("tldr", [])))

    logger.info(
        "Curation done — radar:%d  ai:%d  spotted:%d  awwwards:%s  subject=%r",
        _safe_list_len(result.get("radar")),
        _safe_list_len(result.get("ai")),
        _safe_list_len(result.get("spotted")),
        "sí" if result.get("awwwards") else "null",
        result.get("subject", ""),
    )
    return result
