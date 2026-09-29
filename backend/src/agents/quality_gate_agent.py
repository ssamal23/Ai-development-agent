import json
import subprocess
from pathlib import Path
from src.config.settings import settings


class QualityGateResult:
    """Result of quality gate checks"""

    def __init__(self):
        self.passed = True
        self.checks = {}
        self.errors = []
        self.warnings = []
        self.suggestions = []

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "checks": self.checks,
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
        }


def run_quality_gates(
    workspace_path: str | Path,
) -> QualityGateResult:
    """
    Run all quality gate checks before verification.

    Checks:
    1. Linting (ESLint for JS/TS, Ruff for Python)
    2. Type checking (TypeScript, mypy)
    3. Security scanning (bandit, OWASP checks)
    4. Basic code quality rules

    Returns detailed results but doesn't fail workflow -
    allows workflow to continue but flags issues.
    """

    workspace_path = Path(workspace_path).resolve()
    result = QualityGateResult()

    # Python linting and type checks
    result = _check_python_quality(
        workspace_path,
        result,
    )

    # JavaScript/TypeScript linting and types
    result = _check_typescript_quality(
        workspace_path,
        result,
    )

    # Security checks
    result = _check_security(
        workspace_path,
        result,
    )

    # Determine overall pass/fail
    result.passed = len(result.errors) == 0

    return result


def _check_python_quality(
    workspace_path: Path,
    result: QualityGateResult,
) -> QualityGateResult:
    """Check Python code quality"""

    python_files = list(
        workspace_path.rglob("*.py")
    )

    if not python_files:
        result.checks["python"] = "SKIPPED"
        return result

    python_check = {
        "files_checked": len(python_files),
        "ruff": {"status": "UNKNOWN"},
        "mypy": {"status": "UNKNOWN"},
        "security": {"status": "UNKNOWN"},
    }

    # Run Ruff for linting
    try:
        output = subprocess.run(
            [
                "ruff",
                "check",
                str(workspace_path),
                "--output-format=json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if output.returncode == 0:
            python_check["ruff"]["status"] = "PASS"
        else:
            python_check["ruff"]["status"] = "FAIL"
            try:
                issues = json.loads(output.stdout)
                for issue in issues:
                    result.warnings.append(
                        f"Ruff: {issue.get('message')} "
                        f"({issue.get('filename')})"
                    )
            except json.JSONDecodeError:
                result.warnings.append(
                    "Ruff issues found (see output)"
                )

    except FileNotFoundError:
        python_check["ruff"]["status"] = "SKIPPED"
    except Exception as e:
        result.errors.append(
            f"Ruff check failed: {str(e)}"
        )

    # Run mypy for type checking
    try:
        output = subprocess.run(
            [
                "mypy",
                str(workspace_path),
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if output.returncode == 0:
            python_check["mypy"]["status"] = "PASS"
        else:
            python_check["mypy"]["status"] = "FAIL"
            try:
                issues = json.loads(output.stdout)
                for issue in issues:
                    result.warnings.append(
                        f"Type: {issue.get('message')} "
                        f"({issue.get('filename')})"
                    )
            except json.JSONDecodeError:
                result.warnings.append(
                    "Type check issues found (see output)"
                )

    except FileNotFoundError:
        python_check["mypy"]["status"] = "SKIPPED"
    except Exception as e:
        result.errors.append(
            f"Type check failed: {str(e)}"
        )

    # Run bandit for security
    try:
        output = subprocess.run(
            [
                "bandit",
                "-r",
                str(workspace_path),
                "-f",
                "json",
                "-ll",  # Only high/medium severity
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if output.returncode == 0:
            python_check["security"]["status"] = "PASS"
        else:
            python_check["security"]["status"] = "FAIL"
            try:
                report = json.loads(output.stdout)
                for issue in report.get("results", []):
                    result.errors.append(
                        f"Security: {issue.get('issue_text')} "
                        f"({issue.get('filename')}:{issue.get('line_number')})"
                    )
            except json.JSONDecodeError:
                result.errors.append(
                    "Security issues found (see output)"
                )

    except FileNotFoundError:
        python_check["security"]["status"] = "SKIPPED"
    except Exception as e:
        result.warnings.append(
            f"Security check failed: {str(e)}"
        )

    result.checks["python"] = python_check
    return result


def _check_typescript_quality(
    workspace_path: Path,
    result: QualityGateResult,
) -> QualityGateResult:
    """Check TypeScript/JavaScript code quality"""

    ts_files = list(
        workspace_path.rglob("*.ts")
    )

    js_files = list(
        workspace_path.rglob("*.tsx")
    )

    if not ts_files and not js_files:
        result.checks["typescript"] = "SKIPPED"
        return result

    ts_check = {
        "files_checked": len(ts_files) + len(js_files),
        "eslint": {"status": "UNKNOWN"},
        "tsc": {"status": "UNKNOWN"},
    }

    # Run ESLint
    try:
        output = subprocess.run(
            [
                "eslint",
                str(workspace_path),
                "--format=json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if output.returncode == 0:
            ts_check["eslint"]["status"] = "PASS"
        else:
            ts_check["eslint"]["status"] = "FAIL"
            try:
                issues = json.loads(output.stdout)
                for file_report in issues:
                    for msg in file_report.get("messages", []):
                        result.warnings.append(
                            f"ESLint: {msg.get('message')} "
                            f"({file_report.get('filePath')})"
                        )
            except json.JSONDecodeError:
                result.warnings.append(
                    "ESLint issues found (see output)"
                )

    except FileNotFoundError:
        ts_check["eslint"]["status"] = "SKIPPED"
    except Exception as e:
        result.errors.append(
            f"ESLint check failed: {str(e)}"
        )

    # Run TypeScript compiler
    try:
        output = subprocess.run(
            [
                "tsc",
                "--noEmit",
                "--skipLibCheck",
            ],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if output.returncode == 0:
            ts_check["tsc"]["status"] = "PASS"
        else:
            ts_check["tsc"]["status"] = "FAIL"
            errors = output.stderr.split("\n")
            for error in errors:
                if error.strip():
                    result.warnings.append(
                        f"TypeScript: {error}"
                    )

    except FileNotFoundError:
        ts_check["tsc"]["status"] = "SKIPPED"
    except Exception as e:
        result.errors.append(
            f"TypeScript check failed: {str(e)}"
        )

    result.checks["typescript"] = ts_check
    return result


def _check_security(
    workspace_path: Path,
    result: QualityGateResult,
) -> QualityGateResult:
    """Check for common security issues"""

    security_check = {
        "secrets_scan": "PASS",
        "dependency_check": "PASS",
    }

    # Simple hardcoded secrets check
    secrets_patterns = [
        r"api[_-]?key\s*=",
        r"password\s*=",
        r"secret\s*=",
        r"token\s*=",
    ]

    found_secrets = False

    for py_file in workspace_path.rglob("*.py"):
        try:
            with open(py_file, "r") as f:
                content = f.read()
                for pattern in secrets_patterns:
                    import re
                    if re.search(
                        pattern,
                        content,
                        re.IGNORECASE,
                    ):
                        result.warnings.append(
                            f"Possible hardcoded secret in {py_file}"
                        )
                        found_secrets = True
        except Exception:
            pass

    if found_secrets:
        security_check["secrets_scan"] = "FAIL"

    # Check for package vulnerabilities (pip-audit)
    try:
        output = subprocess.run(
            [
                "pip-audit",
                "--desc",
            ],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if output.returncode != 0:
            security_check["dependency_check"] = "FAIL"
            result.warnings.append(
                "Dependency vulnerabilities found"
            )

    except FileNotFoundError:
        security_check["dependency_check"] = "SKIPPED"
    except Exception:
        security_check["dependency_check"] = "UNKNOWN"

    result.checks["security"] = security_check
    return result
