import json

from src.llm.factory import get_llm
from src.models.code_change import (
    CodeChangeResponse,
)


def generate_code_changes(
    ticket: dict,
    implementation_plan: dict,
    repository_context: list[dict],
    verification_result: dict | None = None,
    test_result: dict | None = None,
    workspace_context: list[dict] | None = None,
    previous_code_changes: dict | None = None,
) -> CodeChangeResponse:
    """
    Generate code changes using the current
    repository/workspace state.

    During retries, workspace_context is the
    source of truth for the latest implementation.
    """

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

    previous_changes_context = ""

    if previous_code_changes:
        previous_changes_context = f"""
PREVIOUS GENERATED CODE CHANGES:

{json.dumps(
    previous_code_changes,
    indent=2,
)}

These changes represent the previous implementation
attempt.

Do not blindly regenerate them.

Keep working changes where appropriate and fix
only the parts that caused verification or test
failures.
"""

    latest_workspace_context = (
        workspace_context
        or []
    )

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

25. Return ONLY valid JSON.

26. Do not return Markdown code fences.

27. Do not add explanations outside the JSON.

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

Return exactly this JSON structure:

{{
  "changes": [
    {{
      "action": "create",
      "file": "relative/path/to/file",
      "reason": "Why this file is required.",
      "content": "Complete file content."
    }},
    {{
      "action": "modify",
      "file": "relative/path/to/file",
      "reason": "Why this file needs modification.",
      "content": "Complete updated file content."
    }},
    {{
      "action": "delete",
      "file": "relative/path/to/file",
      "reason": "Why this file should be deleted.",
      "content": null
    }}
  ]
}}

If no file needs to be deleted, do not include
a delete change.

Every create or modify change MUST contain
complete file content.

Every delete change MUST contain:

"content": null
"""

    response = llm.invoke(prompt)

    content = response.content

    if not isinstance(
        content,
        str,
    ):
        raise ValueError(
            "Coding Agent returned an invalid response."
        )

    content = content.strip()

    if not content:
        raise ValueError(
            "Coding Agent returned an empty response. "
            f"stop_reason="
            f"{response.response_metadata.get('stop_reason')} "
            f"usage={response.response_metadata.get('usage')}"
        )

    if content.startswith("```"):

        if content.startswith("```json"):
            content = content[
                len("```json"):
            ].strip()

        elif content.startswith("```"):
            content = content[
                len("```"):
            ].strip()

        if content.endswith("```"):
            content = content[
                :-len("```")
            ].strip()

    try:
        data = json.loads(
            content
        )

    except json.JSONDecodeError as error:
        raise ValueError(
            "Coding Agent returned invalid JSON: "
            f"{error}"
        )

    if not isinstance(
        data,
        dict,
    ):
        raise ValueError(
            "Coding Agent response must be a JSON object."
        )

    if "changes" not in data:
        raise ValueError(
            "Coding Agent response is missing "
            "'changes'."
        )

    if not isinstance(
        data["changes"],
        list,
    ):
        raise ValueError(
            "'changes' must be a list."
        )

    result = CodeChangeResponse(
        **data
    )

    _validate_code_changes(
        result
    )

    return result


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