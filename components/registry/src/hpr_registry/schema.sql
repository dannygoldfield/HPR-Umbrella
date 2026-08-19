PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_projects (
    source_project_id TEXT PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    CHECK (length(code) BETWEEN 1 AND 32)
);

CREATE TABLE IF NOT EXISTS portraits (
    portrait_id TEXT PRIMARY KEY,
    source_project_id TEXT NOT NULL REFERENCES source_projects(source_project_id),
    intake_filename TEXT NOT NULL,
    original_base_filename TEXT NOT NULL,
    portrait_group TEXT NOT NULL CHECK (
        portrait_group IN ('age_100_plus', 'age_12_or_younger', 'number_prop')
    ),
    current_revision_number INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    UNIQUE (source_project_id, intake_filename)
);

CREATE TABLE IF NOT EXISTS portrait_revisions (
    revision_id TEXT PRIMARY KEY,
    portrait_id TEXT NOT NULL REFERENCES portraits(portrait_id),
    revision_number INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    width INTEGER,
    height INTEGER,
    metadata_manifest_path TEXT NOT NULL,
    source_value TEXT,
    title TEXT,
    caption TEXT,
    headline TEXT,
    alt_text TEXT,
    extended_description TEXT,
    keywords_json TEXT NOT NULL DEFAULT '[]',
    lightroom_rating INTEGER,
    lightroom_color_label TEXT,
    creator TEXT,
    copyright TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (portrait_id, revision_number),
    UNIQUE (portrait_id, sha256),
    CHECK (lightroom_rating IS NULL OR lightroom_rating BETWEEN 0 AND 5)
);

CREATE TABLE IF NOT EXISTS visual_candidates (
    visual_id TEXT PRIMARY KEY,
    portrait_id TEXT NOT NULL REFERENCES portraits(portrait_id),
    revision_id TEXT NOT NULL REFERENCES portrait_revisions(revision_id),
    motion_recipe_id TEXT NOT NULL,
    experiment_id TEXT NOT NULL DEFAULT 'unspecified',
    parent_visual_id TEXT REFERENCES visual_candidates(visual_id),
    duration_sec REAL NOT NULL,
    seed INTEGER NOT NULL,
    generator_version TEXT NOT NULL,
    media_path TEXT,
    manifest_path TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'planned',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audio_candidates (
    audio_id TEXT PRIMARY KEY,
    recipe_id TEXT NOT NULL,
    duration_sec REAL NOT NULL,
    seed INTEGER NOT NULL,
    generator_version TEXT NOT NULL,
    media_path TEXT,
    manifest_path TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'planned',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pair_candidates (
    pair_id TEXT PRIMARY KEY,
    portrait_id TEXT NOT NULL REFERENCES portraits(portrait_id),
    visual_id TEXT NOT NULL REFERENCES visual_candidates(visual_id),
    audio_id TEXT NOT NULL REFERENCES audio_candidates(audio_id),
    media_path TEXT,
    manifest_path TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'planned',
    created_at TEXT NOT NULL,
    UNIQUE (visual_id, audio_id)
);

CREATE TABLE IF NOT EXISTS candidate_reviews (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_kind TEXT NOT NULL CHECK (subject_kind IN ('visual', 'audio', 'pair')),
    subject_id TEXT NOT NULL,
    rating INTEGER CHECK (rating IS NULL OR rating BETWEEN 1 AND 5),
    rejected INTEGER NOT NULL DEFAULT 0 CHECK (rejected IN (0, 1)),
    selected INTEGER NOT NULL DEFAULT 0 CHECK (selected IN (0, 1)),
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS candidate_reviews_subject
ON candidate_reviews(subject_kind, subject_id, review_id);

CREATE TABLE IF NOT EXISTS final_masters (
    master_id TEXT PRIMARY KEY,
    portrait_id TEXT NOT NULL REFERENCES portraits(portrait_id),
    revision_id TEXT NOT NULL REFERENCES portrait_revisions(revision_id),
    visual_id TEXT REFERENCES visual_candidates(visual_id),
    audio_id TEXT REFERENCES audio_candidates(audio_id),
    pair_id TEXT REFERENCES pair_candidates(pair_id),
    media_path TEXT NOT NULL,
    manifest_path TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'approved',
    approved_at TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (portrait_id, master_id)
);

CREATE TABLE IF NOT EXISTS sequence_versions (
    sequence_id TEXT PRIMARY KEY,
    version_number INTEGER NOT NULL UNIQUE,
    name TEXT NOT NULL,
    expected_count INTEGER NOT NULL DEFAULT 120 CHECK (expected_count > 0),
    status TEXT NOT NULL DEFAULT 'draft' CHECK (
        status IN ('draft', 'locked', 'superseded')
    ),
    created_at TEXT NOT NULL,
    locked_at TEXT
);

CREATE TABLE IF NOT EXISTS sequence_entries (
    sequence_id TEXT NOT NULL REFERENCES sequence_versions(sequence_id) ON DELETE CASCADE,
    position INTEGER NOT NULL CHECK (position > 0),
    master_id TEXT NOT NULL REFERENCES final_masters(master_id),
    portrait_id TEXT NOT NULL REFERENCES portraits(portrait_id),
    PRIMARY KEY (sequence_id, position),
    UNIQUE (sequence_id, master_id),
    UNIQUE (sequence_id, portrait_id)
);

CREATE TABLE IF NOT EXISTS publication_records (
    publication_id TEXT PRIMARY KEY,
    sequence_id TEXT NOT NULL REFERENCES sequence_versions(sequence_id),
    episode_number INTEGER NOT NULL CHECK (episode_number > 0),
    master_id TEXT NOT NULL REFERENCES final_masters(master_id),
    status TEXT NOT NULL DEFAULT 'not_scheduled',
    scheduled_at TEXT,
    published_at TEXT,
    platform TEXT,
    external_id TEXT,
    response_json TEXT,
    UNIQUE (sequence_id, episode_number)
);
