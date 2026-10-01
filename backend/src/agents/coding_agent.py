import json
import re

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableLambda
from langfuse import observe, get_client
from pydantic import ValidationError

from src.llm.factory import get_llm
from src.models.code_change import (
    CodeChangeResponse,
)
from src.services.observability import get_langchain_callbacks


@observe(as_type="agent", name="coding-agent")
def generate_code_changes(
    ticket: dict,
    implementation_plan: dict,
    repository_context: list[dict],
    verification_result: dict | None = None,
    test_result: dict | None = None,
    apply_error: dict | None = None,
    design_feedback: dict | None = None,
    workspace_context: list[dict] | None = None,
    previous_code_changes: dict | None = None,
    design_reference: dict | None = None,
) -> CodeChangeResponse:
    """
    Generate code changes using the current
    repository/workspace state.

    During retries, workspace_context is the
    source of truth for the latest implementation.
    """

    # Override the default @observe input capture: the raw args
    # here include full repo/workspace file contents and a
    # base64 design image, which would bloat every trace and
    # obscure the one thing worth seeing at a glance - what this
    # attempt was actually trying to fix.
    get_client().update_current_span(
        input={
            "ticket_id": ticket.get("id"),
            "ticket_title": ticket.get("title"),
            "coding_attempt_is_retry": bool(
                previous_code_changes
            ),
            "previous_verification_status": (
                (verification_result or {}).get("status")
            ),
            "previous_test_success": (
                (test_result or {}).get("success")
            ),
            "has_apply_error": bool(apply_error),
            "has_design_reference": bool(design_reference),
        }
    )

    llm = get_llm()

    verification_feedback = ""

    if verification_result:
        verification_feedback = f"""
PREVIOUS VERIFICATION RESULT:

{json.dumps(
    verification_result,
    indent=2,
)}

The previous implementation failed story verification.

You MUST fix the specific issues identified by
the Verification Agent.

Pay particular attention to:

- Failed acceptance criteria
- Missing requirements
- Incorrect requirements
- Verification recommendations

Do not ignore the verification feedback.

Do not make unrelated changes.
"""

    test_feedback = ""

    if test_result:
        test_feedback = f"""
PREVIOUS TEST RESULT:

{json.dumps(
    test_result,
    indent=2,
)}

The previous implementation failed automated tests.

You MUST analyze the test failure and fix the
underlying problem.

Pay particular attention to:

- Test failures
- Runtime errors
- Compilation errors
- Type errors
- Assertion failures
- Dependency errors
- Stack traces
- Test output

Do NOT:

- Remove tests
- Disable tests
- Weaken tests
- Ignore errors
- Make unrelated changes

Fix the actual implementation problem.
"""

    design_review_feedback = ""

    if design_feedback:
        design_review_feedback = f"""
PREVIOUS DESIGN REVIEW:

{json.dumps(
    design_feedback,
    indent=2,
)}

The implementation passed verification and tests, but a
screenshot of the running app does not match the design
reference. Fix EXACTLY the listed differences, using the
exact values given (hex colors, font sizes, radii). Keep
everything else unchanged.
"""

    apply_error_feedback = ""

    if apply_error:
        apply_error_feedback = f"""
PREVIOUS APPLY ERROR:

{json.dumps(
    apply_error,
    indent=2,
)}

Your previous "changes" could not be applied to the
workspace because of a create/modify/delete action
mismatch with the file's actual current state.

This almost always means one of:

- You used "create" for a file that already exists
  (it was created by YOUR OWN previous attempt in this
  same retry loop - use "modify" for it instead, and
  base the content on LATEST WORKSPACE CONTEXT if that
  file appears there).
- You used "modify" for a file that does not exist yet
  (use "create" instead).
- You used "delete" for a file that does not exist.

Re-check the action for every file in your previous
"changes" against LATEST WORKSPACE CONTEXT and fix the
mismatched action(s). Do not repeat the same mistake.
"""

    previous_changes_context = ""

    if previous_code_changes:
        previous_changes_context = f"""
PREVIOUS GENERATED CODE CHANGES:

{_format_previous_changes(
    previous_code_changes
)}

These changes represent the previous implementation
attempt.

Do not blindly regenerate them.

Keep working changes where appropriate and fix
only the parts that caused verification or test
failures.

Only your latest response is applied, so it must
contain the COMPLETE set of changes: every file
from the previous attempt (unchanged files
included, with their full content) plus your fixes.
"""

    latest_workspace_context = (
        workspace_context
        or []
    )

    design_reference_context = ""
    design_reference_image = None

    if design_reference:

        if design_reference.get("image_base64"):
            style_tokens_block = ""

            if design_reference.get("style_tokens"):
                style_tokens_block = (
                    "EXACT STYLE VALUES FROM THE DESIGN "
                    "(authoritative - use these hex codes, "
                    "not guesses from the image):\n"
                    f"{design_reference['style_tokens']}\n"
                )

            design_reference_context = f"""
DESIGN REFERENCE:

A design reference image is attached to this
message: {design_reference.get("label")}
({design_reference.get("url")}).

Per RULE 27 below, match this design's layout,
structure, content AND its colors, fonts and
radii.
{style_tokens_block}

Study the image carefully, but do NOT describe,
narrate, or explain what you see in it anywhere
in your response. Do not write any sentence like
"Looking at this design..." or "I can see...".
Go straight from analyzing the image to producing
the requested output through the tool/schema
provided for this call.
"""
            design_reference_image = {
                "media_type": (
                    design_reference.get(
                        "image_media_type"
                    )
                    or "image/png"
                ),
                "data": design_reference[
                    "image_base64"
                ],
            }

        elif design_reference.get("error"):
            design_reference_context = f"""
DESIGN REFERENCE:

A design reference was provided
({design_reference.get("url")}) but could not be
loaded: {design_reference.get("error")}

Proceed using the ticket and implementation plan
alone.
"""

    prompt = f"""
You are a senior software engineer working on
an existing software project.

Your job is to implement the requested story
using the existing repository as the source of truth.

You are NOT designing a new application.

You are modifying an existing application.

IMPORTANT RETRY RULE:

If LATEST WORKSPACE CONTEXT is provided, it is
the most recent state of the implementation.

You MUST treat it as the source of truth for
files that were already modified during this
ticket.

Do not assume those files still contain the
original repository-index content.

IMPORTANT RULES:

1. Follow the ticket requirements exactly.

2. Follow the implementation plan.

3. Use the existing repository code as the
   primary source of truth.

4. During retries, use the LATEST WORKSPACE CONTEXT
   as the source of truth for modified files.

5. Reuse existing components, services,
   utilities, patterns, and styles whenever
   appropriate.

6. Do not rewrite unrelated files.

7. Make the minimum required changes.

8. Preserve the existing architecture.

9. Preserve the existing coding style.

10. Do not introduce unnecessary dependencies.

11. Do not create duplicate functionality
    that already exists.

12. Do not change existing behavior unless
    required by the ticket.

13. For existing files that need modification,
    start from the file's EXACT current content
    (from LATEST WORKSPACE CONTEXT if present,
    otherwise ORIGINAL REPOSITORY CONTEXT) and
    apply only the change required by the ticket.

    Return the COMPLETE resulting file content,
    but every line that is not directly related to
    the requested change MUST be copied verbatim,
    unchanged, in its original order.

    Do NOT drop, reorder, "clean up", or rewrite
    existing rules, styles, imports, or markup that
    the ticket did not ask you to change.

14. For new files, return the COMPLETE file content.

15. For deleted files, content must be null.

16. Use relative repository paths.

17. Do not use absolute filesystem paths.

18. Do not modify files that are not required
    by the ticket or implementation plan.

19. If previous verification failed,
    specifically fix the reported issues.

20. If previous tests failed,
    specifically fix the reported errors.

21. Do not blindly regenerate the previous code.

22. Preserve correct changes from previous attempts.

23. Do not remove working functionality.

24. Do not change the implementation plan unless
    required to fix an identified problem.

25. Produce your output only through the
    structured tool/schema provided for this
    call. Do not also write it out as JSON text,
    Markdown, or any other format in your reply.

26. Do not narrate, describe, or explain what you
    see in the ticket, the implementation plan, or
    any provided image anywhere in your reply -
    for example, never write a sentence like
    "Looking at this..." or "I can see...". Go
    directly to producing the requested output.

27. If a DESIGN REFERENCE is provided, the result
    MUST visually match it: layout, structure,
    content, colors, fonts, border radii and
    spacing.

    Use the EXACT STYLE VALUES listed in the
    DESIGN REFERENCE section for every color
    (backgrounds, text, borders, gradients). Do
    not approximate colors from the image when
    exact hex values are given.

    Prefer the repository's existing mechanism for
    expressing them: if an existing CSS variable
    or class already resolves to the same color,
    reuse it. If the design's color differs from
    every existing token, set the design's exact
    value (update the variable's value, or add a
    new variable) instead of substituting the
    "closest" existing color.

    Keep the project's structure and conventions
    (file layout, component patterns, variable
    naming); only the visual values follow the
    design.

TICKET:

{json.dumps(
    ticket,
    indent=2,
)}

IMPLEMENTATION PLAN:

{json.dumps(
    implementation_plan,
    indent=2,
)}

ORIGINAL REPOSITORY CONTEXT:

{json.dumps(
    repository_context,
    indent=2,
)}

LATEST WORKSPACE CONTEXT:

{json.dumps(
    latest_workspace_context,
    indent=2,
)}

{previous_changes_context}

{verification_feedback}

{test_feedback}

{apply_error_feedback}

{design_review_feedback}

{design_reference_context}

CODE GENERATION REQUIREMENTS:

Before generating code:

1. Understand the ticket.

2. Understand the acceptance criteria.

3. Understand the implementation plan.

4. Understand the original repository code.

5. If retrying, understand the latest workspace code.

6. Determine exactly which files need changes.

7. Reuse existing code where possible.

8. Make the smallest possible implementation.

9. Fix the actual verification/test failure.

After generating the code, mentally verify:

1. Does every acceptance criterion have
   an implementation?

2. Are all imports valid?

3. Are referenced components/services/functions
   actually available?

4. Are file paths correct?

5. Are existing coding conventions preserved?

6. For every "modify" change, is every line that
   was not part of the requested change identical
   to the original file content?

7. Are unnecessary files avoided?

8. Could the implementation break existing
   functionality?

9. If previous verification failed, have all
   reported issues been fixed?

10. If previous tests failed, has the root cause
    been addressed?

11. If a design reference was provided, do the
    layout/structure AND every color, font and
    radius match it (using the exact listed hex
    values), expressed through the repository's
    existing variables/classes where they already
    resolve to the same value?

For each file that needs to change, produce one
change entry with an action ("create", "modify",
or "delete"), the relative file path, a short
reason, and its content.

Every "create" or "modify" entry's content MUST
be that file's COMPLETE resulting content. Every
"delete" entry's content MUST be null. Omit
"delete" entries entirely if nothing needs to be
deleted.

Produce the list of change entries directly
through the tool/schema provided for this call -
do not write it out as JSON text in your reply.
"""

    # Structured output: Claude's own tool-calling constructs
    # the JSON, so it can't drift into conversational prose,
    # wrap it in an inconsistent Markdown fence, or emit an
    # unescaped quote/control-character that breaks hand-rolled
    # json.loads() parsing. This replaced a manual invoke() +
    # fence-stripping + json.loads() pipeline that kept failing
    # on a new edge case each time a model quirk surfaced.
    #
    # include_raw=True returns {"raw", "parsed", "parsing_error"}
    # instead of raising inside the parser, so a malformed tool
    # call can be inspected and repaired (see
    # _parse_structured_output) rather than crashing the run
    # after minutes of LLM work.
    #
    # Built by hand instead of with_structured_output() so the
    # double-encoded `changes` string is decoded *before* pydantic
    # validation. Otherwise PydanticToolsParser raises a list_type
    # ValidationError that Langfuse records as a failed span even
    # though the output was recovered afterwards.
    structured_llm = (
        llm.bind_tools(
            [CodeChangeResponse],
            tool_choice=CodeChangeResponse.__name__,
        )
        | RunnableLambda(_decode_string_changes)
        | RunnableLambda(_to_structured_output)
    )

    if design_reference_image:
        message = HumanMessage(
            content=[
                *_build_prompt_blocks(prompt),
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": (
                            design_reference_image[
                                "media_type"
                            ]
                        ),
                        "data": (
                            design_reference_image[
                                "data"
                            ]
                        ),
                    },
                },
            ]
        )
        output = structured_llm.invoke(
            [message],
            config={
                "callbacks": get_langchain_callbacks(),
            },
        )

    else:
        output = structured_llm.invoke(
            [
                HumanMessage(
                    content=_build_prompt_blocks(prompt)
                )
            ],
            config={
                "callbacks": get_langchain_callbacks(),
            },
        )

    result = _parse_structured_output(
        output
    )

    if not isinstance(
        result,
        CodeChangeResponse,
    ):
        raise ValueError(
            "Coding Agent returned an invalid response."
        )

    _validate_code_changes(
        result
    )

    return result


# Everything before this marker (instructions, ticket, plan and the
# original repository context) is identical across the Coding Agent's
# retries within a run; everything after it (latest workspace, feedback)
# changes. The stable part is marked for Anthropic prompt caching, so
# retries re-read it at ~10% of the normal input price.
_CACHE_SPLIT_MARKER = "\nLATEST WORKSPACE CONTEXT:\n"


def _build_prompt_blocks(prompt: str) -> list[dict]:
    split_at = prompt.find(_CACHE_SPLIT_MARKER)

    if split_at == -1:
        return [{"type": "text", "text": prompt}]

    return [
        {
            "type": "text",
            "text": prompt[:split_at],
            "cache_control": {"type": "ephemeral"},
        },
        {"type": "text", "text": prompt[split_at:]},
    ]


def _format_previous_changes(
    previous_code_changes: dict,
) -> str:
    """
    Render the previous attempt as plain file blocks.

    It used to be embedded as a raw {"changes": [...]} JSON
    document - the same shape as the tool schema the model must
    answer with. On retries Claude then echoed that document back
    as a JSON *string* inside the `changes` field instead of
    filling it with a list (seen in production traces, and
    reproduced on the exact failing prompt). Plain blocks remove
    that look-alike, and skip JSON-escaping all the source code.
    """

    blocks = []

    for change in previous_code_changes.get("changes", []):
        content = change.get("content")

        blocks.append(
            f"===== FILE: {change.get('file')} =====\n"
            f"ACTION: {change.get('action')}\n"
            f"REASON: {change.get('reason')}\n"
            f"----- CONTENT -----\n"
            f"{content if content is not None else '(file deleted)'}\n"
            f"===== END FILE ====="
        )

    return "\n\n".join(blocks)


def _parse_structured_output(
    output: dict,
) -> CodeChangeResponse:
    parsed = output.get("parsed")

    if isinstance(parsed, CodeChangeResponse):
        return parsed

    raise ValueError(
        "Coding Agent returned an invalid response: "
        f"{output.get('parsing_error')}"
    )


def _loads_lenient(text: str):
    """
    json.loads() with fallbacks for the ways the model mangles a
    JSON string that holds source code: a Markdown fence around it,
    invalid backslash escapes (regexes, Windows paths, JSX), or
    trailing text after the document. Returns None if unrecoverable.
    """

    candidate = text.strip()

    if candidate.startswith("```"):
        candidate = candidate.split("\n", 1)[-1]
        candidate = candidate.rsplit("```", 1)[0].strip()

    attempts = [
        candidate,
        re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", candidate),
    ]

    last_error = None

    for attempt in attempts:
        try:
            return json.loads(attempt, strict=False)

        except json.JSONDecodeError as error:
            last_error = error

        try:
            value, _ = json.JSONDecoder(strict=False).raw_decode(
                attempt.lstrip()
            )
            return value

        except json.JSONDecodeError as error:
            last_error = error

    print(
        "Coding Agent `changes` string is not recoverable JSON: "
        f"{last_error}"
    )

    return None


def _decode_string_changes(message):
    """
    Claude sometimes fills the tool's `changes` argument with the
    whole document as a JSON string - a bare list or
    {"changes": [...]} - which fails list validation even though
    every change in it is fine. Decode it in place so a complete
    (and ~$0.35) generation isn't discarded.

    Anything that isn't that shape is left untouched and fails
    validation loudly downstream.
    """

    for call in getattr(message, "tool_calls", None) or []:
        args = call.get("args") or {}
        changes = args.get("changes")

        if not isinstance(changes, str):
            continue

        decoded = _loads_lenient(changes)

        if isinstance(decoded, dict):
            decoded = decoded.get("changes")

        if not isinstance(decoded, list):
            continue

        args["changes"] = decoded

        print(
            "Coding Agent passed `changes` as a JSON string "
            "instead of a list; decoded it."
        )

    return message


def _to_structured_output(message) -> dict:
    """
    Mirror with_structured_output(include_raw=True): never raise,
    so a malformed tool call surfaces as a clear ValueError from
    _parse_structured_output instead of inside the chain.
    """

    calls = getattr(message, "tool_calls", None) or []

    if not calls:
        return {
            "raw": message,
            "parsed": None,
            "parsing_error": "model made no tool call",
        }

    try:
        return {
            "raw": message,
            "parsed": CodeChangeResponse(**calls[0]["args"]),
            "parsing_error": None,
        }

    except ValidationError as error:
        return {
            "raw": message,
            "parsed": None,
            "parsing_error": error,
        }


def _validate_code_changes(
    result: CodeChangeResponse,
) -> None:
    """
    Validate generated code changes before
    they are passed to CodeEditService.
    """

    for change in result.changes:

        if not change.file:
            raise ValueError(
                "Code change file cannot be empty."
            )

        if (
            change.file.startswith("/")
            or change.file.startswith("\\")
        ):
            raise ValueError(
                f"Absolute paths are not allowed: "
                f"{change.file}"
            )

        normalized_path = (
            change.file.replace(
                "\\",
                "/",
            )
        )

        if (
            ".."
            in normalized_path.split("/")
        ):
            raise ValueError(
                f"Parent directory traversal is "
                f"not allowed: {change.file}"
            )

        if not change.reason:
            raise ValueError(
                f"Reason cannot be empty: "
                f"{change.file}"
            )

        if change.action in {
            "create",
            "modify",
        }:

            if change.content is None:
                raise ValueError(
                    f"Content is required for "
                    f"{change.action}: "
                    f"{change.file}"
                )

            if not isinstance(
                change.content,
                str,
            ):
                raise ValueError(
                    f"Content must be a string: "
                    f"{change.file}"
                )

        if change.action == "delete":

            if change.content is not None:
                raise ValueError(
                    f"Deleted file must have "
                    f"null content: "
                    f"{change.file}"
                )