# Urhobo TTS Engine — Build Plan

**Scope:** produce a fine-tuned, correctly-toned Urhobo text-to-speech engine from Bible audio + text, plus the supporting tone lexicon and app-integration layer for a Duolingo-style v1. No audio recording budget, no user speech input in v1, no live inference in v1 — everything ships as pre-rendered, human-QA'd audio.

**Compute:** **Kaggle Notebooks free tier only.** No Colab, no GitHub Codespaces GPU (Codespaces dropped GPU machine types in 2025 and shouldn't be planned around), no paid cloud. This is a deliberate constraint, not a fallback — see "Effort & Compute Budget" below for why it's sufficient.

**How to use this document:** phases are ordered by dependency, not by priority — you cannot skip ahead. Each phase has numbered steps and a "Definition of Done" (DoD) checklist. Steps marked **[VERIFY]** are things that must be checked empirically before building on top of them — treat these as spikes, not assumptions.

---

## Effort & Compute Budget

Read this before starting. The GPU is not the bottleneck in this project — the lexicon and tone-verification work is.

| Phase group | Focused human hours | GPU hours needed | Runs on |
|---|---|---|---|
| 0–1 Setup & data acquisition | 10 | 0 | Local or Kaggle CPU |
| 2 Text normalization & numerals | 12 | 0 | Local or Kaggle CPU |
| 3 Audio preparation | 4 | 0 | Local or Kaggle CPU |
| 4 Forced alignment | 8 | 0–3 | Kaggle CPU (slow) or short Kaggle GPU session |
| 5 Segmentation & dataset assembly | 6 | 0 | Local or Kaggle CPU |
| 6 Tone lexicon construction | 20 | 0 | Local (LLM API calls, no GPU) |
| 7 Tone-to-audio supervision bridge | 25 | 0 | Local (listening, review) |
| 8 Base model & tokenizer prep | 3 | 0 | Local or Kaggle CPU |
| 9 Fine-tuning | 8 | 10–15 | **Kaggle GPU** |
| 10 Evaluation & QA | 7 | 0–1 | Kaggle GPU (inference only, cheap) |
| 11 Pre-render & mobile packaging | 7 | 0–1 | Kaggle GPU (inference only, cheap) |
| 12 App feature integration | 15 | 0 | Local (Android project) |
| **Total** | **~125 hrs** | **~10–20 GPU hrs** | |

**Why Kaggle alone is enough:** Phases 6–7 (lexicon + tone-audio grounding) account for over a third of the total effort and need zero GPU — they're reading, prompting an LLM, and listening to short clips. The only phase that hard-requires a GPU is fine-tuning (Phase 9), and `ylacombe/finetune-hf-vits` (the repo this plan uses) is designed to produce a usable VITS/MMS fine-tune from a small, well-formatted sample set in a short training run once your data is correctly formatted — the compute itself is cheap, the data prep is what's expensive. Kaggle's published free quota (~30 GPU-hours/week, P100 or dual T4, sessions capped around 9–12 hours) comfortably covers Phases 4, 9, 10, and 11 combined, including pilot-run mistakes and re-runs, inside a single week's quota if needed — you will not need to buy compute for v1.

**Calendar time:** ~125 focused hours works out to 10–13 weeks at 10–12 hrs/week (realistic for a side project), or 5–6 weeks at 20–25 hrs/week. Treat the lexicon/dictionary-quality unknowns in Phase 6 as the main source of schedule risk, not the model training.

---

## Phase 0 — Foundations, Decisions, Environment

### 0.1 Locked decisions (from prior discussion & updates)
- Base stack: Meta's MMS Yoruba checkpoint (`facebook/mms-tts-yor`, VITS architecture), fine-tuned via `ylacombe/finetune-hf-vits`. Yoruba is specifically selected because its orthography natively marks tones with acute (`´`) and grave (`` ` ``) diacritics matching Urhobo's tone system.
- Answer-checking for English→Urhobo exercises: normalized edit-distance matching against an accepted-answers list, not embedding similarity.
- Tone disambiguation: build a canonical tone-marked lexicon via LLM-assisted extraction from your dictionary PDFs (Phase 6), then bridge it to real audio (Phase 7).
- Aligner tool: `ctc-forced-aligner` PyPI package (PyTorch `torchaudio.pipelines.MMS_FA` is deprecated starting v2.8).
- **Compute platform: Kaggle Notebooks free tier, exclusively.** No other GPU environment is assumed anywhere in this plan.
- **Content scoping: stories and conversations in v1 are constrained to sentences drawn from, or closely adapted from, the aligned Bible corpus text** (see 1.3). This is a new decision versus the original plan and exists specifically because Phase 6.3 scopes tone modeling to word-level only, with no phrase-level downstep — free-authored sentences risk sounding flat or wrongly stressed, while corpus-matched sentences stay inside the same listen-and-approve QA loop used for isolated vocabulary.

### 0.2 Licensing — two independent gates, document both now, decide later
- **Gate 1 — Model license:** `facebook/mms-tts-yor` (and the whole MMS-TTS family) is licensed **CC-BY-NC-4.0** — non-commercial. The MMS forced-alignment model inherits the same restriction. Any model you fine-tune from this checkpoint inherits it too.
- **Gate 2 — Source content license [VERIFY]:** the Urhobo Old Testament recording and text (UBV77 / Bible Society of Nigeria) has its own, separate copyright and distribution terms, independent of the MMS license. This was not checked in the original plan. Before shipping anything derived from this audio — including synthetic speech trained on it — confirm what BSN's terms actually allow (research/non-commercial use, redistribution of derived audio, etc.). This gates commercial release just as hard as Gate 1 does, and fixing Gate 1 alone (e.g. training your own model from scratch later) does not automatically clear Gate 2.
- **Action:** record in your project README, before you ship anything, whether v1 will be free/non-commercial (both gates are non-blocking) or monetized in any way (both gates need resolving — either a from-scratch-trained model on cleared data, or explicit agreements with Meta and BSN).

### 0.3 Environment
- Python ≥3.10, `git`, `ffmpeg` (audio conversion). No local GPU required — see the compute budget above for exactly which phases need one.
- Core packages: `torch`, `torchaudio`, `transformers`, `datasets`, `ctc-forced-aligner`, `uroman`, `num2words` (for non-Urhobo digit fallback only — see 2.4), `pdfplumber` or `PyMuPDF` (dictionary PDF text extraction), `pytesseract` (OCR fallback for scanned PDFs), `noisereduce`, `librosa`, `soundfile`.
- **[VERIFY] Dependency friction:** `ctc-forced-aligner` and its underlying stack are commonly reported to be fiddly to install (compiled dependencies, `torch`/`torchaudio` version sensitivity). Budget a buffer session for Phase 4 environment setup specifically, separate from the alignment work itself — don't let a pip install spiral eat into your Kaggle GPU quota.
- **[VERIFY] `ylacombe/finetune-hf-vits` maintenance:** this is a small, lightly-maintained repository. It works, but pin exact `transformers`/`torch`/`datasets` versions in your `requirements.txt` rather than installing latest, and expect to patch a version mismatch or two rather than a broken pipeline.
- **Kaggle account setup (do this in Phase 0, not Phase 9):** verify your phone number on Kaggle now — GPU accelerators and internet access inside notebooks both require phone verification, and this can take a day to process. Enable "Internet on" in notebook settings before you need to `pip install` anything mid-session.

### 0.4 Repository layout (create this structure now)
```
urhobo-tts/
  data/
    raw/audio/           # downloaded chapter-level MP3s
    raw/text/            # raw scraped/copied verse text per chapter
    raw/dictionaries/     # source PDFs, unmodified
    interim/wav/          # converted chapter-level WAV
    interim/alignments/   # per-chapter alignment JSON output
    processed/segments/   # final (audio_clip, text) training pairs
    lexicon/               # tone lexicon artifacts (Phase 6/7)
  scripts/
    01_scrape_text.py
    02_convert_audio.py
    03_align.py
    04_segment.py
    05_build_dataset.py
    06_extract_lexicon.py
    07_tone_audio_bridge.py
    08_finetune.py
    09_evaluate.py
    10_render_curriculum.py
    11_compress_and_package.py
  models/
    checkpoints/
  app_content/
    curriculum_vocab.tsv
    prerendered_audio/
  README.md
```
- Push this repo to GitHub. Kaggle Notebooks can clone directly from a GitHub repo at session start, which is how you avoid re-uploading code every session and how you keep your pipeline portable if you ever do need to move off Kaggle later.

### DoD for Phase 0
- [x] Repo scaffolded as above and pushed to GitHub.
- [x] Both licensing gates (0.2) documented in README, even if "TBD — free for now."
- [x] `ctc-forced-aligner` pinned in `requirements.txt`, along with pinned `transformers`/`torch`/`datasets` versions for `finetune-hf-vits`.
- [x] Kaggle account phone-verified; GPU and internet access confirmed working in a throwaway test notebook.

---

## Phase 1 — Source Data Acquisition

### 1.1 Bible audio + text
- Primary audio source: Old Testament Urhobo Bible recording (UBV77 / BSN). The Old Testament recording provides clean speech with **no background ambient music/sound**, providing pristine acoustic quality.
- **Corpus Size vs. Fine-Tuning Data Need:** The full Old Testament audio provides ~60 hours of text-to-speech alignment. While 60 hours maximizes natural word coverage when searching for curriculum terms (Phase 7), **fine-tuning VITS requires only 5–10 hours of high-confidence, clean speech clips**. Having the full 60 hours allows filtering for only the highest-scoring alignment clips during Phase 5.
- **[VERIFIED] Acquisition mechanics and a hard constraint:** each bible.com chapter page (e.g. `bible.com/bible/2616/GEN.2.UBV77`) embeds a direct CDN link to a single continuous MP3 for the whole chapter (pattern: `https://audio-bible-cdn.youversionapi.com/{id}/32k/{BOOK}/{chapter}-{hash}.mp3?version_id=2616`) — visible in the page's rendered HTML without needing to reverse-engineer an API. **There is no verse-level timing metadata anywhere on the page or in the audio file** — no chapter markers, no per-verse split, no highlight-sync manifest. This isn't a gap to search harder for; it confirms the premise of Phase 4 (forced alignment) is necessary, not optional. Fetch each chapter's page, extract this MP3 URL, and download — this is the acquisition method, not scraping rendered audio some other way.
- For each book and chapter: record book code, chapter number, audio file location, and transcript text file location.
- Check the source content license here (Phase 0.2, Gate 2) before investing further time — this is cheap to check now and expensive to discover late.

### 1.2 Dictionaries and reference texts
- Archive every dictionary PDF and the encyclopedia you found via Niger-Volta-LTI / omniglot / Wikipedia's Urhobo bibliography (Ukere 1986, Ebireri Okrokoto, Julius Arerierian, Akpobọmẹ Diffrẹ-Odiete's wordlist) into `data/raw/dictionaries/`. Keep each as a separate, clearly-named file — you'll need per-source provenance in Phase 6.
- Note which of these are born-digital (text extractable directly) vs. scanned images (need OCR).

### 1.3 Curriculum vocabulary seed list
- Before touching audio, write a plain-text list of every word/phrase your v1 curriculum will actually need: alphabet items, numbers 1–100 (at minimum), greetings, common objects for the naming feature, and set phrases for the story/conversation module. This list drives prioritization in every later phase — you are not trying to cover the whole language, you're trying to cover this list correctly.
- **New constraint for stories & conversations specifically:** unlike isolated vocabulary (alphabet, numbers, greetings, objects), full sentences need sentence-level prosody that this plan explicitly does not model (Phase 6.3 skips phrase-level downstep). To keep sentence-level content inside the same closed, QA'able set as everything else, **author your story and conversation content by selecting or lightly adapting sentences that already exist in the aligned Bible corpus**, rather than writing new Urhobo sentences freely and hoping the model generalizes to them. This is more constraining than a typical curriculum design process, but it converts "does this sentence sound natural?" from a model-quality gamble into the same listen-and-approve check you're already doing for words. Revisit this constraint in v2 if you later add a native-speaker recording budget for downstep coverage.

### DoD for Phase 1
- [x] Audio+text source decided and archived locally.
- [x] Both licensing gates checked against the actual source terms (not just assumed).
- [x] All dictionary/reference PDFs archived locally with source names preserved.
- [x] Curriculum vocabulary seed list written, with story/conversation entries specifically flagged as corpus-derived or corpus-adapted (even if incomplete — it will grow).

---

## Phase 2 — Text Normalization & Verse Extraction

### 2.1 Parse verse-level text
- For each chapter, extract each verse as a separate string, preserving verse number and book/chapter/verse (BCV) ID, e.g. `GEN_001_001`.
- **[VERIFIED] Verse-number pattern on bible.com:** verse numbers are glued directly onto the start of each verse's text with **no space** (e.g. `1Kẹnẹ a ma odjuvwu vẹ akpọ... 2Vwẹ ẹdẹ rẹ ighwrẹ...`), not set off by punctuation or whitespace. Do not split on any bare number — Bible text (genealogies, ages) contains plenty of other numbers, but this project's translated text spells those out as Urhobo number words rather than digits (see 2.4), so a digit run glued directly to a following letter is, in practice, reliably a verse marker. Validate this per-source rather than assuming it holds everywhere: match candidate verse numbers, then only accept a match if it's exactly one more than the previous accepted verse number, discarding anything else. A reference implementation of this parsing plus the full align-and-segment pipeline is in `scripts/03_align_and_segment.py`.
- Preserve full original diacritics (ẹ, ọ, etc.) — do not simplify at this stage. This is your ground-truth training text.

### 2.2 Handle non-verse narration
- Chapter introductions, section headers, or spoken verse numbers in the audio that don't correspond to verse text: mark these spans for the `*` (star/wildcard) token treatment during alignment (Phase 4), following the same approach as `bookbot-hive/OpenBible-TTS`. Do not try to transcribe this narration verbatim unless you actually need it as training data — the star token tells the aligner "unknown speech here, skip it."
- **[VERIFIED] Concrete example:** Genesis 2 (UBV77) contains an unmarked section heading, "Udju rẹ Idẹn" ("Garden of Eden"), inserted between verses 7 and 8 with no verse number at all. This is a real, live instance of exactly the case this section describes — expect several of these per book, not just at chapter starts.

### 2.3 Concatenation order
- Verses must be concatenated in the exact order they're spoken in the audio, with no gaps, since Phase 4's forced alignment depends on token order matching audio order exactly. Double check for any reordering, combined verses (e.g., "16-17" spoken as one block), or skipped verses in the source, and encode these as explicit metadata rather than silently mismatching.

### 2.4 Digit / numeral spellout
- `num2words` does not support Urhobo. Write `urhobo_numerals.py`: a function mapping integers to their spoken Urhobo word form, covering at minimum 0–100 plus any larger numbers that appear in genealogies/dates in your source text (Bible text has plenty of these — Genesis alone will exercise large numbers).
- **This module is dual-purpose:** it's needed here for correctly rendering any digits in the Bible text before alignment, and it's the exact same module your app's Numbers lesson will use later (Phase 12), including for the compositional runtime-concatenation approach described in 11.1 — build it with explicit access to the tens/units/connector morphemes, not just a flat lookup table, so both uses can share it. Pay attention to the liaison detail you already noticed (e.g., "iyori" → "iyorin" in connected speech): decide explicitly whether the written spellout should include that final -n or whether it's a purely phonetic/audio phenomenon not reflected in text, and apply that decision consistently.

### DoD for Phase 2
- [x] Every chapter has a verse-ordered text file with BCV IDs.
- [x] Non-verse narration spans identified and flagged for star-token handling.
- [x] `urhobo_numerals.py` written and unit-tested against your curriculum's number list, with morphemes accessible individually (not just full-number strings).

---

## Phase 3 — Audio Preparation

### 3.1 Convert chapter-level MP3 → WAV & Audio Enhancement
- Use `ffmpeg`, mono, 16kHz sample rate (matching `facebook/mms-tts-yor` expected input). Keep original files untouched; write converted files to `data/interim/wav/`.
- Apply EBU R128 Loudness Normalization (target -23 LUFS) and an 80Hz high-pass filter to guarantee uniform audio gain across all chapters.
- Runs entirely on CPU — do this locally or in a Kaggle CPU-only notebook, no GPU quota spent.

### 3.2 Sanity checks
- Confirm chapter audio duration is plausible relative to verse count and text length (a chapter that's suspiciously short or long relative to its text is worth spot-checking before you invest alignment compute in it).

### DoD for Phase 3
- [ ] All chapter audio converted to a consistent WAV format (16kHz mono).
- [ ] Loudness normalization and high-pass filtering applied.
- [ ] Duration sanity check script run over the whole corpus, outliers flagged.

---

## Phase 4 — Forced Alignment

### 4.1 Understand what this step actually does (so Phase 2's ordering matters and pause-length does not)
- **[VERIFIED] There is no verse-level timing data available from the source, at all.** Checked directly against a live bible.com chapter page: it serves one continuous MP3 per chapter with no embedded chapter/verse markers, no timestamp manifest, and no API-exposed timing data for the "read-along" text. This is not something to keep searching for — it confirms this phase is mandatory, not a fallback for a worse-than-expected source.
- You already know verse boundaries from the text (Phase 2). The aligner's job is to find *where in the audio* each verse's tokens land, using frame-by-frame CTC probability matching — it does not detect silence or guess boundaries from pauses. A short gap between verses in one paragraph and a long gap between verses in a new paragraph are both handled identically and correctly by this method, provided your verse-ordered text is accurate.

### 4.2 Romanization for alignment only
- The MMS alignment model's output vocabulary is roughly 28 lowercase Latin letters plus an apostrophe — it does not natively handle ẹ, ọ, or other diacritics. Before alignment, romanize/strip your verse text with `uroman` (`pip install uroman`) to a simplified ASCII form **for alignment purposes only**. This does not affect your final training text: alignment gives you timestamps keyed to word/verse position, and you slice the *original, fully-diacritic* audio+text using those positions. Do not train the TTS model on the romanized text — that's a throwaway intermediate representation.

### 4.3 Run alignment per chapter
- **Compute note:** this is inference, not training — it can run on Kaggle's CPU-only kernel if you want to conserve GPU quota, just expect it to be slow over 60 hours of audio (potentially most of a day). If that's impractical, run it in a short Kaggle GPU session instead; it should take well under an hour of GPU time even for the full corpus.
- For each chapter: load WAV, load romanized verse-concatenated transcript (with star tokens inserted at narration spans from 2.2), run `ctc-forced-aligner`, obtain per-token timestamps.
- Retain **word-level** timestamps, not just verse-level — you will need word-level precision in Phase 7 to extract individual ambiguous words from the corpus.

### 4.4 Quality scoring
- Apply the length-normalized probability-difference filter from the MMS paper / OpenBible-TTS methodology: score = (alignment path probability − greedy sequence probability) normalized by audio length; use threshold −0.2 as your starting point (adjust empirically after listening to samples near the threshold on both sides).
- Tag every verse segment with its alignment confidence score. Do not discard low-confidence segments yet — flag them, and use the flag in Phase 5.

### DoD for Phase 4
- [ ] Every chapter aligned via `ctc-forced-aligner`, word-level timestamps stored per BCV ID.
- [ ] Confidence score attached to every verse.
- [ ] Spot-check: manually listen to 10–20 verses across the confidence-score range and confirm the scoring correlates with actual alignment quality before trusting it at scale.

---

## Phase 5 — Segmentation, Filtering & Dataset Assembly

### 5.1 Slice audio at verse boundaries with boundary padding
- Using the timestamps from Phase 4, cut chapter WAVs into individual verse-level audio clips.
- **Edge Click Prevention:** Add 50ms padding at segment start and end boundaries with a 10ms raised-cosine fade-in/fade-out envelope. This prevents harsh audio pops or cut-off consonant decays. Store as `data/processed/segments/{book}/{book}_{chapter}_{verse}.wav`.

### 5.2 Filter & Select Fine-Tuning Subset
- Drop or quarantine segments below your confidence threshold from 4.4.
- Drop segments where the text is empty/star-only (chapter intros with no real verse content).
- **Dataset Volume Selection:** Out of the ~60 hours of available Old Testament aligned clips, select the top **5 to 10 hours** of highest-confidence, cleanest segments for fine-tuning.

### 5.3 Build the dataset manifest
- One record per verse: `{id, book, chapter, verse, text, audio_path, duration_sec, alignment_confidence}`. Store as JSONL or a HuggingFace `datasets`-loadable format matching `ylacombe/finetune-hf-vits`'s expected input schema.

### 5.4 Train/dev/test split
- Split by book or by random verse sampling, not by re-shuffling within a chapter (avoid leaking near-duplicate adjacent verses across splits). Reserve a held-out set specifically containing verses whose text includes any word from your curriculum vocabulary seed list (Phase 1.3) — you'll want these for targeted evaluation in Phase 10. Also flag which held-out verses are candidates for the corpus-derived story/conversation content from 1.3.

### DoD for Phase 5
- [ ] Verse-level WAV clips written with 50ms boundary padding and fade-in/fade-out.
- [ ] Top 5–10 hours of high-confidence segments selected for fine-tuning.
- [ ] Dataset manifest created in the exact format the fine-tuning repo expects.
- [ ] Train/dev/test split created, with a curriculum-relevant held-out subset identified.

---

## Phase 6 — Tone-Marked Lexicon Construction (LLM-assisted)

**Goal of this phase:** produce a text-only reference lexicon mapping plain Urhobo spellings to disambiguated, tone-marked spellings and glosses. This does **not** yet fix TTS pronunciation — that's Phase 7. Keep this distinction explicit throughout; conflating the two is the most likely mistake here. This is the single largest phase in the effort budget (~20 hours) — plan for it, don't compress it.

### 6.1 Extract raw text from every dictionary source
- Born-digital PDFs: extract directly (`pdfplumber`/`PyMuPDF`).
- Scanned PDFs: OCR (`pytesseract`), then manually spot-check OCR accuracy on a sample of pages before trusting it at scale — diacritics are exactly the kind of character OCR gets wrong most often, and this corpus is full of them.

### 6.2 Document each source's own tonal notation legend
- You noted the PDFs each define their own tonal indicators, inconsistently and incompletely. Before any LLM extraction, manually read each source's front matter / notation-key section and write a small `legend_<source>.json`: which symbol represents which tone in *that specific source* (e.g., acute = high in source A, but a different mark or convention in source B). This legend is what you feed the LLM as instructions for that source — do not attempt one universal legend across sources at this stage, since they genuinely differ.

### 6.3 Define your own canonical internal tone-marking scheme
This is a project convention you are defining, independent of any single source's convention, since none of your sources agree. Use standard Africanist tone notation, applied consistently across your whole lexicon regardless of source:
| Tone | Mark | Example on "o" |
|---|---|---|
| High (H) | acute ´ | ó |
| Low (L) | grave ` | ò |
| Rising (LH) | caron ˇ | ǒ |
| Falling (HL) | circumflex ˆ | ô |
| Unmarked / undetermined | none | o |

- For v1, you can reasonably choose to skip marking downstep (a phrase-level phenomenon) and handle only word-level H/L/rising/falling — document this scope decision explicitly in the lexicon file's header so it's not ambiguous later. This is also why story/conversation content is corpus-constrained (see 1.3) rather than freely authored.

### 6.4 LLM extraction pass
- For each source, prompt an LLM with: (a) the source's raw extracted text in manageable chunks, (b) that source's legend from 6.2, (c) your canonical scheme from 6.3, (d) an explicit output schema, and (e) an explicit instruction to mark confidence and to output `null`/`low_confidence` rather than guess when the source text is ambiguous or the entry is incomplete (your sources are "a bit incomplete" — the extraction must surface that, not paper over it).
- Required output fields per entry: `plain_form`, `canonical_tone_form`, `gloss_en`, `pos`, `ipa_if_present`, `source_id`, `raw_source_line`, `confidence` (`high`/`low`).
- Process sources independently — do not merge during extraction. Merging happens next.
- This runs against an LLM API, not the fine-tuning model — no GPU quota is involved.

### 6.5 Cross-source merge and conflict flagging
- Merge entries across sources by matching `plain_form` + overlapping `gloss_en`. Where two or more sources agree (after mapping to your canonical scheme) on the tone form for the same sense, mark `agreement: true`. Where sources disagree, or only one low-confidence source has data, mark `needs_review: true`.

### 6.6 Human review pass — scoped, not exhaustive
- Review, in priority order: (1) every entry matching your curriculum vocabulary seed list (Phase 1.3) — this must reach 100% reviewed before shipping any content using it; (2) every true homograph pair (same `plain_form`, different `gloss_en`/`canonical_tone_form`) anywhere in the lexicon, since these are the highest-risk words generally; (3) everything else, opportunistically, not urgently.
- If you can recruit even one native/heritage Urhobo speaker for a short session, spend their time exclusively on category (1) and (2) — this is a small, bounded task (dozens to low hundreds of words), not a full lexicon audit.

### 6.7 Output artifact
- `data/lexicon/lexicon.tsv` (or `.jsonl`) with columns: `plain_form, canonical_tone_form, gloss_en, pos, source_ids, agreement, needs_review, reviewed`.

### DoD for Phase 6
- [ ] Per-source legends documented.
- [ ] Canonical scheme documented in the lexicon file header.
- [ ] LLM extraction run per source with confidence flags preserved (not discarded).
- [ ] 100% of curriculum-vocabulary entries and all detected homograph pairs manually reviewed.

---

## Phase 7 — Tone-to-Audio Supervision Bridge (the hard, necessary part)

### 7.1 Why this phase exists — do not skip it
A VITS/MMS-style model learns character-to-acoustics mapping only from the (text, audio) pairs it is trained on. If your canonical tone-marked characters (ó, ò, ǒ, ô) never appear anywhere in your training text, the model has no evidence for what they should sound like — the lexicon from Phase 6 is inert until it's connected to real audio. This phase makes that connection for the words that matter most, and it's the second-largest phase in the effort budget (~25 hours) — again, don't compress it.

### 7.2 Build a priority list
- From the reviewed lexicon (Phase 6.6, category 1+2), take the words that will actually be flashcards or vocabulary items in v1 — realistically dozens, not hundreds, of genuinely audio-relevant ambiguities. This is your working list for this phase. Isolated vocabulary only — story/conversation content is handled separately via the corpus-constraint in 1.3, not through this per-word priority list.

### 7.3 Find natural occurrences in your aligned corpus
- For each priority word, search the Phase 5 dataset manifest for verses containing its `plain_form`. Because Bible text is a fixed, high (archaic) register, expect many curriculum-relevant conversational words (greetings, modern object names) to have zero occurrences — track this explicitly per word.

### 7.4 Determine the actual tone spoken in each occurrence
- For each occurrence found, extract the word-level audio clip (using the word-level timestamps from Phase 4.3). Determine which tone reading is actually spoken — either by a native/heritage speaker listening and tagging, or, as a rougher first pass, by extracting the F0 (pitch) contour over the clip and comparing its shape against the H/L/rising/falling patterns in your canonical scheme. Treat F0-based tagging as a first-pass heuristic to prioritize what a human reviewer checks, not as a final source of truth — pitch extraction on short vowels in continuous speech is noisy.
- Record the determined canonical tone-marked form for that specific occurrence.

### 7.5 Handle words with zero occurrences in the corpus
For each priority word not found anywhere in Phase 7.3, choose one, in order of preference:
1. Check a second free Urhobo audio source for the same word (e.g., Global Recordings Network's Urhobo recordings, or any Urhobo-language content on YouTube/radio archives) and repeat 4.3–4.4/7.4 on it if found.
2. Recruit a native speaker for a small, bounded recording session covering only this residual word list (tens of words, minutes of audio) — a fundamentally different scope than recording your whole curriculum, and worth pursuing even if full recording isn't feasible.
3. If neither is possible before v1 ships, explicitly mark these words as "unverified pronunciation" in your content pipeline (Phase 12.6) rather than silently shipping a guess.

### 7.6 Inject into training data
- For every occurrence resolved in 7.4 or 7.5, replace the plain-form text at that specific instance (and only that instance — not every occurrence of that spelling corpus-wide, since other instances may carry the other tone reading) with its canonical tone-marked form in the training manifest. Aim for 3–5 examples per priority word, from different sentence positions, where available, for robustness.

### DoD for Phase 7
- [ ] Every priority word has a disposition: resolved-from-corpus, resolved-from-secondary-source, resolved-from-new-recording, or explicitly-marked-unverified.
- [ ] Training manifest updated with tone-marked forms at the specific resolved instances.
- [ ] No blanket find-and-replace was applied to a word's spelling corpus-wide without per-instance verification.

---

### Phase 8 — Base Model Selection & Tokenizer Preparation

### 8.1 Locked Base Checkpoint
- **Locked Base Model:** `facebook/mms-tts-yor` (Yoruba, CC-BY-NC-4.0).
- **Rationale:** Yoruba orthography natively uses acute (`´`) and grave (`` ` ``) diacritics to represent lexical tones (e.g., *ó*, *ò*). Because `mms-tts-yor` was trained on text with these exact diacritic symbols, its tokenizer and embedding layers already possess acoustic prior knowledge mapping diacritics to pitch variations. Checkpoints like Igbo or standard English do not mark tones orthographically and lack this advantage.

### 8.2 Audit character coverage
- Write a script that extracts the full set of unique Unicode characters appearing in (a) your full training corpus text (Phase 5, including Phase 7's tone-marked insertions) and (b) your lexicon file (Phase 6). Compare against `facebook/mms-tts-yor`'s vocabulary file on Hugging Face. Output an explicit list of missing characters.

### 8.3 Extend vocabulary for missing characters
- Check whether `ylacombe/finetune-hf-vits`'s data-preprocessing pipeline automatically re-builds its tokenizer/vocab fresh from your target-language training corpus. If it reuses the Yoruba tokenizer unmodified, add missing Urhobo-specific characters (such as `ẹ`, `ọ`, `ǒ`, `ô`) to the vocab file and expand the text-embedding matrix with initialized rows.

### DoD for Phase 8
- [ ] Base checkpoint confirmed (`facebook/mms-tts-yor`).
- [ ] Character coverage audit run against Yoruba tokenizer; missing characters identified.
- [ ] Vocab-extension approach confirmed and verified.
- [ ] `transformers`/`torch`/`datasets` versions pinned to match what `finetune-hf-vits` expects (0.3).

---

## Phase 9 — Fine-Tuning (Kaggle Notebooks workflow)

### 9.1 Kaggle notebook setup
- Create a new Kaggle Notebook, set the accelerator to GPU (P100 or dual T4, whichever Kaggle assigns), and confirm "Internet on" is enabled in notebook settings.
- Clone your GitHub repo (Phase 0.4) at the start of every session rather than re-uploading files by hand.
- **Persistence across sessions:** Kaggle interactive sessions do not persist local disk state between separate sessions. Save model checkpoints as notebook **output**, then commit the notebook run — this creates a versioned **Kaggle Dataset** from the output. Attach that dataset as an **input** to your next session to resume training or run inference from the latest checkpoint. Do this every session; do not rely on a single long-running session to get you through fine-tuning.

### 9.2 Session & quota budgeting
- Kaggle's free tier publishes roughly 30 GPU-hours/week, with individual sessions capped around 9–12 hours. Budget fine-tuning across 2–3 sessions within a week rather than assuming one sitting will cover it.
- Save a checkpoint at least every 30–60 minutes of training so a session timeout or disconnect never costs you more than that.

### 9.3 Format the dataset
- Convert your Phase 5/7 manifest into whatever format `ylacombe/finetune-hf-vits` expects (HF `datasets` object or local manifest).

### 9.4 Sample rate consistency
- Ensure WAV audio is 16,000 Hz mono PCM, matching `facebook/mms-tts-yor`'s config.

### 9.5 Pilot run
- Run a short training job (a few hundred steps, small data subset) purely to catch pipeline/format errors before spending real GPU quota on a full run. Do this in your first Kaggle GPU session, before committing to the full fine-tune.

### 9.6 Full fine-tuning run
- Train on the top 5–10 hours of clean, tone-augmented dataset clips from Phase 5/7. Budget ~10–15 GPU-hours total including restarts and checkpoint-resume overhead — this fits inside a single week of Kaggle's free quota, but plan for it to span 2 calendar weeks to allow for debugging and re-runs without quota pressure.

### 9.7 In-training QA
- Periodically (every N steps) render sample audio for: a fixed set of held-out verses, and your priority tone-ambiguous word list. Save these samples to the committed output alongside the checkpoint so you can listen to training progress across sessions, not just at the end.

### DoD for Phase 9
- [ ] Kaggle account phone-verified, GPU + internet access confirmed working before this phase starts.
- [ ] Checkpoint/resume workflow via Kaggle Datasets tested with a throwaway run before the real fine-tune.
- [ ] Pilot run completed without pipeline errors.
- [ ] Full fine-tune completed with loss curves and periodic audio samples logged, spread across sessions within weekly quota.
- [ ] At least one checkpoint saved that a human has listened to and approved.

---

## Phase 10 — Evaluation & QA

### 10.1 Objective closed-loop check
- Generate audio from the fine-tuned model for a held-out set of verse texts. Re-run forced alignment using `ctc-forced-aligner` between generated audio and source text. Low confidence or alignment failures highlight intelligibility defects automatically.
- Compute Mel Cepstral Distance (MCD) relative to ground-truth clips as a quantitative spectral benchmark.
- This is inference only (cheap) — run it in the same Kaggle session as the end of Phase 9, or a short follow-up session, rather than a dedicated multi-hour block.

### 10.2 Subjective listening test
- With any Urhobo speaker(s) accessible, test: (a) general intelligibility of core curriculum content, (b) priority tone-ambiguous pairs — confirm pitch distinction, (c) generalization to out-of-corpus vocabulary.

### 10.3 Pre-defined pass/fail criteria
- Require every priority tone pair to be correctly identified by at least 2 of 3 listeners before shipping.

### DoD for Phase 10
- [ ] Objective alignment and MCD score checks logged.
- [ ] Subjective listening test completed against pre-defined criteria.
- [ ] Explicit list of known-bad words compiled for Phase 12's build-gating.

---

## Phase 11 — Inference & Pronunciation-Override Architecture

### 11.1 Pre-render & compress closed vocabulary for mobile
- Your v1 curriculum content (alphabet, numbers, greetings, common objects, set phrases, corpus-constrained stories/conversations from 1.3) is a small, known set. Generate audio offline at build time, in a short Kaggle GPU session (inference is fast — minutes for the whole curriculum, not hours).
- **Mobile Compression & Asset Packaging:** Convert pre-rendered WAV files into mono **AAC (LC-AAC @ 48–64 kbps)** or **Opus** — speech doesn't need music-grade bitrate, and your source is already 16kHz. At this bitrate, expect roughly 400–500 KB per minute of audio; even a generous v1 content set (alphabet + greetings + objects + ~20 minutes of story/conversation dialogue + numbers) lands around 25–40 MB total, well inside any practical budget.
- **Numbers specifically:** don't pre-render all 101 individual number files. `urhobo_numerals.py` (2.4) already knows the compositional morpheme structure — pre-render the tens/units/connector morphemes once and concatenate at runtime (or pre-render the full set anyway, since even 101 short clips is only a few MB — either is fine, just don't treat it as 101 independent recording/QA tasks).
- **Packaging:** ship audio as an Android **App Bundle (.aab)** with **Play Feature Delivery** (an on-demand or install-time asset pack), rather than flat files in `app/src/main/assets/audio/` inside the base APK. This keeps the base install small and means adding more stories, dialects, or vocabulary later never runs into the ~100 MB APK ceiling — Play serves the asset pack separately per device. Store an index manifest (`audio_manifest.json`) inside the asset pack alongside the audio.

### 11.2 Pronunciation-override routing (for any dynamic text rendered offline/online)
- Before passing text to the TTS engine, replace ambiguous words with their resolved canonical tone-marked forms from Phase 6/7. The app UI always displays plain orthography to the learner.

### 11.3 Caching
- Cache generated audio keyed by `(text, model_version)` to avoid re-rendering.

### DoD for Phase 11
- [ ] All v1 curriculum audio pre-rendered and compressed (AAC/Opus, 48–64 kbps mono).
- [ ] Numbers rendered via the compositional morpheme approach (or explicitly decided against, with reasoning recorded).
- [ ] Pronunciation-override lookup implemented and tested.
- [ ] Audio packaged as a Play Feature Delivery asset pack (not flat base-APK assets), with `audio_manifest.json` generated.

---

## Phase 12 — App Feature Integration

Map each learning feature to its specific data/QA requirement:

### 12.1 Alphabet
- Pre-rendered AAC/Opus audio per letter/sound (Phase 11.1). Manually verify every audio file before shipping.

### 12.2 Numbers
- Audio generated via `urhobo_numerals.py` (Phase 2.4) rendered through the fine-tuned model, pre-rendered per Phase 11.1 using the compositional morpheme approach. Manually verify the morpheme set (and any full 0–100 renders you also keep) before shipping.

### 12.3 Greetings & phrases
- Pre-rendered per Phase 11.1. Flag any out-of-corpus words in a QA tracking sheet.

### 12.4 Story/conversation reading — content-authoring constraint, not just QA
- Per the decision in 1.3, story and conversation content must be drawn from or closely adapted from the aligned Bible corpus text, not freely authored. Enforce this at content-authoring time (whoever writes curriculum copy checks candidate sentences against the corpus before finalizing them), not only at the audio-QA stage — catching a bad sentence after it's already written into the curriculum is more expensive than choosing a corpus-safe one up front.
- Pre-render and spot-check per Phase 11.1 rather than running live inference in-app.

### 12.5 Object naming — treat as highest-risk, isolated-word content
- Isolated single-word content. Every object-naming word must be routed through the Phase 6/7 reviewed lexicon.
- **Build-time gate:** A script fails the content build if any object-naming vocabulary item is absent from `lexicon.tsv` with `reviewed = true`.

### 12.6 Handling "unverified pronunciation" items from Phase 7.5
- For any curriculum word lacking audio-grounded tone verification, flag internally for prioritizing in future content updates.

### 12.7 English→Urhobo answer checking (no audio engine needed)
- Implement normalized edit-distance matching: first pass strips diacritics for a lenient match (catches near-misses), second pass requires correct diacritics for full marks — mirroring Duolingo's grading. Maintain a per-item accepted-answers list.

### DoD for Phase 12
- [ ] Every content module's audio compressed and packaged into the Play Feature Delivery asset pack.
- [ ] Story/conversation content verified as corpus-derived at authoring time, not just at audio QA.
- [ ] Build-time gate implemented for object-naming content.
- [ ] Answer-checking module implemented and unit-tested.

---

## Phase 13 — V2 Roadmap Notes (other Edoid languages)

- Phases 1 and 3–5 (audio/text acquisition through dataset assembly) are reusable — re-run per Edoid language once an aligned Bible audio+text source exists.
- Phase 6/7 (tone lexicon + audio bridge) must be redone per language.
- Phase 8 (base checkpoint selection) re-evaluated per language based on tone diacritic representation in relative MMS models.
- If you later add a recording budget for downstep/phrase-level intonation, the corpus-constraint on story/conversation content (1.3, 12.4) can be relaxed — it exists specifically to work around the lack of phrase-level prosody modeling in v1.
- If Kaggle's free quota stops being sufficient as scope grows (e.g. adding a second language or a recording-based dataset), the pipeline's script-based structure (0.4) means moving to a paid GPU (RunPod, Lambda) or Colab Pro requires no rewrite — only a different accelerator.

---

## Appendix A — Resolved Key Decisions & Open Questions
1. **Audio Source:** Old Testament Urhobo Bible (UBV77 / BSN) — verified clean speech, no ambient/background music.
2. **Fine-Tuning Data Volume:** ~60 hours of OT text-audio alignment available for Phase 7 word searching; **top 5–10 hours of highest-confidence clips** selected for fine-tuning VITS.
3. **Forced Aligner Tool:** `ctc-forced-aligner` PyPI package pinned (replacing deprecated `torchaudio.pipelines.MMS_FA`).
4. **Base Checkpoint:** Locked to `facebook/mms-tts-yor` (Yoruba) due to orthographic tone diacritics (`´`, `` ` ``).
5. **Edge Artifact Prevention:** 50ms segment boundary padding with 10ms raised-cosine fade-in/fade-out.
6. **Mobile Audio Format:** Mono AAC (48–64 kbps) or Opus, packaged as a Play Feature Delivery asset pack rather than flat base-APK assets.
7. **Compute Platform:** Kaggle Notebooks free tier, exclusively — no Colab, no Codespaces GPU, no paid cloud for v1.
8. **Content Licensing:** two independent gates — the MMS model's CC-BY-NC-4.0 license, and the Bible Society of Nigeria's terms on the source recording/text — both must be checked before any commercial release.
9. **Story/Conversation Content:** constrained to corpus-derived or corpus-adapted sentences for v1, to stay within the word-level-only tone modeling scope.
10. **Numbers Packaging:** compositional morpheme concatenation preferred over 101 independently pre-rendered files.

## Appendix B — Reference Links
- Bible text/audio: `https://www.bible.com/bible/2616/GEN.1.UBV77`, `https://www.scriptureearth.org/00eng.php?iso=urh`
- Pipeline precedent: `https://github.com/bookbot-hive/OpenBible-TTS`, `https://github.com/masakhane-io/bibleTTS`
- Fine-tuning: `https://github.com/ylacombe/finetune-hf-vits`
- Base checkpoint: `https://huggingface.co/facebook/mms-tts-yor`
- Aligner tool: `ctc-forced-aligner` on PyPI
- Compute platform: `https://www.kaggle.com/code`
- Mobile packaging: `https://developer.android.com/guide/playcore/feature-delivery`
