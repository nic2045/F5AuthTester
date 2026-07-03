"""Active synthetic HTTP probe.

Drives a real request at an F5-published, SHA-protected application and decides whether the
authentication path looks healthy. Two modes, chosen by config:

* Reachability (default): unauthenticated request should be redirected to Entra ID. Seeing
  that redirect proves the APM access policy + Entra federation front door is alive.
* End-to-end: supply a bearer token / cookie via ``send_headers`` and ``success_markers`` to
  confirm the backend SSO variant actually let the request through.
"""

from __future__ import annotations

import time
from contextlib import nullcontext

import httpx

from ..config import ProbeConfig, TargetConfig
from ..models import CheckResult, CheckSource, Status

_MAX_BODY = 200_000  # cap body scanned for markers


def _host_in(url: httpx.URL, hosts: list[str]) -> bool:
    host = url.host or ""
    return any(h.lower() in host.lower() for h in hosts if h)


def _first_marker(body: str, markers: list[str]) -> str | None:
    lowered = body.lower()
    for m in markers:
        if m and m.lower() in lowered:
            return m
    return None


def _build_headers(probe: ProbeConfig, user_agent: str) -> dict[str, str]:
    headers = {"User-Agent": user_agent}
    headers.update(probe.send_headers)
    if probe.bearer_token:
        headers["Authorization"] = f"Bearer {probe.bearer_token}"
    return headers


def _evaluate(
    probe: ProbeConfig, response: httpx.Response, body: str
) -> tuple[Status, str, dict[str, object]]:
    chain_hosts = [h.url.host for h in response.history]
    through_entra = _host_in(response.url, probe.entra_hosts) or any(
        _host_in(h.url, probe.entra_hosts) for h in response.history
    )
    status_ok = response.status_code in probe.expect_status
    failure_hit = _first_marker(body, probe.failure_markers)
    success_hit = _first_marker(body, probe.success_markers) if probe.success_markers else None

    details: dict[str, object] = {
        "final_url": str(response.url),
        "final_status": response.status_code,
        "redirect_chain": chain_hosts,
        "redirected_through_entra": through_entra,
        "matched_failure_marker": failure_hit,
        "matched_success_marker": success_hit,
    }

    if failure_hit:
        return Status.FAIL, f"Auth/SSO error page detected ('{failure_hit}')", details

    if probe.success_markers:
        if success_hit and status_ok:
            return Status.OK, "End-to-end SSO succeeded (success marker present)", details
        if success_hit and not status_ok:
            return (
                Status.WARN,
                f"Success marker found but unexpected status {response.status_code}",
                details,
            )
        return (
            Status.WARN,
            "Reachable, but could not confirm backend SSO (no success marker)",
            details,
        )

    # Reachability mode.
    if probe.expect_entra_redirect:
        if through_entra:
            return Status.OK, "SHA front door alive — redirected to Entra ID", details
        if status_ok:
            return (
                Status.WARN,
                "Reachable but no Entra redirect seen (already authenticated or misconfigured)",
                details,
            )
        return (
            Status.FAIL,
            f"No Entra redirect and unexpected status {response.status_code}",
            details,
        )

    if status_ok:
        return Status.OK, f"Reachable, status {response.status_code}", details
    return Status.FAIL, f"Unexpected status {response.status_code}", details


async def probe_target(
    target: TargetConfig,
    *,
    user_agent: str = "F5AuthTester/0.2",
    client: httpx.AsyncClient | None = None,
) -> CheckResult:
    """Run the active probe against one target and return a CheckResult."""
    probe = target.probe
    headers = _build_headers(probe, user_agent)

    if client is None:
        ctx = httpx.AsyncClient(
            verify=probe.verify_tls,
            follow_redirects=probe.follow_redirects,
            timeout=probe.timeout_s,
        )
    else:
        ctx = nullcontext(client)  # type: ignore[assignment]

    start = time.perf_counter()
    async with ctx as active_client:
        try:
            response = await active_client.request(
                probe.method,
                target.url,
                headers=headers,
                follow_redirects=probe.follow_redirects,
            )
        except httpx.HTTPError as exc:
            latency = (time.perf_counter() - start) * 1000
            return CheckResult(
                source=CheckSource.ACTIVE_PROBE,
                status=Status.FAIL,
                message=f"Request failed: {type(exc).__name__}: {exc}",
                latency_ms=round(latency, 1),
                details={"url": target.url, "error": str(exc)},
            )
        latency = (time.perf_counter() - start) * 1000
        body = response.text[:_MAX_BODY]

    status, message, details = _evaluate(probe, response, body)
    return CheckResult(
        source=CheckSource.ACTIVE_PROBE,
        status=status,
        message=message,
        latency_ms=round(latency, 1),
        details=details,
    )
