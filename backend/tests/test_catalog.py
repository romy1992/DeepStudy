import hashlib
import json
import struct
import threading
import zlib
import zipfile
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient

from deepstudy.app import create_app
from deepstudy.backup import digest
from deepstudy.catalog import SimulatedCrash, wait_for_job
from deepstudy.database import DEFAULT_SETTINGS, SCHEMA_VERSION, connect, migrate, read_settings
import deepstudy.catalog as catalog

ORIGIN = "http://127.0.0.1:43123"
TOKEN = "test-only-bootstrap-never-a-production-secret"
PDF = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Count 1 /Kids [3 0 R] >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 55 >>
stream
BT /F1 12 Tf 20 100 Td (Prova catalogo) Tj ET
endstream
endobj
trailer
<< /Root 1 0 R >>
%%EOF
"""


def client_for(profile: Path):
    client = TestClient(create_app(profile, ORIGIN, TOKEN), base_url=ORIGIN)
    assert client.post("/api/session", headers={"Origin": ORIGIN, "Authorization": f"Bearer {TOKEN}"}).status_code == 200
    client.headers["Origin"] = ORIGIN
    return client


def png_bytes() -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    raw = b"\x00\xff\xff\xff"
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def fingerprints(root: Path) -> dict[str, str]:
    found = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        found[path.relative_to(root).as_posix()] = hashlib.sha256(data).hexdigest()
    return found


def version_rows(profile: Path):
    with connect(profile / "deepstudy.db") as db:
        return db.execute(
            """SELECT m.locator, v.sha256, v.extraction_state, v.source_revision, v.kind
               FROM material_versions v JOIN materials m ON m.id=v.material_id
               ORDER BY m.locator, CAST(v.source_revision AS INTEGER)"""
        ).fetchall()


def import_folder(client, profile: Path, folder: Path, key: str):
    response = client.post("/api/imports", json={"locator": str(folder), "idempotency_key": key})
    assert response.status_code == 200, response.text
    return wait_for_job(profile / "deepstudy.db", response.json()["id"])


def write_corpus(root: Path, marker: Path):
    root.mkdir()
    (root / "nested").mkdir()
    shared = "def saldo(valore):\n    return valore + 1\n"
    (root / "uno.py").write_text(shared, encoding="utf-8")
    (root / "nested" / "copia.py").write_text(shared, encoding="utf-8")
    (root / "danger.py").write_text(f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n", encoding="utf-8")
    (root / "rotto.py").write_text("def rotto(:\n", encoding="utf-8")
    notebook = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "cells": [
            {"cell_type": "markdown", "source": ["# Titolo\n"]},
            {"cell_type": "code", "source": "print(1)\n", "outputs": [{"text": "SENTINEL_OUTPUT"}], "execution_count": 1},
        ],
    }
    (root / "lezione.ipynb").write_text(json.dumps(notebook), encoding="utf-8")
    (root / "bad.ipynb").write_text("{", encoding="utf-8")
    (root / "nota.md").write_text("# Appunto\n", encoding="utf-8")
    (root / "dati.csv").write_text("nome,valore\nada,1\n", encoding="utf-8")
    (root / "scheda.pdf").write_bytes(PDF)
    (root / "figura.png").write_bytes(png_bytes())
    (root / "modello.pkl").write_bytes(b"pickle-not-loaded")
    (root / "cache.log").write_text("log locale\n", encoding="utf-8")
    cache = root / "__pycache__"
    cache.mkdir()
    (cache / "nascosto.py").write_text("valore = 1\n", encoding="utf-8")
    outside = root.parent / "fuori.py"
    outside.write_text("valore = 2\n", encoding="utf-8")
    (root / "ponte.py").symlink_to(outside)
    (root / "illeggibile.py").write_text("valore = 3\n", encoding="utf-8")
    (root / "illeggibile.py").chmod(0)
    return outside


def test_import_is_static_idempotent_and_versioned(tmp_path):
    profile, corpus = tmp_path / "profile", tmp_path / "corpus"
    marker = tmp_path / "executed.txt"
    outside = write_corpus(corpus, marker)
    readable_before = fingerprints(Path(corpus))
    outside_before = outside.read_bytes()
    client = client_for(profile)
    assert client.post("/api/imports", json={"locator": "relativa", "idempotency_key": "short"}).status_code == 422
    assert client.post("/api/imports", json={"locator": str(tmp_path), "idempotency_key": "reject-parent"}).status_code == 400
    assert client.post("/api/imports", json={"locator": str(Path(__file__).resolve().parents[2]), "idempotency_key": "reject-root"}).status_code == 400
    anonymous = TestClient(create_app(tmp_path / "other", ORIGIN, TOKEN), base_url=ORIGIN)
    assert anonymous.post("/api/imports", json={"locator": str(corpus), "idempotency_key": "anonymous1"}, headers={"Origin": ORIGIN}).status_code == 401

    first = import_folder(client, profile, corpus, "import-one")
    assert first["state"] == "completed"
    assert first["report"]["original_hashes_unchanged"] is True
    assert not marker.exists()
    assert outside.read_bytes() == outside_before
    assert fingerprints(corpus) == readable_before
    errors = {item["path"]: item for item in first["report"]["errors"]}
    assert any(item["path"] == "rotto.py" for item in first["report"]["warnings"])
    assert errors["bad.ipynb"]["code"] == "invalid_notebook"
    assert errors["illeggibile.py"]["code"] == "unreadable"
    assert "ponte.py" in {item["path"] for item in first["report"]["excluded"]}
    assert "modello.pkl" in {item["path"] for item in first["report"]["excluded"]}
    assert "__pycache__/nascosto.py" not in {item["path"] for item in first["report"]["snapshot"]}
    duplicate_paths = {tuple(group["paths"]) for group in first["report"]["duplicates"]}
    assert ("nested/copia.py", "uno.py") in duplicate_paths or ("uno.py", "nested/copia.py") in duplicate_paths
    rows = version_rows(profile)
    locators = [row["locator"] for row in rows]
    assert locators.count("uno.py") == 1
    assert locators.count("nested/copia.py") == 1
    assert "bad.ipynb" in locators
    assert "illeggibile.py" not in locators
    same_hash = [row["sha256"] for row in rows if row["locator"] in ("uno.py", "nested/copia.py")]
    assert same_hash[0] == same_hash[1]
    assert any(row["locator"] == "bad.ipynb" and row["extraction_state"] == "failed" for row in rows)
    assert any(row["locator"] == "scheda.pdf" and row["extraction_state"] == "ready" for row in rows)

    repeated = import_folder(client, profile, corpus, "import-two")
    assert repeated["report"]["versions_created"] == 0
    assert repeated["report"]["versions_reused"] >= 1
    assert len(version_rows(profile)) == len(rows)
    replay = client.post("/api/imports", json={"locator": str(corpus), "idempotency_key": "import-two"})
    assert replay.status_code == 200
    assert replay.json()["id"] == repeated["id"]
    assert len(version_rows(profile)) == len(rows)

    changed = corpus / "nested" / "copia.py"
    changed.write_text("def saldo(valore):\n    return valore + 2\n", encoding="utf-8")
    third = import_folder(client, profile, corpus, "import-three")
    assert third["report"]["original_hashes_unchanged"] is True
    updated = [row for row in version_rows(profile) if row["locator"] == "nested/copia.py"]
    assert [row["source_revision"] for row in updated] == ["1", "2"]
    assert updated[0]["sha256"] != updated[1]["sha256"]
    assert len([row for row in version_rows(profile) if row["locator"] == "uno.py"]) == 1

    materials = client.get("/api/materials").json()
    copy = next(item for item in materials["items"] if item["locator"] == "uno.py")
    chunks = client.get(f"/api/materials/{copy['id']}/versions/{copy['version_id']}/chunks").json()
    assert any(chunk["locator"] == "lines:1-2" for chunk in chunks["chunks"])
    assert all(chunk["quality"] != "reviewed" for chunk in chunks["chunks"])
    notebook = next(item for item in materials["items"] if item["locator"] == "lezione.ipynb")
    notebook_chunks = client.get(f"/api/materials/{notebook['id']}/versions/{notebook['version_id']}/chunks").json()
    visible = "\n".join(chunk["text"] for chunk in notebook_chunks["chunks"])
    assert "print(1)" in visible
    assert "SENTINEL_OUTPUT" not in visible
    assert {chunk["locator"] for chunk in notebook_chunks["chunks"]} == {"cell:0", "cell:1"}
    pdf = next(item for item in materials["items"] if item["locator"] == "scheda.pdf")
    pdf_chunks = client.get(f"/api/materials/{pdf['id']}/versions/{pdf['version_id']}/chunks").json()
    assert pdf_chunks["chunks"][0]["locator"] == "page:1"
    assert "Prova catalogo" in pdf_chunks["chunks"][0]["text"]
    assert pdf_chunks["chunks"][0]["quality"] != "reviewed"
    derived = json.loads((profile / "derived" / "catalog" / f"{notebook['version_id']}.json").read_text(encoding="utf-8"))
    assert "SENTINEL_OUTPUT" not in json.dumps(derived)
    image_error = errors.get("figura.png")
    image_row = next((item for item in materials["items"] if item["locator"] == "figura.png"), None)
    if image_error:
        assert image_error["code"] in {"ocr_unavailable", "ocr_failed", "ocr_empty"}
        assert image_row is None
    else:
        assert image_row["extraction_state"] == "ready"
        image_chunks = client.get(f"/api/materials/{image_row['id']}/versions/{image_row['version_id']}/chunks").json()
        assert image_chunks["chunks"][0]["quality"] == "ocr_unverified"
    (corpus / "illeggibile.py").chmod(0o644)
    assert (corpus / "illeggibile.py").read_text(encoding="utf-8") == "valore = 3\n"
    page = client.get("/api/materials", params={"limit": 1, "offset": 1}).json()
    assert page["total"] == materials["total"]
    assert len(page["items"]) == 1


def test_interrupt_resume_and_process_recovery(tmp_path):
    profile, corpus = tmp_path / "profile", tmp_path / "corpus"
    corpus.mkdir()
    for index in range(4):
        (corpus / f"file-{index}.py").write_text(f"valore = {index}\n", encoding="utf-8")
    client = client_for(profile)
    started, release = threading.Event(), threading.Event()

    def pause(_db, _job, done):
        if done == 1:
            started.set()
            assert release.wait(5)

    catalog.before_item_hook = pause
    try:
        response = client.post("/api/imports", json={"locator": str(corpus), "idempotency_key": "pause-job"})
        assert response.status_code == 200, response.text
        job_id = response.json()["id"]
        assert started.wait(5)
        assert client.post(f"/api/jobs/{job_id}/interrupt").status_code == 200
        release.set()
        paused = wait_for_job(profile / "deepstudy.db", job_id)
        assert paused["state"] == "interrupted"
        assert paused["can_resume"] is True
        assert paused["progress_done"] == 1
        catalog.before_item_hook = None
        assert client.post(f"/api/jobs/{job_id}/resume").status_code == 200
        finished = wait_for_job(profile / "deepstudy.db", job_id)
        assert finished["state"] == "completed"
        assert len(version_rows(profile)) == 4
        assert client.post(f"/api/jobs/{job_id}/interrupt").status_code == 409
    finally:
        catalog.before_item_hook = None
        release.set()

    crash_profile, crash_corpus = tmp_path / "crash-profile", tmp_path / "crash-corpus"
    crash_corpus.mkdir()
    for index in range(3):
        (crash_corpus / f"modulo-{index}.py").write_text(f"valore = {index}\n", encoding="utf-8")
    crash_client = client_for(crash_profile)

    def crash(_db, _job, done):
        if done == 1:
            raise SimulatedCrash()

    catalog.before_item_hook = crash
    try:
        response = crash_client.post("/api/imports", json={"locator": str(crash_corpus), "idempotency_key": "crash-job"})
        job_id = response.json()["id"]
        with catalog._workers_lock:
            thread = catalog._workers.get(job_id)
        if thread:
            thread.join(5)
        running = crash_client.get(f"/api/jobs/{job_id}").json()
        assert running["state"] == "running"
        assert running["progress_done"] == 1
    finally:
        catalog.before_item_hook = None
    restarted = client_for(crash_profile)
    recovered = restarted.get(f"/api/jobs/{job_id}").json()
    assert recovered["state"] == "interrupted"
    assert restarted.post(f"/api/jobs/{job_id}/resume").status_code == 200
    finished = wait_for_job(crash_profile / "deepstudy.db", job_id)
    assert finished["state"] == "completed"
    assert len(version_rows(crash_profile)) == 3
    assert finished["report"]["versions_created"] + finished["report"]["versions_reused"] == 3


def test_restore_upgrades_m1_backup(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    database = source / "deepstudy.db"
    migrate(database, target=2)
    with connect(database) as db:
        db.execute("UPDATE settings SET value=?, revision=1", (json.dumps({**DEFAULT_SETTINGS, "display_name": "Ada"}),))
    payload = BytesIO()
    content = database.read_bytes()
    manifest = {"format": "deepstudy-backup", "version": 1, "schema_version": 2, "files": {"deepstudy.db": {"sha256": digest(content), "bytes": len(content)}}}
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("deepstudy.db", content)
        archive.writestr("manifest.json", json.dumps(manifest))
    destination = tmp_path / "destination"
    migrate(destination / "deepstudy.db")
    from deepstudy.backup import restore_profile
    restore_profile(destination, payload.getvalue())
    assert read_settings(destination / "deepstudy.db")["display_name"] == "Ada"
    with connect(destination / "deepstudy.db") as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        assert db.execute("SELECT name FROM sqlite_master WHERE name='import_jobs'").fetchone()
