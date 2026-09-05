#!/usr/bin/env python3
"""Launch KAVI Desktop (Founder Cockpit) in LOCAL / DEVELOPMENT MODE."""

from __future__ import annotations

import argparse
import sys
import threading
import webbrowser

from kavi.api.routes import build_router
from kavi.container import build_service
from kavi.infrastructure.store import default_data_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="KAVI Desktop v0.1 — Founder Cockpit")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8760)
    parser.add_argument("--vault", default=None, help="Path to the canonical KAVI Vault")
    parser.add_argument("--data", default=None, help="Path to the local store JSON file")
    parser.add_argument("--no-fixtures", action="store_true", help="Hide development fixture data")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument(
        "--set-password", action="store_true",
        help="Set or change the cockpit password, then exit. Required before "
             "binding to anything other than 127.0.0.1.")
    parser.add_argument(
        "--execution", default="hermes", choices=("null", "hermes", "ssh"),
        help="Which runtime the Run button may use. 'null' refuses everything.",
    )
    args = parser.parse_args(argv)

    from kavi.infrastructure.auth import Auth
    auth = Auth()

    if args.set_password:
        import getpass
        first = getpass.getpass("New cockpit password (min 10 chars): ")
        if first != getpass.getpass("Repeat it: "):
            print("They do not match. Nothing was changed.")
            return 1
        try:
            auth.set_password(first)
        except ValueError as error:
            print(f"Refused: {error}")
            return 1
        print("Password set. Existing sessions were invalidated.")
        return 0

    # Refuse to serve the vault to a network without a password. This is the
    # whole reason the cockpit was loopback-only until now.
    if args.host not in ("127.0.0.1", "localhost", "::1") and not auth.enabled():
        print(f"REFUSED: binding to {args.host} exposes the canonical vault "
              "with no password.")
        print("Set one first:  python run.py --set-password")
        return 1

    service = build_service(
        data_path=args.data,
        vault_path=args.vault,
        include_fixtures=not args.no_fixtures,
        execution_adapter=args.execution,
    )
    router = build_router(service)

    from kavi.server import create_server

    try:
        server = create_server(router, args.host, args.port, auth=auth)
    except OSError as exc:
        print(f"cannot bind {args.host}:{args.port} — {exc}", file=sys.stderr)
        return 1

    url = f"http://{args.host}:{args.port}"
    vault_status = service.vault.status()

    print("KAVI Desktop v0.1 — Founder Cockpit")
    print("  mode          LOCAL / DEVELOPMENT MODE")
    print("  engine room   NOT CONNECTED")
    print(f"  url           {url}")
    print(f"  data          {args.data or default_data_dir() / 'kavi.json'}")
    print(
        "  vault         "
        + (f"{vault_status['path']} ({vault_status['note_count']} notes, READ ONLY)"
           if vault_status["available"] else "NOT FOUND — pass --vault")
    )
    print("  fixtures      " + ("hidden" if args.no_fixtures else "shown, labelled FIXTURE"))
    print("\nCtrl+C to stop.")

    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
