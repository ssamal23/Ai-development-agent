from langchain_core.messages import HumanMessage
from langfuse import observe

from src.agents.coding_agent import _loads_lenient
from src.llm.factory import get_llm
from src.services.observability import get_langchain_callbacks

MAX_ISSUES = 8


@observe(as_type="agent", name="design-review-agent")
def review_design(
    design_reference: dict,
    screenshot_base64: str,
) -> dict:
    """
    Compare a screenshot of the generated app with the design
    reference and list concrete visual differences.

    Returns {"status": "PASS"|"FAIL", "summary": str,
    "issues": [{"element", "expected", "actual"}]}.
    """

    style_tokens = design_reference.get("style_tokens") or (
        "(no exact style values available - judge from the image)"
    )

    prompt = f"""
You are a design QA reviewer. Two images follow:

1. DESIGN: the reference design the page must match.
2. IMPLEMENTATION: a screenshot of what was built.

EXACT STYLE VALUES FROM THE DESIGN:

{style_tokens}

First decide whether IMPLEMENTATION shows the same screen as
DESIGN (it may instead show a login page, an error, a blank
page or another screen, because the app could not be navigated
to the designed screen). If it is a different screen, return
status "SKIPPED" with a one-sentence summary and no issues -
do NOT report differences between unrelated screens.

Otherwise compare them and list the visual differences that matter:
wrong colors (use the exact hex values above), wrong fonts or
font sizes/weights, wrong border radius, missing or extra
elements (icons, checkboxes, badges, buttons, columns), wrong
layout or alignment, wrong text content.

Ignore: tiny sub-pixel or spacing differences, different
rendering of the same font, and anything not visible in the
design.

Return ONLY a JSON object, no Markdown:

{{
  "status": "PASS", "FAIL" or "SKIPPED",
  "summary": "one sentence",
  "issues": [
    {{
      "element": "which element, e.g. 'permission dots'",
      "expected": "what the design has, with exact hex/size",
      "actual": "what the implementation has"
    }}
  ]
}}

Return PASS only when there are no color mismatches and no
missing or clearly wrong elements. List at most {MAX_ISSUES}
issues, most visible first.
"""

    message = HumanMessage(
        content=[
            {"type": "text", "text": prompt},
            {"type": "text", "text": "DESIGN:"},
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": (
                        design_reference.get("image_media_type")
                        or "image/png"
                    ),
                    "data": design_reference["image_base64"],
                },
            },
            {"type": "text", "text": "IMPLEMENTATION:"},
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": screenshot_base64,
                },
            },
        ]
    )

    response = get_llm().invoke(
        [message],
        config={"callbacks": get_langchain_callbacks()},
    )

    content = response.content

    if not isinstance(content, str):
        raise ValueError("Design Review Agent returned invalid response.")

    result = _loads_lenient(content)

    if not isinstance(result, dict) or result.get("status") not in (
        "PASS",
        "FAIL",
        "SKIPPED",
    ):
        raise ValueError(
            f"Design Review Agent returned unparseable output: {content[:300]}"
        )

    result["issues"] = (result.get("issues") or [])[:MAX_ISSUES]

    if result["status"] == "FAIL" and not result["issues"]:
        result["status"] = "PASS"

    return result
