"""Console entry point: run the F5AuthTester web dashboard with uvicorn."""

from __future__ import annotations

import os


def main() -> None:
    import uvicorn

    host = os.environ.get("F5AUTHTESTER_HOST", "127.0.0.1")
    port = int(os.environ.get("F5AUTHTESTER_PORT", "8080"))
    uvicorn.run(
        "f5authtester.web:create_app",
        factory=True,
        host=host,
        port=port,
        log_level=os.environ.get("F5AUTHTESTER_LOG_LEVEL", "info"),
    )


if __name__ == "__main__":
    main()
