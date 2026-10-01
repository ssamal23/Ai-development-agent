import json

from langfuse import observe, get_client

from src.llm.factory import get_llm
from src.services.observability import get_langchain_callbacks


@observe(as_type="agent", name="escalation-agent")
def generate_escalation_pr(
    ticket: dict,
    failure_type: str,
    verification_result: dict | None = None,
    test_result: dict | None = None,
    code_changes: dict | None = None,
    attempts: int = 0,
) -> dict:
    get_client().update_current_span(
        input={
            "ticket_id": ticket.get("id"),
            "failure_type": failure_type,
            "attempts": attempts,
        }
    )
    """
    Generate a draft PR with failure analysis when max retries exceeded.

    This handles escalation when:
    - Verification fails after 3 attempts
    - Tests fail after 3 attempts

    The PR includes detailed failure analysis and remediation suggestions.
    """

    llm = get_llm()

    failure_context = ""

    if failure_type == "verification" and verification_result:
        failure_context = f"""
VERIFICATION FAILURE ANALYSIS:

{json.dumps(
    verification_result,
    indent=2,
)}

The implementation failed verification checks after {attempts} attempts.

Key Issues:
- Criteria Met: {verification_result.get('criteria_met', 'Unknown')}
- Issues Found: {verification_result.get('issues', [])}
- Recommendations: {verification_result.get('recommendations', [])}
"""

    elif failure_type == "tests" and test_result:
        failure_context = f"""
TEST FAILURE ANALYSIS:

{json.dumps(
    test_result,
    indent=2,
)}

The implementation failed tests after {attempts} attempts.

Test Output:
{test_result.get('output', 'No output')}

Failed Tests:
{test_result.get('failed_tests', [])}

Errors:
{test_result.get('errors', [])}
"""

    elif failure_type == "apply":
        failure_context = f"""
CODE APPLY FAILURE ANALYSIS:

The generated code changes could not be applied to the
repository after {attempts} attempts.

This typically means the Coding Agent used the wrong
action (create/modify/delete) for a file - e.g. "create"
for a file that already exists, or "modify" for a file
that does not exist.
"""

    prompt = f"""
You are a senior software engineer analyzing an implementation that failed
after {attempts} retry attempts.

Your task is to generate a comprehensive escalation PR body that includes:

1. Problem Summary - What failed and why
2. Failure Analysis - Deep dive into the root causes
3. Attempted Solutions - What was tried
4. Remediation Steps - What a human developer should do next
5. Code Quality Issues - Any secondary issues found
6. Next Steps - Recommendations for resolution

TICKET:

{json.dumps(
    ticket,
    indent=2,
)}

{failure_context}

CODE CHANGES ATTEMPTED:

{json.dumps(
    code_changes or {},
    indent=2,
)}

Generate a professional PR body in Markdown format that:

1. Clearly explains what failed
2. Provides actionable remediation steps
3. Includes code snippets if relevant
4. Suggests alternative approaches
5. Maintains a professional tone
6. Is suitable for human review and action

Return ONLY the Markdown content, no explanations outside of it.
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
            "Escalation Agent returned an invalid response."
        )

    content = content.strip()

    if not content:
        raise ValueError(
            "Escalation Agent returned an empty response."
        )

    return {
        "body": content,
        "failure_type": failure_type,
        "attempts": attempts,
        "draft": True,
        "labels": [
            "ai-agent",
            f"escalation-{failure_type}",
            "needs-review",
        ],
    }


@observe(as_type="tool", name="failure-report")
def create_failure_report(
    ticket: dict,
    failure_type: str,
    verification_result: dict | None = None,
    test_result: dict | None = None,
    coding_attempts: int = 0,
    verification_attempts: int = 0,
    test_attempts: int = 0,
) -> dict:
    """
    Create a detailed failure report for user notification.

    Returns a report that can be:
    - Stored in database
    - Sent via notification
    - Displayed in UI
    """

    report = {
        "ticket_id": ticket.get("id", "unknown"),
        "ticket_title": ticket.get("title", "unknown"),
        "failure_type": failure_type,
        "status": "FAILED",
        "summary": "",
        "details": {},
        "attempts": {
            "coding": coding_attempts,
            "verification": verification_attempts,
            "testing": test_attempts,
        },
        "recommendations": [],
    }

    if failure_type == "verification" and verification_result:
        report["summary"] = (
            "Implementation failed verification checks after "
            f"{verification_attempts} attempts"
        )
        report["details"] = {
            "failure_reason": "Verification checks did not pass",
            "criteria_met": verification_result.get(
                "criteria_met",
                0
            ),
            "issues": verification_result.get("issues", []),
            "score": verification_result.get("score", 0),
        }
        report["recommendations"] = [
            "Review verification feedback carefully",
            "Address each failing criterion individually",
            "Consider alternative implementation approaches",
            "Request help from senior developer if needed",
        ]

    elif failure_type == "tests" and test_result:
        report["summary"] = (
            f"Tests failed after {test_attempts} attempts"
        )
        report["details"] = {
            "failure_reason": "Automated tests did not pass",
            "failed_tests": test_result.get(
                "failed_tests",
                []
            ),
            "errors": test_result.get("errors", []),
            "test_output": test_result.get("output", ""),
        }
        report["recommendations"] = [
            "Analyze test failure output carefully",
            "Fix the root cause, not just the symptoms",
            "Ensure all edge cases are handled",
            "Add additional test cases if needed",
        ]

    elif failure_type == "apply":
        report["summary"] = (
            "Generated code changes could not be applied "
            f"after {coding_attempts} attempts"
        )
        report["details"] = {
            "failure_reason": (
                "CodeEditService rejected the changes "
                "(wrong create/modify/delete action for "
                "the file's actual state)"
            ),
        }
        report["recommendations"] = [
            "Check whether the target file already exists "
            "in the repository",
            "Use 'modify' instead of 'create' for existing "
            "files, and vice versa",
            "Review the implementation plan for stale "
            "assumptions about the repository structure",
        ]

    return report
