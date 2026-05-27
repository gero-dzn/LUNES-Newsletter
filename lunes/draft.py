import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

import config

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent
OUTPUT_DIR = ROOT / "output"


def _next_send_utc() -> datetime:
    """Return today at SEND_HOUR_UTC; push to tomorrow if we're already past that hour."""
    now = datetime.now(timezone.utc)
    candidate = now.replace(hour=config.SEND_HOUR_UTC, minute=0, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def create_broadcast(html_path=None, json_path=None) -> tuple[str, str]:
    """Create a Resend Broadcast in DRAFT state. Returns (broadcast_id, subject)."""
    for var, val in [
        ("RESEND_API_KEY",     config.RESEND_API_KEY),
        ("RESEND_AUDIENCE_ID", config.RESEND_AUDIENCE_ID),
        ("FROM_EMAIL",         config.FROM_EMAIL),
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
    html         = Path(html_path).read_text(encoding="utf-8")

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
        raise RuntimeError(f"Resend API {resp.status_code}: {resp.text[:400]}")

    broadcast_id = resp.json()["id"]
    logger.info("Broadcast DRAFT creado — id=%s  subject=%r", broadcast_id, subject)
    return broadcast_id, subject


def schedule_broadcast(broadcast_id: str, scheduled_at: datetime) -> None:
    """Schedule an existing DRAFT broadcast. Uses POST /broadcasts/{id}/send with scheduled_at."""
    iso = scheduled_at.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    resp = requests.post(
        f"https://api.resend.com/broadcasts/{broadcast_id}/send",
        headers={"Authorization": f"Bearer {config.RESEND_API_KEY}"},
        json={"scheduled_at": iso},
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(
            f"Resend schedule API {resp.status_code}: {resp.text[:400]}"
        )
    logger.info("Broadcast programado → %s UTC (id=%s)", iso[:16], broadcast_id)


def notify_ready(broadcast_id: str, scheduled_at: datetime, subject: str) -> None:
    """Send a notification email to the editor. Non-fatal: logs warning on failure."""
    if not config.NOTIFY_EMAIL:
        logger.warning("NOTIFY_EMAIL no configurada, omitiendo notificación.")
        return

    art_offset = -3
    art_hour   = (scheduled_at.hour + art_offset) % 24
    art_time   = f"{art_hour:02d}:{scheduled_at.minute:02d}"
    utc_time   = scheduled_at.strftime("%H:%M")
    panel_url  = f"https://resend.com/broadcasts/{broadcast_id}"

    html_body = (
        f'<p style="font-family:monospace;font-size:14px;color:#211B17;line-height:1.8">'
        f'<strong>Borrador LUNES listo.</strong><br><br>'
        f'Asunto: {subject}<br>'
        f'Sale a las <strong>{art_time} ART</strong> ({utc_time} UTC).<br><br>'
        f'<a href="{panel_url}" style="color:#FF4D12">Revisá el borrador en Resend →</a>'
        f'</p>'
    )

    resp = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {config.RESEND_API_KEY}"},
        json={
            "from":    config.FROM_EMAIL,
            "to":      [config.NOTIFY_EMAIL],
            "subject": f"LUNES · borrador listo, sale {art_time} ART",
            "html":    html_body,
        },
        timeout=30,
    )
    if not resp.ok:
        logger.warning("Notificación no enviada: %s %s", resp.status_code, resp.text[:200])
        return
    logger.info("Notificación enviada → %s", config.NOTIFY_EMAIL)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(name)s: %(message)s")
    try:
        broadcast_id, subject = create_broadcast()
        send_at = _next_send_utc()
        schedule_broadcast(broadcast_id, send_at)
        notify_ready(broadcast_id, send_at, subject)

        art_hour = (send_at.hour - 3) % 24
        print(f"\n  Broadcast programado")
        print(f"  id     : {broadcast_id}")
        print(f"  Asunto : {subject}")
        print(f"  Sale   : {art_hour:02d}:00 ART  ({send_at.strftime('%H:%M')} UTC)")
        print(f"  Panel  : {f'https://resend.com/broadcasts/{broadcast_id}'}\n")
    except (ValueError, RuntimeError, FileNotFoundError) as exc:
        logger.error("Draft fallido: %s", exc)
        sys.exit(1)
