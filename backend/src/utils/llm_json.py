def strip_markdown_json_fence(content: str) -> str:
    """
    Remove a Markdown code fence around an LLM's JSON
    response, regardless of what (if anything) follows
    the opening ``` on that line.

    Models don't reliably tag the fence as ```json — a
    bare ``` or a stray ```python/```text tag is common.
    Naively stripping only the literal "```json" prefix
    (or only 3 backtick characters) leaves that tag as
    garbage text before the JSON, which breaks json.loads
    at position 0. Discarding the whole opening fence line
    handles every tag the same way.
    """

    content = content.strip()

    if not content.startswith("```"):
        return content

    first_newline = content.find("\n")

    content = (
        content[first_newline + 1:]
        if first_newline != -1
        else content[3:]
    )

    content = content.strip()

    if content.endswith("```"):
        content = content[: -len("```")]

    return content.strip()
