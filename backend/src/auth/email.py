"""
Module for handling email sending functionality in the authentication system.

This module provides utilities for sending various authentication-related emails,
including email verification, password reset, and other account-related notifications.
"""

import asyncio
import logging

from sendgrid.helpers.mail.email import Email
from sendgrid.helpers.mail.mail import Mail
from sendgrid.sendgrid import SendGridAPIClient

from src.auth.constants import VERIFY_EMAIL_TOKEN_MAX_DURATION_MINUTES
from src.auth.exceptions import EmailDeliveryError
from src.auth.models import VerifyEmailToken
from src.config import get_settings
from src.models import User

settings = get_settings()

logger = logging.getLogger(__name__)


async def send_verification_email(user: User, token: VerifyEmailToken) -> None:
    """
    Send a verification email to a user.

    Sends an HTML-formatted email to the specified user containing a verification
    link with an embedded token. The link directs to the appropriate frontend URL
    based on the environment (development or production).

    Args:
        user: The User object containing the email address to send to.
        token: The VerifyEmailToken object containing the token hash for verification.

    Raises:
        EmailDeliveryError: If the email fails to send via SendGrid API.
    """
    base_url = "http://localhost:5173" if settings.IS_DEV else "https://craftmeet.com"
    email_link = f"{base_url}/verify-email?token={token.token_hash}"
    expiry_hours = VERIFY_EMAIL_TOKEN_MAX_DURATION_MINUTES // 60

    subject = "Verify your Craftmeet account"
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #f5f5f8; padding: 40px 20px;">
      <div style="background-color: #ffffff; border-radius: 12px; padding: 40px; text-align: center; border: 1px solid #e5e5ea;">
        <h1 style="color: #006d6b; font-size: 26px; font-weight: bold; margin: 0 0 8px;">Craftmeet</h1>
        <hr style="border: none; border-top: 1px solid #e5e5ea; margin: 24px 0;" />
        <h2 style="color: #1a1a24; font-size: 20px; margin: 0 0 12px;">Verify your email address</h2>
        <p style="color: #7a7a8a; font-size: 15px; margin: 0 0 32px;">Thanks for signing up. Click the button below to verify your account and get started.</p>
        <a href="{email_link}" style="background-color: #006d6b; color: #ffffff; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 15px; display: inline-block;">Verify my account</a>
        <p style="color: #7a7a8a; font-size: 13px; margin: 24px 0 0;">This link expires in <strong style="color: #1a1a24;">{expiry_hours} hours</strong>.</p>
        <p style="color: #b0b0c0; font-size: 12px; margin: 12px 0 0;">If you didn't create a Craftmeet account, you can safely ignore this email.</p>
      </div>
    </div>
    """
    message = Mail(
        from_email=Email(settings.SENDGRID_EMAIL_FROM, "Craftmeet"),
        to_emails=user.email,
        subject=subject,
        html_content=html_content,
    )
    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        await asyncio.to_thread(sg.send, message)
    except Exception as e:
        logger.exception("Failed to send verification email to %s", user.email)
        raise EmailDeliveryError(user.email) from e
