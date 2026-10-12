import json
import logging
import time
from typing import Any, Optional

import anthropic

import config

logger = logging.getLogger(__name__)

# Core keys that must always be present in the curation response
REQUIRED_KEYS = {"subject", "tldr", "lead", "radar", "ai", "try_this"}

MAX_ATTEMPTS = 3          # llamadas a Claude antes de rendirse
MAX_TOKENS   = 8192       # una edición ronda 3k tokens; margen para no truncar

TOOL_NAME = "emit_edition"

# ---------------------------------------------------------------------------
# Schema de la edición. Se le pasa a Claude como input_schema de una tool y se
# fuerza su uso (tool_choice), así la API devuelve JSON parseado y válido en vez
# de texto libre que haya que recortar con regex.
# ---------------------------------------------------------------------------
_STR         = {"type": "string"}
_INT         = {"type": "integer"}
_STR_OR_NULL = {"type": ["string", "null"]}


def _obj(props: dict[str, Any], required: Optional[list[str]] = None, nullable: bool = False) -> dict:
    schema: dict[str, Any] = {
        "type": ["object", "null"] if nullable else "object",
        "properties": props,
        "required": required if required is not None else list(props.keys()),
    }
    return schema


def _arr(item: dict, nullable: bool = False) -> dict:
    return {"type": ["array", "null"] if nullable else "array", "items": item}


CURATION_SCHEMA = _obj(
    {
        "subject": _STR,
        "tldr":    {"type": "array", "items": _STR, "minItems": 4, "maxItems": 4},
        "lead": _obj({
            "title":   _STR,
            "kind":    {"type": "string", "enum": ["sitio", "identidad", "proyecto"]},
            "source":  _STR,
            "mins":    _INT,
            "summary": _STR,
            "url":     _STR,
            "image":   _STR_OR_NULL,
            "credit":  _STR,
        }),
        "radar": _arr(_obj({
            "source":  _STR,
            "mins":    _INT,
            "title":   _STR,
            "take":    _STR,
            "summary": _STR,
            "url":     _STR,
            "image":   _STR_OR_NULL,
            "credit":  _STR,
        })),
        "type_pick": _obj({
            "name":  _STR,
            "note":  _STR,
            "url":   _STR,
            "image": _STR_OR_NULL,
        }, nullable=True),
        "ai": _arr(_obj({
            "source":  _STR,
            "mins":    _INT,
            "title":   _STR,
            "summary": _STR,
            "url":     _STR,
            "image":   _STR_OR_NULL,
            "credit":  _STR,
        })),
        "craft": _obj({
            "title":   _STR,
            "summary": _STR,
            "url":     _STR,
        }, nullable=True),
        "try_this": _obj({
            "title":   _STR,
            "summary": _STR,
            "url":     _STR,
            "image":   _STR_OR_NULL,
            "credit":  _STR,
        }),
        "opportunity": _obj({
            "title":    _STR,
            "org":      _STR,
            "deadline": _STR,
            "url":      _STR,
        }, nullable=True),
        "spotted": _arr(_obj({"title": _STR, "url": _STR}), nullable=True),
        "awwwards": _obj({
            "featured": _obj({
                "name":   _STR,
                "author": _STR,
                "url":    _STR,
                "image":  _STR,
            }),
            "more": _arr(_obj({"name": _STR, "url": _STR})),
        }, nullable=True),
    }
)

CURATION_TOOL = {
    "name": TOOL_NAME,
    "description": (
        "Entrega la edición curada de LUNES. Llamar exactamente una vez con la "
        "edición completa. Las secciones rotativas sin material van en null."
    ),
    "input_schema": CURATION_SCHEMA,
}


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


def _safe_list_len(val: Optional[object]) -> int:
    return len(val) if isinstance(val, list) else 0


def _call_claude(client: anthropic.Anthropic, user_content: str) -> dict:
    """One request to Claude. Returns the tool input dict or raises ValueError."""
    message = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=MAX_TOKENS,
        system=config.CURATION_PROMPT,
        tools=[CURATION_TOOL],
        tool_choice={"type": "tool", "name": TOOL_NAME},
        messages=[{"role": "user", "content": user_content}],
    )

    if message.stop_reason == "max_tokens":
        raise ValueError(
            f"Claude response truncated at max_tokens={MAX_TOKENS} "
            f"(output tokens: {message.usage.output_tokens})"
        )

    for block in message.content:
        if block.type == "tool_use" and block.name == TOOL_NAME:
            result = block.input
            break
    else:
        kinds = [b.type for b in message.content]
        raise ValueError(f"Claude returned no {TOOL_NAME} tool call (blocks: {kinds})")

    if not isinstance(result, dict):
        raise ValueError(f"Tool input is not an object: {type(result).__name__}")

    missing = REQUIRED_KEYS - set(result.keys())
    if missing:
        raise ValueError(
            f"Response missing required keys: {missing}\n\nGot: {list(result.keys())}"
        )

    logger.debug("Raw curation (%d chars)", len(json.dumps(result, ensure_ascii=False)))
    return result


def curate(articles: list[dict]) -> dict:
    """Send articles to Claude and return structured curation dict.

    Returns dict matching the schema in config.CURATION_PROMPT / CURATION_SCHEMA.
    Rotative sections (type_pick, craft, opportunity, spotted, awwwards) may be null.
    Retries up to MAX_ATTEMPTS on malformed responses.
    Raises ValueError if every attempt fails.
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

    last_exc: Optional[Exception] = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            result = _call_claude(client, user_content)
            break
        except ValueError as exc:
            last_exc = exc
            logger.warning("Curation attempt %d/%d failed: %s", attempt, MAX_ATTEMPTS, exc)
            if attempt < MAX_ATTEMPTS:
                time.sleep(2 * attempt)
    else:
        raise ValueError(f"Curation failed after {MAX_ATTEMPTS} attempts: {last_exc}") from last_exc

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
