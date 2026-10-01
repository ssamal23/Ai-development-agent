from langfuse import observe, get_client

from src.llm.factory import get_llm
from src.services.observability import get_langchain_callbacks
from src.utils.ticket_category import parse_ticket_category


@observe(as_type="agent", name="ticket-agent")
def analyze_ticket(ticket: dict) -> str:
    get_client().update_current_span(
        input={
            "ticket_id": ticket.get("id"),
            "ticket_title": ticket.get("title"),
        }
    )

    llm = get_llm()

    category = parse_ticket_category(
        ticket.get("id")
    )

    if category["code"] == "unknown":
        category_context = """
TICKET CATEGORY: Not specified in the ticket ID.
Infer scope entirely from the title/description below.
"""
    else:
        category_context = f"""
TICKET CATEGORY (parsed from the ticket ID prefix):

- Code: {category["code"]}
- Label: {category["label"]}
- Area: {category["area"] or "not area-specific (e.g. testing)"}
- Enhancement: {(
    "Yes - this modifies/extends EXISTING functionality, "
    "not a from-scratch build"
    if category["enhancement"]
    else "No - likely new functionality"
)}

Treat this category as a strong, authoritative signal for
scope. Only deviate from it if the title/description below
clearly contradicts it.
"""

    prompt = f"""
You are a software development requirement analyst.

Analyze the following Agile ticket.

Ticket ID:
{ticket["id"]}

{category_context}

Title:
{ticket["title"]}

Description:
{ticket["description"]}

Acceptance Criteria:
{ticket["acceptance_criteria"]}

Provide:

1. Requirement summary
2. Functional requirements
3. Technical considerations
4. Possible files/components that may need changes
5. Testing requirements
6. Potential risks

Do not write code yet.
"""

    response = llm.invoke(
        prompt,
        config={
            "callbacks": get_langchain_callbacks(),
        },
    )

    return response.content