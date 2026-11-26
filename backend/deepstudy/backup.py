from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import sqlite3
import tempfile
import zipfile

from .database import SCHEMA_VERSION, backup_database, connect, migrate

MAX_ARCHIVE_BYTES = 64 * 1024 * 1024


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def export_profile(profile: Path) -> bytes:
    with tempfile.TemporaryDirectory() as directory:
        snapshot = Path(directory) / "deepstudy.db"
        backup_database(profile / "deepstudy.db", snapshot)
        files = {"deepstudy.db": snapshot.read_bytes()}
        derived = profile / "derived"
        if derived.exists():
            for path in derived.rglob("*"):
                if path.is_symlink() or path.is_junction():
                    raise ValueError("Collegamenti nei derivati non supportati.")
                if path.is_file():
                    files[path.relative_to(profile).as_posix()] = path.read_bytes()
        if sum(map(len, files.values())) > MAX_ARCHIVE_BYTES:
            raise ValueError("Backup oltre il limite M1 di 64 MiB.")
        manifest = {"format": "deepstudy-backup", "version": 1, "schema_version": SCHEMA_VERSION,
                    "files": {name: {"sha256": digest(data), "bytes": len(data)} for name, data in files.items()}}
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, data in files.items():
                archive.writestr(name, data)
            archive.writestr("manifest.json", json.dumps(manifest))
        return output.getvalue()


def schema_signature(db):
    return sorted(tuple(row) for row in db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"))


def is_empty_profile(profile: Path) -> bool:
    with connect(profile / "deepstudy.db") as db:
        settings = db.execute("SELECT revision FROM settings").fetchone()
        if settings[0] != 0:
            return False
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name<>'settings'")]
        if any(db.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0] for name in tables):
            return False
    return not any((profile / "derived").rglob("*"))


def restore_profile(profile: Path, payload: bytes):
    if not is_empty_profile(profile):
        raise ValueError("Ripristino consentito solo su un profilo vuoto. Avvia un nuovo profilo.")
    if len(payload) > MAX_ARCHIVE_BYTES:
        raise ValueError("Archivio troppo grande.")
    # Staging is on the same volume: replace is atomic and failed validation touches no live data.
    with tempfile.TemporaryDirectory(prefix="restore-", dir=profile) as directory:
        staging = Path(directory)
        try:
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                entries = archive.infolist()
                names = [e.filename for e in entries]
                if len(names) != len(set(names)) or len(names) > 10000 or sum(e.file_size for e in entries) > MAX_ARCHIVE_BYTES:
                    raise ValueError("Archivio duplicato o troppo grande.")
                manifest = json.loads(archive.read("manifest.json"))
                if (manifest["format"], manifest["version"], manifest["schema_version"]) != ("deepstudy-backup", 1, SCHEMA_VERSION):
                    raise ValueError("Formato o versione backup non supportata.")
                expected = manifest["files"]
                if set(names) != set(expected) | {"manifest.json"} or "deepstudy.db" not in expected:
                    raise ValueError("Manifest incompleto.")
                for name, metadata in expected.items():
                    parts = PurePosixPath(name).parts
                    if name != "deepstudy.db" and (len(parts) < 2 or parts[0] != "derived"):
                        raise ValueError("Percorso non consentito.")
                    if any(p in (".", "..", "") or ":" in p or "\\" in p or p.endswith((" ", ".")) for p in parts):
                        raise ValueError("Percorso non sicuro.")
                    target = staging.joinpath(*parts)
                    if not target.resolve().is_relative_to(staging.resolve()):
                        raise ValueError("Percorso esterno al profilo.")
                    content = archive.read(name)
                    if len(content) != metadata["bytes"] or digest(content) != metadata["sha256"]:
                        raise ValueError("Integrità backup non valida.")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(content)
            candidate = staging / "deepstudy.db"
            expected_db = staging / "expected.db"
            migrate(expected_db)
            with connect(candidate) as db, connect(expected_db) as reference:
                db.execute("PRAGMA trusted_schema=OFF")
                if db.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION or schema_signature(db) != schema_signature(reference):
                    raise ValueError("Schema backup non riconosciuto.")
                if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok" or db.execute("PRAGMA foreign_key_check").fetchall():
                    raise ValueError("Database backup danneggiato.")
                from .models import Settings
                rows = db.execute("SELECT value,revision FROM settings WHERE id=1").fetchall()
                if len(rows) != 1:
                    raise ValueError("Impostazioni mancanti.")
                Settings(**json.loads(rows[0][0]), revision=rows[0][1])
        except (KeyError, TypeError, zipfile.BadZipFile, sqlite3.Error, json.JSONDecodeError) as exc:
            raise ValueError("Archivio non valido o danneggiato.") from exc
        derived = profile / "derived"
        staged_derived = staging / "derived"
        if staged_derived.exists():
            if derived.exists():
                derived.rmdir()  # empty profile only
            os.replace(staged_derived, derived)
        try:
            os.replace(candidate, profile / "deepstudy.db")
        except OSError:
            # Move back the staged data on failure, keeping the empty profile intact.
            if derived.exists():
                os.replace(derived, staging / "derived-rollback")
            raise
