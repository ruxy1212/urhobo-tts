#!/usr/bin/env python3
"""
scripts/03_prepare_alignment_text.py

Phase 4.1 — Romanization & Alignment Manifest Prepper.

Takes normalized Urhobo text manifests from data/interim/normalized_text/{book}/,
applies uroman to generate clean ASCII/Latin representations matching the MMS
forced aligner dictionary (a-z, ', and * wildcard tokens), and builds
deterministic chapter-level alignment payloads with word-to-verse span indices.

Outputs saved to:
  data/interim/alignment_prep/{book}/{book}_{chapter}_prep.json
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
from uroman import Uroman

# Ensure UTF-8 console output for Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent
NORM_TEXT_DIR = REPO_ROOT / "data" / "interim" / "normalized_text"
ALIGN_PREP_DIR = REPO_ROOT / "data" / "interim" / "alignment_prep"


def clean_punctuation_for_tokens(text: str) -> str:
    """
    Replaces punctuation with spaces while preserving apostrophes within words and star tokens.
    """
    text = re.sub(r"[—–\-]", " ", text)
    text = re.sub(r"[^\w\s\'*]", " ", text)
    return " ".join(text.split())


def extract_clean_words(text: str) -> List[str]:
    """
    Splits text into words, removing punctuation from word edges while preserving internal apostrophes.
    """
    cleaned = re.sub(r"[^\w\s\']", " ", text)
    words = cleaned.split()
    words = [w.strip("'") for w in words if w.strip("'")]
    return words


def process_chapter_manifest(
    norm_json_path: Path,
    uroman_instance: Uroman,
    book: str,
) -> Dict[str, Any]:
    """
    Processes a single chapter's normalized text into an alignment-ready preparation payload.
    """
    with open(norm_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    bcv_chapter = data["bcv_chapter"]
    chapter_num = data.get("chapter", 1)
    segments_in = data.get("segments", [])

    prepared_segments: List[Dict[str, Any]] = []
    chapter_words_urhobo: List[str] = []
    chapter_words_romanized: List[str] = []
    chapter_tokens_for_alignment: List[str] = []

    current_word_idx = 0

    for seg in segments_in:
        seg_type = seg.get("type", "verse")
        bcv_id = seg.get("bcv_id", "")
        verse_num = seg.get("verse_num", None)
        text_urhobo = seg.get("text_normalized", "")

        if seg_type == "heading":
            # Heading: romanize heading words and enclose in wildcard star tokens '*'
            heading_rom = uroman_instance.romanize_string(text_urhobo)
            heading_words_rom = extract_clean_words(heading_rom.lower())
            heading_words_urh = extract_clean_words(text_urhobo)

            h_start_idx = current_word_idx
            h_end_idx = current_word_idx + len(heading_words_rom) - 1 if heading_words_rom else h_start_idx

            heading_word_items = []
            for i, rom_w in enumerate(heading_words_rom):
                urh_w = heading_words_urh[i] if i < len(heading_words_urh) else rom_w
                global_idx = current_word_idx + i
                heading_word_items.append({
                    "word_index": global_idx,
                    "urhobo": urh_w,
                    "romanized": rom_w,
                })
                chapter_words_urhobo.append(urh_w)
                chapter_words_romanized.append(rom_w)

            current_word_idx += len(heading_words_rom)

            # In alignment token representation:
            # We insert '*' before and after heading text so CTC aligner can absorb filler audio
            heading_align_str = f"* {' '.join(heading_words_rom)} *" if heading_words_rom else "*"

            prep_seg = {
                "bcv_id": bcv_id,
                "type": "heading",
                "verse_num": None,
                "text_urhobo": text_urhobo,
                "text_romanized": " ".join(heading_words_rom),
                "alignment_token": heading_align_str,
                "words": heading_word_items,
                "words_urhobo": heading_words_urh,
                "words_romanized": heading_words_rom,
                "word_span": [h_start_idx, h_end_idx] if heading_words_rom else None,
                "word_count": len(heading_words_rom),
            }
            prepared_segments.append(prep_seg)
            chapter_tokens_for_alignment.append(heading_align_str)

        else:
            # Verse: romanize words, map exact 1:1 token indices
            verse_rom = uroman_instance.romanize_string(text_urhobo)
            verse_words_rom = extract_clean_words(verse_rom.lower())
            verse_words_urh = extract_clean_words(text_urhobo)

            start_idx = current_word_idx
            end_idx = current_word_idx + len(verse_words_rom) - 1 if verse_words_rom else start_idx

            word_items = []
            for i, rom_w in enumerate(verse_words_rom):
                urh_w = verse_words_urh[i] if i < len(verse_words_urh) else rom_w
                global_idx = current_word_idx + i
                word_items.append({
                    "word_index": global_idx,
                    "urhobo": urh_w,
                    "romanized": rom_w,
                })
                chapter_words_urhobo.append(urh_w)
                chapter_words_romanized.append(rom_w)

            current_word_idx += len(verse_words_rom)

            prep_seg = {
                "bcv_id": bcv_id,
                "type": "verse",
                "verse_num": verse_num,
                "text_urhobo": text_urhobo,
                "text_romanized": " ".join(verse_words_rom),
                "alignment_token": " ".join(verse_words_rom),
                "words": word_items,
                "word_span": [start_idx, end_idx] if verse_words_rom else None,
                "word_count": len(verse_words_rom),
            }
            prepared_segments.append(prep_seg)
            chapter_tokens_for_alignment.append(" ".join(verse_words_rom))

    full_alignment_text = " ".join(chapter_tokens_for_alignment)
    full_alignment_text = " ".join(full_alignment_text.split())

    payload = {
        "book": book,
        "chapter": chapter_num,
        "bcv_chapter": bcv_chapter,
        "audio_wav": f"data/interim/wav/{book}/{bcv_chapter}.wav",
        "total_verses": data.get("total_verses", 0),
        "total_headings": data.get("headings_count", 0),
        "total_words": len(chapter_words_romanized),
        "full_alignment_text": full_alignment_text,
        "chapter_words_romanized": chapter_words_romanized,
        "chapter_words_urhobo": chapter_words_urhobo,
        "segments": prepared_segments,
    }

    return payload


def main():
    parser = argparse.ArgumentParser(description="Generate romanized alignment preparation manifests.")
    parser.add_argument("--book", type=str, default="GEN", help="Book code (default: GEN)")
    parser.add_argument("--output-dir", type=Path, default=ALIGN_PREP_DIR)
    args = parser.parse_args()

    book_norm_dir = NORM_TEXT_DIR / args.book
    book_out_dir = args.output_dir / args.book

    if not book_norm_dir.exists():
        print(f"Error: Normalized text directory not found: {book_norm_dir}", file=sys.stderr)
        sys.exit(1)

    book_out_dir.mkdir(parents=True, exist_ok=True)

    json_files = sorted(book_norm_dir.glob(f"{args.book}_*.json"))
    print(f"[03_prepare_alignment_text] Initializing uroman...")
    uroman_instance = Uroman()

    print(f"[03_prepare_alignment_text] Processing {len(json_files)} chapters for {args.book}...")

    total_chapters = len(json_files)
    total_verses = 0
    total_headings = 0
    total_words = 0
    all_vocab_chars = set()

    for idx, fpath in enumerate(json_files, start=1):
        payload = process_chapter_manifest(fpath, uroman_instance, args.book)

        out_path = book_out_dir / f"{payload['bcv_chapter']}_prep.json"
        with open(out_path, "w", encoding="utf-8") as out_f:
            json.dump(payload, out_f, indent=2, ensure_ascii=False)

        total_verses += payload["total_verses"]
        total_headings += payload["total_headings"]
        total_words += payload["total_words"]

        for ch in payload["full_alignment_text"]:
            all_vocab_chars.add(ch)

        if idx % 10 == 0 or idx == total_chapters:
            print(f"  [{idx:02d}/{total_chapters}] Processed: {payload['bcv_chapter']}_prep.json ({payload['total_words']} words)")

    illegal_chars = [ch for ch in all_vocab_chars if ch not in "abcdefghijklmnopqrstuvwxyz'* "]

    manifest_summary = {
        "book": args.book,
        "total_chapters": total_chapters,
        "total_verses": total_verses,
        "total_headings": total_headings,
        "total_words": total_words,
        "vocabulary": sorted(list(all_vocab_chars)),
        "illegal_chars": illegal_chars,
        "status": "VALID" if not illegal_chars else "INVALID_CHARS_DETECTED",
    }

    summary_path = book_out_dir / f"{args.book}_prep_manifest.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(manifest_summary, f, indent=2, ensure_ascii=False)

    print("\n=======================================================")
    print(f"ALIGNMENT PREPARATION COMPLETE FOR {args.book}:")
    print(f"  Total Chapters:      {total_chapters}")
    print(f"  Total Verses:        {total_verses}")
    print(f"  Total Headings:      {total_headings} (wildcard '*' tokens)")
    print(f"  Total Words:         {total_words}")
    print(f"  Vocabulary:          {''.join(sorted(list(all_vocab_chars)))}")
    print(f"  Illegal Chars:       {illegal_chars} (Should be empty)")
    print(f"  Validation Status:   {manifest_summary['status']}")
    print(f"  Manifest Summary:    {summary_path}")
    print("=======================================================")


if __name__ == "__main__":
    main()
