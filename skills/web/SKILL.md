---
name: web
description: General web information retrieval using `llm -o online true` with Grok-4.3, `curl`, and Python verification. Use for current facts, URL discovery, deterministic HTTP retrieval, and source verification.
compatibility: Requires `curl`, `llm`, Python 3, and optionally `uv` for Python helper scripts.
---

# Web Information Retrieval

Use this skill when a task needs current web data, reliable URL discovery, deterministic HTTP retrieval, or source verification.

## Tool roles

### 1) `llm -n -m openrouter/x-ai/grok-4.3 -o online true` for live search & synthesis

Use Grok-4.3 online search when you need current facts, URL discovery, broader reasoning across live sources, or a filtered list of official URLs.

```bash
llm -n -m openrouter/x-ai/grok-4.3 -o online true \
  "Current date: 2026-05-21. Find the official documentation and status-related pages for ExampleCloud API authentication and rate limits. Return only direct official URLs as: Title | Site | URL. Exclude forums, mirrors, aggregators, and stale pages."
```

Operational rules:
- Always use `-n` to disable SQLite logging.
- Treat each invocation as stateless.
- Include the current date, geography, filters, exclusions, and desired output format directly in the prompt.
- Use Bash timeouts up to `600000ms` for slower searches.
- Returns leads that still need URL verification; does not read raw HTML.

---

### 2) `curl` or Python for deterministic retrieval and verification

After discovery, verify URLs with direct HTTP retrieval. Use `curl` for quick status / redirect / content-type checks; use Python (+ BeautifulSoup) for parsing and metadata extraction.

```bash
curl -sI "https://example.com"
curl -sL "https://example.com"

uv run --with requests --with beautifulsoup4 \
  python scripts/http_probe.py <url1> <url2>
```

These tools do not interpret JavaScript. If a site only renders useful content in-browser or blocks direct HTTP retrieval, report that limitation and ask the user for an accessible export, screenshot, copied text, or authenticated page content.

---

## Recommended retrieval order

Choose the smallest sufficient tool. Default sequence: Grok-4.3 online → `curl`/Python verification. Skip discovery when the exact URL is known and start at `curl`/Python.
