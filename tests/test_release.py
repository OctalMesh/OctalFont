from __future__ import annotations

import pytest

from conftest import FONT_CONFIG, FONT_YAML, PYPROJECT, TOOL_CONFIG, commit_all, git
from octalfont import release as r
from octalfont.cli import main


def tool_repo(git_repo, version="0.0.0", extra=None):
    files = {"pyproject.toml": PYPROJECT.format(v=version), ".changeset/config.json": TOOL_CONFIG,
             ".changeset/README.md": "# Changesets\n", "src/demo.py": "x = 1\n"}

    files.update(extra or {})

    return git_repo(files)


def cs(bump: str | None, summary: str = "Did a thing.", name: str = "demo") -> str:
    if bump is None:
        return "---\n---\n"

    return f'---\n"{name}": {bump}\n---\n\n{summary}\n'


# versioning


@pytest.mark.parametrize("current,bump,expected", [
    ("0.0.0", "minor", "0.1.0"), ("0.1.4", "patch", "0.1.5"), ("0.1.4", "minor", "0.2.0"),
    ("0.1.4", "major", "1.0.0"), ("1.9.9", "major", "2.0.0"),
])
def test_semver_bumps(current, bump, expected):
    assert r.bump_version(current, bump, "semver") == expected


@pytest.mark.parametrize("current,bump,expected", [
    ("0.000", "major", "1.000"), ("1.000", "minor", "1.001"), ("1.009", "patch", "1.010"),
    ("1.999", "major", "2.000"), ("1.012", "major", "2.000"),
])
def test_font_bumps(current, bump, expected):
    assert r.bump_version(current, bump, "font") == expected


def test_font_minor_exhausted():
    with pytest.raises(r.ReleaseError):
        r.bump_version("1.999", "minor", "font")


@pytest.mark.parametrize("text,scheme", [("1.0", "semver"), ("1.2.3", "font"), ("1.1", "font"), ("v1.0.0", "semver")])
def test_bad_versions_rejected(text, scheme):
    with pytest.raises(r.ReleaseError):
        r.parse_version(text, scheme)


def test_version_ordering_is_numeric_not_alphabetic():
    assert r.parse_version("0.10.0", "semver") > r.parse_version("0.9.0", "semver")
    assert r.parse_version("1.010", "font") > r.parse_version("1.009", "font")


def test_write_version_touches_only_project_table(tmp_path):
    (tmp_path / ".changeset").mkdir()
    (tmp_path / ".changeset/config.json").write_text(TOOL_CONFIG)
    (tmp_path / "pyproject.toml").write_text(PYPROJECT.format(v="0.0.0"))

    cfg = r.Config.load(tmp_path)

    r.write_version(tmp_path, cfg, "0.1.0")

    text = (tmp_path / "pyproject.toml").read_text()

    assert 'name = "demo"\nversion = "0.1.0"' in text
    assert '[tool.other]\nversion = "9.9.9"' in text


def test_write_version_in_font_yaml_keeps_comments_and_quotes(tmp_path):
    (tmp_path / ".changeset").mkdir()
    (tmp_path / ".changeset/config.json").write_text(FONT_CONFIG)
    (tmp_path / "sources").mkdir()
    (tmp_path / "sources/font.yaml").write_text(FONT_YAML.format(v="1.000"))

    cfg = r.Config.load(tmp_path)

    r.write_version(tmp_path, cfg, "1.001")

    assert (tmp_path / "sources/font.yaml").read_text() == FONT_YAML.format(v="1.001")
    assert r.read_version(tmp_path, cfg) == "1.001"


# changesets


def test_parse_changeset_variants(tmp_path):
    (tmp_path / ".changeset").mkdir()
    (tmp_path / ".changeset/config.json").write_text(TOOL_CONFIG)

    cfg = r.Config.load(tmp_path)
    p = tmp_path / ".changeset/a.md"

    p.write_text(cs("minor", "Line one.\n\nLine two."))

    parsed = r.parse_changeset(p, cfg)

    assert (parsed.bump, parsed.summary) == ("minor", "Line one.\n\nLine two.")

    p.write_text(cs(None))

    assert r.parse_changeset(p, cfg).empty

    p.write_text(cs("huge"))
    with pytest.raises(r.ReleaseError):
        r.parse_changeset(p, cfg)

    p.write_text(cs("minor", name="other"))
    with pytest.raises(r.ReleaseError):
        r.parse_changeset(p, cfg)

    p.write_text(cs("minor", summary=""))
    with pytest.raises(r.ReleaseError):
        r.parse_changeset(p, cfg)

    p.write_text("no front matter\n")
    with pytest.raises(r.ReleaseError):
        r.parse_changeset(p, cfg)


def test_changesets_compatible_with_js_changesets_format(tmp_path):
    """Files written by @changesets/cli (single quotes allowed) must parse too."""

    (tmp_path / ".changeset").mkdir()
    (tmp_path / ".changeset/config.json").write_text(TOOL_CONFIG)

    cfg = r.Config.load(tmp_path)
    p = tmp_path / ".changeset/b.md"

    p.write_text("---\n'demo': patch\n---\n\nFix.\n")

    assert r.parse_changeset(p, cfg).bump == "patch"


# apply version


def test_apply_version_consumes_changesets_and_writes_changelog(git_repo):
    root = tool_repo(git_repo, extra={
        ".changeset/a.md": cs("patch", "Fix a bug."),
        ".changeset/b.md": cs("minor", "Add a feature.\nSecond line."),
        ".changeset/c.md": cs(None),
    })
    cfg = r.Config.load(root)

    assert r.next_version(root, cfg) == "0.1.0"
    assert r.apply_version(root, cfg) == "0.1.0"
    assert r.read_version(root, cfg) == "0.1.0"
    assert sorted(p.name for p in (root / ".changeset").iterdir()) == ["README.md", "config.json"]

    log = (root / "CHANGELOG.md").read_text()

    assert log.startswith("# demo\n\n## 0.1.0\n\n### Minor Changes\n")
    assert "Add a feature.\n  Second line." in log
    assert "### Patch Changes" in log and "Fix a bug." in log
    assert log.index("Minor Changes") < log.index("Patch Changes")


def test_second_release_is_prepended(git_repo):
    root = tool_repo(git_repo, extra={".changeset/a.md": cs("minor", "First.")})
    cfg = r.Config.load(root)

    r.apply_version(root, cfg)
    (root / ".changeset/z.md").write_text(cs("patch", "Second."))

    assert r.apply_version(root, cfg) == "0.1.1"

    log = (root / "CHANGELOG.md").read_text()

    assert log.index("## 0.1.1") < log.index("## 0.1.0")
    assert r.changelog_section(log, "0.1.0").startswith("### Minor Changes")
    assert "Second." not in r.changelog_section(log, "0.1.0")


def test_apply_version_without_releasable_changeset_fails(git_repo):
    root = tool_repo(git_repo, extra={".changeset/e.md": cs(None)})
    cfg = r.Config.load(root)

    assert r.next_version(root, cfg) is None
    with pytest.raises(r.ReleaseError):
        r.apply_version(root, cfg)


def test_dry_run_changes_nothing(git_repo):
    root = tool_repo(git_repo, extra={".changeset/a.md": cs("major", "Break.")})
    cfg = r.Config.load(root)

    assert r.apply_version(root, cfg, dry_run=True) == "1.0.0"
    assert r.read_version(root, cfg) == "0.0.0"
    assert (root / ".changeset/a.md").exists() and not (root / "CHANGELOG.md").exists()


def test_font_scheme_end_to_end(git_repo):
    root = git_repo({"sources/font.yaml": FONT_YAML.format(v="0.000"), ".changeset/config.json": FONT_CONFIG,
                     ".changeset/first.md": '---\n"demo-font": major\n---\n\nFirst public release.\n'})
    cfg = r.Config.load(root)

    assert r.apply_version(root, cfg) == "1.000"

    (root / ".changeset/fix.md").write_text('---\n"demo-font": patch\n---\n\nTweak spacing.\n')

    assert r.apply_version(root, cfg) == "1.001"
    assert "### Minor Changes" in (root / "CHANGELOG.md").read_text()  # patch is filed under Minor


def test_changelog_records_the_commit_that_added_the_changeset(git_repo):
    root = tool_repo(git_repo)
    (root / ".changeset/a.md").write_text(cs("minor", "Add a feature."))
    commit_all(root, "add changeset")
    short = git(root, "rev-parse", "--short", "HEAD").strip()
    r.apply_version(root, r.Config.load(root))
    assert f"- {short[:5]}" in (root / "CHANGELOG.md").read_text()


# gates


def release_flow(git_repo):
    """dev with a consumed release commit on top of a `release` baseline."""

    root = tool_repo(git_repo, extra={".changeset/a.md": cs("minor", "Initial release.")})

    git(root, "branch", "release")

    return root


def test_verify_passes_after_version(git_repo):
    root = release_flow(git_repo)
    cfg = r.Config.load(root)

    r.apply_version(root, cfg)
    commit_all(root, "version")

    assert r.verify(root, cfg, "release") == []
    assert main(["-C", str(root), "release", "verify", "--base", "release"]) == 0


def test_verify_fails_when_version_did_not_move(git_repo, capsys):
    root = release_flow(git_repo)
    cfg = r.Config.load(root)
    problems = r.verify(root, cfg, "release")

    assert any("not greater" in p for p in problems)
    assert any("no '## 0.0.0' section" in p for p in problems)
    assert any("unconsumed" in p for p in problems)
    assert main(["-C", str(root), "release", "verify", "--base", "release"]) == 1


def test_verify_reports_missing_base_branch(git_repo):
    root = tool_repo(git_repo)
    problems = r.verify(root, r.Config.load(root), "origin/release")

    assert problems and "origin/release" in problems[0]


def test_check_pr_requires_changeset_for_relevant_files(git_repo):
    root = tool_repo(git_repo)
    cfg = r.Config.load(root)

    git(root, "checkout", "-q", "-b", "feature")
    (root / "docs.md").write_text("docs\n")
    commit_all(root, "docs")

    assert r.check_pr(root, cfg, "dev") is None

    (root / "src/demo.py").write_text("x = 2\n")
    commit_all(root, "code")

    assert "adds no changeset" in (r.check_pr(root, cfg, "dev") or "")

    (root / ".changeset/ok.md").write_text(cs(None))
    commit_all(root, "empty changeset")

    assert r.check_pr(root, cfg, "dev") is None


def test_previous_tag_orders_numerically(git_repo):
    root = tool_repo(git_repo)

    for tag in ("v0.9.0", "v0.10.0", "v0.2.0", "vnext", "other"):
        git(root, "tag", tag)

    cfg = r.Config.load(root)

    assert r.previous_tag(root, cfg, "0.10.1") == "v0.10.0"
    assert r.previous_tag(root, cfg, "0.10.0") == "v0.9.0"
    assert r.previous_tag(root, cfg, "0.1.0") is None


def test_cli_add_status_notes(git_repo, capsys):
    root = tool_repo(git_repo)

    assert main(["-C", str(root), "release", "add", "--bump", "minor", "-m", "Shiny.", "--name", "shiny"]) == 0
    assert (root / ".changeset/shiny.md").read_text() == '---\n"demo": minor\n---\n\nShiny.\n'
    assert main(["-C", str(root), "release", "add", "--empty", "--name", "nothing"]) == 0

    capsys.readouterr()

    assert main(["-C", str(root), "release", "status"]) == 0

    out = capsys.readouterr().out

    assert "minor" in out and "next 0.1.0" in out
    assert main(["-C", str(root), "release", "version"]) == 0

    capsys.readouterr()

    assert main(["-C", str(root), "release", "notes"]) == 0
    assert "Shiny." in capsys.readouterr().out


def test_cli_add_refuses_to_overwrite(git_repo):
    root = tool_repo(git_repo)
    args = ["-C", str(root), "release", "add", "--bump", "patch", "-m", "x", "--name", "same"]

    assert main(args) == 0
    assert main(args) == 2
