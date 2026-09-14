#!/usr/bin/env python3
"""
scripts/08_merge_lexicons.py

Phase 6.3 — Cross-Source Harmonization, Merger & Conflict Flagging.

Merges structured entries across the 4 parsed dictionary sources:
  - Ukere (1986)
  - Okrokoto (2020)
  - Urhobo Grammar Basic Course
  - UCLA Phonetics Archive

Logic:
  1. Aggregates entries by `plain_form` (and senses by English gloss similarity).
  2. Resolves canonical tone representations using source reliability hierarchy:
     UCLA Phonetics (acoustic/IPA) > Grammar Basic Course (minimal pairs) > Ukere (comprehensive) > Okrokoto (pedagogical).
  3. Where multiple sources confirm the same tone pattern, tags `agreement: true`.
  4. Where sources conflict in pitch or only a single low-confidence source exists, tags `needs_review: true`.
  5. Flags all detected homograph pairs (words with identical plain spelling but differing tone/meaning).
  6. Emits `data/lexicon/merged_lexicon.jsonl` and an audit summary.
"""

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
PARSED_DIR = REPO_ROOT / "data" / "interim" / "lexicon_parsed"
LEXICON_DIR = REPO_ROOT / "data" / "lexicon"


def normalize_gloss(gloss: str) -> str:
    """Normalizes English gloss for semantic comparison."""
    g = gloss.lower().strip()
    g = re.sub(r"[^a-z0-9\s]", " ", g)
    words = [w for w in g.split() if w not in ("a", "an", "the", "to", "of", "in", "for", "also", "called")]
    return " ".join(words)


def glosses_overlap(g1: str, g2: str) -> bool:
    """Returns True if two glosses share at least one significant content word."""
    w1 = set(normalize_gloss(g1).split())
    w2 = set(normalize_gloss(g2).split())
    return bool(w1 & w2)


def tones_equivalent(t1: str, t2: str) -> bool:
    """
    Checks if two tone forms are phonologically equivalent (case-insensitive,
    ignoring minor transcription variations).
    """
    s1 = t1.lower().strip()
    s2 = t2.lower().strip()
    return s1 == s2


def merge_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Merges records for a single plain_form. Groups distinct senses/homographs.
    """
    if len(records) == 1:
        r = records[0]
        return [{
            "plain_form": r["plain_form"],
            "canonical_tone_form": r["canonical_tone_form"],
            "gloss_en": r["gloss_en"],
            "pos": r["pos"],
            "source_ids": [r["source_id"]],
            "sources_count": 1,
            "agreement": False,
            "needs_review": True,
            "review_reasons": ["single_source"]
        }]

    # Cluster by gloss semantic overlap or distinct tone markings
    clusters: List[List[Dict[str, Any]]] = []

    for r in records:
        placed = False
        for c in clusters:
            # If gloss overlaps, consider it same sense
            if any(glosses_overlap(r["gloss_en"], existing["gloss_en"]) for existing in c):
                c.append(r)
                placed = True
                break
        if not placed:
            clusters.append([r])

    merged_results = []
    # Source priority weights: UCLA (4) > Grammar (3) > Ukere (2) > Okrokoto (1)
    SOURCE_WEIGHTS = {
        "ucla_phonetics": 4,
        "ucla_phonetics_1960": 4,
        "grammar_basic_course": 3,
        "ukere_1986": 2,
        "okrokoto_2020": 1
    }

    for cluster in clusters:
        source_ids = sorted(list(set(x["source_id"] for x in cluster)))
        tone_forms = [x["canonical_tone_form"] for x in cluster]
        all_glosses = [x["gloss_en"] for x in cluster]
        pos_list = [x["pos"] for x in cluster if x.get("pos")]
        best_pos = pos_list[0] if pos_list else "n."

        # Check tone agreement
        unique_tones = set(t.lower() for t in tone_forms)
        has_agreement = len(source_ids) >= 2 and len(unique_tones) == 1

        # Select best canonical tone form according to source priority
        best_entry = max(cluster, key=lambda x: SOURCE_WEIGHTS.get(x["source_id"], 0))
        best_tone_form = best_entry["canonical_tone_form"]

        needs_rev = False
        reasons = []

        if len(unique_tones) > 1 and len(source_ids) >= 2:
            needs_rev = True
            reasons.append(f"cross_source_tone_conflict: {list(unique_tones)}")
        elif len(source_ids) == 1:
            needs_rev = True
            reasons.append("single_source")

        # Combine glosses cleanly
        combined_gloss = " / ".join(dict.fromkeys(all_glosses))

        merged_results.append({
            "plain_form": cluster[0]["plain_form"],
            "canonical_tone_form": best_tone_form,
            "gloss_en": combined_gloss,
            "pos": best_pos,
            "source_ids": source_ids,
            "sources_count": len(source_ids),
            "agreement": has_agreement,
            "needs_review": needs_rev,
            "review_reasons": reasons
        })

    return merged_results


def main():
    print("=================================================================")
    print("   URHOBO TTS — PHASE 6.3 CROSS-SOURCE LEXICON MERGER")
    print("=================================================================")
    LEXICON_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    sources = ["ukere_1986", "okrokoto_2020", "grammar_basic_course", "ucla_phonetics"]
    records_by_plain = defaultdict(list)
    total_raw_entries = 0

    for s in sources:
        p = PARSED_DIR / f"{s}_parsed.jsonl"
        if not p.exists():
            continue
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line.strip())
                records_by_plain[r["plain_form"]].append(r)
                total_raw_entries += 1

    print(f"  Loaded {total_raw_entries} total records across {len(sources)} sources")
    print(f"  Aggregating {len(records_by_plain)} unique plain word forms...")

    merged_lexicon: List[Dict[str, Any]] = []
    homograph_count = 0
    agreement_count = 0
    review_count = 0

    for plain_form in sorted(records_by_plain.keys()):
        cluster_records = records_by_plain[plain_form]
        merged = merge_records(cluster_records)
        if len(merged) > 1:
            homograph_count += 1
            for m in merged:
                m["is_homograph"] = True
        else:
            for m in merged:
                m["is_homograph"] = False

        for m in merged:
            if m["agreement"]:
                agreement_count += 1
            if m["needs_review"]:
                review_count += 1
            merged_lexicon.append(m)

    # Sort merged lexicon alphabetically by plain_form
    merged_lexicon.sort(key=lambda x: (x["plain_form"], x["canonical_tone_form"]))

    out_file = LEXICON_DIR / "merged_lexicon.jsonl"
    with open(out_file, "w", encoding="utf-8") as f:
        for r in merged_lexicon:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    elapsed = time.time() - t0

    print("-----------------------------------------------------------------")
    print(f"  Merged Lexicon Records   : {len(merged_lexicon)}")
    print(f"  Multi-Source Agreement   : {agreement_count} entries (verified by >=2 independent sources)")
    print(f"  Homograph Lemmas Detected: {homograph_count} plain forms with distinct senses/tones")
    print(f"  Flagged for Review       : {review_count} entries (single-source or pitch conflict)")
    print(f"  Saved to                 : {out_file.relative_to(REPO_ROOT)}")
    print("-----------------------------------------------------------------")
    print(f"Merger completed in {elapsed:.2f}s.")
    print("=================================================================")


if __name__ == "__main__":
    main()
