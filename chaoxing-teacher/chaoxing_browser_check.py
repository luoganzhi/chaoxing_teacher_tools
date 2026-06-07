#!/usr/bin/env python3
"""Open i.chaoxing.com with cookies in agent-browser.

Reads CHAOXING_COOKIE from the environment, injects each cookie into an isolated
agent-browser session, and prints a small login-status summary without dumping
page content or cookie values.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from http.cookies import SimpleCookie


DEFAULT_URL = "https://i.chaoxing.com/"
DEFAULT_DOMAIN = ".chaoxing.com"
DEFAULT_SESSION = "chaoxing-cookie-check"
LOGIN_HOST_HINTS = (
    "passport2.chaoxing.com",
    "login.chaoxing.com",
    "sso.chaoxing.com",
)
LOGIN_TEXT_HINTS = (
    "用户登录",
    "手机号",
    "密码",
    "login",
)


def run_agent_browser(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["agent-browser", *args],
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def parse_cookie_header(header: str) -> list[tuple[str, str]]:
    parsed = SimpleCookie()
    parsed.load(header)
    if parsed:
        return [(key, morsel.value) for key, morsel in parsed.items()]

    cookies: list[tuple[str, str]] = []
    for part in header.split(";"):
        if "=" not in part:
            continue
        name, value = part.split("=", 1)
        name = name.strip()
        if name:
            cookies.append((name, value.strip()))
    return cookies


def looks_logged_out(url: str, title: str, body_text: str) -> bool:
    lower_url = url.lower()
    if any(host in lower_url for host in LOGIN_HOST_HINTS):
        return True

    sample = f"{title}\n{body_text[:8000]}".lower()
    return any(hint.lower() in sample for hint in LOGIN_TEXT_HINTS)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Use agent-browser to check a Chaoxing cookie login state."
    )
    parser.add_argument("--url", default=DEFAULT_URL, help=f"default: {DEFAULT_URL}")
    parser.add_argument("--domain", default=DEFAULT_DOMAIN, help=f"default: {DEFAULT_DOMAIN}")
    parser.add_argument(
        "--session",
        default=os.environ.get("CHAOXING_AGENT_SESSION", DEFAULT_SESSION),
        help=f"default: {DEFAULT_SESSION}",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="show the browser window while checking",
    )
    args = parser.parse_args()

    cookie_header = os.environ.get("CHAOXING_COOKIE", "").strip()
    if not cookie_header:
        print("Missing CHAOXING_COOKIE. Export it in your shell, then rerun.", file=sys.stderr)
        return 2

    cookies = parse_cookie_header(cookie_header)
    if not cookies:
        print("CHAOXING_COOKIE did not contain parseable name=value cookies.", file=sys.stderr)
        return 2

    base = ["--session", args.session]
    if args.headed:
        base.append("--headed")

    run_agent_browser([*base, "open", "about:blank"])
    run_agent_browser([*base, "cookies", "clear"])

    failed: list[str] = []
    for name, value in cookies:
        result = run_agent_browser(
            [
                *base,
                "cookies",
                "set",
                name,
                value,
                "--domain",
                args.domain,
                "--path",
                "/",
                "--secure",
            ],
            check=False,
        )
        if result.returncode != 0:
            failed.append(name)

    if failed:
        print(f"warning: failed to inject {len(failed)} cookie(s): {', '.join(failed)}")

    run_agent_browser([*base, "open", args.url])
    run_agent_browser([*base, "wait", "--load", "networkidle"], check=False)

    url = run_agent_browser([*base, "get", "url"]).stdout.strip()
    title = run_agent_browser([*base, "get", "title"]).stdout.strip()
    body_result = run_agent_browser([*base, "get", "text", "body"], check=False)
    body_text = body_result.stdout if body_result.returncode == 0 else ""
    logged_out = looks_logged_out(url, title, body_text)

    print(f"session: {args.session}")
    print(f"cookies_injected: {len(cookies) - len(failed)}/{len(cookies)}")
    print(f"final_url: {url}")
    print(f"title: {title or '(no title found)'}")
    print(f"auth_result: {'probably_logged_out' if logged_out else 'probably_logged_in'}")

    if re.search(r"(^|\\.)chaoxing\\.com/?", url, flags=re.I) is None:
        print("warning: final URL is outside chaoxing.com")

    return 3 if logged_out else 0


if __name__ == "__main__":
    raise SystemExit(main())
