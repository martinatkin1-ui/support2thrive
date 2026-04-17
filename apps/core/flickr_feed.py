"""Fetch community imagery from Flickr public feeds (Picha-style, no API key)."""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from html import unescape

from django.conf import settings
from django.utils.html import strip_tags
from django.utils.translation import gettext as _

from .models import CommunityPhoto

logger = logging.getLogger(__name__)

_FEED_URL = "https://www.flickr.com/services/feeds/photos_public.gne"
# Flickr often rejects non-browser User-Agents; keep a conventional UA.
_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
}


def _flickr_author_display(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    m = re.search(r'\("([^"]+)"\)', raw)
    if m:
        return m.group(1).strip()
    m = re.search(r"\(([^)]+)\)", raw)
    if m:
        return m.group(1).strip()
    return raw


def _fetch_flickr_feed_for_tag_string(tags: str, *, timeout: int = 20) -> list[dict]:
    """
    One request to the public feed. Comma-separated tags are AND-ed by Flickr,
    so long lists usually return zero items.
    """
    q = urllib.parse.urlencode(
        {"tags": tags, "format": "json", "nojsoncallback": "1"}
    )
    url = f"{_FEED_URL}?{q}"
    req = urllib.request.Request(url, headers=_DEFAULT_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return list(payload.get("items") or [])


def fetch_flickr_merged(tag_csv: str, *, max_items: int) -> tuple[list[dict], str | None]:
    """
    Split ``tag_csv`` on commas and run one feed request per segment (trimmed).
    Flickr ANDs tags within a single request; merging per-tag results gives broad
    regional coverage without requiring one photo to match every tag.

    Returns (items, error_message). error_message is set only on total failure.
    """
    segments = [t.strip() for t in (tag_csv or "").split(",") if t.strip()]
    if not segments:
        return [], "No tags configured (COMMUNITY_PHOTO_FLICKR_TAGS is empty)."

    merged: list[dict] = []
    seen_links: set[str] = set()
    errors: list[str] = []

    cap = max(0, max_items)
    for seg in segments:
        if len(merged) >= cap:
            break
        try:
            batch = _fetch_flickr_feed_for_tag_string(seg)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"{seg!r}: {exc}")
            logger.warning("Flickr feed failed for tag %s: %s", seg, exc)
            continue
        for item in batch:
            link = (item.get("link") or "").strip()
            if not link or link in seen_links:
                continue
            seen_links.add(link)
            merged.append(item)
            if len(merged) >= cap:
                break

    if not merged and errors:
        return [], "; ".join(errors[:3])
    return merged, None


def sync_community_photos_from_flickr(*, limit: int | None = None) -> tuple[int, str | None]:
    """
    Upsert photos from the configured Flickr public feed into CommunityPhoto.

    Returns (processed_count, error_message). ``error_message`` is None on success.
    """
    tags = getattr(
        settings,
        "COMMUNITY_PHOTO_FLICKR_TAGS",
        "wolverhampton,westmidlands,community",
    )
    max_items = limit if limit is not None else int(
        getattr(settings, "COMMUNITY_PHOTO_SYNC_LIMIT", 24)
    )
    items, err = fetch_flickr_merged(tags, max_items=max_items)
    if err:
        logger.warning("Community photo sync: %s", err)
        return 0, err
    if not items:
        msg = (
            "No photos returned for your tag list. "
            "Each comma-separated tag is queried separately; check spelling and network access to flickr.com."
        )
        logger.warning("Community photo sync: %s Tags: %r", msg, tags)
        return 0, msg

    processed = 0
    for item in items:
        link = (item.get("link") or "").strip()
        media = item.get("media") or {}
        image_url = (media.get("m") or "").strip()
        if not link or not image_url:
            continue
        title = unescape(strip_tags(item.get("title") or "")).strip() or _("Untitled")
        desc_html = item.get("description") or ""
        description = unescape(strip_tags(desc_html)).strip()
        if len(description) > 2000:
            description = description[:2000]
        attribution = _flickr_author_display(item.get("author") or "")

        CommunityPhoto.objects.update_or_create(
            source_link=link,
            defaults={
                "title": title[:255],
                "image_url": image_url[:512],
                "description": description,
                "attribution": attribution[:255],
                "is_active": True,
            },
        )
        processed += 1
    return processed, None
