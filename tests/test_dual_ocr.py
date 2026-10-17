import os
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import dual_ocr


def box(x0, y0, text):
    points = [[x0, y0], [x0 + 200, y0], [x0 + 200, y0 + 20], [x0, y0 + 20]]
    return points, text


class FuseTests(unittest.TestCase):

    def test_replaces_a_broken_word_with_the_valid_one(self):
        reading_a = dual_ocr.tokens_from_paragraphs(["the sun rises over LNountains", "and the sea"])
        reading_b = dual_ocr.tokens_from_paragraphs(["the sun rises over mountains and the sea"])
        self.assertEqual(dual_ocr.fuse(reading_a, reading_b),
                         ["the sun rises over mountains", "and the sea"])

    def test_drops_stray_symbols(self):
        reading_a = dual_ocr.tokens_from_paragraphs(["Frater | ~ R.O."])
        reading_b = dual_ocr.tokens_from_paragraphs(["Frater R.O."])
        self.assertEqual(dual_ocr.fuse(reading_a, reading_b), ["Frater R.O."])

    def test_keeps_paragraph_start_from_either_reading(self):
        reading_a = dual_ocr.tokens_from_paragraphs(["one two", "three four"])
        reading_b = dual_ocr.tokens_from_paragraphs(["one two three four"])
        self.assertEqual(dual_ocr.fuse(reading_a, reading_b), ["one two", "three four"])

    def test_single_reading_keeps_its_paragraphs(self):
        tokens = dual_ocr.tokens_from_paragraphs(["first paragraph", "second one"])
        self.assertEqual(dual_ocr.paragraphs_from_tokens(tokens), ["first paragraph", "second one"])


class ValidWordTests(unittest.TestCase):

    def test_plain_english_word_is_valid(self):
        self.assertTrue(dual_ocr.is_valid_word("absorbing"))

    def test_inflected_word_is_valid(self):
        self.assertTrue(dual_ocr.is_valid_word("experiences"))

    def test_nonsense_is_not_valid(self):
        self.assertFalse(dual_ocr.is_valid_word("paasasay"))

    def test_symbol_only_token_is_not_valid(self):
        self.assertFalse(dual_ocr.is_valid_word("|"))


class LineTextTests(unittest.TestCase):

    def test_indent_and_large_gap_start_new_paragraphs(self):
        result = SimpleNamespace(
            boxes=[],
            txts=[],
        )
        for points, text in [box(100, 100, "one"), box(100, 140, "two"),
                             box(140, 180, "indented"), box(100, 260, "new")]:
            result.boxes.append(points)
            result.txts.append(text)
        text = dual_ocr.rapid_lines_to_text(result)
        self.assertEqual(dual_ocr.split_paragraphs(text), ["one two", "indented", "new"])


if __name__ == "__main__":
    unittest.main()
