# Urhobo TTS Engine (`urhobo-tts`)

An end-to-end Text-to-Speech (TTS) pipeline and tone-disambiguation system for the Urhobo language, fine-tuned from Meta's MMS Yoruba checkpoint to power learning and audio features in the *Mẹ́ nẹ Urhobo* platform.

---

## 1. Locked Decisions & Core Architecture

* **Base Model**: Meta MMS Yoruba checkpoint ([`facebook/mms-tts-yor`](https://huggingface.co/facebook/mms-tts-yor), VITS architecture).
  * *Rationale*: Yoruba orthography natively shares the acute (`´`) and grave (`` ` ``) diacritics reflecting Urhobo's tone system.
* **Fine-Tuning Framework**: `ylacombe/finetune-hf-vits`.
* **Forced Aligner**: [`ctc-forced-aligner`](https://pypi.org/project/ctc-forced-aligner/) via CTC frame probability matching.
* **Compute Architecture**: **Kaggle Notebooks (Free Tier, GPU P100/T4) exclusively**.
  * Local development handles text scraping, normalization, dictionary parsing, and CPU audio preprocessing.
  * Heavy compute (forced alignment and VITS fine-tuning) is offloaded to Kaggle's ~30 GPU-hours/week quota.
* **Tone Disambiguation**: LLM-assisted extraction from reference dictionary PDFs (Phase 6) grounded to clean Bible audio segments (Phase 7).
* **Content Scoping**: Stories and conversational phrases for v1 are constrained to sentences drawn or closely adapted from the aligned Bible corpus text to prevent unmodeled phrase-level downstep issues.

---

## 2. Licensing Documentation & Compliance Gates

Before commercial distribution or deployment, two independent licensing gates must be observed:

### Gate 1 — Model & Aligner License (Meta MMS)
* `facebook/mms-tts-yor` and the MMS forced-alignment model are distributed under the **CC-BY-NC-4.0 (Creative Commons Attribution-NonCommercial 4.0 International)** license.
* Any fine-tuned checkpoint derived from MMS inherits this non-commercial restriction.
* **Current Status for v1**: Free/educational/non-commercial use only. Commercial monetization requires either training a model from scratch on permissible weights or securing a commercial license agreement.

### Gate 2 — Source Content License (BSN Urhobo Bible UBV77)
* The Urhobo Old Testament audio recording and text (`UBV77`, Bible Society of Nigeria) has proprietary copyright terms.
* Even if training a model from scratch, derived synthetic speech or distributed speech slices must comply with BSN's research/non-commercial redistribution policies.
* **Current Status for v1**: Non-commercial research & education use.

---

## 3. Directory Layout

```text
urhobo-tts/
  ├── data/
  │   ├── raw/
  │   │   ├── audio/           # Raw downloaded chapter MP3s (UBV77 OT)
  │   │   ├── text/            # Raw scraped verse text per chapter
  │   │   └── dictionaries/    # Unmodified source dictionary PDFs
  │   ├── interim/
  │   │   ├── wav/             # 16kHz mono, loudness-normalized WAVs
  │   │   └── alignments/      # CTC forced alignment JSON files
  │   ├── processed/
  │   │   └── segments/        # Verse-level sliced audio + text pairs
  │   └── lexicon/             # Tone dictionary JSON/TSV artifacts
  ├── scripts/
  │   ├── 01_scrape_text.py
  │   ├── 02_convert_audio.py
  │   ├── 03_align.py
  │   ├── 04_segment.py
  │   ├── 05_build_dataset.py
  │   ├── 06_extract_lexicon.py
  │   ├── 07_tone_audio_bridge.py
  │   ├── 08_finetune.py
  │   ├── 09_evaluate.py
  │   ├── 10_render_curriculum.py
  │   └── 11_compress_and_package.py
  ├── models/
  │   └── checkpoints/         # Fine-tuned VITS checkpoints
  ├── app_content/
  │   ├── curriculum_vocab.tsv # Target app vocabulary seed list
  │   └── prerendered_audio/   # Exported app-ready audio clips
  ├── requirements.txt
  └── README.md
```

---

## 4. Kaggle Workflow

1. **Repository Sync**: Push this repository to GitHub. Kaggle notebooks clone directly from GitHub at runtime (`git clone https://github.com/<user>/urhobo-tts.git`).
2. **Notebook Setup**: Ensure phone verification is completed on Kaggle. Enable **GPU T4 x2 or P100** and toggle **Internet: On**.
3. **Data Mounting**: Small scripts and text datasets can be pulled via Git or Kaggle Datasets; output models/checkpoints are saved as Kaggle notebook artifacts or Hugging Face Hub checkpoints.
