"""Tutor deterministico. Nessun modello e nessun invio cloud."""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .curriculum import UNITS
from .database import connect
from .errors import StudyError

STOP = {
    "alla", "alle", "allo", "come", "cosa", "dagli", "dalla", "delle", "dello", "dove",
    "gli", "il", "indicano", "nella", "nelle", "nello", "non", "per", "perche", "perché",
    "qual", "quale", "quali", "sono", "sul", "sulla", "una", "uno",
}
INJECTION = re.compile(
    r"ignora le istruzioni|ignora le regole|ignore previous|system prompt|cambia la policy|invia tutto|esegui il seguente strumento",
    re.IGNORECASE,
)


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def cloud_adapter() -> None:
    # Deliberately local: no socket, no provider SDK, no fallback.
    raise StudyError(
        409,
        "cloud_disabled",
        "Nessun provider AI è configurato e l'invio cloud è spento. Nessun contenuto è stato trasmesso.",
    )


def _tokens(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-zàèéìòù0-9]{4,}", text.lower()) if token not in STOP]


def _reserve(db_path: Path, day: str, estimate: int, cap: int) -> str | None:
    if estimate > cap:
        return None
    job_id = uuid.uuid4().hex
    with connect(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        used = db.execute(
            "SELECT COALESCE(SUM(cents),0) FROM ai_reservations WHERE day=? AND status='reserved'",
            (day,),
        ).fetchone()[0]
        if int(used) + estimate > cap:
            return None
        db.execute(
            "INSERT INTO ai_reservations(job_id, day, cents, status, created_at) VALUES(?,?,?,'reserved',?)",
            (job_id, day, estimate, utcnow()),
        )
        db.execute(
            """INSERT INTO ai_usage(job_id, model, tokens, estimated_cost, actual_cost, policy, status)
               VALUES(?,?,?,?,NULL,'cloud','reserved')""",
            (job_id, "nessuno", estimate, float(estimate)),
        )
    return job_id


def _release(db_path: Path, job_id: str) -> None:
    with connect(db_path) as db:
        db.execute("UPDATE ai_reservations SET status='released', cents=0 WHERE job_id=?", (job_id,))
        db.execute("UPDATE ai_usage SET status='released', actual_cost=0, tokens=0 WHERE job_id=?", (job_id,))


def answer_cloud(db_path: Path, question: str, estimate: int, cap: int, *, hook=None) -> dict:
    day = utcnow()[:10]
    job_id = _reserve(db_path, day, estimate, cap)
    if not job_id:
        raise StudyError(409, "budget_exceeded", "Limite di spesa raggiunto. Nessuna chiamata è partita.")
    try:
        if hook:
            hook()
        cloud_adapter()
    finally:
        _release(db_path, job_id)
    raise AssertionError("Il provider cloud non restituisce una risposta.")


def _candidate(text: str, **fields) -> dict:
    return {"text": text, **fields}


def _retrieve(db, question: str) -> dict | None:
    wanted = _tokens(question)
    if not wanted:
        return None
    candidates = []
    rows = db.execute(
        """SELECT c.locator, c.text, c.version_id, v.sha256, v.material_id, m.locator AS material_locator
           FROM chunks c
           JOIN material_versions v ON v.id=c.version_id
           JOIN materials m ON m.id=v.material_id
           WHERE v.extraction_state='ready' AND c.quality='extracted'"""
    ).fetchall()
    for row in rows:
        candidates.append(_candidate(
            row["text"], origin="file", version_id=row["version_id"], locator=row["locator"],
            material_id=row["material_id"], material_locator=row["material_locator"], sha256=row["sha256"], title=row["material_locator"],
        ))
    for row in db.execute("SELECT id, title, text FROM added_references ORDER BY created_at"):
        candidates.append(_candidate(
            row["text"], origin="aggiunta", version_id=None, locator=f"reference:{row['id']}",
            material_id=None, material_locator=None, sha256=None, title=row["title"],
        ))
    for unit in UNITS:
        candidates.append(_candidate(
            unit["explanation"], origin="percorso", version_id=None, locator=f"curriculum:{unit['id']}",
            material_id=None, material_locator=None, sha256=None, title=unit["title"],
        ))
    best = None
    best_score = 0
    for item in candidates:
        if INJECTION.search(item["text"]):
            continue
        score = sum(1 for token in wanted if token in item["text"].lower())
        if score > best_score:
            best = item
            best_score = score
    needed = 1 if len(wanted) == 1 else 2
    if not best or best_score < needed:
        return None
    return best


def add_reference(db_path: Path, title: str, text: str) -> dict:
    if INJECTION.search(text) or INJECTION.search(title):
        raise StudyError(422, "reference_rejected", "Il testo sembra un'istruzione per il tutor. Aggiungi un contenuto, non un comando.")
    reference_id = uuid.uuid4().hex
    created = utcnow()
    with connect(db_path) as db:
        db.execute(
            "INSERT INTO added_references(id, title, text, created_at) VALUES(?,?,?,?)",
            (reference_id, title.strip(), text.strip(), created),
        )
    return {"id": reference_id, "title": title.strip(), "created_at": created, "origin": "aggiunta"}


def list_references(db_path: Path) -> dict:
    with connect(db_path) as db:
        rows = db.execute("SELECT id, title, created_at FROM added_references ORDER BY created_at").fetchall()
    return {"items": [dict(row) for row in rows]}


def answer_local(db_path: Path, question: str, session_id: str | None) -> dict:
    with connect(db_path) as db:
        found = _retrieve(db, question)
        if not found:
            text = "Nessun modello generativo è installato. Il corpus indicizzato non sostiene una risposta, quindi mi astengo."
            citations = []
            abstained = 1
        else:
            excerpt = found["text"][:500]
            source = {"file": "un tuo file", "aggiunta": "un testo che hai aggiunto", "percorso": "il percorso ML e DL"}[found["origin"]]
            text = (
                "Nessun modello generativo è installato. Questa è una citazione, non un testo generato. "
                f"Secondo {source}, {found['locator']}: «{excerpt}»"
            )
            citations = [{
                "origin": found["origin"],
                "title": found["title"],
                "version_id": found["version_id"],
                "locator": found["locator"],
                "material_id": found["material_id"],
                "material_locator": found["material_locator"],
                "sha256": found["sha256"],
            }]
            abstained = 0
        turn_id = uuid.uuid4().hex
        db.execute(
            """INSERT INTO tutor_turns(id, policy, question, answer, abstained, citations, created_at)
               VALUES(?,?,?,?,?,?,?)""",
            (turn_id, "local", question, text, abstained, json.dumps(citations, ensure_ascii=False), utcnow()),
        )
    return {
        "id": turn_id,
        "policy": "local",
        "model": None,
        "session_id": session_id,
        "abstained": bool(abstained),
        "answer": text,
        "citations": citations,
        "sent_cloud": False,
    }


def answer(db_path: Path, question: str, policy: str, estimate: int, cap: int, session_id: str | None) -> dict:
    if policy == "off":
        raise StudyError(409, "tutor_off", "Tutor spento. Puoi usare la modalità locale: non installa un modello e non invia dati.")
    if policy == "cloud":
        return answer_cloud(db_path, question, estimate, cap)
    if policy == "local":
        return answer_local(db_path, question, session_id)
    raise StudyError(422, "invalid_policy", "Modalità del tutor non riconosciuta.")
