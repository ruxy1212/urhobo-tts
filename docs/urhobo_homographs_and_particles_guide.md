# Urhobo Homographs & Grammatical Particles Disambiguation Guide

> **Audience**: Native Urhobo Reviewers, Linguists, and TTS Annotation Team  
> **Purpose**: Provide clear contextual distinction between lexical content words (with fixed inherent tones) and grammatical particles/homographs (whose pitch and meaning depend on clause syntax).

---

## 1. Why Urhobo Homographs Require Careful Disambiguation

In Urhobo, words that share identical spelling often carry completely different meanings, parts of speech, and tonal melodies depending on their grammatical role:

1. **Lexical Content Words (Nouns, Numbers, Adjectives, Root Verbs)**:
   - Words like *Ọghẹnẹ*, *akpọ́*, *odjúvwu*, *ọsháre*, *ẹ́rha*, *iyórin*, *urhie*, *ubeku* have **fixed, inherent tones**.
   - These represent over 95% of Urhobo vocabulary and their tone marks should be reviewed and verified directly.
2. **Grammatical Particles & Functional Clitics**:
   - Short words like `re`, `da`, `vwẹ`, `na`, `rẹ`, `kẹ`, `de`, `vẹ` serve as conjunctions, prepositions, relative markers, or aspect markers.
   - Automated dictionary searches often assign root verbal definitions (such as `re` = *"to eat"*, `vwẹ` = *"to urinate"*, `da` = *"to drink"*, or `ta` = *"to condemn"*) to these functional words.
   - When reviewing Bible verses or conversational prompts, **always evaluate the word in its actual sentence context**, not based on an isolated dictionary headword.

---

## 2. Master Disambiguation Table

The table below breaks down the most frequent homographs in the Urhobo corpus, their syntactic roles, tonal contours, and examples.

### 1. `ta`
| Form / Function | Grammatical Role | Meaning | Tone Contour | Urhobo Example | English Translation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`ta` (Primary Verb)** | Transitive / Intransitive Verb | to say, speak, talk, utter | Mid (ta) | *Ọrovwohwo Ọghẹnẹ da ta...* | "The LORD God said..." |
| **`ta` (Compound Verb)** | Verbal Idiom (*ta ohwo / ta ota*) | to blame, rebuke, speak against | Contextual | *Ọ ta ota kpahen riẹ* | "He spoke against / rebuked him" |

---

### 2. `vwẹ`
| Form / Function | Grammatical Role | Meaning | Tone Contour | Urhobo Example | English Translation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`vwẹ` (Preposition)** | Locative Preposition | in, at, on, inside, by | Prepositional (vwẹ) | *Urhie da va phia vwẹ Idẹn* | "A river came out in Eden" |
| **`vwẹ` (Pronoun)** | 1st Person Object Pronoun | me / to me | Post-verbal (vwẹ) | *Ebram da ta: wọ je kẹ vwẹ ọmọ-ọ* | "You have not given me a child" |
| **`vwẹ́` (Verb)** | Lexical Verb | to discharge, pass water, urinate | High (vwẹ́) | *Ọ cha vwẹ́ ame* | "He will pass water" |

---

### 3. `re`
| Form / Function | Grammatical Role | Meaning | Tone Contour | Urhobo Example | English Translation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`re` (Relative)** | Relative Pronoun / Complementizer | that, which, who | Mid / Unmarked (re) | *obo re vọnrọ ejobi* | "that which filled it all" |
| **`ré` (Verb)** | Transitive Action Verb | to eat, consume | High (ré) | *Wọ sa re omamọ komamọ rẹ udju na* | "You may eat of every tree of the garden" |
| **`re` (Aspect)** | Perfective Aspect Marker | already, completed | Low / Mid (re) | *Ọke rẹ emọ na vwọ ghwanre re* | "When the children had grown already" |

---

### 4. `rẹ` / `ri` / `ro` / `rọ`
| Form / Function | Grammatical Role | Meaning | Tone Contour | Urhobo Example | English Translation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`rẹ` / `ri` (Genitive)** | Associative / Genitive Preposition | of, belonging to | Neutral (rẹ / ri) | *odẹ rẹ ọsháre na* | "the name of the man" |
| **`ro` / `rọ` (Relative)** | Contracted Relative Pronoun | who, which (vowel harmony) | Relational (rọ / ro) | *ohwo ro sun ọbara rẹ ohwo* | "the person who sheds human blood" |
| **`rẹ́` (Verb)** | Lexical Verb | to beg, plead, beseech | High (rẹ́) | *Ọ rẹ́ Ọghẹnẹ kẹ erere* | "He pleaded with God for blessing" |

---

### 5. `da` / `de`
| Form / Function | Grammatical Role | Meaning | Tone Contour | Urhobo Example | English Translation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`da` (Narrative)** | Consecutive Past Marker | then, and then | Narrative (da) | *Urhie da va phia ... ọ da jẹn eghọn* | "A river came out ... and then parted" |
| **`de` (Sequential)** | Sequential / Temporal Marker | when, if, then | Sequential (de) | *o de phio phihọ udju rẹ Idẹn* | "and then he put it in the garden" |
| **`dá` (Verb: Drink)** | Action Verb | to drink | High (dá) | *Ọ dá ame nẹ urhie na* | "He drank water from the river" |
| **`dá` (Verb: Hurt)** | Impersonal Stative Verb | to hurt, pain, grieve | High (dá) | *O dá vwe gangan* | "It pained me deeply" |

---

### 6. `vwọ` / `vwo`
| Form / Function | Grammatical Role | Meaning | Tone Contour | Urhobo Example | English Translation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`vwọ` (Particle)** | Temporal / Purposive Particle | when, as, in order to | Temporal (vwọ) | *Ọke rẹ emọ na vwọ ghwanre* | "When the children grew" |
| **`vwo` (Verb: Have)** | Stative Verb | to have, possess, own | Stative (vwo) | *o vwo eka vwẹ orua rọye-e* | "he had no blemish in his family" |
| **`vwo` (Instrumental)**| Instrumental / Associative | with, using, thereby | Associative (vwo) | *vwẹ ọmọ ọfa vwo ba kẹ vwẹ* | "add another child unto me with it" |
| **`vwọ́` (Verb: Lift)** | Action Verb | to lift / place load on head | High (vwọ́) | *Vwọ erere kpahen uyovwin* | "Lift load onto head" |

---

### 7. `dia`
| Form / Function | Grammatical Role | Meaning | Tone Contour | Urhobo Example | English Translation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`dia` (Stative Verb)**| Locative / Stative Verb | to stay, live, dwell, be | Stative (dia / diá) | *Oyoma rere ọsháre ọ́vo vwọ dia sogono-o*| "It is not good that man should stay alone" |
| **`dia` (Physiological)**| Specialized Verb | to menstruate | Low / Specific | (Colloquial / medical) |

---

### 8. `vẹ`
| Form / Function | Grammatical Role | Meaning | Tone Contour | Urhobo Example | English Translation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`vẹ` (Conjunction)** | Coordinating Conjunction | and, along with, with | Neutral (vẹ) | *odjúvwu vẹ akpọ́* | "heavens and earth" |
| **`vẹ́` (Verb)** | Action Verb | to disperse (crowd) | High (vẹ́) | *Otu na vẹ́ re* | "The crowd has dispersed" |

---

### 9. `kẹ` / `ke`
| Form / Function | Grammatical Role | Meaning | Tone Contour | Urhobo Example | English Translation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`kẹ` (Preposition)** | Dative Preposition | to, for, toward | Dative (kẹ) | *ji urhi kẹ ohwo na* | "gave a command to the man" |
| **`ke` (Consecutive)** | Future / Consecutive Particle | then shall, will then | Particle (ke / kẹ) | *ke se nẹ Ayé* | "then shall she be called Woman" |
| **`kẹ́` (Verb)** | Action Verb | to give, grant, bestow | High (kẹ́) | *wọ je kẹ vwẹ ọmọ-ọ* | "you have not given me a child" |

---

### 10. `se`
| Form / Function | Grammatical Role | Meaning | Tone Contour | Urhobo Example | English Translation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`se` (Verb: Call)** | Verbal Root (*se odẹ*) | to call, name, invite | Neutral / Mid (se) | *ke se nẹ Ayé* / *o de se odẹ rọye* | "shall be called Woman" / "named him" |
| **`sé` (Verb: Read)** | Verbal Root (*se ẹbe*) | to read, count, recite | High (sé) | *Se ẹbe na kẹ avwanre* | "Read the book to us" |

---

### 11. `isọ`
| Form / Function | Grammatical Role | Meaning | Tone Contour | Urhobo Example | English Translation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`Isọ` (Proper Name)**| Biblical Name (Esau) | Esau (son of Isaac) | Capitalized (Isọ) | *Isọ kẹ ọgba oruẹ, ohwo rẹ aghwa* | "Esau was a skillful hunter" |
| **`isọ` (Noun)** | Common Noun | excreta, stool, feces | Low / Common | *Ku isọ na phio otọ* | "Throw the dirt/feces out" |

---

### 12. `mi` / `me` / `mẹ`
| Form / Function | Grammatical Role | Meaning | Tone Contour | Urhobo Example | English Translation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`mi` / `me` (Subject)**| 1st Person Subject Pronoun | I | Subject (mi / me) | *Me ma ọchuko* / *ri mi vwo mu* | "I will make a helper" / "which I made" |
| **`mẹ` (Possessive)** | 1st Person Possessive Pronoun | my, mine | Possessive (mẹ) | *ubeku mẹ́ kugbe uvwo rẹ uvwo mẹ* | "bone of my bones, flesh of my flesh" |
| **`mí` (Verb: Squeeze)**| Action Verb | to squeeze, wring out | High (mí) | *Mí ame nẹ iwun na* | "Wring water from the cloth" |
| **`mé` (Verb: Plait)** | Action Verb | to plait (hair) | High (mé) | *Mé eto na* | "Plait the hair" |

---

## 3. How to Review the Spreadsheet

In `data/lexicon/top_500_priority_tones_review.csv`:

1. **Ranks 1 through 500**:
   - Every row represents a word as used in its actual **Genesis Context** column.
   - Read the **Genesis Context** sentence first.
   - If the word is a content word (noun, adjective, number), verify the accurate tone mark in the **Verified Tone** column.
   - If the word is a grammatical particle, mark its pitch as heard in natural spoken cadence in that sentence.
2. **Rows H-01 through H-26 (Disambiguation Rows)**:
   - These rows at the bottom isolate each distinct meaning and verbal form of the homographs listed above.
   - Native speakers can verify the tone of each form independently (e.g., verifying `ré` for *"eat"* vs `re` for *"that/which"*).
