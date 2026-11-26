"""Esecuzione su richiesta, in un namespace senza rete e senza i file dell'host."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile

from .database import connect
from .errors import StudyError

SANDBOX = "unshare-user-mount-net"


def utcnow() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sandbox_available() -> bool:
    return shutil.which("unshare") is not None and os.name == "posix"


def _store(db_path: Path, result: dict, source: str, timeout_s: float) -> dict:
    digest = hashlib.sha256(source.encode()).hexdigest()
    with connect(db_path) as db:
        db.execute(
            """INSERT INTO lab_runs(id, state, timeout_s, exit_code, stdout, stderr, source_sha256, created_at)
               VALUES(?,?,?,?,?,?,?,?)""",
            (result["id"], result["state"], timeout_s, result.get("exit_code"), result["stdout"], result["stderr"], digest, utcnow()),
        )
    result["source_sha256"] = digest
    result["rubric"] = {
        "stato": "non_approvata",
        "proposta_v0_1": {"correttezza": 35, "metodo": 25, "riproducibilita": 20, "spiegazione": 20},
        "soglia": None,
        "esito": "nessun voto assegnato",
        "note": "P05 non è approvata: il laboratorio non assegna 80/100 né un superamento.",
    }
    return result


def run_lab(db_path: Path, source: str, timeout_s: int) -> dict:
    import uuid
    run_id = uuid.uuid4().hex
    if not sandbox_available():
        return _store(db_path, {
            "id": run_id, "state": "sandbox_unavailable", "exit_code": None, "stdout": "",
            "stderr": "Isolamento non disponibile: il codice non è stato eseguito.", "sandbox": None,
        }, source, timeout_s)
    root = Path(tempfile.mkdtemp(prefix="ds-jail-"))
    env = {
        "PATH": "/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1]),
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "LAB_ROOT": str(root),
        "LAB_TIMEOUT": str(timeout_s),
    }
    command = [
        "unshare", "--user", "--map-root-user", "--mount", "--net", "--fork", "--pid", "--mount-proc",
        sys.executable, "-m", "deepstudy.labs", "--sandbox",
    ]
    process = subprocess.Popen(
        command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=env, start_new_session=True, text=True,
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(source, timeout=timeout_s + 2)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=3)
        stdout, stderr = "", "Tempo massimo superato. Il processo è stato fermato."
        parsed = None
    else:
        parsed = _parse_sandbox(stdout)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    if timed_out or parsed is None and process.returncode in (-signal.SIGKILL, -9):
        return _store(db_path, {
            "id": run_id, "state": "timeout", "exit_code": None, "stdout": stdout[:4000],
            "stderr": stderr[:4000], "sandbox": SANDBOX,
        }, source, timeout_s)
    if parsed is None:
        return _store(db_path, {
            "id": run_id, "state": "failed", "exit_code": process.returncode, "stdout": "",
            "stderr": (stderr or "Isolamento non riuscito. Il codice non è stato eseguito sull'host.")[:4000],
            "sandbox": SANDBOX,
        }, source, timeout_s)
    state = parsed.get("state")
    if state not in ("completed", "failed", "timeout"):
        state = "completed" if parsed["exit_code"] == 0 else "failed"
    return _store(db_path, {
        "id": run_id, "state": state, "exit_code": parsed["exit_code"],
        "stdout": parsed["stdout"][:4000], "stderr": parsed["stderr"][:4000], "sandbox": SANDBOX,
    }, source, timeout_s)


def _parse_sandbox(stdout: str) -> dict | None:
    line = stdout.strip().splitlines()[-1] if stdout.strip() else ""
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict) or "exit_code" not in payload:
        return None
    return payload


def _sandbox_main() -> None:
    source = sys.stdin.read(8001)
    if len(source) > 8000:
        print(json.dumps({"exit_code": None, "stdout": "", "stderr": "Codice troppo lungo."}))
        return
    root = Path(os.environ["LAB_ROOT"])
    binds: list[Path] = []
    try:
        for name in ("usr", "tmp", "proc", "dev", "etc"):
            (root / name).mkdir(exist_ok=True)
        def bind(src: str, dst: Path) -> None:
            source = Path(src)
            if source.exists() and not source.is_symlink():
                subprocess.run(["mount", "--bind", src, str(dst)], check=True)
                binds.append(dst)
        bind("/usr", root / "usr")
        for link, target in (("bin", "usr/bin"), ("lib", "usr/lib"), ("lib64", "usr/lib64")):
            alias = root / link
            if not alias.exists():
                alias.symlink_to(target)
        subprocess.run(["mount", "-t", "proc", "proc", str(root / "proc")], check=True)
        binds.append(root / "proc")
        subprocess.run(["mount", "-t", "tmpfs", "-o", "size=8m", "tmpfs", str(root / "tmp")], check=True)
        binds.append(root / "tmp")
        cache = Path("/etc/ld.so.cache")
        if cache.exists():
            target = root / "etc" / "ld.so.cache"
            target.write_bytes(b"")
            bind(str(cache), target)
        (root / "tmp" / "student.py").write_text(source, encoding="utf-8")
        child = subprocess.run(
            [sys.executable, "-m", "deepstudy.labs", "--chroot", str(root)],
            capture_output=True, text=True, env={
                "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
                "PYTHONNOUSERSITE": "1", "LAB_TIMEOUT": os.environ.get("LAB_TIMEOUT", "2"),
            }, timeout=int(os.environ.get("LAB_TIMEOUT", "2")) + 1,
        )
        sys.stdout.write(child.stdout)
        if child.returncode != 0 and not child.stdout:
            print(json.dumps({"exit_code": child.returncode, "stdout": "", "stderr": child.stderr[-1000:]}))
    except Exception as exc:
        print(json.dumps({"exit_code": None, "stdout": "", "stderr": f"Isolamento non riuscito: {type(exc).__name__}"}))
    finally:
        for mount in reversed(binds):
            subprocess.run(["umount", "-l", str(mount)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _chroot_main(root: str) -> None:
    import resource
    os.chroot(root)
    os.chdir("/tmp")
    timeout = int(os.environ.get("LAB_TIMEOUT", "2"))
    python = "/usr/bin/python3.12" if Path("/usr/bin/python3.12").exists() else "/usr/bin/python3"

    def limits() -> None:
        cpu = max(1, timeout)
        resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
        resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_FSIZE, (1_000_000, 1_000_000))
        resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))

    try:
        completed = subprocess.run(
            [python, "-I", "/tmp/student.py"],
            capture_output=True, text=True, timeout=timeout,
            env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": "/tmp", "TMPDIR": "/tmp", "PYTHONNOUSERSITE": "1"},
            preexec_fn=limits,
        )
        payload = {"exit_code": completed.returncode, "stdout": completed.stdout[-4000:], "stderr": completed.stderr[-4000:]}
    except subprocess.TimeoutExpired as exc:
        payload = {"exit_code": None, "state": "timeout", "stdout": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "", "stderr": "Tempo massimo superato dentro l'isolamento."}
    print(json.dumps(payload))


if __name__ == "__main__":
    if "--sandbox" in sys.argv:
        _sandbox_main()
    elif "--chroot" in sys.argv:
        _chroot_main(sys.argv[-1])
