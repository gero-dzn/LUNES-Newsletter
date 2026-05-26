import json
import logging
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

import config

logger = logging.getLogger(__name__)

ROOT         = Path(__file__).parent
TEMPLATE_DIR = ROOT / "template"
OUTPUT_DIR   = ROOT / "output"


def _issue_date(generated_at: str) -> str:
    try:
        dt = datetime.fromisoformat(generated_at)
    except Exception:
        dt = datetime.now(timezone.utc)
    months = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
    ]
    return f"Lunes {dt.day} · {months[dt.month - 1]} {dt.year}"


def _clean(obj: object) -> object:
    """Recursively unescape HTML entities in string values (fixes &amp; in image URLs)."""
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean(v) for v in obj]
    if isinstance(obj, str):
        return unescape(obj)
    return obj


def render(issue_json_path: Path, issue_number: str = "#01") -> Path:
    """Render output/issue.json → output/issue.html using lunes.html Jinja2 template."""
    raw = json.loads(issue_json_path.read_text(encoding="utf-8"))
    c   = _clean(raw["curation"])

    tldr           = c.get("tldr") or []
    lead           = c.get("lead") or {}
    radar          = c.get("radar") or []
    type_pick      = c.get("type_pick")       # None = rotativa ausente
    ai             = c.get("ai") or []
    craft          = c.get("craft")
    try_this       = c.get("try_this") or {}
    opportunity    = c.get("opportunity")
    spotted        = c.get("spotted")
    awwwards       = c.get("awwwards")

    preheader_text = " · ".join(tldr[:2]) if tldr else ""

    env  = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    tmpl = env.get_template("lunes.html")

    html = tmpl.render(
        preheader_text=preheader_text,
        issue_number=issue_number,
        issue_date=_issue_date(raw.get("generated_at", "")),
        tldr=tldr,
        lead=lead,
        radar=radar,
        type_pick=type_pick,
        ai=ai,
        craft=craft,
        try_this=try_this,
        opportunity=opportunity,
        spotted=spotted,
        awwwards=awwwards,
        unsubscribe_url="#",
        web_url="#",
    )

    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / "issue.html"
    out_path.write_text(html, encoding="utf-8")

    sections = sum([
        1 if lead.get("url") else 0,
        len(radar),
        1 if type_pick else 0,
        len(ai),
        1 if craft else 0,
        1 if try_this.get("url") else 0,
        1 if opportunity else 0,
        len(spotted) if spotted else 0,
        1 if awwwards else 0,
    ])
    logger.info("Render done: %d sections → %s (%d KB)", sections, out_path, len(html) // 1024)
    return out_path
