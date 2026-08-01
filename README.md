# spoj/skills

Personal [pi](https://github.com/mariozechner/pi-coding-agent) skills bundle.

## Skills

- **`eml`** — safely inspect RFC 822/MIME email files, read bounded body text, and extract attachments.
- **`gemini-image`** — generate and edit images via Gemini image models.
- **`inspire`** — draw mid-surprisal word dice for lateral thinking when the space is too open or the obvious angles feel exhausted.

## Install

```bash
pi install git:github.com/spoj/skills
```

To load only one:

```bash
pi install git:github.com/spoj/skills
# then in ~/.pi/agent/settings.json, use the object form:
# { "source": "git:github.com/spoj/skills", "skills": ["skills/eml/SKILL.md"] }
```

## Layout

```
skills/
├── eml/
│   ├── SKILL.md
│   └── scripts/eml_tool.py
├── gemini-image/
│   ├── SKILL.md
│   └── scripts/generate.py
└── inspire/
    ├── SKILL.md
    ├── inspire.py
    └── words.txt
```

Pi auto-discovers `SKILL.md` files recursively under the conventional `skills/` directory — no `package.json` manifest required.
