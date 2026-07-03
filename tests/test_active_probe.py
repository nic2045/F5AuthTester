import asyncio

import httpx

from f5authtester.checks.active import probe_target
from f5authtester.config import ProbeConfig, TargetConfig
from f5authtester.models import Status, Variant


def _run(target: TargetConfig, handler) -> object:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=True)

    async def go():
        try:
            return await probe_target(target, client=client)
        finally:
            await client.aclose()

    return asyncio.run(go())


def test_entra_redirect_is_ok():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "login.microsoftonline.com":
            return httpx.Response(200, text="please authenticate")
        return httpx.Response(
            302, headers={"Location": "https://login.microsoftonline.com/authorize"}
        )

    target = TargetConfig(name="KCD", variant=Variant.KERBEROS_KCD, url="https://app.internal/")
    result = _run(target, handler)
    assert result.status == Status.OK
    assert result.details["redirected_through_entra"] is True


def test_failure_marker_is_fail():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="Access was denied by the access policy")

    target = TargetConfig(name="HR", variant=Variant.HEADER, url="https://app.internal/")
    result = _run(target, handler)
    assert result.status == Status.FAIL
    assert "Access was denied" in result.details["matched_failure_marker"]


def test_success_marker_is_ok():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text='{"authenticated": true, "user": "alice"}')

    target = TargetConfig(
        name="API",
        variant=Variant.OAUTH,
        url="https://app.internal/whoami",
        probe=ProbeConfig(expect_entra_redirect=False, success_markers=['"authenticated": true']),
    )
    result = _run(target, handler)
    assert result.status == Status.OK


def test_transport_error_is_fail():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    target = TargetConfig(name="Down", variant=Variant.FORMS, url="https://app.internal/")
    result = _run(target, handler)
    assert result.status == Status.FAIL
    assert "Request failed" in result.message
