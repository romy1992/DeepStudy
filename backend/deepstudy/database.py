from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

SCHEMA_VERSION = 3
DEFAULT_SETTINGS = {"display_name": "", "theme": "system", "timezone": "Europe/Rome", "ai_mode": "off"}

# M1 owns the foundation tables. M2 adds import jobs without rewriting those contracts.
MIGRATIONS = {
    1: [
        "CREATE TABLE settings (id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL CHECK(json_valid(value)))",
        "CREATE TABLE sources (id TEXT PRIMARY KEY, provider TEXT NOT NULL, locator TEXT NOT NULL, read_only INTEGER NOT NULL DEFAULT 1 CHECK(read_only=1), scope TEXT NOT NULL)",
        "CREATE TABLE materials (id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES sources(id), locator TEXT NOT NULL)",
        "CREATE TABLE material_versions (id TEXT PRIMARY KEY, material_id TEXT NOT NULL REFERENCES materials(id), source_revision TEXT NOT NULL, sha256 TEXT NOT NULL CHECK(length(sha256)=64), kind TEXT NOT NULL, extraction_state TEXT NOT NULL, UNIQUE(material_id, sha256))",
        "CREATE TABLE chunks (id TEXT PRIMARY KEY, version_id TEXT NOT NULL REFERENCES material_versions(id), locator TEXT NOT NULL, text TEXT NOT NULL, quality TEXT NOT NULL, index_version TEXT NOT NULL)",
        "CREATE TABLE objectives (id TEXT PRIMARY KEY, curriculum_version TEXT NOT NULL, title TEXT NOT NULL)",
        "CREATE TABLE prerequisites (objective_id TEXT NOT NULL REFERENCES objectives(id), prerequisite_id TEXT NOT NULL REFERENCES objectives(id), PRIMARY KEY(objective_id, prerequisite_id), CHECK(objective_id <> prerequisite_id))",
        "CREATE TRIGGER prerequisite_cycle BEFORE INSERT ON prerequisites WHEN EXISTS (WITH RECURSIVE ancestors(id) AS (SELECT NEW.prerequisite_id UNION SELECT p.prerequisite_id FROM prerequisites p JOIN ancestors a ON p.objective_id=a.id) SELECT 1 FROM ancestors WHERE id=NEW.objective_id) BEGIN SELECT RAISE(ABORT,'cyclic prerequisite'); END",
        "CREATE TRIGGER prerequisite_no_update BEFORE UPDATE ON prerequisites BEGIN SELECT RAISE(ABORT,'replace edge instead'); END",
        "CREATE TABLE exam_blueprints (id TEXT PRIMARY KEY, provider TEXT NOT NULL, code TEXT NOT NULL, version TEXT NOT NULL, checked_at TEXT NOT NULL, source TEXT NOT NULL, status TEXT NOT NULL)",
        "CREATE TABLE objective_evidence (id TEXT PRIMARY KEY, objective_id TEXT NOT NULL REFERENCES objectives(id), version_id TEXT NOT NULL REFERENCES material_versions(id), locator TEXT NOT NULL, coverage TEXT NOT NULL, review TEXT NOT NULL)",
        "CREATE TABLE question_versions (id TEXT PRIMARY KEY, objective_id TEXT NOT NULL REFERENCES objectives(id), prompt TEXT NOT NULL, options TEXT NOT NULL, solution TEXT NOT NULL, rationale TEXT NOT NULL, sources TEXT NOT NULL, review TEXT NOT NULL)",
        "CREATE TABLE attempts (id TEXT PRIMARY KEY, device_id TEXT NOT NULL, question_version_id TEXT NOT NULL REFERENCES question_versions(id), answer TEXT NOT NULL, score REAL NOT NULL, timestamp TEXT NOT NULL)",
        "CREATE TABLE review_states (objective_id TEXT PRIMARY KEY REFERENCES objectives(id), algorithm_version TEXT NOT NULL, due_at TEXT NOT NULL)",
        "CREATE TABLE note_versions (id TEXT PRIMARY KEY, note_id TEXT NOT NULL, base_version TEXT REFERENCES note_versions(id), content TEXT NOT NULL, device_id TEXT NOT NULL)",
        "CREATE TABLE ai_usage (job_id TEXT PRIMARY KEY, model TEXT NOT NULL, tokens INTEGER NOT NULL, estimated_cost REAL NOT NULL, actual_cost REAL, policy TEXT NOT NULL, status TEXT NOT NULL)",
        "CREATE TABLE sync_events (id TEXT PRIMARY KEY, entity_id TEXT NOT NULL, base_revision TEXT, payload_version INTEGER NOT NULL, payload TEXT NOT NULL, ack_state TEXT NOT NULL)",
    ] + [f"CREATE TRIGGER {table}_no_{op.lower()} BEFORE {op} ON {table} BEGIN SELECT RAISE(ABORT,'immutable record'); END"
         for table in ("material_versions", "question_versions", "attempts", "note_versions") for op in ("UPDATE", "DELETE")],
    2: ["ALTER TABLE settings ADD COLUMN revision INTEGER NOT NULL DEFAULT 0"],
    3: [
        """CREATE TABLE import_jobs (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL REFERENCES sources(id),
            idempotency_key TEXT NOT NULL,
            phase TEXT NOT NULL,
            state TEXT NOT NULL CHECK(state IN ('running','interrupted','completed','failed')),
            progress_done INTEGER NOT NULL DEFAULT 0 CHECK(progress_done >= 0),
            progress_total INTEGER NOT NULL DEFAULT 0 CHECK(progress_total >= 0),
            interrupt_requested INTEGER NOT NULL DEFAULT 0 CHECK(interrupt_requested IN (0,1)),
            error_code TEXT,
            error_message TEXT,
            report TEXT,
            snapshot TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(source_id, idempotency_key)
        )""",
        """CREATE TABLE import_job_items (
            id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL REFERENCES import_jobs(id),
            relative_path TEXT NOT NULL,
            state TEXT NOT NULL CHECK(state IN ('pending','done','error','excluded')),
            sha256 TEXT CHECK(sha256 IS NULL OR length(sha256)=64),
            material_id TEXT REFERENCES materials(id),
            version_id TEXT REFERENCES material_versions(id),
            error_code TEXT,
            error_message TEXT,
            byte_length INTEGER,
            outcome TEXT,
            retryable INTEGER NOT NULL DEFAULT 0 CHECK(retryable IN (0,1)),
            detail TEXT,
            UNIQUE(job_id, relative_path)
        )""",
        "CREATE UNIQUE INDEX materials_source_locator ON materials(source_id, locator)",
        "CREATE INDEX material_versions_sha ON material_versions(sha256)",
        "CREATE INDEX import_items_job_state ON import_job_items(job_id, state)",
    ],
}


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()


def connect(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path, timeout=10, factory=ClosingConnection)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=10000")
    return db


def backup_database(source: Path, destination: Path):
    with connect(source) as src, connect(destination) as dst:
        src.backup(dst)


def migrate(path: Path, target: int = SCHEMA_VERSION):
    path.parent.mkdir(parents=True, exist_ok=True)
    db = connect(path)
    try:
        current = db.execute("PRAGMA user_version").fetchone()[0]
        if current > target:
            raise ValueError("Schema più recente dell'applicazione: nessun downgrade automatico.")
        if current and current < target:
            backups = path.parent / "backups"
            backups.mkdir(exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            backup_database(path, backups / f"pre-migration-v{current}-{stamp}.db")
        db.execute("BEGIN IMMEDIATE")
        for version in range(current + 1, target + 1):
            for statement in MIGRATIONS[version]:
                db.execute(statement)
            if version == 1:
                db.execute("INSERT INTO settings(id,value) VALUES(1,?)", (json.dumps(DEFAULT_SETTINGS),))
            db.execute(f"PRAGMA user_version={version}")
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("Riferimenti non validi dopo la migrazione.")
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def read_settings(path: Path):
    with connect(path) as db:
        row = db.execute("SELECT value,revision FROM settings WHERE id=1").fetchone()
        return {**json.loads(row["value"]), "revision": row["revision"]}


def save_settings(path: Path, value: dict, expected_revision: int):
    with connect(path) as db:
        result = db.execute("UPDATE settings SET value=?,revision=revision+1 WHERE id=1 AND revision=?", (json.dumps(value), expected_revision))
        if result.rowcount != 1:
            raise ValueError("Impostazioni modificate in un'altra finestra. Ricarica prima di salvare.")
    return read_settings(path)
