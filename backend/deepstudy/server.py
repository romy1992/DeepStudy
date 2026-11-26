"""Single profile/process, bound to an OS-assigned loopback port."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import secrets
import socket
import sys
import threading
import time
import webbrowser
import uvicorn
from .app import create_app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--desktop", action="store_true")
    parser.add_argument("--profile", default="default")
    parser.add_argument("--data-root", type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,47}", args.profile):
        parser.error("Nome profilo: 1–48 lettere, numeri, trattini o underscore.")
    root = Path(__file__).resolve().parents[2]
    data_root = args.data_root or Path(os.environ.get("LOCALAPPDATA", Path.home())) / "DeepStudy" / "profiles"
    profile = (data_root.resolve() / args.profile).resolve()
    if profile.is_relative_to((root / "docs").resolve()):
        parser.error("I profili non possono risiedere nella documentazione originale.")
    profile.mkdir(parents=True, exist_ok=True)
    # Advisory byte lock released automatically even after a crash.
    profile_lock = (profile / ".lock").open("a+b")
    profile_lock.seek(0)
    if os.name == "nt":
        import msvcrt
        try:
            msvcrt.locking(profile_lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            sys.exit("Profilo già aperto. Chiudi la sessione precedente o usa un altro profilo.")
    static_dir = root / "frontend" / "dist"
    if not (static_dir / "index.html").exists():
        sys.exit("Interfaccia assente. Esegui npm run build.")
    token = secrets.token_urlsafe(32)
    sock = socket.socket()
    if os.name == "nt":
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    app = create_app(profile, origin, token, static_dir)
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", access_log=False, proxy_headers=False))
    url = f"{origin}/#token={token}"

    def launch():
        while not server.started and not server.should_exit:
            time.sleep(0.025)
        if not server.started:
            return
        if args.desktop:
            # Private pipe consumed by Rust. Never write this handshake to a log.
            print(json.dumps({"url": url}), flush=True)
        else:
            webbrowser.open(url)
            print("DeepStudy aperto nel browser. Per chiudere il servizio premi Ctrl+C.", flush=True)

    def watch_parent():
        sys.stdin.buffer.read()  # EOF when the owning desktop process closes or crashes
        server.should_exit = True

    threading.Thread(target=launch, daemon=True).start()
    if args.desktop:
        threading.Thread(target=watch_parent, daemon=True).start()
    try:
        server.run(sockets=[sock])
    finally:
        sock.close()
        profile_lock.close()


if __name__ == "__main__":
    main()
