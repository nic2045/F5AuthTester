"""F5 BIG-IP iControl REST check.

Logs in to the BIG-IP management plane with token auth and inspects the APM objects that
back a target: the access profile and, where the variant maps to one, the SSO configuration
object. Confirming these exist and are reachable complements the active data-plane probe.

Connectivity or auth problems to the management plane are reported as UNKNOWN (we simply
could not verify), not FAIL, so a management-plane hiccup never masquerades as a broken login.
"""

from __future__ import annotations

import time
from contextlib import nullcontext

import httpx

from ..config import F5Config, TargetConfig
from ..models import CheckResult, CheckSource, Status
from ..variants import meta_for


def _obj_path(partition: str, name: str) -> str:
    return f"~{partition}~{name}"


async def _login(client: httpx.AsyncClient, f5: F5Config) -> str:
    resp = await client.post(
        "/mgmt/shared/authn/login",
        json={
            "username": f5.username,
            "password": f5.password,
            "loginProviderName": "tmos",
        },
    )
    resp.raise_for_status()
    token = resp.json().get("token", {}).get("token")
    if not token:
        raise httpx.HTTPError("login response contained no auth token")
    return token


async def check_target(
    f5: F5Config,
    target: TargetConfig,
    *,
    client: httpx.AsyncClient | None = None,
) -> CheckResult:
    """Inspect the BIG-IP APM objects backing one target via iControl REST."""
    if not f5.enabled or not f5.host:
        return CheckResult(
            source=CheckSource.ICONTROL,
            status=Status.SKIPPED,
            message="iControl REST not configured",
        )

    if client is None:
        ctx = httpx.AsyncClient(
            base_url=f"https://{f5.host}",
            verify=f5.verify_tls,
            timeout=f5.timeout_s,
        )
    else:
        ctx = nullcontext(client)  # type: ignore[assignment]

    start = time.perf_counter()
    async with ctx as c:
        try:
            token = await _login(c, f5)
            c.headers["X-F5-Auth-Token"] = token
            status, message, details = await _inspect(c, target)
        except httpx.HTTPError as exc:
            latency = (time.perf_counter() - start) * 1000
            return CheckResult(
                source=CheckSource.ICONTROL,
                status=Status.UNKNOWN,
                message=f"Could not query BIG-IP: {type(exc).__name__}: {exc}",
                latency_ms=round(latency, 1),
                details={"host": f5.host},
            )
        latency = (time.perf_counter() - start) * 1000

    return CheckResult(
        source=CheckSource.ICONTROL,
        status=status,
        message=message,
        latency_ms=round(latency, 1),
        details=details,
    )


async def _get_json(client: httpx.AsyncClient, url: str) -> tuple[int, dict]:
    resp = await client.get(url)
    if resp.status_code == 404:
        return 404, {}
    resp.raise_for_status()
    return resp.status_code, resp.json()


async def _inspect(
    client: httpx.AsyncClient, target: TargetConfig
) -> tuple[Status, str, dict[str, object]]:
    apm = target.apm
    meta = meta_for(target.variant)
    details: dict[str, object] = {"partition": apm.partition}
    problems: list[str] = []

    # Access profile.
    if apm.access_profile:
        path = _obj_path(apm.partition, apm.access_profile)
        code, data = await _get_json(client, f"/mgmt/tm/apm/profile/access/{path}")
        details["access_profile"] = apm.access_profile
        if code == 404:
            problems.append(f"access profile '{apm.access_profile}' not found")
        else:
            details["access_profile_found"] = True
            # Best-effort live-session read; not all versions expose the same stats shape.
            try:
                _, stats = await _get_json(client, f"/mgmt/tm/apm/profile/access/{path}/stats")
                details["active_sessions"] = _extract_sessions(stats)
            except httpx.HTTPError:
                pass

    # SSO object, when the variant maps to one.
    if meta.icontrol_sso_type and apm.sso_config:
        path = _obj_path(apm.partition, apm.sso_config)
        code, _ = await _get_json(client, f"/mgmt/tm/apm/sso/{meta.icontrol_sso_type}/{path}")
        details["sso_type"] = meta.icontrol_sso_type
        details["sso_config"] = apm.sso_config
        if code == 404:
            problems.append(f"{meta.icontrol_sso_type} SSO object '{apm.sso_config}' not found")
        else:
            details["sso_config_found"] = True

    if not apm.access_profile and not apm.sso_config:
        return (
            Status.SKIPPED,
            "No APM objects configured for this target",
            details,
        )

    if problems:
        return Status.WARN, "; ".join(problems), details
    return Status.OK, "APM objects present on BIG-IP", details


def _extract_sessions(stats: dict) -> int | None:
    """Pull the active-session gauge out of an iControl stats payload if present."""
    entries = stats.get("entries", {})
    for entry in entries.values():
        nested = entry.get("nestedStats", {}).get("entries", {})
        for key, val in nested.items():
            if key.lower().endswith("currentactivesessions") or key.lower().endswith(
                "currentactiveallowedsessions"
            ):
                return val.get("value")
    return None
