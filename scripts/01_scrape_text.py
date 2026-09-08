"""
Script 01: Scrape text and download chapter MP3 audio for Urhobo Old Testament Bible (UBV77).

Inputs:
  - Bible.com UBV77 chapter URLs (e.g., https://www.bible.com/bible/2616/GEN.1.UBV77)
Outputs:
  - data/raw/text/{book}/{book}_{chapter:03d}.json (Verse-ordered text with BCV IDs and headings)
  - data/raw/audio/{book}/{book}_{chapter:03d}.mp3 (Raw chapter audio)
"""

import os
import sys
import json
import re
import socket
import argparse
import urllib.request
from pathlib import Path
from bs4 import BeautifulSoup

# Ensure UTF-8 output in Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
RAW_TEXT_DIR = DATA_DIR / "raw" / "text"
RAW_AUDIO_DIR = DATA_DIR / "raw" / "audio"

# Verified Fastly CDN IP fallback to prevent local Windows DNS timeouts
FASTLY_IP = "167.82.21.55"
TARGET_HOSTS = {"www.bible.com", "bible.com", "audio-bible-cdn.youversionapi.com"}

_orig_getaddrinfo = socket.getaddrinfo


def _patched_getaddrinfo(host, port, *args, **kwargs):
    if host in TARGET_HOSTS:
        try:
            return _orig_getaddrinfo(FASTLY_IP, port, *args, **kwargs)
        except Exception:
            pass
    return _orig_getaddrinfo(host, port, *args, **kwargs)


socket.getaddrinfo = _patched_getaddrinfo


def get_headers():
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }


def parse_chapter_range(chap_str):
    """
    Parses strings like '1', '1-5', '1,2,5' into a sorted list of integer chapter numbers.
    """
    chapters = set()
    for part in chap_str.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            chapters.update(range(int(start), int(end) + 1))
        elif part:
            chapters.add(int(part))
    return sorted(list(chapters))


def fetch_chapter_html(book: str, chapter: int, version_id: int = 2616, timeout: int = 30) -> str:
    url = f"https://www.bible.com/bible/{version_id}/{book}.{chapter}.UBV77"
    req = urllib.request.Request(url, headers=get_headers())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        raise RuntimeError(f"Failed to fetch {url}: {e}") from e


def extract_audio_url(html: str) -> str:
    """
    Extracts the direct MP3 CDN URL embedded in the bible.com chapter HTML.
    """
    matches = re.findall(r'(?:https:)?//audio-bible-cdn\.youversionapi\.com/[^\s"\'<>\\]+', html)
    if not matches:
        raise ValueError("Could not locate audio-bible-cdn MP3 URL in page HTML")
    raw_url = matches[0]
    if not raw_url.startswith("http"):
        raw_url = "https:" + raw_url
    return raw_url


def extract_verses_and_headings(html: str, book: str, chapter: int):
    """
    Extracts verse text, verse numbers, BCV IDs, and section headings.
    Preserves original Urhobo diacritics (ẹ, ọ, etc.).
    """
    soup = BeautifulSoup(html, "html.parser")

    # Extract headings (e.g. Genesis 1 'Emama re akpọ kugbe Ohwo')
    headings = []
    heading_elements = soup.find_all(attrs={"class": re.compile(r"heading", re.I)})
    for h in heading_elements:
        txt = h.get_text(strip=True)
        if txt and txt not in headings:
            headings.append(txt)

    # Extract verses via data-usfm attribute
    verses_dict = {}
    verse_prefix = f"{book}.{chapter}."
    usfm_spans = soup.find_all(attrs={"data-usfm": True})

    for span in usfm_spans:
        usfm = span.get("data-usfm", "")
        if not usfm.startswith(verse_prefix):
            continue

        parts = usfm.split(".")
        if len(parts) != 3:
            continue

        try:
            v_num = int(parts[2])
        except ValueError:
            continue

        # Extract text from content spans, ignoring label spans
        content_spans = span.find_all(attrs={"class": re.compile(r"content")})
        if content_spans:
            text_chunk = " ".join(cs.get_text(strip=True) for cs in content_spans)
        else:
            # Fallback: remove labels and extract text
            clone = BeautifulSoup(str(span), "html.parser")
            for lbl in clone.find_all(attrs={"class": re.compile(r"label")}):
                lbl.decompose()
            text_chunk = clone.get_text(strip=True)

        if not text_chunk:
            continue

        if v_num not in verses_dict:
            verses_dict[v_num] = []
        if text_chunk not in verses_dict[v_num]:
            verses_dict[v_num].append(text_chunk)

    ordered_verses = []
    for v_num in sorted(verses_dict.keys()):
        bcv_id = f"{book}_{chapter:03d}_{v_num:03d}"
        combined_text = " ".join(verses_dict[v_num]).strip()
        # Clean excessive internal spaces
        combined_text = re.sub(r"\s+", " ", combined_text)
        ordered_verses.append({
            "bcv_id": bcv_id,
            "verse_num": v_num,
            "text": combined_text,
        })

    return ordered_verses, headings


def download_audio_file(audio_url: str, dest_path: Path, timeout: int = 60, force: bool = False):
    if dest_path.exists() and dest_path.stat().st_size > 10000 and not force:
        print(f"    [Audio] Using cached audio: {dest_path.name} ({dest_path.stat().st_size // 1024} KB)")
        return

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(audio_url, headers=get_headers())
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest_path, "wb") as f:
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            f.write(chunk)
    print(f"    [Audio] Downloaded: {dest_path.name} ({dest_path.stat().st_size // 1024} KB)")


def scrape_chapter(book: str, chapter: int, version_id: int = 2616, force: bool = False):
    bcv_chapter = f"{book}_{chapter:03d}"
    out_text_dir = RAW_TEXT_DIR / book
    out_audio_dir = RAW_AUDIO_DIR / book
    out_text_dir.mkdir(parents=True, exist_ok=True)
    out_audio_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_text_dir / f"{bcv_chapter}.json"
    audio_path = out_audio_dir / f"{bcv_chapter}.mp3"

    print(f"\nProcessing {book} Chapter {chapter} ({bcv_chapter})...")

    # Fetch and parse HTML
    html = fetch_chapter_html(book, chapter, version_id=version_id)
    audio_url = extract_audio_url(html)
    verses, headings = extract_verses_and_headings(html, book, chapter)

    if not verses:
        raise ValueError(f"No verses extracted for {book} chapter {chapter}")

    # Download audio
    download_audio_file(audio_url, audio_path, force=force)

    # Save verse manifest
    manifest = {
        "book": book,
        "chapter": chapter,
        "bcv_chapter": bcv_chapter,
        "version_id": version_id,
        "audio_url": audio_url,
        "audio_file": str(audio_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "audio_size_bytes": audio_path.stat().st_size,
        "headings": headings,
        "total_verses": len(verses),
        "verses": verses,
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"    [Text]  Saved {len(verses)} verses to {json_path.name}")
    print(f"    [Text]  First verse: {verses[0]['text'][:60]}...")
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Scrape Urhobo Bible text and chapter audio (UBV77).")
    parser.add_argument("--book", type=str, default="GEN", help="Book code (e.g., GEN, EXO)")
    parser.add_argument("--chapters", type=str, default="1", help="Comma-separated or range (e.g. 1, 1-3, 1-50)")
    parser.add_argument("--force", action="store_true", help="Force re-downloading audio and text")
    args = parser.parse_args()

    chapters = parse_chapter_range(args.chapters)
    print(f"[01_scrape_text] Starting acquisition for {args.book} (Total chapters: {len(chapters)})")

    success_count = 0
    for chap in chapters:
        try:
            scrape_chapter(args.book, chap, force=args.force)
            success_count += 1
        except Exception as e:
            print(f"    [ERROR] Failed processing chapter {chap}: {e}", file=sys.stderr)

    print(f"\n[01_scrape_text] Complete! Successfully processed {success_count}/{len(chapters)} chapters.")


if __name__ == "__main__":
    main()
