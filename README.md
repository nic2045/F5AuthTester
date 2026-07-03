# F5AuthTester

> A small web dashboard that tells you, at a glance, whether your **F5 BIG-IP APM Secure Hybrid Access (SHA)** SSO variants are working — end-to-end and on the box.

[![CI - Python](https://github.com/nic2045/f5authtester/actions/workflows/ci-python.yml/badge.svg)](https://github.com/nic2045/f5authtester/actions/workflows/ci-python.yml)
[![CI - PowerShell](https://github.com/nic2045/f5authtester/actions/workflows/ci-powershell.yml/badge.svg)](https://github.com/nic2045/f5authtester/actions/workflows/ci-powershell.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](pyproject.toml)

## The scenario

You put **Microsoft Entra ID** (with MFA) in front of on-prem applications by publishing them
through **F5 BIG-IP APM** — the *Secure Hybrid Access* pattern. Entra ID authenticates the user
at the front door; the BIG-IP then performs **single sign-on to the backend** using whichever
mechanism that app understands:

| Variant | Backend SSO | iControl SSO object |
| --- | --- | --- |
| **Kerberos / KCD** | Kerberos ticket (S4U2Proxy) | `apm sso kerberos` |
| **HTTP Header** | Injected identity headers | *(header rules, no SSO object)* |
| **Forms** | Auto-submitted login form | `apm sso form-based` |
| **SAML** | SAML assertion | `apm sso saml` |
| **NTLM** | NTLMv1/v2 handshake | `apm sso ntlmv2` |
| **OAuth / OIDC** | OAuth bearer token | `apm sso oauth-bearer` |

F5AuthTester monitors these and shows a colour-coded health tile per published app.

## How it checks

Each target is evaluated by **two independent checks**, then aggregated (worst wins):

1. **Active HTTP probe** (data plane) — makes a real request at the published URL.
   - *Reachability mode* (default): an unauthenticated request should be redirected to Entra ID.
     Seeing that redirect proves the APM access policy + Entra federation front door is alive.
   - *End-to-end mode*: supply a bearer token / cookie and a `success_marker` to confirm the
     backend SSO variant actually let the request through. Known F5/APM error pages flip a tile to red.
2. **F5 iControl REST** (management plane) — logs in to the BIG-IP with token auth and confirms
   the access profile and the variant's SSO object exist and are reachable (and reads active
   session counts where available). Management-plane hiccups report as *Unknown*, never a false *Fail*.

Results are cached and refreshed by a background scheduler; the dashboard auto-refreshes every 15s.

## Quick start

```bash
make install          # pip install -e ".[dev]"
make demo             # run the dashboard with the built-in demo config → http://127.0.0.1:8080
```

Point it at your environment by copying the example config, then run it:

```bash
cp config.example.yaml config.yaml     # edit it; secrets stay in env vars
export F5_PASSWORD='…'

make check            # run every target once, print a report, exit non-zero on failure
make dev              # run the dashboard with auto-reload (picks up config.yaml)
```

### Make targets

| Target | What it does |
| --- | --- |
| `make install` | Install the app + dev tools (editable) |
| `make dev` | Run the dashboard with **auto-reload** (uses `config.yaml` if present) |
| `make serve` / `make run` | Run the dashboard without reload |
| `make demo` | Run with the built-in demo config (ignores `config.yaml`) |
| `make check` | **Env/config smoke test** — run all checks once, print a report, exit non-zero on failure |
| `make test` | Run the pytest suite |
| `make lint` / `make fmt` | Ruff lint-check / auto-format + fix |
| `make clean` | Remove caches and build artifacts |

Override variables inline, e.g. `make dev PORT=9000 CONFIG=./staging.yaml`.

### Testing your environment with `make check`

`make check` (or `python -m f5authtester check`) runs every configured target once and prints a
per-target table without starting the web server — ideal for validating config or wiring into
CI/cron. Add `--json` for machine-readable output. Exit codes: **0** = at least one OK and no
failures, **2** = at least one target FAILed, **3** = nothing came back OK.

```text
$ make check
[OK  ] Intranet (KCD)       (kerberos_kcd)
        active_probe  OK    SHA front door alive — redirected to Entra ID [142.0ms]
        icontrol      OK    APM objects present on BIG-IP [88.1ms]
Summary: ok=1  warn=0  fail=0  unknown=0  skipped=0
```

You can still run things without `make`:

```bash
pip install -e ".[dev]"
python -m f5authtester            # serve (default)
python -m f5authtester check      # one-shot env test
export F5AUTHTESTER_CONFIG=./config.yaml   # or pass -c ./config.yaml
```

### Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `F5AUTHTESTER_CONFIG` | `./config.yaml` (else demo) | Path to the YAML config |
| `F5AUTHTESTER_HOST` | `127.0.0.1` | Bind address |
| `F5AUTHTESTER_PORT` | `8080` | Bind port |
| `F5AUTHTESTER_LOG_LEVEL` | `info` | uvicorn log level |
| `F5AUTHTESTER_RELOAD` | `0` | Set to `1` to enable auto-reload (same as `serve --reload`) |
| any `${VAR}` in the config | — | Expanded at load time (use for passwords/tokens) |

## Configuration

See [`config.example.yaml`](config.example.yaml) for a fully commented example covering all six
variants, per-target probe expectations, and the global BIG-IP iControl connection. Minimal shape:

```yaml
poll_interval_s: 300
f5:
  enabled: true
  host: bigip.corp.example.com
  username: svc-f5authtester
  password: ${F5_PASSWORD}
targets:
  - name: Intranet (KCD)
    variant: kerberos_kcd
    url: https://intranet.corp.example.com/
    apm:
      access_profile: ap_intranet
      sso_config: kcd_intranet
```

Set `f5.enabled: false` to run active probes only (no BIG-IP credentials needed).

## HTTP API

| Endpoint | Method | Returns |
| --- | --- | --- |
| `/` | GET | HTML dashboard |
| `/api/status` | GET | Latest cached report (JSON) |
| `/api/run` | POST | Trigger a fresh run, return the report |
| `/healthz` | GET | Liveness probe |

## PowerShell helper

For admins who live in PowerShell, the `F5AuthTester` module wraps the API:

```powershell
Import-Module ./powershell/F5AuthTester.psd1
Get-F5AuthStatus -BaseUrl http://localhost:8080     # latest report as objects
Invoke-F5AuthRun  -BaseUrl http://localhost:8080     # force a fresh run
```

## Development

```bash
pip install -e ".[dev]"
ruff check .
ruff format --check .
pytest

# PowerShell
Invoke-ScriptAnalyzer -Path ./powershell -Recurse
Invoke-Pester -Path ./tests
```

## Project layout

```
src/f5authtester/
├── models.py            # status/variant enums, CheckResult/TargetResult/Report + aggregation
├── config.py            # YAML config + ${ENV} expansion, demo fallback
├── variants.py          # the six SSO variants and their iControl mappings
├── checks/
│   ├── active.py        # active synthetic HTTP probe
│   └── icontrol.py      # F5 iControl REST client + APM object inspection
├── runner.py            # runs both checks per target, concurrently, and aggregates
├── web/
│   ├── app.py           # FastAPI app, JSON API, background scheduler
│   └── templates/       # dashboard.html
└── __main__.py          # `python -m f5authtester`
powershell/F5AuthTester.{psm1,psd1}   # PowerShell API wrapper
tests/                                # pytest + Pester
```
