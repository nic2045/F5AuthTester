from fastapi.testclient import TestClient

import f5authtester.web.app as webapp
from f5authtester.models import (
    CheckResult,
    CheckSource,
    Report,
    Status,
    TargetResult,
    Variant,
)
from f5authtester.web import create_app


def _canned_report() -> Report:
    checks = [
        CheckResult(
            source=CheckSource.ACTIVE_PROBE, status=Status.OK, message="ok", latency_ms=12.3
        ),
        CheckResult(source=CheckSource.ICONTROL, status=Status.SKIPPED, message="not configured"),
    ]
    return Report(
        results=[TargetResult.from_checks("Intranet", Variant.KERBEROS_KCD, "https://x/", checks)]
    )


def _client(monkeypatch) -> TestClient:
    async def fake_run_report(cfg):
        return _canned_report()

    monkeypatch.setattr(webapp, "run_report", fake_run_report)
    return TestClient(create_app())


def test_healthz(monkeypatch):
    with _client(monkeypatch) as client:
        resp = client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


def test_api_status_has_report(monkeypatch):
    with _client(monkeypatch) as client:
        resp = client.get("/api/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["report"]["results"][0]["name"] == "Intranet"
        assert body["report"]["summary"]["ok"] == 1


def test_dashboard_renders(monkeypatch):
    with _client(monkeypatch) as client:
        resp = client.get("/")
        assert resp.status_code == 200
        assert "F5" in resp.text and "Auth" in resp.text


def test_api_run_triggers_refresh(monkeypatch):
    with _client(monkeypatch) as client:
        resp = client.post("/api/run")
        assert resp.status_code == 200
        assert resp.json()["results"][0]["variant"] == "kerberos_kcd"
