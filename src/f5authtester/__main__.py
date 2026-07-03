"""Console entry point.

Two subcommands:

* ``serve`` (default) — run the web dashboard with uvicorn.
* ``check``            — run every configured target once, print the report, and exit.
                         Exit code is non-zero if any target is FAIL (2) or nothing is OK (3),
                         which makes it usable as a config/environment smoke test in CI or cron.
"""

from __future__ import annotations

import argparse
import json
import os


def _serve(args: argparse.Namespace) -> int:
    import uvicorn

    host = args.host or os.environ.get("F5AUTHTESTER_HOST", "127.0.0.1")
    port = args.port or int(os.environ.get("F5AUTHTESTER_PORT", "8080"))
    reload = args.reload or os.environ.get("F5AUTHTESTER_RELOAD") == "1"
    uvicorn.run(
        "f5authtester.web:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
        log_level=os.environ.get("F5AUTHTESTER_LOG_LEVEL", "info"),
    )
    return 0


def _check(args: argparse.Namespace) -> int:
    from .config import load_config
    from .models import Status
    from .runner import run_report_sync

    loaded = load_config(args.config)
    report = run_report_sync(loaded.config)

    if args.json:
        print(json.dumps(report.model_dump_web(), indent=2))
    else:
        _print_table(loaded.source, report)

    statuses = [r.status for r in report.results]
    if Status.FAIL in statuses:
        return 2
    if not any(s == Status.OK for s in statuses):
        return 3
    return 0


_SYMBOL = {
    "ok": "OK  ",
    "warn": "WARN",
    "fail": "FAIL",
    "unknown": "UNKN",
    "skipped": "SKIP",
}


def _print_table(source: str, report) -> None:  # noqa: ANN001 - internal formatter
    print(f"F5AuthTester check — config: {source}")
    print(f"Generated: {report.generated_at}\n")
    width = max((len(r.name) for r in report.results), default=4)
    for r in report.results:
        print(f"[{_SYMBOL.get(r.status.value, '?')}] {r.name:<{width}}  ({r.variant.value})")
        for c in r.checks:
            lat = f"{c.latency_ms}ms" if c.latency_ms is not None else "-"
            sym = _SYMBOL.get(c.status.value, "?")
            print(f"        {c.source.value:<13} {sym}  {c.message} [{lat}]")
    summary = report.summary
    print(
        "\nSummary: "
        + "  ".join(f"{k}={summary[k]}" for k in ("ok", "warn", "fail", "unknown", "skipped"))
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="f5authtester", description="F5 APM SHA SSO health")
    parser.add_argument(
        "-c",
        "--config",
        help="path to config YAML (default: $F5AUTHTESTER_CONFIG or ./config.yaml)",
    )
    sub = parser.add_subparsers(dest="command")

    p_serve = sub.add_parser("serve", help="run the web dashboard (default)")
    p_serve.add_argument("--host", help="bind address")
    p_serve.add_argument("--port", type=int, help="bind port")
    p_serve.add_argument("--reload", action="store_true", help="auto-reload on code changes")

    p_check = sub.add_parser("check", help="run all checks once, print report, exit")
    p_check.add_argument("--json", action="store_true", help="emit JSON instead of a table")

    args = parser.parse_args()
    # A -c/--config given on the CLI wins; export it so the web factory picks it up too.
    if getattr(args, "config", None):
        os.environ["F5AUTHTESTER_CONFIG"] = args.config

    if args.command == "check":
        raise SystemExit(_check(args))
    # default and "serve"
    if not hasattr(args, "host"):
        args.host = args.port = None
        args.reload = False
    raise SystemExit(_serve(args))


if __name__ == "__main__":
    main()
