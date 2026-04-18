---
name: web
description: General web information retrieval using `llm -o online true` with Grok-4.20, `curl`, Python verification, and Hyperbrowser browser automation. Use for current facts, URL discovery, JS-heavy pages, and human-in-the-loop browser sessions.
compatibility: Requires `curl`, `llm`, Python 3, and optionally `uv`, `hyperbrowser`, and `HYPERBROWSER_API_KEY` for browser tasks.
---

# Web Information Retrieval

Use this skill when a task needs current web data, reliable URL discovery, deterministic HTTP retrieval, browser-visible verification, or a reusable browser session that can be shared with a human user.

## Tool roles

### 1) `llm -n -m openrouter/x-ai/grok-4.20 -o online true` for live search & synthesis

Use Grok-4.20 online search when you need current facts, URL discovery, broader reasoning across live sources, or a filtered list of official URLs.

```bash
llm -n -m openrouter/x-ai/grok-4.20 -o online true \
  "Current date: 2026-04-17. Find the official documentation and status-related pages for ExampleCloud API authentication and rate limits. Return only direct official URLs as: Title | Site | URL. Exclude forums, mirrors, aggregators, and stale pages."
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

Neither interprets JavaScript; some sites only render useful content in-browser.

---

### 3) Hyperbrowser for browser-visible truth

Use Hyperbrowser when the page is JS-heavy, bot-protected, or browser state / authentication matters. Uses HyperAgent `version="1.1.0"` with `gemini-3-flash-preview`.

Set the API key first:

```bash
export HYPERBROWSER_API_KEY="..."
```

Basic task example:

```bash
uv run --with hyperbrowser \
  python scripts/hb_task.py \
  --task "Open https://example.com and report the visible title and whether a primary CTA is visible. Return 2 bullet points."
```

Region override (optional, e.g. `us-east`, `europe-west`, `asia-south`):

```bash
uv run --with hyperbrowser \
  python scripts/hb_task.py \
  --region us-east \
  --task "Open https://example.com and summarize only the browser-visible content."
```

---

## Human-in-the-loop browser sessions

Use this pattern when the agent should do part of the browser work, then the user should interact manually, then the agent should continue in the same authenticated or stateful browser session.

Typical cases: login, MFA, CAPTCHA, SSO, cookie/consent prompts, file uploads, manually narrowing a search UI before extraction.

### Protocol

1. **Create or prime a reusable session** with a real timeout.
2. **Print `SESSION_ID` and `LIVE_URL`.**
3. **Agent performs setup steps** (e.g. opening the site, navigating to login).
4. **Ask the user to open `LIVE_URL` and interact manually.**
5. **Wait in chat** until the user confirms.
6. **Resume automation with the same `SESSION_ID`.**
7. **Extend or stop the session** if needed.

### Create a reusable session

```bash
uv run --with hyperbrowser \
  python scripts/hb_task.py \
  --create-session-only \
  --timeout-minutes 20 \
  --live-view-ttl-seconds 3600
```

### Prime the browser, then leave it open for human

```bash
uv run --with hyperbrowser \
  python scripts/hb_task.py \
  --task "Open https://example.com/login and stop on the login page. Return exactly: ready for human login" \
  --keep-browser-open \
  --timeout-minutes 20 \
  --live-view-ttl-seconds 3600
```

### Resume after the user confirms

```bash
uv run --with hyperbrowser \
  python scripts/hb_task.py \
  --session-id <SESSION_ID> \
  --task "Continue from the current page and extract the visible account summary. Return 5 bullet points." \
  --keep-browser-open \
  --live-view-ttl-seconds 3600
```

### Extend or stop sessions

```bash
# Extend
uv run --with hyperbrowser \
  python scripts/hb_task.py \
  --session-id <SESSION_ID> \
  --extend-session-minutes 15 \
  --print-session-details

# Stop
uv run --with hyperbrowser \
  python scripts/hb_task.py \
  --stop-session <SESSION_ID>
```

### Notes on sessions
- `timeoutMinutes` is a practical keepalive / inactivity window, not a precise wall-clock cutoff. Use `--extend-session-minutes` when the human step may run longer.
- `liveViewTtlSeconds` controls the lifetime of the live-view URL token. A session may still be active even if an older `LIVE_URL` has expired.
- Use `--view-only-live-view` only when the user should observe without controlling.
- **Popup-heavy flows** (enterprise portals, embedded viewers): navigate to the launcher with the agent, let the user click the popup/launch control in `LIVE_URL`, then resume once stable.

---

## Recommended retrieval order

Choose the smallest sufficient tool. Default sequence: Grok-4.20 online → `curl`/Python → Hyperbrowser. Skip ahead when the exact URL is known (start at `curl`/Python) or authentication is required (start at Hyperbrowser session).
