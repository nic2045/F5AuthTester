"""FastAPI application: dashboard + JSON API + background polling scheduler."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from .. import __version__
from ..config import LoadedConfig, load_config
from ..models import Report
from ..runner import run_report
from ..variants import VARIANT_META

log = logging.getLogger("f5authtester")

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_STATIC_DIR = Path(__file__).parent / "static"


@dataclass
class AppState:
    loaded: LoadedConfig
    report: Report | None = None
    last_run: str | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    scheduler_task: asyncio.Task | None = None


async def _refresh(state: AppState) -> Report:
    """Run all checks once and cache the result. Serialized via the state lock."""
    async with state.lock:
        report = await run_report(state.loaded.config)
        state.report = report
        state.last_run = report.generated_at
        return report


async def _scheduler(state: AppState) -> None:
    interval = max(15, state.loaded.config.poll_interval_s)
    while True:
        try:
            await _refresh(state)
        except Exception:  # noqa: BLE001 - scheduler must never die on a single failure
            log.exception("scheduled refresh failed")
        await asyncio.sleep(interval)


def create_app(config_path: str | None = None) -> FastAPI:
    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        state: AppState = app.state.f5  # set below before startup
        try:
            await _refresh(state)
        except Exception:  # noqa: BLE001
            log.exception("initial refresh failed")
        state.scheduler_task = asyncio.create_task(_scheduler(state))
        yield
        state.scheduler_task.cancel()

    app = FastAPI(title="F5AuthTester", version=__version__, lifespan=lifespan)
    app.state.f5 = AppState(loaded=load_config(config_path))

    if _STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    def _state(request: Request) -> AppState:
        return request.app.state.f5

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request) -> HTMLResponse:
        state = _state(request)
        report = state.report
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "version": __version__,
                "source": state.loaded.source,
                "poll_interval": state.loaded.config.poll_interval_s,
                "report": report.model_dump_web() if report else None,
                "variant_meta": {
                    v.value: {"label": m.label, "backend_sso": m.backend_sso}
                    for v, m in VARIANT_META.items()
                },
            },
        )

    @app.get("/api/status")
    async def api_status(request: Request) -> JSONResponse:
        state = _state(request)
        payload = {
            "version": __version__,
            "source": state.loaded.source,
            "poll_interval_s": state.loaded.config.poll_interval_s,
            "last_run": state.last_run,
            "report": state.report.model_dump_web() if state.report else None,
        }
        return JSONResponse(payload)

    @app.post("/api/run")
    async def api_run(request: Request) -> JSONResponse:
        state = _state(request)
        report = await _refresh(state)
        return JSONResponse(report.model_dump_web())

    @app.get("/healthz")
    async def healthz() -> JSONResponse:
        return JSONResponse({"status": "ok", "version": __version__})

    return app
