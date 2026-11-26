"""Scambio locale di eventi. Nessun provider remoto e nessun pacchetto cifrato."""
from __future__ import annotations

import json
import uuid
from pathlib import Path

from .database import connect
from .errors import StudyError


def device_id(db) -> str:
    row = db.execute("SELECT device_id FROM local_device WHERE id=1").fetchone()
    if row:
        return row["device_id"]
    value = "dev_" + uuid.uuid4().hex[:16]
    db.execute("INSERT INTO local_device(id, device_id) VALUES(1,?)", (value,))
    return value


def record_event(db, *, kind: str, entity_id: str, base_revision: str | None, body: dict) -> str:
    event_id = uuid.uuid4().hex
    payload = json.dumps({"kind": kind, "device_id": body.get("device_id") or device_id(db), "body": body}, ensure_ascii=False)
    if len(payload) > 20_000:
        raise StudyError(413, "event_too_large", "Evento troppo grande per la coda locale.")
    db.execute(
        """INSERT INTO sync_events(id, entity_id, base_revision, payload_version, payload, ack_state)
           VALUES(?,?,?,?,?,'pending')""",
        (event_id, entity_id, base_revision, 1, payload),
    )
    db.execute("INSERT INTO sync_log(event_id) VALUES(?)", (event_id,))
    return event_id


def _apply_one(db, event: dict) -> dict:
    if not isinstance(event, dict):
        raise StudyError(422, "invalid_event", "Evento non leggibile.", retryable=False)
    event_id = event.get("id")
    entity_id = event.get("entity_id")
    payload = event.get("payload")
    if not isinstance(event_id, str) or not isinstance(entity_id, str) or not isinstance(payload, dict):
        raise StudyError(422, "invalid_event", "Evento incompleto.", retryable=False)
    if db.execute("SELECT 1 FROM sync_events WHERE id=?", (event_id,)).fetchone():
        return {"id": event_id, "status": "duplicate", "conflict": False, "retryable": False}
    kind = payload.get("kind")
    body = payload.get("body")
    if kind not in ("note", "attempt", "tombstone") or not isinstance(body, dict):
        raise StudyError(422, "invalid_event", "Tipo di evento non riconosciuto.", retryable=False)
    conflict = False
    status = "applied"
    if kind == "note":
        version_id = body.get("version_id")
        content = body.get("content")
        owner = body.get("device_id") or payload.get("device_id") or "sconosciuto"
        if not isinstance(version_id, str) or not isinstance(content, str):
            raise StudyError(422, "invalid_event", "Nota incompleta.", retryable=False)
        existing = db.execute("SELECT content FROM note_versions WHERE id=?", (version_id,)).fetchone()
        if existing and existing["content"] != content:
            conflict = True
            status = "kept_original"
        elif not existing:
            db.execute(
                "INSERT INTO note_versions(id, note_id, base_version, content, device_id) VALUES(?,?,?,?,?)",
                (version_id, entity_id, event.get("base_revision"), content, owner),
            )
    elif kind == "tombstone":
        db.execute(
            "INSERT INTO tombstones(entity_id, entity_kind, at) VALUES(?,?,?) ON CONFLICT(entity_id) DO NOTHING",
            (entity_id, body.get("entity_kind") or "note", body.get("at") or ""),
        )
    elif kind == "attempt":
        from .quiz import score_answer
        question_id = body.get("question_version_id")
        question = db.execute(
            """SELECT q.solution, m.kind FROM question_versions q
               JOIN question_meta m ON m.question_version_id=q.id WHERE q.id=?""",
            (question_id,),
        ).fetchone()
        if not question:
            return {"id": event_id, "status": "waiting_question", "conflict": False, "retryable": True}
        try:
            answer = json.loads(body.get("answer", "[]"))
        except json.JSONDecodeError:
            raise StudyError(422, "invalid_event", "Risposta dell'evento non leggibile.") from None
        points = score_answer(question["kind"], question["solution"], answer)
        existing = db.execute("SELECT answer, score FROM attempts WHERE id=?", (body.get("id") or entity_id,)).fetchone()
        attempt_key = body.get("id") or entity_id
        if existing:
            if existing["answer"] != body.get("answer"):
                conflict = True
                status = "kept_original"
        else:
            db.execute(
                "INSERT INTO attempts(id, device_id, question_version_id, answer, score, timestamp) VALUES(?,?,?,?,?,?)",
                (attempt_key, body.get("device_id") or payload.get("device_id") or "sconosciuto",
                 question_id, body.get("answer"), points, body.get("timestamp") or ""),
            )
    encoded = json.dumps(payload, ensure_ascii=False)
    db.execute(
        """INSERT INTO sync_events(id, entity_id, base_revision, payload_version, payload, ack_state)
           VALUES(?,?,?,?,?,'acked')""",
        (event_id, entity_id, event.get("base_revision"), int(event.get("payload_version") or 1), encoded),
    )
    db.execute("INSERT INTO sync_log(event_id) VALUES(?)", (event_id,))
    return {"id": event_id, "status": status, "conflict": conflict, "retryable": False}


def exchange(db_path: Path, known_ids: list[str], events: list[dict]) -> dict:
    if len(events) > 500:
        raise StudyError(413, "too_many_events", "Troppi eventi in un solo scambio.")
    with connect(db_path) as db:
        device_id(db)
        applied = [_apply_one(db, event) for event in events]
        known = set(known_ids) | {item["id"] for item in applied if item["status"] != "waiting_question"}
        rows = db.execute(
            """SELECT e.id, e.entity_id, e.base_revision, e.payload_version, e.payload, e.ack_state, l.seq
               FROM sync_events e JOIN sync_log l ON l.event_id=e.id ORDER BY l.seq"""
        ).fetchall()
        outgoing = []
        for row in rows:
            if row["id"] in known:
                continue
            outgoing.append({
                "id": row["id"],
                "entity_id": row["entity_id"],
                "base_revision": row["base_revision"],
                "payload_version": row["payload_version"],
                "payload": json.loads(row["payload"]),
                "seq": row["seq"],
            })
        cursor = rows[-1]["seq"] if rows else 0
    return {
        "applied": applied,
        "conflicts": [item for item in applied if item["conflict"]],
        "outgoing": outgoing,
        "cursor": cursor,
        "transport": "locale-non-cifrato",
        "remote": False,
        "encryption": "non configurata: le chiavi remote non sono state scelte",
    }


def remote_blocked() -> None:
    raise StudyError(403, "sync_remote_unavailable", "Nessun provider di sincronizzazione è configurato. Nessun dato è stato inviato.")
