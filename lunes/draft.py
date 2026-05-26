import json
import logging
from pathlib import Path

import requests

import config

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent
OUTPUT_DIR = ROOT / "output"


def create_broadcast(html_path=None, json_path=None):
    """Create a Resend Broadcast in DRAFT state. Returns broadcast id.

    Raises:
        ValueError   — missing env vars
        RuntimeError — Resend rejected the request
    """
    for var, val in [
        ("RESEND_API_KEY",    config.RESEND_API_KEY),
        ("RESEND_AUDIENCE_ID", config.RESEND_AUDIENCE_ID),
        ("FROM_EMAIL",        config.FROM_EMAIL),
    ]:
        if not val:
            raise ValueError(f"{var} está vacía. Revisá .env o los Secrets de Actions.")

    html_path = html_path or OUTPUT_DIR / "issue.html"
    json_path = json_path or OUTPUT_DIR / "issue.json"

    payload      = json.loads(Path(json_path).read_text(encoding="utf-8"))
    hook         = payload["curation"]["subject"]
    issue_number = payload.get("issue_number", "#01")
    subject      = f"{hook} · LUNES {issue_number}"
    date_str     = payload["generated_at"][:10]
    html     = Path(html_path).read_text(encoding="utf-8")

    body = {
        "audience_id": config.RESEND_AUDIENCE_ID,
        "from":        config.FROM_EMAIL,
        "subject":     subject,
        "html":        html,
        "name":        f"LUNES {date_str}",
    }
    if config.REPLY_TO:
        body["reply_to"] = config.REPLY_TO

    resp = requests.post(
        "https://api.resend.com/broadcasts",
        headers={"Authorization": f"Bearer {config.RESEND_API_KEY}"},
        json=body,
        timeout=30,
    )

    if not resp.ok:
        raise RuntimeError(
            f"Resend API {resp.status_code}: {resp.text[:400]}"
        )

    broadcast_id = resp.json()["id"]
    logger.info("Broadcast DRAFT creado — id=%s  subject=%r", broadcast_id, subject)
    print(f"\n  Broadcast creado en borrador")
    print(f"  id      : {broadcast_id}")
    print(f"  Asunto  : {subject}")
    print(f"  Revisalo en https://resend.com/broadcasts/{broadcast_id}\n")
    return broadcast_id


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(name)s: %(message)s")
    try:
        create_broadcast()
    except (ValueError, RuntimeError, FileNotFoundError) as exc:
        logger.error("Draft fallido: %s", exc)
        sys.exit(1)
