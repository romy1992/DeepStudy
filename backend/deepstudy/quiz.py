"""Quesiti, punteggi e ripassi. Il client non invia il punteggio."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .curriculum import UNITS, ensure_study_questions, unit
from .database import connect
from .errors import StudyError
from .exchange import device_id, record_event

ALGORITHM = "ripasso-v1"


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def stamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())


def score_answer(kind: str, solution_raw: str, answer: list[str]) -> float:
    if kind == "flashcard":
        expected = json.loads(solution_raw)
        return 1.0 if len(answer) == 1 and _normalize(answer[0]) == _normalize(expected[0]) else 0.0
    expected = json.loads(solution_raw)
    if not isinstance(expected, list) or any(not isinstance(item, str) for item in answer):
        raise StudyError(422, "invalid_answer", "Risposta non leggibile.")
    if len(answer) != len(set(answer)):
        return 0.0
    if kind == "single":
        return 1.0 if answer == expected else 0.0
    return 1.0 if set(answer) == set(expected) else 0.0


def _public_attempt(row, question, *, replayed: bool, reveal: bool) -> dict:
    payload = {
        "id": row["id"],
        "question_version_id": row["question_version_id"],
        "replayed": replayed,
        "timestamp": row["timestamp"],
    }
    if reveal:
        payload.update({
            "score": row["score"],
            "answer": json.loads(row["answer"]),
            "solution": json.loads(question["solution"]),
            "rationale": question["rationale"],
            "next_review_at": None,
        })
    return payload


def _mock_is_open(db, question_id: str) -> bool:
    return db.execute(
        """SELECT 1 FROM mock_items i JOIN mock_sessions s ON s.id=i.mock_id
           WHERE i.question_version_id=? AND s.state='open'""",
        (question_id,),
    ).fetchone() is not None


def record_attempt(db_path: Path, attempt_id: str, question_id: str, answer: list[str], *, timestamp: str | None = None, reveal: bool = True) -> dict:
    when = timestamp or utcnow()
    canonical = json.dumps(answer, ensure_ascii=False)
    with connect(db_path) as db:
        question = db.execute(
            """SELECT q.*, m.kind, m.bank, m.origin FROM question_versions q
               JOIN question_meta m ON m.question_version_id=q.id WHERE q.id=?""",
            (question_id,),
        ).fetchone()
        if not question:
            raise StudyError(404, "question_not_found", "Quesito non trovato.")
        if reveal and _mock_is_open(db, question_id):
            raise StudyError(409, "mock_in_progress", "Durante la simulazione il punteggio resta nascosto.")
        existing = db.execute("SELECT * FROM attempts WHERE id=?", (attempt_id,)).fetchone()
        if existing:
            if existing["question_version_id"] != question_id or existing["answer"] != canonical:
                raise StudyError(409, "attempt_conflict", "Questo identificativo appartiene già a un altro tentativo.")
            payload = _public_attempt(existing, question, replayed=True, reveal=reveal)
            if reveal:
                payload["next_review_at"] = _due_for_objective(db, question["objective_id"])
            return payload
        points = score_answer(question["kind"], question["solution"], answer)
        device = device_id(db)
        db.execute(
            "INSERT INTO attempts(id, device_id, question_version_id, answer, score, timestamp) VALUES(?,?,?,?,?,?)",
            (attempt_id, device, question_id, canonical, points, when),
        )
        record_event(db, kind="attempt", entity_id=attempt_id, base_revision=None, body={
            "id": attempt_id,
            "device_id": device,
            "question_version_id": question_id,
            "answer": canonical,
            "score": points,
            "timestamp": when,
        })
        if question["bank"] != "mock":
            rebuild_reviews(db, when)
        row = db.execute("SELECT * FROM attempts WHERE id=?", (attempt_id,)).fetchone()
        payload = _public_attempt(row, question, replayed=False, reveal=reveal)
        if reveal:
            payload["next_review_at"] = _due_for_objective(db, question["objective_id"])
        return payload


def create_question(db_path: Path, body) -> dict:
    question_id = "q-" + uuid.uuid4().hex[:16]
    options = [item.model_dump() for item in body.options]
    if body.kind == "flashcard" and options:
        raise StudyError(422, "invalid_question", "La flashcard non ha opzioni.")
    if body.kind != "flashcard" and len(options) < 2:
        raise StudyError(422, "invalid_question", "Servono almeno due opzioni.")
    option_ids = {item["id"] for item in options}
    if body.kind != "flashcard" and any(item not in option_ids for item in body.solution):
        raise StudyError(422, "invalid_question", "La soluzione indica un'opzione inesistente.")
    review = "ai_draft" if body.origin == "ai_draft" else "reviewed"
    with connect(db_path) as db:
        ensure_study_questions(db)
        if not db.execute("SELECT 1 FROM objectives WHERE id=?", (body.objective_id,)).fetchone():
            raise StudyError(404, "objective_not_found", "Obiettivo sconosciuto.")
        db.execute(
            """INSERT INTO question_versions(id, objective_id, prompt, options, solution, rationale, sources, review)
               VALUES(?,?,?,?,?,?,?,?)""",
            (question_id, body.objective_id, body.prompt, json.dumps(options, ensure_ascii=False),
             json.dumps(body.solution, ensure_ascii=False), body.rationale, "[]", review),
        )
        db.execute(
            "INSERT INTO question_meta(question_version_id, bank, family, kind, origin) VALUES(?,?,?,?,?)",
            (question_id, body.bank, body.family, body.kind, body.origin),
        )
    return {"id": question_id, "review": review, "origin": body.origin, "bank": body.bank, "family": body.family}


def promote_question(db_path: Path, question_id: str) -> dict:
    with connect(db_path) as db:
        row = db.execute(
            """SELECT q.*, m.bank, m.family, m.kind, m.origin FROM question_versions q
               JOIN question_meta m ON m.question_version_id=q.id WHERE q.id=?""",
            (question_id,),
        ).fetchone()
        if not row:
            raise StudyError(404, "question_not_found", "Quesito non trovato.")
        if row["origin"] != "ai_draft":
            raise StudyError(409, "not_a_draft", "Solo una bozza AI si promuove, e resta riconoscibile.")
        new_id = "q-" + uuid.uuid4().hex[:16]
        db.execute(
            """INSERT INTO question_versions(id, objective_id, prompt, options, solution, rationale, sources, review)
               VALUES(?,?,?,?,?,?,?,?)""",
            (new_id, row["objective_id"], row["prompt"], row["options"], row["solution"], row["rationale"], row["sources"], "reviewed"),
        )
        db.execute(
            "INSERT INTO question_meta(question_version_id, bank, family, kind, origin) VALUES(?,?,?,?,?)",
            (new_id, row["bank"], row["family"], row["kind"], "ai_draft"),
        )
    return {
        "id": new_id,
        "previous_id": question_id,
        "review": "reviewed",
        "origin": "ai_draft",
        "evaluative": False,
        "note": "La bozza resta marcata come AI e non entra nella simulazione né sblocca il percorso.",
    }


def correct_objectives(db) -> set[str]:
    rows = db.execute(
        """SELECT DISTINCT q.objective_id FROM attempts a
           JOIN question_versions q ON q.id=a.question_version_id
           JOIN question_meta m ON m.question_version_id=q.id
           WHERE a.score >= 1 AND m.bank='study' AND m.origin='authored' AND q.review='reviewed'"""
    ).fetchall()
    return {row[0] for row in rows}


def mastery_rows(db) -> list[dict]:
    titles = {item["id"]: item["title"] for item in UNITS}
    sessions = {
        row["objective_id"]: row["n"]
        for row in db.execute("SELECT objective_id, COUNT(*) AS n FROM study_sessions GROUP BY objective_id")
    }
    practice = {
        row["objective_id"]
        for row in db.execute("SELECT DISTINCT objective_id FROM practice_marks")
    }
    attempts = db.execute(
        """SELECT q.objective_id, a.score, a.timestamp FROM attempts a
           JOIN question_versions q ON q.id=a.question_version_id
           JOIN question_meta m ON m.question_version_id=q.id
           WHERE m.bank='study' AND m.origin='authored' AND q.review='reviewed' AND a.score >= 1"""
    ).fetchall()
    days: dict[str, set[str]] = {}
    for row in attempts:
        days.setdefault(row["objective_id"], set()).add(row["timestamp"][:10])
    rows = []
    for item in UNITS:
        objective_id = item["id"]
        correct_days = len(days.get(objective_id, ()))
        opened = sessions.get(objective_id, 0)
        if objective_id in practice and correct_days >= 2:
            level, reason = "consolidato", "Prova pratica e risposte corrette in almeno due giorni UTC distinti."
        elif correct_days >= 1:
            level = "in_corso"
            missing = []
            if correct_days < 2:
                missing.append("una seconda giornata con un quesito corretto")
            if objective_id not in practice:
                missing.append("una prova pratica registrata")
            reason = "Manca " + " e ".join(missing) + "."
        elif opened:
            level, reason = "letto", "La sessione è stata aperta. Non risulta un tentativo corretto."
        else:
            level, reason = "non_iniziato", "Nessuna lettura e nessun tentativo."
        rows.append({"id": objective_id, "title": titles[objective_id], "level": level, "reason": reason, "reading_sessions": opened})
    return rows


def _interval(streak: int, correct: bool) -> int:
    if not correct:
        return 1
    if streak <= 1:
        return 3
    return 7


def rebuild_reviews(db, now: str) -> list[dict]:
    grouped: dict[str, list] = {}
    rows = db.execute(
        """SELECT q.objective_id, a.score, a.timestamp FROM attempts a
           JOIN question_versions q ON q.id=a.question_version_id
           JOIN question_meta m ON m.question_version_id=q.id
           WHERE m.bank IN ('study','flashcard') AND m.origin='authored' AND q.review='reviewed'
           ORDER BY a.timestamp, a.id"""
    ).fetchall()
    for row in rows:
        grouped.setdefault(row["objective_id"], []).append(row)
    db.execute("DELETE FROM review_states")
    titles = {item["id"]: item["title"] for item in UNITS}
    due = []
    for objective_id, attempts in grouped.items():
        streak = 0
        last = attempts[-1]
        for attempt in attempts:
            correct = attempt["score"] >= 1
            streak = streak + 1 if correct else 0
        interval = _interval(streak, last["score"] >= 1)
        due_at = stamp(parse_ts(last["timestamp"]) + timedelta(days=interval))
        reason = (
            f"L'ultimo tentativo su {titles.get(objective_id, objective_id)} non è corretto. Algoritmo {ALGORITHM}, intervallo {interval} giorni."
            if last["score"] < 1
            else f"Intervallo {ALGORITHM} di {interval} giorni dopo un tentativo corretto su {titles.get(objective_id, objective_id)}."
        )
        db.execute(
            "INSERT INTO review_states(objective_id, algorithm_version, due_at) VALUES(?,?,?)",
            (objective_id, ALGORITHM, due_at),
        )
        if due_at <= now:
            due.append({"objective_id": objective_id, "title": titles.get(objective_id, objective_id), "due_at": due_at, "reason": reason, "algorithm": ALGORITHM})
    due.sort(key=lambda item: item["due_at"])
    return due


def _due_for_objective(db, objective_id: str) -> str | None:
    row = db.execute("SELECT due_at FROM review_states WHERE objective_id=?", (objective_id,)).fetchone()
    return row["due_at"] if row else None


def reviews_due(db_path: Path, *, now: str | None = None) -> dict:
    clock = now or utcnow()
    with connect(db_path) as db:
        items = rebuild_reviews(db, clock)
        stored = [dict(row) for row in db.execute("SELECT objective_id, algorithm_version, due_at FROM review_states ORDER BY due_at")]
    return {"algorithm": ALGORITHM, "now": clock, "due": items, "states": stored}


def flashcards(db_path: Path) -> dict:
    with connect(db_path) as db:
        rows = db.execute(
            """SELECT q.id, q.objective_id, q.prompt, m.kind, m.origin, q.review
               FROM question_versions q JOIN question_meta m ON m.question_version_id=q.id
               WHERE m.bank='flashcard' ORDER BY q.id"""
        ).fetchall()
    return {"items": [dict(row) for row in rows]}
