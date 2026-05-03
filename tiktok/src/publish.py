"""TikTok Content Posting API client.

Implements the FILE_UPLOAD flow:
  1. init          -> get publish_id + signed upload_url
  2. PUT chunks    -> stream the video to TikTok storage
  3. poll status   -> wait for PUBLISH_COMPLETE (or surface failure)

Reference: https://developers.tiktok.com/doc/content-posting-api-reference-direct-post
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

import requests

API_BASE = "https://open.tiktokapis.com/v2"
INIT_URL = f"{API_BASE}/post/publish/video/init/"
STATUS_URL = f"{API_BASE}/post/publish/status/fetch/"

# TikTok requires chunks of 5MB-64MB (last chunk may be smaller).
CHUNK_SIZE = 10 * 1024 * 1024


@dataclass
class PublishResult:
    publish_id: str
    status: str
    publicaly_available_post_id: str | None = None
    fail_reason: str | None = None


def _auth_headers(access_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
    }


def init_video_post(
    access_token: str,
    video_path: Path,
    title: str,
    privacy_level: str | None = None,
    disable_duet: bool = False,
    disable_comment: bool = False,
    disable_stitch: bool = False,
) -> tuple[str, str]:
    """Returns (publish_id, upload_url)."""
    privacy = privacy_level or os.environ.get("TIKTOK_DEFAULT_PRIVACY", "SELF_ONLY")
    video_size = video_path.stat().st_size
    total_chunks = max(1, (video_size + CHUNK_SIZE - 1) // CHUNK_SIZE)
    chunk_size = video_size if total_chunks == 1 else CHUNK_SIZE

    payload = {
        "post_info": {
            "title": title,
            "privacy_level": privacy,
            "disable_duet": disable_duet,
            "disable_comment": disable_comment,
            "disable_stitch": disable_stitch,
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": video_size,
            "chunk_size": chunk_size,
            "total_chunk_count": total_chunks,
        },
    }
    resp = requests.post(INIT_URL, headers=_auth_headers(access_token), json=payload, timeout=30)
    resp.raise_for_status()
    body = resp.json()
    if body.get("error", {}).get("code") not in (None, "ok"):
        raise RuntimeError(f"init failed: {body['error']}")
    data = body["data"]
    return data["publish_id"], data["upload_url"]


def upload_video(video_path: Path, upload_url: str) -> None:
    video_size = video_path.stat().st_size
    with video_path.open("rb") as f:
        offset = 0
        while offset < video_size:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            end = offset + len(chunk) - 1
            headers = {
                "Content-Range": f"bytes {offset}-{end}/{video_size}",
                "Content-Length": str(len(chunk)),
                "Content-Type": "video/mp4",
            }
            r = requests.put(upload_url, headers=headers, data=chunk, timeout=300)
            if r.status_code not in (200, 201, 206):
                raise RuntimeError(f"chunk upload failed [{r.status_code}]: {r.text}")
            offset += len(chunk)


def poll_status(
    access_token: str,
    publish_id: str,
    timeout_s: int = 600,
    interval_s: int = 5,
) -> PublishResult:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        r = requests.post(
            STATUS_URL,
            headers=_auth_headers(access_token),
            json={"publish_id": publish_id},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json().get("data", {})
        status = data.get("status", "UNKNOWN")
        if status == "PUBLISH_COMPLETE":
            return PublishResult(
                publish_id=publish_id,
                status=status,
                publicaly_available_post_id=(data.get("publicaly_available_post_id") or [None])[0],
            )
        if status == "FAILED":
            return PublishResult(
                publish_id=publish_id, status=status, fail_reason=data.get("fail_reason")
            )
        time.sleep(interval_s)
    return PublishResult(publish_id=publish_id, status="TIMEOUT")
