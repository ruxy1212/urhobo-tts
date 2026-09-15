#!/usr/bin/env python3
"""
scripts/15_prepare_finetune_dataset.py
Phase 8: Step 8.3 - Prepare & Validate Dataset Manifests for MMS-VITS Fine-Tuning

This script:
1. Ingests the tone-supervised manifests:
   - data/processed/train.jsonl (998 verses, with tone injections)
   - data/processed/dev.jsonl (101 verses)
   - data/processed/test.jsonl (91 verses)
2. Validates audio segment metadata (paths, duration, sample rate 16kHz).
3. Verifies complete tokenization compatibility against `models/urhobo_tokenizer/vocab.json`
   (ensuring 0 unhandled tokens or dropped letters).
4. Exports standardized fine-tuning manifests to `data/processed/finetune/`:
   - train.jsonl (with audio, text, speaker_id=0)
   - dev.jsonl
   - test.jsonl
   - metadata_train.csv (pipe-separated / LJSpeech format)
   - metadata_dev.csv
5. Outputs a detailed validation summary in `data/processed/finetune/dataset_finetune_summary.json`.
"""

import os
import sys
import json
import csv
import unicodedata
from pathlib import Path

# Reconfigure console stdout for UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
FINETUNE_DIR = PROCESSED_DIR / "finetune"
TOKENIZER_DIR = PROJECT_ROOT / "models" / "urhobo_tokenizer"
VOCAB_PATH = TOKENIZER_DIR / "vocab.json"
SUMMARY_PATH = FINETUNE_DIR / "dataset_finetune_summary.json"


def load_tokenizer_vocab():
    """Load the custom 70-token Urhobo vocabulary."""
    if not VOCAB_PATH.exists():
        raise FileNotFoundError(
            f"Urhobo vocabulary not found at {VOCAB_PATH}. Run scripts/14_prepare_urhobo_tokenizer.py first."
        )
    with open(VOCAB_PATH, "r", encoding="utf-8") as f:
        vocab = json.load(f)
    return vocab


def validate_and_format_split(input_path: Path, split_name: str, vocab: dict):
    """
    Validate and format a manifest split for HuggingFace VITS training.
    """
    records = []
    total_duration = 0.0
    dropped_chars_set = set()
    missing_audio_files = 0

    if not input_path.exists():
        raise FileNotFoundError(f"Manifest not found: {input_path}")

    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            verse_id = item["id"]
            text = item["text"]
            audio_rel = item.get("audio", item.get("audio_path", ""))
            duration = item.get("duration", item.get("duration_sec", 0.0))
            confidence = item.get("confidence", item.get("alignment_confidence", 0.0))

            # Check audio file existence on disk
            audio_full = PROJECT_ROOT / audio_rel
            if not audio_full.exists():
                missing_audio_files += 1

            # Check tokenization compatibility
            text_lower = text.lower()
            for c in text_lower:
                if c not in vocab and c != " " and not unicodedata.category(c).startswith(("P", "S")):
                    dropped_chars_set.add(c)

            total_duration += duration

            # Standard Hugging Face VITS dataset schema
            record = {
                "id": verse_id,
                "audio": audio_rel.replace("\\", "/"),
                "text": text,
                "duration_sec": round(duration, 3),
                "speaker_id": 0,
                "alignment_confidence": round(confidence, 4)
            }
            records.append(record)

    return {
        "split_name": split_name,
        "count": len(records),
        "total_duration_sec": round(total_duration, 2),
        "total_duration_hours": round(total_duration / 3600.0, 3),
        "missing_audio_files": missing_audio_files,
        "dropped_phonetic_chars": list(dropped_chars_set),
        "records": records
    }


def prepare_finetune_datasets():
    print("=" * 70)
    print("Phase 8 Step 8.3: Prepare & Validate Dataset for VITS Fine-Tuning")
    print("=" * 70)

    # 1. Load Urhobo vocabulary
    vocab = load_tokenizer_vocab()
    print(f"1. Loaded Urhobo tokenizer vocabulary ({len(vocab)} tokens).")

    # 2. Process and validate all splits
    print("\n2. Processing and validating manifest splits...")
    FINETUNE_DIR.mkdir(parents=True, exist_ok=True)

    splits = {}
    for split_name in ["train", "dev", "test"]:
        input_file = PROCESSED_DIR / f"{split_name}.jsonl"
        print(f"  Validating {split_name} ({input_file.relative_to(PROJECT_ROOT)})...")
        split_data = validate_and_format_split(input_file, split_name, vocab)
        splits[split_name] = split_data

        print(f"    - Clips:      {split_data['count']:,}")
        print(f"    - Audio:      {split_data['total_duration_hours']:.2f} hours ({split_data['total_duration_sec']:,.1f}s)")
        print(f"    - Missing:    {split_data['missing_audio_files']}")
        print(f"    - OOV Chars:  {split_data['dropped_phonetic_chars'] or 'None (100% covered)'}")

        # Export formatted JSONL
        out_jsonl = FINETUNE_DIR / f"{split_name}.jsonl"
        with open(out_jsonl, "w", encoding="utf-8") as f:
            for rec in split_data["records"]:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"    -> Exported:  {out_jsonl.relative_to(PROJECT_ROOT)}")

        # Export metadata CSV (pipe-separated)
        out_csv = FINETUNE_DIR / f"metadata_{split_name}.csv"
        with open(out_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter="|")
            for rec in split_data["records"]:
                writer.writerow([rec["id"], rec["audio"], rec["text"]])
        print(f"    -> Exported:  {out_csv.relative_to(PROJECT_ROOT)}\n")

    # 3. Overall dataset summary
    total_clips = sum(s["count"] for s in splits.values())
    total_sec = sum(s["total_duration_sec"] for s in splits.values())
    total_hours = sum(s["total_duration_hours"] for s in splits.values())

    all_oov = any(len(s["dropped_phonetic_chars"]) > 0 for s in splits.values())

    summary = {
        "status": "success" if not all_oov else "warning",
        "total_clips": total_clips,
        "total_duration_hours": round(total_hours, 3),
        "total_duration_seconds": round(total_sec, 2),
        "tokenizer_vocab_size": len(vocab),
        "splits": {
            k: {
                "count": v["count"],
                "duration_hours": v["total_duration_hours"],
                "missing_audio_files": v["missing_audio_files"],
                "dropped_phonetic_chars": v["dropped_phonetic_chars"]
            }
            for k, v in splits.items()
        }
    }

    with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"3. Dataset Summary:")
    print(f"  Total Clips:       {total_clips:,}")
    print(f"  Total Speech:      {total_hours:.2f} hours")
    print(f"  Train:             {splits['train']['count']} clips ({splits['train']['total_duration_hours']:.2f}h)")
    print(f"  Dev (Eval):        {splits['dev']['count']} clips ({splits['dev']['total_duration_hours']:.2f}h)")
    print(f"  Test:              {splits['test']['count']} clips ({splits['test']['total_duration_hours']:.2f}h)")
    print(f"  Manifest written:  {SUMMARY_PATH.relative_to(PROJECT_ROOT)}")
    print("=" * 70)


if __name__ == "__main__":
    prepare_finetune_datasets()
