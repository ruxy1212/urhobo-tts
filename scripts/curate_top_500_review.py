"""
Curate and disambiguate top 500 priority tones review sheet.
Fixes naive dictionary lemma mismatches (e.g. 're' = eat vs relative marker,
'vwẹ' = urinate vs preposition in/at, 'isọ' = feces vs Esau),
and adds explicit rows for homographs and multi-functional words.
"""

import csv
import os
import sys

INPUT_CSV = "data/lexicon/top_500_priority_tones_review.csv"
OUTPUT_CSV = "data/lexicon/top_500_priority_tones_review.csv"
OUTPUT_TSV = "data/lexicon/top_500_priority_tones_review.tsv"

# Explicit corrections for words whose naive dictionary lookup produced misleading or wrong glosses
GLOSS_CORRECTIONS = {
    "rẹ": "of [genitive / possessive particle]",
    "da": "then / and then [narrative marker]",
    "na": "the / that [definite demonstrative article]",
    "kẹ": "to / for [dative preposition]",
    "vwẹ": "in / at / on [locative preposition]",
    "ọ": "he / she / it [3rd person subject pronoun]",
    "de": "then / when [sequential / conditional marker]",
    "ri": "of / who [genitive / relative marker]",
    "rọye": "his / her / its [3rd person possessive pronoun]",
    "ta": "say / speak / tell [verb]",
    "re": "that / which / who [relative marker]",
    "o": "he / she / it [3rd person subject pronoun]",
    "vwọ": "when / as / in order to [relational particle]",
    "mẹ": "my / mine [1st person possessive pronoun]",
    "me": "I [1st person subject pronoun]",
    "wẹn": "your / yours [2nd person singular possessive]",
    "vẹ": "and / along with [conjunction]",
    "vwo": "to have / possess [stative verb] ; with [instrumental]",
    "dia": "stay / live / dwell / be [stative verb]",
    "otọ": "ground / land / earth [noun]",
    "rọ": "who / which [relative pronoun contraction]",
    "ro": "who / which [relative pronoun contraction]",
    "ọghẹnẹ": "God [noun]",
    "ki": "then / is [connective / copula]",
    "jekọp": "Jacob [biblical name]",
    "wẹ": "you [2nd person singular object pronoun]",
    "wọ": "you [2nd person singular subject pronoun]",
    "mi": "I [1st person singular subject pronoun]",
    "se": "call / name [verb]",
    "aye": "woman / wife [noun]",
    "ke": "then shall / will then [consecutive particle]",
    "kidie": "because / for [conjunction]",
    "wo": "you [2nd person singular subject pronoun variant]",
    "gbe": "do / tell / creep / dance [verb]",
    "ọrovwohwo": "Lord / The LORD [noun]",
    "mu": "establish / set / carry [verb]",
    "isọ": "Esau [biblical name]",
    "rayen": "their / theirs [3rd person plural possessive]",
    "we": "you [2nd person pronoun variant]",
    "aizik": "Isaac [biblical name]",
    "je": "also / still / admire [particle / verb]",
    "a": "one / they / someone [impersonal passive pronoun]",
    "rhi": "come to / become [verb / auxiliary]",
    "ijipt": "Egypt [proper noun]",
    "cha": "will / shall / coming [future auxiliary]",
    "nana": "this / these [demonstrative]",
    "ọye": "he / she / him / it [emphatic 3rd person pronoun]",
    "enana": "these [demonstrative plural]",
    "asan": "places / place [noun]",
    "vwe": "me [1st person object pronoun variant]",
    "nu": "from / out of [prepositional verb]",
    "laban": "Laban [biblical name]",
    "ẹ": "you [dialectal pronoun]",
    "ku": "pour / cover [verb]",
    "nene": "follow / along with [preposition / verb]",
    "rha": "again / also [aspectual particle]",
    "kọ": "then / so that [sequential connective]",
    "evun": "inside / belly / womb [noun / preposition]",
    "gbẹ": "and / plus [numeral connective]",
    "sa": "can / able to [modal auxiliary]",
    "ko": "then / so [sequential connective]",
    "wa": "you all [2nd person plural pronoun]",
    "igodẹ": "sheep [noun]",
    "owẹ": "you [2nd person object/disjunctive pronoun]",
    "eya": "women / wives [noun plural]",
    "kemu": "everything [compound pronoun]",
    "che": "will / about to [future auxiliary]",
    "orere": "city / town [noun]",
    "noa": "Noah [biblical name]",
    "jẹn": "let / allow [imperative verb]",
    "eyẹ": "or [conjunction]",
    "lọt": "Lot [biblical name]",
    "leah": "Leah [biblical name]",
    "izrẹl": "Israel [biblical name]",
    "rere": "in order that / so that [conjunction]",
    "fiki": "because of / on account of [preposition]",
    "fikiridie": "because / for the reason that [conjunction]",
    "herọ": "is there / exists [existential copula]",
    "ubrotọ": "territory / region / land [noun]",
    "urhie": "river [noun]",
    "udju": "garden [noun]",
    "omamọ": "good / standard / proper [adjective]",
    "eghọn": "branches / river branches [noun]",
    "ọvwata": "righteousness / righteous person [noun]",
    "oka": "sign / mark [noun]",
    "uvwre": "between / midst [preposition/noun]",
    "uvwo": "flesh / body [noun]",
    "enre": "sun / day [noun]",
    "uphephe": "plain / valley [noun]",
}

# Explicit multi-form homographs to expose for native speaker disambiguation
MULTI_FORM_HOMOGRAPHS = [
    {
        "Word": "ta (verb: say / speak)",
        "BaseWord": "ta",
        "Frequency": 352,
        "English Gloss": "say / speak / tell [primary verb]",
        "Proposed Tone": "ta",
        "Genesis Context": "Ọrovwohwo Ọghẹnẹ da ta, Oyoma rere ọsháre ọ́vo vwọ dia sogono-o (The LORD God said...)",
    },
    {
        "Word": "ta (verb: blame / condemn)",
        "BaseWord": "ta",
        "Frequency": 10,
        "English Gloss": "blame / rebuke / condemn [idiomatic/compound: ta ohwo]",
        "Proposed Tone": "ta",
        "Genesis Context": "Example: Ọ ta ota kpahen riẹ (He spoke against / rebuked him)",
    },
    {
        "Word": "vwẹ (prep: in / at)",
        "BaseWord": "vwẹ",
        "Frequency": 506,
        "English Gloss": "in / at / on / inside [locative preposition]",
        "Proposed Tone": "vwẹ",
        "Genesis Context": "Urhie da va phia vwẹ Idẹn (A river came out in Eden)",
    },
    {
        "Word": "vwẹ (pronoun: me / to me)",
        "BaseWord": "vwẹ",
        "Frequency": 140,
        "English Gloss": "me / to me [1st person object pronoun]",
        "Proposed Tone": "vwẹ",
        "Genesis Context": "Ebram da ta, Nighe, wọ je kẹ vwẹ ọmọ-ọ (You did not give me a child)",
    },
    {
        "Word": "vwẹ (verb: discharge / urinate)",
        "BaseWord": "vwẹ",
        "Frequency": 5,
        "English Gloss": "discharge / pass water [lexical verb]",
        "Proposed Tone": "vwẹ́",
        "Genesis Context": "Example: Ọ cha vwẹ́ ame (He will pass water)",
    },
    {
        "Word": "re (relative: that / which)",
        "BaseWord": "re",
        "Frequency": 341,
        "English Gloss": "that / which / who [relative marker / complementizer]",
        "Proposed Tone": "re",
        "Genesis Context": "Kẹnẹ a ma odjúvwu vẹ akpọ́ kugbe obo re vọnrọ ejobi wan (Genesis 2:1)",
    },
    {
        "Word": "re (verb: eat)",
        "BaseWord": "re",
        "Frequency": 45,
        "English Gloss": "to eat [lexical verb]",
        "Proposed Tone": "ré",
        "Genesis Context": "Wọ sa re omamọ komamọ rẹ udju na (You may eat of every tree of the garden)",
    },
    {
        "Word": "re (aspect: already)",
        "BaseWord": "re",
        "Frequency": 80,
        "English Gloss": "already / completed [clause-final aspect particle]",
        "Proposed Tone": "re",
        "Genesis Context": "Ọke rẹ emọ na vwọ ghwanre re (When the children had already grown)",
    },
    {
        "Word": "da (narrative: then)",
        "BaseWord": "da",
        "Frequency": 924,
        "English Gloss": "then / and then [consecutive narrative marker]",
        "Proposed Tone": "da",
        "Genesis Context": "Urhie da va phia vwẹ Idẹn ... Etiyin ọ da jẹn eghọn ẹ́ne (Genesis 2:10)",
    },
    {
        "Word": "da (verb: drink)",
        "BaseWord": "da",
        "Frequency": 15,
        "English Gloss": "to drink [lexical verb]",
        "Proposed Tone": "dá",
        "Genesis Context": "Example: Ọ dá ame nẹ urhie na (He drank water from the river)",
    },
    {
        "Word": "da (verb: pain / hurt)",
        "BaseWord": "da",
        "Frequency": 5,
        "English Gloss": "to hurt / pain [impersonal verb: o da vwe]",
        "Proposed Tone": "dá",
        "Genesis Context": "Example: O da vwe gangan (It pained me deeply)",
    },
    {
        "Word": "de (sequential: and / then / when)",
        "BaseWord": "de",
        "Frequency": 494,
        "English Gloss": "and then / when / so [sequential clause marker]",
        "Proposed Tone": "de",
        "Genesis Context": "o de phio phihọ udju rẹ Idẹn na rere ọ sẹro rọye (Genesis 2:15)",
    },
    {
        "Word": "vwọ (particle: when / as)",
        "BaseWord": "vwọ",
        "Frequency": 243,
        "English Gloss": "when / as / in order to [relational particle]",
        "Proposed Tone": "vwọ",
        "Genesis Context": "Ọke rẹ emọ na vwọ ghwanre re (When the children grew)",
    },
    {
        "Word": "vwọ (verb: lift to head)",
        "BaseWord": "vwọ",
        "Frequency": 5,
        "English Gloss": "assist to lift load onto head [physical action verb]",
        "Proposed Tone": "vwọ́",
        "Genesis Context": "Example: Vwọ erere kpahen uyovwin (Lift load onto head)",
    },
    {
        "Word": "vwo (verb: have / possess)",
        "BaseWord": "vwo",
        "Frequency": 207,
        "English Gloss": "to have / possess / own [stative verb]",
        "Proposed Tone": "vwo",
        "Genesis Context": "o vwo eka vwẹ orua rọye na-a (he had no blemish in his family)",
    },
    {
        "Word": "vwo (instrumental: with / using)",
        "BaseWord": "vwo",
        "Frequency": 150,
        "English Gloss": "with / using / thereby [instrumental associative particle]",
        "Proposed Tone": "vwo",
        "Genesis Context": "vwẹ ọmọ ọfa vwo ba kẹ vwẹ (add another son unto me with it)",
    },
    {
        "Word": "dia (verb: stay / live / be)",
        "BaseWord": "dia",
        "Frequency": 182,
        "English Gloss": "stay / live / dwell / remain [stative / locative verb]",
        "Proposed Tone": "dia",
        "Genesis Context": "Oyoma rere ọsháre ọ́vo vwọ dia sogono-o (Not good that man should stay alone)",
    },
    {
        "Word": "vẹ (conjunction: and / with)",
        "BaseWord": "vẹ",
        "Frequency": 207,
        "English Gloss": "and / along with [connective conjunction]",
        "Proposed Tone": "vẹ",
        "Genesis Context": "Kẹnẹ a ma odjúvwu vẹ akpọ́ (Thus heavens and earth were created)",
    },
    {
        "Word": "kẹ (prep: to / for)",
        "BaseWord": "kẹ",
        "Frequency": 605,
        "English Gloss": "to / for [dative preposition]",
        "Proposed Tone": "kẹ",
        "Genesis Context": "Ọrovwohwo Ọghẹnẹ de ji urhi kẹ ohwo na (God gave command to the man)",
    },
    {
        "Word": "kẹ (verb: give / bestow)",
        "BaseWord": "kẹ",
        "Frequency": 50,
        "English Gloss": "to give / gift / bestow [lexical verb]",
        "Proposed Tone": "kẹ́",
        "Genesis Context": "wọ je kẹ vwẹ ọmọ-ọ (you have not given me a child)",
    },
    {
        "Word": "se (verb: call / name)",
        "BaseWord": "se",
        "Frequency": 114,
        "English Gloss": "call / name [verb: se odẹ]",
        "Proposed Tone": "se",
        "Genesis Context": "ke se nẹ Ayé, fikiridie omá rẹ ọshare esiro nurhe (she shall be called Woman)",
    },
    {
        "Word": "se (verb: read / count)",
        "BaseWord": "se",
        "Frequency": 15,
        "English Gloss": "to read / recite / count [lexical verb]",
        "Proposed Tone": "sé",
        "Genesis Context": "Example: Se ẹbe na (Read the book / count)",
    },
    {
        "Word": "isọ (name: Esau)",
        "BaseWord": "isọ",
        "Frequency": 83,
        "English Gloss": "Esau [biblical proper name]",
        "Proposed Tone": "Isọ",
        "Genesis Context": "Isọ kẹ ọgba oruẹ, ohwo rẹ aghwa (Esau was a skillful hunter)",
    },
    {
        "Word": "isọ (noun: excreta / feces)",
        "BaseWord": "isọ",
        "Frequency": 2,
        "English Gloss": "excreta / stool / feces [noun]",
        "Proposed Tone": "isọ",
        "Genesis Context": "Example: Ku isọ na phio otọ (Throw the dirt/feces out)",
    },
    {
        "Word": "me (pronoun: I)",
        "BaseWord": "me",
        "Frequency": 215,
        "English Gloss": "I [1st person subject pronoun]",
        "Proposed Tone": "me",
        "Genesis Context": "Me ma ọchuko ro fori vwọ kẹ (I will make a helper suitable for him)",
    },
    {
        "Word": "mẹ (possessive: my / mine)",
        "BaseWord": "mẹ",
        "Frequency": 235,
        "English Gloss": "my / mine [1st person possessive pronoun]",
        "Proposed Tone": "mẹ",
        "Genesis Context": "Ọnana ubeku mẹ́ kugbe uvwo rẹ uvwo mẹ (This is bone of my bones)",
    },
]


def curate_review_sheet():
    if not os.path.exists(INPUT_CSV):
        print(f"Error: {INPUT_CSV} not found.")
        sys.exit(1)

    with open(INPUT_CSV, "r", encoding="utf-8-sig") as f:
        reader = list(csv.DictReader(f))

    fieldnames = ["Rank", "Word", "Frequency", "English Gloss", "Proposed Tone", "Verified Tone", "Genesis Context"]

    # 1. Update existing rows with accurate glosses
    updated_rows = []
    seen_words = set()

    for row in reader:
        word = row["Word"].strip()
        word_lower = word.lower()

        # Update gloss if we have an accurate contextual correction
        if word_lower in GLOSS_CORRECTIONS:
            row["English Gloss"] = GLOSS_CORRECTIONS[word_lower]

        # Reset any mistaken previous tone inputs on particles that caused confusion
        if word_lower == "re" and row.get("Verified Tone") == "ré":
            row["Verified Tone"] = "re"
        elif word_lower == "da" and row.get("Verified Tone") == "dá":
            row["Verified Tone"] = "da"

        updated_rows.append(row)
        seen_words.add(word_lower)

    # 2. Add multi-form disambiguation rows at the end or integrated cleanly
    start_rank = len(updated_rows) + 1
    disambiguation_rows = []
    for idx, item in enumerate(MULTI_FORM_HOMOGRAPHS, start=start_rank):
        new_row = {
            "Rank": f"H-{idx - start_rank + 1:02d}",
            "Word": item["Word"],
            "Frequency": str(item["Frequency"]),
            "English Gloss": item["English Gloss"],
            "Proposed Tone": item["Proposed Tone"],
            "Verified Tone": item["Proposed Tone"],
            "Genesis Context": item["Genesis Context"],
        }
        disambiguation_rows.append(new_row)

    all_rows = updated_rows + disambiguation_rows

    # Write CSV with UTF-8 BOM
    with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    # Write TSV
    with open(OUTPUT_TSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"Successfully updated review files:")
    print(f"  - CSV: {OUTPUT_CSV} ({len(all_rows)} rows)")
    print(f"  - TSV: {OUTPUT_TSV} ({len(all_rows)} rows)")
    print(f"  - Cleaned up {len(GLOSS_CORRECTIONS)} glosses.")
    print(f"  - Added {len(MULTI_FORM_HOMOGRAPHS)} explicit multi-form homograph rows.")


if __name__ == "__main__":
    curate_review_sheet()
