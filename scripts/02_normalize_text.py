"""
Script 02: Verse-Level Text Normalization & Alignment Prepper (Phase 2).

Inputs:
  - data/raw/text/{book}/{book}_{chapter:03d}.json (Raw chapter verse manifests)
Outputs:
  - data/interim/normalized_text/{book}/{book}_{chapter:03d}.json (Normalized manifests with star-token markers)
  - data/interim/normalized_text/{book}/{book}_{chapter:03d}.txt (Concatenated alignment-ready transcripts)

Processing:
  1. Verifies strict monotonic verse ordering (1, 2, ..., N).
  2. Spells out any standalone digits using scripts/urhobo_numerals.py.
  3. Standardizes whitespace and punctuation while preserving authentic Urhobo diacritics (ẹ, ọ, acute, grave).
  4. Tags non-verse narration / section headings with asterisk wildcard tokens (*) for Phase 4 CTC aligner.
"""

import sys
import json
import re
import argparse
from pathlib import Path

# UTF-8 console output for Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from urhobo_numerals import spellout_digits_in_text

RAW_TEXT_DIR = REPO_ROOT / "data" / "raw" / "text"
INTERIM_NORM_DIR = REPO_ROOT / "data" / "interim" / "normalized_text"


def clean_punctuation_and_spaces(text: str) -> str:
    """
    Standardizes whitespace and quotes while preserving diacritics and hyphens.
    """
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("—", " - ").replace("–", " - ")
    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_verse_text(text: str) -> str:
    """
    Normalizes a single verse's text: expands digits and cleans spacing.
    Preserves all Urhobo diacritics.
    """
    # 1. Expand standalone numbers
    text_expanded = spellout_digits_in_text(text, toned=False)
    # 2. Clean punctuation/whitespace
    cleaned = clean_punctuation_and_spaces(text_expanded)
    return cleaned


def normalize_chapter(raw_json_path: Path, out_dir: Path) -> dict:
    with open(raw_json_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    book = raw_data["book"]
    chapter = raw_data["chapter"]
    bcv_chapter = raw_data["bcv_chapter"]
    raw_verses = raw_data["verses"]
    headings = raw_data.get("headings", [])

    # 1. Verify strict monotonic verse numbering
    expected_num = 1
    normalized_segments = []
    digits_expanded_count = 0

    # Add chapter heading as star-token wildcard span if present
    if headings:
        for idx, h in enumerate(headings, start=1):
            h_clean = clean_punctuation_and_spaces(h)
            normalized_segments.append({
                "type": "heading",
                "bcv_id": f"{bcv_chapter}_H{idx:02d}",
                "text_raw": h,
                "text_normalized": h_clean,
                "alignment_token": f"* {h_clean} *",
            })

    for v in raw_verses:
        v_num = v["verse_num"]
        if v_num != expected_num:
            # Note gaps or skips
            print(f"    [WARN] Non-consecutive verse in {bcv_chapter}: expected {expected_num}, got {v_num}")
        expected_num = v_num + 1

        raw_text = v["text"]
        # Check if digits exist before expansion
        has_digits = bool(re.search(r"\b\d+\b", raw_text))
        if has_digits:
            digits_expanded_count += 1

        norm_text = normalize_verse_text(raw_text)

        normalized_segments.append({
            "type": "verse",
            "bcv_id": v["bcv_id"],
            "verse_num": v_num,
            "text_raw": raw_text,
            "text_normalized": norm_text,
            "alignment_token": norm_text,
        })

    # Assemble concatenated transcript for CTC aligner
    # Headings use wildcard * tokens, verses use normalized text
    concat_tokens = [s["alignment_token"] for s in normalized_segments]
    full_transcript = " ".join(concat_tokens)

    # Output files
    out_dir.mkdir(parents=True, exist_ok=True)
    norm_json_path = out_dir / f"{bcv_chapter}.json"
    norm_txt_path = out_dir / f"{bcv_chapter}.txt"

    manifest = {
        "book": book,
        "chapter": chapter,
        "bcv_chapter": bcv_chapter,
        "total_verses": len(raw_verses),
        "total_segments": len(normalized_segments),
        "headings_count": len(headings),
        "digits_expanded_count": digits_expanded_count,
        "audio_file": raw_data.get("audio_file", f"data/raw/audio/{book}/{bcv_chapter}.mp3"),
        "segments": normalized_segments,
    }

    with open(norm_json_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    with open(norm_txt_path, "w", encoding="utf-8") as f:
        f.write(full_transcript + "\n")

    return manifest


def main():
    parser = argparse.ArgumentParser(description="Normalize verse text and prepare alignment manifests.")
    parser.add_argument("--book", type=str, default="GEN", help="Book code (default: GEN)")
    args = parser.parse_args()

    book_dir = RAW_TEXT_DIR / args.book
    if not book_dir.exists():
        print(f"Error: Raw text directory not found: {book_dir}", file=sys.stderr)
        sys.exit(1)

    raw_files = sorted(book_dir.glob(f"{args.book}_*.json"))
    print(f"[02_normalize_text] Processing {len(raw_files)} chapters for {args.book}...")

    out_dir = INTERIM_NORM_DIR / args.book
    total_verses = 0
    total_headings = 0
    total_digits_expanded = 0

    for fpath in raw_files:
        manifest = normalize_chapter(fpath, out_dir)
        total_verses += manifest["total_verses"]
        total_headings += manifest["headings_count"]
        total_digits_expanded += manifest["digits_expanded_count"]

    print("\n=======================================================")
    print(f"TEXT NORMALIZATION COMPLETE FOR {args.book}:")
    print(f"  Chapters Processed:        {len(raw_files)}")
    print(f"  Total Verses Normalized:   {total_verses}")
    print(f"  Headings Marked with (*):  {total_headings}")
    print(f"  Verses with Digits Expanded: {total_digits_expanded}")
    print(f"  Outputs Saved to:          {out_dir}")
    print("=======================================================")


if __name__ == "__main__":
    main()
