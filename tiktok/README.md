# NEITHLABEL TikTok Auto-Poster

Posts videos from a local queue folder to NEITHLABEL's TikTok account using the
official [TikTok Content Posting API](https://developers.tiktok.com/doc/content-posting-api-get-started).

## Layout

```
tiktok/
  src/
    auth.py       # refresh_token -> short-lived access_token (cached)
    publish.py    # init -> chunked upload -> status poll
    pipeline.py   # pick next .mp4 from queue, post, archive
    cli.py        # `python -m src.cli post-next` etc.
  requirements.txt
  .env.example
.github/workflows/scheduled-tiktok-post.yml   # daily cron
tiktok-privacy-policy.html                    # required for app review
```

## One-time setup

1. Create a TikTok developer app at <https://developers.tiktok.com>. Enable the
   **Content Posting API** scope (`video.publish` for direct publish, or just
   `video.upload` to land in the inbox as a draft).
2. Add the privacy policy URL: `https://<your-pages-domain>/tiktok-privacy-policy.html`.
3. Run the OAuth flow once (locally or via TikTok's sandbox UI) for the
   NEITHLABEL account and capture the **refresh token** — it's long-lived.
4. Copy `.env.example` to `.env` and fill in `TIKTOK_CLIENT_KEY`,
   `TIKTOK_CLIENT_SECRET`, `TIKTOK_REFRESH_TOKEN`.

> Until your app is audited by TikTok, `privacy_level` must be `SELF_ONLY` and
> videos appear as drafts in the creator's inbox. After audit you can switch to
> `PUBLIC_TO_EVERYONE`.

## Local usage

```bash
cd tiktok
pip install -r requirements.txt

# post one video right now
python -m src.cli post --video ../uploads/queue/clip.mp4 --title "drop 03 // teaser"

# post the next video in the queue
python -m src.cli post-next --queue ../uploads/queue --archive ../uploads/posted
```

### Queue format

Drop a `.mp4` into `uploads/queue/`. Optionally add a sibling `.json`:

```json
{ "title": "drop 03 // teaser #neithlabel", "privacy_level": "SELF_ONLY" }
```

Posted files are moved to `uploads/posted/`.

## Scheduling

The included GitHub Actions workflow runs daily at 16:00 UTC. Add these repo
secrets: `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_REFRESH_TOKEN`.

For a self-hosted box, a cron line works too:

```cron
0 16 * * *  cd /srv/neithlabel/tiktok && /usr/bin/python -m src.cli post-next >> /var/log/tiktok.log 2>&1
```

## Notes

- Chunk size is 10 MB. TikTok requires 5–64 MB chunks; the last chunk may be smaller.
- The status poll waits up to 10 minutes for `PUBLISH_COMPLETE`.
- Don't bypass this with browser automation. It violates TikTok's TOS and gets accounts banned.
