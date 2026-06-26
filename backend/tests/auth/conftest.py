"""Auth-specific fixtures for signup and login tests.

Provides pre-created user records and payloads covering the various
signup and login scenarios:
- Fresh user (not in DB)
- Unverified existing user (with and without an existing verify token)
- Verified existing user
- OAuth user (password=None)
"""

import datetime
import secrets
import uuid

import jwt as pyjwt
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.constants import (
    RESET_PASSWORD_TOKEN_BYTES,
    RESET_PASSWORD_TOKEN_MAX_DURATION_MINUTES,
    VERIFY_EMAIL_TOKEN_BYTES,
    VERIFY_EMAIL_TOKEN_MAX_DURATION_MINUTES,
)
from src.auth.crypto import hash_password
from src.auth.models import RefreshToken, ResetPasswordToken, VerifyEmailToken
from src.auth.repository import insert_refresh_token
from src.auth.token import JWT_ALGORITHM, generate_access_token, generate_refresh_token
from src.config import get_settings
from src.models import User

# Plaintext password shared by the user fixtures that have a password set.
# Used by login tests to send the correct (or deliberately wrong) credential.
VALID_PASSWORD = "ExistingP@ss1"  # noqa: S105


@pytest_asyncio.fixture
async def signup_payload() -> dict[str, str]:
    """A valid signup request payload for a fresh user."""
    return {
        "username": "newuser",
        "email": "fresh@example.com",
        "password": "ValidP@ss1234",
    }


@pytest_asyncio.fixture
async def alternate_signup_payload() -> dict[str, str]:
    """A signup payload with different credentials than the default fixtures.

    Use when testing the paths that update an existing unverified user's
    username and password (i.e. they differ from what was set during
    fixture creation).
    """
    return {
        "username": "updateduser",
        "email": "unverified@example.com",
        "password": "NewValidP@ss1",
    }


@pytest_asyncio.fixture
async def unverified_user(session: AsyncSession) -> User:
    """A user inserted into the db with ``verified=False`` and no verify-email token row."""
    user = User(
        email="unverified@example.com",
        username="unverifieduser",
        password=hash_password("ValidP@ss1234"),
        verified=False,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


# Forgot-password fixtures


@pytest.fixture
async def forgot_password_payload() -> dict[str, str]:
    """A valid forgot-password payload whose email matches ``forgot_password_user``."""
    return {"email": "forgotpwd@example.com"}


@pytest.fixture
async def nonexistent_forgot_password_payload() -> dict[str, str]:
    """Forgot-password payload with an email not in the database.

    The endpoint always returns 200 regardless (security best practice).
    """
    return {"email": "nobody@example.com"}


@pytest_asyncio.fixture
async def forgot_password_user(session: AsyncSession) -> User:
    """A verified user with no existing ``ResetPasswordToken``.

    Sends forgot-password → token created, email sent.
    """
    user = User(
        email="forgotpwd@example.com",
        username="forgotpwduser",
        password=hash_password("ExistingP@ss1"),
        verified=True,
        verified_at=datetime.datetime.now(tz=datetime.UTC),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def forgot_password_user_with_token(session: AsyncSession) -> User:
    """A user that already has a ``ResetPasswordToken`` whose cooldown has *not* elapsed.

    The token was created moments ago (cooldown is 1 min), so a new
    forgot-password request should NOT rotate the token or send an email.
    """
    user = User(
        email="forgotpwd-token@example.com",
        username="forgotpwdtoken",
        password=hash_password("ExistingP@ss1"),
        verified=True,
        verified_at=datetime.datetime.now(tz=datetime.UTC),
    )
    session.add(user)
    await session.flush()

    token = ResetPasswordToken(
        user_id=user.id,
        token_hash=secrets.token_urlsafe(RESET_PASSWORD_TOKEN_BYTES),
        expires_at=datetime.datetime.now(tz=datetime.UTC)
        + datetime.timedelta(minutes=RESET_PASSWORD_TOKEN_MAX_DURATION_MINUTES),
    )
    session.add(token)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def verify_email_user_with_token(
    session: AsyncSession,
) -> tuple[User, str]:
    """An unverified user with a valid (unexpired) verify-email token.

    Returns ``(user, raw_token)`` so tests can send the raw token in the
    request body and verify side-effects on the user/token records.
    """
    raw_token = secrets.token_urlsafe(VERIFY_EMAIL_TOKEN_BYTES)
    user = User(
        email="verify-valid@example.com",
        username="verifyvalid",
        password=hash_password("ExistingP@ss1"),
        verified=False,
    )
    session.add(user)
    await session.flush()

    token = VerifyEmailToken(
        user_id=user.id,
        token_hash=raw_token,
        expires_at=datetime.datetime.now(tz=datetime.UTC)
        + datetime.timedelta(minutes=VERIFY_EMAIL_TOKEN_MAX_DURATION_MINUTES),
    )
    session.add(token)
    await session.commit()
    await session.refresh(user)
    return user, raw_token


@pytest_asyncio.fixture
async def verify_email_user_expired_token(
    session: AsyncSession,
) -> tuple[User, VerifyEmailToken]:
    """An unverified user whose verify-email token has *expired*.

    The token's ``expires_at`` is set in the past, so the handler should
    raise ``InvalidTokenError`` -> 400.
    Returns ``(user, raw_token)``.
    """
    raw_token = secrets.token_urlsafe(VERIFY_EMAIL_TOKEN_BYTES)
    user = User(
        email="verify-expired@example.com",
        username="verifyexpired",
        password=hash_password("ExistingP@ss1"),
        verified=False,
    )
    session.add(user)
    await session.flush()

    token = VerifyEmailToken(
        user_id=user.id,
        token_hash=raw_token,
        expires_at=datetime.datetime.now(tz=datetime.UTC)
        - datetime.timedelta(minutes=1),
    )
    session.add(token)
    await session.commit()
    await session.refresh(user)
    await session.refresh(token)
    return user, token


@pytest_asyncio.fixture
async def verify_email_orphan_token(session: AsyncSession) -> VerifyEmailToken:
    """A verify-email token whose ``user_id`` does **not** match any user.

    The handler fetches the user after validating the token and should
    raise ``InvalidTokenError`` -> 400 when the user is ``None``.
    Returns the raw token string.
    """
    raw_token = secrets.token_urlsafe(VERIFY_EMAIL_TOKEN_BYTES)
    token = VerifyEmailToken(
        user_id=uuid.uuid4(),  # non-existent user
        token_hash=raw_token,
        expires_at=datetime.datetime.now(tz=datetime.UTC)
        + datetime.timedelta(minutes=VERIFY_EMAIL_TOKEN_MAX_DURATION_MINUTES),
    )
    session.add(token)
    await session.commit()
    await session.refresh(token)
    return token


@pytest_asyncio.fixture
async def forgot_password_user_expired_cooldown(session: AsyncSession) -> User:
    """A user whose ``ResetPasswordToken`` cooldown *has* elapsed.

    The token was created 2 minutes ago (cooldown is 1 min), so a new
    forgot-password request should rotate the token and re-send the email.
    """
    user = User(
        email="forgotpwd-cooldown@example.com",
        username="forgotpwdcooldown",
        password=hash_password("ExistingP@ss1"),
        verified=True,
        verified_at=datetime.datetime.now(tz=datetime.UTC),
    )
    session.add(user)
    await session.flush()

    token = ResetPasswordToken(
        user_id=user.id,
        token_hash=secrets.token_urlsafe(RESET_PASSWORD_TOKEN_BYTES),
        expires_at=datetime.datetime.now(tz=datetime.UTC)
        + datetime.timedelta(hours=24),
        created_at=datetime.datetime.now(tz=datetime.UTC)
        - datetime.timedelta(minutes=2),
    )
    session.add(token)
    await session.commit()
    await session.refresh(user)
    return user


# Reset-password fixtures


@pytest_asyncio.fixture
async def reset_password_user_with_token(
    session: AsyncSession,
) -> tuple[User, str]:
    """A verified user with a valid (not expired, not used) reset password token.

    Returns ``(user, raw_token)`` so tests can send the raw token in the
    request body and verify side-effects on the user/token records.
    """
    raw_token = secrets.token_urlsafe(RESET_PASSWORD_TOKEN_BYTES)
    user = User(
        email="resetpwd-valid@example.com",
        username="resetpwdvalid",
        password=hash_password("ExistingP@ss1"),
        verified=True,
        verified_at=datetime.datetime.now(tz=datetime.UTC),
    )
    session.add(user)
    await session.flush()

    token = ResetPasswordToken(
        user_id=user.id,
        token_hash=raw_token,
        expires_at=datetime.datetime.now(tz=datetime.UTC)
        + datetime.timedelta(minutes=RESET_PASSWORD_TOKEN_MAX_DURATION_MINUTES),
    )
    session.add(token)
    await session.commit()
    await session.refresh(user)
    return user, raw_token


@pytest_asyncio.fixture
async def reset_password_user_expired_token(
    session: AsyncSession,
) -> tuple[User, str]:
    """A verified user whose reset password token has *expired*.

    The token's ``expires_at`` is set in the past, so the handler should
    raise ``InvalidTokenError`` → 400.
    Returns ``(user, raw_token)``.
    """
    raw_token = secrets.token_urlsafe(RESET_PASSWORD_TOKEN_BYTES)
    user = User(
        email="resetpwd-expired@example.com",
        username="resetpwdexpired",
        password=hash_password("ExistingP@ss1"),
        verified=True,
        verified_at=datetime.datetime.now(tz=datetime.UTC),
    )
    session.add(user)
    await session.flush()

    token = ResetPasswordToken(
        user_id=user.id,
        token_hash=raw_token,
        expires_at=datetime.datetime.now(tz=datetime.UTC)
        - datetime.timedelta(minutes=1),
    )
    session.add(token)
    await session.commit()
    await session.refresh(user)
    return user, raw_token


@pytest_asyncio.fixture
async def reset_password_user_used_token(
    session: AsyncSession,
) -> tuple[User, str]:
    """A verified user whose reset password token has *already been used*.

    The token has a ``used_at`` timestamp set, so the handler should
    raise ``InvalidTokenError`` → 400.
    Returns ``(user, raw_token)``.
    """
    raw_token = secrets.token_urlsafe(RESET_PASSWORD_TOKEN_BYTES)
    user = User(
        email="resetpwd-used@example.com",
        username="resetpwdused",
        password=hash_password("ExistingP@ss1"),
        verified=True,
        verified_at=datetime.datetime.now(tz=datetime.UTC),
    )
    session.add(user)
    await session.flush()

    token = ResetPasswordToken(
        user_id=user.id,
        token_hash=raw_token,
        expires_at=datetime.datetime.now(tz=datetime.UTC)
        + datetime.timedelta(minutes=RESET_PASSWORD_TOKEN_MAX_DURATION_MINUTES),
        used_at=datetime.datetime.now(tz=datetime.UTC),
    )
    session.add(token)
    await session.commit()
    await session.refresh(user)
    return user, raw_token


@pytest_asyncio.fixture
async def reset_password_orphan_token(session: AsyncSession) -> str:
    """A reset password token whose ``user_id`` does **not** match any user.

    The handler fetches the user after validating the token and should
    raise ``InvalidTokenError`` → 400 when the user is ``None``.
    Returns the raw token string.
    """
    raw_token = secrets.token_urlsafe(RESET_PASSWORD_TOKEN_BYTES)
    token = ResetPasswordToken(
        user_id=uuid.uuid4(),  # non-existent user
        token_hash=raw_token,
        expires_at=datetime.datetime.now(tz=datetime.UTC)
        + datetime.timedelta(minutes=RESET_PASSWORD_TOKEN_MAX_DURATION_MINUTES),
    )
    session.add(token)
    await session.commit()
    return raw_token


@pytest_asyncio.fixture
async def verified_user(session: AsyncSession) -> User:
    """A user inserted in the db with ``verified=True`` (signup should return 409)."""
    user = User(
        email="verified@example.com",
        username="verifieduser",
        password=hash_password("ExistingP@ss1"),
        verified=True,
        verified_at=datetime.datetime.now(tz=datetime.UTC),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def unverified_user_with_token(session: AsyncSession) -> User:
    """An unverified user that already has a ``VerifyEmailToken`` (cooldown not elapsed).

    The token was created moments ago, so the 1-minute cooldown has *not*
    passed — signup should raise ``VerifyEmailTokenCooldownError`` (400).
    """
    user = User(
        email="tokenuser@example.com",
        username="tokenuser",
        password=hash_password("ExistingP@ss1"),
        verified=False,
    )
    session.add(user)
    await session.flush()

    token = VerifyEmailToken(
        user_id=user.id,
        token_hash=secrets.token_urlsafe(VERIFY_EMAIL_TOKEN_BYTES),
        expires_at=datetime.datetime.now(tz=datetime.UTC)
        + datetime.timedelta(minutes=VERIFY_EMAIL_TOKEN_MAX_DURATION_MINUTES),
    )
    session.add(token)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def access_token_jwt(verified_user: User) -> str:
    """A valid access token JWT for ``verified_user``.

    Useful when a test needs to send an access token where a refresh
    token is expected (e.g. logout with wrong token type).
    """
    return generate_access_token(u_id=verified_user.id)


@pytest_asyncio.fixture
async def expired_access_token_jwt(verified_user: User) -> str:
    """An access token JWT for ``verified_user`` whose ``exp`` is in the past.

    ``decode_access_token`` will raise ``InvalidTokenError`` because the
    signature-verification step detects the expired ``exp`` claim.
    """
    settings = get_settings()
    now = datetime.datetime.now(datetime.UTC)
    payload = {
        "user_id": str(verified_user.id),
        "exp": now - datetime.timedelta(minutes=1),
        "iat": now - datetime.timedelta(hours=1),
        "type": "access",
    }
    return pyjwt.encode(
        payload=payload, key=settings.JWT_SECRET_KEY, algorithm=JWT_ALGORITHM
    )


@pytest_asyncio.fixture
async def refresh_token_jwt(verified_user: User) -> str:
    """A valid refresh token JWT for ``verified_user``.

    The ``type`` claim is ``"refresh"``, so endpoints that expect an
    access token (e.g. ``/auth/me``) will reject it with
    ``InvalidTokenError``.
    """
    rt = generate_refresh_token(u_id=verified_user.id)
    return rt.token_hash


@pytest_asyncio.fixture
async def orphan_access_token_jwt() -> str:
    """A structurally valid access token whose ``user_id`` does **not**
    belong to any user in the database.

    ``decode_access_token`` succeeds, but the subsequent user lookup
    returns ``None``, which triggers ``InvalidTokenError`` in handlers
    like ``handle_me``.
    """
    return generate_access_token(u_id=uuid.uuid4())


@pytest_asyncio.fixture
async def stored_orphan_refresh_token_jwt(session: AsyncSession) -> str:
    """A refresh token persisted in the database for ``orphan user``."""
    token = generate_refresh_token(u_id=uuid.uuid4())
    token = await insert_refresh_token(db=session, token=token)
    await session.refresh(token)
    return token.token_hash


@pytest_asyncio.fixture
async def stored_refresh_token(
    session: AsyncSession, verified_user: User
) -> RefreshToken:
    """A refresh token persisted in the database for ``verified_user``.

    ``handle_refresh`` calls ``get_refresh_token(db, token_hash=...)``,
    so the token must exist in the DB for the success path.
    """
    rt = generate_refresh_token(u_id=verified_user.id)
    rt = await insert_refresh_token(db=session, token=rt)
    await session.commit()
    await session.refresh(rt)
    return rt


@pytest_asyncio.fixture
async def expired_refresh_token_jwt(verified_user: User) -> str:
    """A refresh token JWT for ``verified_user`` whose ``exp`` is in the past.

    ``decode_refresh_token(return_anyway=False)`` will raise
    ``InvalidTokenError`` because the signature-verification step detects
    the expired ``exp`` claim.
    """
    settings = get_settings()
    now = datetime.datetime.now(datetime.UTC)
    payload = {
        "user_id": str(verified_user.id),
        "exp": now - datetime.timedelta(minutes=1),
        "iat": now - datetime.timedelta(hours=1),
        "type": "refresh",
    }
    return pyjwt.encode(
        payload=payload, key=settings.JWT_SECRET_KEY, algorithm=JWT_ALGORITHM
    )


# Login-payload fixtures


@pytest.fixture
async def nonexistent_login_payload() -> dict[str, str]:
    """Login payload for an email that is not in the database.

    No matching user exists -> UserNotFoundError -> 401 INVALID_CREDENTIALS.
    """
    return {"email": "noone@example.com", "password": "DoesntM@tter1"}


@pytest.fixture
async def valid_login_payload() -> dict[str, str]:
    """Login payload that matches ``verified_user`` credentials.

    Correct password + verified user -> successful login -> 200.
    """
    return {"email": "verified@example.com", "password": VALID_PASSWORD}


@pytest.fixture
async def invalid_login_payload() -> dict[str, str]:
    """Login payload with the correct email but a wrong password for ``verified_user``.

    Wrong password -> UserInvalidPasswordError -> 401 INVALID_CREDENTIALS.
    """
    return {"email": "verified@example.com", "password": "WrongP@ssword1"}


@pytest.fixture
async def oauth_login_payload() -> dict[str, str]:
    """Login payload for the OAuth user (``oauth_user``, password is None).

    Password field is None -> UserInvalidPasswordError -> 401 INVALID_CREDENTIALS.
    """
    return {"email": "oauth@example.com", "password": "AnyP@ssword1"}


@pytest_asyncio.fixture
async def oauth_user(session: AsyncSession) -> User:
    """A user who signed up via Google OAuth (password is None, google_id set).

    Attempting to log in with a password should raise UserInvalidPasswordError.
    """
    user = User(
        email="oauth@example.com",
        username="oauthuser",
        google_id="google-sub-12345",
        password=None,
        verified=True,
        verified_at=datetime.datetime.now(tz=datetime.UTC),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def unverified_user_expired_cooldown(session: AsyncSession) -> User:
    """An unverified user whose existing token's cooldown *has* elapsed.

    The token was created 2 minutes ago (cooldown is 1 minute), so signup
    should delete it, create a fresh one, and send the email.
    """
    user = User(
        email="cooldownuser@example.com",
        username="cooldownuser",
        password=hash_password("ExistingP@ss1"),
        verified=False,
    )
    session.add(user)
    await session.flush()

    token = VerifyEmailToken(
        user_id=user.id,
        token_hash=secrets.token_urlsafe(VERIFY_EMAIL_TOKEN_BYTES),
        expires_at=datetime.datetime.now(tz=datetime.UTC)
        + datetime.timedelta(hours=24),
        created_at=datetime.datetime.now(tz=datetime.UTC)
        - datetime.timedelta(minutes=2),
    )
    session.add(token)
    await session.commit()
    await session.refresh(user)
    return user
