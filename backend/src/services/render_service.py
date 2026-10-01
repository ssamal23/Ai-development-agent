import base64
import json
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _kill_tree(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return

    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
        )
    else:
        process.terminate()


def _wait_for_server(url: str, process: subprocess.Popen, timeout: int) -> bool:
    deadline = time.time() + timeout

    while time.time() < deadline:
        if process.poll() is not None:
            return False

        try:
            with urllib.request.urlopen(url, timeout=2):
                return True
        except Exception:
            time.sleep(1)

    return False


def render_workspace(
    workspace_path: str | Path,
    route: str = "/",
    viewport_width: int = 1440,
    install_timeout: int = 420,
    start_timeout: int = 90,
) -> tuple[str | None, str | None]:
    """
    Start the workspace's dev server, screenshot its root page,
    and stop the server.

    Returns (png_base64, error); exactly one is None. Any
    failure (no dev script, install error, server never came
    up, Playwright missing) comes back as an error string so the
    design review can be skipped rather than failing the ticket.
    """

    workspace = Path(workspace_path)
    package_json = workspace / "package.json"

    if not package_json.exists():
        return None, "No package.json in the workspace."

    try:
        scripts = json.loads(
            package_json.read_text(encoding="utf-8")
        ).get("scripts", {})
    except (OSError, json.JSONDecodeError):
        return None, "Could not read package.json."

    if "dev" not in scripts:
        return None, "package.json has no 'dev' script."

    npm = shutil.which("npm")

    if not npm:
        return None, "npm is not installed."

    if not (workspace / "node_modules").exists():
        try:
            install = subprocess.run(
                [npm, "install", "--no-audit", "--no-fund"],
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=install_timeout,
            )
        except subprocess.TimeoutExpired:
            return None, "npm install timed out."

        if install.returncode != 0:
            return None, (
                "npm install failed: "
                f"{install.stderr.strip()[-500:]}"
            )

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None, "Playwright is not installed."

    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    url = base_url + "/"
    page_url = base_url + (
        route if route.startswith(("/", "#")) else "/" + route
    )

    server = subprocess.Popen(
        [
            npm, "run", "dev", "--",
            "--host", "127.0.0.1",
            "--port", str(port),
            "--strictPort",
        ],
        cwd=workspace,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        if not _wait_for_server(url, server, start_timeout):
            return None, "The dev server did not start."

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(
                viewport={"width": viewport_width, "height": 900}
            )
            page.goto(page_url, wait_until="networkidle", timeout=30000)
            image = page.screenshot(full_page=True)
            browser.close()

        return base64.b64encode(image).decode(), None

    except Exception as error:
        return None, f"Could not screenshot the app: {error}"

    finally:
        _kill_tree(server)
