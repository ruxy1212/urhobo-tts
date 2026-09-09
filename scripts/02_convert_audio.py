"""
Script 02: Convert chapter MP3s to 16kHz mono WAV with EBU R128 normalization,
80Hz high-pass filtering, and duration sanity checks (Phase 3).

Inputs:
  - data/raw/audio/{book}/{book}_{chapter:03d}.mp3
  - data/interim/normalized_text/{book}/{book}_{chapter:03d}.json
Outputs:
  - data/interim/wav/{book}/{book}_{chapter:03d}.wav (16kHz mono, -23 LUFS, 80Hz HPF)
  - data/interim/wav/{book}_audio_sanity_report.json (Corpus duration sanity audit)
"""

import sys
import os
import json
import wave
import shutil
import argparse
import subprocess
from pathlib import Path

# UTF-8 console output for Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_AUDIO_DIR = REPO_ROOT / "data" / "raw" / "audio"
NORM_TEXT_DIR = REPO_ROOT / "data" / "interim" / "normalized_text"
INTERIM_WAV_DIR = REPO_ROOT / "data" / "interim" / "wav"


def get_ffmpeg_executable() -> str:
    """
    Locates FFmpeg binary from imageio-ffmpeg or system PATH.
    """
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    which_ffmpeg = shutil.which("ffmpeg")
    if which_ffmpeg:
        return which_ffmpeg
    raise RuntimeError("FFmpeg executable not found. Please install imageio-ffmpeg.")


def get_wav_duration_seconds(wav_path: Path) -> float:
    with wave.open(str(wav_path), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / float(rate)


def convert_chapter_audio(
    mp3_path: Path,
    out_wav_path: Path,
    ffmpeg_exe: str,
    target_lufs: float = -23.0,
    force: bool = False,
) -> bool:
    """
    Converts MP3 to 16kHz mono WAV with 80Hz high-pass filter and EBU R128 loudness normalization.
    """
    if out_wav_path.exists() and out_wav_path.stat().st_size > 10000 and not force:
        return False  # Already converted

    out_wav_path.parent.mkdir(parents=True, exist_ok=True)

    # Audio filter: 80Hz high-pass filter + EBU R128 loudness normalization
    af_filter = f"highpass=f=80,loudnorm=I={target_lufs}:LRA=7:tp=-2"

    cmd = [
        ffmpeg_exe,
        "-y",
        "-i", str(mp3_path),
        "-af", af_filter,
        "-ar", "16000",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        str(out_wav_path),
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg failed for {mp3_path.name}: {res.stderr}")

    return True


def run_duration_sanity_check(bcv_chapter: str, wav_path: Path, norm_json_path: Path) -> dict:
    """
    Compares audio duration with normalized verse and character counts to detect anomalies.
    """
    duration_sec = get_wav_duration_seconds(wav_path)

    char_count = 0
    word_count = 0
    verse_count = 0

    if norm_json_path.exists():
        with open(norm_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        verse_count = data.get("total_verses", 0)
        for s in data.get("segments", []):
            txt = s.get("text_normalized", "")
            char_count += len(txt)
            word_count += len(txt.split())

    chars_per_sec = round(char_count / duration_sec, 2) if duration_sec > 0 else 0
    words_per_min = round((word_count / duration_sec) * 60, 2) if duration_sec > 0 else 0
    sec_per_verse = round(duration_sec / verse_count, 2) if verse_count > 0 else 0

    # Sanity flags
    flags = []
    if duration_sec < 15.0:
        flags.append("suspiciously_short")
    if chars_per_sec < 6.0:
        flags.append("abnormally_slow_speech")
    elif chars_per_sec > 25.0:
        flags.append("abnormally_fast_speech")
    if verse_count == 0:
        flags.append("missing_verse_text")

    status = "OK" if not flags else "FLAGGED"

    return {
        "bcv_chapter": bcv_chapter,
        "wav_file": str(wav_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "wav_size_kb": wav_path.stat().st_size // 1024,
        "duration_sec": round(duration_sec, 2),
        "duration_min": round(duration_sec / 60.0, 2),
        "verse_count": verse_count,
        "word_count": word_count,
        "char_count": char_count,
        "chars_per_sec": chars_per_sec,
        "words_per_min": words_per_min,
        "sec_per_verse": sec_per_verse,
        "status": status,
        "flags": flags,
    }


def main():
    parser = argparse.ArgumentParser(description="Convert chapter MP3s to normalized 16kHz mono WAV.")
    parser.add_argument("--book", type=str, default="GEN", help="Book code (default: GEN)")
    parser.add_argument("--force", action="store_true", help="Force re-conversion of existing WAVs")
    args = parser.parse_args()

    book_audio_dir = RAW_AUDIO_DIR / args.book
    book_norm_dir = NORM_TEXT_DIR / args.book
    out_wav_dir = INTERIM_WAV_DIR / args.book

    if not book_audio_dir.exists():
        print(f"Error: Audio directory not found: {book_audio_dir}", file=sys.stderr)
        sys.exit(1)

    ffmpeg_exe = get_ffmpeg_executable()
    print(f"[02_convert_audio] Using FFmpeg: {ffmpeg_exe}")

    mp3_files = sorted(book_audio_dir.glob(f"{args.book}_*.mp3"))
    print(f"[02_convert_audio] Processing {len(mp3_files)} chapter audio files for {args.book}...")

    converted_count = 0
    cached_count = 0
    sanity_records = []
    total_audio_duration_sec = 0.0

    for idx, mp3_path in enumerate(mp3_files, start=1):
        bcv_chapter = mp3_path.stem
        out_wav_path = out_wav_dir / f"{bcv_chapter}.wav"
        norm_json_path = book_norm_dir / f"{bcv_chapter}.json"

        was_converted = convert_chapter_audio(mp3_path, out_wav_path, ffmpeg_exe, force=args.force)
        if was_converted:
            converted_count += 1
            print(f"  [{idx:02d}/{len(mp3_files)}] Converted: {bcv_chapter}.wav ({out_wav_path.stat().st_size // 1024} KB)")
        else:
            cached_count += 1

        # Run duration sanity check
        record = run_duration_sanity_check(bcv_chapter, out_wav_path, norm_json_path)
        sanity_records.append(record)
        total_audio_duration_sec += record["duration_sec"]

    # Write sanity audit report
    flagged_chapters = [r for r in sanity_records if r["status"] == "FLAGGED"]
    avg_speech_rate = (
        round(sum(r["chars_per_sec"] for r in sanity_records) / len(sanity_records), 2)
        if sanity_records else 0
    )

    report = {
        "book": args.book,
        "total_chapters": len(sanity_records),
        "total_audio_duration_sec": round(total_audio_duration_sec, 2),
        "total_audio_duration_hours": round(total_audio_duration_sec / 3600.0, 2),
        "audio_format": "16kHz Mono 16-bit PCM WAV",
        "enhancement": "80Hz High-Pass Filter + EBU R128 (-23 LUFS) Normalization",
        "average_speech_rate_chars_per_sec": avg_speech_rate,
        "flagged_count": len(flagged_chapters),
        "flagged_chapters": flagged_chapters,
        "chapters": sanity_records,
    }

    report_path = INTERIM_WAV_DIR / f"{args.book}_audio_sanity_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n=======================================================")
    print(f"AUDIO PREPARATION COMPLETE FOR {args.book}:")
    print(f"  Total Chapters:            {len(sanity_records)} (Newly Converted: {converted_count}, Cached: {cached_count})")
    print(f"  Total Audio Duration:      {round(total_audio_duration_sec / 60.0, 2)} minutes ({round(total_audio_duration_sec / 3600.0, 2)} hours)")
    print(f"  Audio Format:              16kHz Mono 16-bit PCM WAV")
    print(f"  Loudness Target:           -23 LUFS (EBU R128) + 80Hz High-Pass Filter")
    print(f"  Average Speech Rate:       {avg_speech_rate} chars/sec")
    print(f"  Outliers / Flagged:        {len(flagged_chapters)}")
    print(f"  Sanity Report Saved to:    {report_path}")
    print("=======================================================")


if __name__ == "__main__":
    main()
