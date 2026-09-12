#!/usr/bin/env python3
"""
scripts/05_assemble_dataset.py

Phase 5.2 — Dataset Assembly & Stratified Train/Dev/Test Split.

Assembles processed verse audio clips into model training manifests:
  - train.jsonl (~85% audio duration)
  - dev.jsonl   (~7.5% audio duration)
  - test.jsonl  (~7.5% audio duration, enriched with mobile curriculum phrases)
  - metadata.csv (Universal LJSpeech format: clip_id|text|normalized_text)
  - dataset_summary.json (Audit & quality report)

Splits are strictly chapter-level to prevent data leakage (acoustic room / pitch contour overlap).
Curriculum vocabulary from app_content/curriculum_vocab.tsv is cross-referenced and tagged.
"""

import argparse
import json
import re
import sys
import time
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# Ensure UTF-8 console output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent
SEGMENTS_DIR = REPO_ROOT / "data" / "processed" / "segments"
ALIGN_DIR = REPO_ROOT / "data" / "interim" / "alignments"
NORM_DIR = REPO_ROOT / "data" / "interim" / "normalized_text"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
CURRICULUM_PATH = REPO_ROOT / "app_content" / "curriculum_vocab.tsv"


def load_curriculum_vocab(tsv_path: Path) -> List[Dict[str, str]]:
    """
    Loads target curriculum vocabulary items from app_content/curriculum_vocab.tsv.
    """
    if not tsv_path.exists():
        print(f"Warning: Curriculum vocab not found at {tsv_path}", file=sys.stderr)
        return []

    items = []
    with open(tsv_path, "r", encoding="utf-8") as f:
        headers = f.readline().strip().split("\t")
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            parts = line_str.split("\t")
            if len(parts) >= 5:
                items.append({
                    "id": parts[0],
                    "raw": parts[1],
                    "toned": parts[2],
                    "english": parts[3],
                    "category": parts[4],
                    "audio_source": parts[5] if len(parts) > 5 else "",
                    "status": parts[6] if len(parts) > 6 else "",
                })
    return items


def load_normalized_transcripts(book: str) -> Dict[str, Dict[str, Any]]:
    """
    Loads normalized verse transcripts keyed by bcv_id.
    """
    norm_verses = {}
    book_norm_dir = NORM_DIR / book
    if not book_norm_dir.exists():
        return norm_verses

    for json_file in sorted(book_norm_dir.glob(f"{book}_*.json")):
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        for seg in data.get("segments", []):
            if seg.get("type") == "verse":
                norm_verses[seg["bcv_id"]] = seg
    return norm_verses


def match_curriculum_in_verse(
    bcv_id: str,
    verse_text: str,
    curriculum: List[Dict[str, str]]
) -> List[Dict[str, str]]:
    """
    Matches a verse's text against the curriculum seed vocabulary.
    Returns list of matched curriculum entries.
    """
    matches = []
    text_lower = verse_text.lower()

    for item in curriculum:
        # 1. Direct bcv_id attribution in audio_source
        if item["audio_source"].startswith("corpus:"):
            target_bcv = item["audio_source"].replace("corpus:", "").strip()
            if bcv_id == target_bcv:
                matches.append({
                    "vocab_id": item["id"],
                    "match_type": "exact_corpus_phrase",
                    "term": item["raw"],
                    "english": item["english"],
                })
                continue

        # 2. Whole-word lexical matching for words (len >= 3, excluding alphabet letters)
        if len(item["raw"]) >= 3 and item["category"] not in ("alphabet", "phrase_corpus"):
            pattern = r"\b" + re.escape(item["raw"].lower()) + r"\b"
            if re.search(pattern, text_lower):
                matches.append({
                    "vocab_id": item["id"],
                    "match_type": "lexical_word",
                    "term": item["raw"],
                    "english": item["english"],
                })

    return matches


def collect_accepted_clips(
    book: str,
    curriculum: List[Dict[str, str]],
    norm_verses: Dict[str, Dict[str, Any]]
) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, float]]:
    """
    Scans the sliced audio files in data/processed/segments/{book} and associates them
    with alignment metadata, normalized text, and curriculum tags.
    Returns:
      - chapter_clips: { chapter_name: [ clip_records ] }
      - chapter_durations: { chapter_name: total_duration_sec }
    """
    book_segments_dir = SEGMENTS_DIR / book
    book_align_dir = ALIGN_DIR / book

    existing_wavs = set(p.stem for p in book_segments_dir.glob("*.wav"))
    chapter_clips: Dict[str, List[Dict[str, Any]]] = {}
    chapter_durations: Dict[str, float] = {}

    for align_file in sorted(book_align_dir.glob(f"{book}_*_align.json")):
        chapter_name = align_file.stem.replace("_align", "")
        with open(align_file, "r", encoding="utf-8") as f:
            align_data = json.load(f)

        chapter_clips[chapter_name] = []
        tot_dur = 0.0

        for verse in align_data.get("verses", []):
            bcv_id = verse["bcv_id"]
            if bcv_id in existing_wavs:
                wav_path = book_segments_dir / f"{bcv_id}.wav"
                rel_audio_path = str(wav_path.relative_to(REPO_ROOT)).replace("\\", "/")

                # Text retrieval
                norm_entry = norm_verses.get(bcv_id, {})
                text_raw = verse.get("text_urhobo", "")
                text_norm = norm_entry.get("text_normalized", text_raw)

                # Duration calculation (aligned span + 50ms start/end pad = +0.10s)
                dur = round(verse.get("end_sec", 0.0) - verse.get("start_sec", 0.0) + 0.10, 2)
                score = round(verse.get("confidence_score", 0.0), 4)

                # Cross-reference curriculum
                curriculum_matches = match_curriculum_in_verse(bcv_id, text_raw, curriculum)

                record = {
                    "id": bcv_id,
                    "book": align_data.get("book", book),
                    "chapter": align_data.get("chapter", 1),
                    "verse": verse.get("verse_num", 1),
                    "audio": rel_audio_path,
                    "text": text_raw,
                    "normalized_text": text_norm,
                    "duration": dur,
                    "confidence": score,
                    "curriculum_tags": [m["vocab_id"] for m in curriculum_matches],
                    "curriculum_details": curriculum_matches,
                }
                chapter_clips[chapter_name].append(record)
                tot_dur += dur

        chapter_durations[chapter_name] = tot_dur

    return chapter_clips, chapter_durations


def optimize_splits(
    chapter_clips: Dict[str, List[Dict[str, Any]]],
    chapter_durations: Dict[str, float],
    target_train_pct: float = 0.85,
    target_dev_pct: float = 0.075,
    target_test_pct: float = 0.075,
) -> Tuple[List[str], List[str], List[str]]:
    """
    Determines optimal chapter split for Train, Dev, and Test.
    Constraints:
      - Test set maximizes curriculum phrases (from corpus-derived app items)
      - Test set audio duration is close to target_test_pct (~7.5%)
      - Dev set audio duration is close to target_dev_pct (~7.5%)
      - Remaining chapters form Train set (~85%)
    """
    total_duration = sum(chapter_durations.values())
    target_test_sec = total_duration * target_test_pct
    target_dev_sec = total_duration * target_dev_pct

    # Count corpus-derived phrases per chapter
    chap_phrases: Dict[str, int] = {}
    for chap, clips in chapter_clips.items():
        count = 0
        for clip in clips:
            if any(m["match_type"] == "exact_corpus_phrase" for m in clip["curriculum_details"]):
                count += 1
        chap_phrases[chap] = count

    # Chapters with corpus phrases are prime candidates for test set
    test_candidates = [c for c, count in chap_phrases.items() if count > 0]

    best_test_combo = None
    best_test_score = -999999
    best_test_diff = 999999

    for k in (3, 4, 5):
        for combo in combinations(test_candidates, k):
            dur = sum(chapter_durations[c] for c in combo)
            phrases = sum(chap_phrases[c] for c in combo)
            diff = abs(dur - target_test_sec)
            # Acceptable within 90s tolerance
            if diff < 90.0:
                # Prioritize more phrases, then closer duration
                score = phrases * 1000 - diff
                if score > best_test_score:
                    best_test_score = score
                    best_test_combo = combo
                    best_test_diff = diff

    if not best_test_combo:
        # Fallback: take top 4 chapters by phrase count closest to target
        test_candidates.sort(key=lambda c: (chap_phrases[c], -abs(chapter_durations[c] - target_test_sec / 4)), reverse=True)
        best_test_combo = tuple(test_candidates[:4])

    test_chapters = set(best_test_combo)
    remaining = [c for c in chapter_clips.keys() if c not in test_chapters]

    # Select Dev set from remaining chapters to match target_dev_sec
    best_dev_combo = None
    best_dev_diff = 999999

    for k in (3, 4, 5):
        for combo in combinations(remaining, k):
            dur = sum(chapter_durations[c] for c in combo)
            diff = abs(dur - target_dev_sec)
            if diff < best_dev_diff:
                best_dev_diff = diff
                best_dev_combo = combo

    dev_chapters = set(best_dev_combo)
    train_chapters = [c for c in remaining if c not in dev_chapters]

    return train_chapters, sorted(list(dev_chapters)), sorted(list(test_chapters))


def write_manifest_files(
    splits: Dict[str, List[Dict[str, Any]]],
    output_dir: Path
) -> None:
    """
    Writes train.jsonl, dev.jsonl, test.jsonl, and metadata.csv.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Write JSONL splits
    for split_name in ("train", "dev", "test"):
        records = splits[split_name]
        jsonl_path = output_dir / f"{split_name}.jsonl"
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for rec in records:
                out_rec = {
                    "id": rec["id"],
                    "audio": rec["audio"],
                    "text": rec["text"],
                    "normalized_text": rec["normalized_text"],
                    "duration": rec["duration"],
                    "confidence": rec["confidence"],
                    "curriculum_tags": rec["curriculum_tags"],
                }
                f.write(json.dumps(out_rec, ensure_ascii=False) + "\n")

    # 2. Write metadata.csv (Universal LJSpeech format: clip_id|text|normalized_text)
    metadata_path = output_dir / "metadata.csv"
    with open(metadata_path, "w", encoding="utf-8") as f:
        f.write("clip_id|text|normalized_text\n")
        for split_name in ("train", "dev", "test"):
            for rec in splits[split_name]:
                # Clean pipes or carriage returns if any
                clean_raw = rec["text"].replace("|", " ").replace("\n", " ")
                clean_norm = rec["normalized_text"].replace("|", " ").replace("\n", " ")
                f.write(f"{rec['id']}|{clean_raw}|{clean_norm}\n")


def generate_summary_report(
    splits: Dict[str, List[Dict[str, Any]]],
    split_chapters: Dict[str, List[str]],
    curriculum: List[Dict[str, str]],
    output_path: Path
) -> Dict[str, Any]:
    """
    Builds and writes a comprehensive audit report for dataset assembly.
    """
    summary: Dict[str, Any] = {
        "dataset_name": "urhobo-genesis-tts",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_clips": sum(len(clips) for clips in splits.values()),
        "total_duration_sec": round(sum(sum(c["duration"] for c in clips) for clips in splits.values()), 2),
        "total_duration_hours": round(sum(sum(c["duration"] for c in clips) for clips in splits.values()) / 3600, 2),
        "splits": {},
        "curriculum_coverage": {},
    }

    tot_sec = summary["total_duration_sec"]

    for name in ("train", "dev", "test"):
        clips = splits[name]
        durs = [c["duration"] for c in clips]
        confs = [c["confidence"] for c in clips]
        dur_sum = round(sum(durs), 2)

        curr_tags = set()
        for c in clips:
            curr_tags.update(c["curriculum_tags"])

        summary["splits"][name] = {
            "chapters_count": len(split_chapters[name]),
            "chapters": split_chapters[name],
            "clips_count": len(clips),
            "duration_sec": dur_sum,
            "duration_hours": round(dur_sum / 3600, 2),
            "duration_percentage": round((dur_sum / tot_sec) * 100, 2) if tot_sec > 0 else 0.0,
            "average_duration_sec": round(dur_sum / len(clips), 2) if clips else 0.0,
            "min_duration_sec": min(durs) if durs else 0.0,
            "max_duration_sec": max(durs) if durs else 0.0,
            "average_confidence": round(sum(confs) / len(confs), 4) if confs else 0.0,
            "curriculum_items_count": len(curr_tags),
            "curriculum_items": sorted(list(curr_tags)),
        }

    test_clips = splits["test"]
    corpus_phrases_in_test = []
    for c in test_clips:
        for m in c["curriculum_details"]:
            if m["match_type"] == "exact_corpus_phrase":
                corpus_phrases_in_test.append({
                    "bcv_id": c["id"],
                    "vocab_id": m["vocab_id"],
                    "phrase": m["term"],
                    "english": m["english"],
                })

    summary["curriculum_coverage"]["total_curriculum_seed_items"] = len(curriculum)
    summary["curriculum_coverage"]["test_corpus_phrases_captured_count"] = len(corpus_phrases_in_test)
    summary["curriculum_coverage"]["test_corpus_phrases_captured"] = corpus_phrases_in_test

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    return summary


def main():
    parser = argparse.ArgumentParser(description="Assemble TTS dataset manifests with stratified splits.")
    parser.add_argument("--book", type=str, default="GEN", help="Book code (default: GEN)")
    parser.add_argument("--train-pct", type=float, default=0.85, help="Train split ratio (default: 0.85)")
    parser.add_argument("--dev-pct", type=float, default=0.075, help="Dev split ratio (default: 0.075)")
    parser.add_argument("--test-pct", type=float, default=0.075, help="Test split ratio (default: 0.075)")
    args = parser.parse_args()

    print("=================================================================")
    print("      URHOBO TTS — PHASE 5.2 DATASET ASSEMBLY & SPLITTING")
    print("=================================================================")
    print(f"Target Splits: Train={args.train_pct*100:.1f}%, Dev={args.dev_pct*100:.1f}%, Test={args.test_pct*100:.1f}%")

    t0 = time.time()

    curriculum = load_curriculum_vocab(CURRICULUM_PATH)
    print(f"  Loaded {len(curriculum)} curriculum items from {CURRICULUM_PATH.name}")

    norm_verses = load_normalized_transcripts(args.book)
    print(f"  Loaded {len(norm_verses)} normalized transcripts for {args.book}")

    chapter_clips, chapter_durations = collect_accepted_clips(args.book, curriculum, norm_verses)
    total_clips = sum(len(clips) for clips in chapter_clips.values())
    total_dur = sum(chapter_durations.values())
    print(f"  Found {total_clips} accepted clips across {len(chapter_clips)} chapters ({total_dur / 3600:.2f} hours)")

    if total_clips == 0:
        print("Error: No accepted clips found. Please run scripts/04_slice_audio.py first.", file=sys.stderr)
        sys.exit(1)

    train_chaps, dev_chaps, test_chaps = optimize_splits(
        chapter_clips,
        chapter_durations,
        target_train_pct=args.train_pct,
        target_dev_pct=args.dev_pct,
        target_test_pct=args.test_pct,
    )

    splits: Dict[str, List[Dict[str, Any]]] = {
        "train": [clip for c in train_chaps for clip in chapter_clips[c]],
        "dev": [clip for c in dev_chaps for clip in chapter_clips[c]],
        "test": [clip for c in test_chaps for clip in chapter_clips[c]],
    }
    split_chapters = {
        "train": train_chaps,
        "dev": dev_chaps,
        "test": test_chaps,
    }

    write_manifest_files(splits, PROCESSED_DIR)
    print("  Created manifests in data/processed/:")
    print(f"    - train.jsonl   ({len(splits['train'])} clips)")
    print(f"    - dev.jsonl     ({len(splits['dev'])} clips)")
    print(f"    - test.jsonl    ({len(splits['test'])} clips)")
    print("    - metadata.csv  (universal LJSpeech format)")

    summary_path = PROCESSED_DIR / "dataset_summary.json"
    summary = generate_summary_report(splits, split_chapters, curriculum, summary_path)
    print(f"  Saved audit summary report to {summary_path.name}")

    elapsed = time.time() - t0

    print("\n-----------------------------------------------------------------")
    print("                      DATASET SPLIT SUMMARY                      ")
    print("-----------------------------------------------------------------")
    for name in ("train", "dev", "test"):
        s = summary["splits"][name]
        print(f"  {name.upper():<5} : {s['clips_count']:>4} clips ({s['duration_hours']:>4.2f}h, {s['duration_percentage']:>5.2f}%) | "
              f"{s['chapters_count']:>2} chapters | {s['curriculum_items_count']:>2} curriculum items | avg conf: {s['average_confidence']:.3f}")
    print("-----------------------------------------------------------------")
    print(f"  Test Captured Corpus Phrases : {summary['curriculum_coverage']['test_corpus_phrases_captured_count']} phrases")
    for p in summary["curriculum_coverage"]["test_corpus_phrases_captured"]:
        print(f"    • [{p['bcv_id']}] {p['vocab_id']}: \"{p['phrase']}\" ({p['english']})")
    print("-----------------------------------------------------------------")
    print(f"Dataset assembly completed in {elapsed:.2f}s.")


if __name__ == "__main__":
    main()
