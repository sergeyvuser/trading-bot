"""Crypto utilities. Helpers for signature generation and other crypto operations."""

from typing import Optional
import hmac
import hashlib


def generate_signature(key: str, secret: str, payload: Optional[str] = None) -> str:
    if payload:
        return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return hmac.new(secret.encode(), key.encode(), hashlib.sha256).hexdigest()
