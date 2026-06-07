"""Cryptography module for authentication.

This module handles all cryptographic operations related to authentication,
including password hashing, encoding and decoding.
"""

import bcrypt


def hash_password(raw: str) -> str:
    """Hash a raw password string using bcrypt.

    Args:
        raw: The raw password string to hash.

    Returns:
        The hashed password as a UTF-8 encoded string.
    """
    salt = bcrypt.gensalt()
    raw_bytes = raw.encode("utf-8")
    hashed = bcrypt.hashpw(raw_bytes, salt)
    return hashed.decode("utf-8")


def check_password(raw: str, hashed: str) -> bool:
    """Check if a raw password matches a hashed password using bcrypt.

    Args:
        raw: The raw password string to check.
        hashed: The hashed password string to compare against.

    Returns:
        True if the raw password matches the hashed password, False otherwise.
    """
    return bcrypt.checkpw(raw.encode("utf-8"), hashed.encode("utf-8"))
