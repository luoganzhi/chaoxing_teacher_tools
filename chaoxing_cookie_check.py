#!/usr/bin/env python3
"""Check whether a Chaoxing cookie reaches an authenticated page.

The cookie is read from CHAOXING_COOKIE so secrets are not stored in this file
or printed to stdout.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from html import unescape
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener


DEFAULT_URL = "https://i.chaoxing.com/"
LOGIN_HOST_HINTS = (
    "passport2.chaoxing.com",
    "login.chaoxing.com",
    "sso.chaoxing.com",
)
LOGIN_TEXT_HINTS = (
    "用户登录",
    "登录",
    "手机号",
    "密码",
    "login",
)


def title_from_html(html: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.I | re.S)
    if not match:
        return ""
    title = re.sub(r"\s+", " ", match.group(1)).strip()
    return unescape(title)


def looks_logged_out(final_url: str, html: str) -> bool:
    lowered_url = final_url.lower()
    if any(host in lowered_url for host in LOGIN_HOST_HINTS):
        return True

    sample = html[:20000].lower()
    return any(hint.lower() in sample for hint in LOGIN_TEXT_HINTS)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check whether CHAOXING_COOKIE can access i.chaoxing.com."
    )
    parser.add_argument("--url", default=DEFAULT_URL, help=f"default: {DEFAULT_URL}")
    parser.add_argument("--timeout", type=float, default=20.0, help="request timeout")
    args = parser.parse_args()

    cookie = os.environ.get("CHAOXING_COOKIE", "").strip()
    if not cookie:
        print("Missing CHAOXING_COOKIE. Export it in your shell, then rerun.", file=sys.stderr)
        return 2

    request = Request(
        args.url,
        headers={
            "Cookie": cookie,
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
    )

    opener = build_opener()
    try:
        with opener.open(request, timeout=args.timeout) as response:
            final_url = response.geturl()
            status = response.status
            content_type = response.headers.get("content-type", "")
            raw = response.read(2_000_000)
    except HTTPError as exc:
        print(f"HTTP error: {exc.code} {exc.reason}", file=sys.stderr)
        return 1
    except URLError as exc:
        print(f"Network error: {exc.reason}", file=sys.stderr)
        return 1

    charset_match = re.search(r"charset=([^;\s]+)", content_type, flags=re.I)
    charset = charset_match.group(1) if charset_match else "utf-8"
    html = raw.decode(charset, errors="replace")
    title = title_from_html(html)
    logged_out = looks_logged_out(final_url, html)

    print(f"status: {status}")
    print(f"final_url: {final_url}")
    print(f"title: {title or '(no title found)'}")
    print(f"auth_result: {'probably_logged_out' if logged_out else 'probably_logged_in'}")
    return 3 if logged_out else 0


if __name__ == "__main__":
    raise SystemExit(main())
