# Urhobo TTS Engine — Build & Engineering Log

A development diary tracking the high-level milestones, technical breakthroughs, and architectural decisions in creating an authentic, tone-accurate Text-to-Speech (TTS) engine and curriculum audio for the Urhobo language.

---

### Phase 0: Architecture, Constraints & Environment Foundations
* **Tone-Aware Base Model Selection**: Chose Meta's MMS Yoruba checkpoint (`facebook/mms-tts-yor`, VITS architecture) as our foundation. Yoruba orthography natively marks tones using acute (´) and grave (`) diacritics that closely match Urhobo's tonal system, giving the acoustic model a massive phonetic head start compared to generic multilingual models.
* **Democratizing Compute on Kaggle Free Tier**: Deliberately constrained our heavy compute pipeline to Kaggle Notebooks free tier (T4 / P100 GPUs, ~30 hrs/week). By decoupling data prep (CPU) from fine-tuning and forced alignment (GPU), we engineered the pipeline to build a production-grade language engine with zero cloud spend.
* **Dual Licensing Gates Documented**: Established transparent non-commercial compliance boundaries for both the Meta MMS base checkpoint (CC-BY-NC-4.0) and the Bible Society of Nigeria (BSN UBV77) source content.
* **Scaffolded Portable Pipeline**: Set up clean repository modularity (`data/`, `scripts/`, `models/`, `app_content/`), pinned exact versions for `ctc-forced-aligner` and `finetune-hf-vits`, and connected direct GitHub-to-Kaggle syncing.

---

### Phase 1: Source Data Acquisition & Corpus Engineering
* **Dissecting the Audio-Text Source (Bible.com UBV77)**: Analyzed the Old Testament Urhobo Bible recording. Confirmed that audio streams provide continuous chapter-level recordings with zero verse-level timing metadata. This proved that building a custom CTC forced-alignment pipeline (Phase 4) was essential for generating clean, verse-level training pairs.
* **Engineered a Resilient Scraping & Ingestion Engine**:
  * Developed `scripts/01_scrape_text.py` to extract both the direct 32k CDN MP3 streams and chapter HTML.
  * Overcame local DNS timeouts and bot protection by configuring dynamic Fastly CDN routing fallbacks.
  * Implemented precision DOM parsing that strips verse label numbers from actual spoken text while strictly preserving Urhobo diacritics (ẹ, ọ, etc.).
  * Automated extraction of un-numbered narrative headings (e.g., Genesis 2 *"Udju rẹ Idẹn"* / Garden of Eden) to enable asterisk wildcard alignment handling during audio segmentation.
* **Genesis Corpus Acquisition Completed**: Successfully extracted and verified the complete Book of Genesis (all 50 chapters, 1,533 verses, ~59 MB / ~3.5 hours of speech) with 100% diacritic fidelity and mid-chapter narrative headings captured, establishing the primary grounded speech-text corpus for forced alignment and model training.
