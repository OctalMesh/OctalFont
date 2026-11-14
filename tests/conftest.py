from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout


@pytest.fixture
def git_repo(tmp_path: Path):
    """Factory for a throw-away git repository with a committer identity."""

    def make(files: dict[str, str]) -> Path:
        git(tmp_path, "init", "-q", "-b", "dev")
        git(tmp_path, "config", "user.name", "Test")
        git(tmp_path, "config", "user.email", "test@example.com")

        for name, text in files.items():
            path = tmp_path / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

        git(tmp_path, "add", "-A")
        git(tmp_path, "commit", "-q", "-m", "initial")

        return tmp_path

    return make


PYPROJECT = '[build-system]\nrequires = ["hatchling"]\n\n[project]\nname = "demo"\nversion = "{v}"\n\n[tool.other]\nversion = "9.9.9"\n'
TOOL_CONFIG = '{"name": "demo", "scheme": "semver", "paths": ["src/**", "pyproject.toml"]}\n'
FONT_YAML = '# comment\nfamily: Demo\nversion: "{v}"\ncopyright_year: 2025\n'
FONT_CONFIG = '{"name": "demo-font", "scheme": "font", "paths": ["sources/**"]}\n'


def commit_all(root: Path, message: str) -> None:
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)
