import base64
import re
from dataclasses import dataclass

import httpx

from src.config.settings import settings


@dataclass
class DesignReference:
    """
    A design reference resolved to an image the Coding Agent
    can look at, or an error explaining why it couldn't be.

    `image_base64` is None whenever resolution failed - callers
    must check `error` and degrade gracefully (proceed without
    the image) rather than fail the whole ticket over a design
    reference that couldn't be fetched.
    """

    source_type: str
    url: str
    label: str
    image_base64: str | None
    image_media_type: str | None
    error: str | None
    # Exact values read from the design source (currently Figma
    # only), as text. A screenshot can't convey precise hex
    # colors, so these are what the Coding Agent must match.
    style_tokens: str | None = None


def _to_hex(color: dict, opacity: float = 1.0) -> str:
    def channel(name: str) -> int:
        return round(float(color.get(name, 0)) * 255)

    hex_value = (
        f"#{channel('r'):02X}{channel('g'):02X}{channel('b'):02X}"
    )

    alpha = float(color.get("a", 1.0)) * opacity

    if alpha < 0.995:
        hex_value += f"{round(alpha * 255):02X}"

    return hex_value


def _solid_colors(paints: list | None) -> list[str]:
    colors = []

    for paint in paints or []:
        if (
            paint.get("type") == "SOLID"
            and paint.get("visible", True)
            and paint.get("color")
        ):
            colors.append(
                _to_hex(
                    paint["color"],
                    float(paint.get("opacity", 1.0)),
                )
            )

    return colors


def _outline_figma_nodes(
    root: dict,
    max_depth: int = 7,
    max_lines: int = 90,
) -> list[str]:
    """
    Indented layer outline with each visible node's own fill,
    stroke, text color/font and radius, so the agent can tell
    WHICH element uses which color (e.g. the active nav item vs
    the matrix dots), not just which colors exist.

    Repeated siblings (table rows) are collapsed after the first
    few so the outline stays within max_lines.
    """

    out: list[str] = []

    def describe(node: dict) -> str:
        parts = []

        fills = _solid_colors(node.get("fills"))

        if fills:
            label = "text" if node.get("type") == "TEXT" else "fill"
            parts.append(f"{label} {'/'.join(fills)}")

        strokes = _solid_colors(node.get("strokes"))

        if strokes:
            parts.append(f"stroke {'/'.join(strokes)}")

        for paint in node.get("fills") or []:
            if str(paint.get("type", "")).startswith("GRADIENT"):
                stops = "->".join(
                    _to_hex(s["color"])
                    for s in paint.get("gradientStops", [])
                    if s.get("color")
                )
                parts.append(f"gradient {stops}")

        if node.get("cornerRadius"):
            parts.append(f"radius {node['cornerRadius']}px")

        style = node.get("style") or {}

        if style.get("fontSize"):
            parts.append(
                f"{style.get('fontFamily')} "
                f"{style['fontSize']}px/{style.get('fontWeight')}"
            )

        if node.get("type") == "TEXT":
            parts.append(f"\"{(node.get('characters') or '')[:40]}\"")

        return ", ".join(parts)

    def walk(node: dict, depth: int) -> None:
        if (
            len(out) >= max_lines
            or node.get("visible", True) is False
        ):
            return

        details = describe(node)

        if details or depth == 0:
            out.append(
                f"{'  ' * depth}{node.get('name')} "
                f"[{node.get('type')}]"
                + (f": {details}" if details else "")
            )

        if depth >= max_depth:
            return

        seen: dict[str, int] = {}

        for child in node.get("children") or []:
            signature = f"{child.get('type')}"
            seen[signature] = seen.get(signature, 0) + 1

            # Collapse long runs of look-alike siblings
            # (table rows, icons).
            if (
                len(node.get("children") or []) > 6
                and seen[signature] > 3
            ):
                continue

            walk(child, depth + 1)

    walk(root, 0)

    return out


def _collect_figma_styles(root: dict) -> str | None:
    """
    Walk a Figma node tree and summarise the exact colors, fonts
    and radii it uses, most frequent first.
    """

    from collections import Counter

    backgrounds: Counter = Counter()
    text_colors: Counter = Counter()
    strokes: Counter = Counter()
    fonts: Counter = Counter()
    radii: Counter = Counter()
    gradients: Counter = Counter()

    def walk(node: dict) -> None:
        if node.get("visible", True) is False:
            return

        is_text = node.get("type") == "TEXT"

        for hex_value in _solid_colors(node.get("fills")):
            (text_colors if is_text else backgrounds)[
                hex_value
            ] += 1

        for paint in node.get("fills") or []:
            if str(paint.get("type", "")).startswith("GRADIENT"):
                stops = ", ".join(
                    f"{_to_hex(s['color'])} "
                    f"@{round(s.get('position', 0) * 100)}%"
                    for s in paint.get("gradientStops", [])
                    if s.get("color")
                )
                gradients[
                    f"{paint['type']}: {stops}"
                ] += 1

        for hex_value in _solid_colors(node.get("strokes")):
            strokes[hex_value] += 1

        style = node.get("style") or {}

        if style.get("fontFamily"):
            fonts[
                f"{style['fontFamily']} "
                f"{style.get('fontSize')}px "
                f"weight {style.get('fontWeight')}"
            ] += 1

        if node.get("cornerRadius"):
            radii[f"{node['cornerRadius']}px"] += 1

        for child in node.get("children") or []:
            walk(child)

    walk(root)

    def lines(title: str, counter: Counter) -> list[str]:
        if not counter:
            return []

        return [
            f"{title}: "
            + ", ".join(
                f"{value} (x{count})"
                for value, count in counter.most_common(12)
            )
        ]

    outline = _outline_figma_nodes(root)

    summary = (
        (
            [
                "Element styles (layer name: exact values):",
                *outline,
            ]
            if outline
            else []
        )
        + lines("Background/fill colors", backgrounds)
        + lines("Text colors", text_colors)
        + lines("Stroke/border colors", strokes)
        + lines("Gradients", gradients)
        + lines("Fonts", fonts)
        + lines("Corner radii", radii)
    )

    return "\n".join(summary) or None


_FIGMA_FILE_KEY_RE = re.compile(
    r"figma\.com/(?:file|design|proto)/"
    r"(?P<file_key>[a-zA-Z0-9]+)"
)

_FIGMA_NODE_ID_RE = re.compile(
    r"[?&]node-id=([^&]+)"
)


def _extract_figma_node_id(
    url: str,
) -> str | None:

    match = _FIGMA_NODE_ID_RE.search(url)

    if not match:
        return None

    raw = match.group(1)

    # Figma URLs write the node id as "123-456"; the REST
    # API needs "123:456".
    if "-" in raw and ":" not in raw:
        return raw.replace(
            "-",
            ":",
            1,
        )

    return raw


def _resolve_figma(
    url: str,
) -> DesignReference:

    if not settings.figma_api_token:
        return DesignReference(
            source_type="figma",
            url=url,
            label="Figma design",
            image_base64=None,
            image_media_type=None,
            error=(
                "FIGMA_API_TOKEN is not configured, so the "
                "referenced Figma design could not be fetched. "
                "The ticket is being processed without it."
            ),
        )

    file_match = _FIGMA_FILE_KEY_RE.search(url)

    if not file_match:
        return DesignReference(
            source_type="figma",
            url=url,
            label="Figma design",
            image_base64=None,
            image_media_type=None,
            error=(
                "Could not find a Figma file key in this URL."
            ),
        )

    file_key = file_match.group("file_key")
    node_id = _extract_figma_node_id(url)

    if not node_id:
        return DesignReference(
            source_type="figma",
            url=url,
            label="Figma design",
            image_base64=None,
            image_media_type=None,
            error=(
                "This Figma URL doesn't include a node-id "
                "(a specific frame). In Figma, select the "
                "frame and use 'Copy link to selection' to "
                "get a URL that points at one frame."
            ),
        )

    headers = {
        "X-Figma-Token": settings.figma_api_token,
    }

    try:
        with httpx.Client(timeout=30) as client:

            images_response = client.get(
                f"https://api.figma.com/v1/images/"
                f"{file_key}",
                params={
                    "ids": node_id,
                    "format": "png",
                    "scale": "2",
                },
                headers=headers,
            )

            images_response.raise_for_status()

            images_data = images_response.json()

            image_url = (
                images_data
                .get("images", {})
                .get(node_id)
            )

            if not image_url:
                return DesignReference(
                    source_type="figma",
                    url=url,
                    label="Figma design",
                    image_base64=None,
                    image_media_type=None,
                    error=(
                        "Figma did not return a rendered "
                        f"image for node {node_id}. "
                        f"{images_data.get('err') or ''}"
                    ).strip(),
                )

            image_response = client.get(
                image_url
            )

            image_response.raise_for_status()

            image_bytes = image_response.content

            # Best effort: exact colors/fonts from the node tree.
            # A failure here must not lose the image.
            style_tokens = None

            try:
                nodes_response = client.get(
                    f"https://api.figma.com/v1/files/"
                    f"{file_key}/nodes",
                    params={"ids": node_id},
                    headers=headers,
                )

                nodes_response.raise_for_status()

                node = (
                    nodes_response.json()
                    .get("nodes", {})
                    .get(node_id, {})
                    .get("document")
                )

                if node:
                    style_tokens = _collect_figma_styles(node)

            except (httpx.HTTPError, ValueError, KeyError):
                style_tokens = None

    except httpx.HTTPError as error:
        return DesignReference(
            source_type="figma",
            url=url,
            label="Figma design",
            image_base64=None,
            image_media_type=None,
            error=(
                f"Figma API request failed: {error}"
            ),
        )

    return DesignReference(
        source_type="figma",
        url=url,
        label=f"Figma frame {node_id}",
        image_base64=base64.b64encode(
            image_bytes
        ).decode(),
        image_media_type="image/png",
        error=None,
        style_tokens=style_tokens,
    )


def _resolve_webpage(
    url: str,
) -> DesignReference:

    try:
        from playwright.sync_api import (
            sync_playwright,
        )

    except ImportError:
        return DesignReference(
            source_type="webpage",
            url=url,
            label="Web page design",
            image_base64=None,
            image_media_type=None,
            error=(
                "Playwright is not installed, so this "
                "web page could not be screenshotted."
            ),
        )

    try:
        with sync_playwright() as playwright:

            browser = (
                playwright.chromium.launch()
            )

            page = browser.new_page(
                viewport={
                    "width": 1440,
                    "height": 900,
                }
            )

            page.goto(
                url,
                wait_until="networkidle",
                timeout=20000,
            )

            # Viewport only, not full_page: a full-page
            # capture of a long page gets so tall that
            # vision models downscale it into mush. The
            # initial viewport is what "matches the design"
            # usually means anyway.
            image_bytes = page.screenshot()

            browser.close()

    except Exception as error:
        return DesignReference(
            source_type="webpage",
            url=url,
            label="Web page design",
            image_base64=None,
            image_media_type=None,
            error=(
                f"Could not screenshot this page: {error}"
            ),
        )

    return DesignReference(
        source_type="webpage",
        url=url,
        label=f"Web page: {url}",
        image_base64=base64.b64encode(
            image_bytes
        ).decode(),
        image_media_type="image/png",
        error=None,
    )


_DATA_URL_RE = re.compile(
    r"^data:(?P<media_type>image/[a-zA-Z0-9.+-]+);"
    r"base64,(?P<data>.+)$",
    re.DOTALL,
)


def _resolve_pasted_image(
    image_data: str,
) -> DesignReference:
    """
    Resolve a directly-pasted design image: either a data URL
    (data:image/png;base64,...., as a browser paste/upload
    would produce) or a bare base64 string.
    """

    image_data = image_data.strip()

    data_url_match = _DATA_URL_RE.match(
        image_data
    )

    if data_url_match:
        media_type = data_url_match.group(
            "media_type"
        )
        raw_base64 = data_url_match.group(
            "data"
        )

    else:
        media_type = "image/png"
        raw_base64 = image_data

    try:
        base64.b64decode(
            raw_base64,
            validate=True,
        )

    except (
        ValueError,
        base64.binascii.Error,
    ):
        return DesignReference(
            source_type="pasted_image",
            url="",
            label="Pasted design image",
            image_base64=None,
            image_media_type=None,
            error=(
                "The pasted design image is not "
                "valid base64 image data."
            ),
        )

    return DesignReference(
        source_type="pasted_image",
        url="",
        label="Pasted design image",
        image_base64=raw_base64,
        image_media_type=media_type,
        error=None,
    )


def resolve_design_reference(
    url: str | None,
    image_data: str | None = None,
) -> DesignReference | None:
    """
    Resolve a ticket's design reference into an image the
    Coding Agent can look at, checking in this priority order:

    1. A Figma URL in `url` - fetched via the Figma API.
    2. A directly pasted/uploaded image in `image_data`.
    3. Any other URL in `url` - screenshotted as a web page.

    Returns None when neither was given at all (the common
    case). Returns a DesignReference with `error` set (and no
    image) when one was given but couldn't be resolved -
    callers proceed without the image rather than failing the
    ticket over it.
    """

    url = url.strip() if url else ""
    image_data = (
        image_data.strip()
        if image_data
        else ""
    )

    if "figma.com" in url:
        return _resolve_figma(url)

    if image_data:
        return _resolve_pasted_image(
            image_data
        )

    if url:
        return _resolve_webpage(url)

    return None
