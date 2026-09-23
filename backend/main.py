from fastapi import FastAPI
from pydantic import BaseModel

from src.services.repository_index_service import (
    RepositoryIndexService,
)

from src.services.repository_service import (
    RepositoryService,
)

from src.workflows.ticket_workflow import (
    create_workflow,
)


app = FastAPI(
    title="AI Development Agent",
    version="0.9.0",
)


class TicketRequest(BaseModel):
    ticket: dict


@app.get("/")
def root():
    return {
        "message": (
            "AI Development Agent is running"
        )
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.get("/repository/scan")
def scan_repository():

    service = RepositoryService()

    files = service.scan_repository()

    return {
        "total_files": len(files),

        "files": [
            file.model_dump()
            for file in files
        ],
    }


@app.post("/repository/index")
def create_repository_index():

    service = RepositoryIndexService()

    index = service.index_repository()

    return {
        "message": (
            "Repository indexed successfully"
        ),

        "repository": (
            index.repository_path
        ),

        "commit": index.last_commit,

        "total_files": len(
            index.files
        ),
    }


@app.post("/repository/update-index")
def update_repository_index():

    service = RepositoryIndexService()

    result = service.update_index()

    index = result["index"]

    changes = result["changes"]

    return {
        "message": (
            "Repository index updated"
        ),

        "repository": (
            index.repository_path
        ),

        "commit": index.last_commit,

        "total_files": len(
            index.files
        ),

        "changes": changes,
    }


@app.post("/api/agent/analyze")
def analyze_ticket_endpoint(
    request: TicketRequest,
):

    workflow = create_workflow()

    result = workflow.invoke({
        "ticket": request.ticket,

        "analysis": "",

        "repository_structure": [],

        "relevant_files": [],

        "repository_context": [],

        "workspace_context": [],

        "implementation_plan": {},

        "code_changes": {},

        "previous_code_changes": {},

        "verification_result": {},

        "verification_attempts": 0,

        "coding_attempts": 0,

        "changed_files": [],

        "test_result": {},

        "test_attempts": 0,

        "workspace_path": "",

        "git_branch": "",

        "git_result": {},

        "pull_request": {},
    })

    return {
        "ticket": result["ticket"],

        "analysis": result["analysis"],

        "repository_structure": (
            result[
                "repository_structure"
            ]
        ),

        "relevant_files": (
            result[
                "relevant_files"
            ]
        ),

        "implementation_plan": (
            result[
                "implementation_plan"
            ]
        ),

        "code_changes": (
            result[
                "code_changes"
            ]
        ),

        "verification_result": (
            result[
                "verification_result"
            ]
        ),

        "verification_attempts": (
            result[
                "verification_attempts"
            ]
        ),

        "coding_attempts": (
            result[
                "coding_attempts"
            ]
        ),

        "changed_files": (
            result[
                "changed_files"
            ]
        ),

        "test_result": (
            result[
                "test_result"
            ]
        ),

        "test_attempts": (
            result[
                "test_attempts"
            ]
        ),

        "workspace_path": (
            result[
                "workspace_path"
            ]
        ),

        "git_branch": (
            result[
                "git_branch"
            ]
        ),

        "git_result": (
            result[
                "git_result"
            ]
        ),

        "pull_request": (
            result[
                "pull_request"
            ]
        ),
    }

@app.get("/repository/search")
def search_repository(query: str):

    service = RepositorySearchService()

    results = service.search(query)

    return {
        "query": query,
        "total_results": len(results),
        "files": [
            file.model_dump()
            for file in results
        ],
    }