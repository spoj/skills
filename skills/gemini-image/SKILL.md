---
name: gemini-image
description: Generate and edit images using Gemini image models (gemini-3-pro-image-preview, gemini-3.1-flash-image-preview). Use when the user wants to create, generate, edit, or transform images via AI. Triggers on requests like "generate an image", "create a picture", "edit this photo", "make a logo", or any image creation/manipulation task.
compatibility: Requires `uv` and a Gemini API key (via `llm keys set gemini`, LLM_GEMINI_KEY, or GEMINI_API_KEY).
---

# Gemini Image Generation

Generate and edit images using Gemini's native image output models.

## Generate an image

```bash
uv run --with httpx scripts/generate.py "a cat astronaut floating in space" -o cat.png
```

## Edit an existing image

```bash
uv run --with httpx scripts/generate.py "make the background blue" -i input.jpg -o edited.png
```

## Models

| Model | Flag | Notes |
|---|---|---|
| `gemini-3-pro-image-preview` | (default) | Best quality |
| `gemini-3.1-flash-image-preview` | `-m gemini-3.1-flash-image-preview` | Faster |
| `gemini-2.5-flash-image` | `-m gemini-2.5-flash-image` | Older, still available |

## Options

| Flag | Description | Default |
|---|---|---|
| `-o`, `--output` | Output file path | `output.png` |
| `-i`, `--input` | Input image for editing | None |
| `-m`, `--model` | Model to use | `gemini-3-pro-image-preview` |
| `--timeout` | Request timeout in seconds | `120` |

## API key

The script finds the Gemini API key in this order:
1. `LLM_GEMINI_KEY` env var
2. `GEMINI_API_KEY` env var
3. `llm keys get gemini` (llm keystore)
