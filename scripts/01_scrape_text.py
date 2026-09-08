"""
Script 01: Scrape text and download chapter MP3 audio for Urhobo Old Testament Bible (UBV77).

Inputs:
  - Bible.com UBV77 chapter URLs (e.g., https://bible.com/bible/2616/GEN.1.UBV77)
Outputs:
  - data/raw/text/{book}/{book}_{chapter}.json (Verse-ordered text with BCV IDs)
  - data/raw/audio/{book}/{book}_{chapter}.mp3 (Raw chapter audio)
"""

import os
import sys
import json
import argparse
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_TEXT_DIR = DATA_DIR / "raw" / "text"
RAW_AUDIO_DIR = DATA_DIR / "raw" / "audio"


def main():
    parser = argparse.ArgumentParser(description="Scrape Urhobo Bible text and chapter audio.")
    parser.add_argument("--book", type=str, default="GEN", help="Book code (e.g., GEN, EXO)")
    parser.add_argument("--chapters", type=str, default="1", help="Comma-separated chapters or range (e.g., 1-5)")
    args = parser.parse_args()

    print(f"[01_scrape_text] Starting acquisition for {args.book} (Chapters: {args.chapters})...")
    # Implemented in Phase 1
    print("[01_scrape_text] Ready for Phase 1 execution.")


if __name__ == "__main__":
    main()
