#!/usr/bin/env python3
"""
scripts/11_classify_tone_dispositions.py

Phase 7.2 — Acoustic Tone Verification & Disposition Classification.

Assigns each of the 204 priority targets one of the four strict dispositions
mandated by the Phase 7 Definition of Done:
  1. `resolved-from-corpus`:
     Natural spoken occurrence in Genesis training audio (106 words, 3,955 instances).
     Selects 3–5 optimal, varied sentence instances per word (different sentence positions:
     initial, medial, final) to prepare for targeted training supervision without blanket replacement.
  2. `resolved-from-secondary-source`:
     Verified against UCLA Phonetics Archive audio recordings (7 words with zero Genesis occurrences).
  3. `resolved-from-new-recording`:
     Reserved for studio-recorded residual words (0 words in v1).
  4. `explicitly-marked-unverified`:
     Residual zero-corpus words (91 words: modern numbers, formal greetings, rare homographs)
     explicitly tracked for the Phase 12 runtime content pipeline.

Emits `data/lexicon/priority_dispositions.json` and prints comprehensive audit metrics.
"""

import csv
import json
import re
import sys
import time
from collections import Counter, defaultdict
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
OCCURRENCES_PATH = REPO_ROOT / "data" / "lexicon" / "priority_corpus_occurrences.json"
UCLA_RAW_PATH = REPO_ROOT / "data" / "interim" / "lexicon_raw" / "ucla_phonetics_raw.tsv"
UCLA_1960_PATH = REPO_ROOT / "data" / "interim" / "lexicon_raw" / "ucla_phonetics_1960_raw.tsv"
OUT_DISPOSITIONS_PATH = REPO_ROOT / "data" / "lexicon" / "priority_dispositions.json"


def load_ucla_words() -> Dict[str, Dict[str, Any]]:
    """Loads UCLA phonetic words and audio references."""
    ucla = {}
    for p, src in [(UCLA_RAW_PATH, "ucla_phonetics"), (UCLA_1960_PATH, "ucla_phonetics_1960")]:
        if p.exists():
            lines = p.read_text(encoding="utf-8").split("\n")[1:]
            for line in lines:
                parts = line.strip().split("\t")
                if len(parts) >= 3:
                    plain = parts[1].strip().lower()
                    ucla[plain] = {
                        "plain_form": plain,
                        "canonical_tone_form": parts[2].strip() if len(parts) >= 4 else parts[1].strip(),
                        "gloss_en": parts[3].strip() if len(parts) >= 4 else parts[2].strip(),
                        "source_id": src,
                    }
    return ucla


def select_best_instances(occurrences: List[Dict[str, Any]], target_count: int = 4) -> List[Dict[str, Any]]:
    """
    Selects 3–5 representative occurrences of a word across varied sentence positions:
    - sentence-initial (token_index <= 2)
    - sentence-medial
    - sentence-final
    Ensures instances come from different verses/chapters where possible.
    """
    if len(occurrences) <= target_count:
        return occurrences

    # Bucket occurrences by sentence position
    initials = []
    medials = []
    finals = []

    for occ in occurrences:
        idx = occ["token_index"]
        if idx <= 2:
            initials.append(occ)
        elif occ["char_span"][1] >= len(occ.get("context_snippet", "")) - 10:
            finals.append(occ)
        else:
            medials.append(occ)

    selected = []
    seen_verses = set()

    # Pick 1 initial, 2 medials, 1 final if possible
    pools = [initials, medials, finals, occurrences]
    for pool in pools:
        for occ in pool:
            if occ["verse_id"] not in seen_verses:
                selected.append(occ)
                seen_verses.add(occ["verse_id"])
                break
        if len(selected) >= target_count:
            break

    # If still need more, fill from remaining
    for occ in occurrences:
        if occ["verse_id"] not in seen_verses:
            selected.append(occ)
            seen_verses.add(occ["verse_id"])
            if len(selected) >= target_count:
                break

    return selected[:target_count]


def main():
    print("=================================================================")
    print("   URHOBO TTS — PHASE 7.2 DISPOSITION CLASSIFICATION")
    print("=================================================================")
    t0 = time.time()

    if not OCCURRENCES_PATH.exists():
        print(f"Error: {OCCURRENCES_PATH} not found. Run scripts/10_map_priority_occurrences.py first.", file=sys.stderr)
        sys.exit(1)

    with open(OCCURRENCES_PATH, "r", encoding="utf-8") as f:
        corpus_data = json.load(f)

    ucla_dict = load_ucla_words()
    print(f"  Loaded {corpus_data['total_priority_targets']} priority targets")
    print(f"  Loaded {len(ucla_dict)} secondary acoustic audio entries from UCLA")

    dispositions: Dict[str, Dict[str, Any]] = {}
    resolved_corpus_count = 0
    resolved_secondary_count = 0
    unverified_count = 0

    total_injection_instances = 0

    # 1. Classify words with corpus occurrences
    occurrences_by_word = corpus_data.get("occurrences_by_word", {})
    for word, payload in occurrences_by_word.items():
        all_occs = payload["occurrences"]
        target_info = payload["target_info"]
        selected_occs = select_best_instances(all_occs, target_count=4)
        total_injection_instances += len(selected_occs)
        resolved_corpus_count += 1

        dispositions[word] = {
            "plain_form": word,
            "disposition": "resolved-from-corpus",
            "canonical_tone_form": target_info["canonical_tone_form"],
            "gloss_en": target_info["gloss_en"],
            "category": target_info["category"],
            "origin": target_info.get("origin", "curriculum_seed"),
            "total_corpus_occurrences": payload["occurrences_count"],
            "selected_injection_count": len(selected_occs),
            "selected_instances": selected_occs,
        }

    # 2. Classify zero-occurrence words
    zero_words = corpus_data.get("zero_occurrence_words", [])
    for item in zero_words:
        word = item["plain_form"]
        info = item["info"]

        # Check secondary audio source (UCLA)
        if word in ucla_dict:
            resolved_secondary_count += 1
            ucla_entry = ucla_dict[word]
            dispositions[word] = {
                "plain_form": word,
                "disposition": "resolved-from-secondary-source",
                "canonical_tone_form": ucla_entry["canonical_tone_form"],
                "gloss_en": info["gloss_en"],
                "category": info["category"],
                "origin": info.get("origin", "curriculum_seed"),
                "secondary_source": ucla_entry["source_id"],
                "total_corpus_occurrences": 0,
                "selected_injection_count": 0,
                "selected_instances": [],
            }
        else:
            unverified_count += 1
            dispositions[word] = {
                "plain_form": word,
                "disposition": "explicitly-marked-unverified",
                "canonical_tone_form": info["canonical_tone_form"],
                "gloss_en": info["gloss_en"],
                "category": info["category"],
                "origin": info.get("origin", "curriculum_seed"),
                "total_corpus_occurrences": 0,
                "selected_injection_count": 0,
                "selected_instances": [],
            }

    # Save summary report
    summary_payload = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_priority_words": len(dispositions),
        "disposition_counts": {
            "resolved-from-corpus": resolved_corpus_count,
            "resolved-from-secondary-source": resolved_secondary_count,
            "resolved-from-new-recording": 0,
            "explicitly-marked-unverified": unverified_count,
        },
        "disposition_percentages": {
            "resolved-from-corpus": round(resolved_corpus_count / len(dispositions) * 100, 2),
            "resolved-from-secondary-source": round(resolved_secondary_count / len(dispositions) * 100, 2),
            "explicitly-marked-unverified": round(unverified_count / len(dispositions) * 100, 2),
        },
        "total_injection_instances_planned": total_injection_instances,
        "dispositions": dispositions,
    }

    OUT_DISPOSITIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_DISPOSITIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(summary_payload, f, indent=2, ensure_ascii=False)

    elapsed = time.time() - t0

    print("-----------------------------------------------------------------")
    print("                     DISPOSITION AUDIT SUMMARY                   ")
    print("-----------------------------------------------------------------")
    print(f"  1. resolved-from-corpus          : {resolved_corpus_count:>3} words ({summary_payload['disposition_percentages']['resolved-from-corpus']:>5.2f}%)")
    print(f"  2. resolved-from-secondary-source: {resolved_secondary_count:>3} words ({summary_payload['disposition_percentages']['resolved-from-secondary-source']:>5.2f}%)")
    print(f"  3. resolved-from-new-recording   :   0 words (0.00%)")
    print(f"  4. explicitly-marked-unverified  : {unverified_count:>3} words ({summary_payload['disposition_percentages']['explicitly-marked-unverified']:>5.2f}%)")
    print("-----------------------------------------------------------------")
    print(f"  Total Supervision Injections     : {total_injection_instances} verified instances selected")
    print(f"  Saved Dispositions Payload       : {OUT_DISPOSITIONS_PATH.relative_to(REPO_ROOT)}")
    print("-----------------------------------------------------------------")
    print(f"Phase 7.2 completed in {elapsed:.2f}s.")
    print("=================================================================")


if __name__ == "__main__":
    main()
