from pathlib import Path


class CodeEditService:

    def __init__(
        self,
        repository_path: str | Path,
    ):
        self.repository_path = Path(
            repository_path
        ).resolve()

    def apply_changes(
        self,
        changes,
    ) -> list[str]:

        changed_files = []

        for change in changes:

            file_path = (
                self.repository_path
                / change.file
            ).resolve()

            self._validate_path(
                file_path
            )

            if change.action == "create":

                self._create_file(
                    file_path,
                    change.content,
                )

            elif change.action == "modify":

                self._modify_file(
                    file_path,
                    change.content,
                )

            elif change.action == "delete":

                self._delete_file(
                    file_path
                )

            else:

                raise ValueError(
                    f"Unsupported code change action: "
                    f"{change.action}"
                )

            changed_files.append(
                change.file
            )

        return changed_files

    def _create_file(
        self,
        file_path: Path,
        content: str | None,
    ) -> None:

        if file_path.exists():
            raise FileExistsError(
                f"File already exists: "
                f"{file_path}"
            )

        if content is None:
            raise ValueError(
                "Content is required when "
                "creating a file."
            )

        file_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        file_path.write_text(
            content,
            encoding="utf-8",
        )

    def _modify_file(
        self,
        file_path: Path,
        content: str | None,
    ) -> None:

        if not file_path.exists():
            raise FileNotFoundError(
                f"File does not exist: "
                f"{file_path}"
            )

        if content is None:
            raise ValueError(
                "Content is required when "
                "modifying a file."
            )

        file_path.write_text(
            content,
            encoding="utf-8",
        )

    def _delete_file(
        self,
        file_path: Path,
    ) -> None:

        if not file_path.exists():
            raise FileNotFoundError(
                f"File does not exist: "
                f"{file_path}"
            )

        file_path.unlink()

    def _validate_path(
        self,
        file_path: Path,
    ) -> None:

        if not file_path.is_relative_to(
            self.repository_path
        ):
            raise ValueError(
                "Invalid file path."
            )