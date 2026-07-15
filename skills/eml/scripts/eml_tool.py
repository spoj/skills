#!/usr/bin/env python3
"""Safely inspect and extract RFC 822/MIME (.eml) files."""

from __future__ import annotations

import argparse
import hashlib
import html
from html.parser import HTMLParser
import json
from email import policy
from email.header import decode_header, make_header
from email.message import EmailMessage, Message
from email.parser import BytesParser
from pathlib import Path
import re
import sys
from typing import Any


class TextExtractor(HTMLParser):
    BREAK_TAGS = {"br", "p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}
    SKIP_TAGS = {"script", "style", "head", "title", "svg"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in self.SKIP_TAGS:
            self.skip_depth += 1
        if tag in self.BREAK_TAGS and not self.skip_depth:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.SKIP_TAGS and self.skip_depth:
            self.skip_depth -= 1
        if tag in self.BREAK_TAGS and not self.skip_depth:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.parts.append(data)

    def text(self) -> str:
        value = html.unescape("".join(self.parts)).replace("\r", "")
        value = re.sub(r"[ \t]+", " ", value)
        value = re.sub(r" *\n *", "\n", value)
        return re.sub(r"\n{3,}", "\n\n", value).strip()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def decoded_header(message: Message, name: str) -> str | None:
    value = message.get(name)
    if value is None:
        return None
    try:
        return str(make_header(decode_header(str(value))))
    except (LookupError, UnicodeError):
        return str(value)


def load_message(path: Path) -> tuple[bytes, EmailMessage]:
    data = path.read_bytes()
    message = BytesParser(policy=policy.default).parsebytes(data)
    return data, message  # type: ignore[return-value]


def part_bytes(part: Message) -> bytes:
    payload = part.get_payload(decode=True)
    if isinstance(payload, bytes):
        return payload
    return b""


def decoded_filename(part: Message) -> str | None:
    name = part.get_filename()
    if not name:
        return None
    try:
        return str(make_header(decode_header(name)))
    except (LookupError, UnicodeError):
        return str(name)


def body_text(message: EmailMessage) -> tuple[str, str | None]:
    candidates: dict[str, list[str]] = {"text/plain": [], "text/html": []}
    for part in message.walk():
        if part.is_multipart() or part.get_content_disposition() == "attachment":
            continue
        content_type = part.get_content_type()
        if content_type not in candidates:
            continue
        try:
            value = part.get_content()
        except (LookupError, UnicodeError):
            raw = part_bytes(part)
            value = raw.decode(part.get_content_charset() or "utf-8", errors="replace")
        if isinstance(value, str):
            candidates[content_type].append(value)

    if candidates["text/plain"]:
        text = "\n\n".join(candidates["text/plain"]).replace("\r\n", "\n").strip()
        return text, "text/plain"
    if candidates["text/html"]:
        parser = TextExtractor()
        parser.feed("\n".join(candidates["text/html"]))
        return parser.text(), "text/html"
    return "", None


def mime_parts(message: EmailMessage) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, part in enumerate(message.walk()):
        if part.is_multipart():
            size = None
        else:
            size = len(part_bytes(part))
        rows.append(
            {
                "index": index,
                "content_type": part.get_content_type(),
                "disposition": part.get_content_disposition(),
                "filename": decoded_filename(part),
                "content_id": part.get("Content-ID"),
                "size": size,
            }
        )
    return rows


def attachment_rows(message: EmailMessage, include_inline: bool = True) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, part in enumerate(message.walk()):
        if part.is_multipart():
            continue
        disposition = part.get_content_disposition()
        filename = decoded_filename(part)
        is_inline = disposition == "inline" or (filename is not None and disposition != "attachment")
        is_attachment = disposition == "attachment" or filename is not None
        if not is_attachment or (is_inline and not include_inline):
            continue
        data = part_bytes(part)
        rows.append(
            {
                "part_index": index,
                "filename": filename,
                "content_type": part.get_content_type(),
                "disposition": disposition,
                "content_id": part.get("Content-ID"),
                "size": len(data),
                "sha256": sha256_bytes(data),
                "inline": is_inline,
            }
        )
    return rows


def metadata(path: Path, data: bytes, message: EmailMessage, preview: int) -> dict[str, Any]:
    text, body_type = body_text(message)
    result: dict[str, Any] = {
        "path": str(path.resolve()),
        "size": len(data),
        "sha256": sha256_bytes(data),
        "headers": {
            "subject": decoded_header(message, "Subject"),
            "from": decoded_header(message, "From"),
            "to": decoded_header(message, "To"),
            "cc": decoded_header(message, "Cc"),
            "date": decoded_header(message, "Date"),
            "message_id": decoded_header(message, "Message-ID"),
            "in_reply_to": decoded_header(message, "In-Reply-To"),
        },
        "body_type": body_type,
        "mime_parts": mime_parts(message),
        "attachments": attachment_rows(message),
    }
    if preview:
        result["body_preview"] = text[:preview]
        result["body_truncated"] = len(text) > preview
    return result


def safe_name(name: str | None, index: int) -> str:
    value = Path(name or f"attachment-{index}").name
    value = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "_", value).strip(" .")
    return value[:180] or f"attachment-{index}"


def unique_path(directory: Path, name: str) -> Path:
    candidate = directory / name
    stem, suffix = candidate.stem, candidate.suffix
    counter = 1
    while candidate.exists():
        candidate = directory / f"{stem}-{counter}{suffix}"
        counter += 1
    return candidate


def command_inspect(args: argparse.Namespace) -> int:
    path = Path(args.file)
    data, message = load_message(path)
    result = metadata(path, data, message, args.body_preview)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    headers = result["headers"]
    print(f"Path: {result['path']}")
    print(f"Size: {result['size']} bytes")
    print(f"SHA-256: {result['sha256']}")
    for key in ("subject", "from", "to", "cc", "date", "message_id"):
        if headers.get(key):
            print(f"{key.replace('_', ' ').title()}: {headers[key]}")
    print(f"Body type: {result['body_type'] or 'none'}")
    print(f"MIME parts: {len(result['mime_parts'])}")
    print(f"Attachments/inline resources: {len(result['attachments'])}")
    for row in result["attachments"]:
        print(
            f"  [{row['part_index']}] {row['filename'] or '(unnamed)'} | "
            f"{row['content_type']} | {row['size']} bytes | sha256:{row['sha256']}"
        )
    if args.body_preview:
        print("\nBody preview:\n")
        print(result.get("body_preview", ""))
        if result.get("body_truncated"):
            print("\n[preview truncated]")
    return 0


def command_body(args: argparse.Namespace) -> int:
    _, message = load_message(Path(args.file))
    text, _ = body_text(message)
    print(text[: args.max_chars])
    if len(text) > args.max_chars:
        print("\n[body truncated]", file=sys.stderr)
    return 0


def command_attachments(args: argparse.Namespace) -> int:
    _, message = load_message(Path(args.file))
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    extracted: list[dict[str, Any]] = []
    for index, part in enumerate(message.walk()):
        if part.is_multipart():
            continue
        disposition = part.get_content_disposition()
        filename = decoded_filename(part)
        is_inline = disposition == "inline" or (filename is not None and disposition != "attachment")
        is_attachment = disposition == "attachment" or filename is not None
        if not is_attachment or (is_inline and not args.include_inline):
            continue
        data = part_bytes(part)
        destination = unique_path(output, safe_name(filename, index))
        destination.write_bytes(data)
        extracted.append(
            {
                "part_index": index,
                "path": str(destination.resolve()),
                "content_type": part.get_content_type(),
                "size": len(data),
                "sha256": sha256_bytes(data),
                "inline": is_inline,
            }
        )
    print(json.dumps(extracted, ensure_ascii=False, indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)

    inspect = commands.add_parser("inspect", help="Inspect headers, MIME parts, and attachments")
    inspect.add_argument("file")
    inspect.add_argument("--json", action="store_true")
    inspect.add_argument("--body-preview", type=int, default=0, metavar="CHARS")
    inspect.set_defaults(func=command_inspect)

    body = commands.add_parser("body", help="Print safe local text extraction of the body")
    body.add_argument("file")
    body.add_argument("--max-chars", type=int, default=20000)
    body.set_defaults(func=command_body)

    attachments = commands.add_parser("attachments", help="Extract attachment files")
    attachments.add_argument("file")
    attachments.add_argument("--output", required=True)
    attachments.add_argument("--include-inline", action="store_true")
    attachments.set_defaults(func=command_attachments)
    return root


def main() -> int:
    args = parser().parse_args()
    if getattr(args, "body_preview", 0) < 0 or getattr(args, "max_chars", 1) < 1:
        raise SystemExit("character limits must be positive")
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
