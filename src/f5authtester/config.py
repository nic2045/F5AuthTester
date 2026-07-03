"""Configuration models and loading for F5AuthTester.

Config is YAML. Any string value may reference an environment variable with ``${VAR}``
syntax — use this for secrets (F5 password, bearer tokens) so they never live in the file.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from .models import Variant

_ENV_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)\}")


def _expand_env(value: object) -> object:
    """Recursively replace ``${VAR}`` in strings with environment values (empty if unset)."""
    if isinstance(value, str):
        return _ENV_PATTERN.sub(lambda m: os.environ.get(m.group(1), ""), value)
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    return value


class ProbeConfig(BaseModel):
    """Expectations for the active, synthetic HTTP probe against a published app."""

    method: str = "GET"
    timeout_s: float = 10.0
    verify_tls: bool = True
    follow_redirects: bool = True
    # When unauthenticated, an SHA-protected app should bounce the user to Entra ID.
    # Seeing that redirect proves the APM access policy + Entra federation front door is alive.
    expect_entra_redirect: bool = True
    entra_hosts: list[str] = Field(
        default_factory=lambda: ["login.microsoftonline.com", "login.microsoft.com"]
    )
    # HTTP status codes considered healthy for the *final* response.
    expect_status: list[int] = Field(default_factory=lambda: [200])
    # Substrings whose presence in the final body proves backend SSO succeeded.
    success_markers: list[str] = Field(default_factory=list)
    # Substrings whose presence signals an auth/SSO error (e.g. F5 logon page, 401 text).
    failure_markers: list[str] = Field(
        default_factory=lambda: [
            "Access was denied",
            "APM_ACCESS_DENY",
            "Session could not be established",
            "single sign-on",  # F5 SSO error pages commonly mention this
        ]
    )
    # Optional headers / bearer token to drive an authenticated end-to-end transaction.
    send_headers: dict[str, str] = Field(default_factory=dict)
    bearer_token: str | None = None


class ApmConfig(BaseModel):
    """Per-target pointers into the BIG-IP config, used by the iControl REST check."""

    partition: str = "Common"
    access_profile: str | None = None
    sso_config: str | None = None


class TargetConfig(BaseModel):
    name: str
    variant: Variant
    url: str
    enabled: bool = True
    probe: ProbeConfig = Field(default_factory=ProbeConfig)
    apm: ApmConfig = Field(default_factory=ApmConfig)


class F5Config(BaseModel):
    """Global BIG-IP iControl REST connection settings."""

    enabled: bool = False
    host: str = ""
    username: str = ""
    password: str = ""
    verify_tls: bool = True
    timeout_s: float = 15.0


class AppConfig(BaseModel):
    poll_interval_s: int = 300
    user_agent: str = "F5AuthTester/0.2"
    f5: F5Config = Field(default_factory=F5Config)
    targets: list[TargetConfig] = Field(default_factory=list)


def _demo_config() -> AppConfig:
    """Built-in example used when no config file is present, so the UI is never empty."""
    return AppConfig(
        poll_interval_s=300,
        targets=[
            TargetConfig(
                name="Intranet (KCD)",
                variant=Variant.KERBEROS_KCD,
                url="https://intranet.example.com/",
                apm=ApmConfig(access_profile="ap_intranet", sso_config="kcd_intranet"),
            ),
            TargetConfig(
                name="HR Portal (Header)",
                variant=Variant.HEADER,
                url="https://hr.example.com/",
                apm=ApmConfig(access_profile="ap_hr"),
            ),
            TargetConfig(
                name="Legacy App (Forms)",
                variant=Variant.FORMS,
                url="https://legacy.example.com/login",
                apm=ApmConfig(access_profile="ap_legacy", sso_config="form_legacy"),
            ),
            TargetConfig(
                name="Partner SP (SAML)",
                variant=Variant.SAML,
                url="https://partner.example.com/",
                apm=ApmConfig(access_profile="ap_partner", sso_config="saml_partner"),
            ),
            TargetConfig(
                name="SharePoint (NTLM)",
                variant=Variant.NTLM,
                url="https://sp.example.com/",
                apm=ApmConfig(access_profile="ap_sp", sso_config="ntlm_sp"),
            ),
            TargetConfig(
                name="API Gateway (OAuth)",
                variant=Variant.OAUTH,
                url="https://api.example.com/health",
                apm=ApmConfig(access_profile="ap_api", sso_config="oauth_api"),
            ),
        ],
    )


class LoadedConfig(BaseModel):
    config: AppConfig
    source: str  # human-readable origin ("demo", or the file path)


def resolve_config_path(explicit: str | os.PathLike[str] | None = None) -> Path | None:
    if explicit:
        return Path(explicit)
    env = os.environ.get("F5AUTHTESTER_CONFIG")
    if env:
        return Path(env)
    default = Path("config.yaml")
    return default if default.exists() else None


def load_config(explicit: str | os.PathLike[str] | None = None) -> LoadedConfig:
    """Load config from the resolved path, or fall back to the built-in demo config."""
    path = resolve_config_path(explicit)
    if path is None:
        return LoadedConfig(config=_demo_config(), source="demo")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    expanded = _expand_env(raw)
    return LoadedConfig(config=AppConfig.model_validate(expanded), source=str(path))
