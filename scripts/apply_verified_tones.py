"""
Apply Human-Verified Tones to Training and Dev Manifests
Reads data/lexicon/top_500_priority_tones_review.csv and projects verified tone marks
onto all matching words in data/processed/finetune/train.jsonl and dev.jsonl.
"""

import os
import re
import csv
import json
from typing import Dict, Tuple

LEXICON_CSV = "data/lexicon/top_500_priority_tones_review.csv"
TRAIN_MANIFEST = "data/processed/finetune/train.jsonl"
DEV_MANIFEST = "data/processed/finetune/dev.jsonl"
VOCAB_FILE = "models/urhobo_tokenizer/vocab.json"


def load_vocab():
    with open(VOCAB_FILE, "r", encoding="utf-8") as f:
        return set(json.load(f).keys())


def load_verified_tones() -> Dict[str, str]:
    mapping = {}
    if not os.path.exists(LEXICON_CSV):
        raise FileNotFoundError(f"Review file not found at {LEXICON_CSV}")

    with open(LEXICON_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_word = row["Word"].strip().lower()
            verified = row["Verified Tone"].strip()
            # If verified column is empty, fallback to Proposed Tone
            if not verified:
                verified = row.get("Proposed Tone", "").strip()

            if verified:
                mapping[raw_word] = verified

    print(f"Loaded {len(mapping)} verified/proposed tone words from review sheet.")
    return mapping


def match_case(template: str, text: str) -> str:
    """Matches the capitalization of the original word."""
    if template.isupper():
        return text.upper()
    elif template and template[0].isupper():
        return text[0].upper() + text[1:] if len(text) > 1 else text.upper()
    return text.lower()


def apply_tones_to_text(text: str, tone_map: Dict[str, str], word_regex: re.Pattern) -> Tuple[str, int]:
    replacements = 0

    def replace_match(match):
        nonlocal replacements
        original = match.group(0)
        lower_orig = original.lower()
        if lower_orig in tone_map:
            replacements += 1
            replacement = tone_map[lower_orig]
            return match_case(original, replacement)
        return original

    toned_text = word_regex.sub(replace_match, text)
    return toned_text, replacements


def process_manifest(manifest_path: str, tone_map: Dict[str, str], word_regex: re.Pattern):
    if not os.path.exists(manifest_path):
        print(f"Manifest not found: {manifest_path}, skipping.")
        return

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = [json.loads(line) for line in f]

    total_replacements = 0
    total_tokens = 0
    modified_rows = 0

    output_rows = []
    for row in data:
        text = row["text"]
        toned_text, reps = apply_tones_to_text(text, tone_map, word_regex)
        tokens_count = len(word_regex.findall(text))
        total_tokens += tokens_count
        if reps > 0:
            modified_rows += 1
            total_replacements += reps
        row["text"] = toned_text
        output_rows.append(row)

    with open(manifest_path, "w", encoding="utf-8") as f:
        for row in output_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    pct = (total_replacements / total_tokens * 100) if total_tokens > 0 else 0
    print(f"Updated {manifest_path}:")
    print(f"  - Rows modified: {modified_rows} / {len(data)}")
    print(f"  - Tone-supervised words: {total_replacements} / {total_tokens} ({pct:.2f}%)")


def main():
    vocab = load_vocab()
    tone_map = load_verified_tones()

    # Verify that all characters in the tone map are inside tokenizer vocabulary
    invalid_chars = set()
    for word, toned in tone_map.items():
        for char in toned.lower():
            if char not in vocab:
                invalid_chars.add(char)

    if invalid_chars:
        print(f"WARNING: Found {len(invalid_chars)} characters not in 70-token vocab: {invalid_chars}")
        print("Please ensure verified tones only use characters in vocab.json!")
    else:
        print("Vocabulary Validation: All tone characters exist in the 70-token Urhobo vocabulary!")

    # Sort keys by length descending to match longest compound words first
    sorted_words = sorted(tone_map.keys(), key=lambda w: -len(w))
    pattern_str = r'\b(' + '|'.join(re.escape(w) for w in sorted_words) + r')\b'
    word_regex = re.compile(r'[a-zA-Z\u00C0-\u024F\u1E00-\u1EFF]+')
    replace_regex = re.compile(pattern_str, re.IGNORECASE)

    print("\nApplying verified tones to train and dev manifests...")
    process_manifest(TRAIN_MANIFEST, tone_map, replace_regex)
    process_manifest(DEV_MANIFEST, tone_map, replace_regex)
    print("\nTone injection completed successfully!")


if __name__ == "__main__":
    main()
