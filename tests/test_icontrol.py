import asyncio

import httpx

from f5authtester.checks.icontrol import check_target
from f5authtester.config import ApmConfig, F5Config, TargetConfig
from f5authtester.models import Status, Variant


def _run(f5: F5Config, target: TargetConfig, handler) -> object:
    client = httpx.AsyncClient(
        base_url="https://bigip.test", transport=httpx.MockTransport(handler)
    )

    async def go():
        try:
            return await check_target(f5, target, client=client)
        finally:
            await client.aclose()

    return asyncio.run(go())


def _f5() -> F5Config:
    return F5Config(enabled=True, host="bigip.test", username="svc", password="pw")


def _target(sso_config: str | None = "kcd_app") -> TargetConfig:
    return TargetConfig(
        name="KCD App",
        variant=Variant.KERBEROS_KCD,
        url="https://app.test/",
        apm=ApmConfig(access_profile="ap_app", sso_config=sso_config),
    )


def _login_ok(request: httpx.Request) -> httpx.Response | None:
    if request.url.path == "/mgmt/shared/authn/login":
        return httpx.Response(200, json={"token": {"token": "abc123"}})
    return None


def test_skipped_when_disabled():
    result = _run(F5Config(enabled=False), _target(), lambda r: httpx.Response(200))
    assert result.status == Status.SKIPPED


def test_ok_when_objects_present():
    def handler(request: httpx.Request) -> httpx.Response:
        login = _login_ok(request)
        if login is not None:
            return login
        return httpx.Response(200, json={"name": "obj"})

    result = _run(_f5(), _target(), handler)
    assert result.status == Status.OK
    assert result.details["sso_config_found"] is True


def test_warn_when_sso_object_missing():
    def handler(request: httpx.Request) -> httpx.Response:
        login = _login_ok(request)
        if login is not None:
            return login
        if "/apm/sso/" in request.url.path:
            return httpx.Response(404, json={"code": 404})
        return httpx.Response(200, json={"name": "ap_app"})

    result = _run(_f5(), _target(), handler)
    assert result.status == Status.WARN
    assert "not found" in result.message


def test_unknown_when_login_fails():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "auth failed"})

    result = _run(_f5(), _target(), handler)
    assert result.status == Status.UNKNOWN
    assert "Could not query BIG-IP" in result.message
