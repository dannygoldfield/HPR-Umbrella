from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "verify_production.py"
SPEC = importlib.util.spec_from_file_location("verify_production", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ProductionVerificationTests(unittest.TestCase):
    def test_umbrella_contains_no_embedded_generator_copies(self) -> None:
        MODULE.verify_no_embedded_generators()

    def test_three_approved_visuals_match_the_recorded_baseline(self) -> None:
        self.assertEqual(3, len(MODULE.verify_approved_visuals()))


if __name__ == "__main__":
    unittest.main()
