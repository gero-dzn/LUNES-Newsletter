import json
import logging
from pathlib import Path

import resend

import config

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent
OUTPUT_DIR = ROOT / "output"

# For test sends Resend allows onboarding@resend.dev as sender, but the
# recipient MUST be the email registered with your Resend account.
# For production: verify your domain at resend.com/domains and swap this.
FROM_TEST = "LUNES <onboarding@resend.dev>"


def send_test(
    html_path=None,
    json_path=None,
):
    """Send rendered newsletter to TEST_EMAIL. Returns Resend email id.

    Raises:
        ValueError   — missing API key / email config
        RuntimeError — Resend rejected the request (domain, quota, etc.)
    """
    if not config.RESEND_API_KEY:
        raise ValueError(
            "RESEND_API_KEY está vacía. Agregala en .env y volvé a correr."
        )
    if not config.TEST_EMAIL:
        raise ValueError(
            "TEST_EMAIL está vacía. Agregala en .env y volvé a correr."
        )

    html_path = html_path or OUTPUT_DIR / "issue.html"
    json_path = json_path or OUTPUT_DIR / "issue.json"

    if not Path(html_path).exists():
        raise FileNotFoundError(
            f"HTML no encontrado: {html_path}. Corré render primero."
        )
    if not Path(json_path).exists():
        raise FileNotFoundError(
            f"JSON no encontrado: {json_path}. Corré main.py primero."
        )

    html = Path(html_path).read_text(encoding="utf-8")
    subject = json.loads(
        Path(json_path).read_text(encoding="utf-8")
    )["curation"]["subject"]

    resend.api_key = config.RESEND_API_KEY

    params = {
        "from": FROM_TEST,
        "to": [config.TEST_EMAIL],
        "subject": f"[TEST] {subject}",
        "html": html,
    }

    logger.info("Enviando a %s (from: %s)…", config.TEST_EMAIL, FROM_TEST)

    try:
        result = resend.Emails.send(params)
    except Exception as exc:
        err = str(exc)
        if any(kw in err.lower() for kw in ("domain", "not verified", "403", "422")):
            raise RuntimeError(
                "Dominio no verificado.\n\n"
                "Para test: asegurate de que TEST_EMAIL sea el email con el que\n"
                "  te registraste en Resend (onboarding@resend.dev solo manda al dueño).\n\n"
                "Para producción: verificá tu dominio en https://resend.com/domains\n"
                f"\nDetalle: {exc}"
            ) from exc
        raise RuntimeError(f"Resend error: {exc}") from exc

    email_id = result.get("id") if isinstance(result, dict) else str(result)
    logger.info("Email enviado. id=%s", email_id)
    logger.warning(
        "Enviado desde onboarding@resend.dev (sandbox).\n"
        "  Para producción: verificá tu dominio en https://resend.com/domains"
    )
    return email_id
