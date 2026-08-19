# Lightroom JPEG metadata contract

Lightroom Classic remains authoritative for photographic edits, source-project
metadata, and rights metadata. HPR Umbrella ingests exported JPEGs without
modifying the Lightroom originals.

## Intake identity and episode order

Episode order is an editorial decision made after the visual-and-audio masters
can be reviewed. It is not part of portrait intake.

- Preserve the original Lightroom export filename at intake.
- Combine the source-project code and original filename to form the intake key.
- Assign an immutable Registry `portrait_id` during ingest.
- Leave `episode_number` empty until the completed videos are sequenced and the
  sequence is locked.
- Apply `NNN-` prefixes only to release-stage masters and publication records.

The inspector therefore has separate `intake` and `release` filename modes.
Release mode accepts three or more digits so episode numbers above 999 remain
possible.

## Required production fields

| Lightroom field | Production use | Rule |
| --- | --- | --- |
| IPTC Source | Canonical source-project code | Required; use a stable ASCII code no longer than 32 characters |
| Creator | Rights and attribution | Required |
| Copyright | Rights | Required |

Recommended source-project codes for the current three archive groups include
`NYChildren`, `10000`, and `Infinity`. The Registry stores the corresponding
human-readable display names separately.

The 32-character restriction avoids disagreement between the legacy IPTC IIM
Source value and the XMP Source value. In the pilot, XMP preserved a longer
project name while the legacy IPTC value stopped after 32 characters.

## Optional fields to preserve

| Lightroom field | Use |
| --- | --- |
| Title | Human-readable portrait title when one exists |
| Caption | Source-photo description and possible publication copy input |
| Headline | Preserve when already used; not required because it overlaps Title |
| Alt Text | Accessibility source text |
| Extended Description | Additional accessibility context when needed |
| Keywords | Archive discovery and source context |

Lightroom star ratings and color labels survive export, but they are not HPR
candidate ratings. Visual, audio, and pair ratings belong in the Registry and
remain separate from one another.

## Verified JPEG mappings

| Lightroom field | Embedded JPEG locations observed in the pilot |
| --- | --- |
| IPTC Source | `IPTC:ApplicationRecord:Source`; `XMP:photoshop:Source` |
| Title | `IPTC:ApplicationRecord:ObjectName`; `XMP:dc:title` |
| Caption | `EXIF:IFD0:ImageDescription`; `IPTC:ApplicationRecord:CaptionAbstract`; `XMP:dc:description` |
| Headline | `IPTC:ApplicationRecord:Headline`; `XMP:photoshop:Headline` |
| Alt Text | `XMP:Iptc4xmpCore:AltTextAccessibility` |
| Extended Description | `XMP:Iptc4xmpCore:ExtDescrAccessibility` |
| Keywords | `IPTC:ApplicationRecord:Keywords`; `XMP:dc:subject` |
| Star Rating | `XMP:xmp:Rating` |
| Color Label | `XMP:xmp:Label`; `XMP:photoshop:LabelColor` |
| Creator | `EXIF:IFD0:Artist`; `IPTC:ApplicationRecord:Byline`; `XMP:dc:creator` |
| Copyright | `EXIF:IFD0:Copyright`; `IPTC:ApplicationRecord:CopyrightNotice`; `XMP:dc:rights` |

The production ingester should retain the complete extracted EXIF, IPTC, and
XMP record in provenance JSON while promoting only the required operational
values into Registry columns.
