"""End-to-end: pick the next video from a queue folder, post it, archive on success."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from .auth import get_access_token
from .publish import init_video_post, poll_status, upload_video


@dataclass
class QueueItem:
    video: Path
    title: str
    privacy_level: str | None = None


def pick_next(queue_dir: Path) -> QueueItem | None:
    """Each item is a .mp4 with a sibling .json holding caption + options."""
    for video in sorted(queue_dir.glob("*.mp4")):
        meta_file = video.with_suffix(".json")
        meta = json.loads(meta_file.read_text()) if meta_file.exists() else {}
        return QueueItem(
            video=video,
            title=meta.get("title", video.stem),
            privacy_level=meta.get("privacy_level"),
        )
    return None


def post_one(item: QueueItem, archive_dir: Path) -> str:
    token = get_access_token()
    publish_id, upload_url = init_video_post(
        access_token=token,
        video_path=item.video,
        title=item.title,
        privacy_level=item.privacy_level,
    )
    upload_video(item.video, upload_url)
    result = poll_status(token, publish_id)
    if result.status != "PUBLISH_COMPLETE":
        raise RuntimeError(f"post did not complete: {result}")

    archive_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(item.video), archive_dir / item.video.name)
    meta = item.video.with_suffix(".json")
    if meta.exists():
        shutil.move(str(meta), archive_dir / meta.name)
    return publish_id
