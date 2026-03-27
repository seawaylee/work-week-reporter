#!/usr/bin/env python3

import argparse
from http.cookies import SimpleCookie
import os
from pathlib import Path
import shlex
import sys
import tempfile
from urllib.parse import urlparse

import requests


class GrafanaCookieRefreshError(RuntimeError):
    pass


def log(message):
    print(f"[grafana-cookie-refresh] {message}", file=sys.stderr)


def shell_quote(value):
    return "'" + value.replace("'", "'\"'\"'") + "'"


def load_env_defaults(env_file, names):
    missing = [name for name in names if not os.getenv(name)]
    if not missing:
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, raw_value = line.split("=", 1)
        key = key.strip()
        if key not in missing or os.getenv(key):
            continue

        parsed = shlex.split(raw_value, posix=True, comments=False)
        os.environ[key] = " ".join(parsed)


def require_env(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise GrafanaCookieRefreshError(f"Missing required env var: {name}")
    return value


def grafana_root_url(url_base):
    parsed = urlparse(url_base)
    if not parsed.scheme or not parsed.netloc:
        raise GrafanaCookieRefreshError("GRAFANA_URL_BASE must be an absolute URL")
    return f"{parsed.scheme}://{parsed.netloc}"


def iter_cookie_items(cookie_source):
    if not cookie_source:
        return []

    if hasattr(cookie_source, "items"):
        return list(cookie_source.items())

    items = []
    for cookie in cookie_source:
        name = getattr(cookie, "name", None)
        value = getattr(cookie, "value", None)
        if name and value is not None:
            items.append((name, value))
    return items


def extract_set_cookie_items(response):
    headers = []
    raw_headers = getattr(getattr(response, "raw", None), "headers", None)
    if hasattr(raw_headers, "get_all"):
        headers.extend(raw_headers.get_all("Set-Cookie") or [])

    set_cookie = getattr(response, "headers", {}).get("Set-Cookie", "")
    if set_cookie:
        headers.append(set_cookie)

    items = []
    for header in headers:
        jar = SimpleCookie()
        jar.load(header)
        items.extend((name, morsel.value) for name, morsel in jar.items())
    return items


def build_cookie_header(*cookie_sources):
    seen = set()
    cookie_items = []
    for source in cookie_sources:
        for name, value in source:
            key = str(name).strip()
            if not key:
                continue
            lowered = key.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            cookie_items.append((key, str(value)))

    if not cookie_items:
        raise GrafanaCookieRefreshError("Grafana login succeeded but no auth cookies were returned")

    return "; ".join(f"{name}={value}" for name, value in cookie_items)


def extract_grafana_cookie(response, cookie_jar=None):
    direct_items = iter_cookie_items(cookie_jar)
    response_items = iter_cookie_items(getattr(response, "cookies", None))
    header_items = extract_set_cookie_items(response)
    if direct_items or response_items or header_items:
        return build_cookie_header(direct_items, response_items, header_items)

    raise GrafanaCookieRefreshError("Grafana login succeeded but no auth cookies were returned")


def grafana_query_url(url_base):
    configured = os.getenv("GRAFANA_URL", "").strip()
    if configured:
        return configured
    return f"{url_base.rstrip('/')}/query_range"


def describe_response_error(response):
    try:
        payload = response.json()
    except ValueError:
        payload = {}

    if isinstance(payload, dict):
        for key in ("message", "error", "status"):
            value = payload.get(key)
            if value:
                return str(value)

    text = getattr(response, "text", "").strip()
    return text[:200] if text else ""


def verify_grafana_api(session, grafana_url, grafana_org_id, timeout):
    try:
        response = session.post(
            grafana_url,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "week-reporter-grafana-cookie-refresh/1.0",
                "x-grafana-org-id": str(grafana_org_id).strip() or "1",
            },
            data="query=1&start=0&end=1&step=1",
            allow_redirects=False,
            timeout=timeout,
            verify=False,
        )
    except requests.RequestException as exc:
        raise GrafanaCookieRefreshError(f"Grafana API self-check failed: {exc}") from exc

    if response.status_code >= 400:
        detail = describe_response_error(response)
        suffix = f": {detail}" if detail else ""
        raise GrafanaCookieRefreshError(
            f"Grafana API self-check failed with HTTP {response.status_code}{suffix}"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise GrafanaCookieRefreshError("Grafana API self-check returned invalid JSON") from exc

    if isinstance(payload, dict) and payload.get("status") not in (None, "success"):
        detail = payload.get("error") or payload.get("message") or payload.get("status")
        raise GrafanaCookieRefreshError(f"Grafana API self-check failed: {detail}")


def login_and_get_cookie(root_url, username, password, timeout, grafana_url=None, grafana_org_id="1"):
    login_url = f"{root_url.rstrip('/')}/login"
    try:
        session = requests.Session()
        response = session.post(
            login_url,
            json={"user": username, "password": password},
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "week-reporter-grafana-cookie-refresh/1.0",
            },
            allow_redirects=False,
            timeout=timeout,
            verify=False,
        )
    except requests.RequestException as exc:
        raise GrafanaCookieRefreshError(f"Grafana login request failed: {exc}") from exc

    if response.status_code >= 400:
        detail = describe_response_error(response)
        suffix = f": {detail}" if detail else ""
        raise GrafanaCookieRefreshError(
            f"Grafana login failed with HTTP {response.status_code}{suffix}"
        )

    cookie_header = extract_grafana_cookie(response, cookie_jar=getattr(session, "cookies", None))
    verify_grafana_api(
        session=session,
        grafana_url=grafana_url or grafana_query_url(root_url),
        grafana_org_id=grafana_org_id,
        timeout=timeout,
    )
    return cookie_header


def write_grafana_cookie(env_file, cookie_value):
    env_path = Path(env_file)
    if not env_path.exists():
        raise GrafanaCookieRefreshError(f"Env file not found: {env_path}")

    replacement = f"GRAFANA_COOKIE={shell_quote(cookie_value)}"
    original = env_path.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)

    updated_lines = []
    replaced = False
    for line in lines:
        if line.startswith("GRAFANA_COOKIE="):
            updated_lines.append(replacement + ("\n" if line.endswith("\n") else ""))
            replaced = True
        else:
            updated_lines.append(line)

    if not replaced:
        if updated_lines and not updated_lines[-1].endswith("\n"):
            updated_lines[-1] = updated_lines[-1] + "\n"
        updated_lines.append(replacement + "\n")

    stat_result = env_path.stat()
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=env_path.parent,
            delete=False,
        ) as handle:
            handle.write("".join(updated_lines))
            temp_path = Path(handle.name)
        os.chmod(temp_path, stat_result.st_mode)
        os.replace(temp_path, env_path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Refresh GRAFANA_COOKIE in .env.local")
    parser.add_argument(
        "--env-file",
        default=".env.local",
        help="Path to the shell env file to update (default: .env.local)",
    )
    parser.add_argument(
        "--timeout",
        default=15,
        type=int,
        help="Grafana login request timeout in seconds (default: 15)",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    env_file = Path(args.env_file).expanduser()
    if not env_file.exists():
        raise GrafanaCookieRefreshError(f"Env file not found: {env_file}")

    load_env_defaults(
        env_file,
        ["GRAFANA_USERNAME", "GRAFANA_PASSWORD", "GRAFANA_URL_BASE", "GRAFANA_URL", "GRAFANA_ORG_ID"],
    )

    url_base = require_env("GRAFANA_URL_BASE")
    root_url = grafana_root_url(url_base)
    log(f"Logging into Grafana root domain: {root_url}")
    cookie_value = login_and_get_cookie(
        root_url=root_url,
        username=require_env("GRAFANA_USERNAME"),
        password=require_env("GRAFANA_PASSWORD"),
        timeout=args.timeout,
        grafana_url=grafana_query_url(url_base),
        grafana_org_id=os.getenv("GRAFANA_ORG_ID", "1"),
    )
    write_grafana_cookie(env_file, cookie_value)
    log(f"Updated GRAFANA_COOKIE in {env_file}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GrafanaCookieRefreshError as exc:
        log(f"ERROR: {exc}")
        raise SystemExit(1)
