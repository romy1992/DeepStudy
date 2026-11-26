"""Catalogo M2: scansione, hash, deduplica, parser e job riprendibili. Nessuna esecuzione."""
from __future__ import annotations

import errno
import hashlib
import json
import os
import stat
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .database import connect
from .parsers import INDEX_VERSION, ParseResult, ocr_engine, parse_image, parse_notebook, parse_pdf, parse_python, parse_table, parse_text

MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_FILES = 20_000
ALLOWLIST = {
    ".py": "python",
    ".ipynb": "notebook",
    ".md": "markdown",
    ".txt": "text",
    ".csv": "csv",
    ".tsv": "tsv",
    ".pdf": "pdf",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
}
EXCLUDED_DIRECTORIES = {"__pycache__", ".ipynb_checkpoints", ".git", "node_modules", ".venv", "venv"}
EXCLUDED_SUFFIXES = {".pyc", ".pkl", ".pickle", ".keras", ".h5", ".log", ".zip", ".db"}

_workers: dict[str, threading.Thread] = {}
_workers_lock = threading.Lock()
before_item_hook = None


class SimulatedCrash(BaseException):
    """Interruzione di processo usata solo dai test di ripresa."""


class CatalogError(ValueError):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code


class _Symlink(OSError):
    pass


class _NotRegular(OSError):
    pass


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def engine_name() -> str:
    return "tesseract" if ocr_engine() else "unavailable"


def recover_interrupted_jobs(db_path: Path):
    with connect(db_path) as db:
        db.execute(
            "UPDATE import_jobs SET state='interrupted', phase='interrupted', interrupt_requested=0, updated_at=? WHERE state='running'",
            (utcnow(),),
        )


def authorize_folder(locator: str, repo_root: Path, profile: Path) -> Path:
    raw = Path(locator)
    if not raw.is_absolute():
        raise CatalogError(400, "import_rejected", "Indica il percorso assoluto della cartella autorizzata.")
    if not raw.exists() or not raw.is_dir():
        raise CatalogError(400, "import_rejected", "Cartella non trovata oppure non utilizzabile.")
    folder = raw.resolve()
    originals = (repo_root / "docs" / "originali-v0.1").resolve()
    for blocked in (profile.resolve(), originals):
        if folder == blocked or folder.is_relative_to(blocked) or blocked.is_relative_to(folder):
            raise CatalogError(400, "import_rejected", "Questa cartella include il profilo dell'app o la documentazione originale.")
    return folder


def _open_regular(path: Path):
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        if exc.errno in (getattr(errno, "ELOOP", -1), getattr(errno, "EMLINK", -1)):
            raise _Symlink from exc
        raise
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise _NotRegular
        return descriptor
    except Exception:
        os.close(descriptor)
        raise


def _hash_file(path: Path) -> tuple[str, int]:
    descriptor = _open_regular(path)
    digest = hashlib.sha256()
    size = 0
    try:
        while True:
            block = os.read(descriptor, 1024 * 1024)
            if not block:
                break
            size += len(block)
            digest.update(block)
    finally:
        os.close(descriptor)
    return digest.hexdigest(), size


def _read_file(path: Path) -> bytes:
    descriptor = _open_regular(path)
    chunks: list[bytes] = []
    try:
        while True:
            block = os.read(descriptor, 1024 * 1024)
            if not block:
                break
            chunks.append(block)
    finally:
        os.close(descriptor)
    return b"".join(chunks)


def _decode(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Il file non è testo UTF-8.") from exc


def _iter_paths(root: Path):
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(name for name in dirnames if name not in EXCLUDED_DIRECTORIES and not Path(directory, name).is_symlink())
        for name in sorted(filenames):
            yield Path(directory, name)


def _job_row(db_path: Path, job_id: str):
    with connect(db_path) as db:
        row = db.execute(
            """SELECT j.*, s.locator FROM import_jobs j JOIN sources s ON s.id=j.source_id WHERE j.id=?""",
            (job_id,),
        ).fetchone()
    if not row:
        raise CatalogError(404, "job_not_found", "Importazione inesistente.")
    return row


def _dump_job(row) -> dict:
    report = json.loads(row["report"]) if row["report"] else None
    return {
        "id": row["id"],
        "source_id": row["source_id"],
        "locator": row["locator"],
        "state": row["state"],
        "phase": row["phase"],
        "progress_done": row["progress_done"],
        "progress_total": row["progress_total"],
        "error_code": row["error_code"],
        "error_message": row["error_message"],
        "can_resume": row["state"] == "interrupted",
        "retryable": row["state"] == "interrupted",
        "report": report,
    }


def get_job(db_path: Path, job_id: str) -> dict:
    return _dump_job(_job_row(db_path, job_id))


def _worker_alive(job_id: str) -> bool:
    with _workers_lock:
        thread = _workers.get(job_id)
        return bool(thread and thread.is_alive())


def start_worker(profile: Path, job_id: str):
    def target():
        try:
            run_job(profile, job_id)
        except SimulatedCrash:
            return
        finally:
            with _workers_lock:
                current = _workers.get(job_id)
                if current is threading.current_thread():
                    _workers.pop(job_id, None)

    with _workers_lock:
        current = _workers.get(job_id)
        if current and current.is_alive():
            return
        thread = threading.Thread(target=target, name=f"import-{job_id[:8]}", daemon=True)
        _workers[job_id] = thread
        thread.start()


def create_import(profile: Path, repo_root: Path, locator: str, idempotency_key: str) -> dict:
    folder = authorize_folder(locator, repo_root, profile)
    db_path = profile / "deepstudy.db"
    source_id = uuid.uuid5(uuid.NAMESPACE_URL, f"local-folder:{folder}").hex
    scope = json.dumps({"formats": sorted(ALLOWLIST), "read_only": True}, ensure_ascii=False)
    now = utcnow()
    with connect(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        existing_source = db.execute(
            "SELECT id FROM sources WHERE provider='local-folder' AND locator=?",
            (str(folder),),
        ).fetchone()
        if not existing_source:
            db.execute(
                "INSERT INTO sources(id, provider, locator, read_only, scope) VALUES(?,?,?,?,?)",
                (source_id, "local-folder", str(folder), 1, scope),
            )
        else:
            source_id = existing_source["id"]
        existing = db.execute(
            "SELECT id, state FROM import_jobs WHERE source_id=? AND idempotency_key=?",
            (source_id, idempotency_key),
        ).fetchone()
        if existing:
            job_id = existing["id"]
            autostart = existing["state"] == "running" and not _worker_alive(job_id)
        else:
            job_id = uuid.uuid4().hex
            db.execute(
                """INSERT INTO import_jobs(id, source_id, idempotency_key, phase, state, progress_done, progress_total,
                   interrupt_requested, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (job_id, source_id, idempotency_key, "scanning", "running", 0, 0, 0, now, now),
            )
            autostart = True
    if autostart:
        start_worker(profile, job_id)
    return get_job(db_path, job_id)


def request_interrupt(db_path: Path, job_id: str) -> dict:
    with connect(db_path) as db:
        row = db.execute("SELECT state FROM import_jobs WHERE id=?", (job_id,)).fetchone()
        if not row:
            raise CatalogError(404, "job_not_found", "Importazione inesistente.")
        if row["state"] in ("completed", "failed"):
            raise CatalogError(409, "job_state", "Questa importazione è già conclusa.")
        db.execute(
            "UPDATE import_jobs SET interrupt_requested=1, updated_at=? WHERE id=? AND state='running'",
            (utcnow(), job_id),
        )
    return get_job(db_path, job_id)


def resume_job(profile: Path, job_id: str) -> dict:
    db_path = profile / "deepstudy.db"
    with connect(db_path) as db:
        row = db.execute("SELECT state FROM import_jobs WHERE id=?", (job_id,)).fetchone()
        if not row:
            raise CatalogError(404, "job_not_found", "Importazione inesistente.")
        if row["state"] != "interrupted":
            raise CatalogError(409, "job_state", "Si può riprendere solo un'importazione interrotta.")
        if _worker_alive(job_id):
            raise CatalogError(409, "job_state", "Importazione già in corso.")
        db.execute(
            """UPDATE import_jobs SET state='running', phase='scanning', interrupt_requested=0, error_code=NULL,
               error_message=NULL, updated_at=? WHERE id=?""",
            (utcnow(), job_id),
        )
    start_worker(profile, job_id)
    return get_job(db_path, job_id)


def wait_for_job(db_path: Path, job_id: str, timeout: float = 10) -> dict:
    import time
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = get_job(db_path, job_id)
        if job["state"] in ("completed", "failed", "interrupted"):
            with _workers_lock:
                thread = _workers.get(job_id)
            if thread:
                thread.join(timeout=1)
            return job
        time.sleep(0.02)
    raise TimeoutError("Importazione non conclusa nel tempo previsto.")


def _update_job(db_path: Path, job_id: str, **fields):
    fields["updated_at"] = utcnow()
    assignments = ", ".join(f"{key}=?" for key in fields)
    with connect(db_path) as db:
        db.execute(f"UPDATE import_jobs SET {assignments} WHERE id=?", (*fields.values(), job_id))


def _stop_requested(db_path: Path, job_id: str) -> bool:
    with connect(db_path) as db:
        row = db.execute("SELECT interrupt_requested FROM import_jobs WHERE id=?", (job_id,)).fetchone()
    return bool(row and row["interrupt_requested"])


def _mark_interrupted(db_path: Path, job_id: str):
    _update_job(db_path, job_id, state="interrupted", phase="interrupted", interrupt_requested=0)


def _fail_job(db_path: Path, job_id: str, code: str, message: str):
    report = {"errors": [{"path": "", "code": code, "message": message, "retryable": False}], "original_hashes_unchanged": code != "originals_modified"}
    _update_job(db_path, job_id, state="failed", phase="failed", error_code=code, error_message=message, report=json.dumps(report, ensure_ascii=False))


def _scan(profile: Path, job_id: str, root: Path) -> str:
    db_path = profile / "deepstudy.db"
    with connect(db_path) as db:
        if db.execute("SELECT snapshot FROM import_jobs WHERE id=?", (job_id,)).fetchone()["snapshot"]:
            return "ready"
        known = {row["relative_path"] for row in db.execute("SELECT relative_path FROM import_job_items WHERE job_id=?", (job_id,))}
    seen = set(known)
    for path in _iter_paths(root):
        if _stop_requested(db_path, job_id):
            _mark_interrupted(db_path, job_id)
            return "interrupted"
        if len(seen) >= MAX_FILES:
            _fail_job(db_path, job_id, "too_many_files", f"La cartella supera il limite M2 di {MAX_FILES} file.")
            return "failed"
        relative = path.relative_to(root).as_posix()
        if relative in seen or ".." in path.relative_to(root).parts:
            continue
        seen.add(relative)
        suffix = path.suffix.lower()
        state, outcome, code, message, digest, size, retryable = "pending", None, None, None, None, None, 0
        if path.is_symlink():
            state, outcome, code, message = "excluded", "excluded", "symlink", "Collegamento non seguito."
        elif suffix in EXCLUDED_SUFFIXES or suffix not in ALLOWLIST:
            state, outcome, code, message = "excluded", "excluded", "outside_allowlist", "Formato escluso dal catalogo didattico."
        else:
            try:
                digest, size = _hash_file(path)
            except _Symlink:
                state, outcome, code, message = "excluded", "excluded", "symlink", "Collegamento non seguito."
            except (PermissionError, OSError):
                state, outcome, code, message, retryable = "error", "error", "unreadable", "File illeggibile. L'originale non è stato modificato.", 1
            else:
                if size > MAX_FILE_BYTES:
                    state, outcome, code, message, retryable = "error", "error", "file_too_large", "File oltre il limite M2 di 32 MiB.", 1
        with connect(db_path) as db:
            db.execute(
                """INSERT INTO import_job_items(id, job_id, relative_path, state, sha256, error_code, error_message, byte_length, outcome, retryable)
                   VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (uuid.uuid4().hex, job_id, relative, state, digest, code, message, size, outcome, retryable),
            )
    with connect(db_path) as db:
        rows = db.execute("SELECT relative_path, sha256, byte_length FROM import_job_items WHERE job_id=? AND sha256 IS NOT NULL ORDER BY relative_path", (job_id,)).fetchall()
        total = db.execute("SELECT count(*) FROM import_job_items WHERE job_id=? AND state IN ('pending','done','error')", (job_id,)).fetchone()[0]
        done = db.execute("SELECT count(*) FROM import_job_items WHERE job_id=? AND state IN ('done','error')", (job_id,)).fetchone()[0]
        snapshot = json.dumps([{"path": row["relative_path"], "sha256": row["sha256"], "bytes": row["byte_length"]} for row in rows], ensure_ascii=False)
        db.execute(
            "UPDATE import_jobs SET snapshot=?, phase='extracting', progress_total=?, progress_done=?, updated_at=? WHERE id=?",
            (snapshot, total, done, utcnow(), job_id),
        )
    return "ready"


def _parse(kind: str, path: Path, data: bytes) -> ParseResult:
    if kind == "image":
        return parse_image(data, str(path))
    if kind == "pdf":
        return parse_pdf(data)
    text = _decode(data)
    if kind == "python":
        return parse_python(text)
    if kind == "notebook":
        return parse_notebook(text)
    if kind == "csv":
        return parse_table(text, ",")
    if kind == "tsv":
        return parse_table(text, "\t")
    return parse_text(text, empty_message="File di testo vuoto.")


def _write_derived(profile: Path, version_id: str, payload: dict):
    target = profile / "derived" / "catalog" / f"{version_id}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, target)


def _store_version(profile: Path, source_id: str, material_locator: str, kind: str, digest: str, result: ParseResult) -> tuple[str, str, str]:
    db_path = profile / "deepstudy.db"
    material_id = uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}:{material_locator}").hex
    version_id = uuid.uuid5(uuid.NAMESPACE_URL, f"{material_id}:{digest}").hex
    with connect(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("INSERT OR IGNORE INTO materials(id, source_id, locator) VALUES(?,?,?)", (material_id, source_id, material_locator))
        current = db.execute("SELECT id, extraction_state FROM material_versions WHERE material_id=? AND sha256=?", (material_id, digest)).fetchone()
        if current:
            outcome = "reused"
            version_id = current["id"]
            extraction_state = current["extraction_state"]
        else:
            outcome = "created"
            revision = db.execute("SELECT count(*) FROM material_versions WHERE material_id=?", (material_id,)).fetchone()[0] + 1
            extraction_state = "failed" if result.extraction_state == "failed" else "ready"
            db.execute(
                """INSERT INTO material_versions(id, material_id, source_revision, sha256, kind, extraction_state)
                   VALUES(?,?,?,?,?,?)""",
                (version_id, material_id, str(revision), digest, kind, extraction_state),
            )
            for chunk in result.chunks if extraction_state == "ready" else ():
                chunk_id = uuid.uuid5(uuid.NAMESPACE_URL, f"{version_id}:{chunk.locator}").hex
                db.execute(
                    "INSERT INTO chunks(id, version_id, locator, text, quality, index_version) VALUES(?,?,?,?,?,?)",
                    (chunk_id, version_id, chunk.locator, chunk.text, chunk.quality, INDEX_VERSION),
                )
    if outcome == "created" or not (profile / "derived" / "catalog" / f"{version_id}.json").exists():
        _write_derived(profile, version_id, {
            "version_id": version_id,
            "material_id": material_id,
            "locator": material_locator,
            "sha256": digest,
            "kind": kind,
            "extraction_state": extraction_state,
            "error_code": result.error_code,
            "error_message": result.error_message,
            "chunks": [{"locator": chunk.locator, "text": chunk.text, "quality": chunk.quality, "index_version": INDEX_VERSION} for chunk in result.chunks] if extraction_state == "ready" else [],
        })
    return material_id, version_id, outcome


def _process_item(profile: Path, source_id: str, root: Path, item):
    db_path = profile / "deepstudy.db"
    path = root / item["relative_path"]
    kind = ALLOWLIST[path.suffix.lower()]
    try:
        data = _read_file(path)
    except (PermissionError, OSError, _Symlink, _NotRegular):
        _finish_item(db_path, item["id"], state="error", outcome="error", code="unreadable", message="File illeggibile. L'originale non è stato modificato.", retryable=1)
        return
    if len(data) != item["byte_length"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
        raise RuntimeError("originals_modified")
    try:
        result = _parse(kind, path, data)
    except ValueError as exc:
        result = ParseResult("failed", "undecodable", str(exc), False, (), ())
    if result.retryable:
        _finish_item(db_path, item["id"], state="error", outcome="error", code=result.error_code, message=result.error_message, retryable=1, detail=None)
        return
    material_id, version_id, outcome = _store_version(profile, source_id, item["relative_path"], kind, item["sha256"], result)
    detail = " ".join(result.warnings) or None
    if result.extraction_state == "failed":
        _finish_item(db_path, item["id"], state="error", outcome=outcome, code=result.error_code, message=result.error_message, retryable=0, material_id=material_id, version_id=version_id, detail=detail)
        return
    _finish_item(db_path, item["id"], state="done", outcome=outcome, material_id=material_id, version_id=version_id, detail=detail)


def _finish_item(db_path: Path, item_id: str, *, state: str, outcome: str, code: str | None = None, message: str | None = None, retryable: int = 0, material_id: str | None = None, version_id: str | None = None, detail: str | None = None):
    with connect(db_path) as db:
        db.execute(
            """UPDATE import_job_items SET state=?, outcome=?, error_code=?, error_message=?, retryable=?, material_id=?, version_id=?, detail=? WHERE id=?""",
            (state, outcome, code, message, retryable, material_id, version_id, detail, item_id),
        )
        job_id = db.execute("SELECT job_id FROM import_job_items WHERE id=?", (item_id,)).fetchone()["job_id"]
        done = db.execute("SELECT count(*) FROM import_job_items WHERE job_id=? AND state IN ('done','error')", (job_id,)).fetchone()[0]
        db.execute("UPDATE import_jobs SET progress_done=?, updated_at=? WHERE id=?", (done, utcnow(), job_id))


def _verify_snapshot(root: Path, db_path: Path, job_id: str) -> bool:
    with connect(db_path) as db:
        rows = db.execute("SELECT relative_path, sha256 FROM import_job_items WHERE job_id=? AND sha256 IS NOT NULL", (job_id,)).fetchall()
    for row in rows:
        try:
            digest, _size = _hash_file(root / row["relative_path"])
        except OSError:
            return False
        if digest != row["sha256"]:
            return False
    return True


def _finalize(profile: Path, job_id: str, source_id: str, root: Path):
    db_path = profile / "deepstudy.db"
    unchanged = _verify_snapshot(root, db_path, job_id)
    with connect(db_path) as db:
        items = db.execute("SELECT * FROM import_job_items WHERE job_id=? ORDER BY relative_path", (job_id,)).fetchall()
        duplicates_rows = db.execute(
            """SELECT v.sha256, m.locator FROM material_versions v
               JOIN materials m ON m.id=v.material_id
               JOIN (
                 SELECT material_id, MAX(CAST(source_revision AS INTEGER)) AS revision
                 FROM material_versions GROUP BY material_id
               ) latest ON latest.material_id=v.material_id AND latest.revision=CAST(v.source_revision AS INTEGER)
               WHERE m.source_id=? ORDER BY v.sha256, m.locator""",
            (source_id,),
        ).fetchall()
    grouped: dict[str, list[str]] = {}
    for row in duplicates_rows:
        grouped.setdefault(row["sha256"], [])
        if row["locator"] not in grouped[row["sha256"]]:
            grouped[row["sha256"]].append(row["locator"])
    report = {
        "files_seen": len(items),
        "versions_created": sum(row["outcome"] == "created" for row in items),
        "versions_reused": sum(row["outcome"] == "reused" for row in items),
        "original_hashes_unchanged": unchanged,
        "ocr_engine": engine_name(),
        "max_file_bytes": MAX_FILE_BYTES,
        "errors": [{"path": row["relative_path"], "code": row["error_code"], "message": row["error_message"], "retryable": bool(row["retryable"])} for row in items if row["state"] == "error"],
        "warnings": [{"path": row["relative_path"], "message": row["detail"]} for row in items if row["detail"]],
        "excluded": [{"path": row["relative_path"], "reason": row["error_code"], "message": row["error_message"]} for row in items if row["state"] == "excluded"],
        "duplicates": [{"sha256": digest, "paths": paths} for digest, paths in sorted(grouped.items()) if len(paths) > 1],
        "snapshot": [{"path": row["relative_path"], "sha256": row["sha256"], "bytes": row["byte_length"]} for row in items if row["sha256"]],
    }
    if not unchanged:
        report["errors"].append({"path": "", "code": "originals_modified", "message": "Un originale è cambiato durante la lettura. DeepStudy non scrive in quella cartella.", "retryable": False})
        _update_job(db_path, job_id, state="failed", phase="failed", error_code="originals_modified", error_message=report["errors"][-1]["message"], report=json.dumps(report, ensure_ascii=False))
        return
    _update_job(db_path, job_id, state="completed", phase="completed", error_code=None, error_message=None, report=json.dumps(report, ensure_ascii=False))


def run_job(profile: Path, job_id: str):
    db_path = profile / "deepstudy.db"
    try:
        row = _job_row(db_path, job_id)
        if row["state"] not in ("running", "interrupted"):
            return
        root = Path(row["locator"])
        source_id = row["source_id"]
        _update_job(db_path, job_id, state="running", phase="scanning")
        if _stop_requested(db_path, job_id):
            _mark_interrupted(db_path, job_id)
            return
        scan_state = _scan(profile, job_id, root)
        if scan_state != "ready":
            return
        while True:
            with connect(db_path) as db:
                done = db.execute("SELECT count(*) FROM import_job_items WHERE job_id=? AND state IN ('done','error')", (job_id,)).fetchone()[0]
                item = db.execute(
                    "SELECT * FROM import_job_items WHERE job_id=? AND state='pending' ORDER BY relative_path LIMIT 1",
                    (job_id,),
                ).fetchone()
            if before_item_hook:
                before_item_hook(db_path, job_id, done)
            if _stop_requested(db_path, job_id):
                _mark_interrupted(db_path, job_id)
                return
            if item is None:
                break
            _update_job(db_path, job_id, phase="extracting")
            try:
                _process_item(profile, source_id, root, item)
            except RuntimeError as exc:
                if str(exc) != "originals_modified":
                    raise
                _finalize(profile, job_id, source_id, root)
                return
        _update_job(db_path, job_id, phase="deduplicating")
        _finalize(profile, job_id, source_id, root)
    except SimulatedCrash:
        raise
    except Exception:
        _fail_job(db_path, job_id, "internal_error", "Importazione non riuscita. I file originali e le versioni già registrate restano invariati.")


def list_materials(db_path: Path, *, kind: str | None, state: str | None, limit: int, offset: int) -> dict:
    filters = []
    parameters: list = []
    if kind:
        filters.append("v.kind=?")
        parameters.append(kind)
    if state:
        filters.append("v.extraction_state=?")
        parameters.append(state)
    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    query = f"""
        SELECT m.id, m.locator, m.source_id, v.id AS version_id, v.sha256, v.kind, v.extraction_state, v.source_revision
        FROM materials m
        JOIN material_versions v ON v.material_id=m.id
        JOIN (
            SELECT material_id, MAX(CAST(source_revision AS INTEGER)) AS revision
            FROM material_versions GROUP BY material_id
        ) latest ON latest.material_id=v.material_id AND latest.revision=CAST(v.source_revision AS INTEGER)
        {where}
        ORDER BY m.locator
    """
    with connect(db_path) as db:
        rows = db.execute(query, parameters).fetchall()
        duplicate_map: dict[str, list[str]] = {}
        if rows:
            hashes = sorted({row["sha256"] for row in rows})
            placeholders = ",".join("?" for _ in hashes)
            related = db.execute(
                f"""SELECT v.sha256, m.locator FROM material_versions v
                    JOIN materials m ON m.id=v.material_id
                    JOIN (
                      SELECT material_id, MAX(CAST(source_revision AS INTEGER)) AS revision
                      FROM material_versions GROUP BY material_id
                    ) latest ON latest.material_id=v.material_id AND latest.revision=CAST(v.source_revision AS INTEGER)
                    WHERE v.sha256 IN ({placeholders}) ORDER BY m.locator""",
                hashes,
            ).fetchall()
            for related_row in related:
                duplicate_map.setdefault(related_row["sha256"], [])
                if related_row["locator"] not in duplicate_map[related_row["sha256"]]:
                    duplicate_map[related_row["sha256"]].append(related_row["locator"])
    page = rows[offset:offset + limit]
    return {
        "total": len(rows),
        "limit": limit,
        "offset": offset,
        "items": [{
            "id": row["id"],
            "source_id": row["source_id"],
            "locator": row["locator"],
            "version_id": row["version_id"],
            "sha256": row["sha256"],
            "kind": row["kind"],
            "extraction_state": row["extraction_state"],
            "source_revision": row["source_revision"],
            "duplicate_locators": [locator for locator in duplicate_map.get(row["sha256"], []) if locator != row["locator"]],
        } for row in page],
    }


def get_chunks(db_path: Path, material_id: str, version_id: str) -> dict:
    with connect(db_path) as db:
        version = db.execute(
            "SELECT id, extraction_state, sha256, kind FROM material_versions WHERE id=? AND material_id=?",
            (version_id, material_id),
        ).fetchone()
        if not version:
            raise CatalogError(404, "version_not_found", "Versione non trovata.")
        chunks = db.execute(
            "SELECT locator, text, quality, index_version FROM chunks WHERE version_id=? ORDER BY locator",
            (version_id,),
        ).fetchall()
    return {
        "version_id": version["id"],
        "kind": version["kind"],
        "sha256": version["sha256"],
        "extraction_state": version["extraction_state"],
        "chunks": [dict(chunk) for chunk in chunks],
    }
