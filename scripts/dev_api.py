"""p4n4-api for development: auto-reload on lib/ and api/ changes, and the
dashboard container's token header handled the way its nginx does.

The dashboard sends its bearer token in `X-Upstream-Authorization` when the
API is on its own origin (so basic auth can use `Authorization`), and nginx
moves it back. `flutter run`'s dev proxy (dashboard/web_dev_config.yaml)
doesn't, so without this every API call from a hot-reload dashboard is a 401.

Run by `scripts/dev api` / `scripts/dev up`; it takes the same P4N4_API_* and
P4N4_PROJECT_DIR variables as `p4n4-api serve`.
"""

from __future__ import annotations

from pathlib import Path

from p4n4_api.main import app as _api

_UPSTREAM = b"x-upstream-authorization"


async def app(scope, receive, send):
    if scope["type"] == "http":
        headers = scope["headers"]
        token = next((v for k, v in headers if k == _UPSTREAM), None)
        if token is not None:
            kept = [(k, v) for k, v in headers if k not in (_UPSTREAM, b"authorization")]
            scope = {**scope, "headers": [*kept, (b"authorization", token)]}
    await _api(scope, receive, send)


if __name__ == "__main__":
    import uvicorn

    from p4n4_api import logs
    from p4n4_api.config import load_settings

    here = Path(__file__).resolve().parent
    root = here.parent
    settings = load_settings()
    # Same options as `p4n4-api serve` (p4n4_api/cli.py), plus reload.
    uvicorn.run(
        "dev_api:app",
        app_dir=str(here),
        host=settings.host,
        port=settings.port,
        reload=True,
        reload_dirs=[str(root / "api" / "p4n4_api"), str(root / "lib" / "p4n4_lib"), str(here)],
        proxy_headers=False,
        access_log=False,
        log_config=logs.log_config(settings.log_format, settings.log_level),
    )
