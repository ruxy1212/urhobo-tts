"""
Script 05: Filter and format training dataset for Hugging Face VITS fine-tuning.

Inputs:
  - data/processed/segments/
  - Alignment confidence scores
Outputs:
  - Hugging Face Dataset or metadata.csv (audio_path, text, speaker_id)
"""

import sys
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Build filtered training dataset for VITS fine-tuning.")
    args = parser.parse_args()
    print("[05_build_dataset] Dataset builder initialized...")


if __name__ == "__main__":
    main()
