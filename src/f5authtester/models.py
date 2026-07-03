"""Domain models shared across checks, runner and web layers."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class Variant(str, Enum):
    """The F5 APM SSO / authentication variants this app knows how to check."""

    KERBEROS_KCD = "kerberos_kcd"
    HEADER = "header"
    FORMS = "forms"
    SAML = "saml"
    NTLM = "ntlm"
    OAUTH = "oauth"


class Status(str, Enum):
    """Health status of a single check or an aggregated target."""

    OK = "ok"
    WARN = "warn"
    FAIL = "fail"
    UNKNOWN = "unknown"
    SKIPPED = "skipped"


class CheckSource(str, Enum):
    """Where a check result came from."""

    ACTIVE_PROBE = "active_probe"
    ICONTROL = "icontrol"


# Worst-first ordering used to aggregate several check results into one status.
_SEVERITY = {
    Status.FAIL: 0,
    Status.UNKNOWN: 1,
    Status.WARN: 2,
    Status.OK: 3,
    Status.SKIPPED: 4,
}


def aggregate_status(statuses: list[Status]) -> Status:
    """Combine per-check statuses into one overall status.

    Rules:
    - No statuses (or all skipped) -> UNKNOWN.
    - Otherwise the most severe non-skipped status wins (FAIL > UNKNOWN > WARN > OK).
    """
    relevant = [s for s in statuses if s is not Status.SKIPPED]
    if not relevant:
        return Status.UNKNOWN
    return min(relevant, key=lambda s: _SEVERITY[s])


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class CheckResult(BaseModel):
    """Outcome of one check (one probe, or one iControl query) against one target."""

    source: CheckSource
    status: Status
    message: str = ""
    latency_ms: float | None = None
    details: dict[str, object] = Field(default_factory=dict)
    checked_at: str = Field(default_factory=utcnow_iso)


class TargetResult(BaseModel):
    """Aggregated result for a single configured target across all its checks."""

    name: str
    variant: Variant
    url: str
    status: Status
    checks: list[CheckResult] = Field(default_factory=list)

    @classmethod
    def from_checks(
        cls, name: str, variant: Variant, url: str, checks: list[CheckResult]
    ) -> TargetResult:
        overall = aggregate_status([c.status for c in checks])
        return cls(name=name, variant=variant, url=url, status=overall, checks=checks)


class Report(BaseModel):
    """A full run across every configured target."""

    generated_at: str = Field(default_factory=utcnow_iso)
    results: list[TargetResult] = Field(default_factory=list)

    @property
    def summary(self) -> dict[str, int]:
        counts = {s.value: 0 for s in Status}
        for r in self.results:
            counts[r.status.value] += 1
        return counts

    def model_dump_web(self) -> dict[str, object]:
        data = self.model_dump()
        data["summary"] = self.summary
        return data
