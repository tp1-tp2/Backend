import logging

logger = logging.getLogger(__name__)


async def send_confirmation(to: str, user_id: str) -> None:
    # TODO: replace with real SMTP / SendGrid call
    logger.info("Registration confirmation → %s (user_id=%s)", to, user_id)


async def send_verification_link(to: str, token: str, link_type: str) -> None:
    # TODO: replace with real SMTP / SendGrid call
    logger.info(
        "Email-change verification [%s] → %s (token=%s)", link_type, to, token
    )
