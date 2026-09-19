# Phase 9 Fine-Tuning: Revised Diagnostic & Mitigation Plan (v2)

This supersedes `training_issues_and_mitigation.md`. It keeps what that document got right, corrects two load-bearing assumptions, and adds a root cause (cold-start token embeddings) that the numbers benchmark evidence points to directly.

---

## 1. Headline answer: is the 2.52-hour Genesis corpus too small?

**No, not for the fix below.** The trainable module in a decoder-frozen recipe (text encoder + duration predictor + flow) is ~10M parameters. `ylacombe/finetune-hf-vits`'s own reference examples reach usable quality from 80–150 samples in ~20 minutes when training is stable (see e.g. `ylacombe/mms-mar-finetuned-monospeaker`). Your 998 clips are an order of magnitude more data than that floor.

Data volume *is* a secondary risk factor for the approach you actually ran (full decoder + active discriminator retraining): a small, single-speaker, single-domain corpus makes it much easier for a discriminator to memorize the "real" distribution and overpower the generator. But it is not the proximate cause of the buzz, the phoneme skipping, or the loss climbing to 130 — those are training-dynamics failures that would have surfaced on a 10-hour corpus too, just perhaps a little later.

Don't block the fix below on acquiring more Bible books. Do treat more data as a Phase 13/v2 lever for phrase-level naturalness, not a Phase 9 blocker.

---

## 2. Root causes, corrected and extended

| # | Defect | Original diagnosis (still valid) | Correction / addition |
|---|---|---|---|
| 1 | Metallic buzz, all checkpoints | HiFi-GAN decoder retrained with active discriminator on small data | **Refinement:** `finetune-hf-vits` requires a *converted* discriminator checkpoint before training (inference-only Hub checkpoints ship no discriminator). The standard setup step (`convert_original_discriminator_checkpoint.py --language_code yor`) pulls a discriminator that was already **fully converged** on Meta's original Yoruba training data — not randomly initialized. That discriminator had a sharp, confident "real vs. fake" boundary tuned to a different speaker, mic chain, and language from day one of your fine-tune. Any domain mismatch (recording condition as much as language) gave it an easy signal, and the generator's only way to satisfy it was to learn compensating high-frequency artifacts. **Please confirm which discriminator source you actually used** — this isn't visible in `commands.txt` (which only covers the local data-prep scripts, not the Kaggle training invocation) or `log.md`. If you used something other than the Yoruba-paired discriminator, the specific mechanism changes but the fix (drop the discriminator) doesn't. |
| 2 | Loss climbing 22 → 130 | Adversarial divergence | Confirmed by #1's mechanism — this is what a discriminator with an unfair, domain-mismatched advantage looks like in the loss curve. |
| 3 | LR frozen near-flat (0.000198 at step 5000) | Epoch-based scheduler stepped only 79 times | Confirmed. Combined with #1/#2, the model never got the chance to cool into fine acoustic detail while also fighting an escalating adversarial signal — the worst of both. |
| 4 | Phoneme skipping / rushed pacing | Duration predictor collapse under GAN penalty | Confirmed. Important for §3 below: this module's weights are *also* suspect for warm-starting, not just the decoder. |
| 5 | `checkpoint-3000`/`4000` emit white noise on load | Unfused `weight_g`/`weight_v` saved by `accelerator.save_state`; only fused at step 5000 via `remove_weight_norm()` | Confirmed, and this isn't really a "bug" — it's expected PyTorch weight-norm reparameterization behavior during training. The gap is that your pipeline has no step that produces a **fused, inference-ready export** at intermediate checkpoints, which is why Phase 9.7's "periodic audio QA" DoD item was never actually achievable. Fix in §4. |
| 6 | **NEW** — Numbers 1, 2, 5 fail; 3, 4 succeed | *(not previously identified)* | See §3 below — this maps almost exactly onto which words use newly-added (cold-start) tokenizer characters. |
| 7 | **NEW** — `iyorin`'s nasal coda missing | *(not previously identified as a data issue)* | Your own `plan.md` §2.4 already flagged the "iyori → iyorin" liaison as an undecided question. If the canonical written form never marks nasalization, there is no textual signal for the model to learn from — this is a transcription-convention decision, not a model defect. Resolve it once, in the numeral spellout module, independent of retraining. |

---

## 3. New finding: cold-start tokenizer embeddings explain the numbers benchmark

Your Phase 8.1/8.2 audit (log.md) extended the Yoruba vocabulary (43 tokens) with 27 new Urhobo tokens (IDs 43–69) — `v, c, z, x, q`, combining caron/circumflex/tilde/dot-below, and precomposed diacritic vowels — all with randomly initialized embedding rows. The base Yoruba tokens (including `ẹ`, `ọ`, acute, grave) already carry pretrained acoustic associations from Meta's original training.

Cross-referencing against your numbers benchmark:

| Word | Meaning | Characters used | Contains a cold-start token? | Outcome |
|---|---|---|---|---|
| `ẹ́rha` | 3 | ẹ, r, h, a | No | Phonetically consistent |
| `ẹ́ne` | 4 | ẹ, n, e | No | Phonetically consistent |
| `ọvo` | 1 | ọ, **v**, o | Yes (`v`) | Clipped, hurried |
| `ive` | 2 | i, **v**, e | Yes (`v`) | Flat/distorted glide |
| `iyorin` | 5 | i, y, o, r, i, n | No new *character*, but nasal coda isn't written at all | Dropped nasal + swallowed tap |

The only two words that synthesized correctly are the only two built entirely from characters the base model already had converged embeddings for. This is consistent with — not separate from — root causes #1–#3: `'v'` appears 3,159 times in your training text (per the Phase 8.1 audit), so this isn't primarily a data-sparsity problem for that token. It's that the embedding never got a stable, low-noise gradient signal to converge on, because every step it received was also carrying the destabilized adversarial and duration-collapse pressure described above. This predicts something falsifiable: **`'v'`-containing words should improve quickly (within the first several hundred steps) once training is stable**, since the token isn't actually rare. If it doesn't, that would point to a separate data or initialization issue worth revisiting. Build this check into your evaluation protocol (§6).

---

## 4. Will freezing the decoder on top of checkpoint-5000 work? No.

Your existing diagram already says to freeze the decoder at *"Meta's original pre-trained Yoruba weights"* — that instinct is correct, but it's worth stating the failure mode explicitly so it doesn't get lost in implementation: **`model.decoder` at checkpoint-5000 is not Meta's original decoder.** By step 5000 it has been dragged into a bad adversarial optimum (that's the buzz). If you load `checkpoint-5000` and then call `model.decoder.requires_grad_(False)`, you are freezing the *damaged* decoder in place — permanently locking in the artifact rather than removing it.

**Required:** initialize `model.decoder` and `model.posterior_encoder` from the original `facebook/mms-tts-yor` checkpoint (or your resized-embedding checkpoint from immediately after Phase 8.2, before any Phase 9 training), never from checkpoint-3000/4000/5000.

**Open question, worth A/B testing rather than guessing:** should the *other* modules (text encoder, duration predictor, flow) warm-start from checkpoint-5000 to preserve the ~60% tone-transfer progress, or restart clean? The duration predictor specifically is flagged in your own root-cause table as having collapsed under GAN pressure, so it may have learned compensating behavior that's now mismatched to a clean decoder. Given the full decoder-frozen run costs ~25–35 minutes on a Kaggle T4, this is cheap enough to just test both:

- **Run A:** fully fresh from base checkpoint (post-Phase-8.2 resize), decoder-frozen recipe.
- **Run B:** warm-start text encoder/duration predictor/flow from checkpoint-5000, but decoder/posterior-encoder from base.

Compare both against the numbers benchmark and a handful of held-out verses before picking one. Don't assume B is strictly better just because it "keeps progress" — if the duration predictor's collapse doesn't self-correct quickly under a clean reconstruction-only loss, A is safer.

---

## 5. Revised mitigation plan

### 5.1 Freeze targets (corrected)
```python
# Load decoder + posterior encoder from the ORIGINAL base checkpoint,
# never from checkpoint-3000/4000/5000.
model.decoder.requires_grad_(False)
model.posterior_encoder.requires_grad_(False)
```

### 5.2 Remove the discriminator from the training loop entirely — not just from the loss
Freezing the decoder while a discriminator is still instantiated and stepping is wasted GPU time at best and a source of dead-gradient bugs at worst. Patch the training script (`run_vits_finetuning.py` or your fork) to skip discriminator instantiation, the discriminator optimizer, and the adversarial + feature-matching loss terms outright. Train purely on:
- Mel reconstruction loss
- KL divergence (flow)
- Duration loss

`finetune-hf-vits` does not expose a config flag for this (confirmed — no `freeze_decoder`/`freeze_discriminator` option in its config surface), so this needs a direct code change to the model-setup and loss-computation steps, not a JSON config toggle.

### 5.3 Learning rate schedule
- Per-step (not per-epoch) schedule, warmup 200 steps.
- Peak LR: start at `1e-4` rather than `2e-4` — with the decoder frozen, the trainable module is small (~10M params) and already has ~60%-correct tone transfer to build on (if warm-starting per Run B in §4); a slightly lower peak reduces the chance of re-destabilizing the duration predictor.
- Target min LR: `1e-5`, cosine decay.

### 5.4 Step budget: monitor, don't fix in advance
1,500–2,000 steps is a reasonable starting estimate, but treat it as a ceiling to check against, not a target to hit. Track dev-split (101 clips) reconstruction + duration loss every 100–200 steps and stop on plateau or the first sign of dev loss rising while train loss keeps falling. Fixed-step training is exactly what produced the runaway loss in the original run — don't repeat "train for N steps regardless of what the curves say."

### 5.5 Fix the checkpoint-export problem (so you can actually do in-training QA)
Don't call `remove_weight_norm()` on the live training model — that changes its parameterization and can break resuming. Instead, at each checkpoint save:
1. Save the raw `accelerator.save_state()` as before (for resuming).
2. Load a **separate copy** of the model from that state, call `.remove_weight_norm()` on the copy, and export it as a standalone inference checkpoint.
3. Run your fixed evaluation set (held-out verses + numbers benchmark + priority tone-ambiguous words) through the inference copy and archive the audio alongside the checkpoint.

This directly unblocks Phase 9.7's DoD item, which was previously unachievable because intermediate checkpoints emitted noise.

### 5.6 Inference-time settings
Keep your existing findings: `speaking_rate=0.85`, `noise_scale=0.33` as defaults for evaluation. Re-verify these after decoder-freezing — a stable, non-adversarial decoder may tolerate a higher `noise_scale` (closer to VITS defaults) without the jitter you were seeing before, which would also restore some of the natural variation forced fine-tuning suppressed.

---

## 6. Verification protocol (run this before declaring victory)

1. **Numbers benchmark, word-by-word**, checkpointed every ~300 steps: confirm `ọvo`, `ive`, `iyorin` (the cold-start-token words) converge to natural durations and clean glides within the run, not just `ẹrha`/`ẹne`. If they lag well behind, that's evidence the cold-start-embedding hypothesis needs more than just stable training (e.g., a short targeted warm-up on high-frequency cold-start-token words before the main run).
2. **`iyorin` nasal coda**: this is a data decision, not a training outcome — resolve in `urhobo_numerals.py` per plan.md §2.4 (either mark nasalization explicitly in the canonical spelling, or explicitly document that it's phonetic-only and out of scope) before judging the model on it again.
3. **Held-out verse set**: confirm reconstruction quality and pacing on Phase 5's `dev.jsonl`/`test.jsonl` splits, which were never touched by tone-supervision injection — this is your cleanest apples-to-apples comparison against the original 5,000-step run.
4. **A/B checkpoint-5000 warm-start vs. fresh restart** (§4) on the above two checks before committing to one lineage.
5. **Sentence-level listening pass**, explicitly scoped to segmental quality (clarity, pacing, no swallowed syllables) — not overall melodic naturalness. Full-sentence intonation is out of scope for this fix; see §7.

---

## 7. What this fix will not solve

Your plan already scopes tone modeling to the **word level only** (`plan.md` §1.3, §6.3) and explicitly defers phrase-level downstep/declination to a hypothetical v2 with a recording budget (`plan.md` Phase 13). Decoder-freezing addresses segmental quality — buzz, phoneme skipping, duration collapse — which is most of what's "totally unusable" right now. It does not add phrase-level melodic contour modeling. After this fix, expect isolated words and short corpus-derived carrier phrases (your actual v1 content scope, per §1.3) to sound substantially better; don't expect full connected-speech "tune" to match the source recording's natural downstep until a deliberate v2 prosody pass.