from __future__ import annotations

import sys
import unittest
from pathlib import Path


TOOL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOL_DIR))

import inspect_metadata  # noqa: E402


class FilenameTests(unittest.TestCase):
    def test_intake_preserves_original_name_without_episode(self) -> None:
        result = inspect_metadata.parse_filename(Path("bahamas.210.jpg"), "intake")
        self.assertTrue(result.valid)
        self.assertIsNone(result.episode_number)
        self.assertEqual(result.source_filename, "bahamas.210.jpg")
        self.assertEqual(result.source_basename, "bahamas.210")

    def test_intake_accepts_tiff_without_episode(self) -> None:
        result = inspect_metadata.parse_filename(Path("portrait.tif"), "intake")
        self.assertTrue(result.valid)
        self.assertIsNone(result.episode_number)
        self.assertEqual(result.source_filename, "portrait.tif")
        self.assertEqual(result.source_basename, "portrait")

    def test_release_parses_three_digit_episode(self) -> None:
        result = inspect_metadata.parse_filename(Path("037-original-name.jpg"), "release")
        self.assertTrue(result.valid)
        self.assertEqual(result.episode_number, 37)
        self.assertEqual(result.source_filename, "original-name.jpg")

    def test_release_allows_more_than_three_digits(self) -> None:
        result = inspect_metadata.parse_filename(Path("1000-original-name.jpeg"), "release")
        self.assertTrue(result.valid)
        self.assertEqual(result.episode_number, 1000)

    def test_release_rejects_unsequenced_name(self) -> None:
        result = inspect_metadata.parse_filename(Path("original-name.jpg"), "release")
        self.assertFalse(result.valid)


class XmpTests(unittest.TestCase):
    def test_extracts_attributes_alt_text_and_bag(self) -> None:
        raw = b"""<?xml version='1.0'?>
<x:xmpmeta xmlns:x='adobe:ns:meta/'>
  <rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>
    <rdf:Description xmlns:xmp='http://ns.adobe.com/xap/1.0/'
      xmlns:dc='http://purl.org/dc/elements/1.1/' xmp:Rating='3'>
      <dc:title><rdf:Alt><rdf:li xml:lang='x-default'>Title</rdf:li></rdf:Alt></dc:title>
      <dc:subject><rdf:Bag><rdf:li>one</rdf:li><rdf:li>two</rdf:li></rdf:Bag></dc:subject>
    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>"""
        result = inspect_metadata.extract_xmp(raw)
        self.assertEqual(result["XMP:xmp:Rating"], "3")
        self.assertEqual(result["XMP:dc:title"], "Title")
        self.assertEqual(result["XMP:dc:subject"], ["one", "two"])


class ComparisonTests(unittest.TestCase):
    def test_color_label_comparison_is_case_insensitive(self) -> None:
        metadata = {
            "XMP:xmp:Label": "Red",
            "XMP:photoshop:LabelColor": "red",
        }
        result = inspect_metadata.compare_fields(metadata, {"color_label": "Red"})
        self.assertEqual(result["color_label"]["status"], "match")

    def test_single_creator_sequence_matches_scalar_expectation(self) -> None:
        metadata = {"XMP:dc:creator": ["HPR-TEST-A-CREATOR"]}
        result = inspect_metadata.compare_fields(
            metadata, {"creator": "HPR-TEST-A-CREATOR"}
        )
        self.assertEqual(result["creator"]["status"], "match")


if __name__ == "__main__":
    unittest.main()
