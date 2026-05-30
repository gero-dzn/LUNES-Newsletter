"""
resend_confirm.py — Re-envía el mail de confirmación a contactos pendientes.

Un contacto está "pendiente" si aparece con unsubscribed=True en Resend
(fue creado por el flow de suscripción pero aún no hizo click en el link).

Uso:
    python lunes/resend_confirm.py           # dry-run: muestra qué haría
    python lunes/resend_confirm.py --send    # envía de verdad
"""
import argparse
import base64
import hashlib
import hmac
import json
import logging
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
import config

logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
logger = logging.getLogger(__name__)

TOKEN_TTL_MS = 24 * 60 * 60 * 1000   # 24 h
EMAILS_DIR   = Path(__file__).parent.parent / "lunes-web" / "emails"


# ── Token ────────────────────────────────────────────────────────────────────

def _make_token(email: str, contact_id: str) -> str:
    """
    Replica exacta de makeToken() en subscribe.js:
      payload = base64url(JSON.stringify({email, id, exp}))
      sig     = HMAC-SHA256(payload, HMAC_SECRET).hex
      token   = payload + "." + sig
    """
    payload_json = json.dumps(
        {"email": email, "id": contact_id, "exp": int(time.time() * 1000) + TOKEN_TTL_MS},
        separators=(",", ":"),
    )
    # base64url sin padding (igual que Buffer.toString('base64url') en Node.js)
    payload = base64.urlsafe_b64encode(payload_json.encode()).rstrip(b"=").decode()
    sig = hmac.new(
        config.HMAC_SECRET.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}.{sig}"


# ── Resend API ────────────────────────────────────────────────────────────────

def _list_pending() -> list[dict]:
    """Devuelve contactos con unsubscribed=True."""
    resp = requests.get(
        f"https://api.resend.com/audiences/{config.RESEND_AUDIENCE_ID}/contacts",
        headers={"Authorization": f"Bearer {config.RESEND_API_KEY}"},
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"contacts.list {resp.status_code}: {resp.text[:300]}")
    contacts = resp.json().get("data", [])
    return [c for c in contacts if c.get("unsubscribed") is True]


def _send_confirmation(email: str, contact_id: str) -> bool:
    """Genera token fresco y envía mail de confirmación. Devuelve True si OK."""
    token       = _make_token(email, contact_id)
    confirm_url = f"{config.API_BASE_URL}/api/confirm?token={token}"

    tmpl = EMAILS_DIR / "confirm.html"
    if tmpl.exists():
        import re
        html = re.sub(r"\{\{\s*confirm_url\s*\}\}", confirm_url, tmpl.read_text(encoding="utf-8"))
    else:
        html = (
            f'<p style="font-family:monospace">Confirmá tu suscripción a LUNES:<br>'
            f'<a href="{confirm_url}">Confirmar →</a></p>'
        )

    resp = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {config.RESEND_API_KEY}"},
        json={
            "from":    config.FROM_EMAIL,
            "to":      [email],
            "subject": "Confirmá tu suscripción a LUNES",
            "html":    html,
            **({"reply_to": config.REPLY_TO} if config.REPLY_TO else {}),
        },
        timeout=30,
    )
    if not resp.ok:
        logger.error("  ✗ %s → %s %s", email, resp.status_code, resp.text[:120])
        return False
    logger.info("  ✓ %s", email)
    return True


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--send", action="store_true",
                        help="Enviar de verdad (sin este flag es dry-run)")
    args = parser.parse_args()
    dry_run = not args.send

    if dry_run:
        print("\n  === DRY-RUN — pasá --send para enviar de verdad ===\n")

    pending = _list_pending()
    print(f"  Contactos pendientes de confirmación: {len(pending)}\n")

    if not pending:
        return

    sent = 0
    for c in pending:
        if dry_run:
            print(f"  [DRY-RUN] enviaría a: {c['email']}  (id={c['id']})")
        else:
            if _send_confirmation(c["email"], c["id"]):
                sent += 1

    if not dry_run:
        print(f"\n  Enviados: {sent}/{len(pending)}\n")
    else:
        print(f"\n  Pasá --send para enviar a {len(pending)} contacto(s).\n")


if __name__ == "__main__":
    main()
