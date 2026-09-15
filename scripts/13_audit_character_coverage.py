#!/usr/bin/env python3
"""
scripts/13_audit_character_coverage.py
Phase 8: Step 8.1 - Audit Character Coverage & Discrepancies against facebook/mms-tts-yor

This script:
1. Downloads or loads the base checkpoint tokenizer files for `facebook/mms-tts-yor`:
   - vocab.json
   - config.json
   - tokenizer_config.json
   Saves local reference copies in `models/base_mms_yor/`.
2. Audits all unique characters and their frequencies across:
   - data/processed/train.jsonl (with Phase 7 tone-supervision injections)
   - data/processed/dev.jsonl
   - data/processed/test.jsonl
   - data/lexicon/lexicon.tsv (plain_form and canonical_tone_form)
   - app_content/curriculum_vocab.tsv (urhobo_raw and urhobo_toned)
3. Compares all Urhobo characters against the 43 base Yoruba tokens.
4. Categorizes missing characters:
   - Missing core Latin letters (e.g., 'v', 'c', 'z')
   - Missing tone diacritics (e.g., caron, circumflex, tilde)
   - Missing combining marks (e.g., combining dot below \u0323, combining caron \u030c)
   - Punctuation / symbols
5. Simulates VitsTokenizer behavior to verify stripping vs OOV impact.
6. Outputs a comprehensive audit report to `models/tokenizer_audit_report.json`.
"""

import os
import sys
import json
import csv
import unicodedata
from collections import Counter
from pathlib import Path
import requests

# Reconfigure console stdout for UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BASE_MMS_DIR = PROJECT_ROOT / "models" / "base_mms_yor"
AUDIT_REPORT_PATH = PROJECT_ROOT / "models" / "tokenizer_audit_report.json"

TRAIN_PATH = PROJECT_ROOT / "data" / "processed" / "train.jsonl"
DEV_PATH = PROJECT_ROOT / "data" / "processed" / "dev.jsonl"
TEST_PATH = PROJECT_ROOT / "data" / "processed" / "test.jsonl"
LEXICON_PATH = PROJECT_ROOT / "data" / "lexicon" / "lexicon.tsv"
CURRICULUM_PATH = PROJECT_ROOT / "app_content" / "curriculum_vocab.tsv"

MMS_YOR_BASE_URL = "https://huggingface.co/facebook/mms-tts-yor/raw/main"
FILES_TO_CACHE = ["vocab.json", "config.json", "tokenizer_config.json", "special_tokens_map.json"]


def fetch_and_cache_base_model():
    """Fetch and cache base MMS Yoruba tokenizer files locally."""
    BASE_MMS_DIR.mkdir(parents=True, exist_ok=True)
    cached_data = {}

    for fname in FILES_TO_CACHE:
        local_file = BASE_MMS_DIR / fname
        if local_file.exists():
            print(f"  [Cache] Loading existing {fname} from {local_file.relative_to(PROJECT_ROOT)}")
            with open(local_file, "r", encoding="utf-8") as f:
                cached_data[fname] = json.load(f)
        else:
            url = f"{MMS_YOR_BASE_URL}/{fname}"
            print(f"  [Download] Fetching {fname} from {url}...")
            try:
                resp = requests.get(url, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                with open(local_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                cached_data[fname] = data
                print(f"  [Save] Cached {fname} -> {local_file.relative_to(PROJECT_ROOT)}")
            except Exception as e:
                print(f"  [ERROR] Failed to fetch {url}: {e}")
                raise e

    return cached_data


def extract_characters_from_manifest(file_path: Path):
    """Extract character counts and unique lines from a jsonl manifest."""
    raw_counter = Counter()
    lower_counter = Counter()
    total_lines = 0

    if not file_path.exists():
        print(f"  [Warning] File not found: {file_path}")
        return raw_counter, lower_counter, total_lines

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            text = item.get("text", "")
            raw_counter.update(text)
            lower_counter.update(text.lower())
            total_lines += 1

    return raw_counter, lower_counter, total_lines


def extract_characters_from_lexicon(file_path: Path):
    """Extract characters from plain_form and canonical_tone_form in lexicon.tsv."""
    raw_counter = Counter()
    lower_counter = Counter()
    total_rows = 0

    if not file_path.exists():
        print(f"  [Warning] Lexicon file not found: {file_path}")
        return raw_counter, lower_counter, total_rows

    with open(file_path, "r", encoding="utf-8") as f:
        lines = [l for l in f if not l.startswith("#")]
        reader = csv.DictReader(lines, delimiter="\t")
        for row in reader:
            total_rows += 1
            for field in ["plain_form", "canonical_tone_form"]:
                val = row.get(field, "")
                if val:
                    raw_counter.update(val)
                    lower_counter.update(val.lower())

    return raw_counter, lower_counter, total_rows


def extract_characters_from_curriculum(file_path: Path):
    """Extract characters from urhobo_raw and urhobo_toned in curriculum_vocab.tsv."""
    raw_counter = Counter()
    lower_counter = Counter()
    total_rows = 0

    if not file_path.exists():
        print(f"  [Warning] Curriculum file not found: {file_path}")
        return raw_counter, lower_counter, total_rows

    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            total_rows += 1
            for field in ["urhobo_raw", "urhobo_toned"]:
                val = row.get(field, "")
                if val:
                    raw_counter.update(val)
                    lower_counter.update(val.lower())

    return raw_counter, lower_counter, total_rows


def char_info(c: str):
    """Return dictionary with unicode character details."""
    try:
        name = unicodedata.name(c)
    except ValueError:
        name = "UNKNOWN"
    return {
        "char": c,
        "codepoint": f"U+{ord(c):04X}",
        "category": unicodedata.category(c),
        "name": name,
    }


def simulate_vits_normalization(text: str, vocab: dict):
    """
    Simulates HuggingFace VitsTokenizer normalize_text + character filtering:
    1. Lowercase text.
    2. Filter to only characters present in vocab.
    """
    text_lower = text.lower()
    filtered = "".join([c for c in text_lower if c in vocab])
    return filtered


def run_character_audit():
    print("=" * 70)
    print("Phase 8 Step 8.1: Urhobo TTS Character Coverage & Tokenizer Audit")
    print("=" * 70)

    # 1. Fetch & cache base model files
    print("\n1. Fetching base Yoruba model configuration (facebook/mms-tts-yor)...")
    base_data = fetch_and_cache_base_model()
    yor_vocab = base_data["vocab.json"]
    print(f"  [Base Vocab] Total Yoruba tokens: {len(yor_vocab)}")

    # 2. Extract characters across all project corpora
    print("\n2. Extracting characters across Urhobo datasets...")
    train_raw, train_lower, train_lines = extract_characters_from_manifest(TRAIN_PATH)
    dev_raw, dev_lower, dev_lines = extract_characters_from_manifest(DEV_PATH)
    test_raw, test_lower, test_lines = extract_characters_from_manifest(TEST_PATH)
    lex_raw, lex_lower, lex_rows = extract_characters_from_lexicon(LEXICON_PATH)
    curr_raw, curr_lower, curr_rows = extract_characters_from_curriculum(CURRICULUM_PATH)

    corpus_lower = train_lower + dev_lower + test_lower
    all_project_lower = corpus_lower + lex_lower + curr_lower

    print(f"  Train verses:      {train_lines:,} ({sum(train_lower.values()):,} characters, {len(train_lower)} unique)")
    print(f"  Dev verses:        {dev_lines:,} ({sum(dev_lower.values()):,} characters, {len(dev_lower)} unique)")
    print(f"  Test verses:       {test_lines:,} ({sum(test_lower.values()):,} characters, {len(test_lower)} unique)")
    print(f"  Lexicon entries:   {lex_rows:,} ({sum(lex_lower.values()):,} characters, {len(lex_lower)} unique)")
    print(f"  Curriculum items:  {curr_rows:,} ({sum(curr_lower.values()):,} characters, {len(curr_lower)} unique)")
    print(f"  Total characters:  {sum(all_project_lower.values()):,} ({len(all_project_lower)} unique lowercase)")

    # 3. Discrepancy analysis against Yoruba base vocab
    print("\n3. Auditing character discrepancies against base Yoruba vocabulary...")
    
    covered_in_train = {c: count for c, count in train_lower.items() if c in yor_vocab}
    missing_in_train = {c: count for c, count in train_lower.items() if c not in yor_vocab}

    covered_in_project = {c: count for c, count in all_project_lower.items() if c in yor_vocab}
    missing_in_project = {c: count for c, count in all_project_lower.items() if c not in yor_vocab}

    # Categorize missing characters
    missing_letters_train = {}
    missing_diacritics_train = {}
    missing_punctuation_train = {}
    missing_other_train = {}

    for c, count in missing_in_train.items():
        cat = unicodedata.category(c)
        if cat.startswith("L"):  # Letter
            if len(c) == 1 and "a" <= c <= "z":
                missing_letters_train[c] = count
            else:
                missing_diacritics_train[c] = count
        elif cat.startswith("M"):  # Mark (combining)
            missing_diacritics_train[c] = count
        elif cat.startswith("P"):  # Punctuation
            missing_punctuation_train[c] = count
        else:
            missing_other_train[c] = count

    print(f"\n  --- TRAIN CORPUS COVERAGE ---")
    print(f"  Characters covered by Yoruba base: {len(covered_in_train)}")
    print(f"  Characters MISSING in Yoruba base: {len(missing_in_train)}")
    
    print("\n  [Missing Latin Letters in Train]:")
    for c, cnt in sorted(missing_letters_train.items(), key=lambda x: -x[1]):
        info = char_info(c)
        print(f"    '{c}' ({info['codepoint']}, {info['name']}): {cnt:,} occurrences")

    print("\n  [Missing Tone/Diacritic Characters in Train]:")
    for c, cnt in sorted(missing_diacritics_train.items(), key=lambda x: -x[1]):
        info = char_info(c)
        print(f"    '{c}' ({info['codepoint']}, {info['name']}): {cnt:,} occurrences")

    print("\n  [Missing Punctuation in Train (Default VitsTokenizer strips these)]: ")
    for c, cnt in sorted(missing_punctuation_train.items(), key=lambda x: -x[1]):
        info = char_info(c)
        print(f"    '{c}' ({info['codepoint']}, {info['name']}): {cnt:,} occurrences")

    # 4. Global project missing characters (Lexicon + Curriculum)
    missing_letters_project = {}
    missing_diacritics_project = {}
    missing_other_project = {}

    for c, count in missing_in_project.items():
        cat = unicodedata.category(c)
        if cat.startswith("L"):
            if len(c) == 1 and "a" <= c <= "z":
                missing_letters_project[c] = count
            else:
                missing_diacritics_project[c] = count
        elif cat.startswith("M"):
            missing_diacritics_project[c] = count
        elif not cat.startswith("P"):
            missing_other_project[c] = count

    print("\n  --- ALL PROJECT SOURCES (Corpus + Lexicon + Curriculum) ---")
    print("  [Additional Missing Letters Across Project]:")
    for c, cnt in sorted(missing_letters_project.items(), key=lambda x: -x[1]):
        if c not in missing_letters_train:
            info = char_info(c)
            print(f"    '{c}' ({info['codepoint']}, {info['name']}): {cnt:,} occurrences")

    print("  [Additional Missing Diacritics Across Project]:")
    for c, cnt in sorted(missing_diacritics_project.items(), key=lambda x: -x[1]):
        if c not in missing_diacritics_train:
            info = char_info(c)
            print(f"    '{c}' ({info['codepoint']}, {info['name']}): {cnt:,} occurrences")

    # 5. Tokenizer impact demonstration
    print("\n4. Demonstrating Tokenizer Impact on Urhobo Sentences...")
    sample_sentences = [
        "Avwanre vwo ẹgba vwọ kẹ Osolobrugwẹ.",
        "Ọmọ na da rhe vwo ẹghwẹ.",
        "Mẹ́vwẹ yen rha cha.",
        "Zebulun vẹ Naftali.",
    ]

    for sent in sample_sentences:
        normalized_yor = simulate_vits_normalization(sent, yor_vocab)
        print(f"  Original:    \"{sent}\"")
        print(f"  Base Yor:    \"{normalized_yor}\"")
        # Check what was dropped
        dropped = [c for c in sent.lower() if c not in yor_vocab and not unicodedata.category(c).startswith("P") and c != " "]
        if dropped:
            print(f"  [ALERT] Dropped letters/tones: {dropped}")
        print()

    # 6. Recommended Extension Characters
    # Core Urhobo letters to add:
    # 'v' (critical, thousands of occurrences)
    # 'c' (digraph 'ch', names)
    # 'z' (Biblical names / loanwords)
    # 'x', 'q' (standard latin completeness)
    # Combining & Precomposed Tones:
    # '\u030c' (combining caron / rising tone)
    # '\u0302' (combining circumflex / falling tone)
    # '\u0323' (combining dot below)
    # 'ǐ' (i with caron), 'ǔ' (u with caron), 'ê', 'ô', etc.
    essential_additions = ["v", "c", "z", "x", "q", "\u030c", "\u0302", "\u0323", "ǐ", "ǔ", "ê", "ô", "î", "â", "û", "ĩ", "ẽ", "õ", "ã"]
    
    # Filter to unique additions not already in yor_vocab
    recommended_tokens = [t for t in essential_additions if t not in yor_vocab]

    print("5. Recommended Extension Characters for Step 8.2:")
    for token in recommended_tokens:
        info = char_info(token)
        print(f"  + Token: '{token}' ({info['codepoint']}, {info['name']})")

    # 7. Write JSON Report
    report = {
        "base_model": {
            "checkpoint": "facebook/mms-tts-yor",
            "vocab_size": len(yor_vocab),
            "sample_rate": base_data["config.json"].get("sampling_rate", 16000),
            "model_type": base_data["config.json"].get("model_type", "vits"),
            "is_uroman": base_data["tokenizer_config.json"].get("is_uroman", False),
            "normalize": base_data["tokenizer_config.json"].get("normalize", True),
            "add_blank": base_data["tokenizer_config.json"].get("add_blank", True),
            "vocab_tokens": sorted(list(yor_vocab.keys())),
        },
        "corpus_statistics": {
            "train": {"verses": train_lines, "total_chars": sum(train_lower.values()), "unique_chars": len(train_lower)},
            "dev": {"verses": dev_lines, "total_chars": sum(dev_lower.values()), "unique_chars": len(dev_lower)},
            "test": {"verses": test_lines, "total_chars": sum(test_lower.values()), "unique_chars": len(test_lower)},
            "lexicon": {"entries": lex_rows, "total_chars": sum(lex_lower.values()), "unique_chars": len(lex_lower)},
            "curriculum": {"items": curr_rows, "total_chars": sum(curr_lower.values()), "unique_chars": len(curr_lower)},
        },
        "audit_results": {
            "train_missing_letters": {c: {"count": cnt, **char_info(c)} for c, cnt in missing_letters_train.items()},
            "train_missing_diacritics": {c: {"count": cnt, **char_info(c)} for c, cnt in missing_diacritics_train.items()},
            "train_missing_punctuation": {c: {"count": cnt, **char_info(c)} for c, cnt in missing_punctuation_train.items()},
            "all_project_missing_letters": {c: {"count": cnt, **char_info(c)} for c, cnt in missing_letters_project.items()},
            "all_project_missing_diacritics": {c: {"count": cnt, **char_info(c)} for c, cnt in missing_diacritics_project.items()},
        },
        "recommendations": {
            "tokens_to_add": [char_info(t) for t in recommended_tokens],
            "total_new_tokens": len(recommended_tokens),
            "extended_vocab_size": len(yor_vocab) + len(recommended_tokens),
        }
    }

    AUDIT_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n[Done] Audit report written to: {AUDIT_REPORT_PATH.relative_to(PROJECT_ROOT)}")
    print("=" * 70)


if __name__ == "__main__":
    run_character_audit()
