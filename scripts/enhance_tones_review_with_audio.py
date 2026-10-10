"""
Enhance top_500_priority_tones_review.csv with audio verse references (e.g., GEN_002_006.wav)
and copy the referenced audio files to a non-tracking local folder review_audio_samples/.
"""

import csv
import os
import re
import shutil
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(BASE_DIR, "data", "lexicon", "top_500_priority_tones_review.csv")
TSV_PATH = os.path.join(BASE_DIR, "data", "lexicon", "top_500_priority_tones_review.tsv")
METADATA_PATH = os.path.join(BASE_DIR, "data", "processed", "metadata.csv")
SEGMENTS_DIR = os.path.join(BASE_DIR, "data", "processed", "segments", "GEN")
TARGET_AUDIO_DIR = os.path.join(BASE_DIR, "review_audio_samples")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(f"Base Directory: {BASE_DIR}")
    print(f"Target Audio Folder: {TARGET_AUDIO_DIR}")

    # Ensure target audio directory exists
    os.makedirs(TARGET_AUDIO_DIR, exist_ok=True)

    # 1. Load metadata.csv mapping
    text_to_clip = {}
    clip_to_text = {}
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="|")
        header = next(reader)
        for row in reader:
            if len(row) >= 2:
                cid = row[0].strip()
                txt = row[1].strip()
                text_to_clip[txt] = cid
                clip_to_text[cid] = txt

    print(f"Loaded {len(text_to_clip)} verse clips from metadata.csv.")

    # 2. Read existing CSV
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    if "Audio File" not in fieldnames:
        # Place Audio File right after Genesis Context
        if "Genesis Context" in fieldnames:
            idx = fieldnames.index("Genesis Context") + 1
            fieldnames.insert(idx, "Audio File")
        else:
            fieldnames.append("Audio File")

    # 3. Match contexts to audio files
    matched_count = 0
    blank_count = 0
    unique_audio_files = set()

    for r in rows:
        ctx = r.get("Genesis Context", "").strip()
        rnk = r.get("Rank", "").strip()
        audio_file = ""

        if not ctx:
            # User instruction: Leave the 7 words without context blank
            audio_file = ""
        elif ctx in text_to_clip:
            audio_file = f"{text_to_clip[ctx]}.wav"
        elif rnk.startswith("H-"):
            clean = re.sub(r"\(.*?\)", "", ctx).strip()
            if not clean.lower().startswith("example:"):
                # Handle ellipsis split if present
                if "..." in clean:
                    parts = [p.strip() for p in clean.split("...") if p.strip()]
                    candidates = [cid for cid, txt in clip_to_text.items() if all(p in txt for p in parts)]
                else:
                    candidates = [cid for cid, txt in clip_to_text.items() if clean in txt]
                if candidates:
                    audio_file = f"{candidates[0]}.wav"

        r["Audio File"] = audio_file
        if audio_file:
            matched_count += 1
            unique_audio_files.add(audio_file)
        else:
            blank_count += 1

    print(f"Total CSV rows: {len(rows)}")
    print(f"Rows with Audio File assigned: {matched_count}")
    print(f"Rows left blank: {blank_count}")
    print(f"Unique audio files referenced: {len(unique_audio_files)}")

    # 4. Save enhanced CSV
    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Updated {CSV_PATH}")

    # Also update TSV for consistency if it exists
    if os.path.exists(TSV_PATH):
        with open(TSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
            writer.writeheader()
            writer.writerows(rows)
        print(f"Updated {TSV_PATH}")

    # 5. Copy referenced audio files to review_audio_samples/
    copied_count = 0
    missing_sources = []
    for af in sorted(unique_audio_files):
        src_path = os.path.join(SEGMENTS_DIR, af)
        dst_path = os.path.join(TARGET_AUDIO_DIR, af)
        if os.path.exists(src_path):
            shutil.copy2(src_path, dst_path)
            copied_count += 1
        else:
            missing_sources.append(af)

    print(f"Successfully copied {copied_count} files into {TARGET_AUDIO_DIR}.")
    if missing_sources:
        print(f"WARNING: {len(missing_sources)} files were not found in {SEGMENTS_DIR}: {missing_sources}")

    # 6. Verify GEN_002_006.wav references
    gen_002_006_rows = [r for r in rows if r["Audio File"] == "GEN_002_006.wav"]
    print(f"\nVerification: {len(gen_002_006_rows)} words reference GEN_002_006.wav:")
    for r in gen_002_006_rows:
        print(f"  Rank {r['Rank']:>4}: {r['Word']:<12} (Freq: {r['Frequency']})")


if __name__ == "__main__":
    main()
