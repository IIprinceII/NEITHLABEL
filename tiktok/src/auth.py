"""TikTok OAuth token handling. Refreshes the access token using the long-lived refresh token."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import requests

TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"


def _cache_path() -> Path:
    return Path(os.environ.get("TIKTOK_TOKEN_CACHE", ".tokens.json"))


def _load_cache() -> dict | None:
    p = _cache_path()
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return None


def _save_cache(payload: dict) -> None:
    _cache_path().write_text(json.dumps(payload, indent=2))


def get_access_token(force_refresh: bool = False) -> str:
    cached = None if force_refresh else _load_cache()
    if cached and cached.get("expires_at", 0) - 60 > time.time():
        return cached["access_token"]

    client_key = os.environ["TIKTOK_CLIENT_KEY"]
    client_secret = os.environ["TIKTOK_CLIENT_SECRET"]
    refresh_token = (cached or {}).get("refresh_token") or os.environ["TIKTOK_REFRESH_TOKEN"]

    resp = requests.post(
        TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": client_key,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    if "access_token" not in body:
        raise RuntimeError(f"Token refresh failed: {body}")

    body["expires_at"] = int(time.time()) + int(body.get("expires_in", 0))
    _save_cache(body)
    return body["access_token"]
