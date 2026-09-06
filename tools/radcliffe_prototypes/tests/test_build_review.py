from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_review import require_approval


class ApprovalBoundaryTests(unittest.TestCase):
    def test_no_review_cannot_be_treated_as_approval(self):
        with self.assertRaisesRegex(ValueError, "explicit human approval"):
            require_approval(None, "AUD-TEST")

    def test_five_star_rating_without_approval_is_insufficient(self):
        with self.assertRaises(ValueError):
            require_approval({"rating": 5, "selected": 0, "rejected": 0}, "AUD-TEST")

    def test_rejected_track_cannot_enter_av_review(self):
        with self.assertRaises(ValueError):
            require_approval({"rating": 5, "selected": 1, "rejected": 1}, "AUD-TEST")

    def test_explicit_nonrejected_approval_is_accepted(self):
        require_approval({"rating": 4, "selected": 1, "rejected": 0}, "AUD-TEST")


if __name__ == "__main__":
    unittest.main()
