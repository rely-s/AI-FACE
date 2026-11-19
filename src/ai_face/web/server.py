"""Server launcher for AI-FACE Clinical Web Platform."""

import threading
import time
import webbrowser
from pathlib import Path

import uvicorn

from ai_face.constants import DEFAULT_MODEL_PATH
from ai_face.web.app import create_app


def open_browser(url: str, delay_s: float = 1.0) -> None:
    """Open web browser in background thread after delay."""
    time.sleep(delay_s)
    webbrowser.open(url)


def run_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    model_path: str | Path = DEFAULT_MODEL_PATH,
    auto_open: bool = True,
) -> None:
    """Start FastAPI uvicorn server for AI-FACE."""
    app = create_app(model_path=model_path)
    url = f"http://{host}:{port}"
    print(f"\n[AI-FACE Web Platform] Server running at: {url}")
    print("[AI-FACE Web Platform] Press Ctrl+C in terminal to stop.")

    if auto_open:
        threading.Thread(target=open_browser, args=(url,), daemon=True).start()

    uvicorn.run(app, host=host, port=port, log_level="info")
