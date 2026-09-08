"""
Script 02: Convert chapter MP3s to 16kHz mono WAV with normalization and filtering.

Inputs:
  - data/raw/audio/{book}/{book}_{chapter}.mp3
Outputs:
  - data/interim/wav/{book}/{book}_{chapter}.wav (16kHz mono, -23 LUFS normalized, 80Hz HPF)
"""

import sys
import argparse
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_AUDIO_DIR = DATA_DIR / "raw" / "audio"
INTERIM_WAV_DIR = DATA_DIR / "interim" / "wav"


def main():
    parser = argparse.ArgumentParser(description="Convert chapter MP3s to normalized 16kHz mono WAV.")
    parser.add_argument("--input-dir", type=Path, default=RAW_AUDIO_DIR)
    parser.add_argument("--output-dir", type=Path, default=INTERIM_WAV_DIR)
    args = parser.parse_args()

    print(f"[02_convert_audio] Converting audio from {args.input_dir} -> {args.output_dir}...")
    # Implemented in Phase 3


if __name__ == "__main__":
    main()
