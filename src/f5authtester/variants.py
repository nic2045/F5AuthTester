"""Metadata describing each F5 APM SSO / auth variant.

The Entra ID Secure Hybrid Access (SHA) flow is the same at the front door for every
variant — the user is redirected to Entra ID, authenticates (with MFA), and is sent back
to the BIG-IP with a SAML assertion / OIDC token. The variants differ in how the BIG-IP
then performs SSO to the *backend* application. These definitions capture that difference
and map each variant to the iControl REST SSO object type used to inspect it.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import Variant


@dataclass(frozen=True)
class VariantMeta:
    label: str
    short: str
    description: str
    backend_sso: str
    # tmsh/iControl SSO object type, e.g. GET /mgmt/tm/apm/sso/<icontrol_sso_type>
    icontrol_sso_type: str | None


VARIANT_META: dict[Variant, VariantMeta] = {
    Variant.KERBEROS_KCD: VariantMeta(
        label="Kerberos / KCD",
        short="KCD",
        description=(
            "Kerberos Constrained Delegation: the BIG-IP requests a Kerberos service "
            "ticket on the user's behalf and presents it to the backend (SPNEGO)."
        ),
        backend_sso="Kerberos ticket (S4U2Proxy)",
        icontrol_sso_type="kerberos",
    ),
    Variant.HEADER: VariantMeta(
        label="HTTP Header",
        short="Header",
        description=(
            "Header-based SSO: the BIG-IP injects identity HTTP headers "
            "(e.g. upn, mail, groups) into the request to the backend."
        ),
        backend_sso="Injected HTTP headers",
        icontrol_sso_type=None,  # implemented via HTTP header modify rules, not an SSO object
    ),
    Variant.FORMS: VariantMeta(
        label="Forms",
        short="Forms",
        description=(
            "Forms-based SSO: the BIG-IP detects the backend login form and submits "
            "credentials on the user's behalf."
        ),
        backend_sso="Auto-submitted login form",
        icontrol_sso_type="form-based",
    ),
    Variant.SAML: VariantMeta(
        label="SAML",
        short="SAML",
        description=(
            "SAML federation: Entra ID is the IdP and the BIG-IP is the SAML SP. "
            "Optionally the BIG-IP re-asserts SAML to the backend."
        ),
        backend_sso="SAML assertion",
        icontrol_sso_type="saml",
    ),
    Variant.NTLM: VariantMeta(
        label="NTLM",
        short="NTLM",
        description=(
            "NTLM SSO: the BIG-IP performs an NTLM handshake with the backend using "
            "the user's mapped identity."
        ),
        backend_sso="NTLMv1/v2 handshake",
        icontrol_sso_type="ntlmv2",
    ),
    Variant.OAUTH: VariantMeta(
        label="OAuth / OIDC",
        short="OAuth",
        description=(
            "OAuth bearer SSO: the BIG-IP obtains and forwards an OAuth/OIDC bearer "
            "token to the backend API."
        ),
        backend_sso="OAuth bearer token",
        icontrol_sso_type="oauth-bearer",
    ),
}


def meta_for(variant: Variant) -> VariantMeta:
    return VARIANT_META[variant]
