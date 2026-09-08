# Portrait metadata inspector

`inspect_metadata.py` validates HPR JPEG and TIFF intake filenames, extracts EXIF, IPTC IIM,
and XMP metadata, compares Lightroom test values, and writes both Markdown and
JSON reports.

The tool deliberately separates two filename stages:

- `intake`: accepts JPEG or TIFF, preserves the original exported filename, and does not assign an
  episode number.
- `release`: requires `NNN-original-filename.jpg`; the numeric prefix may be
  three or more digits, so future episode numbers above 999 remain valid.

## Install

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r tools/inspect_metadata/requirements.txt
```

## Run

```bash
python3 tools/inspect_metadata/inspect_metadata.py \
  --filename-mode intake \
  --expected workspace/metadata-pilot/expected.json \
  --json-output workspace/metadata-pilot/metadata-report.json \
  --markdown-output workspace/metadata-pilot/metadata-report.md \
  /path/to/portrait-a.jpg /path/to/portrait-b.jpg /path/to/portrait-c.jpg
```

The expected-values file is keyed by exported filename:

```json
{
  "files": {
    "portrait-a.jpg": {
      "pilot_id": "A",
      "fields": {
        "source": "HPR-TEST-A-SOURCE | Project Name",
        "title": "HPR-TEST-A-TITLE",
        "caption": "HPR-TEST-A-CAPTION",
        "headline": "HPR-TEST-A-HEADLINE",
        "alt_text": "HPR-TEST-A-ALT-TEXT",
        "extended_description": "HPR-TEST-A-EXTENDED-DESCRIPTION",
        "keywords": ["HPR-TEST-A-KEYWORD-1", "HPR-TEST-A-KEYWORD-2"],
        "rating": 1,
        "color_label": "Red",
        "creator": "HPR-TEST-A-CREATOR",
        "copyright": "HPR-TEST-A-COPYRIGHT"
      }
    }
  }
}
```

The generated JSON contains the complete extracted EXIF, IPTC, and XMP
records. The Markdown report focuses on the Lightroom fields under test and
their exact embedded tag locations.

## Test

```bash
python3 -m unittest discover -s tools/inspect_metadata/tests -v
```
