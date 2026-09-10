#!/usr/bin/env python3
"""
scripts/04_slice_audio.py

Phase 5.1 — Audio Slicer & Acoustic Edge Conditioner.

Slices 16kHz chapter WAV audio into verse-level clips using alignment timestamps.
Applies:
  - 50ms boundary padding at start and end
  - 10ms raised-cosine (half-Hann) fade-in and fade-out envelope to eliminate clicks/pops
  - Acoustic quality filtering (confidence threshold >= -0.85, duration between 1.0s and 18.0s)

Outputs:
  Clean training clips:  data/processed/segments/{book}/{bcv_id}.wav
  Slicing audit report:  data/processed/segments/{book}_slicing_report.json
"""

import argparse
import array
import json
import math
import os
import sys
import time
import wave
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Ensure UTF-8 console output for Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent
WAV_DIR = REPO_ROOT / "data" / "interim" / "wav"
ALIGN_DIR = REPO_ROOT / "data" / "interim" / "alignments"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
SEGMENTS_DIR = PROCESSED_DIR / "segments"
QUARANTINE_DIR = PROCESSED_DIR / "quarantine"


def apply_raised_cosine_fade(samples: array.array, fade_samples: int) -> None:
    """
    Applies a 10ms raised-cosine (half-Hann) fade-in and fade-out in place to eliminate edge clicks.
    """
    length = len(samples)
    if length == 0 or fade_samples <= 0:
        return

    n_fade = min(fade_samples, length // 2)

    # Fade in: 0.5 * (1 - cos(pi * i / N)) from 0 to 1
    for i in range(n_fade):
        factor = 0.5 * (1.0 - math.cos(math.pi * i / n_fade))
        samples[i] = int(round(samples[i] * factor))

    # Fade out: 0.5 * (1 + cos(pi * i / N)) from 1 to 0
    for i in range(n_fade):
        factor = 0.5 * (1.0 + math.cos(math.pi * i / n_fade))
        idx = length - n_fade + i
        samples[idx] = int(round(samples[idx] * factor))


def slice_verse_clip(
    chapter_samples: array.array,
    framerate: int,
    start_sec: float,
    end_sec: float,
    pad_ms: float = 50.0,
    fade_ms: float = 10.0,
) -> Tuple[array.array, float]:
    """
    Cuts a verse segment from chapter samples, applies 50ms padding and 10ms raised-cosine fade.
    Returns (segment_samples, actual_duration_sec).
    """
    total_frames = len(chapter_samples)
    pad_samples = int((pad_ms / 1000.0) * framerate)
    fade_samples = int((fade_ms / 1000.0) * framerate)

    start_idx = max(0, int(start_sec * framerate) - pad_samples)
    end_idx = min(total_frames, int(end_sec * framerate) + pad_samples)

    segment = array.array("h", chapter_samples[start_idx:end_idx])
    apply_raised_cosine_fade(segment, fade_samples)

    duration_sec = round(len(segment) / float(framerate), 3)
    return segment, duration_sec


def process_chapter(
    bcv_chapter: str,
    wav_path: Path,
    align_path: Path,
    out_book_dir: Path,
    quarantine_book_dir: Path,
    confidence_threshold: float = -0.85,
    min_duration: float = 1.0,
    max_duration: float = 18.0,
    pad_ms: float = 50.0,
    fade_ms: float = 10.0,
    force: bool = False,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Processes all verses of one chapter: slicing, filtering, and writing clips.
    Returns (accepted_records, quarantined_records).
    """
    with open(align_path, "r", encoding="utf-8") as f:
        align_data = json.load(f)

    # Load chapter audio
    with wave.open(str(wav_path), "rb") as wf:
        nchannels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        nframes = wf.getnframes()
        raw_bytes = wf.readframes(nframes)

    samples = array.array("h")
    samples.frombytes(raw_bytes)

    accepted_records: List[Dict[str, Any]] = []
    quarantined_records: List[Dict[str, Any]] = []

    for v in align_data.get("verses", []):
        bcv_id = v["bcv_id"]
        verse_num = v.get("verse_num", 1)
        start_sec = v.get("start_sec", 0.0)
        end_sec = v.get("end_sec", 0.0)
        raw_dur = v.get("duration_sec", 0.0)
        score = v.get("confidence_score", -1.0)
        status = v.get("status", "")
        text_urhobo = v.get("text_urhobo", "").strip()
        text_romanized = v.get("text_romanized", "").strip()
        words_count = v.get("word_count", len(text_urhobo.split()))

        # Evaluation criteria
        reasons = []
        if status == "ALIGNMENT_FAILED" or score <= -2.0:
            reasons.append("alignment_failed")
        if score < confidence_threshold:
            reasons.append(f"low_confidence ({score:.3f} < {confidence_threshold})")
        if raw_dur < min_duration:
            reasons.append(f"too_short ({raw_dur:.2f}s < {min_duration}s)")
        elif raw_dur > max_duration:
            reasons.append(f"too_long ({raw_dur:.2f}s > {max_duration}s)")
        if not text_urhobo or text_urhobo == "*":
            reasons.append("empty_or_invalid_text")

        # Slice clip
        clip_samples, clip_dur = slice_verse_clip(
            samples, framerate, start_sec, end_sec, pad_ms=pad_ms, fade_ms=fade_ms
        )

        record = {
            "id": bcv_id,
            "book": align_data.get("book", "GEN"),
            "chapter": align_data.get("chapter", 1),
            "verse": verse_num,
            "text": text_urhobo,
            "text_romanized": text_romanized,
            "start_sec": start_sec,
            "end_sec": end_sec,
            "duration_sec": clip_dur,
            "confidence_score": score,
            "word_count": words_count,
            "char_count": len(text_urhobo),
            "pad_ms": pad_ms,
            "fade_ms": fade_ms,
        }

        if reasons:
            record["quarantine_reasons"] = reasons
            quarantined_records.append(record)
        else:
            out_clip_path = out_book_dir / f"{bcv_id}.wav"
            record["audio_path"] = str(out_clip_path.relative_to(REPO_ROOT)).replace("\\", "/")

            if not out_clip_path.exists() or force:
                with wave.open(str(out_clip_path), "wb") as out_wf:
                    out_wf.setnchannels(nchannels)
                    out_wf.setsampwidth(sampwidth)
                    out_wf.setframerate(framerate)
                    out_wf.writeframes(clip_samples.tobytes())

            accepted_records.append(record)

    return accepted_records, quarantined_records


def main():
    parser = argparse.ArgumentParser(description="Slice chapter WAVs into conditioned verse clips.")
    parser.add_argument("--book", type=str, default="GEN", help="Book code (default: GEN)")
    parser.add_argument("--confidence-threshold", type=float, default=-0.85, help="Cutoff score (default: -0.85)")
    parser.add_argument("--min-duration", type=float, default=1.0, help="Min duration in sec (default: 1.0)")
    parser.add_argument("--max-duration", type=float, default=18.0, help="Max duration in sec (default: 18.0)")
    parser.add_argument("--pad-ms", type=float, default=50.0, help="Boundary padding ms (default: 50.0)")
    parser.add_argument("--fade-ms", type=float, default=10.0, help="Fade envelope ms (default: 10.0)")
    parser.add_argument("--force", action="store_true", help="Force re-slicing existing WAV files")
    args = parser.parse_args()

    book_wav_dir = WAV_DIR / args.book
    book_align_dir = ALIGN_DIR / args.book
    out_book_dir = SEGMENTS_DIR / args.book
    quarantine_book_dir = QUARANTINE_DIR / args.book

    if not book_wav_dir.exists() or not book_align_dir.exists():
        print(f"Error: WAV or Alignment directory not found for {args.book}", file=sys.stderr)
        sys.exit(1)

    out_book_dir.mkdir(parents=True, exist_ok=True)
    quarantine_book_dir.mkdir(parents=True, exist_ok=True)

    align_files = sorted(book_align_dir.glob(f"{args.book}_*_align.json"))
    print(f"[04_slice_audio] Processing {len(align_files)} chapters for {args.book}...")
    print(f"  Quality Cutoff:      confidence >= {args.confidence_threshold}")
    print(f"  Duration Bounds:     {args.min_duration}s - {args.max_duration}s")
    print(f"  Boundary Padding:    {args.pad_ms}ms with {args.fade_ms}ms raised-cosine fade envelope")

    all_accepted: List[Dict[str, Any]] = []
    all_quarantined: List[Dict[str, Any]] = []

    t0 = time.time()

    for idx, align_path in enumerate(align_files, start=1):
        bcv_chapter = align_path.stem.replace("_align", "")
        wav_path = book_wav_dir / f"{bcv_chapter}.wav"

        if not wav_path.exists():
            print(f"  Warning: WAV not found: {wav_path.name}", file=sys.stderr)
            continue

        acc, quar = process_chapter(
            bcv_chapter,
            wav_path,
            align_path,
            out_book_dir,
            quarantine_book_dir,
            confidence_threshold=args.confidence_threshold,
            min_duration=args.min_duration,
            max_duration=args.max_duration,
            pad_ms=args.pad_ms,
            fade_ms=args.fade_ms,
            force=args.force,
        )

        all_accepted.extend(acc)
        all_quarantined.extend(quar)

        if idx % 10 == 0 or idx == len(align_files):
            print(f"  [{idx:02d}/{len(align_files)}] {bcv_chapter}: Accepted={len(acc)}, Quarantined={len(quar)}")

    elapsed = time.time() - t0

    total_eval = len(all_accepted) + len(all_quarantined)
    total_acc_sec = sum(r["duration_sec"] for r in all_accepted)
    total_quar_sec = sum(r["duration_sec"] for r in all_quarantined)
    avg_dur = round(total_acc_sec / len(all_accepted), 2) if all_accepted else 0.0
    avg_score = round(sum(r["confidence_score"] for r in all_accepted) / len(all_accepted), 4) if all_accepted else 0.0

    report = {
        "book": args.book,
        "total_verses_evaluated": total_eval,
        "accepted_verses_count": len(all_accepted),
        "quarantined_verses_count": len(all_quarantined),
        "acceptance_rate": round(len(all_accepted) / total_eval, 4) if total_eval else 0.0,
        "total_audio_duration_sec": round(total_acc_sec, 2),
        "total_audio_duration_hours": round(total_acc_sec / 3600.0, 2),
        "average_verse_duration_sec": avg_dur,
        "average_confidence_score": avg_score,
        "filter_parameters": {
            "confidence_threshold": args.confidence_threshold,
            "min_duration_sec": args.min_duration,
            "max_duration_sec": args.max_duration,
            "pad_ms": args.pad_ms,
            "fade_ms": args.fade_ms,
        },
        "quarantined_verses": all_quarantined,
    }

    report_path = SEGMENTS_DIR / f"{args.book}_slicing_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n=======================================================")
    print(f"AUDIO SLICING COMPLETE FOR {args.book}:")
    print(f"  Total Verses Evaluated:    {total_eval}")
    print(f"  Clean Accepted Clips:      {len(all_accepted)} ({report['acceptance_rate']*100:.1f}%)")
    print(f"  Quarantined Clips:         {len(all_quarantined)}")
    print(f"  Accepted Audio Duration:   {report['total_audio_duration_hours']} hours ({round(total_acc_sec/60.0, 1)} mins)")
    print(f"  Average Clip Duration:     {avg_dur} seconds")
    print(f"  Average Confidence Score:  {avg_score}")
    print(f"  Output Directory:          {out_book_dir}")
    print(f"  Slicing Report:            {report_path}")
    print(f"  Elapsed Processing Time:   {elapsed:.2f} seconds")
    print("=======================================================")


if __name__ == "__main__":
    main()
