# HPR Registry

The HPR Registry is the authoritative operational SQLite database for portrait
revisions, generated candidates, reviews, completed masters, deferred sequence
versions, and publication records.

An intake portrait has a permanent `portrait_id` but no episode number. The
episode number is created only when a complete sequence of approved masters is
locked.

## Initialize and ingest the metadata pilot

```bash
hpr-registry init --db workspace/registry/hpr.sqlite3

hpr-registry ingest-metadata-report \
  --db workspace/registry/hpr.sqlite3 \
  --report workspace/metadata-pilot/metadata-report.json \
  --intake-config workspace/metadata-pilot/expected.json \
  --manifest-root workspace/registry/manifests/portraits
```

Running the same intake again is idempotent. A changed JPEG with the same
source-project code and filename creates the next portrait revision without
discarding earlier candidates or decisions.

## Deferred sequencing

After approved final masters exist, create a draft sequence and supply an
ordered text or JSON file of master IDs:

```bash
hpr-registry create-sequence \
  --db workspace/registry/hpr.sqlite3 \
  --name "HPR Archive sequence" \
  --expected-count 120

hpr-registry set-sequence-order \
  --db workspace/registry/hpr.sqlite3 \
  --sequence-id SEQ-0001 \
  --master-ids workspace/registry/sequence-v1.txt
```

The draft may be reordered repeatedly. Locking it validates that all 120
approved masters are present, freezes their positions as episode numbers, and
creates the publication ledger rows.
