from src.llm.factory import get_llm


def analyze_ticket(ticket: dict) -> str:
    llm = get_llm()

    prompt = f"""
You are a software development requirement analyst.

Analyze the following Agile ticket.

Ticket ID:
{ticket["id"]}

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

    response = llm.invoke(prompt)

    return response.content