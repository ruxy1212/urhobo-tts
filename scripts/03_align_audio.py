#!/usr/bin/env python3
"""
scripts/03_align_audio.py

Phase 4.2 — Forced Alignment & Temporal Synchronization Engine.

Aligns chapter audio WAVs (16kHz mono) with romanized alignment prep manifests
using Meta MMS CTC forced aligner (via ctc-forced-aligner).
Supports GPU/CUDA acceleration for Kaggle execution (or CPU fallback).

Outputs word-level and verse-level timestamps with length-normalized
confidence scoring to:
  data/interim/alignments/{book}/{bcv_chapter}_align.json
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

# Ensure UTF-8 console output for Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent
ALIGN_PREP_DIR = REPO_ROOT / "data" / "interim" / "alignment_prep"
INTERIM_WAV_DIR = REPO_ROOT / "data" / "interim" / "wav"
ALIGNMENTS_DIR = REPO_ROOT / "data" / "interim" / "alignments"


def align_chapter(
    prep_json_path: Path,
    wav_path: Path,
    alignment_model: Any,
    alignment_tokenizer: Any,
    device: str,
    batch_size: int = 16,
    confidence_threshold: float = -0.20,
) -> Dict[str, Any]:
    """
    Runs CTC forced alignment on a single chapter and maps word timestamps back to verses.
    """
    import torch
    from ctc_forced_aligner import (
        load_audio,
        generate_emissions,
        preprocess_text,
        get_alignments,
        get_spans,
        postprocess_results,
    )

    with open(prep_json_path, "r", encoding="utf-8") as f:
        prep_data = json.load(f)

    bcv_chapter = prep_data["bcv_chapter"]
    book = prep_data["book"]
    chapter_num = prep_data["chapter"]
    full_alignment_text = prep_data["full_alignment_text"]
    prep_segments = prep_data["segments"]
    expected_words = prep_data["chapter_words_romanized"]

    # 1. Load audio waveform
    audio_waveform = load_audio(str(wav_path), alignment_model.dtype, alignment_model.device)
    audio_duration_sec = audio_waveform.shape[-1] / 16000.0

    # 2. Generate CTC emissions
    emissions, stride = generate_emissions(
        alignment_model,
        audio_waveform,
        batch_size=batch_size,
    )

    # 3. Preprocess text (already romanized in Step 4.1)
    tokens_starred, text_starred = preprocess_text(
        full_alignment_text,
        romanize=False,
        language="eng",
    )

    # 4. Viterbi alignment
    segments, scores, blank_token = get_alignments(
        emissions,
        tokens_starred,
        alignment_tokenizer,
    )

    # 5. Extract spans & postprocess to word timestamps
    spans = get_spans(tokens_starred, segments, blank_token)
    raw_word_results = postprocess_results(text_starred, spans, stride, scores)

    # Filter out wildcard star tokens to retain real spoken words
    real_words = [
        w for w in raw_word_results
        if (w.get("text") or w.get("word") or "").strip() not in ("<star>", "*", "")
    ]

    # Map timestamps back to verse segments
    aligned_verses: List[Dict[str, Any]] = []
    aligned_headings: List[Dict[str, Any]] = []

    total_words_aligned = len(real_words)
    scores_list = [float(w.get("score", 0.0)) for w in real_words if "score" in w]
    chapter_avg_score = round(sum(scores_list) / len(scores_list), 4) if scores_list else 0.0

    # Build word index lookup
    for seg in prep_segments:
        seg_type = seg.get("type", "verse")
        bcv_id = seg.get("bcv_id", "")

        if seg_type == "heading":
            word_span = seg.get("word_span")
            h_words = []
            if word_span and word_span[0] is not None:
                w_start_idx, w_end_idx = word_span[0], word_span[1]
                for i in range(w_start_idx, min(w_end_idx + 1, len(real_words))):
                    aligned_w = real_words[i]
                    h_words.append({
                        "word_index": i,
                        "word_romanized": aligned_w.get("text") or aligned_w.get("word", ""),
                        "start_sec": round(float(aligned_w.get("start", 0.0)), 3),
                        "end_sec": round(float(aligned_w.get("end", 0.0)), 3),
                    })
            h_start = h_words[0]["start_sec"] if h_words else 0.0
            h_end = h_words[-1]["end_sec"] if h_words else 0.0
            aligned_headings.append({
                "bcv_id": bcv_id,
                "type": "heading",
                "text_urhobo": seg.get("text_urhobo", ""),
                "text_romanized": seg.get("text_romanized", ""),
                "start_sec": h_start,
                "end_sec": h_end,
                "duration_sec": round(h_end - h_start, 3),
                "words": h_words,
            })
            continue

        verse_num = seg.get("verse_num", 1)
        word_span = seg.get("word_span")
        text_urhobo = seg.get("text_urhobo", "")
        text_romanized = seg.get("text_romanized", "")
        verse_words_meta = seg.get("words", [])

        if not word_span or word_span[0] is None:
            aligned_verses.append({
                "bcv_id": bcv_id,
                "verse_num": verse_num,
                "status": "NO_WORDS",
                "confidence_score": -1.0,
                "text_urhobo": text_urhobo,
                "start_sec": 0.0,
                "end_sec": 0.0,
                "duration_sec": 0.0,
                "words": [],
            })
            continue

        w_start_idx, w_end_idx = word_span[0], word_span[1]

        # Extract slice of aligned words corresponding to this verse
        verse_word_records: List[Dict[str, Any]] = []
        verse_scores: List[float] = []

        for i in range(w_start_idx, min(w_end_idx + 1, len(real_words))):
            aligned_w = real_words[i]
            orig_meta = verse_words_meta[i - w_start_idx] if (i - w_start_idx) < len(verse_words_meta) else {}
            w_score = round(float(aligned_w.get("score", 0.0)), 4)
            verse_scores.append(w_score)
            word_str = aligned_w.get("text") or aligned_w.get("word", "")

            verse_word_records.append({
                "word_index": i,
                "word_urhobo": orig_meta.get("urhobo", word_str),
                "word_romanized": word_str,
                "start_sec": round(float(aligned_w.get("start", 0.0)), 3),
                "end_sec": round(float(aligned_w.get("end", 0.0)), 3),
                "duration_sec": round(float(aligned_w.get("end", 0.0)) - float(aligned_w.get("start", 0.0)), 3),
                "confidence_score": w_score,
            })

        if verse_word_records:
            v_start = verse_word_records[0]["start_sec"]
            v_end = verse_word_records[-1]["end_sec"]
            v_dur = round(v_end - v_start, 3)
            v_score = round(sum(verse_scores) / len(verse_scores), 4) if verse_scores else 0.0
            is_flagged = v_score < confidence_threshold
            v_status = "FLAGGED_LOW_CONFIDENCE" if is_flagged else "HIGH_CONFIDENCE"
        else:
            v_start = 0.0
            v_end = 0.0
            v_dur = 0.0
            v_score = -1.0
            v_status = "ALIGNMENT_FAILED"

        aligned_verses.append({
            "bcv_id": bcv_id,
            "verse_num": verse_num,
            "text_urhobo": text_urhobo,
            "text_romanized": text_romanized,
            "start_sec": v_start,
            "end_sec": v_end,
            "duration_sec": v_dur,
            "confidence_score": v_score,
            "status": v_status,
            "word_count": len(verse_word_records),
            "words": verse_word_records,
        })

    flagged_verses = [v for v in aligned_verses if v["status"] != "HIGH_CONFIDENCE"]

    result_manifest = {
        "book": book,
        "chapter": chapter_num,
        "bcv_chapter": bcv_chapter,
        "audio_wav": str(wav_path.as_posix()),
        "audio_duration_sec": round(audio_duration_sec, 2),
        "total_verses": len(aligned_verses),
        "total_headings": len(aligned_headings),
        "total_words_expected": len(expected_words),
        "total_words_aligned": total_words_aligned,
        "chapter_average_confidence": chapter_avg_score,
        "confidence_threshold": confidence_threshold,
        "flagged_verses_count": len(flagged_verses),
        "verses": aligned_verses,
        "headings": aligned_headings,
    }

    return result_manifest


def main():
    parser = argparse.ArgumentParser(description="Run MMS CTC forced alignment on chapter audio.")
    parser.add_argument("--book", type=str, default="GEN", help="Book code (default: GEN)")
    parser.add_argument("--chapter", type=str, default=None, help="Specific chapter to align, e.g. 1 or GEN_001")
    parser.add_argument("--device", type=str, default=None, help="Device: cuda or cpu (auto-detected if None)")
    parser.add_argument("--batch-size", type=int, default=16, help="Inference batch size (default: 16)")
    parser.add_argument("--confidence-threshold", type=float, default=-0.20, help="Score cutoff (default: -0.20)")
    parser.add_argument("--model-name", type=str, default="MahmoudAshraf/mms-300m-1130-forced-aligner")
    parser.add_argument("--force", action="store_true", help="Force re-alignment of existing files")
    args = parser.parse_args()

    # Verify dependencies
    try:
        import torch
        from ctc_forced_aligner import load_alignment_model
    except ImportError as e:
        print(f"Error: Missing required packages: {e}", file=sys.stderr)
        print("Please run: pip install ctc-forced-aligner torch torchaudio", file=sys.stderr)
        sys.exit(1)

    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[03_align_audio] Using device: {device} (CUDA available: {torch.cuda.is_available()})")
    if device == "cuda":
        print(f"[03_align_audio] GPU: {torch.cuda.get_device_name(0)}")

    book_prep_dir = ALIGN_PREP_DIR / args.book
    book_wav_dir = INTERIM_WAV_DIR / args.book
    book_out_dir = ALIGNMENTS_DIR / args.book

    if not book_prep_dir.exists():
        print(f"Error: Alignment prep directory not found: {book_prep_dir}", file=sys.stderr)
        sys.exit(1)

    book_out_dir.mkdir(parents=True, exist_ok=True)

    if args.chapter:
        ch_str = f"{int(args.chapter):03d}" if args.chapter.isdigit() else args.chapter.replace(f"{args.book}_", "")
        bcv = f"{args.book}_{ch_str}"
        prep_files = [book_prep_dir / f"{bcv}_prep.json"]
    else:
        prep_files = sorted(book_prep_dir.glob(f"{args.book}_*_prep.json"))

    print(f"[03_align_audio] Loading MMS CTC alignment model: {args.model_name}...")
    dtype = torch.float16 if device == "cuda" else torch.float32
    alignment_model, alignment_tokenizer = load_alignment_model(
        device=device,
        dtype=dtype,
        model_path=args.model_name,
    )

    print(f"[03_align_audio] Aligning {len(prep_files)} chapters for {args.book}...")
    start_time = time.time()

    completed_records = []
    total_flagged_verses = 0
    total_aligned_verses = 0

    for idx, prep_path in enumerate(prep_files, start=1):
        with open(prep_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        bcv_chapter = meta["bcv_chapter"]
        wav_path = book_wav_dir / f"{bcv_chapter}.wav"
        out_align_path = book_out_dir / f"{bcv_chapter}_align.json"

        if out_align_path.exists() and not args.force:
            print(f"  [{idx:02d}/{len(prep_files)}] Skipping (already exists): {bcv_chapter}_align.json")
            with open(out_align_path, "r", encoding="utf-8") as f:
                completed_records.append(json.load(f))
            continue

        if not wav_path.exists():
            print(f"  [{idx:02d}/{len(prep_files)}] Warning: WAV not found: {wav_path}", file=sys.stderr)
            continue

        ch_t0 = time.time()
        res = align_chapter(
            prep_path,
            wav_path,
            alignment_model,
            alignment_tokenizer,
            device=device,
            batch_size=args.batch_size,
            confidence_threshold=args.confidence_threshold,
        )
        ch_elapsed = time.time() - ch_t0

        with open(out_align_path, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2, ensure_ascii=False)

        completed_records.append(res)
        total_flagged_verses += res["flagged_verses_count"]
        total_aligned_verses += res["total_verses"]

        print(
            f"  [{idx:02d}/{len(prep_files)}] Aligned {bcv_chapter} in {ch_elapsed:.1f}s | "
            f"Verses: {res['total_verses']} | Avg Score: {res['chapter_average_confidence']:.3f} | "
            f"Flagged: {res['flagged_verses_count']}"
        )

    total_time = time.time() - start_time

    # Save corpus summary report
    summary = {
        "book": args.book,
        "device": device,
        "total_chapters_aligned": len(completed_records),
        "total_verses_aligned": total_aligned_verses,
        "total_flagged_verses": total_flagged_verses,
        "overall_flagged_rate": round(total_flagged_verses / total_aligned_verses, 4) if total_aligned_verses else 0,
        "confidence_threshold": args.confidence_threshold,
        "total_wall_time_sec": round(total_time, 2),
    }

    summary_path = book_out_dir / f"{args.book}_alignment_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print("\n=======================================================")
    print(f"FORCED ALIGNMENT RUN COMPLETE FOR {args.book}:")
    print(f"  Device:                 {device}")
    print(f"  Chapters Processed:     {len(completed_records)}")
    print(f"  Total Verses Aligned:   {total_aligned_verses}")
    print(f"  Flagged (< {args.confidence_threshold}):     {total_flagged_verses}")
    print(f"  Total Time:             {total_time:.1f}s ({total_time / 60.0:.2f} mins)")
    print(f"  Summary Report:         {summary_path}")
    print("=======================================================")


if __name__ == "__main__":
    main()
