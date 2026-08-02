from __future__ import annotations

from array import array
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory
import wave
import xml.etree.ElementTree as ET


SOURCE_ROOT = Path(__file__).resolve().parents[1]


class AudioFixture:
    """Materialize small synthetic WAV assets for public-repository tests."""

    def __enter__(self) -> Path:
        self._temporary = TemporaryDirectory()
        root = Path(self._temporary.name)
        config = root / "config/generator.xml"
        config.parent.mkdir(parents=True)
        copyfile(SOURCE_ROOT / "config/generator.xml", config)
        document = ET.parse(config)
        for node in document.findall("./assets/asset"):
            path = root / node.attrib["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            role = node.attrib["role"]
            frames = 4800 if role == "Gesture" else 48017
            samples = array("h")
            for frame in range(frames):
                value = (frame % 2000) - 1000
                samples.extend((value, -value))
            with wave.open(str(path), "wb") as output:
                output.setnchannels(2)
                output.setsampwidth(2)
                output.setframerate(48000)
                output.writeframes(samples.tobytes())
        return config

    def __exit__(self, exc_type, exc, traceback) -> None:
        self._temporary.cleanup()
