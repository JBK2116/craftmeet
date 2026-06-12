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

from src.auth.constants import (
    RESET_PASSWORD_TOKEN_MAX_DURATION_MINUTES,
    VERIFY_EMAIL_TOKEN_MAX_DURATION_MINUTES,
)
from src.auth.exceptions import EmailDeliveryError
from src.auth.models import ResetPasswordToken, VerifyEmailToken
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
    font_stack = (
        "'Figtree','Figtree Variable',-apple-system,BlinkMacSystemFont,"
        "'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
    )
    logo_svg = (
        '<svg width="34" height="34" viewBox="0 0 100 100" '
        'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Craftmeet" '
        'style="display:block;">'
        '<path fill-rule="evenodd" fill="#005153" '
        'd="M 18 5 L 76 5 Q 88 5 88 17 L 88 61 Q 88 73 76 73 L 36 73 L 19 90 '
        "L 25 73 L 18 73 Q 6 73 6 61 L 6 17 Q 6 5 18 5 Z M 18 14 L 76 14 Q 80 14 "
        "80 18 L 80 32 Q 80 36 76 36 L 18 36 Q 14 36 14 32 L 14 18 Q 14 14 18 14 Z "
        "M 18 41 L 40 41 Q 44 41 44 45 L 44 63 Q 44 67 40 67 L 18 67 Q 14 67 14 63 "
        "L 14 45 Q 14 41 18 41 Z M 54 41 L 76 41 Q 80 41 80 45 L 80 63 Q 80 67 76 67 "
        "L 54 67 Q 50 67 50 63 L 50 45 Q 50 41 54 41 Z M 65 48 L 67 52 L 71 54 L 67 56 "
        'L 65 60 L 63 56 L 59 54 L 63 52 Z"/></svg>'
    )
    html_content = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="color-scheme" content="light only">
  <meta name="supported-color-schemes" content="light">
  <title>Verify your Craftmeet account</title>
</head>
<body style="margin:0;padding:0;background-color:#f5f7f9;-webkit-text-size-adjust:100%;">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;font-size:1px;line-height:1px;color:#f5f7f9;">
    Confirm your email address to activate your Craftmeet account.&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;
  </div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f5f7f9;">
    <tr>
      <td align="center" style="padding:40px 20px;">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:600px;">
          <tr>
            <td align="center" style="padding:0 0 24px 0;">
              <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td style="vertical-align:middle;padding-right:10px;">{logo_svg}</td>
                  <td style="vertical-align:middle;font-family:{font_stack};font-size:22px;font-weight:700;letter-spacing:-0.02em;color:#005153;">Craftmeet</td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="background-color:#ffffff;border:1px solid #d8dbdf;border-radius:16px;padding:44px 40px;">
              <h1 style="margin:0 0 10px 0;font-family:{font_stack};font-size:22px;line-height:1.3;font-weight:600;letter-spacing:-0.02em;color:#0f1417;">Verify your email address</h1>
              <p style="margin:0 0 28px 0;font-family:{font_stack};font-size:15px;line-height:1.6;color:#6d7277;">Thanks for signing up. Confirm your email address to activate your account and start running better meetings.</p>
              <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td align="center" style="border-radius:10px;background-color:#005153;">
                    <a href="{email_link}" target="_blank" style="display:inline-block;padding:13px 30px;font-family:{font_stack};font-size:15px;font-weight:600;line-height:1;color:#ffffff;text-decoration:none;border-radius:10px;">Verify my account</a>
                  </td>
                </tr>
              </table>
              <p style="margin:28px 0 0 0;font-family:{font_stack};font-size:13px;line-height:1.6;color:#6d7277;">This link expires in <strong style="color:#0f1417;">{expiry_hours} hours</strong>. If the button doesn't work, copy and paste this URL into your browser:</p>
              <p style="margin:8px 0 0 0;font-family:{font_stack};font-size:13px;line-height:1.6;word-break:break-all;">
                <a href="{email_link}" target="_blank" style="color:#005153;text-decoration:underline;">{email_link}</a>
              </p>
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr><td style="padding:28px 0 0 0;border-top:1px solid #d8dbdf;"></td></tr>
              </table>
              <p style="margin:24px 0 0 0;font-family:{font_stack};font-size:12px;line-height:1.6;color:#6d7277;">If you didn't create a Craftmeet account, you can safely ignore this email.</p>
            </td>
          </tr>
          <tr>
            <td align="center" style="padding:24px 0 0 0;font-family:{font_stack};font-size:12px;line-height:1.6;color:#6d7277;">
              &copy; Craftmeet &middot; Real-time structured meetings
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
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


async def send_reset_password_email(user: User, token: ResetPasswordToken) -> None:
    """
    Send a password reset email to a user.

    Sends an HTML-formatted email to the specified user containing a password
    reset link with an embedded token. The link directs to the appropriate frontend
    URL based on the environment (development or production).

    Args:
        user: The User object containing the email address to send to.
        token: The ResetPasswordToken object containing the token hash for verification.

    Raises:
        EmailDeliveryError: If the email fails to send via SendGrid API.
    """
    base_url = "http://localhost:5173" if settings.IS_DEV else "https://craftmeet.com"
    email_link = f"{base_url}/reset-password?token={token.token_hash}"
    expiry_minutes = RESET_PASSWORD_TOKEN_MAX_DURATION_MINUTES

    subject = "Reset your Craftmeet password"
    font_stack = (
        "'Figtree','Figtree Variable',-apple-system,BlinkMacSystemFont,"
        "'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
    )
    logo_svg = (
        '<svg width="34" height="34" viewBox="0 0 100 100" '
        'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Craftmeet" '
        'style="display:block;">'
        '<path fill-rule="evenodd" fill="#005153" '
        'd="M 18 5 L 76 5 Q 88 5 88 17 L 88 61 Q 88 73 76 73 L 36 73 L 19 90 '
        "L 25 73 L 18 73 Q 6 73 6 61 L 6 17 Q 6 5 18 5 Z M 18 14 L 76 14 Q 80 14 "
        "80 18 L 80 32 Q 80 36 76 36 L 18 36 Q 14 36 14 32 L 14 18 Q 14 14 18 14 Z "
        "M 18 41 L 40 41 Q 44 41 44 45 L 44 63 Q 44 67 40 67 L 18 67 Q 14 67 14 63 "
        "L 14 45 Q 14 41 18 41 Z M 54 41 L 76 41 Q 80 41 80 45 L 80 63 Q 80 67 76 67 "
        "L 54 67 Q 50 67 50 63 L 50 45 Q 50 41 54 41 Z M 65 48 L 67 52 L 71 54 L 67 56 "
        'L 65 60 L 63 56 L 59 54 L 63 52 Z"/></svg>'
    )
    html_content = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="color-scheme" content="light only">
  <meta name="supported-color-schemes" content="light">
  <title>Reset your Craftmeet password</title>
</head>
<body style="margin:0;padding:0;background-color:#f5f7f9;-webkit-text-size-adjust:100%;">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;font-size:1px;line-height:1px;color:#f5f7f9;">
    Reset your Craftmeet password by clicking the link below.&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;
  </div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f5f7f9;">
    <tr>
      <td align="center" style="padding:40px 20px;">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:600px;">
          <tr>
            <td align="center" style="padding:0 0 24px 0;">
              <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td style="vertical-align:middle;padding-right:10px;">{logo_svg}</td>
                  <td style="vertical-align:middle;font-family:{font_stack};font-size:22px;font-weight:700;letter-spacing:-0.02em;color:#005153;">Craftmeet</td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="background-color:#ffffff;border:1px solid #d8dbdf;border-radius:16px;padding:44px 40px;">
              <h1 style="margin:0 0 10px 0;font-family:{font_stack};font-size:22px;line-height:1.3;font-weight:600;letter-spacing:-0.02em;color:#0f1417;">Reset your password</h1>
              <p style="margin:0 0 28px 0;font-family:{font_stack};font-size:15px;line-height:1.6;color:#6d7277;">We received a request to reset the password for your Craftmeet account. Click the button below to choose a new password.</p>
              <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td align="center" style="border-radius:10px;background-color:#005153;">
                    <a href="{email_link}" target="_blank" style="display:inline-block;padding:13px 30px;font-family:{font_stack};font-size:15px;font-weight:600;line-height:1;color:#ffffff;text-decoration:none;border-radius:10px;">Reset my password</a>
                  </td>
                </tr>
              </table>
              <p style="margin:28px 0 0 0;font-family:{font_stack};font-size:13px;line-height:1.6;color:#6d7277;">This link expires in <strong style="color:#0f1417;">{expiry_minutes} minutes</strong>. If the button doesn't work, copy and paste this URL into your browser:</p>
              <p style="margin:8px 0 0 0;font-family:{font_stack};font-size:13px;line-height:1.6;word-break:break-all;">
                <a href="{email_link}" target="_blank" style="color:#005153;text-decoration:underline;">{email_link}</a>
              </p>
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr><td style="padding:28px 0 0 0;border-top:1px solid #d8dbdf;"></td></tr>
              </table>
              <p style="margin:24px 0 0 0;font-family:{font_stack};font-size:12px;line-height:1.6;color:#6d7277;">If you didn't request a password reset, you can safely ignore this email. Your password will not change.</p>
            </td>
          </tr>
          <tr>
            <td align="center" style="padding:24px 0 0 0;font-family:{font_stack};font-size:12px;line-height:1.6;color:#6d7277;">
              &copy; Craftmeet &middot; Real-time structured meetings
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
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
        logger.exception("Failed to send reset password email to %s", user.email)
        raise EmailDeliveryError(user.email) from e
