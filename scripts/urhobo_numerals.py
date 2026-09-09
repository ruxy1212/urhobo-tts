"""
Urhobo Numerals (Ukeri rẹ Urhobo)
Algorithmic numeral decomposition and spellout engine for Urhobo.

Converts integers (0-100+) into natural Urhobo word forms with explicit
access to base, unit, and connector morphemes for both TTS text normalization
and interactive mobile curriculum lessons.
"""

import re
from typing import List, Dict, Any
from dataclasses import dataclass, field


@dataclass
class Morpheme:
    kind: str       # 'unit', 'ten', 'base', 'connector'
    text: str       # plain orthography, e.g. 'ihwe', 'gb', 'ọvo'
    toned: str      # tone-marked orthography, e.g. 'ihwé', 'ọ́vo'
    value: int      # numeric contribution


@dataclass
class UrhoboNumeral:
    value: int
    text: str
    toned_text: str
    morphemes: List[Morpheme] = field(default_factory=list)
    formula: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "text": self.text,
            "toned_text": self.toned_text,
            "formula": self.formula,
            "morphemes": [
                {"kind": m.kind, "text": m.text, "toned": m.toned, "value": m.value}
                for m in self.morphemes
            ],
        }


# Base Units (0 - 10)
UNITS: Dict[int, Dict[str, str]] = {
    0: {"raw": "ofefe", "toned": "oféfe"},
    1: {"raw": "ọvo", "toned": "ọ́vo"},
    2: {"raw": "ive", "toned": "ǐve"},
    3: {"raw": "erha", "toned": "ẹ́rha"},
    4: {"raw": "ẹne", "toned": "ẹ́ne"},
    5: {"raw": "iyori", "toned": "iyórĩ"},
    6: {"raw": "esan", "toned": "esán"},
    7: {"raw": "ighwrẹ", "toned": "ighwrẹ́"},
    8: {"raw": "ẹrẹnren", "toned": "ẹrẹ́nrẹn"},
    9: {"raw": "irhirhi", "toned": "irhírhi"},
    10: {"raw": "ihwe", "toned": "ihwé"},
}

# Vigesimal / Decade Bases (20 - 100)
DECADES: Dict[int, Dict[str, str]] = {
    20: {"raw": "ucheve", "toned": "uchéve", "alt": "uje"},
    30: {"raw": "ogba", "toned": "ogbá", "alt": "ọgba"},
    40: {"raw": "ucheye", "toned": "uchéye", "alt": "ujuve"},
    50: {"raw": "ujuve gbihwe", "toned": "ujǔve gbihwé"},
    60: {"raw": "ujorha", "toned": "ujọ́rha"},
    70: {"raw": "ujorha gbihwe", "toned": "ujọ́rha gbihwé"},
    80: {"raw": "ujone", "toned": "ujọ́ne"},
    90: {"raw": "ujone gbihwe", "toned": "ujọ́ne gbihwé"},
    100: {"raw": "uri", "toned": "urí", "alt": "ujori"},
    200: {"raw": "uri", "toned": "urí"},
    1000: {"raw": "uriori", "toned": "urióri"},
}


def decompose_numeral(n: int) -> UrhoboNumeral:
    """
    Decomposes an integer into its structural Urhobo morphemes and full word string.
    """
    if n < 0:
        raise ValueError(f"Negative numbers not supported: {n}")

    if n <= 10:
        unit = UNITS[n]
        m = Morpheme(kind="unit", text=unit["raw"], toned=unit["toned"], value=n)
        return UrhoboNumeral(value=n, text=unit["raw"], toned_text=unit["toned"], morphemes=[m], formula=str(n))

    # Teens (11 - 19)
    if 11 <= n <= 19:
        unit_val = n - 10
        unit = UNITS[unit_val]
        m_ten = Morpheme(kind="ten", text="ihwe", toned="ihwé", value=10)
        m_conn = Morpheme(kind="connector", text="gb", toned="gb", value=0)
        m_unit = Morpheme(kind="unit", text=unit["raw"], toned=unit["toned"], value=unit_val)

        text = f"ihwegb{unit['raw']}"
        toned_text = f"ihwégb{unit['toned']}"
        return UrhoboNumeral(
            value=n,
            text=text,
            toned_text=toned_text,
            morphemes=[m_ten, m_conn, m_unit],
            formula=f"10 + {unit_val}",
        )

    # Exact Decades (20, 30, 40, 50, 60, 70, 80, 90, 100)
    if n in DECADES:
        dec = DECADES[n]
        m = Morpheme(kind="base", text=dec["raw"], toned=dec["toned"], value=n)
        return UrhoboNumeral(value=n, text=dec["raw"], toned_text=dec["toned"], morphemes=[m], formula=str(n))

    # Numbers 21 - 99
    if 20 < n < 100:
        if 21 <= n <= 29:
            base_val = 20
        elif 31 <= n <= 39:
            base_val = 30
        elif 41 <= n <= 49:
            base_val = 40
        elif 51 <= n <= 59:
            base_val = 50
        elif 61 <= n <= 69:
            base_val = 60
        elif 71 <= n <= 79:
            base_val = 70
        elif 81 <= n <= 89:
            base_val = 80
        else:
            base_val = 90

        unit_val = n - base_val
        unit = UNITS[unit_val]
        base = DECADES[base_val]

        m_base = Morpheme(kind="base", text=base["raw"], toned=base["toned"], value=base_val)
        m_conn = Morpheme(kind="connector", text="gb", toned="gb", value=0)
        m_unit = Morpheme(kind="unit", text=unit["raw"], toned=unit["toned"], value=unit_val)

        text = f"{base['raw']} gb{unit['raw']}"
        toned_text = f"{base['toned']} gb{unit['toned']}"

        return UrhoboNumeral(
            value=n,
            text=text,
            toned_text=toned_text,
            morphemes=[m_base, m_conn, m_unit],
            formula=f"{base_val} + {unit_val}",
        )

    # 101 - 199
    if 100 < n < 200:
        rem = n - 100
        m_hundred = Morpheme(kind="base", text="uri", toned="urí", value=100)
        sub = decompose_numeral(rem)
        text = f"uri kugbe {sub.text}"
        toned_text = f"urí kugbé {sub.toned_text}"
        return UrhoboNumeral(
            value=n,
            text=text,
            toned_text=toned_text,
            morphemes=[m_hundred] + sub.morphemes,
            formula=f"100 + {rem}",
        )

    # 200
    if n == 200:
        m = Morpheme(kind="base", text="uri", toned="urí", value=200)
        return UrhoboNumeral(value=n, text="uri", toned_text="urí", morphemes=[m], formula="200")

    # Multiples of 1000
    if n % 1000 == 0:
        k = n // 1000
        if k == 1:
            m = Morpheme(kind="base", text="uriori", toned="urióri", value=1000)
            return UrhoboNumeral(value=n, text="uriori", toned_text="urióri", morphemes=[m], formula="1000")
        sub_k = decompose_numeral(k)
        text = f"uriori {sub_k.text}"
        toned_text = f"urióri {sub_k.toned_text}"
        return UrhoboNumeral(
            value=n,
            text=text,
            toned_text=toned_text,
            morphemes=[Morpheme("base", "uriori", "urióri", 1000)] + sub_k.morphemes,
            formula=f"1000 * {k}",
        )

    # General composite numbers >= 200
    hundreds = (n // 100) * 100
    rem = n % 100
    base_h = decompose_numeral(hundreds) if hundreds in DECADES else UrhoboNumeral(hundreds, f"uri {n//100}", f"urí {n//100}")
    if rem == 0:
        return base_h
    sub_rem = decompose_numeral(rem)
    return UrhoboNumeral(
        value=n,
        text=f"{base_h.text} kugbe {sub_rem.text}",
        toned_text=f"{base_h.toned_text} kugbé {sub_rem.toned_text}",
        morphemes=base_h.morphemes + sub_rem.morphemes,
        formula=f"{hundreds} + {rem}",
    )


def int_to_urhobo(n: int, toned: bool = False) -> str:
    """
    Returns the spoken Urhobo word for integer n.
    """
    decomp = decompose_numeral(n)
    return decomp.toned_text if toned else decomp.text


def spellout_digits_in_text(text: str, toned: bool = False) -> str:
    """
    Finds isolated integers in text and converts them into spoken Urhobo words.
    Ignores verse prefix numbers if attached directly to words.
    """
    def replace_match(match):
        num_str = match.group(0)
        try:
            val = int(num_str)
            return int_to_urhobo(val, toned=toned)
        except Exception:
            return num_str

    # Replace standalone digits surrounded by word boundaries
    return re.sub(r"\b\d+\b", replace_match, text)
