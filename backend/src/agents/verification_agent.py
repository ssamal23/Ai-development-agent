import json

from src.llm.factory import get_llm


def verify_implementation(
    ticket: dict,
    implementation_plan: dict,
    code_changes: dict,
) -> dict:
    """
    Verify whether the generated code satisfies
    the story ticket and acceptance criteria.
    """

    llm = get_llm()

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

STORY / TICKET:

{json.dumps(ticket, indent=2)}

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

    response = llm.invoke(prompt)

    content = response.content

    if not isinstance(content, str):
        raise ValueError(
            "Verification Agent returned invalid response."
        )

    content = content.strip()

    # Remove Markdown fences if the model returns them.
    if content.startswith("```"):
        content = (
            content
            .replace("```json", "", 1)
            .replace("```", "", 1)
            .strip()
        )

    try:
        result = json.loads(content)

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