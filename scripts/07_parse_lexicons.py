#!/usr/bin/env python3
"""
scripts/07_parse_lexicons.py

Phase 6.2 — Canonical Tone Schema & Structured Lexicon Parser.

Parses extracted raw texts from reference dictionaries and archives:
  - Ukere (1986 / Roger Blench 2005)
  - Okrokoto (2020)
  - Urhobo Grammar Basic Course
  - UCLA Phonetics Archive (1960 and contemporary)

Maps raw entries to canonical Africanist tone scheme:
  - High tone: acute (´)
  - Low tone: grave (`)
  - Rising tone: caron (ˇ)
  - Falling tone: circumflex (ˆ)
  - Mid tone: unmarked

Emits structured JSONL files for each source into `data/interim/lexicon_parsed/`:
  - ukere_1986_parsed.jsonl
  - okrokoto_2020_parsed.jsonl
  - grammar_basic_course_parsed.jsonl
  - ucla_phonetics_parsed.jsonl
"""

import json
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure UTF-8 console output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "interim" / "lexicon_raw"
PARSED_DIR = REPO_ROOT / "data" / "interim" / "lexicon_parsed"


def strip_tone_marks(text: str) -> str:
    """
    Removes tone marks (acute, grave, caron, circumflex, tilde) while strictly
    preserving Urhobo open-mid sub-dots (ẹ, ọ).
    """
    # Replace sub-dot characters with placeholders so NFD decomposition doesn't strip them
    text = text.replace("ẹ", "§e").replace("Ẹ", "§E")
    text = text.replace("ọ", "§o").replace("Ọ", "§O")
    
    # Decompose unicode
    decomposed = unicodedata.normalize("NFD", text)
    # Filter out combining acute (0301), grave (0300), circumflex (0302), caron (030C), tilde (0303)
    filtered = "".join(c for c in decomposed if ord(c) not in (0x0300, 0x0301, 0x0302, 0x0303, 0x030C))
    composed = unicodedata.normalize("NFC", filtered)
    
    # Restore sub-dots
    composed = composed.replace("§e", "ẹ").replace("§E", "Ẹ")
    composed = composed.replace("§o", "ọ").replace("§O", "Ọ")
    return composed


def clean_ukere_orthography(text: str) -> str:
    """Decodes PUA characters in Ukere dictionary text."""
    text = text.replace("é\uf024", "ẹ́").replace("É\uf024", "Ẹ́")
    text = text.replace("ó\uf027", "ọ́").replace("Ó\uf027", "Ọ́")
    text = text.replace("é\uf027", "ẹ́").replace("É\uf027", "Ẹ́")
    text = text.replace("ó\uf024", "ọ́").replace("Ó\uf024", "Ọ́")
    text = text.replace("\uf024", "").replace("\uf027", "")
    return text


def clean_headword(raw_hw: str) -> Tuple[str, str]:
    """
    Cleans headword string: removes trailing homograph numbers (e.g. áda1 -> áda).
    Returns (canonical_tone_form, plain_form).
    """
    # Strip trailing digits e.g. áda1 -> áda
    hw = re.sub(r"\d+$", "", raw_hw.strip()).strip()
    # Strip parenthetical alternative from headword if present e.g. "agbara (aga)" -> "agbara"
    hw_main = re.sub(r"\s*\([^\)]+\)", "", hw).strip()
    plain = strip_tone_marks(hw_main).lower()
    return hw_main, plain


def parse_ukere(raw_file: Path, out_file: Path) -> int:
    """Parses Ukere (1986) raw text."""
    if not raw_file.exists():
        return 0

    lines = raw_file.read_text(encoding="utf-8").split("\n")
    # Pre-clean PUA characters
    cleaned_lines = [clean_ukere_orthography(l.strip()) for l in lines if l.strip()]

    # Stitch lines where definition or PoS wrapped
    stitched = []
    for l in cleaned_lines:
        if re.match(r"^[A-ZẸỌ]\s+[a-zẹọ]$", l):
            continue
        if stitched and (re.match(r"^(?:n\.|v\.|a\.|adv\.|conj\.|prep\.|pron\.|excl\.|num\.|interj\.|aux\.|id\.|phr\.)", l) or l.startswith("(")):
            if not re.search(r"\b(?:n\.|v\.|a\.|adv\.|conj\.|prep\.|pron\.|excl\.|num\.|interj\.|aux\.|id\.|phr\.)\b", stitched[-1]):
                stitched[-1] = stitched[-1] + " " + l
                continue
        stitched.append(l)

    POS_LIST = ["n.", "v. t", "v. i", "v.t", "v.i", "v.", "a.", "adv.", "conj.", "prep.", "pron.", "excl.", "num.", "interj.", "aux.", "id.", "phr.", "exp.", "int."]
    pos_pattern = re.compile(r"\s+(" + "|".join(re.escape(p) for p in sorted(POS_LIST, key=len, reverse=True)) + r")(?:\s+|$)", re.IGNORECASE)

    records = []
    for line in stitched:
        m = pos_pattern.search(line)
        if m:
            raw_hw = line[:m.start()].strip()
            pos = m.group(1).strip()
            gloss = line[m.end():].strip()
            if not raw_hw:
                continue
            canonical_hw, plain_hw = clean_headword(raw_hw)
            if not plain_hw:
                continue
            
            # Confidence: high if pos and gloss exist and headword is reasonable
            conf = "high" if len(plain_hw) >= 2 and gloss else "low"
            rec = {
                "plain_form": plain_hw,
                "canonical_tone_form": canonical_hw,
                "gloss_en": gloss,
                "pos": pos.lower(),
                "source_id": "ukere_1986",
                "raw_source_line": line,
                "confidence": conf
            }
            records.append(rec)

    with open(out_file, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"  [Ukere 1986] Parsed {len(records)} entries -> {out_file.name}")
    return len(records)


def parse_okrokoto(raw_file: Path, out_file: Path) -> int:
    """Parses Okrokoto (2020) raw text."""
    if not raw_file.exists():
        return 0

    lines = raw_file.read_text(encoding="utf-8").split("\n")
    records = []

    for line in lines:
        line_s = line.strip()
        if not line_s or len(line_s) <= 2 or "URHOBO WORDS" in line_s:
            continue
        
        # Split on ellipsis or dot sequences
        parts = re.split(r"…+|\.{3,}", line_s)
        if len(parts) >= 2:
            raw_hw = parts[0].strip()
            gloss = parts[-1].strip()
            # Clean leading dots or whitespace from gloss
            gloss = re.sub(r"^[\.\s]+", "", gloss).strip()
            if not raw_hw or not gloss:
                continue
            
            canonical_hw, plain_hw = clean_headword(raw_hw)
            if not plain_hw:
                continue

            # Infer pos if present in gloss (e.g. starts with "A species of...", "Guilty verdict")
            conf = "high" if len(plain_hw) >= 2 and gloss else "low"
            rec = {
                "plain_form": plain_hw,
                "canonical_tone_form": canonical_hw,
                "gloss_en": gloss,
                "pos": "n.", # Okrokoto vocabulary is predominantly nominal
                "source_id": "okrokoto_2020",
                "raw_source_line": line_s,
                "confidence": conf
            }
            records.append(rec)

    with open(out_file, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"  [Okrokoto 2020] Parsed {len(records)} entries -> {out_file.name}")
    return len(records)


def parse_grammar_course(raw_file: Path, out_file: Path) -> int:
    """Parses tone exercises and vocabulary tables from Grammar Basic Course."""
    if not raw_file.exists():
        return 0

    lines = raw_file.read_text(encoding="utf-8").split("\n")
    records = []

    def clean_grammar_line(text: str) -> str:
        text = text.replace("e\u0316", "ẹ").replace("E\u0316", "Ẹ")
        text = text.replace("o\u0316", "ọ").replace("O\u0316", "Ọ")
        text = text.replace("e̖", "ẹ").replace("E̖", "Ẹ")
        text = text.replace("o̖", "ọ").replace("O̖", "Ọ")
        return text

    alpha_pattern = re.compile(r"^[A-ZẸỌ]+\s*==?\s*([^\(]+)\s*\(([^\)]+)\)", re.IGNORECASE)

    # Specific tone pair lines in Chapter 1
    # Oma Body Óma Statute
    # Ẹvwé Goat  Ẹvwe Kola nut
    # Odẹ Name Ódẹˊ Tomorrow
    # Úko Back Úkó Cup
    # Asa Place Asá A bird’s name
    pair_lines = [
        ("Oma", "Body", "Óma", "Statute"),
        ("Ẹvwé", "Goat", "Ẹvwe", "Kola nut"),
        ("Odẹ", "Name", "Ódẹ́", "Tomorrow"),
        ("Úko", "Back", "Úkó", "Cup"),
        ("Asa", "Place", "Asá", "A bird's name"),
        ("Ató", "Chewing stick", "Ato", "Desert"),
        ("òkà", "Style", "óka", "Mark"),
        ("Erha", "Three (3)", "ẽrha", "Palm oil shaft for fire"),
        ("Ógọ", "In-law / relative", "Ọgó", "Bottle"),
        ("ùdì", "Wine / drink", "údi", "Chest / trunk"),
        ("ení", "Elephant", "eni", "Head pad")
    ]

    for p in pair_lines:
        w1, g1, w2, g2 = p
        c1, pl1 = clean_headword(w1)
        c2, pl2 = clean_headword(w2)
        records.append({
            "plain_form": pl1,
            "canonical_tone_form": c1,
            "gloss_en": g1,
            "pos": "n.",
            "source_id": "grammar_basic_course",
            "raw_source_line": f"{w1} ({g1}) vs {w2} ({g2})",
            "confidence": "high"
        })
        records.append({
            "plain_form": pl2,
            "canonical_tone_form": c2,
            "gloss_en": g2,
            "pos": "n.",
            "source_id": "grammar_basic_course",
            "raw_source_line": f"{w1} ({g1}) vs {w2} ({g2})",
            "confidence": "high"
        })

    for line in lines:
        l = clean_grammar_line(line.strip())
        if not l or l.startswith("--- PAGE"):
            continue

        # Check alphabet pattern e.g. A = ame (water)
        m_alpha = alpha_pattern.match(l)
        if m_alpha:
            raw_hw = m_alpha.group(1).strip()
            gloss = m_alpha.group(2).strip()
            # Clean comments like "discontinue)OR JE..."
            gloss = gloss.split("OR")[0].strip()
            canonical_hw, plain_hw = clean_headword(raw_hw)
            if plain_hw and gloss and len(plain_hw) > 1 and " " not in plain_hw:
                records.append({
                    "plain_form": plain_hw,
                    "canonical_tone_form": canonical_hw,
                    "gloss_en": gloss,
                    "pos": "n.",
                    "source_id": "grammar_basic_course",
                    "raw_source_line": l,
                    "confidence": "high"
                })

    with open(out_file, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"  [Grammar Course] Parsed {len(records)} entries -> {out_file.name}")
    return len(records)


def parse_ucla_phonetics(raw_tsv: Path, raw_1960_tsv: Path, out_file: Path) -> int:
    """Parses UCLA Phonetics tables into structured records."""
    records = []

    # 1. Contemporary list (107 words)
    if raw_tsv.exists():
        lines = raw_tsv.read_text(encoding="utf-8").split("\n")[1:]
        for line in lines:
            parts = line.strip().split("\t")
            if len(parts) >= 4:
                idx, plain_hw, phonetic_hw, gloss = parts[:4]
                plain_clean = plain_hw.strip().lower()
                # If plain_form was omitted in HTML table (e.g. phrases 102-107), derive from phonetic
                if not plain_clean and phonetic_hw.strip():
                    plain_clean = strip_tone_marks(phonetic_hw.strip()).lower()
                    # map IPA to standard Urhobo orthography
                    plain_clean = plain_clean.replace("ɛ", "ẹ").replace("ɔ", "ọ").replace("ʍ", "hw").replace("ʋ", "vw").replace("ɣ", "gh")
                if plain_clean:
                    rec = {
                        "plain_form": plain_clean,
                        "canonical_tone_form": phonetic_hw.strip(),
                        "gloss_en": gloss.strip(),
                        "pos": "phr." if " " in plain_clean else "n.",
                        "source_id": "ucla_phonetics",
                        "raw_source_line": line.strip(),
                        "confidence": "high"
                    }
                    records.append(rec)

    # 2. 1960 archive list (32 words)
    if raw_1960_tsv.exists():
        lines = raw_1960_tsv.read_text(encoding="utf-8").split("\n")[1:]
        for line in lines:
            parts = line.strip().split("\t")
            if len(parts) >= 3:
                idx, toned_hw, gloss = parts[:3]
                plain_hw = strip_tone_marks(toned_hw).lower()
                rec = {
                    "plain_form": plain_hw,
                    "canonical_tone_form": toned_hw.strip(),
                    "gloss_en": gloss.strip(),
                    "pos": "n.",
                    "source_id": "ucla_phonetics_1960",
                    "raw_source_line": line.strip(),
                    "confidence": "high"
                }
                records.append(rec)

    with open(out_file, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"  [UCLA Phonetics] Parsed {len(records)} entries -> {out_file.name}")
    return len(records)


def main():
    print("=================================================================")
    print("   URHOBO TTS — PHASE 6.2 STRUCTURED LEXICON PARSER")
    print("=================================================================")
    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    n_ukere = parse_ukere(RAW_DIR / "ukere_1986_raw.txt", PARSED_DIR / "ukere_1986_parsed.jsonl")
    n_okrokoto = parse_okrokoto(RAW_DIR / "okrokoto_2020_raw.txt", PARSED_DIR / "okrokoto_2020_parsed.jsonl")
    n_grammar = parse_grammar_course(RAW_DIR / "grammar_basic_course_raw.txt", PARSED_DIR / "grammar_basic_course_parsed.jsonl")
    n_ucla = parse_ucla_phonetics(RAW_DIR / "ucla_phonetics_raw.tsv", RAW_DIR / "ucla_phonetics_1960_raw.tsv", PARSED_DIR / "ucla_phonetics_parsed.jsonl")

    total = n_ukere + n_okrokoto + n_grammar + n_ucla
    elapsed = time.time() - t0

    print("-----------------------------------------------------------------")
    print(f"Parsed {total} total lexical entries across 4 sources in {elapsed:.2f}s.")
    print("=================================================================")


if __name__ == "__main__":
    main()
