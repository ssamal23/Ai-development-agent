from pathlib import Path
import json
import subprocess

from src.config.settings import settings


class TestResult:

    def __init__(
        self,
        success: bool,
        output: str,
        command: str,
        exit_code: int | None,
    ):
        self.success = success
        self.output = output
        self.command = command
        self.exit_code = exit_code

    def model_dump(self):
        return {
            "success": self.success,
            "output": self.output,
            "command": self.command,
            "exit_code": self.exit_code,
        }


class TestAgent:

    def __init__(
        self,
        repository_path: str | Path | None = None,
    ):
        if repository_path:

            self.repository_path = Path(
                repository_path
            ).resolve()

        else:

            self.repository_path = Path(
                settings.repository_path
            ).resolve()

    def run_tests(self) -> TestResult:

        command = self._detect_test_command()

        if command is None:

            return TestResult(
                success=True,
                output=(
                    "No supported test command "
                    "was detected."
                ),
                command="",
                exit_code=None,
            )

        command_string = " ".join(
            command
        )

        try:

            result = subprocess.run(
                command,
                cwd=self.repository_path,
                capture_output=True,
                text=True,
                timeout=300,
            )

            output = self._build_output(
                result.stdout,
                result.stderr,
            )

            return TestResult(
                success=(
                    result.returncode == 0
                ),
                output=output,
                command=command_string,
                exit_code=result.returncode,
            )

        except subprocess.TimeoutExpired as error:

            output = (
                "Tests exceeded the "
                "5-minute timeout."
            )

            if error.stdout:

                output += (
                    f"\n\nSTDOUT:\n"
                    f"{error.stdout}"
                )

            if error.stderr:

                output += (
                    f"\n\nSTDERR:\n"
                    f"{error.stderr}"
                )

            return TestResult(
                success=False,
                output=output,
                command=command_string,
                exit_code=None,
            )

        except FileNotFoundError as error:

            return TestResult(
                success=False,
                output=(
                    "Test command could not "
                    f"be executed: {error}"
                ),
                command=command_string,
                exit_code=None,
            )

        except Exception as error:

            return TestResult(
                success=False,
                output=str(error),
                command=command_string,
                exit_code=None,
            )

    def _detect_test_command(
        self,
    ) -> list[str] | None:

        package_json = (
            self.repository_path
            / "package.json"
        )

        if package_json.exists():

            return self._detect_npm_test_command(
                package_json
            )

        pyproject = (
            self.repository_path
            / "pyproject.toml"
        )

        if pyproject.exists():

            return [
                "pytest"
            ]

        requirements = (
            self.repository_path
            / "requirements.txt"
        )

        if requirements.exists():

            return [
                "pytest"
            ]

        return None

    def _detect_npm_test_command(
        self,
        package_json: Path,
    ) -> list[str] | None:

        try:

            package_data = json.loads(
                package_json.read_text(
                    encoding="utf-8"
                )
            )

            scripts = package_data.get(
                "scripts",
                {}
            )

            if "test" in scripts:

                return [
                    "npm",
                    "test",
                ]

            if "test:unit" in scripts:

                return [
                    "npm",
                    "run",
                    "test:unit",
                ]

            if "test:ci" in scripts:

                return [
                    "npm",
                    "run",
                    "test:ci",
                ]

        except (
            json.JSONDecodeError,
            OSError,
        ):
            pass

        return None

    def _build_output(
        self,
        stdout: str,
        stderr: str,
    ) -> str:

        sections = []

        if stdout.strip():

            sections.append(
                f"STDOUT:\n"
                f"{stdout.strip()}"
            )

        if stderr.strip():

            sections.append(
                f"STDERR:\n"
                f"{stderr.strip()}"
            )

        if not sections:

            return (
                "Test command completed "
                "with no output."
            )

        return "\n\n".join(
            sections
        )


def run_tests(
    repository_path: str | Path | None = None,
) -> dict:

    agent = TestAgent(
        repository_path=repository_path
    )

    result = agent.run_tests()

    return result.model_dump()