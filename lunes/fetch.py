import logging
import re
import struct
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from typing import Optional
from urllib.parse import urljoin

import feedparser
import requests

import config

logger = logging.getLogger(__name__)

MIN_IMAGE_WIDTH = 600
_FETCH_TIMEOUT  = 7   # seconds per HTTP request
_MAX_WORKERS    = 12
_HEADERS        = {"User-Agent": "Mozilla/5.0 (compatible; LUNES-bot/1.0)"}


# ── HTML helpers ──────────────────────────────────────────────────────────────

def _strip_html(raw: str) -> str:
    class _P(HTMLParser):
        def __init__(self):
            super().__init__()
            self.parts: list[str] = []
        def handle_data(self, data: str) -> None:
            self.parts.append(data)
    p = _P()
    p.feed(raw or "")
    return " ".join(p.parts).strip()


# ── RSS image extraction ──────────────────────────────────────────────────────

def _extract_image(entry) -> Optional[str]:
    # media:thumbnail — often a proper featured image
    for t in getattr(entry, "media_thumbnail", []):
        url = t.get("url", "")
        if url:
            return url
    # media:content — skip audio/video
    for m in getattr(entry, "media_content", []):
        url = m.get("url", "")
        if url and not url.lower().endswith((".mp4", ".webm", ".mp3", ".ogg")):
            return url
    # enclosures with image MIME type
    for enc in getattr(entry, "enclosures", []):
        if enc.get("type", "").startswith("image/"):
            return enc.get("href") or enc.get("url") or ""
    # first <img src> in full content or summary HTML
    raw = ""
    if entry.get("content"):
        raw = entry.content[0].get("value", "")
    if not raw:
        raw = getattr(entry, "summary", "") or ""
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', raw)
    if m:
        return m.group(1)
    return None


# ── Image dimension parsing from raw bytes ────────────────────────────────────

def _parse_image_width(data: bytes) -> Optional[int]:
    # PNG: IHDR at byte 8, width at bytes 16-19
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        return struct.unpack(">I", data[16:20])[0]
    # JPEG: scan for SOF markers
    if data[:2] == b"\xff\xd8":
        i = 2
        while i + 4 <= len(data):
            if data[i] != 0xff:
                break
            marker = data[i + 1]
            if marker in (0xc0, 0xc1, 0xc2, 0xc3):
                if i + 9 <= len(data):
                    return struct.unpack(">H", data[i + 7: i + 9])[0]
            length = struct.unpack(">H", data[i + 2: i + 4])[0]
            i += 2 + length
    # WebP
    if len(data) >= 30 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        if data[12:16] == b"VP8 ":
            return struct.unpack("<H", data[26:28])[0] & 0x3FFF
        if data[12:16] == b"VP8L" and len(data) >= 25:
            return (struct.unpack("<I", data[21:25])[0] & 0x3FFF) + 1
        if data[12:16] == b"VP8X" and len(data) >= 30:
            return struct.unpack("<I", data[24:27] + b"\x00")[0] + 1
    # GIF
    if data[:6] in (b"GIF87a", b"GIF89a") and len(data) >= 10:
        return struct.unpack("<H", data[6:8])[0]
    return None


# ── Image URL validation ──────────────────────────────────────────────────────

def _validate_image_url(url: str) -> bool:
    """True if URL returns an image with width >= MIN_IMAGE_WIDTH."""
    if not url:
        return False
    try:
        resp = requests.get(url, stream=True, timeout=_FETCH_TIMEOUT, headers=_HEADERS)
        if resp.status_code not in (200, 206):
            return False
        ct = resp.headers.get("Content-Type", "")
        data = b""
        for chunk in resp.iter_content(8192):
            data += chunk
            break
        resp.close()
        width = _parse_image_width(data)
        if width is None:
            return "image" in ct
        return width >= MIN_IMAGE_WIDTH
    except Exception:
        return False


# ── og:image fallback ─────────────────────────────────────────────────────────

def _fetch_og_image(article_url: str) -> Optional[str]:
    """Fetch article page head and return og:image / twitter:image URL, or None."""
    try:
        resp = requests.get(
            article_url, stream=True, timeout=_FETCH_TIMEOUT, headers=_HEADERS
        )
        if resp.status_code != 200:
            return None
        raw = b""
        for chunk in resp.iter_content(2048):
            raw += chunk
            if b"</head>" in raw or b"<body" in raw or len(raw) > 32_000:
                break
        resp.close()
        head = raw.decode("utf-8", errors="ignore")
        for pat in (
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']{12,})["\']',
            r'<meta[^>]+content=["\']([^"\']{12,})["\'][^>]+property=["\']og:image["\']',
            r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']{12,})["\']',
            r'<meta[^>]+content=["\']([^"\']{12,})["\'][^>]+name=["\']twitter:image["\']',
        ):
            m = re.search(pat, head, re.IGNORECASE)
            if m:
                img = m.group(1)
                if img.startswith("//"):
                    img = "https:" + img
                elif img.startswith("/"):
                    img = urljoin(article_url, img)
                return img
    except Exception:
        pass
    return None


# ── Image enrichment (runs on curated items only) ─────────────────────────────

def enrich_images(items: list[dict]) -> None:
    """Validate RSS images and fill missing ones with og:image. Modifies items in-place.

    items — flat list of curated story dicts, each with keys: url, image (may be None).
    After this call every item has image=<valid url> or image=None.
    Sets item["credit"] = item["source"] when image is present, else None.
    Items without a "source" key (e.g. awwwards.featured uses "author") keep their
    existing credit value unchanged.
    """
    # Phase 1: validate images that came from the RSS feed
    rss_items = [it for it in items if it.get("image")]
    if rss_items:
        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as exe:
            fut_map = {exe.submit(_validate_image_url, it["image"]): it for it in rss_items}
            cleared = 0
            for fut in as_completed(fut_map):
                it = fut_map[fut]
                try:
                    if not fut.result():
                        it["image"] = None
                        cleared += 1
                except Exception:
                    it["image"] = None
                    cleared += 1
        logger.info(
            "Images — RSS valid: %d  cleared (too small/unreachable): %d",
            len(rss_items) - cleared, cleared,
        )

    # Phase 2: og:image fetch for items still without an image
    missing = [it for it in items if not it.get("image") and it.get("url")]
    if missing:
        logger.info("Images — fetching og:image for %d items…", len(missing))
        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as exe:
            fut_map = {exe.submit(_fetch_og_image, it["url"]): it for it in missing}
            found = 0
            for fut in as_completed(fut_map):
                it = fut_map[fut]
                try:
                    it["image"] = fut.result()
                    if it["image"]:
                        found += 1
                except Exception:
                    it["image"] = None
        logger.info("Images — og:image found: %d / %d", found, len(missing))

    # Phase 3: validate newly fetched og:images
    new_images = [it for it in missing if it.get("image")]
    if new_images:
        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as exe:
            fut_map = {exe.submit(_validate_image_url, it["image"]): it for it in new_images}
            for fut in as_completed(fut_map):
                it = fut_map[fut]
                try:
                    if not fut.result():
                        it["image"] = None
                except Exception:
                    it["image"] = None

    # Credit: set from "source" if present; leave unchanged for items without "source"
    for it in items:
        if "source" in it:
            it["credit"] = it["source"] if it.get("image") else None

    valid = sum(1 for it in items if it.get("image"))
    logger.info("Images — final: %d / %d items have a valid image", valid, len(items))


# ── Date parsing ──────────────────────────────────────────────────────────────

def _parse_date(entry) -> Optional[datetime]:
    for field in ("published_parsed", "updated_parsed"):
        t = getattr(entry, field, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


# ── Main fetch ────────────────────────────────────────────────────────────────

def fetch_articles() -> list[dict]:
    """Fetch, filter and normalise articles from all configured FEEDS sections.

    Returns list of dicts: {title, source, section, date, summary, url, image, credit}
    Sections match FEEDS keys: "diseño", "ia", "awwwards".
    Only items published in the last WINDOW_DAYS days (or undated items).
    Deduped globally by URL, then by normalised title.
    image/credit are provisional RSS values; call enrich_images() on curated
    items for validated, og:image-enriched URLs.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=config.WINDOW_DAYS)
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    articles: list[dict] = []

    for section, feeds in config.FEEDS.items():
        for feed_cfg in feeds:
            name = feed_cfg["name"]
            url = feed_cfg["url"]
            filter_prefix = feed_cfg.get("filter_url_prefix")
            count_before = len(articles)

            try:
                d = feedparser.parse(url)
                if d.get("bozo") and not d.entries:
                    logger.warning("%-20s  parse error: %s", name, d.get("bozo_exception", ""))
                    continue

                for entry in d.entries:
                    link = (getattr(entry, "link", None) or getattr(entry, "id", None) or "").strip()

                    if filter_prefix and not link.startswith(filter_prefix):
                        continue

                    date = _parse_date(entry)
                    if date is not None and date < cutoff:
                        continue

                    title = (getattr(entry, "title", "") or "").strip()

                    url_key = link.rstrip("/").lower()
                    if url_key and url_key in seen_urls:
                        continue
                    title_key = title.lower()[:80]
                    if title_key and title_key in seen_titles:
                        continue

                    if url_key:
                        seen_urls.add(url_key)
                    if title_key:
                        seen_titles.add(title_key)

                    raw_summary = ""
                    if entry.get("content"):
                        raw_summary = entry.content[0].get("value", "")
                    if not raw_summary:
                        raw_summary = getattr(entry, "summary", "") or ""
                    summary = _strip_html(raw_summary)[:500]

                    articles.append({
                        "title":   title,
                        "source":  name,
                        "section": section,
                        "date":    date.isoformat() if date else None,
                        "summary": summary,
                        "url":     link,
                        "image":   _extract_image(entry),
                        "credit":  name,  # provisional; enrich_images() sets final value
                    })

            except Exception as exc:
                logger.warning("%-20s  fetch failed: %s", name, exc)
                continue

            added = len(articles) - count_before
            logger.info("%-20s  +%d", name, added)

    articles.sort(key=lambda a: a["date"] or "0000", reverse=True)
    by_section = {}
    for a in articles:
        by_section.setdefault(a["section"], 0)
        by_section[a["section"]] += 1
    logger.info(
        "Total: %d articles — %s  (window: %d days)",
        len(articles),
        "  ".join(f"{s}:{n}" for s, n in by_section.items()),
        config.WINDOW_DAYS,
    )
    return articles
