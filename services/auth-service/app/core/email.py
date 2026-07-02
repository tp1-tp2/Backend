import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import partial

from app.core.config import settings

logger = logging.getLogger(__name__)


def _send_sync(to: str, subject: str, html_body: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        smtp.starttls()
        smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.sendmail(settings.smtp_from, [to], msg.as_string())


async def _send(to: str, subject: str, html_body: str) -> None:
    if not settings.smtp_user:
        logger.info("[MAIL-STUB] To=%s Subject=%r", to, subject)
        return
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, partial(_send_sync, to, subject, html_body))
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", to, exc)
        raise


async def send_recovery_email(to: str, token: str, expires_iso: str) -> None:
    link = f"{settings.frontend_url}/auth/reset-password?token={token}"
    html = f"""
<p>Hola,</p>
<p>Recibiste este correo porque solicitaste recuperar tu contraseña en <strong>ASR Quechua</strong>.</p>
<p><a href="{link}">Restablecer contraseña</a></p>
<p>Este enlace caduca el <strong>{expires_iso} (UTC)</strong>.</p>
<p>Si no realizaste esta solicitud, ignora este mensaje. Tu contraseña no cambiará.</p>
"""
    await _send(to, "Recuperación de contraseña – ASR Quechua", html)
