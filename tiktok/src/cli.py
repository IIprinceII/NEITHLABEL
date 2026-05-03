"""CLI entry point.

Usage:
  python -m tiktok.src.cli post-next --queue ./uploads/queue --archive ./uploads/posted
  python -m tiktok.src.cli post --video ./clip.mp4 --title "Hello"
  python -m tiktok.src.cli refresh-token
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from .auth import get_access_token
from .pipeline import QueueItem, pick_next, post_one


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="tiktok")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_next = sub.add_parser("post-next", help="post the next queued video")
    p_next.add_argument("--queue", type=Path, default=Path("uploads/queue"))
    p_next.add_argument("--archive", type=Path, default=Path("uploads/posted"))

    p_one = sub.add_parser("post", help="post a single video")
    p_one.add_argument("--video", type=Path, required=True)
    p_one.add_argument("--title", required=True)
    p_one.add_argument("--privacy", default=None)
    p_one.add_argument("--archive", type=Path, default=Path("uploads/posted"))

    sub.add_parser("refresh-token", help="force a token refresh and print the new access token")

    args = parser.parse_args(argv)

    if args.cmd == "refresh-token":
        print(get_access_token(force_refresh=True))
        return 0

    if args.cmd == "post-next":
        item = pick_next(args.queue)
        if item is None:
            print("queue empty")
            return 0
        publish_id = post_one(item, args.archive)
        print(f"posted: {publish_id}")
        return 0

    if args.cmd == "post":
        item = QueueItem(video=args.video, title=args.title, privacy_level=args.privacy)
        publish_id = post_one(item, args.archive)
        print(f"posted: {publish_id}")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
