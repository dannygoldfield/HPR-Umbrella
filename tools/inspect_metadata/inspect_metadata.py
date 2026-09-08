#!/usr/bin/env python3
"""Inspect Lightroom-exported portrait metadata without modifying the images."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET

try:
    from PIL import ExifTags, Image, ImageCms, IptcImagePlugin
except ModuleNotFoundError as exc:  # pragma: no cover - exercised by users
    raise SystemExit(
        "Pillow is required. Install tools/inspect_metadata/requirements.txt"
    ) from exc


RELEASE_FILENAME_RE = re.compile(
    r"^(?P<episode>[0-9]{3,})-(?P<source>.+)\.(?P<extension>jpe?g)$",
    re.IGNORECASE,
)

IPTC_DATASET_NAMES = {
    (1, 90): "CodedCharacterSet",
    (2, 0): "RecordVersion",
    (2, 5): "ObjectName",
    (2, 7): "EditStatus",
    (2, 10): "Urgency",
    (2, 15): "Category",
    (2, 20): "SupplementalCategories",
    (2, 22): "FixtureIdentifier",
    (2, 25): "Keywords",
    (2, 26): "ContentLocationCode",
    (2, 27): "ContentLocationName",
    (2, 30): "ReleaseDate",
    (2, 35): "ReleaseTime",
    (2, 37): "ExpirationDate",
    (2, 38): "ExpirationTime",
    (2, 40): "SpecialInstructions",
    (2, 42): "ActionAdvised",
    (2, 45): "ReferenceService",
    (2, 47): "ReferenceDate",
    (2, 50): "ReferenceNumber",
    (2, 55): "DateCreated",
    (2, 60): "TimeCreated",
    (2, 62): "DigitalCreationDate",
    (2, 63): "DigitalCreationTime",
    (2, 65): "OriginatingProgram",
    (2, 70): "ProgramVersion",
    (2, 75): "ObjectCycle",
    (2, 80): "Byline",
    (2, 85): "BylineTitle",
    (2, 90): "City",
    (2, 92): "SubLocation",
    (2, 95): "ProvinceState",
    (2, 100): "CountryCode",
    (2, 101): "CountryName",
    (2, 103): "OriginalTransmissionReference",
    (2, 105): "Headline",
    (2, 110): "Credit",
    (2, 115): "Source",
    (2, 116): "CopyrightNotice",
    (2, 118): "Contact",
    (2, 120): "CaptionAbstract",
    (2, 122): "WriterEditor",
    (2, 125): "RasterizedCaption",
    (2, 130): "ImageType",
    (2, 131): "ImageOrientation",
    (2, 135): "LanguageIdentifier",
    (2, 184): "JobID",
}

NAMESPACE_PREFIXES = {
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf",
    "http://www.w3.org/XML/1998/namespace": "xml",
    "http://purl.org/dc/elements/1.1/": "dc",
    "http://ns.adobe.com/photoshop/1.0/": "photoshop",
    "http://ns.adobe.com/xap/1.0/": "xmp",
    "http://ns.adobe.com/xap/1.0/mm/": "xmpMM",
    "http://ns.adobe.com/xap/1.0/rights/": "xmpRights",
    "http://ns.adobe.com/exif/1.0/": "exif",
    "http://ns.adobe.com/exif/1.0/aux/": "aux",
    "http://cipa.jp/exif/1.0/": "exifEX",
    "http://iptc.org/std/Iptc4xmpCore/1.0/xmlns/": "Iptc4xmpCore",
    "http://iptc.org/std/Iptc4xmpExt/2008-02-29/": "Iptc4xmpExt",
    "http://ns.useplus.org/ldf/xmp/1.0/": "plus",
    "http://ns.adobe.com/lightroom/1.0/": "lr",
    "http://ns.adobe.com/camera-raw-settings/1.0/": "crs",
    "http://ns.adobe.com/xmp/1.0/DynamicMedia/": "xmpDM",
}

FIELD_TAGS = {
    "source": ["IPTC:ApplicationRecord:Source", "XMP:photoshop:Source"],
    "title": ["IPTC:ApplicationRecord:ObjectName", "XMP:dc:title"],
    "caption": [
        "EXIF:IFD0:ImageDescription",
        "IPTC:ApplicationRecord:CaptionAbstract",
        "XMP:dc:description",
    ],
    "headline": [
        "IPTC:ApplicationRecord:Headline",
        "XMP:photoshop:Headline",
    ],
    "alt_text": ["XMP:Iptc4xmpCore:AltTextAccessibility"],
    "extended_description": ["XMP:Iptc4xmpCore:ExtDescrAccessibility"],
    "keywords": ["IPTC:ApplicationRecord:Keywords", "XMP:dc:subject"],
    "rating": ["XMP:xmp:Rating"],
    "color_label": ["XMP:xmp:Label", "XMP:photoshop:LabelColor"],
    "creator": [
        "EXIF:IFD0:Artist",
        "IPTC:ApplicationRecord:Byline",
        "XMP:dc:creator",
    ],
    "copyright": [
        "EXIF:IFD0:Copyright",
        "IPTC:ApplicationRecord:CopyrightNotice",
        "XMP:dc:rights",
    ],
}


@dataclass(frozen=True)
class FilenameInfo:
    valid: bool
    mode: str
    intake_key: str
    episode_number: int | None
    source_filename: str
    source_basename: str
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "mode": self.mode,
            "intake_key": self.intake_key,
            "episode_number": self.episode_number,
            "source_filename": self.source_filename,
            "source_basename": self.source_basename,
            "error": self.error,
        }


def parse_filename(path: Path, mode: str) -> FilenameInfo:
    """Validate an intake portrait filename or a release JPEG filename."""
    name = path.name
    if path.suffix.lower() not in {".jpg", ".jpeg", ".tif", ".tiff"}:
        return FilenameInfo(
            False, mode, name, None, name, path.stem,
            "Intake file must be JPEG or TIFF",
        )

    match = RELEASE_FILENAME_RE.match(name)
    resolved_mode = mode
    if mode == "auto":
        resolved_mode = "release" if match else "intake"

    if resolved_mode == "intake":
        return FilenameInfo(True, "intake", name, None, name, path.stem)

    if resolved_mode != "release":
        raise ValueError(f"Unknown filename mode: {mode}")

    if not match:
        return FilenameInfo(
            False, "release", name, None, name, path.stem,
            "Release filename must be NNN-original-filename.jpg",
        )

    source_filename = f"{match.group('source')}.{match.group('extension')}"
    return FilenameInfo(
        True, "release", name, int(match.group("episode")),
        source_filename, Path(source_filename).stem,
    )


def _decode(value: Any) -> Any:
    if isinstance(value, bytes):
        for encoding in ("utf-8", "latin-1"):
            try:
                return value.decode(encoding).rstrip("\x00")
            except UnicodeDecodeError:
                continue
        return value.hex()
    if isinstance(value, tuple):
        return [_decode(item) for item in value]
    if isinstance(value, list):
        return [_decode(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _decode(item) for key, item in value.items()}
    if hasattr(value, "numerator") and hasattr(value, "denominator"):
        denominator = value.denominator
        return value.numerator / denominator if denominator else None
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _qname(name: str) -> str:
    if not name.startswith("{"):
        return name
    namespace, local = name[1:].split("}", 1)
    prefix = NAMESPACE_PREFIXES.get(namespace, namespace)
    return f"{prefix}:{local}"


def _xmp_property_value(element: ET.Element) -> Any:
    containers = {
        "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Alt",
        "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Bag",
        "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Seq",
    }
    for child in element:
        if child.tag in containers:
            values = []
            languages = []
            for item in child:
                values.append((item.text or "").strip())
                languages.append(
                    item.attrib.get("{http://www.w3.org/XML/1998/namespace}lang")
                )
            if child.tag.endswith("Alt") and len(values) == 1:
                return values[0]
            if child.tag.endswith("Alt"):
                return [
                    {"language": language, "value": value}
                    for language, value in zip(languages, values)
                ]
            return values

    children = list(element)
    if children:
        grouped: dict[str, list[Any]] = {}
        for child in children:
            grouped.setdefault(_qname(child.tag), []).append(
                _xmp_property_value(child)
            )
        return {
            key: values[0] if len(values) == 1 else values
            for key, values in grouped.items()
        }

    text = (element.text or "").strip()
    attributes = {_qname(key): _decode(value) for key, value in element.attrib.items()}
    if attributes and text:
        return {"attributes": attributes, "text": text}
    if attributes:
        return attributes
    return text


def extract_xmp(raw_xmp: bytes | None) -> dict[str, Any]:
    if not raw_xmp:
        return {}
    try:
        root = ET.fromstring(raw_xmp)
    except ET.ParseError as exc:
        return {"XMP:ParseError": str(exc)}

    description_tag = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description"
    records: dict[str, Any] = {}
    for description in root.iter(description_tag):
        for key, value in description.attrib.items():
            if key.endswith("}about"):
                continue
            records[f"XMP:{_qname(key)}"] = _decode(value)
        for child in description:
            records[f"XMP:{_qname(child.tag)}"] = _xmp_property_value(child)
    return records


def extract_iptc(image: Image.Image) -> dict[str, Any]:
    raw = IptcImagePlugin.getiptcinfo(image) or {}
    records: dict[str, Any] = {}
    for key, value in raw.items():
        if isinstance(key, tuple) and len(key) == 2:
            record, dataset = key
            record_name = "ApplicationRecord" if record == 2 else f"Record{record}"
            dataset_name = IPTC_DATASET_NAMES.get(key, f"Dataset{dataset}")
            tag = f"IPTC:{record_name}:{dataset_name}"
        else:
            tag = f"IPTC:{key}"
        records[tag] = _decode(value)
    return records


def extract_exif(image: Image.Image) -> dict[str, Any]:
    records: dict[str, Any] = {}
    exif = image.getexif()
    for tag_id, value in exif.items():
        tag_name = ExifTags.TAGS.get(tag_id, f"Tag{tag_id}")
        records[f"EXIF:IFD0:{tag_name}"] = _decode(value)

    ifd_specs = [
        ("Exif", getattr(ExifTags.IFD, "Exif", None)),
        ("GPS", getattr(ExifTags.IFD, "GPSInfo", None)),
        ("Interop", getattr(ExifTags.IFD, "Interop", None)),
    ]
    for ifd_name, ifd_id in ifd_specs:
        if ifd_id is None:
            continue
        try:
            values = exif.get_ifd(ifd_id)
        except (KeyError, TypeError, ValueError):
            continue
        tag_names = ExifTags.GPSTAGS if ifd_name == "GPS" else ExifTags.TAGS
        for tag_id, value in values.items():
            tag_name = tag_names.get(tag_id, f"Tag{tag_id}")
            records[f"EXIF:{ifd_name}:{tag_name}"] = _decode(value)
    return records


def _normalize_comparison(field: str, value: Any) -> Any:
    if field != "keywords" and isinstance(value, list) and len(value) == 1:
        value = value[0]
    if field == "rating":
        try:
            return int(value)
        except (TypeError, ValueError):
            return value
    if field == "color_label" and isinstance(value, str):
        return value.casefold()
    if field == "keywords":
        if not isinstance(value, list):
            value = [value]
        return [str(item) for item in value]
    return value


def compare_fields(
    metadata: dict[str, Any], expected: dict[str, Any] | None
) -> dict[str, Any]:
    comparisons: dict[str, Any] = {}
    expected = expected or {}
    for field, tags in FIELD_TAGS.items():
        locations = [
            {"tag": tag, "value": metadata[tag]}
            for tag in tags
            if tag in metadata
        ]
        expected_value = expected.get(field)
        if field not in expected:
            status = "not_tested"
        elif not locations:
            status = "missing"
        else:
            normalized_expected = _normalize_comparison(field, expected_value)
            status = "match"
            for location in locations:
                actual = _normalize_comparison(field, location["value"])
                if actual != normalized_expected:
                    status = "mismatch"
                    break
        comparisons[field] = {
            "expected": expected_value,
            "status": status,
            "locations": locations,
        }
    return comparisons


def inspect_image(
    path: Path,
    filename_mode: str,
    expected_entry: dict[str, Any] | None,
) -> dict[str, Any]:
    filename = parse_filename(path, filename_mode)
    with Image.open(path) as image:
        image.load()
        exif = extract_exif(image)
        iptc = extract_iptc(image)
        xmp = extract_xmp(image.info.get("xmp"))
        icc_profile = image.info.get("icc_profile")
        profile_description = None
        if icc_profile:
            try:
                profile_description = ImageCms.getProfileDescription(
                    ImageCms.ImageCmsProfile(BytesIO(icc_profile))
                ).strip()
            except (OSError, ValueError):
                profile_description = "unreadable"
        bits_per_sample = None
        compression = None
        if image.format == "TIFF":
            bits_per_sample = image.tag_v2.get(258)
            compression = image.tag_v2.get(259)
        image_info = {
            "format": image.format,
            "width": image.width,
            "height": image.height,
            "mode": image.mode,
            "bits_per_sample": bits_per_sample,
            "compression": compression,
            "icc_profile_present": bool(icc_profile),
            "icc_profile_description": profile_description,
        }

    all_metadata = {**exif, **iptc, **xmp}
    expected_fields = (expected_entry or {}).get("fields", expected_entry or {})
    return {
        "path": str(path.resolve()),
        "pilot_id": (expected_entry or {}).get("pilot_id"),
        "filename": filename.as_dict(),
        "image": image_info,
        "fields": compare_fields(all_metadata, expected_fields),
        "metadata": {"exif": exif, "iptc": iptc, "xmp": xmp},
    }


def _markdown(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, (list, dict)):
        text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value)
    return text.replace("|", "\\|").replace("\n", "<br>")


def render_markdown(results: Iterable[dict[str, Any]]) -> str:
    results = list(results)
    lines = [
        "# HPR portrait metadata inspection", "", "## Summary", "",
        "| File | Pilot | Filename mode | Episode | Matched | Problems |",
        "| --- | --- | --- | ---: | ---: | ---: |",
    ]
    for result in results:
        fields = result["fields"].values()
        matched = sum(field["status"] == "match" for field in fields)
        problems = sum(
            field["status"] in {"missing", "mismatch"} for field in fields
        )
        filename = result["filename"]
        lines.append(
            "| {file} | {pilot} | {mode} | {episode} | {matched} | {problems} |".format(
                file=_markdown(Path(result["path"]).name),
                pilot=_markdown(result.get("pilot_id")),
                mode=_markdown(filename["mode"]),
                episode=_markdown(filename["episode_number"]),
                matched=matched,
                problems=problems,
            )
        )

    for result in results:
        lines.extend([
            "", f"## {_markdown(Path(result['path']).name)}", "",
            "| Lightroom field | Expected | Status | Embedded tags and values |",
            "| --- | --- | --- | --- |",
        ])
        for field, comparison in result["fields"].items():
            locations = "<br>".join(
                f"`{_markdown(location['tag'])}` = {_markdown(location['value'])}"
                for location in comparison["locations"]
            ) or "—"
            lines.append(
                f"| {_markdown(field)} | {_markdown(comparison['expected'])} | "
                f"{_markdown(comparison['status'])} | {locations} |"
            )
    return "\n".join(lines) + "\n"


def load_expected(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    files = data.get("files", data)
    if not isinstance(files, dict):
        raise ValueError("Expected-values JSON must contain a 'files' object")
    return files


def has_problems(results: Iterable[dict[str, Any]]) -> bool:
    for result in results:
        if not result["filename"]["valid"]:
            return True
        for field in result["fields"].values():
            if field["status"] in {"missing", "mismatch"}:
                return True
    return False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", nargs="+", type=Path)
    parser.add_argument(
        "--filename-mode", choices=("intake", "release", "auto"), default="intake"
    )
    parser.add_argument("--expected", type=Path)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    expected = load_expected(args.expected)
    results = []
    for path in args.images:
        if not path.is_file():
            raise SystemExit(f"Image not found: {path}")
        results.append(
            inspect_image(path, args.filename_mode, expected.get(path.name))
        )

    payload = {
        "schema_version": "1.0",
        "results": results,
        "problem_count": sum(
            field["status"] in {"missing", "mismatch"}
            for result in results for field in result["fields"].values()
        ),
    }
    markdown = render_markdown(results)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(markdown, encoding="utf-8")
    sys.stdout.write(markdown)
    return 1 if has_problems(results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
