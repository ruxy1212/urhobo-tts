# Phase 9 Fine-Tuning: Post-Training Diagnostic & Mitigation Plan

## 1. Executive Summary
Following the completion of the 5,000-step fine-tuning run of `facebook/mms-tts-yor` on 2.52 hours of Urhobo Genesis audio, the acoustic model successfully verified token-level Urhobo phonetic transfer (~60% correct accent and tone recognition). However, the generated audio exhibits severe auditory defects: persistent coarseness/metallic buzz, phoneme skipping in connected speech, and distorted pitch/duration contours on key vocabulary (e.g., numbers).

This document details the observed issues, technical root causes, and the concrete mitigation plan (Decoder-Frozen Training).

---

## 2. Observed Issues & Auditory Symptoms

### A. Coarse & Metallic Robotic Texture
* **Symptom**: Across all checkpoints (3000, 4000, and 5000), speech exhibits a harsh, buzzy, robotic rasp. It sounds degraded compared to both the smooth base `facebook/mms-tts-yor` model and the clean studio-recorded Genesis training audio.
* **Inference adjustment**: Lowering `noise_scale` to `0.33` partially reduced the jitter, but the underlying metallic distortion remained baked into the vocoder weights.

### B. Phoneme Skipping & Swallowed Syllables
* **Symptom**: In connected carrier sentences (e.g., *"Ọ́vo yen ọrọ kpahe. Ǐve yen rha cha"*), the model rushes through syllables, swallows transitional consonants, and skips phonemes entirely.
* **Duration distortion**: The pacing is unnaturally rapid, lacking natural inter-word decay and vowel sustaining.

### C. Severe Lexical & Contour Tone Failure (Numbers Benchmark)
* **Symptom**: Numbers 1–5 (*ọvo, ive, ẹrha, ẹne, iyorin*) fail to produce authentic Edoid contours:
  * **`Ọvo` (1)**: Should have stretched, sustained vowels ($[\text{ọ́}\cdot\text{vo}]$); synthesized clipped and hurried.
  * **`Ive` (2)**: Should have a peaked rising-falling glide on the prefix; synthesized flat or distorted.
  * **`Iyorin` (5)**: Dropped the audible nasal coda ($[\tilde{\imath}] / [\eta]$) when spelled without nasal markers, and swallowed the tap `r`.
* Only `ẹ́rha` (3) and `ẹ́ne` (4) sounded phonetically consistent.

### D. Intermediate Checkpoint Weight Normalization Trap
* **Symptom**: Intermediate checkpoints (`checkpoint-3000`, `checkpoint-4000`) emitted explosive white noise when loaded directly via `VitsModel.from_pretrained()`.
* **Cause**: `accelerator.save_state` saved unfused PyTorch weight normalization parameters (`weight_g` and `weight_v`). The model only fused weights at the very end of Step 5,000 via `model.decoder.remove_weight_norm()`.

---

## 3. Technical Root Cause Analysis

| Defect | Root Cause | Underlying Mechanism |
|---|---|---|
| **Coarse / Robotic Buzz** | **HiFi-GAN Vocoder Retraining with Active Discriminator** | Full fine-tuning updated all model parameters, including the HiFi-GAN decoder (`model.decoder`). On a small 2.5-hour dataset, the adversarial discriminator overfitted, forcing the decoder into high-frequency adversarial artifacts (metallic buzz) to escape discriminator penalties. |
| **Loss Explosion (22 $\rightarrow$ 130)** | **Adversarial Divergence** | Step loss started optimal at **22.5** (Step 500) and **24.8** (Step 1000), but climbed continuously: 47 (Step 2000), 62 (Step 3000), 86 (Step 4000), and **130.0** (Step 5000). The discriminator overpowered the generator, destabilizing synthesis. |
| **Learning Rate Stagnation** | **Per-Epoch Scheduler Glitch** | The run logged `lr=0.000198` at Step 5,000 (effectively zero decay from initial `0.000200`). `do_step_schedule_per_epoch=True` only stepped the scheduler 79 times ($0.999875^{79} \approx 0.990$), preventing the model from cooling into fine acoustic details. |
| **Phoneme Skipping & Rushed Pacing** | **Duration Predictor Collapse under GAN Penalty** | Under severe adversarial loss pressure, the stochastic duration predictor collapsed toward minimal durations, truncating vowel lengths and dropping low-energy phonemes. |

---

## 4. Mitigation Strategy: Decoder-Frozen Fine-Tuning

In modern low-resource TTS research (Meta MMS, Coqui, Hugging Face), adapting to a new language/dialect should **never retrain the HiFi-GAN vocoder**. Instead, **Reconstruction Fine-Tuning (Decoder-Frozen)** is the proven industry standard.

```
                    ┌────────────────────────────────────────────────────────┐
                    │                      TRAINABLE                         │
[Urhobo 70-Tokens] ─┼──> [Text Encoder] ──> [Duration Predictor] ──> [Flow] ─┼──┐
                    └────────────────────────────────────────────────────────┘  │
                                                                                ▼
                    ┌────────────────────────────────────────────────────────┐  │
                    │                   FROZEN (100% LOCKED)                 │  │
                    │               [Meta HiFi-GAN Decoder] <───────────────────┘
                    │        (Guarantees smooth, noise-free audio)           │
                    └────────────────────────────────────────────────────────┘
                                                │
                                                ▼
                                    [Pristine Urhobo Speech]
```

### Key Components of the Fix:

1. **Freeze the Decoder & Posterior Encoder**:
   ```python
   # Lock the HiFi-GAN vocoder to Meta's original pre-trained Yoruba weights
   model.decoder.requires_grad_(False)
   model.posterior_encoder.requires_grad_(False)
   ```
   * **Why it works**: The decoder retains 100% of Meta’s smooth, high-fidelity acoustic filtering. It cannot degrade, overfit, or buzz.

2. **Disable the Adversarial Discriminator**:
   * Since the decoder is frozen, the adversarial discriminator is unnecessary.
   * Training optimizes purely on **Mel reconstruction loss**, **KL divergence**, and **Duration loss**.
   * **No adversarial divergence. No loss climbing to 130.**

3. **Per-Step Cosine Learning Rate Decay**:
   * Switch from epoch-based scheduler to **per-step linear or cosine schedule with warmup**:
     * Warmup: 200 steps
     * Peak LR: `2e-4`
     * Target Min LR: `1e-5` (cooling down gradually to settle durations).

4. **Targeted Step Count: 1,500 – 2,000 Steps**:
   * The trainable text encoder has only ~10M parameters.
   * Optimal convergence occurs within **1,200 to 1,800 steps**.
   * Training time drops from 3.5 hours to **~25–35 minutes** on Kaggle GPU.

5. **Inference Pacing Calibration**:
   * Set default evaluation inference to `speaking_rate=0.85` and `noise_scale=0.33` to allow Edoid vowel lengths and tone glides to articulate naturally without rushing.
