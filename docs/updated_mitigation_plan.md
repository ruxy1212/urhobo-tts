# Phase 9 Fine-Tuning: Updated Post-Training Diagnostic & Mitigation Plan

## 1. Executive Summary

Following the initial 5,000-step fine-tuning run of `facebook/mms-tts-yor` on 2.52 hours of Urhobo Genesis audio, the resulting model exhibited severe auditory defects: a metallic robotic buzz, swallowed syllables, and a near-total lack of natural Urhobo intonation.

A deeper analysis revealed that the issues stem from catastrophic adversarial divergence (GAN loss explosion up to 130), a 76% tone-blindness in the training text, excessively tight forced-alignment audio cuts, and a dataset size slightly below the optimal VITS transfer-learning threshold.

This updated document details the sequential, root-cause fixes required to achieve natural, studio-quality Urhobo speech.

## 2. Root Cause Analysis

| Defect | Root Cause | 
 | ----- | ----- | 
| **Flat / Missing Intonation** | **76% Tone-Blindness:** Only 24.25% of the training verses had tone diacritics injected. For the remaining 76%, the pitch predictor received flat text but heard melodic audio, forcing it to average out the pitch into a flat, robotic monotone. | 
| **Swallowed Syllables** | **Aggressive Audio Slicing:** The forced aligner stripped diacritics to map the text, resulting in tightly bounded timestamps. The 50ms padding at segment edges physically cut off the natural duration of tonal glides (like the rising-falling *ive*). | 
| **Coarse / Robotic Buzz** | **Adversarial GAN Divergence:** Full fine-tuning of the HiFi-GAN vocoder on a small dataset caused the discriminator to overpower the generator, baking high-frequency artifacts (white noise) into the weights. | 
| **Muffled Urhobo Consonants** | **Yoruba Acoustic Ceiling:** While the Yoruba base model is excellent for tones, it lacks native acoustics for Urhobo-specific letters (like 'v'). A 100% frozen decoder cannot learn these new sounds properly. | 

## 3. Step 1: Dataset Expansion (Reaching the 5–10 Hour Target)

To improve phonetic robustness and provide the text encoder with more acoustic variety, we will expand the training corpus from 2.52 hours to approximately 6.3 hours. We will strictly use Old Testament narrative books to maintain the pristine, single-speaker acoustic environment and avoid the background noise inherent in dramatized New Testament recordings.

* **Target Books:** Exodus (`EXO`), Joshua (`JOS`), and Ruth (`RUT`).

* **Expected Yield:** \~4.75 raw hours, netting approximately **3.8 high-confidence hours** after filtering (confidence >= -0.85).

* **Commands:**

  * `python scripts/01_scrape_text.py --book EXO --chapters 1-40`

  * `python scripts/01_scrape_text.py --book JOS --chapters 1-24`

  * `python scripts/01_scrape_text.py --book RUT --chapters 1-4`

  * *(Followed by the standard conversion, alignment, and slicing pipeline for these books).*

## 4. Step 2: Data Pipeline Fixes

Before training, the text and audio data must be mathematically calibrated to support Urhobo's melody and pacing.

### A. Automate 100% Tone Imputation

* **Action:** Modify `scripts/12_inject_tone_supervision.py`.

* **Logic:** Iterate through all plain-text verses in `train.jsonl`. Perform a lookup against the 2,561 canonical entries in `data/lexicon/merged_lexicon.jsonl`. Automatically inject canonical tone marks (e.g., `ó`, `ò`, `ǒ`) for all high-confidence dictionary matches.

* **Verification:** `tone_supervision_report.json` must reflect near 100% diacritic coverage for known vocabulary across the entire dataset.

### B. Expand Audio Boundary Windows

* **Action:** Update `scripts/04_slice_audio.py`.

* **Logic:** Increase the segment boundary padding from `50ms` to `80ms`. This gives the stochastic duration predictor the physical time needed to sustain tonal glides and natural consonant decays.

* **Verification:** Manually listen to freshly sliced clips to ensure the ends of sentences are no longer rushed or clipped.

## 5. Step 3: Two-Stage Semi-Frozen Fine-Tuning

To prevent the discriminator from destroying the audio quality while still allowing the vocoder to learn Urhobo-specific sounds (like 'v' and 'c'), we will use a two-stage step scheduler.

### Stage 1: Alignment & Pitch Stabilization (Steps 0 – 1000)

* **Mechanics:**

  * Freeze the vocoder: `model.decoder.requires_grad_(False)` and `model.posterior_encoder.requires_grad_(False)`.

  * Disable the adversarial discriminator completely.

  * Use a per-step cosine learning rate schedule peaking at `2e-4`.

* **Goal:** Force the newly expanded 70-token text encoder to perfectly align text-to-audio and stabilize the pitch predictor using the newly imputed tone data, without triggering GAN divergence.

### Stage 2: Acoustic Refinement (Steps 1001 – 1500)

* **Mechanics:**

  * Unfreeze the decoder.

  * Drop the learning rate dramatically to `1e-5`.

* **Goal:** Allow the vocoder to gently learn the acoustic properties of missing Urhobo consonants without drifting away from Meta's pristine Yoruba baseline.

## 6. Step 4: Inference Pacing Calibration

At evaluation and runtime, the model will inherently try to read at a brisk, scripture-reading pace. To allow the melodic vowels to articulate fully for language learners:

* **Configuration:** Set default generation parameters to `speaking_rate=0.85` and `noise_scale=0.33`.

* **Verification:** Synthesize the priority numbers (1–5). The pacing should allow words like *ọvo* and *ive* to stretch naturally with correct intonation.