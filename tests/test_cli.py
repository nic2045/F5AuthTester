import argparse

import f5authtester.config as config_mod
import f5authtester.runner as runner_mod
from f5authtester.__main__ import _check
from f5authtester.config import AppConfig, LoadedConfig
from f5authtester.models import (
    CheckResult,
    CheckSource,
    Report,
    Status,
    TargetResult,
    Variant,
)


def _patch(monkeypatch, statuses: list[Status]) -> None:
    def fake_load(_explicit=None):
        return LoadedConfig(config=AppConfig(), source="test")

    def fake_run(_cfg):
        results = [
            TargetResult.from_checks(
                f"t{i}",
                Variant.HEADER,
                "https://x/",
                [CheckResult(source=CheckSource.ACTIVE_PROBE, status=s)],
            )
            for i, s in enumerate(statuses)
        ]
        return Report(results=results)

    monkeypatch.setattr(config_mod, "load_config", fake_load)
    monkeypatch.setattr(runner_mod, "run_report_sync", fake_run)


def _args() -> argparse.Namespace:
    return argparse.Namespace(config=None, json=False)


def test_check_exit_zero_when_all_ok(monkeypatch, capsys):
    _patch(monkeypatch, [Status.OK, Status.SKIPPED])
    assert _check(_args()) == 0
    assert "Summary" in capsys.readouterr().out


def test_check_exit_two_on_fail(monkeypatch):
    _patch(monkeypatch, [Status.OK, Status.FAIL])
    assert _check(_args()) == 2


def test_check_exit_three_when_no_ok(monkeypatch):
    _patch(monkeypatch, [Status.WARN, Status.SKIPPED])
    assert _check(_args()) == 3


def test_check_json_output(monkeypatch, capsys):
    _patch(monkeypatch, [Status.OK])
    args = argparse.Namespace(config=None, json=True)
    assert _check(args) == 0
    assert '"summary"' in capsys.readouterr().out
