"""Orchestrates checks across all configured targets and aggregates the report."""

from __future__ import annotations

import asyncio

from .checks import active, icontrol
from .config import AppConfig, TargetConfig
from .models import CheckResult, CheckSource, Report, Status, TargetResult


async def _check_one(cfg: AppConfig, target: TargetConfig) -> TargetResult:
    probe_result, icontrol_result = await asyncio.gather(
        active.probe_target(target, user_agent=cfg.user_agent),
        icontrol.check_target(cfg.f5, target),
        return_exceptions=True,
    )

    checks: list[CheckResult] = [
        _normalize(probe_result, CheckSource.ACTIVE_PROBE),
        _normalize(icontrol_result, CheckSource.ICONTROL),
    ]
    return TargetResult.from_checks(target.name, target.variant, target.url, checks)


def _normalize(result: object, source: CheckSource) -> CheckResult:
    """Convert an unexpected exception from gather() into a FAIL CheckResult."""
    if isinstance(result, CheckResult):
        return result
    return CheckResult(
        source=source,
        status=Status.FAIL,
        message=f"Check crashed: {type(result).__name__}: {result}",
    )


async def run_report(cfg: AppConfig) -> Report:
    """Run every enabled target concurrently and return an aggregated Report."""
    targets = [t for t in cfg.targets if t.enabled]
    results = await asyncio.gather(*(_check_one(cfg, t) for t in targets))
    return Report(results=list(results))


def run_report_sync(cfg: AppConfig) -> Report:
    """Convenience synchronous wrapper around :func:`run_report`."""
    return asyncio.run(run_report(cfg))
