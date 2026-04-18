"""
Gemini image generation CLI.

Uses the Gemini REST API directly with responseModalities: ["TEXT", "IMAGE"].

Requirements: httpx (pip install httpx)
"""

import argparse
import base64
import json
import os
import sys
import subprocess

def get_api_key():
    """Get Gemini API key from env or llm keys store."""
    key = os.environ.get("LLM_GEMINI_KEY") or os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    # Try llm keys store
    try:
        result = subprocess.run(
            ["llm", "keys", "get", "gemini"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    print("Error: No Gemini API key found.", file=sys.stderr)
    print("Set LLM_GEMINI_KEY or GEMINI_API_KEY, or run: llm keys set gemini", file=sys.stderr)
    sys.exit(1)


def build_proxy_client(timeout=120):
    """Build httpx client respecting HTTP_PROXY/HTTPS_PROXY env vars."""
    import httpx

    proxy_url = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY") or \
                os.environ.get("https_proxy") or os.environ.get("http_proxy")
    if proxy_url:
        print(f"Using proxy: {proxy_url}", file=sys.stderr)
        return httpx.Client(proxy=proxy_url, timeout=timeout)
    return httpx.Client(timeout=timeout)


def generate_image(prompt, model="gemini-3-pro-image-preview", output_path="output.png",
                   input_image=None, api_key=None, timeout=120):
    """Generate an image using Gemini's image generation API."""
    import httpx

    key = api_key or get_api_key()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    # Build the content parts
    parts = []
    if input_image:
        # Read and encode the input image
        with open(input_image, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        # Detect mime type from extension
        ext = os.path.splitext(input_image)[1].lower()
        mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                    ".webp": "image/webp", ".gif": "image/gif"}
        mime_type = mime_map.get(ext, "image/png")
        parts.append({"inline_data": {"mime_type": mime_type, "data": image_data}})

    parts.append({"text": prompt})

    body = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
        },
    }

    client = build_proxy_client(timeout=timeout)
    try:
        response = client.post(
            url,
            headers={"x-goog-api-key": key},
            json=body,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        print(f"API error {e.response.status_code}: {e.response.text}", file=sys.stderr)
        sys.exit(1)
    finally:
        client.close()

    data = response.json()

    # Check for API-level errors
    if "error" in data:
        print(f"API error: {data['error']['message']}", file=sys.stderr)
        sys.exit(1)

    # Extract image and text from response
    candidates = data.get("candidates", [])
    if not candidates:
        print("Error: No candidates in response.", file=sys.stderr)
        print(json.dumps(data, indent=2), file=sys.stderr)
        sys.exit(1)

    text_parts = []
    image_count = 0
    for part in candidates[0].get("content", {}).get("parts", []):
        # API returns camelCase keys (inlineData, mimeType)
        inline = part.get("inlineData") or part.get("inline_data")
        if inline:
            image_bytes = base64.b64decode(inline["data"])
            mime = inline.get("mimeType") or inline.get("mime_type", "image/png")
            # Determine extension from mime
            ext_map = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
            ext = ext_map.get(mime, ".png")

            if image_count == 0:
                save_path = output_path
            else:
                base, orig_ext = os.path.splitext(output_path)
                save_path = f"{base}_{image_count}{orig_ext or ext}"

            # If output_path has no extension, add one based on mime
            if not os.path.splitext(save_path)[1]:
                save_path += ext

            with open(save_path, "wb") as f:
                f.write(image_bytes)
            print(f"Saved: {save_path} ({len(image_bytes)} bytes, {mime})", file=sys.stderr)
            image_count += 1
        elif "text" in part:
            text_parts.append(part["text"])

    if text_parts:
        print("\n".join(text_parts))

    if image_count == 0:
        print("Warning: No image was returned by the model.", file=sys.stderr)
        print("Response text:", file=sys.stderr)
        for t in text_parts:
            print(t, file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Generate images using Gemini image models.",
        epilog="Examples:\n"
               "  %(prog)s \"a cat astronaut floating in space\"\n"
               "  %(prog)s \"make the background blue\" -i photo.jpg -o edited.png\n"
               "  %(prog)s \"pixel art castle\" -m gemini-3.1-flash-image-preview\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("prompt", help="Image generation prompt")
    parser.add_argument("-o", "--output", default="output.png",
                        help="Output file path (default: output.png)")
    parser.add_argument("-i", "--input", default=None,
                        help="Input image for editing/transformation")
    parser.add_argument("-m", "--model", default="gemini-3-pro-image-preview",
                        choices=[
                            "gemini-3-pro-image-preview",
                            "gemini-3.1-flash-image-preview",
                            "gemini-2.5-flash-image",
                        ],
                        help="Model to use (default: gemini-3-pro-image-preview)")
    parser.add_argument("--timeout", type=int, default=120,
                        help="Request timeout in seconds (default: 120)")
    args = parser.parse_args()

    generate_image(
        prompt=args.prompt,
        model=args.model,
        output_path=args.output,
        input_image=args.input,
        timeout=args.timeout,
    )


if __name__ == "__main__":
    main()
