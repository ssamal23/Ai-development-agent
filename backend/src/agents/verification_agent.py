import json

from langfuse import observe, get_client

from src.llm.factory import get_llm
from src.services.observability import get_langchain_callbacks
from src.utils.llm_json import (
    strip_markdown_json_fence,
)


@observe(as_type="agent", name="verification-agent")
def verify_implementation(
    ticket: dict,
    implementation_plan: dict,
    code_changes: dict,
    design_reference: dict | None = None,
) -> dict:
    """
    Verify whether the generated code satisfies
    the story ticket and acceptance criteria.
    """

    # Override the default @observe input: code_changes carries
    # full generated file content, which belongs in the output of
    # the Coding Agent's own span, not duplicated across every
    # span that happens to receive it as an argument.
    get_client().update_current_span(
        input={
            "ticket_id": ticket.get("id"),
            "ticket_title": ticket.get("title"),
            "acceptance_criteria": ticket.get(
                "acceptance_criteria"
            ),
            "changed_files": [
                change.get("file")
                for change in code_changes.get(
                    "changes", []
                )
            ],
        }
    )

    llm = get_llm()

    design_context = ""

    if design_reference and design_reference.get("style_tokens"):
        design_context = f"""
DESIGN REFERENCE - EXACT STYLE VALUES (authoritative):

{design_reference["style_tokens"]}

When an acceptance criterion requires matching the design,
check the hex colors, fonts, sizes and radii in the GENERATED
CODE against these values (e.g. a CSS variable or rule that
holds #33A533 satisfies a "green #33A533" requirement).
Adding or changing CSS variables to hold these design values
is REQUIRED, not an unnecessary change, and does not violate
the plan's advice to reuse existing variables. Do not fail a
criterion only because you cannot see the design image; judge
it from these values. Fail it only when the code uses a
different color/value than listed for that element.
"""

    prompt = f"""
You are a senior software engineer performing a
strict implementation review.

Your job is to verify whether the generated code
correctly implements the requested story.

Do NOT write or modify code.

Compare these three things:

1. STORY / TICKET
2. IMPLEMENTATION PLAN
3. GENERATED CODE

Verification must focus primarily on the STORY
and its ACCEPTANCE CRITERIA.

IMPORTANT RULES:

1. Every acceptance criterion must be satisfied.
2. Identify missing requirements.
3. Identify incorrectly implemented requirements.
4. Identify unnecessary changes that are unrelated
   to the story.
5. Check whether the implementation follows the
   implementation plan.
6. Do not reject code only because you would have
   implemented it differently.
7. Do not invent requirements that are not present
   in the ticket.
8. Existing repository architecture should be
   respected according to the implementation plan.
9. Be strict about acceptance criteria.
10. Do NOT generate code.
11. Return ONLY valid JSON.
12. Do not use Markdown code fences.
13. Fail a criterion only on CONCRETE evidence in the
    GENERATED CODE CHANGES that it is not met. Do not fail
    it because of something that "may", "might" or "could"
    be wrong in files you were not shown (existing CSS, other
    components): you only see the changed files, so
    unverifiable risk is not a failure.
14. The implementation plan describes ONE way to reach the
    goal. If the code meets the acceptance criterion by a
    different technique (e.g. a class toggle instead of
    position:fixed), that is a PASS. Fail for a plan deviation
    only when it breaks a criterion or the existing
    functionality.

STORY / TICKET:

{json.dumps(ticket, indent=2)}
{design_context}
IMPLEMENTATION PLAN:

{json.dumps(implementation_plan, indent=2)}

GENERATED CODE CHANGES:

{json.dumps(code_changes, indent=2)}

Return exactly this JSON structure:

{{
  "status": "PASS | FAIL",
  "summary": "Short explanation of the verification result.",
  "score": 0,
  "acceptance_criteria": [
    {{
      "criterion": "Acceptance criterion from the ticket",
      "status": "PASS | FAIL",
      "reason": "Why this criterion passed or failed."
    }}
  ],
  "missing_requirements": [
    "Requirement that has not been implemented."
  ],
  "incorrect_requirements": [
    "Requirement that has been implemented incorrectly."
  ],
  "unnecessary_changes": [
    "Changes that are unrelated to the story."
  ],
  "recommendations": [
    "Specific change required before the implementation can pass."
  ]
}}

SCORING:

100 = All requirements correctly implemented.

90-99 = Minor non-functional issue but all
acceptance criteria are satisfied.

70-89 = One or more important issues exist.

Below 70 = Major requirements are missing or
incorrect.

STATUS RULE:

Return PASS only when all acceptance criteria
are satisfied and there are no important
implementation problems.

Otherwise return FAIL.
"""

    response = llm.invoke(
        prompt,
        config={
            "callbacks": get_langchain_callbacks(),
        },
    )

    content = response.content

    if not isinstance(content, str):
        raise ValueError(
            "Verification Agent returned invalid response."
        )

    content = strip_markdown_json_fence(content)

    if not content:
        raise ValueError(
            "Verification Agent returned a response that was "
            "only a Markdown code fence with nothing inside "
            "it (likely truncated mid-generation). "
            f"stop_reason="
            f"{response.response_metadata.get('stop_reason')} "
            f"usage={response.response_metadata.get('usage')}"
        )

    try:
        # strict=False: tolerate raw control characters (e.g.
        # an unescaped newline) inside a JSON string value,
        # which standard JSON forbids but LLM output routinely
        # contains when a string field holds multi-line text.
        result = json.loads(
            content,
            strict=False,
        )

    except json.JSONDecodeError as error:
        raise ValueError(
            "Verification Agent returned invalid JSON: "
            f"{error}"
        )

    _normalize_verification_result(result)

    _validate_verification_result(result)

    return result


def _normalize_status(
    status: object,
) -> str:
    """
    Normalize an LLM-provided status value to
    exactly "PASS" or "FAIL".

    Any value that isn't a clean, case-insensitive
    match for "PASS" (e.g. "Partial", "WARN", "N/A",
    stray whitespace) is conservatively treated as
    "FAIL" instead of crashing the workflow.
    """

    normalized = str(status).strip().upper()

    if normalized == "PASS":
        return "PASS"

    return "FAIL"


def _normalize_verification_result(
    result: dict,
) -> None:
    """
    Normalize status fields returned by the LLM
    before strict validation, so minor formatting
    deviations don't crash the whole ticket run.
    """

    if "status" in result:
        result["status"] = _normalize_status(
            result["status"]
        )

    for criterion in result.get(
        "acceptance_criteria",
        [],
    ):
        if (
            isinstance(criterion, dict)
            and "status" in criterion
        ):
            criterion["status"] = _normalize_status(
                criterion["status"]
            )


def _validate_verification_result(
    result: dict,
) -> None:
    """
    Validate the structure returned by the LLM.
    """

    required_fields = {
        "status",
        "summary",
        "score",
        "acceptance_criteria",
        "missing_requirements",
        "incorrect_requirements",
        "unnecessary_changes",
        "recommendations",
    }

    missing_fields = (
        required_fields
        - result.keys()
    )

    if missing_fields:
        raise ValueError(
            "Verification Agent response is missing "
            f"required fields: {sorted(missing_fields)}"
        )

    if result["status"] not in {
        "PASS",
        "FAIL",
    }:
        raise ValueError(
            "Verification status must be "
            "PASS or FAIL."
        )

    if not isinstance(
        result["summary"],
        str,
    ):
        raise ValueError(
            "Verification summary must be a string."
        )

    if not isinstance(
        result["score"],
        (int, float),
    ):
        raise ValueError(
            "Verification score must be a number."
        )

    if not 0 <= result["score"] <= 100:
        raise ValueError(
            "Verification score must be between 0 and 100."
        )

    if not isinstance(
        result["acceptance_criteria"],
        list,
    ):
        raise ValueError(
            "Acceptance criteria must be a list."
        )

    if not isinstance(
        result["missing_requirements"],
        list,
    ):
        raise ValueError(
            "Missing requirements must be a list."
        )

    if not isinstance(
        result["incorrect_requirements"],
        list,
    ):
        raise ValueError(
            "Incorrect requirements must be a list."
        )

    if not isinstance(
        result["unnecessary_changes"],
        list,
    ):
        raise ValueError(
            "Unnecessary changes must be a list."
        )

    if not isinstance(
        result["recommendations"],
        list,
    ):
        raise ValueError(
            "Recommendations must be a list."
        )

    for criterion in result[
        "acceptance_criteria"
    ]:
        if not isinstance(
            criterion,
            dict,
        ):
            raise ValueError(
                "Each acceptance criterion "
                "must be an object."
            )

        required_criterion_fields = {
            "criterion",
            "status",
            "reason",
        }

        missing_criterion_fields = (
            required_criterion_fields
            - criterion.keys()
        )

        if missing_criterion_fields:
            raise ValueError(
                "Acceptance criterion is missing "
                f"fields: "
                f"{sorted(missing_criterion_fields)}"
            )

        if criterion["status"] not in {
            "PASS",
            "FAIL",
        }:
            raise ValueError(
                "Acceptance criterion status "
                "must be PASS or FAIL."
            )

    # An LLM-inconsistent PASS (one that still lists
    # missing/incorrect requirements) is downgraded to
    # FAIL instead of crashing the workflow. The listed
    # issues are real signal for the next coding retry
    # even if the LLM's own top-level status disagreed.
    if (
        result["status"] == "PASS"
        and (
            result["missing_requirements"]
            or result["incorrect_requirements"]
        )
    ):
        result["status"] = "FAIL"