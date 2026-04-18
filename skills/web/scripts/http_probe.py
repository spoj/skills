#!/usr/bin/env python3
import sys
import re
import requests
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0"}


def extract_meta(soup, key, value):
    tag = soup.find("meta", attrs={key: value})
    return tag.get("content", "").strip() if tag and tag.get("content") else ""


def probe(url: str):
    try:
        r = requests.get(url, headers=UA, timeout=20)
    except Exception as e:
        print(f"URL: {url}\nERROR: {e}\n")
        return

    soup = BeautifulSoup(r.text, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    desc = extract_meta(soup, "name", "description") or extract_meta(soup, "property", "og:description")
    og_title = extract_meta(soup, "property", "og:title")
    text = " ".join(soup.get_text(" ").split())[:2000]
    expired = any(x in text.lower() for x in [
        "this job has expired",
        "no longer available",
        "role is no longer available",
        "job not found",
        "404 error",
    ])

    print(f"URL: {url}")
    print(f"STATUS: {r.status_code}")
    print(f"CONTENT-TYPE: {r.headers.get('content-type', '')}")
    print(f"TITLE: {title}")
    if og_title:
        print(f"OG_TITLE: {og_title}")
    if desc:
        print(f"DESCRIPTION: {desc[:300]}")
    print(f"EXPIRED_SIGNAL: {expired}")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: http_probe.py <url1> <url2> ...")
        raise SystemExit(2)
    for url in sys.argv[1:]:
        probe(url)
