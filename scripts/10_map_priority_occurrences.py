#!/usr/bin/env python3
"""
scripts/10_map_priority_occurrences.py

Phase 7.1 — Priority Target Compilation & Corpus Occurrence Search.

1. Compiles the priority vocabulary target list from:
     - Curriculum seed items (app_content/curriculum_vocab.tsv)
     - Audited homograph lemma pairs (data/lexicon/homographs.tsv)
2. Searches the Phase 5 training manifest (data/processed/train.jsonl) for natural occurrences
   of each priority plain word form across all 998 training verses.
3. Maps each occurrence to:
     - verse_id (e.g. GEN_002_007)
     - chapter (e.g. GEN_002)
     - word_token & token_position in sentence
     - canonical_tone_form from Phase 6 lexicon
4. Emits `data/lexicon/priority_corpus_occurrences.json` and prints summary statistics.
"""

import csv
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# UTF-8 console output for Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent
CURRICULUM_PATH = REPO_ROOT / "app_content" / "curriculum_vocab.tsv"
HOMOGRAPHS_PATH = REPO_ROOT / "data" / "lexicon" / "homographs.tsv"
TRAIN_PATH = REPO_ROOT / "data" / "processed" / "train.jsonl"
OUT_PATH = REPO_ROOT / "data" / "lexicon" / "priority_corpus_occurrences.json"


def load_priority_targets() -> Dict[str, Dict[str, Any]]:
    """Loads priority target vocabulary from curriculum and homographs."""
    priority_items: Dict[str, Dict[str, Any]] = {}

    # 1. Load curriculum items (pronouns, numbers, objects, greetings)
    if CURRICULUM_PATH.exists():
        with open(CURRICULUM_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for r in reader:
                cat = r["category"].strip()
                if cat in ("pronoun", "number", "object", "greeting"):
                    raw = r["urhobo_raw"].strip().lower()
                    if len(raw) > 1:
                        priority_items[raw] = {
                            "id": r["id"],
                            "plain_form": raw,
                            "canonical_tone_form": r["urhobo_toned"].strip(),
                            "gloss_en": r["english"].strip(),
                            "category": cat,
                            "origin": "curriculum_seed",
                        }

    # 2. Load homograph pairs
    if HOMOGRAPHS_PATH.exists():
        with open(HOMOGRAPHS_PATH, "r", encoding="utf-8") as f:
            lines = [l for l in f if not l.startswith("#")]
            reader = csv.DictReader(lines, delimiter="\t")
            for r in reader:
                plain = r["plain_form"].strip().lower()
                if plain not in priority_items and len(plain) > 1:
                    priority_items[plain] = {
                        "id": f"hom_{plain}",
                        "plain_form": plain,
                        "canonical_tone_form": r["canonical_tone_form"].strip(),
                        "gloss_en": r["gloss_en"].strip(),
                        "category": "homograph",
                        "origin": "homograph_audit",
                    }

    return priority_items


def find_token_spans(sentence: str) -> List[Tuple[str, int, int]]:
    """Finds words and their character start/end spans in a sentence."""
    spans = []
    for m in re.finditer(r"[a-zA-ZẸỌẹọ]+", sentence):
        spans.append((m.group(0), m.start(), m.end()))
    return spans


def search_corpus_occurrences(
    priority_targets: Dict[str, Dict[str, Any]],
    train_path: Path
) -> Tuple[Dict[str, List[Dict[str, Any]]], int]:
    """Searches train.jsonl for occurrences of priority targets."""
    occurrences = defaultdict(list)
    total_verses = 0

    with open(train_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            total_verses += 1
            rec = json.loads(line.strip())
            verse_id = rec["id"]
            verse_text = rec["text"]
            audio_path = rec["audio"]
            duration = rec["duration"]

            spans = find_token_spans(verse_text)
            for idx, (token, start_char, end_char) in enumerate(spans):
                token_lower = token.lower()
                if token_lower in priority_targets:
                    p_info = priority_targets[token_lower]
                    occ = {
                        "verse_id": verse_id,
                        "chapter": verse_id.rsplit("_", 1)[0],
                        "audio_path": audio_path,
                        "verse_duration": duration,
                        "token_index": idx,
                        "token_raw": token,
                        "char_span": [start_char, end_char],
                        "context_snippet": verse_text[max(0, start_char-20):min(len(verse_text), end_char+20)],
                        "canonical_tone_form": p_info["canonical_tone_form"],
                        "category": p_info["category"],
                        "gloss_en": p_info["gloss_en"],
                    }
                    occurrences[token_lower].append(occ)

    return occurrences, total_verses


def main():
    print("=================================================================")
    print("   URHOBO TTS — PHASE 7.1 PRIORITY CORPUS OCCURRENCE SEARCH")
    print("=================================================================")
    t0 = time.time()

    priority_targets = load_priority_targets()
    print(f"  Loaded {len(priority_targets)} priority target lemmas (curriculum & homographs)")

    occurrences, total_verses = search_corpus_occurrences(priority_targets, TRAIN_PATH)
    print(f"  Scanned {total_verses} training verses in train.jsonl")

    found_targets = {k: occs for k, occs in occurrences.items()}
    zero_targets = [k for k in priority_targets if k not in occurrences]

    total_occurrences_found = sum(len(v) for v in occurrences.values())

    # Build comprehensive payload
    payload = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_priority_targets": len(priority_targets),
        "found_targets_count": len(found_targets),
        "found_targets_percentage": round(len(found_targets) / len(priority_targets) * 100, 2),
        "zero_targets_count": len(zero_targets),
        "total_corpus_occurrences": total_occurrences_found,
        "occurrences_by_word": {
            k: {
                "target_info": priority_targets[k],
                "occurrences_count": len(occs),
                "occurrences": occs[:10], # Store top 10 sample instances per word
            }
            for k, occs in sorted(found_targets.items(), key=lambda x: len(x[1]), reverse=True)
        },
        "zero_occurrence_words": [
            {
                "plain_form": k,
                "info": priority_targets[k]
            }
            for k in sorted(zero_targets)
        ]
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    elapsed = time.time() - t0

    print("-----------------------------------------------------------------")
    print(f"  Target Words Found in Corpus : {len(found_targets)}/{len(priority_targets)} ({payload['found_targets_percentage']}%)")
    print(f"  Zero-Occurrence Target Words : {len(zero_targets)}/{len(priority_targets)}")
    print(f"  Total Natural Occurrences    : {total_occurrences_found} across {total_verses} training verses")
    print(f"  Saved Occurrences Payload    : {OUT_PATH.relative_to(REPO_ROOT)}")
    print("-----------------------------------------------------------------")
    print(f"Phase 7.1 completed in {elapsed:.2f}s.")
    print("=================================================================")


if __name__ == "__main__":
    main()
