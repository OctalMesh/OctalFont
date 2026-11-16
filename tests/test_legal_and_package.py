from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from octalfont.check import check_legal
from octalfont.config import load_config
from octalfont.package import make_archive

FONT_YAML = """family: Demo Font
version: "1.002"
copyright_year: 2025
repository: https://github.com/Example/demo
vendor_id: DEMO
designer: Someone
"""
COPYRIGHT = "Copyright 2025 The Demo Font Project Authors (https://github.com/Example/demo)"


@pytest.fixture
def font_repo(tmp_path: Path) -> Path:
    (tmp_path / "sources").mkdir()
    (tmp_path / "sources/font.yaml").write_text(FONT_YAML)
    (tmp_path / "OFL.txt").write_text(f"{COPYRIGHT}\n\nPREAMBLE\n...\n")
    (tmp_path / "AUTHORS.txt").write_text("Someone <someone@example.com>\n")
    (tmp_path / "requirements.txt").write_text("octalfont\n")

    return tmp_path


def levels(root: Path) -> dict[str, str]:
    return {f.message: f.level for f in check_legal(load_config(root))}


def test_contributors_file_is_not_required(font_repo):
    assert not (font_repo / "CONTRIBUTORS.txt").exists()

    result = check_legal(load_config(font_repo))

    assert [f.level for f in result] == ["PASS"]


def test_empty_contributors_file_is_flagged_but_not_failed(font_repo):
    (font_repo / "CONTRIBUTORS.txt").write_text("# Contributors. Format: Name <email>\n")

    result = check_legal(load_config(font_repo))

    assert [f.level for f in result] == ["WARN"]


def test_contributors_with_entries_pass(font_repo):
    (font_repo / "CONTRIBUTORS.txt").write_text("# Contributors\nOlha Example <olha@example.com>\n")

    assert [f.level for f in check_legal(load_config(font_repo))] == ["PASS"]


def test_authors_still_required(font_repo):
    (font_repo / "AUTHORS.txt").unlink()

    assert any(f.level == "WARN" and "AUTHORS.txt" in f.message for f in check_legal(load_config(font_repo)))


def test_archive_is_deterministic_and_skips_missing_contributors(font_repo, monkeypatch):
    (font_repo / "README.md").write_text("# Demo\n")
    (font_repo / "fonts/ttf").mkdir(parents=True)
    (font_repo / "fonts/ttf/DemoFont-Regular.ttf").write_bytes(b"ttf-bytes")
    (font_repo / "fonts/variable").mkdir()
    (font_repo / "fonts/variable/DemoFont[wght].ttf").write_bytes(b"vf-bytes")
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1700000000")

    cfg = load_config(font_repo)
    first = make_archive(cfg, font_repo / "dist").read_bytes()
    second = make_archive(cfg, font_repo / "dist").read_bytes()

    assert first == second

    with zipfile.ZipFile(font_repo / "dist/DemoFont-v1.002.zip") as zf:
        names = zf.namelist()
    assert names == [
        "DemoFont-v1.002/fonts/ttf/DemoFont-Regular.ttf",
        "DemoFont-v1.002/fonts/variable/DemoFont[wght].ttf",
        "DemoFont-v1.002/OFL.txt",
        "DemoFont-v1.002/AUTHORS.txt",
        "DemoFont-v1.002/README.md",
    ]


def test_archive_requires_built_fonts(font_repo):
    with pytest.raises(FileNotFoundError):
        make_archive(load_config(font_repo), font_repo / "dist")
