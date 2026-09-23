import json

from src.llm.factory import get_llm


def create_implementation_plan(
    ticket: dict,
    repository_structure: list[str],
    relevant_files: list[dict],
) -> dict:
    """
    Create an implementation plan based on:

    - Development ticket
    - Actual repository structure
    - Actual existing file contents

    The repository is treated as the source of truth.
    """

    llm = get_llm()

    # =========================================================
    # Repository structure
    # =========================================================

    structure_context = "\n".join(
        repository_structure
    )

    # =========================================================
    # Relevant file contents
    # =========================================================

    file_context_parts = []

    for file in relevant_files:
        file_context_parts.append(
            f"""
FILE: {file["path"]}

LANGUAGE: {file.get("language")}

CONTENT:
{file.get("content", "")}

================================
"""
        )

    file_context = "\n".join(
        file_context_parts
    )

    # =========================================================
    # Planning prompt
    # =========================================================

    prompt = f"""
You are a senior software architect working
inside an EXISTING software repository.

Your job is to create an implementation plan
for the development ticket below.

The repository is the SOURCE OF TRUTH.

You MUST understand and follow the existing
repository structure, architecture, coding
patterns, component patterns, styling system,
naming conventions, and technologies.

Do NOT design a generic application.

Do NOT invent an architecture.

Do NOT assume technologies that are not present.

============================================================
DEVELOPMENT TICKET
============================================================

{json.dumps(ticket, indent=2)}

============================================================
ACTUAL REPOSITORY STRUCTURE
============================================================

{structure_context}

============================================================
ACTUAL RELEVANT FILE CONTENT
============================================================

{file_context}

============================================================
ARCHITECTURAL RULES
============================================================

RULE 1 — REPOSITORY IS THE SOURCE OF TRUTH
------------------------------------------------------------

The actual repository structure and existing
source code have higher priority than generic
software architecture knowledge.

Your plan must be based on what actually exists
in the repository.

Do not assume a standard or popular architecture.

------------------------------------------------------------

RULE 2 — DO NOT INVENT FOLDERS
------------------------------------------------------------

Before creating a new file, inspect the actual
repository structure.

If the project already has:

src/pages/

then use:

src/pages/

If the project already has:

src/components/

then use:

src/components/

If the project already has:

src/features/

then follow that structure.

DO NOT create a new folder merely because it is
common in other React, Angular, Vue, Node, or
other projects.

For example, do not automatically create:

src/features/
src/modules/
src/screens/
src/views/

unless the repository already uses those
structures or there is strong evidence that a new
directory is genuinely required.

------------------------------------------------------------

RULE 3 — FOLLOW EXISTING FILE NAMING
------------------------------------------------------------

Inspect existing file names and follow their
naming convention.

For example, if the repository uses:

UserPage.tsx

then prefer:

LoginPage.tsx

If the repository uses:

user-page.tsx

then follow that convention.

If the repository uses:

login.tsx

follow that convention.

Do not introduce a different naming style.

------------------------------------------------------------

RULE 4 — FOLLOW EXISTING COMPONENT PATTERNS
------------------------------------------------------------

Inspect existing components.

Determine whether the project uses patterns such as:

function Component()

or:

const Component = () =>

or another established pattern.

The new component must follow the existing
component pattern.

Also follow existing conventions for:

- imports
- exports
- props
- hooks
- state
- event handlers
- JSX structure
- component organization

------------------------------------------------------------

RULE 5 — EXISTING CSS IS THE SOURCE OF TRUTH
------------------------------------------------------------

The existing project's styling system must be
treated as the SOURCE OF TRUTH.

Before creating or modifying CSS, inspect the
existing CSS files.

Identify:

- CSS variables
- colors
- typography
- font sizes
- font families
- spacing
- margins
- padding
- borders
- border radius
- buttons
- inputs
- forms
- containers
- layouts
- responsive breakpoints
- media queries
- existing reusable classes

The new feature must reuse the existing styling
approach wherever possible.

DO NOT invent a new visual design.

DO NOT introduce arbitrary colors.

DO NOT introduce arbitrary fonts.

DO NOT introduce a new spacing system.

DO NOT introduce a new design system.

DO NOT introduce a new CSS framework.

------------------------------------------------------------

RULE 6 — USE THE EXISTING STYLING TECHNOLOGY
------------------------------------------------------------

Determine which styling technology the repository
actually uses.

Examples:

.css
.scss
.module.css
Tailwind
styled-components
Emotion
Material UI
Bootstrap

Use the technology already used by the project.

If the project uses plain CSS:

use plain CSS.

If the project uses SCSS:

use SCSS.

If the project uses CSS modules:

use CSS modules.

DO NOT introduce another styling technology
just for the new feature.

------------------------------------------------------------

RULE 7 — REUSE EXISTING CSS VARIABLES
------------------------------------------------------------

If existing CSS defines variables such as:

--bg
--text
--accent
--border
--primary
--secondary

reuse those variables.

DO NOT create duplicate variables such as:

--login-background
--login-text
--login-primary

unless there is a specific architectural reason.

------------------------------------------------------------

RULE 8 — REUSE EXISTING CSS CLASSES
------------------------------------------------------------

If existing CSS contains reusable styles for:

- buttons
- inputs
- forms
- containers
- cards
- layouts

reuse those styles where appropriate.

Do not recreate an existing style with slightly
different values.

The new feature should visually look like it
belongs to the existing application.

------------------------------------------------------------

RULE 9 — DO NOT CHANGE GLOBAL CSS UNNECESSARILY
------------------------------------------------------------

Do not modify global CSS simply to make the new
feature work.

Prefer component-level CSS when appropriate.

Only modify global CSS if:

1. The existing architecture requires it, or
2. The ticket genuinely requires a global change.

Do not modify index.css just because a new
component is being added.

------------------------------------------------------------

RULE 10 — PRESERVE EXISTING VISUAL LANGUAGE
------------------------------------------------------------

The new feature must follow the existing project's:

- colors
- typography
- spacing
- borders
- buttons
- inputs
- layouts
- responsive behavior

The new feature should look like it was created
by an existing developer on the project.

It should NOT look like an independent AI-generated
design.

------------------------------------------------------------

RULE 11 — REUSE EXISTING COMPONENTS
------------------------------------------------------------

Before creating a new component, inspect the
existing repository.

Determine whether an existing component can be
reused or extended.

Do not create duplicate functionality.

------------------------------------------------------------

RULE 12 — REUSE EXISTING HOOKS
------------------------------------------------------------

Before creating a custom hook, inspect the
repository for existing hooks.

Do NOT create a custom hook simply because it is
considered good architecture.

Only create a new hook when:

1. The project already follows that pattern, OR
2. The ticket genuinely requires reusable logic.

------------------------------------------------------------

RULE 13 — REUSE EXISTING TYPES
------------------------------------------------------------

Before creating a new types file, inspect the
repository for existing type/model patterns.

Do NOT automatically create:

LoginPage.types.ts

or:

Login.types.ts

unless the project already follows that pattern
or the types are genuinely required.

------------------------------------------------------------

RULE 14 — MINIMUM REQUIRED FILES
------------------------------------------------------------

Create the smallest reasonable number of files
required to implement the ticket.

DO NOT create unnecessary:

- components
- hooks
- services
- utilities
- types
- constants
- folders

Do not over-engineer a simple ticket.

------------------------------------------------------------

RULE 15 — EXISTING FILE VS FILE TO MODIFY
------------------------------------------------------------

An existing file can be relevant for understanding
the application without requiring modification.

Therefore:

existing_relevant_files

means:

"Files inspected or useful for understanding
the implementation."

files_to_modify

means:

"Existing files that actually require code changes."

Do NOT put every relevant file into
files_to_modify.

------------------------------------------------------------

RULE 16 — NEW FILE DETECTION
------------------------------------------------------------

If the requested feature/component/page does
not already exist:

1. Confirm that it does not exist.
2. Inspect the repository structure.
3. Find the closest existing architectural pattern.
4. Determine the correct location.
5. Create the minimum required files.

Do not assume the requested component already exists.

------------------------------------------------------------

RULE 17 — ROUTING
------------------------------------------------------------

Before proposing routing changes, inspect the
repository.

If a routing library exists:

modify the existing routing structure.

If routing does not exist:

do not automatically introduce a routing library
unless the ticket explicitly requires routing.

Do not add React Router simply because the ticket
mentions a page.

------------------------------------------------------------

RULE 18 — DEPENDENCIES
------------------------------------------------------------

Do not add dependencies unless they are actually
required.

Before adding a dependency, check whether the
existing project already has functionality that
can satisfy the requirement.

If no dependency is required:

dependencies must be an empty array.

Do NOT modify:

package.json
package-lock.json

unless a real dependency change is required.

------------------------------------------------------------

RULE 19 — DO NOT MODIFY UNNECESSARY FILES
------------------------------------------------------------

Do not modify a file simply because it is related
to the application.

Only include a file in files_to_modify when the
implementation actually requires a change.

------------------------------------------------------------

RULE 20 — DO NOT REMOVE FUNCTIONALITY WITHOUT REASON
------------------------------------------------------------

Do not remove existing functionality simply because
the ticket introduces a new feature.

If existing demo/example content must be replaced,
explicitly explain why.

If existing functionality can remain, preserve it.

------------------------------------------------------------

RULE 21 — FOLLOW EXISTING PROJECT COMPLEXITY
------------------------------------------------------------

If the existing project is simple, keep the solution
simple.

If the existing project has a complex architecture,
follow that architecture.

Do not introduce enterprise-level abstractions into
a simple application.

Do not simplify a complex existing architecture
without a reason.

------------------------------------------------------------

RULE 22 — PLAN MUST BE IMPLEMENTABLE
------------------------------------------------------------

The plan will later be passed to a Coding Agent.

Therefore every planned file must have a clear
purpose.

The Coding Agent should be able to understand:

- which files already exist
- which files need modification
- which files need creation
- where new files belong
- what implementation is required
- which existing styles should be reused

------------------------------------------------------------

RULE 23 — PLAN CONSISTENCY
------------------------------------------------------------

The final JSON must be internally consistent.

Every file described as a "new file" in the
implementation_plan MUST appear in new_files.

Every file described as "modify" or "update" in the
implementation_plan MUST appear in files_to_modify.

Do not put an existing file in new_files.

Do not put a new file in files_to_modify.

Every stylesheet that must be newly created MUST
appear in new_files.

Do not include package.json or package-lock.json
unless dependencies actually change.

------------------------------------------------------------

RULE 24 — EXISTING DIRECTORY PREFERENCE
------------------------------------------------------------

When creating a new file:

1. Prefer an existing directory containing similar
   files.

2. If a suitable existing directory does not exist,
   use the simplest location consistent with the
   current repository structure.

3. Do not create a new directory merely because it
   is common in other projects.

4. If a new directory is genuinely necessary,
   explain why in reasoning.

------------------------------------------------------------

RULE 25 — DO NOT GUESS
------------------------------------------------------------

If the repository does not contain enough
information to determine something:

DO NOT guess.

Explicitly mention the limitation in reasoning.

The repository structure and source code should
determine the implementation wherever possible.

============================================================
STYLING ANALYSIS
============================================================

When the ticket involves UI, explicitly analyze
the existing styling system.

Return:

- CSS files that should be followed
- CSS variables that should be reused
- existing classes that may be reusable
- existing typography approach
- existing color approach
- existing spacing approach
- existing responsive approach

Do not invent these values.

Derive them from the repository.

============================================================
FILE CLASSIFICATION
============================================================

Classify files carefully.

existing_relevant_files:
Files that are useful for understanding the
implementation, even if they do not need changes.

files_to_modify:
ONLY existing files that actually require code
changes.

new_files:
ONLY files that do not currently exist and must
be created.

Examples:

If src/App.tsx already exists and must change:

files_to_modify:
[
    "src/App.tsx"
]

If src/LoginPage.tsx does not exist:

new_files:
[
    "src/LoginPage.tsx"
]

If src/LoginPage.css also does not exist and
the implementation requires it:

new_files:
[
    "src/LoginPage.tsx",
    "src/LoginPage.css"
]

Do NOT mention a new file only inside
implementation_plan.

It MUST also appear in new_files.

============================================================
IMPLEMENTATION PLAN FORMAT
============================================================

Each implementation step MUST use this structure:

{{
    "step": 1,
    "action": "modify",
    "file": "src/App.tsx",
    "description": "Describe exactly what needs to change."
}}

For creating a new file:

{{
    "step": 2,
    "action": "create",
    "file": "src/LoginPage.tsx",
    "description": "Describe exactly what needs to be implemented."
}}

For CSS:

{{
    "step": 3,
    "action": "create",
    "file": "src/LoginPage.css",
    "description": "Create component styling by reusing the existing project's CSS variables, colors, typography, spacing and responsive patterns."
}}

Use only these actions where appropriate:

- create
- modify
- update
- change

Do NOT include steps for verifying, testing,
reviewing, or validating the implementation.
Verification and testing are handled by separate
agents later in the pipeline. implementation_plan
must contain ONLY file create/modify steps.

Every implementation-plan file MUST appear in either:

new_files

OR:

files_to_modify

============================================================
OUTPUT FORMAT
============================================================

Return ONLY valid JSON.

Do not return Markdown.

Do not wrap the JSON inside:

```json

or:
Return exactly this structure:

{{
"project_architecture": {{
"framework": "",
"language": "",
"build_tool": "",
"component_structure": "",
"styling_approach": "",
"routing_approach": "",
"state_management": ""
}},
"styling_guidelines": {{
    "css_files_to_follow": [],
    "css_variables_to_reuse": [],
    "existing_classes_to_reuse": [],
    "color_approach": "",
    "typography_approach": "",
    "spacing_approach": "",
    "responsive_approach": ""
}},

"existing_relevant_files": [],

"files_to_modify": [],

"new_files": [],

"implementation_plan": [],

"dependencies": [],

"reasoning": ""
}}
============================================================
FINAL VALIDATION BEFORE RESPONSE

Before returning the JSON, verify all of the following.

Every new file in implementation_plan exists
in new_files.
Every modified file in implementation_plan
exists in files_to_modify.
No unnecessary files are listed.
package.json and package-lock.json are not listed
unless dependencies actually change.
New folders follow the existing repository
structure.
New components follow existing component
patterns.
New CSS follows existing CSS technology.
Existing CSS variables are reused where
appropriate.
Existing styles/classes are reused where
appropriate.
No arbitrary design system has been invented.
No unnecessary hooks/types/services/utilities
have been introduced.
The plan can be directly understood and
implemented by a Coding Agent.
Every file with action "create" is present
in new_files.
Every file with action "modify", "update", or
"change" is present in files_to_modify.
No file appears in both new_files and
files_to_modify.
A file that already exists in the repository
MUST NOT be placed in new_files.
A file that does not exist in the repository
MUST NOT be placed in files_to_modify.
If a new CSS file is required, it MUST appear
in new_files.
If no dependency is required, dependencies
MUST be [].
Do not invent CSS values that are not supported
by the repository evidence.

Return ONLY the JSON object.
"""
    # =========================================================
    # Call LLM
    # =========================================================

    response = llm.invoke(prompt)

    content = response.content

    # Gemini may sometimes return content as a list.
    if isinstance(content, list):
        content = "".join(
            item.get("text", "")
            for item in content
            if isinstance(item, dict)
        )

    # Make sure content is a string.
    content = str(content).strip()

    # =========================================================
    # Remove accidental Markdown JSON fences
    # =========================================================

    if content.startswith("```"):
        content = content.strip("`")
        content = content.removeprefix("json")
        content = content.strip()

    # =========================================================
    # Parse JSON
    # =========================================================

    try:
        plan = json.loads(content)

    except json.JSONDecodeError as error:

        print(
            "\n===== INVALID PLANNING AGENT RESPONSE ====="
        )

        print(content)

        print(
            "============================================\n"
        )

        raise ValueError(
            "Planning Agent returned invalid JSON."
        ) from error

    # =========================================================
    # Validate top-level response structure
    # =========================================================

    required_keys = {
        "project_architecture",
        "styling_guidelines",
        "existing_relevant_files",
        "files_to_modify",
        "new_files",
        "implementation_plan",
        "dependencies",
        "reasoning",
    }

    missing_keys = (
        required_keys
        - set(plan.keys())
    )

    if missing_keys:
        raise ValueError(
            "Planning Agent response is missing "
            f"required fields: {sorted(missing_keys)}"
        )

    # =========================================================
    # Validate response field types
    # =========================================================

    if not isinstance(
        plan["project_architecture"],
        dict,
    ):
        raise ValueError(
            "project_architecture must be an object."
        )

    if not isinstance(
        plan["styling_guidelines"],
        dict,
    ):
        raise ValueError(
            "styling_guidelines must be an object."
        )

    if not isinstance(
        plan["existing_relevant_files"],
        list,
    ):
        raise ValueError(
            "existing_relevant_files must be an array."
        )

    if not isinstance(
        plan["files_to_modify"],
        list,
    ):
        raise ValueError(
            "files_to_modify must be an array."
        )

    if not isinstance(
        plan["new_files"],
        list,
    ):
        raise ValueError(
            "new_files must be an array."
        )

    if not isinstance(
        plan["implementation_plan"],
        list,
    ):
        raise ValueError(
            "implementation_plan must be an array."
        )

    if not isinstance(
        plan["dependencies"],
        list,
    ):
        raise ValueError(
            "dependencies must be an array."
        )

    if not isinstance(
        plan["reasoning"],
        str,
    ):
        raise ValueError(
            "reasoning must be a string."
        )

    # =========================================================
    # Normalize file paths
    # =========================================================

    def normalize_path(path: str) -> str:
        return path.replace("\\", "/").strip()

    new_files = {
        normalize_path(path)
        for path in plan["new_files"]
    }

    files_to_modify = {
        normalize_path(path)
        for path in plan["files_to_modify"]
    }

    existing_relevant_files = {
        normalize_path(path)
        for path in plan["existing_relevant_files"]
    }

    # =========================================================
    # Validate duplicate classification
    # =========================================================

    overlap = (
        new_files
        & files_to_modify
    )

    if overlap:
        raise ValueError(
            "Planning Agent inconsistency: "
            "the following files appear in both "
            f"new_files and files_to_modify: "
            f"{sorted(overlap)}"
        )

    # =========================================================
    # Validate implementation plan
    # =========================================================

    filtered_implementation_plan = []

    for index, step in enumerate(
        plan["implementation_plan"],
        start=1,
    ):

        if not isinstance(step, dict):
            raise ValueError(
                "Implementation plan step "
                f"{index} must be an object."
            )

        step_action = str(
            step.get(
                "action",
                "",
            )
        ).lower().strip()

        if step_action in {
            "verify",
            "validate",
            "test",
            "review",
        }:
            # Verification/testing is handled by
            # dedicated downstream agents, not the
            # Coding Agent. Drop non-compliant steps
            # instead of failing the whole run.
            continue

        filtered_implementation_plan.append(step)

    plan["implementation_plan"] = (
        filtered_implementation_plan
    )

    for index, step in enumerate(
        plan["implementation_plan"],
        start=1,
    ):

        action = str(
            step.get(
                "action",
                "",
            )
        ).lower().strip()

        file_path = normalize_path(
            str(
                step.get(
                    "file",
                    "",
                )
            )
        )

        description = step.get(
            "description",
            "",
        )

        if not action:
            raise ValueError(
                "Implementation plan step "
                f"{index} is missing action."
            )

        if not file_path:
            raise ValueError(
                "Implementation plan step "
                f"{index} is missing file."
            )

        if not isinstance(
            description,
            str,
        ):
            raise ValueError(
                "Implementation plan step "
                f"{index} description must be a string."
            )

        # -----------------------------------------------------
        # Create validation
        # -----------------------------------------------------

        if action in {
            "create",
            "add",
            "new",
        }:

            if file_path not in new_files:
                raise ValueError(
                    "Planning Agent inconsistency: "
                    f"{file_path} is marked as '{action}' "
                    "in implementation_plan but is missing "
                    "from new_files."
                )

            if file_path in files_to_modify:
                raise ValueError(
                    "Planning Agent inconsistency: "
                    f"{file_path} is marked as both new "
                    "and modified."
                )

        # -----------------------------------------------------
        # Modify validation
        # -----------------------------------------------------

        elif action in {
            "modify",
            "update",
            "change",
        }:

            if file_path not in files_to_modify:
                raise ValueError(
                    "Planning Agent inconsistency: "
                    f"{file_path} is marked as '{action}' "
                    "in implementation_plan but is missing "
                    "from files_to_modify."
                )

            if file_path in new_files:
                raise ValueError(
                    "Planning Agent inconsistency: "
                    f"{file_path} is marked as both modified "
                    "and new."
                )

        else:
            raise ValueError(
                "Planning Agent returned unsupported "
                f"action '{action}' for file "
                f"'{file_path}'. "
                "Allowed actions are: create, modify, "
                "update, change."
            )

    # =========================================================
    # Validate files_to_modify are existing files
    # =========================================================

    repository_files = {
        normalize_path(path)
        for path in repository_structure
    }

    for file_path in files_to_modify:

        if file_path not in repository_files:
            raise ValueError(
                "Planning Agent inconsistency: "
                f"{file_path} is listed in "
                "files_to_modify but does not exist "
                "in the repository structure."
            )

    # =========================================================
    # Validate new files do not already exist
    # =========================================================

    existing_new_files = (
        new_files
        & repository_files
    )

    if existing_new_files:
        raise ValueError(
            "Planning Agent inconsistency: "
            "the following files are listed as new "
            "but already exist in the repository: "
            f"{sorted(existing_new_files)}"
        )

    # =========================================================
    # Validate relevant files exist
    # =========================================================

    invalid_relevant_files = (
        existing_relevant_files
        - repository_files
    )

    if invalid_relevant_files:
        raise ValueError(
            "Planning Agent inconsistency: "
            "the following files are listed as "
            "existing_relevant_files but do not exist "
            "in the repository structure: "
            f"{sorted(invalid_relevant_files)}"
        )

    # =========================================================
    # Validate CSS files in styling guidelines
    # =========================================================

    styling_guidelines = plan[
        "styling_guidelines"
    ]

    css_files_to_follow = styling_guidelines.get(
        "css_files_to_follow",
        [],
    )

    if not isinstance(
        css_files_to_follow,
        list,
    ):
        raise ValueError(
            "styling_guidelines.css_files_to_follow "
            "must be an array."
        )

    invalid_css_files = []

    for css_file in css_files_to_follow:

        normalized_css_file = normalize_path(
            str(css_file)
        )

        if normalized_css_file not in repository_files:
            invalid_css_files.append(
                normalized_css_file
            )

    if invalid_css_files:
        raise ValueError(
            "Planning Agent inconsistency: "
            "the following CSS files in "
            "css_files_to_follow do not exist "
            "in the repository: "
            f"{sorted(invalid_css_files)}"
        )

    # =========================================================
    # Validate newly created stylesheet references
    # =========================================================

    for new_file in new_files:

        lower_file = new_file.lower()

        is_stylesheet = lower_file.endswith(
            (
                ".css",
                ".scss",
                ".sass",
                ".less",
            )
        )

        if not is_stylesheet:
            continue

        # If a new stylesheet is listed, make sure
        # it appears in the implementation plan.

        plan_references_file = any(
            normalize_path(
                str(
                    step.get(
                        "file",
                        "",
                    )
                )
            )
            == new_file
            for step in plan[
                "implementation_plan"
            ]
            if isinstance(step, dict)
        )

        if not plan_references_file:
            raise ValueError(
                "Planning Agent inconsistency: "
                f"new stylesheet {new_file} is listed "
                "in new_files but is missing from "
                "implementation_plan."
            )

    # =========================================================
    # Normalize paths in final response
    # =========================================================

    plan["existing_relevant_files"] = [
        normalize_path(path)
        for path in plan[
            "existing_relevant_files"
        ]
    ]

    plan["files_to_modify"] = [
        normalize_path(path)
        for path in plan[
            "files_to_modify"
        ]
    ]

    plan["new_files"] = [
        normalize_path(path)
        for path in plan[
            "new_files"
        ]
    ]

    # =========================================================
    # Final validation passed
    # =========================================================

    print(
        "\n===== IMPLEMENTATION PLAN VALIDATED ====="
    )

    print(
        f"Existing relevant files: "
        f"{len(plan['existing_relevant_files'])}"
    )

    print(
        f"Files to modify: "
        f"{len(plan['files_to_modify'])}"
    )

    print(
        f"New files: "
        f"{len(plan['new_files'])}"
    )

    print(
        f"Implementation steps: "
        f"{len(plan['implementation_plan'])}"
    )

    print(
        "=========================================\n"
    )

    return plan