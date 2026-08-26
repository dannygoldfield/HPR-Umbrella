from array import array
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
import wave


TOOL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOL_ROOT))

from assemble_pair_round import _stable_id, _validate_source_wav  # noqa: E402


class AssemblePairRoundTests(unittest.TestCase):
    def test_pair_identity_is_stable_and_asset_specific(self) -> None:
        first = _stable_id("PAIR", "VIS-1", "AUD-1")
        self.assertEqual(first, _stable_id("PAIR", "VIS-1", "AUD-1"))
        self.assertNotEqual(first, _stable_id("PAIR", "VIS-1", "AUD-2"))

    def test_source_wav_must_be_native_eleven_second_delivery(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "audio.wav"
            samples = array("h", [0]) * (11 * 48000 * 2)
            with wave.open(str(path), "wb") as audio:
                audio.setnchannels(2)
                audio.setsampwidth(2)
                audio.setframerate(48000)
                audio.writeframes(samples.tobytes())
            self.assertEqual(11 * 48000, _validate_source_wav(path, 11)["frameCount"])


if __name__ == "__main__":
    unittest.main()
