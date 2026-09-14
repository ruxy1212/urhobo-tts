#!/usr/bin/env python3
"""
scripts/06_extract_raw_texts.py

Phase 6.1 — Raw Text Extraction & Source Structuring.

Extracts structured raw text from the born-digital reference dictionaries
and phonetic archives into `data/interim/lexicon_raw/`:
  - ukere_1986_raw.txt (Anthony Ukere 1986 / Roger Blench 2005)
  - okrokoto_2020_raw.txt (Ebireri Okrokoto 2020)
  - grammar_basic_course_raw.txt (Urhobo Grammar Basic Course)
  - language_primer_raw.txt (Urhobo Language Primer)
  - ucla_phonetics_raw.tsv (UCLA Phonetics Archive 107-word table)
  - ucla_phonetics_1960_raw.tsv (UCLA Phonetics Archive 1960 32-word table)
"""

import os
import re
import sys
import time
from pathlib import Path
from bs4 import BeautifulSoup
import pypdf

# UTF-8 console output for Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent
DICT_DIR = REPO_ROOT / "data" / "raw" / "dictionaries"
RAW_OUT_DIR = REPO_ROOT / "data" / "interim" / "lexicon_raw"


def extract_pdf_pages(pdf_path: Path, start_page: int = 1, end_page: int = None) -> list:
    """Extracts text page by page from a PDF file."""
    reader = pypdf.PdfReader(str(pdf_path))
    total_pages = len(reader.pages)
    if end_page is None or end_page > total_pages:
        end_page = total_pages

    pages_text = []
    for p_idx in range(start_page - 1, end_page):
        page = reader.pages[p_idx]
        txt = page.extract_text() or ""
        pages_text.append((p_idx + 1, txt))
    return pages_text


def extract_ukere(dict_dir: Path, out_dir: Path) -> int:
    """Extracts Ukere (1986) dictionary body (pages 4 to 53)."""
    pdf_path = dict_dir / "ukere_1986_dictionary.pdf"
    out_file = out_dir / "ukere_1986_raw.txt"
    pages = extract_pdf_pages(pdf_path, start_page=4, end_page=53)

    lines_out = []
    for page_num, text in pages:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        for line in lines:
            # Skip running headers/footers
            if "Urhobo Dictionary" in line and "Roger Blench" in line:
                continue
            if line.isdigit():
                continue
            if line == "Urhobo PoS English gloss":
                continue
            lines_out.append(line)

    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines_out) + "\n")

    print(f"  [Ukere 1986] Extracted {len(lines_out)} lines from 50 pages -> {out_file.name}")
    return len(lines_out)


def extract_okrokoto(dict_dir: Path, out_dir: Path) -> int:
    """Extracts Okrokoto (2020) dictionary body (pages 2 to 64)."""
    pdf_path = dict_dir / "okrokoto_dictionary.pdf"
    out_file = out_dir / "okrokoto_2020_raw.txt"
    pages = extract_pdf_pages(pdf_path, start_page=2, end_page=64)

    lines_out = []
    for page_num, text in pages:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        for line in lines:
            if line.isdigit():
                continue
            if "URHOBO WORDS" in line and "ENGLISH" in line:
                continue
            lines_out.append(line)

    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines_out) + "\n")

    print(f"  [Okrokoto 2020] Extracted {len(lines_out)} lines from 63 pages -> {out_file.name}")
    return len(lines_out)


def extract_grammar_course(dict_dir: Path, out_dir: Path) -> int:
    """Extracts Urhobo Grammar Basic Course vocabulary exercises and text."""
    pdf_path = dict_dir / "urhobo_grammar_basic_course.pdf"
    out_file = out_dir / "grammar_basic_course_raw.txt"
    pages = extract_pdf_pages(pdf_path, start_page=1, end_page=115)

    lines_out = []
    for page_num, text in pages:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if lines:
            lines_out.append(f"--- PAGE {page_num} ---")
            lines_out.extend(lines)

    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines_out) + "\n")

    print(f"  [Grammar Course] Extracted {len(lines_out)} lines from 115 pages -> {out_file.name}")
    return len(lines_out)


def extract_language_primer(dict_dir: Path, out_dir: Path) -> int:
    """Extracts Urhobo Language Primer text."""
    pdf_path = dict_dir / "urhobo_Language_primer.pdf"
    out_file = out_dir / "language_primer_raw.txt"
    pages = extract_pdf_pages(pdf_path, start_page=1, end_page=71)

    lines_out = []
    for page_num, text in pages:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if lines:
            lines_out.append(f"--- PAGE {page_num} ---")
            lines_out.extend(lines)

    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines_out) + "\n")

    print(f"  [Language Primer] Extracted {len(lines_out)} lines from 71 pages -> {out_file.name}")
    return len(lines_out)


def extract_ucla_wordlists(dict_dir: Path, out_dir: Path) -> tuple:
    """Extracts structured tables from UCLA Phonetics Archive HTML files."""
    # Main list (107 words)
    f1 = dict_dir / "word_list_for_urhobo.html"
    out1 = out_dir / "ucla_phonetics_raw.tsv"
    soup1 = BeautifulSoup(f1.read_text(encoding="utf-8", errors="ignore"), "html.parser")
    rows1 = soup1.find_all("tr")
    lines1 = ["index\turhobo_raw\turhobo_phonetic_tone\tenglish"]
    for r in rows1:
        cells = [c.get_text().strip() for c in r.find_all(["td", "th"])]
        if len(cells) >= 4 and cells[0].isdigit():
            lines1.append(f"{cells[0]}\t{cells[1]}\t{cells[2]}\t{cells[3]}")

    with open(out1, "w", encoding="utf-8") as f:
        f.write("\n".join(lines1) + "\n")

    # 1960 archive list (32 words)
    f2 = dict_dir / "word_list_for_urhobo_1960.html"
    out2 = out_dir / "ucla_phonetics_1960_raw.tsv"
    soup2 = BeautifulSoup(f2.read_text(encoding="utf-8", errors="ignore"), "html.parser")
    rows2 = soup2.find_all("tr")
    lines2 = ["index\turhobo_toned\tenglish"]
    for r in rows2:
        cells = [c.get_text().strip() for c in r.find_all(["td", "th"])]
        if len(cells) >= 3 and cells[0].isdigit():
            lines2.append(f"{cells[0]}\t{cells[1]}\t{cells[2]}")

    with open(out2, "w", encoding="utf-8") as f:
        f.write("\n".join(lines2) + "\n")

    print(f"  [UCLA Phonetics] Extracted {len(lines1)-1} items -> {out1.name}")
    print(f"  [UCLA 1960 Archive] Extracted {len(lines2)-1} items -> {out2.name}")
    return len(lines1) - 1, len(lines2) - 1


def main():
    print("=================================================================")
    print("      URHOBO TTS — PHASE 6.1 RAW TEXT EXTRACTION ENGINE")
    print("=================================================================")
    RAW_OUT_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    ukere_lines = extract_ukere(DICT_DIR, RAW_OUT_DIR)
    okrokoto_lines = extract_okrokoto(DICT_DIR, RAW_OUT_DIR)
    grammar_lines = extract_grammar_course(DICT_DIR, RAW_OUT_DIR)
    primer_lines = extract_language_primer(DICT_DIR, RAW_OUT_DIR)
    ucla_count, ucla_1960_count = extract_ucla_wordlists(DICT_DIR, RAW_OUT_DIR)

    elapsed = time.time() - t0
    print("-----------------------------------------------------------------")
    print(f"Extracted all 6 resources into {RAW_OUT_DIR.name}/ in {elapsed:.2f}s.")
    print("=================================================================")


if __name__ == "__main__":
    main()
