"""Sessioni, note e panoramica. Aprire una pagina non sblocca il modulo successivo."""
from __future__ import annotations

import json
import uuid
from pathlib import Path

from .curriculum import CURRICULUM_VERSION, HOURS_NOTE, UNITS, ensure_curriculum, ensure_study_questions, unit
from .database import connect
from .errors import StudyError
from .exchange import device_id, record_event
from .quiz import correct_objectives, mastery_rows, rebuild_reviews


def utcnow() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _citation_for(db, objective_id: str) -> dict:
    evidence = db.execute(
        """SELECT e.version_id, e.locator, c.text, v.sha256, m.locator AS material_locator, m.id AS material_id
           FROM objective_evidence e
           LEFT JOIN chunks c ON c.version_id=e.version_id AND c.locator=e.locator
           LEFT JOIN material_versions v ON v.id=e.version_id
           LEFT JOIN materials m ON m.id=v.material_id
           WHERE e.objective_id=? AND e.review='reviewed'
           ORDER BY e.id LIMIT 1""",
        (objective_id,),
    ).fetchone()
    if evidence:
        return {
            "kind": "materiale",
            "version_id": evidence["version_id"],
            "locator": evidence["locator"],
            "material_id": evidence["material_id"],
            "material_locator": evidence["material_locator"],
            "sha256": evidence["sha256"],
            "excerpt": evidence["text"],
            "curriculum_version": CURRICULUM_VERSION,
        }
    item = unit(objective_id)
    return {
        "kind": "percorso",
        "version_id": None,
        "locator": f"curriculum:{objective_id}",
        "material_id": None,
        "material_locator": None,
        "sha256": None,
        "excerpt": item["explanation"],
        "curriculum_version": CURRICULUM_VERSION,
    }


def _question_public(db, objective_id: str) -> dict | None:
    row = db.execute(
        """SELECT q.id, q.prompt, q.options, q.review, m.kind, m.origin
           FROM question_versions q JOIN question_meta m ON m.question_version_id=q.id
           WHERE q.objective_id=? AND m.bank='study' AND m.origin='authored' AND q.review='reviewed'
           ORDER BY q.id LIMIT 1""",
        (objective_id,),
    ).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "prompt": row["prompt"],
        "options": json.loads(row["options"]),
        "kind": row["kind"],
        "origin": row["origin"],
        "review": row["review"],
    }


def _session_payload(db, row, *, resumed: bool) -> dict:
    citation = json.loads(row["citation"])
    return {
        "id": row["id"],
        "objective_id": row["objective_id"],
        "title": unit(row["objective_id"])["title"],
        "mode": row["mode"],
        "state": row["state"],
        "started_at": row["started_at"],
        "updated_at": row["updated_at"],
        "resumed": resumed,
        "citation": citation,
        "question": _question_public(db, row["objective_id"]),
        "mastery_note": "Questa apertura non è un tentativo e non sblocca il modulo successivo.",
    }


def start_session(db_path: Path, objective_id: str, mode: str) -> dict:
    try:
        unit(objective_id)
    except KeyError:
        raise StudyError(404, "objective_not_found", "Obiettivo sconosciuto.") from None
    now = utcnow()
    with connect(db_path) as db:
        ensure_study_questions(db)
        unlocked = _unlocked(db)
        if objective_id not in unlocked:
            raise StudyError(409, "prerequisite_missing", "I prerequisiti non hanno ancora un tentativo corretto.")
        citation = _citation_for(db, objective_id)
        session_id = uuid.uuid4().hex
        db.execute(
            """INSERT INTO study_sessions(id, objective_id, mode, state, citation, started_at, updated_at)
               VALUES(?,?,?,'active',?,?,?)""",
            (session_id, objective_id, mode, json.dumps(citation, ensure_ascii=False), now, now),
        )
        row = db.execute("SELECT * FROM study_sessions WHERE id=?", (session_id,)).fetchone()
        return _session_payload(db, row, resumed=False)


def _load_session(db, session_id: str):
    row = db.execute("SELECT * FROM study_sessions WHERE id=?", (session_id,)).fetchone()
    if not row:
        raise StudyError(404, "session_not_found", "Sessione non trovata.")
    return row


def interrupt_session(db_path: Path, session_id: str) -> dict:
    now = utcnow()
    with connect(db_path) as db:
        row = _load_session(db, session_id)
        if row["state"] == "interrupted":
            return _session_payload(db, row, resumed=False)
        db.execute("UPDATE study_sessions SET state='interrupted', updated_at=? WHERE id=?", (now, session_id))
        row = _load_session(db, session_id)
        return _session_payload(db, row, resumed=False)


def resume_session(db_path: Path, session_id: str) -> dict:
    now = utcnow()
    with connect(db_path) as db:
        row = _load_session(db, session_id)
        if row["state"] == "active":
            return _session_payload(db, row, resumed=True)
        db.execute("UPDATE study_sessions SET state='active', updated_at=? WHERE id=?", (now, session_id))
        row = _load_session(db, session_id)
        return _session_payload(db, row, resumed=True)


def get_session(db_path: Path, session_id: str) -> dict:
    with connect(db_path) as db:
        return _session_payload(db, _load_session(db, session_id), resumed=False)


def add_evidence(db_path: Path, objective_id: str, version_id: str, locator: str, coverage: str, review: str) -> dict:
    try:
        unit(objective_id)
    except KeyError:
        raise StudyError(404, "objective_not_found", "Obiettivo sconosciuto.") from None
    with connect(db_path) as db:
        ensure_curriculum(db)
        version = db.execute("SELECT id FROM material_versions WHERE id=?", (version_id,)).fetchone()
        if not version:
            raise StudyError(404, "version_not_found", "Versione del materiale non trovata.")
        evidence_id = uuid.uuid4().hex
        db.execute(
            """INSERT INTO objective_evidence(id, objective_id, version_id, locator, coverage, review)
               VALUES(?,?,?,?,?,?)""",
            (evidence_id, objective_id, version_id, locator, coverage, review),
        )
    return {"id": evidence_id, "objective_id": objective_id, "version_id": version_id, "locator": locator}


def add_practice(db_path: Path, objective_id: str, note: str) -> dict:
    try:
        unit(objective_id)
    except KeyError:
        raise StudyError(404, "objective_not_found", "Obiettivo sconosciuto.") from None
    now = utcnow()
    mark_id = uuid.uuid4().hex
    with connect(db_path) as db:
        ensure_curriculum(db)
        db.execute(
            "INSERT INTO practice_marks(id, objective_id, note, created_at) VALUES(?,?,?,?)",
            (mark_id, objective_id, note, now),
        )
    return {"id": mark_id, "objective_id": objective_id, "created_at": now}


def save_note(db_path: Path, note_id: str, base_version: str | None, content: str, objective_id: str | None) -> dict:
    now = utcnow()
    version_id = uuid.uuid4().hex
    with connect(db_path) as db:
        if objective_id:
            ensure_curriculum(db)
            if not db.execute("SELECT 1 FROM objectives WHERE id=?", (objective_id,)).fetchone():
                raise StudyError(404, "objective_not_found", "Obiettivo sconosciuto.")
        if base_version and not db.execute(
            "SELECT 1 FROM note_versions WHERE id=? AND note_id=?", (base_version, note_id)
        ).fetchone():
            raise StudyError(409, "base_missing", "La versione di partenza non esiste più per questa nota.")
        device = device_id(db)
        db.execute(
            "INSERT INTO note_versions(id, note_id, base_version, content, device_id) VALUES(?,?,?,?,?)",
            (version_id, note_id, base_version, content, device),
        )
        record_event(db, kind="note", entity_id=note_id, base_revision=base_version, body={
            "version_id": version_id, "content": content, "device_id": device, "objective_id": objective_id, "at": now,
        })
        return _note_view(db, note_id)


def tombstone_note(db_path: Path, note_id: str) -> dict:
    now = utcnow()
    with connect(db_path) as db:
        if not db.execute("SELECT 1 FROM note_versions WHERE note_id=?", (note_id,)).fetchone():
            raise StudyError(404, "note_not_found", "Nota non trovata.")
        db.execute(
            "INSERT INTO tombstones(entity_id, entity_kind, at) VALUES(?,?,?) ON CONFLICT(entity_id) DO NOTHING",
            (note_id, "note", now),
        )
        record_event(db, kind="tombstone", entity_id=note_id, base_revision=None, body={"entity_kind": "note", "at": now})
        return _note_view(db, note_id)


def get_note(db_path: Path, note_id: str) -> dict:
    with connect(db_path) as db:
        if not db.execute("SELECT 1 FROM note_versions WHERE note_id=?", (note_id,)).fetchone():
            raise StudyError(404, "note_not_found", "Nota non trovata.")
        return _note_view(db, note_id)


def _note_view(db, note_id: str) -> dict:
    rows = db.execute(
        "SELECT id, base_version, content, device_id FROM note_versions WHERE note_id=? ORDER BY id",
        (note_id,),
    ).fetchall()
    bases: dict[str | None, int] = {}
    versions = []
    for row in rows:
        bases[row["base_version"]] = bases.get(row["base_version"], 0) + 1
        versions.append({
            "id": row["id"], "base_version": row["base_version"], "content": row["content"], "device_id": row["device_id"],
        })
    conflict = any(count > 1 for count in bases.values())
    hidden = db.execute("SELECT at FROM tombstones WHERE entity_id=? AND entity_kind='note'", (note_id,)).fetchone()
    return {
        "note_id": note_id,
        "versions": versions,
        "conflict": conflict,
        "tombstoned": hidden is not None,
        "retained": True,
    }


def _unlocked(db) -> set[str]:
    done = correct_objectives(db)
    return {item["id"] for item in UNITS if all(pre in done for pre in item["prerequisites"])}


def curriculum_view(db_path: Path) -> dict:
    with connect(db_path) as db:
        present = db.execute("SELECT 1 FROM objectives WHERE id='c00'").fetchone()
        if present:
            ensure_curriculum(db)
        unlocked = _unlocked(db) if present else {"c00"}
        levels = {row["id"]: row for row in mastery_rows(db)} if present else {}
        modules = []
        for item in UNITS:
            level = levels.get(item["id"], {"level": "non_iniziato", "reason": "Nessuna lettura e nessun tentativo."})
            modules.append({
                "id": item["id"],
                "title": item["title"],
                "summary": item["summary"],
                "estimate_hours": item["estimate"],
                "prerequisites": list(item["prerequisites"]),
                "locked": item["id"] not in unlocked,
                "mastery": level["level"],
                "mastery_reason": level["reason"],
            })
    return {"version": CURRICULUM_VERSION, "hours_note": HOURS_NOTE, "modules": modules}


def dashboard(db_path: Path, *, now: str | None = None) -> dict:
    clock = now or utcnow()
    with connect(db_path) as db:
        present = db.execute("SELECT 1 FROM objectives WHERE id='c00'").fetchone() is not None
        reviews = rebuild_reviews(db, clock) if present else []
        unlocked = _unlocked(db) if present else {"c00"}
        levels = {row["id"]: row for row in mastery_rows(db)} if present else {}
        sessions = db.execute("SELECT COUNT(*) FROM study_sessions").fetchone()[0] if present else 0
    frontier = next((item for item in UNITS if item["id"] in unlocked and levels.get(item["id"], {}).get("level") in (None, "non_iniziato", "letto")), None)
    partial = next((item for item in UNITS if levels.get(item["id"], {}).get("level") == "in_corso"), None)
    if reviews:
        first = reviews[0]
        action = {
            "kind": "ripasso",
            "objective_id": first["objective_id"],
            "title": first["title"],
            "reason": first["reason"],
        }
    elif frontier:
        action = {
            "kind": "sessione",
            "objective_id": frontier["id"],
            "title": frontier["title"],
            "reason": "Non c'è ancora un tentativo corretto. Aprire il testo non sblocca il modulo successivo.",
        }
    elif partial:
        action = {
            "kind": "pratica",
            "objective_id": partial["id"],
            "title": partial["title"],
            "reason": partial_reason(levels[partial["id"]]["reason"]),
        }
    else:
        action = {
            "kind": "simulazione",
            "objective_id": "c12",
            "title": "Consolidamento e simulazioni",
            "reason": "I moduli di base hanno un tentativo corretto. La certificazione ufficiale non è stata scelta.",
        }
    gaps = [
        {"id": item["id"], "title": item["title"], "reason": "Nessun tentativo corretto su un quesito di studio."}
        for item in UNITS
        if levels.get(item["id"], {}).get("level", "non_iniziato") in ("non_iniziato", "letto")
    ]
    return {
        "next_action": action,
        "reviews_due": reviews,
        "gaps": gaps[:8],
        "reading": {
            "sessions": sessions,
            "note": "Le letture restano separate dai tentativi, dalla padronanza e dalla copertura d'esame.",
        },
        "mastery": [levels.get(item["id"], {"id": item["id"], "title": item["title"], "level": "non_iniziato", "reason": "Nessuna lettura e nessun tentativo."}) for item in UNITS],
        "certification_chosen": False,
        "hours_note": HOURS_NOTE,
    }


def partial_reason(reason: str) -> str:
    return reason
