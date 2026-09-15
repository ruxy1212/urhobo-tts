#!/usr/bin/env python3
"""
scripts/14_prepare_urhobo_tokenizer.py
Phase 8: Step 8.2 - Urhobo Tokenizer Extension & VITS Embedding Preparation

This script:
1. Loads the base Yoruba tokenizer files from `models/base_mms_yor/` (43 tokens).
2. Expands the vocabulary to 70 tokens by adding:
   - Missing Urhobo Latin letters: 'v', 'c', 'z', 'x', 'q'
   - Combining tone & phonetic diacritics: combining caron \u030C, combining circumflex \u0302,
     combining tilde \u0303, combining dot below \u0323
   - Precomposed tone & nasal vowels:
     - Rising tone (caron): ǎ, ě, ǐ, ǒ, ǔ
     - Falling tone (circumflex): â, ê, î, ô, û
     - Nasal tildes: ã, ẽ, ĩ, õ, ũ
   - Orthographic apostrophe variants: ’, ‘, ʼ
3. Preserves all 43 original Yoruba token IDs (0 to 42) exactly, ensuring zero disruption
   to pretrained Yoruba acoustic weights.
4. Generates complete HuggingFace-compatible tokenizer files in `models/urhobo_tokenizer/`:
   - vocab.json
   - tokenizer_config.json (language='urh')
   - special_tokens_map.json
   - config.json (vocab_size=70)
5. Implements the VITS embedding resizing utility `resize_vits_embeddings(model, new_vocab_size)`:
   - Safely resizes `model.text_encoder.embed_tokens`
   - Retains pretrained rows [0:43]
   - Smoothly initializes rows [43:70] with normal distribution (std = initializer_range = 0.02)
6. Verifies tokenization across critical Urhobo phrases and writes an audit summary to
   `models/tokenizer_extension_summary.json`.
"""

import os
import sys
import json
import unicodedata
from pathlib import Path

# Reconfigure console stdout for UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BASE_MMS_DIR = PROJECT_ROOT / "models" / "base_mms_yor"
OUTPUT_DIR = PROJECT_ROOT / "models" / "urhobo_tokenizer"
SUMMARY_PATH = PROJECT_ROOT / "models" / "tokenizer_extension_summary.json"

# 27 Targeted extension tokens for complete Urhobo phonetic & orthographic fidelity
URHOBO_EXTENSION_TOKENS = [
    # 1. Missing Latin consonants
    "v",  # U+0076 (LATIN SMALL LETTER V) - Essential Urhobo consonant (3,159 occurrences in train)
    "c",  # U+0063 (LATIN SMALL LETTER C) - Digraph 'ch' (252 occurrences)
    "z",  # U+007A (LATIN SMALL LETTER Z) - Biblical names / loanwords (189 occurrences)
    "x",  # U+0078 (LATIN SMALL LETTER X) - Lexicon / loanwords
    "q",  # U+0071 (LATIN SMALL LETTER Q) - Full alphabet completeness

    # 2. Combining diacritics (for decomposed Unicode / NFD text)
    "\u030c",  # COMBINING CARON (Rising tone mark)
    "\u0302",  # COMBINING CIRCUMFLEX ACCENT (Falling tone mark)
    "\u0303",  # COMBINING TILDE (Nasalization mark)
    "\u0323",  # COMBINING DOT BELOW (Open vowels ẹ / ọ decomposed)

    # 3. Precomposed Rising Tone vowels (Caron, NFC)
    "ǎ",  # U+01CE (LATIN SMALL LETTER A WITH CARON)
    "ě",  # U+011B (LATIN SMALL LETTER E WITH CARON)
    "ǐ",  # U+01D0 (LATIN SMALL LETTER I WITH CARON)
    "ǒ",  # U+01D2 (LATIN SMALL LETTER O WITH CARON)
    "ǔ",  # U+01D4 (LATIN SMALL LETTER U WITH CARON)

    # 4. Precomposed Falling Tone vowels (Circumflex, NFC)
    "â",  # U+00E2 (LATIN SMALL LETTER A WITH CIRCUMFLEX)
    "ê",  # U+00EA (LATIN SMALL LETTER E WITH CIRCUMFLEX)
    "î",  # U+00EE (LATIN SMALL LETTER I WITH CIRCUMFLEX)
    "ô",  # U+00F4 (LATIN SMALL LETTER O WITH CIRCUMFLEX)
    "û",  # U+00FB (LATIN SMALL LETTER U WITH CIRCUMFLEX)

    # 5. Precomposed Nasal vowels (Tilde, NFC)
    "ã",  # U+00E3 (LATIN SMALL LETTER A WITH TILDE)
    "ẽ",  # U+1EBD (LATIN SMALL LETTER E WITH TILDE)
    "ĩ",  # U+0129 (LATIN SMALL LETTER I WITH TILDE)
    "õ",  # U+00F5 (LATIN SMALL LETTER O WITH TILDE)
    "ũ",  # U+0169 (LATIN SMALL LETTER U WITH TILDE)

    # 6. Apostrophe variants
    "’",  # U+2019 (RIGHT SINGLE QUOTATION MARK / CURLY APOSTROPHE)
    "‘",  # U+2018 (LEFT SINGLE QUOTATION MARK)
    "ʼ",  # U+02BC (MODIFIER LETTER APOSTROPHE)
]


def load_base_files():
    """Load cached base Yoruba tokenizer and config files."""
    vocab_file = BASE_MMS_DIR / "vocab.json"
    config_file = BASE_MMS_DIR / "config.json"
    tok_config_file = BASE_MMS_DIR / "tokenizer_config.json"
    spec_tokens_file = BASE_MMS_DIR / "special_tokens_map.json"

    if not vocab_file.exists():
        raise FileNotFoundError(
            f"Base vocab file not found at {vocab_file}. Please run scripts/13_audit_character_coverage.py first."
        )

    with open(vocab_file, "r", encoding="utf-8") as f:
        base_vocab = json.load(f)
    with open(config_file, "r", encoding="utf-8") as f:
        base_config = json.load(f)
    with open(tok_config_file, "r", encoding="utf-8") as f:
        base_tok_config = json.load(f)
    with open(spec_tokens_file, "r", encoding="utf-8") as f:
        base_spec_tokens = json.load(f)

    return base_vocab, base_config, base_tok_config, base_spec_tokens


def build_urhobo_vocabulary(base_vocab: dict):
    """
    Build extended Urhobo vocabulary dictionary.
    Guarantees:
    - Base Yoruba tokens 0..42 remain unchanged in index.
    - New Urhobo tokens are appended starting at index 43.
    """
    extended_vocab = dict(base_vocab)
    next_index = max(base_vocab.values()) + 1
    added_tokens = []

    for token in URHOBO_EXTENSION_TOKENS:
        if token not in extended_vocab:
            extended_vocab[token] = next_index
            added_tokens.append({
                "token": token,
                "id": next_index,
                "codepoint": f"U+{ord(token):04X}",
                "name": unicodedata.name(token, "UNKNOWN")
            })
            next_index += 1

    return extended_vocab, added_tokens


def simulate_tokenize(text: str, vocab: dict, add_blank: bool = True, pad_token: str = "|"):
    """
    Exact simulation of Hugging Face VitsTokenizer encoding:
    1. Lowercase text.
    2. Filter out characters not in vocab (strip unsupported chars).
    3. Interleave pad_token ('|') if add_blank is True.
    4. Map tokens to IDs.
    """
    text_lower = text.lower()
    filtered = "".join([c for c in text_lower if c in vocab])
    tokens = list(filtered)

    if add_blank:
        interspersed = [pad_token] * (len(tokens) * 2 + 1)
        interspersed[1::2] = tokens
        token_strings = interspersed
    else:
        token_strings = tokens

    token_ids = [vocab.get(tok, vocab.get(pad_token, 0)) for tok in token_strings]
    return {
        "raw_text": text,
        "filtered_text": filtered,
        "tokens": token_strings,
        "input_ids": token_ids,
        "dropped_chars": [c for c in text_lower if c not in vocab and c != " " and not unicodedata.category(c).startswith(("P", "S"))]
    }


def resize_vits_embeddings(model, new_vocab_size: int = 70, pad_token_id: int = 0):
    """
    Standalone embedding resizing logic for VitsModel in PyTorch.
    Can be imported and executed directly in Kaggle/training scripts.

    Resizes model.text_encoder.embed_tokens from old_vocab_size to new_vocab_size:
    1. Preserves pretrained Yoruba rows [0:old_vocab_size]
    2. Initializes new rows [old_vocab_size:new_vocab_size] from normal distribution
       with mean 0.0 and std = config.initializer_range.
    3. Updates model.config.vocab_size.
    """
    try:
        import torch
        import torch.nn as nn
    except ImportError:
        print("  [Note] PyTorch not installed locally. Generating function definition for training pipeline.")
        return None

    old_embeddings = model.text_encoder.embed_tokens
    old_num_tokens, embedding_dim = old_embeddings.weight.shape

    if old_num_tokens == new_vocab_size:
        return model

    new_embeddings = nn.Embedding(new_vocab_size, embedding_dim, padding_idx=pad_token_id)
    
    # Initialize with normal distribution matching VITS config
    init_std = getattr(model.config, "initializer_range", 0.02)
    nn.init.normal_(new_embeddings.weight, mean=0.0, std=init_std)

    # Copy over existing weights
    with torch.no_grad():
        copy_size = min(old_num_tokens, new_vocab_size)
        new_embeddings.weight[:copy_size, :] = old_embeddings.weight[:copy_size, :]

    model.text_encoder.embed_tokens = new_embeddings
    model.config.vocab_size = new_vocab_size

    # Attach helper methods to model instance so HF transformers methods don't fail
    model.get_input_embeddings = lambda: model.text_encoder.embed_tokens
    model.set_input_embeddings = lambda new_emb: setattr(model.text_encoder, "embed_tokens", new_emb)

    return model


def prepare_urhobo_tokenizer():
    print("=" * 70)
    print("Phase 8 Step 8.2: Urhobo Tokenizer Extension & VITS Embedding Prep")
    print("=" * 70)

    # 1. Load base Yoruba files
    print("\n1. Loading base Yoruba model files...")
    base_vocab, base_config, base_tok_config, base_spec_tokens = load_base_files()
    print(f"  Base vocabulary size: {len(base_vocab)} tokens")

    # 2. Build extended vocabulary
    print("\n2. Expanding vocabulary with Urhobo phonemes and tone diacritics...")
    urhobo_vocab, added_tokens = build_urhobo_vocabulary(base_vocab)
    print(f"  Added tokens:         {len(added_tokens)} tokens")
    print(f"  Extended vocab size:  {len(urhobo_vocab)} tokens")

    # 3. Create updated config objects
    urhobo_tok_config = dict(base_tok_config)
    urhobo_tok_config["language"] = "urh"
    urhobo_tok_config["tokenizer_class"] = "VitsTokenizer"

    urhobo_config = dict(base_config)
    urhobo_config["vocab_size"] = len(urhobo_vocab)

    # 4. Save tokenizer artifacts to models/urhobo_tokenizer/
    print(f"\n3. Saving extended tokenizer to {OUTPUT_DIR.relative_to(PROJECT_ROOT)}...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_DIR / "vocab.json", "w", encoding="utf-8") as f:
        json.dump(urhobo_vocab, f, indent=2, ensure_ascii=False)
    print(f"  [Saved] vocab.json ({len(urhobo_vocab)} tokens)")

    with open(OUTPUT_DIR / "tokenizer_config.json", "w", encoding="utf-8") as f:
        json.dump(urhobo_tok_config, f, indent=2, ensure_ascii=False)
    print(f"  [Saved] tokenizer_config.json (language='urh')")

    with open(OUTPUT_DIR / "special_tokens_map.json", "w", encoding="utf-8") as f:
        json.dump(base_spec_tokens, f, indent=2, ensure_ascii=False)
    print(f"  [Saved] special_tokens_map.json")

    with open(OUTPUT_DIR / "config.json", "w", encoding="utf-8") as f:
        json.dump(urhobo_config, f, indent=2, ensure_ascii=False)
    print(f"  [Saved] config.json (vocab_size={len(urhobo_vocab)})")

    # 5. Verification tests
    print("\n4. Verifying tokenization on representative Urhobo sentences...")
    test_sentences = [
        ("Avwanre vwo ẹgba vwọ kẹ Osolobrugwẹ.", "All 'v' letters preserved"),
        ("Mẹ́vwẹ yen rha cha.", "Acute tone on ẹ + 'v' + 'ch' digraph preserved"),
        ("Ọmọ na da rhe vwo ẹghwẹ.", "Underdot vowels 'ọ', 'ẹ' + 'v' preserved"),
        ("Zebulun vẹ Naftali rha re.", "Consonant 'z' and 'v' preserved"),
        ("ọ̌mǒ vẹ âkpô", "Rising (caron) and falling (circumflex) tones preserved"),
        ("mẹ’vwẹ kẹ wẹʼ", "Apostrophe variants preserved"),
    ]

    verification_results = []
    all_passed = True

    for sent, desc in test_sentences:
        base_sim = simulate_tokenize(sent, base_vocab)
        urh_sim = simulate_tokenize(sent, urhobo_vocab)

        dropped_in_base = base_sim["dropped_chars"]
        dropped_in_urh = urh_sim["dropped_chars"]

        passed = len(dropped_in_urh) == 0
        if not passed:
            all_passed = False

        status = "PASSED" if passed else "FAILED"
        print(f"  [{status}] {desc}")
        print(f"    Input:       \"{sent}\"")
        print(f"    Base Yor:    \"{base_sim['filtered_text']}\" (Dropped: {dropped_in_base})")
        print(f"    Urhobo:      \"{urh_sim['filtered_text']}\" (Dropped: {dropped_in_urh})")
        print(f"    Token IDs:   {urh_sim['input_ids'][:12]}... (total {len(urh_sim['input_ids'])} IDs)")
        print()

        verification_results.append({
            "input": sent,
            "description": desc,
            "base_filtered": base_sim["filtered_text"],
            "base_dropped": dropped_in_base,
            "urhobo_filtered": urh_sim["filtered_text"],
            "urhobo_dropped": dropped_in_urh,
            "urhobo_token_ids_preview": urh_sim["input_ids"][:12],
            "passed": passed
        })

    # 6. Check full training manifest coverage
    print("5. Verifying 100% token preservation across data/processed/train.jsonl...")
    train_path = PROJECT_ROOT / "data" / "processed" / "train.jsonl"
    total_train_verses = 0
    total_dropped_train = 0
    dropped_sample = set()

    with open(train_path, "r", encoding="utf-8") as f:
        for line in f:
            total_train_verses += 1
            text = json.loads(line)["text"]
            sim = simulate_tokenize(text, urhobo_vocab)
            if sim["dropped_chars"]:
                total_dropped_train += 1
                dropped_sample.update(sim["dropped_chars"])

    print(f"  Total verses checked: {total_train_verses:,}")
    print(f"  Verses with dropped phonetic/letter characters: {total_dropped_train}")
    if total_dropped_train > 0:
        print(f"  Dropped characters: {dropped_sample}")
    else:
        print("  [PERFECT] 100% of alphabetic and tonal characters preserved across the entire training corpus!")

    # 7. Write comprehensive summary report
    summary_report = {
        "status": "success" if all_passed and total_dropped_train == 0 else "warning",
        "base_vocab_size": len(base_vocab),
        "extended_vocab_size": len(urhobo_vocab),
        "total_new_tokens": len(added_tokens),
        "new_tokens": added_tokens,
        "token_ranges": {
            "pretrained_yoruba_tokens": "0 to 42 (43 tokens, weight frozen/reused)",
            "urhobo_extension_tokens": f"43 to {len(urhobo_vocab) - 1} ({len(added_tokens)} tokens, newly initialized)"
        },
        "embedding_resizing_spec": {
            "source_shape": [len(base_vocab), base_config.get("hidden_size", 192)],
            "target_shape": [len(urhobo_vocab), base_config.get("hidden_size", 192)],
            "initialization": "nn.init.normal_(weight, mean=0.0, std=0.02) for rows [43:70]",
            "pad_token_id": 0,
            "pad_token": "|"
        },
        "verification_suite": {
            "all_passed": all_passed,
            "train_corpus_perfect_coverage": total_dropped_train == 0,
            "sample_tests": verification_results
        }
    }

    with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump(summary_report, f, indent=2, ensure_ascii=False)

    print(f"\n[Done] Extension summary report written to: {SUMMARY_PATH.relative_to(PROJECT_ROOT)}")
    print("=" * 70)


if __name__ == "__main__":
    prepare_urhobo_tokenizer()
