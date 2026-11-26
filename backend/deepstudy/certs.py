"""Simulazioni locali. Nessuna certificazione ufficiale è selezionata."""
from __future__ import annotations

import json
import uuid
from pathlib import Path

from .curriculum import LOCAL_BLUEPRINT, ensure_mock_bank
from .database import connect
from .errors import StudyError
from .quiz import record_attempt, score_answer, utcnow


def list_blueprints(db_path: Path) -> dict:
    with connect(db_path) as db:
        rows = db.execute(
            "SELECT id, provider, code, version, checked_at, source, status FROM exam_blueprints ORDER BY checked_at, id"
        ).fetchall()
    return {
        "certification_chosen": False,
        "items": [dict(row) for row in rows],
        "note": "L03 è aperta: questi blueprint sono bozze locali, non esami ufficiali.",
    }


def create_blueprint(db_path: Path, version: str, source: str, question_ids: list[str]) -> dict:
    lowered = source.lower()
    if "parola dump" in lowered or "exam dump" in lowered or "sono un dump" in lowered:
        raise StudyError(422, "dump_rejected", "I dump d'esame non sono accettati.")
    blueprint_id = "bp-" + uuid.uuid4().hex[:16]
    with connect(db_path) as db:
        ensure_mock_bank(db)
        for question_id in question_ids:
            row = db.execute(
                """SELECT q.review, m.bank, m.origin FROM question_versions q
                   JOIN question_meta m ON m.question_version_id=q.id WHERE q.id=?""",
                (question_id,),
            ).fetchone()
            if not row or row["bank"] != "mock" or row["origin"] != "authored" or row["review"] != "reviewed":
                raise StudyError(422, "question_not_in_mock_bank", "La simulazione accetta solo quesiti originali della banca mock.")
        db.execute(
            """INSERT INTO exam_blueprints(id, provider, code, version, checked_at, source, status)
               VALUES(?,?,?,?,?,?,?)""",
            (blueprint_id, "locale", "NESSUNA", version, utcnow()[:10], source, "bozza"),
        )
        for position, question_id in enumerate(question_ids):
            db.execute(
                "INSERT INTO blueprint_questions(blueprint_id, position, question_version_id) VALUES(?,?,?)",
                (blueprint_id, position, question_id),
            )
    return {"id": blueprint_id, "provider": "locale", "code": "NESSUNA", "version": version, "status": "bozza"}


def _open_payload(db, mock_id: str) -> dict:
    mock = db.execute("SELECT * FROM mock_sessions WHERE id=?", (mock_id,)).fetchone()
    if not mock:
        raise StudyError(404, "mock_not_found", "Simulazione non trovata.")
    items = db.execute(
        """SELECT i.position, q.id, q.prompt, q.options, m.kind
           FROM mock_items i
           JOIN question_versions q ON q.id=i.question_version_id
           JOIN question_meta m ON m.question_version_id=q.id
           WHERE i.mock_id=? ORDER BY i.position""",
        (mock_id,),
    ).fetchall()
    payload = {
        "id": mock["id"],
        "blueprint_id": mock["blueprint_id"],
        "state": mock["state"],
        "started_at": mock["started_at"],
        "questions": [
            {"position": row["position"], "id": row["id"], "prompt": row["prompt"], "options": json.loads(row["options"]), "kind": row["kind"]}
            for row in items
        ],
        "hints": False,
    }
    if mock["state"] == "closed":
        payload["closed_at"] = mock["closed_at"]
        payload["report"] = json.loads(mock["report"])
    return payload


def start_mock(db_path: Path, blueprint_id: str) -> dict:
    with connect(db_path) as db:
        ensure_mock_bank(db)
        if not db.execute("SELECT 1 FROM exam_blueprints WHERE id=?", (blueprint_id,)).fetchone():
            raise StudyError(404, "blueprint_not_found", "Blueprint non trovato.")
        questions = db.execute(
            "SELECT question_version_id FROM blueprint_questions WHERE blueprint_id=? ORDER BY position",
            (blueprint_id,),
        ).fetchall()
        if not questions:
            raise StudyError(409, "blueprint_empty", "Il blueprint non ha quesiti.")
        mock_id = uuid.uuid4().hex
        now = utcnow()
        db.execute(
            "INSERT INTO mock_sessions(id, blueprint_id, state, started_at) VALUES(?,?, 'open', ?)",
            (mock_id, blueprint_id, now),
        )
        for position, row in enumerate(questions):
            db.execute(
                "INSERT INTO mock_items(mock_id, position, question_version_id) VALUES(?,?,?)",
                (mock_id, position, row["question_version_id"]),
            )
        return _open_payload(db, mock_id)


def get_mock(db_path: Path, mock_id: str) -> dict:
    with connect(db_path) as db:
        return _open_payload(db, mock_id)


def answer_mock(db_path: Path, mock_id: str, attempt_id: str, question_id: str, answer: list[str]) -> dict:
    with connect(db_path) as db:
        mock = db.execute("SELECT state FROM mock_sessions WHERE id=?", (mock_id,)).fetchone()
        if not mock:
            raise StudyError(404, "mock_not_found", "Simulazione non trovata.")
        if mock["state"] != "open":
            raise StudyError(409, "mock_closed", "La simulazione è già chiusa. Il rapporto non cambia.")
        if not db.execute(
            "SELECT 1 FROM mock_items WHERE mock_id=? AND question_version_id=?", (mock_id, question_id)
        ).fetchone():
            raise StudyError(404, "question_not_in_mock", "Quesito estraneo a questa simulazione.")
    record_attempt(db_path, attempt_id, question_id, answer, reveal=False)
    with connect(db_path) as db:
        db.execute(
            """INSERT INTO mock_answers(mock_id, question_version_id, attempt_id) VALUES(?,?,?)
               ON CONFLICT(mock_id, question_version_id) DO NOTHING""",
            (mock_id, question_id, attempt_id),
        )
    return {"accepted": True, "id": attempt_id, "mock_id": mock_id}


def close_mock(db_path: Path, mock_id: str) -> dict:
    with connect(db_path) as db:
        mock = db.execute("SELECT * FROM mock_sessions WHERE id=?", (mock_id,)).fetchone()
        if not mock:
            raise StudyError(404, "mock_not_found", "Simulazione non trovata.")
        if mock["state"] == "closed":
            return _open_payload(db, mock_id)
        items = db.execute(
            """SELECT q.id, q.objective_id, q.solution, q.prompt, m.kind, o.title
               FROM mock_items i
               JOIN question_versions q ON q.id=i.question_version_id
               JOIN question_meta m ON m.question_version_id=q.id
               JOIN objectives o ON o.id=q.objective_id
               WHERE i.mock_id=? ORDER BY i.position""",
            (mock_id,),
        ).fetchall()
        domains: dict[str, dict] = {}
        answered = 0
        correct = 0
        for item in items:
            attempt = db.execute(
                """SELECT a.answer, a.score FROM mock_answers ma
                   JOIN attempts a ON a.id=ma.attempt_id
                   WHERE ma.mock_id=? AND ma.question_version_id=?""",
                (mock_id, item["id"]),
            ).fetchone()
            domain = domains.setdefault(item["objective_id"], {"objective_id": item["objective_id"], "title": item["title"], "correct": 0, "total": 0})
            domain["total"] += 1
            if attempt:
                answered += 1
                points = score_answer(item["kind"], item["solution"], json.loads(attempt["answer"]))
                if points >= 1:
                    domain["correct"] += 1
                    correct += 1
        report = {
            "answered": answered,
            "correct": correct,
            "total": len(items),
            "domains": list(domains.values()),
            "pass_probability": None,
            "note": "Punteggio di questa simulazione. Non è una probabilità di promozione e non usa un esame ufficiale.",
            "certification_chosen": False,
        }
        closed = utcnow()
        db.execute(
            "UPDATE mock_sessions SET state='closed', closed_at=?, report=? WHERE id=?",
            (closed, json.dumps(report, ensure_ascii=False), mock_id),
        )
        return _open_payload(db, mock_id)


def seed_local_blueprint(db_path: Path) -> dict:
    with connect(db_path) as db:
        ensure_mock_bank(db)
    return {"id": LOCAL_BLUEPRINT["id"], "certification_chosen": False}
