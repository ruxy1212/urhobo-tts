# Urhobo Tone & Accent Guide for Native Reviewers
*(Ona rẹ Emuo rẹ Urhobo: How to mark tones on the review sheet)*

This guide is designed for native Urhobo speakers reviewing the **Top 500 Priority Words Sheet** (`top_500_priority_tones_review.csv`). 

You already know the correct melody and pronunciation of Urhobo words naturally with your ear and voice. This guide explains which **keyboard symbols** correspond to the exact musical pitch movements you hear.

---

## 1. Quick Reference Table: All Allowed Tonal Symbols

All of the symbols below exist in our Urhobo AI model's vocabulary. You can copy and paste them directly into the **`Verified Tone`** column:

| Tone / Pitch Movement | Symbol Name | Mark | Example Vowels | How It Sounds in English / Music | Common Urhobo Example |
|---|---|---|---|---|---|
| **High Pitch** | **Acute** | `´` (slanted up to right) | **á, é, ẹ́, í, ó, ọ́, ú, ń** | Sharp, energetic high note (like singing *"Do-Re-**MI**"* or saying an enthusiastic *"Yes!"*) | **ọ́vo** (high on first syllable)<br>**ẹ́rha**, **ẹ́ne** |
| **Low Pitch** | **Grave** | `` ` `` (slanted down to right) | **à, è, ẹ̀, ì, ò, ọ̀, ù, ǹ** | Deep, dropped low note (like singing ***DO**-Re-Mi* or a low murmur) | **òtọ̀**, **àkpọ̀** |
| **Mid Pitch (Neutral)** | **Unmarked** | *(no mark)* | **a, e, ẹ, i, o, ọ, u** | Normal conversational speaking pitch without high or low stress. | Middle syllables in long words |
| **Rising Glide** *(Slide Low $\rightarrow$ High)* | **Caron / Wedge** | `ˇ` (V-shape) | **ǎ, ě, ǐ, ǒ, ǔ, ẹ̌, ọ̌** | Pitch starts low and **slides UP** in the same breath (like asking an inquisitive *"Really?"* or *"Huh?"*) | **ǐve** (the rising slide on *"two"*) |
| **Falling Glide** *(Slide High $\rightarrow$ Low)* | **Circumflex / Hat** | `ˆ` (tent-shape) | **â, ê, î, ô, û, ệ, ộ** | Pitch starts high and **slides DOWN** in the same breath (like a sigh: *"Ohh..."*) | Peaked emphasis words |
| **Nasalized Vowel** *(The "ng" / nasal hum)* | **Tilde / 'n'** | `~` or trailing `n` | **ã, ẽ, ĩ, õ, ũ** (or `in`, `an`, `ẹn`, `ọn`) | Air flows through the nose (like the end of *"sing"* or French *"bon"*) | **iyórĩ** or **iyorin** (the nasal sound on *"five"*) |

---

## 2. Vowel Length: Short vs. Stretched / Elongated Sounds

In Urhobo, some words have a **short, clipped** vowel, while others have a **stretched, elongated** vowel:

* **Short Vowel**: Write a single letter.
  * Example: `ẹ́ne` (4) — short, clipped open `ẹ`.
* **Stretched / Drawn-Out Vowel**: Double the letter to tell the model to hold the note longer.
  * Example: `ọ́ọvo` or `ọ́vo` — if the speaker holds the first vowel longer.

---

## 3. The 3 Special Urhobo Vowels

Always ensure the dot-below vowels are written properly:
* **`ẹ` / `Ẹ`** (open e — like *"bed"* or *"pet"*): With acute $\rightarrow$ **`ẹ́`**, with grave $\rightarrow$ **`ẹ̀`**.
* **`ọ` / `Ọ`** (open o — like *"law"* or *"call"*): With acute $\rightarrow$ **`ọ́`**, with grave $\rightarrow$ **`ọ̀`**.
* **`ṣ` / `Ṣ`** (sh sound): If applicable in dialect words.

---

## 4. Cheat Sheet for Copy-Pasting into Excel / Google Sheets

If your keyboard does not have tone marks, you can simply **copy and paste** from this block directly into the spreadsheet:

### High Tone Vowels (Acute):
```text
á   é   ẹ́   í   ó   ọ́   ú   ń
Á   É   Ẹ́   Í   Ó   Ọ́   Ú
```

### Low Tone Vowels (Grave):
```text
à   è   ẹ̀   ì   ò   ọ̀   ù   ǹ
À   È   Ẹ̀   Ì   Ò   Ọ̀   Ù
```

### Rising Tone Vowels (Slide Up):
```text
ǎ   ě   ẹ̌   ǐ   ǒ   ọ̌   ǔ
Ǎ   Ě   Ẹ̌   Ǐ   Ǒ   Ọ̌   Ǔ
```

### Falling Tone Vowels (Slide Down):
```text
â   ê   ệ   î   ô   ộ   û
Â   Ê   Ệ   Î   Ô   Ộ   Û
```

### Nasal Vowels:
```text
ã   ẽ   ĩ   õ   ũ
```
*(You can also simply write a normal vowel followed by 'n', like `iyorin` or `ẹvwen`)*.

---

## 5. Summary of Instructions for Reviewers
1. Look at the word in Genesis context.
2. Say the word naturally out loud.
3. If the pitch stays normal/flat $\rightarrow$ Leave the letters plain (`a, e, ẹ, i, o, ọ, u`).
4. If your voice goes up $\rightarrow$ Use acute (`á, é, ẹ́, í, ó, ọ́, ú`).
5. If your voice drops down $\rightarrow$ Use grave (`à, è, ẹ̀, ì, ò, ọ̀, ù`).
6. If your voice slides from low to high on one syllable $\rightarrow$ Use caron (`ǐ, ě, ǒ...`).
7. Paste or type the corrected word into the **`Verified Tone`** column.
