"""
Script 03: Forced Alignment using ctc-forced-aligner.

Inputs:
  - data/interim/wav/{book}/{book}_{chapter}.wav
  - data/raw/text/{book}/{book}_{chapter}.json
Outputs:
  - data/interim/alignments/{book}/{book}_{chapter}.json (Token/word/verse-level timestamps and quality scores)
"""

import sys
import argparse
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def main():
    parser = argparse.ArgumentParser(description="Run CTC forced alignment on Urhobo chapter audio.")
    parser.add_argument("--chapter", type=str, help="Book and chapter (e.g. GEN_001)")
    args = parser.parse_args()

    print(f"[03_align] Forced alignment runner initialized...")
    # Implemented in Phase 4 (Run locally or on Kaggle GPU)


if __name__ == "__main__":
    main()
