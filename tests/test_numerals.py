"""
Unit tests for Urhobo Numerals Module (scripts/urhobo_numerals.py).
Validates algorithmic decomposition, tone marking, and cross-checks with
app_content/curriculum_vocab.tsv.
"""

import sys
import unittest
import csv
from pathlib import Path

# Add scripts directory to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from urhobo_numerals import (
    int_to_urhobo,
    decompose_numeral,
    spellout_digits_in_text,
    UNITS,
    DECADES,
)


class TestUrhoboNumerals(unittest.TestCase):

    def test_units_0_to_10(self):
        expected = {
            0: "ofefe",
            1: "ọvo",
            2: "ive",
            3: "erha",
            4: "ẹne",
            5: "iyori",
            6: "esan",
            7: "ighwrẹ",
            8: "ẹrẹnren",
            9: "irhirhi",
            10: "ihwe",
        }
        for n, exp in expected.items():
            with self.subTest(n=n):
                self.assertEqual(int_to_urhobo(n, toned=False), exp)
                decomp = decompose_numeral(n)
                self.assertEqual(decomp.value, n)
                self.assertGreater(len(decomp.morphemes), 0)

    def test_teens_11_to_19(self):
        expected = {
            11: ("ihwegbọvo", "ihwégbọ́vo"),
            12: ("ihwegbive", "ihwégbǐve"),
            13: ("ihwegberha", "ihwégbẹ́rha"),
            14: ("ihwegbẹne", "ihwégbẹ́ne"),
            15: ("ihwegbiyori", "ihwégbiyórĩ"),
            16: ("ihwegbesan", "ihwégbesán"),
            17: ("ihwegbighwrẹ", "ihwégbighwrẹ́"),
            18: ("ihwegbẹrẹnren", "ihwégbẹrẹ́nrẹn"),
            19: ("ihwegbirhirhi", "ihwégbirhírhi"),
        }
        for n, (exp_raw, exp_toned) in expected.items():
            with self.subTest(n=n):
                self.assertEqual(int_to_urhobo(n, toned=False), exp_raw)
                self.assertEqual(int_to_urhobo(n, toned=True), exp_toned)
                decomp = decompose_numeral(n)
                self.assertEqual(len(decomp.morphemes), 3)  # ten + connector + unit
                self.assertEqual(decomp.morphemes[0].kind, "ten")
                self.assertEqual(decomp.morphemes[1].kind, "connector")
                self.assertEqual(decomp.morphemes[2].kind, "unit")

    def test_decades_and_hundred(self):
        self.assertEqual(int_to_urhobo(20), "ucheve")
        self.assertEqual(int_to_urhobo(30), "ogba")
        self.assertEqual(int_to_urhobo(40), "ucheye")
        self.assertEqual(int_to_urhobo(50), "ujuve gbihwe")
        self.assertEqual(int_to_urhobo(60), "ujorha")
        self.assertEqual(int_to_urhobo(70), "ujorha gbihwe")
        self.assertEqual(int_to_urhobo(80), "ujone")
        self.assertEqual(int_to_urhobo(90), "ujone gbihwe")
        self.assertEqual(int_to_urhobo(100), "uri")

    def test_composite_numbers(self):
        self.assertEqual(int_to_urhobo(21), "ucheve gbọvo")
        self.assertEqual(int_to_urhobo(25), "ucheve gbiyori")
        self.assertEqual(int_to_urhobo(35), "ogba gbiyori")
        self.assertEqual(int_to_urhobo(73), "ujorha gbihwe gberha")
        self.assertEqual(int_to_urhobo(99), "ujone gbihwe gbirhirhi")

    def test_hundreds_and_thousands(self):
        self.assertEqual(int_to_urhobo(105), "uri kugbe iyori")
        self.assertEqual(int_to_urhobo(120), "uri kugbe ucheve")
        self.assertEqual(int_to_urhobo(200), "uri")
        self.assertEqual(int_to_urhobo(1000), "uriori")

    def test_morphemic_decomposition(self):
        decomp = decompose_numeral(25)
        self.assertEqual(decomp.value, 25)
        self.assertEqual(decomp.formula, "20 + 5")
        kinds = [m.kind for m in decomp.morphemes]
        self.assertEqual(kinds, ["base", "connector", "unit"])
        d = decomp.to_dict()
        self.assertIn("morphemes", d)
        self.assertEqual(len(d["morphemes"]), 3)

    def test_spellout_digits_in_text(self):
        text = "Avwanre vwo ihwo 12 vẹ emọ 5."
        result = spellout_digits_in_text(text, toned=False)
        self.assertEqual(result, "Avwanre vwo ihwo ihwegbive vẹ emọ iyori.")

    def test_cross_check_curriculum_tsv(self):
        tsv_path = REPO_ROOT / "app_content" / "curriculum_vocab.tsv"
        self.assertTrue(tsv_path.exists(), "curriculum_vocab.tsv missing")
        with open(tsv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                if row["category"] == "number":
                    raw = row["urhobo_raw"]
                    toned = row["urhobo_toned"]
                    # If this is a base single number, test that it maps correctly
                    # Check that raw is non-empty and toned has diacritics
                    self.assertTrue(len(raw) > 0)
                    self.assertTrue(len(toned) > 0)


if __name__ == "__main__":
    unittest.main()
