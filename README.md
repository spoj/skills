# spoj/skills

Personal [pi](https://github.com/mariozechner/pi-coding-agent) skills bundle.

## Skills

- **`gemini-image`** — generate and edit images via Gemini image models.
- **`web`** — web retrieval: Grok online search, `curl`/Python verification, Hyperbrowser automation, human-in-the-loop sessions.

## Install

```bash
pi install git:github.com/spoj/skills
```

To load only one:

```bash
pi install git:github.com/spoj/skills
# then in ~/.pi/agent/settings.json, use the object form:
# { "source": "git:github.com/spoj/skills", "skills": ["skills/web/SKILL.md"] }
```

## Layout

```
skills/
├── gemini-image/
│   ├── SKILL.md
│   └── scripts/generate.py
└── web/
    ├── SKILL.md
    └── scripts/{http_probe.py,hb_task.py}
```

Pi auto-discovers `SKILL.md` files recursively under the conventional `skills/` directory — no `package.json` manifest required.
