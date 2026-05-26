import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import fetch
import curate
import render
import send

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger("main")

ROOT       = Path(__file__).parent
OUTPUT_DIR = ROOT / "output"


def _curated_items_for_enrich(curation: dict) -> List[dict]:
    """Flatten all curated items that have an image field into a single list."""
    items = []
    # Lead
    lead = curation.get("lead") or {}
    if lead.get("url"):
        items.append(lead)
    # Radar
    for it in (curation.get("radar") or []):
        if it.get("url"):
            items.append(it)
    # AI
    for it in (curation.get("ai") or []):
        if it.get("url"):
            items.append(it)
    # Try this
    try_this = curation.get("try_this") or {}
    if try_this.get("url"):
        items.append(try_this)
    # Type pick (rotativa)
    type_pick = curation.get("type_pick") or {}
    if type_pick.get("url"):
        items.append(type_pick)
    # Awwwards featured — excluded from enrich; Awwwards provides valid screenshots
    return items


def _print_summary(curation: dict, n_fetched: int) -> None:
    sep = "─" * 64
    lead     = curation.get("lead") or {}
    radar    = curation.get("radar") or []
    ai       = curation.get("ai") or []
    try_this = curation.get("try_this") or {}
    awwwards = curation.get("awwwards") or {}

    print(f"\n{sep}")
    print(f"  LUNES  ·  {datetime.now().strftime('%Y-%m-%d')}  ·  {n_fetched} artículos fetched")
    print(sep)
    print(f"  Asunto : {curation.get('subject', '')}")
    print(f"\n  TL;DR")
    for bullet in (curation.get("tldr") or []):
        print(f"    • {bullet}")

    print(f"\n  Lead")
    if lead.get("title"):
        img = "🖼" if lead.get("image") else "—"
        print(f"    {img}  [{lead.get('kind','?')}] {lead['title']}  —  {lead.get('source','')}")

    print(f"\n  Radar ({len(radar)} notas)")
    for s in radar:
        img = "🖼" if s.get("image") else "—"
        print(f"    {img}  {s.get('title','')}  —  {s.get('source','')}")
        if s.get("take"):
            print(f"        take: {s['take']}")

    print(f"\n  IA ({len(ai)} notas)")
    for s in ai:
        img = "🖼" if s.get("image") else "—"
        print(f"    {img}  {s.get('title','')}  —  {s.get('source','')}")

    if try_this.get("title"):
        img = "🖼" if try_this.get("image") else "—"
        print(f"\n  Try this  {img}  {try_this['title']}")

    rotativas = []
    if curation.get("type_pick"):
        rotativas.append("type_pick")
    if curation.get("craft"):
        rotativas.append("craft")
    if curation.get("opportunity"):
        rotativas.append("opportunity")
    if curation.get("spotted"):
        rotativas.append(f"spotted ({len(curation['spotted'])})")
    if awwwards.get("featured"):
        rotativas.append("awwwards")
    if rotativas:
        print(f"\n  Rotativas: {', '.join(rotativas)}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="LUNES newsletter generator")
    parser.add_argument("--debug",        action="store_true", help="Verbose logging")
    parser.add_argument("--send",         action="store_true", help="Render + send preview to TEST_EMAIL")
    parser.add_argument("--issue-number", default="#01",       help="Issue number (e.g. #03)")
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # ── Fase 1: Fetch ────────────────────────────────────────────────────────
    logger.info("── Fase 1: fetch ─────────────────────────────────────────")
    articles = fetch.fetch_articles()

    if not articles:
        logger.error("No articles found. Check feeds and WINDOW_DAYS in config.py.")
        sys.exit(1)

    # ── Fase 2: Curate ───────────────────────────────────────────────────────
    logger.info("── Fase 2: curate ────────────────────────────────────────")
    try:
        curation = curate.curate(articles)
    except ValueError as exc:
        logger.error("Curación fallida: %s", exc)
        sys.exit(1)

    # ── Fase 2b: Enrich images (curated items only) ──────────────────────────
    logger.info("── Fase 2b: enrich images ────────────────────────────────")
    enrich_items = _curated_items_for_enrich(curation)
    fetch.enrich_images(enrich_items)

    # ── Save output/issue.json ───────────────────────────────────────────────
    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / "issue.json"

    payload = {
        "generated_at":     datetime.now(timezone.utc).isoformat(),
        "issue_number":     args.issue_number,
        "articles_fetched": len(articles),
        "articles_raw":     articles,
        "curation":         curation,
    }

    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Saved → %s", out_path)

    # ── Fase 3: Render ───────────────────────────────────────────────────────
    logger.info("── Fase 3: render ────────────────────────────────────────")
    html_path = render.render(out_path, issue_number=args.issue_number)

    # ── Summary ──────────────────────────────────────────────────────────────
    _print_summary(curation, len(articles))
    print(f"  output/issue.json  ({out_path.stat().st_size // 1024} KB)")
    print(f"  output/issue.html  ({html_path.stat().st_size // 1024} KB)\n")

    # ── Fase 4: Send (optional) ──────────────────────────────────────────────
    if args.send:
        logger.info("── Fase 4: send ──────────────────────────────────────────")
        try:
            email_id = send.send_test(html_path=html_path, json_path=out_path)
            print(f"  Email enviado → id={email_id}\n")
        except (ValueError, RuntimeError, FileNotFoundError) as exc:
            logger.error("Envío fallido: %s", exc)
            sys.exit(1)


if __name__ == "__main__":
    main()
