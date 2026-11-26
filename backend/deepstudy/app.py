from __future__ import annotations

import hmac
from pathlib import Path
import secrets
import threading
import uuid

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from .backup import MAX_ARCHIVE_BYTES, export_profile, restore_profile, is_empty_profile
from .catalog import ALLOWLIST, CatalogError, create_import, engine_name, get_chunks, get_job, list_materials, recover_interrupted_jobs, request_interrupt, resume_job
from .database import SCHEMA_VERSION, migrate, read_settings, save_settings
from .models import ImportRequest, Settings


def create_app(profile: Path, origin: str, bootstrap_token: str, static_dir: Path | None = None):
    profile.mkdir(parents=True, exist_ok=True)
    db = profile / "deepstudy.db"
    repo_root = Path(__file__).resolve().parents[2]
    migrate(db)
    recover_interrupted_jobs(db)
    lock = threading.RLock()
    session = secrets.token_urlsafe(32)
    bootstrap_available = True
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    expected_host = origin.removeprefix("http://")
    cookie_name = f"deepstudy_{expected_host.rsplit(':', 1)[-1]}"

    def error(status: int, code: str, message: str, request_id: str):
        return JSONResponse(status_code=status, content={"code": code, "message": message, "retryable": False, "request_id": request_id})

    @app.middleware("http")
    async def boundary(request: Request, call_next):
        request_id = uuid.uuid4().hex
        request.state.request_id = request_id
        if request.headers.get("host") != expected_host:
            return error(403, "invalid_host", "Host non autorizzato.", request_id)
        request_origin = request.headers.get("origin")
        if request_origin and request_origin != origin:
            return error(403, "invalid_origin", "Origine non autorizzata.", request_id)
        if request.headers.get("sec-fetch-site") == "cross-site":
            return error(403, "cross_site", "Richiesta esterna non autorizzata.", request_id)
        if request.method not in ("GET", "HEAD") and request_origin != origin:
            return error(403, "origin_required", "Origine locale richiesta.", request_id)
        if request.url.path.startswith("/api/") and request.url.path != "/api/session":
            supplied = request.cookies.get(cookie_name, "")
            if not hmac.compare_digest(supplied.encode(), session.encode()):
                return error(401, "unauthenticated", "Sessione scaduta. Riapri DeepStudy dal programma di avvio.", request_id)
        try:
            response = await call_next(request)
        except Exception:
            # Never log request headers, bodies, tokens, or local paths.
            response = error(500, "internal_error", "Operazione non riuscita. I dati esistenti sono conservati.", request_id)
        response.headers["X-Request-ID"] = request_id
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, _exc):
        return error(422, "invalid_input", "Valori non validi. Controlla i campi inseriti.", request.state.request_id)

    @app.post("/api/session")
    def authenticate(request: Request):
        nonlocal bootstrap_available
        with lock:
            supplied = request.headers.get("authorization", "")
            if not bootstrap_available or not hmac.compare_digest(supplied.encode(), f"Bearer {bootstrap_token}".encode()):
                return error(401, "invalid_bootstrap", "Collegamento scaduto. Riapri DeepStudy.", request.state.request_id)
            bootstrap_available = False
        response = JSONResponse({"authenticated": True})
        # HTTP is restricted to loopback; no remote use. Cookie is never readable by JS.
        response.set_cookie(cookie_name, session, httponly=True, samesite="strict", path="/api")
        return response

    @app.get("/api/status")
    def status():
        with lock:
            return {"milestone": "M2", "schema_version": SCHEMA_VERSION, "mode": "local", "ai_enabled": False,
                    "sync_enabled": False, "profile": profile.name, "can_restore": is_empty_profile(profile),
                    "import_formats": sorted(ALLOWLIST), "ocr_engine": engine_name()}

    @app.get("/api/settings")
    def settings():
        with lock:
            return read_settings(db)

    @app.put("/api/settings")
    def update_settings(value: Settings, request: Request):
        with lock:
            try:
                return save_settings(db, value.model_dump(exclude={"revision"}), value.revision)
            except ValueError as exc:
                return error(409, "revision_conflict", str(exc), request.state.request_id)

    def catalog_error(exc: CatalogError, request: Request):
        return error(exc.status, exc.code, str(exc), request.state.request_id)

    @app.post("/api/imports")
    def start_import(body: ImportRequest, request: Request):
        try:
            return create_import(profile, repo_root, body.locator, body.idempotency_key)
        except CatalogError as exc:
            return catalog_error(exc, request)

    @app.get("/api/jobs/{job_id}")
    def job(job_id: str, request: Request):
        try:
            return get_job(db, job_id)
        except CatalogError as exc:
            return catalog_error(exc, request)

    @app.post("/api/jobs/{job_id}/interrupt")
    def interrupt(job_id: str, request: Request):
        try:
            return request_interrupt(db, job_id)
        except CatalogError as exc:
            return catalog_error(exc, request)

    @app.post("/api/jobs/{job_id}/resume")
    def resume(job_id: str, request: Request):
        try:
            return resume_job(profile, job_id)
        except CatalogError as exc:
            return catalog_error(exc, request)

    @app.get("/api/materials")
    def materials(kind: str | None = None, state: str | None = None, limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0)):
        return list_materials(db, kind=kind, state=state, limit=limit, offset=offset)

    @app.get("/api/materials/{material_id}/versions/{version_id}/chunks")
    def chunks(material_id: str, version_id: str, request: Request):
        try:
            return get_chunks(db, material_id, version_id)
        except CatalogError as exc:
            return catalog_error(exc, request)

    @app.post("/api/exports")
    def export(request: Request):
        with lock:
            try:
                payload = export_profile(profile)
            except ValueError as exc:
                return error(400, "export_failed", str(exc), request.state.request_id)
        return Response(payload, media_type="application/zip", headers={"Content-Disposition": 'attachment; filename="deepstudy-backup.zip"'})

    @app.post("/api/restore")
    async def restore(request: Request):
        payload = bytearray()
        async for block in request.stream():
            if len(payload) + len(block) > MAX_ARCHIVE_BYTES:
                return error(413, "archive_too_large", "Limite backup M1: 64 MiB.", request.state.request_id)
            payload.extend(block)
        # File validation/SQLite must not block the event loop.
        from starlette.concurrency import run_in_threadpool
        def apply_restore():
            with lock:
                restore_profile(profile, bytes(payload))
        try:
            await run_in_threadpool(apply_restore)
        except ValueError as exc:
            return error(400, "restore_rejected", str(exc), request.state.request_id)
        return {"restored": True}

    if static_dir:
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
    return app
