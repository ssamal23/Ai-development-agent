To reun the backend application
uvicorn main:app --reload


┌─────────────────────────────────────────────────────────────────────┐
│                         DEVELOPER / USER                            │
│                                                                     │
│  Hardcoded Ticket                                                   │
│                                                                     │
│  ID: DEMO-001                                                       │
│  Title: Create Login Page                                           │
│  Description: Create login page...                                  │
│  Acceptance Criteria:                                               │
│    • Email field                                                    │
│    • Password field                                                 │
│    • Login button                                                   │
│    • Required validation                                            │
│    • Existing architecture/style                                    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         FASTAPI                                     │
│                                                                     │
│                    POST /api/agent/analyze                          │
│                                                                     │
│                    TicketRequest                                    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       LANGGRAPH WORKFLOW                            │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   1. Create         │
                    │   Temporary         │
                    │   Workspace         │
                    └──────────┬──────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    2. TICKET AGENT                                  │
│                                                                     │
│  Understands:                                                       │
│  • Ticket                                                        │
│  • Description                                                     │
│  • Acceptance Criteria                                             │
│                                                                     │
│  Produces ticket analysis                                          │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    3. REPOSITORY INDEX                              │
│                                                                     │
│                 Existing repository index                           │
│                                                                     │
│  repository.json                                                    │
│                                                                     │
│  Contains:                                                          │
│  • File paths                                                       │
│  • Hashes                                                           │
│  • File sizes                                                       │
│  • Languages                                                        │
│  • File contents                                                    │
│  • Last Git commit                                                  │
│                                                                     │
│  IMPORTANT:                                                         │
│  No full repository scan for every ticket.                         │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    4. REPOSITORY AGENT                              │
│                                                                     │
│                 Search existing index                               │
│                                                                     │
│  Ticket: "Create Login Page"                                        │
│                 ↓                                                   │
│  Search file names                                                  │
│  Search file paths                                                   │
│  Search file contents                                                │
│                 ↓                                                   │
│  Relevant Files                                                      │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Read Relevant      │
                    │ Files               │
                    └──────────┬──────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    5. PLANNING AGENT                                │
│                                                                     │
│  Inputs:                                                            │
│  • Ticket                                                           │
│  • Repository structure                                             │
│  • Relevant source files                                            │
│                                                                     │
│  Determines:                                                        │
│  • Files to modify                                                  │
│  • Files to create                                                  │
│  • Implementation approach                                          │
│  • Existing components to reuse                                     │
│                                                                     │
│                  Implementation Plan                                │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    6. CODING AGENT                                  │
│                                                                     │
│  Inputs:                                                            │
│  • Ticket                                                           │
│  • Implementation Plan                                              │
│  • Repository Context                                               │
│  • Latest Workspace Context                                         │
│  • Previous Code Changes                                            │
│  • Verification Feedback                                            │
│  • Test Feedback                                                    │
│                                                                     │
│  Produces:                                                          │
│                                                                     │
│  {                                                                  │
│    "changes": [                                                     │
│      {                                                              │
│        "action": "modify",                                          │
│        "file": "...",                                                │
│        "content": "complete file..."                                │
│      }                                                              │
│    ]                                                                │
│  }                                                                  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    7. VERIFICATION AGENT                             │
│                                                                     │
│  Checks generated code against:                                    │
│                                                                     │
│  • Ticket                                                          │
│  • Acceptance Criteria                                              │
│  • Implementation Plan                                              │
│  • Generated Code                                                   │
│                                                                     │
│                    ┌───────────────┐                                │
│                    │   PASS / FAIL │                                │
│                    └───────┬───────┘                                │
│                            │                                         │
│                 ┌──────────┴──────────┐                              │
│                 │                     │                              │
│                FAIL                  PASS                           │
│                 │                     │                              │
│                 ▼                     ▼                              │
│        Refresh Workspace       Apply Code Changes                   │
│                 │                     │                              │
│                 ▼                     ▼                              │
│          Coding Agent               Testing                         │
│                 │                                                     │
│                 └── Max 3 attempts                                   │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    8. APPLY CODE CHANGES                             │
│                                                                     │
│                  Temporary Workspace                                │
│                                                                     │
│  CodeEditService                                                    │
│                                                                     │
│  create → create file                                               │
│  modify → update file                                                │
│  delete → delete file                                                │
│                                                                     │
│  IMPORTANT:                                                          │
│  Real repository is NOT modified yet.                               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    9. REFRESH WORKSPACE                              │
│                                                                     │
│  Read latest files from temporary workspace.                        │
│                                                                     │
│  This becomes the current implementation state.                     │
│                                                                     │
│  Used for test/retry cycles.                                        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    10. TEST AGENT                                   │
│                                                                     │
│  Runs tests inside temporary workspace.                             │
│                                                                     │
│  Detects:                                                           │
│  • npm test                                                         │
│  • pytest                                                           │
│  • Other supported test commands                                    │
│                                                                     │
│                    ┌───────────────┐                                │
│                    │   PASS / FAIL │                                │
│                    └───────┬───────┘                                │
│                            │                                         │
│                 ┌──────────┴──────────┐                              │
│                 │                     │                              │
│                FAIL                  PASS                           │
│                 │                     │                              │
│                 ▼                     ▼                              │
│        Refresh Workspace       Tests Passed                         │
│                 │                                                     │
│                 ▼                                                     │
│          Coding Agent                                                 │
│                 │                                                     │
│                 └── Max 3 attempts                                   │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               │ PASS
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    11. CREATE GIT BRANCH                             │
│                                                                     │
│  Git Agent                                                          │
│                                                                     │
│  Example:                                                           │
│                                                                     │
│  ai-agent/DEMO-001-create-login-page                                │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    12. APPLY WORKSPACE                              │
│                                                                     │
│  Successful tested workspace                                        │
│                         ↓                                           │
│                  Real Repository                                    │
│                                                                     │
│  Only after:                                                        │
│  ✓ Verification PASS                                                │
│  ✓ Tests PASS                                                       │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    13. GIT AGENT                                    │
│                                                                     │
│  git status                                                         │
│       ↓                                                             │
│  git add -A                                                         │
│       ↓                                                             │
│  git commit                                                         │
│       ↓                                                             │
│  git push -u origin <branch>                                        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    14. GITHUB                                      │
│                                                                     │
│  Branch pushed                                                      │
│                                                                     │
│  ai-agent/DEMO-001-create-login-page                                │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    15. PR AGENT                                    │
│                                                                     │
│  Creates Pull Request                                               │
│                                                                     │
│  Title:                                                             │
│  DEMO-001: Create Login Page                                        │
│                                                                     │
│  Body contains:                                                     │
│  • Ticket                                                          │
│  • Description                                                      │
│  • Acceptance Criteria                                              │
│  • Changed Files                                                    │
│  • Verification Status                                             │
│  • Verification Score                                               │
│  • Test Status                                                      │
│  • Branch                                                           │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    GitHub PR        │
                    │                     │
                    │    PR URL           │
                    │                     │
                    │    PR Number        │
                    └─────────────────────┘

Repository indexing flow: 

                 Repository Connected
                         │
                         ▼
                Is Index Available?
                  /             \
                NO               YES
                │                 │
                ▼                 ▼
          Full Repository      Check Git
              Scan             Commit
                │                 │
                │          Has repository
                │             changed?
                │             /       \
                │           NO         YES
                │           │           │
                │           │           ▼
                │           │      git diff
                │           │           │
                │           │           ▼
                │           │    Added / Modified
                │           │       / Deleted
                │           │           │
                │           │           ▼
                │           │    Update ONLY
                │           │    changed files
                │           │
                └───────────┴───────────────┐
                                            ▼
                                   repository.json

┌──────────────────────────────────────────┐
│          AI DEVELOPMENT AGENT            │
├──────────────────────────────────────────┤
│                                          │
│  1. Connect to Git Repository       ✅   │
│                                          │
│  2. Full Repository Scan             ✅   │
│                                          │
│  3. Repository Index                 ✅   │
│                                          │
│  4. Incremental Index Update         ✅   │
│                                          │
│  5. Receive Development Ticket       ✅   │
│                                          │
│  6. Analyze Ticket                   ✅   │
│                                          │
│  7. Search Repository Index          ✅   │
│                                          │
│  8. Find Relevant Files              ✅   │
│                                          │
│  9. Read Relevant Code                ✅   │
│                                          │
│ 10. Create Implementation Plan       ✅   │
│                                          │
│ 11. Generate Code Changes             ✅   │
│                                          │
│ 12. Apply Changes to Repository      ✅   │
│                                          │
│ 13. Run Tests                         🔨   │
│                                          │
│ 14. Fix Failed Tests                  ⏳   │
│                                          │
│ 15. Git Branch                        ⏳   │
│                                          │
│ 16. Git Commit                        ⏳   │
│                                          │
│ 17. Git Push                          ⏳   │
│                                          │
│ 18. Create Pull Request               ⏳   │
│                                          │
│ 19. Azure Boards MCP                  ⏳   │
│                                          │
│ 20. Figma Integration                 ⏳   │
│                                          │
│ 21. Screenshot / Vision               ⏳   │
│                                          │
│ 22. UI Visual Validation              ⏳   │
│                                          │
└──────────────────────────────────────────┘