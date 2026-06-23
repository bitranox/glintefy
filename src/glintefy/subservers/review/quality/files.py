"""File management for quality analysis."""

from pathlib import Path


class FileManager:
    """Manages file loading and validation for quality analysis."""

    def __init__(self, input_dir: Path, repo_path: Path):
        """Initialize file manager.

        Args:
            input_dir: Directory containing files_to_review.txt or files_code.txt
            repo_path: Repository root path for resolving relative paths
        """
        self.input_dir = input_dir
        self.repo_path = repo_path

    def validate_inputs(self) -> tuple[bool, list[str]]:
        """Validate that required input files exist.

        Returns:
            Tuple of (is_valid, list_of_missing_items)
        """
        missing = []
        files_list = self.input_dir / "files_to_review.txt"
        if not files_list.exists():
            files_list = self.input_dir / "files_code.txt"
            if not files_list.exists():
                missing.append(f"No files list found in {self.input_dir}. Run scope sub-server first.")
        return len(missing) == 0, missing

    def load_python_files(self) -> list[str]:
        """Load Python files from input directory.

        Returns:
            List of absolute paths to Python files
        """
        files_list = self.input_dir / "files_code.txt"
        if not files_list.exists():
            files_list = self.input_dir / "files_to_review.txt"
        if not files_list.exists():
            return []

        all_files = files_list.read_text().strip().split("\n")
        python_files = [f for f in all_files if f.endswith(".py") and f]
        return [str(self.repo_path / f) for f in python_files]

    def load_js_files(self) -> list[str]:
        """Load JavaScript/TypeScript files from input directory.

        Returns:
            List of absolute paths to JS/TS files
        """
        files_list = self.input_dir / "files_to_review.txt"
        if not files_list.exists():
            return []

        all_files = files_list.read_text().strip().split("\n")
        js_extensions = (".js", ".jsx", ".ts", ".tsx")
        js_files = [f for f in all_files if f.endswith(js_extensions) and f]
        return [str(self.repo_path / f) for f in js_files]
