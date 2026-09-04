"""KAVI Desktop — native application window.

Opens KAVI in its own chromeless window with its own taskbar icon, rather than
as a tab in a browser. There is no URL bar, no tabs, and no bookmarks: it looks
and behaves like a desktop application.

This adds no dependency. It reuses the Chromium engine already installed on the
machine in "app mode", which is how Chrome and Edge expose a plain window with
no browser furniture. The KAVI server itself still runs locally, in-process,
bound to loopback only.

Usage:
    python kavi_app.py            # open the app window
    python kavi_app.py --port N   # pin a port instead of picking a free one
    python kavi_app.py --keep     # leave the server running after the window closes
"""

from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from kavi.api.routes import build_router  # noqa: E402
from kavi.container import build_service  # noqa: E402
from kavi.server import create_server  # noqa: E402

APP_NAME = "KAVI Desktop"
WINDOW_SIZE = (1600, 1000)

# Where Chromium-based browsers usually live on Windows. The first one that
# exists is used purely as a rendering engine.
BROWSER_CANDIDATES = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
)


def find_browser() -> str | None:
    """Locate an installed Chromium engine, preferring an explicit override."""
    override = os.environ.get("KAVI_BROWSER")
    if override and pathlib.Path(override).is_file():
        return override
    for candidate in BROWSER_CANDIDATES:
        if pathlib.Path(candidate).is_file():
            return candidate
    for name in ("chrome", "msedge", "chromium", "brave"):
        found = shutil.which(name)
        if found:
            return found
    return None


def free_port(preferred: int | None = None) -> int:
    """Pick a usable loopback port.

    A pinned port is honoured only if it is actually free; otherwise a stale
    server from an earlier run would silently serve the old application.
    """
    if preferred:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            if probe.connect_ex(("127.0.0.1", preferred)) != 0:
                return preferred
        print(f"  port {preferred} is already in use; choosing a free one instead")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def start_server(port: int, *, vault: str | None, fixtures: bool):
    """Run the KAVI server on a background thread, bound to loopback only.

    This reuses the same server the CLI launcher uses, so the app window and
    `python run.py` serve byte-identical behaviour.
    """
    service = build_service(vault_path=vault, include_fixtures=fixtures)
    server = create_server(build_router(service), host="127.0.0.1", port=port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def wait_until_ready(url: str, *, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{url}/api/runtime", timeout=2) as response:
                if response.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            time.sleep(0.15)
    return False


def open_window(browser: str, url: str, profile: pathlib.Path) -> subprocess.Popen[bytes]:
    """Open a chromeless application window.

    A dedicated profile directory keeps KAVI out of the Founder's ordinary
    browsing session: separate history, separate cookies, its own taskbar icon.
    """
    profile.mkdir(parents=True, exist_ok=True)
    width, height = WINDOW_SIZE
    return subprocess.Popen(
        [
            browser,
            f"--app={url}",
            f"--user-data-dir={profile}",
            f"--window-size={width},{height}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-features=Translate,AutofillServerCommunication",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--port", type=int, default=None,
                        help="pin a port instead of choosing a free one")
    parser.add_argument("--vault", default=None, help="path to the canonical KAVI Vault")
    parser.add_argument("--no-fixtures", action="store_true",
                        help="hide development fixture data")
    parser.add_argument("--keep", action="store_true",
                        help="leave the server running after the window closes")
    args = parser.parse_args()

    browser = find_browser()
    if browser is None:
        print("No Chromium-based browser was found, so the app window cannot open.")
        print("Set KAVI_BROWSER to a chrome.exe or msedge.exe path, or run:")
        print("    python run.py")
        print("and open the address it prints.")
        return 1

    port = free_port(args.port)
    url = f"http://127.0.0.1:{port}"
    server = start_server(port, vault=args.vault, fixtures=not args.no_fixtures)

    print(f"  {APP_NAME}")
    print(f"  engine   {pathlib.Path(browser).name}")
    print(f"  serving  {url}  (loopback only)")

    if not wait_until_ready(url):
        print("  the local server did not become ready; nothing was opened")
        server.shutdown()
        return 1

    profile = pathlib.Path(
        os.environ.get("LOCALAPPDATA", pathlib.Path.home())
    ) / "kavi-desktop" / "window-profile"
    window = open_window(browser, url, profile)
    print("  window   open — close it to quit\n")

    try:
        window.wait()
    except KeyboardInterrupt:
        window.terminate()
    finally:
        if not args.keep:
            server.shutdown()
            server.server_close()
            print("  KAVI Desktop closed.")
        else:
            print(f"  window closed; server still running at {url}")
            try:
                threading.Event().wait()
            except KeyboardInterrupt:
                server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
