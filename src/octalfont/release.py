"""Changeset-style versioning and release helpers (``octalfont release ...``).

The same flow is used by this repository and by every font repository:

* a *changeset* is a small Markdown file in ``.changeset/`` that records one
  change and its bump level (``patch`` / ``minor`` / ``major``);
* ``release version`` consumes all pending changesets: it bumps the version
  file, prepends a section to ``CHANGELOG.md`` and deletes the changesets;
* ``release verify`` is the release gate: the version must have moved forward
  relative to the ``release`` branch and the changelog must describe it;
* ``release check`` tells a pull request that it needs a changeset.

Behaviour is configured by ``.changeset/config.json`` (see ``Config``). Two
version schemes exist:

``semver``  ``X.Y.Z`` in ``pyproject.toml`` (this tool).
``font``    ``MAJOR.MINOR`` with a three-digit minor, ``1.001`` in
            ``sources/font.yaml`` (Google Fonts convention). ``patch`` is an
            alias of ``minor`` because a font has no patch component.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import random
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

CHANGESET_DIR = ".changeset"
CONFIG_NAME = "config.json"
NON_CHANGESET_FILES = {"README.md", CONFIG_NAME}

BUMPS = ("patch", "minor", "major")
_RANK = {"none": 0, "patch": 1, "minor": 2, "major": 3}

SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
FONT_RE = re.compile(r"^(\d+)\.(\d{3})$")

_WORDS_A = ("brave", "calm", "clever", "cold", "eager", "fair", "gentle", "keen", "kind", "late",
            "neat", "quick", "quiet", "sharp", "silver", "smooth", "solid", "swift", "tidy", "warm")
_WORDS_B = ("badges", "comets", "fonts", "glyphs", "hinges", "kernels", "lines", "marks", "masters",
            "pens", "rivers", "serifs", "stems", "strokes", "tables", "tools", "units", "weights")
_WORDS_C = ("align", "bloom", "build", "check", "drift", "grow", "hold", "land", "learn", "move",
            "ship", "shine", "sing", "sleep", "turn", "walk", "wave")


class ReleaseError(RuntimeError):
    """A release rule was violated or a file is malformed."""


# ============================================================================ #
#                                    Config                                    #
# ============================================================================ #


@dataclass
class Config:
    name: str                                      # changelog heading and changeset key
    scheme: str = "semver"                         # "semver" | "font"
    version_file: str = "pyproject.toml"
    base_branch: str = "dev"
    release_branch: str = "release"
    tag_prefix: str = "v"
    changelog: str = "CHANGELOG.md"
    paths: list[str] = field(default_factory=list) # globs that require a changeset

    @classmethod
    def load(cls, root: Path) -> "Config":
        path = root / CHANGESET_DIR / CONFIG_NAME

        if not path.is_file():
            raise ReleaseError(f"{CHANGESET_DIR}/{CONFIG_NAME} not found in {root}")

        data = json.loads(path.read_text(encoding="utf-8"))

        if "name" not in data:
            raise ReleaseError(f"{CHANGESET_DIR}/{CONFIG_NAME}: missing required key 'name'")

        scheme = data.get("scheme", "semver")

        if scheme not in ("semver", "font"):
            raise ReleaseError(f"{CHANGESET_DIR}/{CONFIG_NAME}: scheme must be 'semver' or 'font'")

        default_file = "pyproject.toml" if scheme == "semver" else "sources/font.yaml"

        return cls(
            name=data["name"],
            scheme=scheme,
            version_file=data.get("versionFile", default_file),
            base_branch=data.get("baseBranch", "dev"),
            release_branch=data.get("releaseBranch", "release"),
            tag_prefix=data.get("tagPrefix", "v"),
            changelog=data.get("changelog", "CHANGELOG.md"),
            paths=list(data.get("paths", [])),
        )


# ============================================================================ #
#                                   Versions                                   #
# ============================================================================ #

Version = tuple[int, ...]


def parse_version(text: str, scheme: str) -> Version:
    text = text.strip()
    regex = SEMVER_RE if scheme == "semver" else FONT_RE
    m = regex.match(text)

    if not m:
        shape = "X.Y.Z" if scheme == "semver" else "MAJOR.MINOR with a three-digit minor (e.g. 1.001)"
        raise ReleaseError(f"version '{text}' must look like {shape}")

    return tuple(int(g) for g in m.groups())


def format_version(v: Version, scheme: str) -> str:
    if scheme == "semver":
        return f"{v[0]}.{v[1]}.{v[2]}"

    return f"{v[0]}.{v[1]:03d}"


def bump_version(current: str, bump: str, scheme: str) -> str:
    """Return ``current`` raised by ``bump`` (``major`` resets lower parts)."""

    v = parse_version(current, scheme)

    if bump not in BUMPS:
        raise ReleaseError(f"unknown bump '{bump}' (expected one of {', '.join(BUMPS)})")

    if scheme == "font":
        if bump == "major":
            return format_version((v[0] + 1, 0), scheme)

        if v[1] >= 999:
            raise ReleaseError("font minor version is exhausted (999); use a major bump")

        return format_version((v[0], v[1] + 1), scheme)

    major, minor, patch = v

    if bump == "major":
        return format_version((major + 1, 0, 0), scheme)

    if bump == "minor":
        return format_version((major, minor + 1, 0), scheme)

    return format_version((major, minor, patch + 1), scheme)


def _version_pattern(cfg: Config) -> re.Pattern[str]:
    if cfg.version_file.endswith(".toml"):
        # first `version = "..."` inside the [project] table
        return re.compile(r'(?ms)(^\[project\]\s*$.*?^version\s*=\s*")([^"]+)(")')

    return re.compile(r'(?m)(^version:\s*["\']?)([^"\'\s#]+)(["\']?)')


def read_version_text(text: str, cfg: Config) -> str:
    m = _version_pattern(cfg).search(text)

    if not m:
        raise ReleaseError(f"no version found in {cfg.version_file}")

    return m.group(2)


def read_version(root: Path, cfg: Config) -> str:
    path = root / cfg.version_file

    if not path.is_file():
        raise ReleaseError(f"{cfg.version_file} not found")

    version = read_version_text(path.read_text(encoding="utf-8"), cfg)

    parse_version(version, cfg.scheme)

    return version


def write_version(root: Path, cfg: Config, version: str) -> None:
    path = root / cfg.version_file
    text = path.read_text(encoding="utf-8")
    new, n = _version_pattern(cfg).subn(lambda m: m.group(1) + version + m.group(3), text, count=1)

    if n != 1:
        raise ReleaseError(f"no version found in {cfg.version_file}")

    path.write_text(new, encoding="utf-8", newline="")


# ============================================================================ #
#                                  Changesets                                  #
# ============================================================================ #


@dataclass
class Changeset:
    path: Path
    bump: str          # "none" for an empty changeset
    summary: str

    @property
    def empty(self) -> bool:
        return self.bump == "none"


_FRONT = re.compile(r"\A---[ \t]*\r?\n(.*?)^---[ \t]*\r?\n?(.*)\Z", re.S | re.M)


def parse_changeset(path: Path, cfg: Config) -> Changeset:
    text = path.read_text(encoding="utf-8")
    m = _FRONT.match(text)

    if not m:
        raise ReleaseError(f"{path.name}: missing '---' front matter")

    front, body = m.group(1).strip(), m.group(2).strip()

    if not front:
        return Changeset(path, "none", body)

    bump = "none"

    for line in front.splitlines():
        key, sep, value = line.partition(":")

        if not sep:
            raise ReleaseError(f"{path.name}: cannot parse front matter line '{line}'")

        key, value = key.strip().strip("\"'"), value.strip().strip("\"'")

        if key != cfg.name:
            raise ReleaseError(f"{path.name}: unknown package '{key}' (this repository is '{cfg.name}')")

        if value not in BUMPS:
            raise ReleaseError(f"{path.name}: bump must be one of {', '.join(BUMPS)}, got '{value}'")

        bump = "minor" if (cfg.scheme == "font" and value == "patch") else value  # fonts have no patch part

    if bump != "none" and not body:
        raise ReleaseError(f"{path.name}: the summary is empty")

    return Changeset(path, bump, body)


def pending_changesets(root: Path, cfg: Config) -> list[Changeset]:
    directory = root / CHANGESET_DIR

    if not directory.is_dir():
        return []

    files = sorted(p for p in directory.glob("*.md") if p.name not in NON_CHANGESET_FILES)

    return [parse_changeset(p, cfg) for p in files]


def highest_bump(changesets: list[Changeset]) -> str:
    best = "none"

    for cs in changesets:
        if _RANK[cs.bump] > _RANK[best]:
            best = cs.bump

    return best


def render_changeset(cfg: Config, bump: str | None, summary: str) -> str:
    if bump is None:
        return "---\n---\n"

    return f'---\n"{cfg.name}": {bump}\n---\n\n{summary.strip()}\n'


def random_name(rng: random.Random | None = None) -> str:
    rng = rng or random.Random()
    return "-".join((rng.choice(_WORDS_A), rng.choice(_WORDS_B), rng.choice(_WORDS_C)))


def add_changeset(root: Path, cfg: Config, bump: str | None, summary: str = "",
                  name: str | None = None) -> Path:
    directory = root / CHANGESET_DIR
    directory.mkdir(exist_ok=True)

    for _ in range(50):
        stem = name or random_name()
        path = directory / f"{stem}.md"

        if not path.exists():
            break

        if name:
            raise ReleaseError(f"{path.relative_to(root)} already exists")

    path.write_text(render_changeset(cfg, bump, summary), encoding="utf-8", newline="\n")

    return path


# ============================================================================ #
#                                  Changelog                                   #
# ============================================================================ #

_SECTIONS = (("major", "Major Changes"), ("minor", "Minor Changes"), ("patch", "Patch Changes"))


def _git(root: Path, *args: str, check: bool = True) -> str:
    try:
        res = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:  # pragma: no cover - git is always present in CI
        raise ReleaseError("git is required for this command") from exc

    if check and res.returncode != 0:
        raise ReleaseError(f"git {' '.join(args)} failed: {res.stderr.strip()}")

    return res.stdout


def _short_commit(root: Path, path: Path) -> str:
    """Abbreviated hash of the commit that added ``path`` (empty if unknown)."""

    try:
        rel = path.relative_to(root).as_posix()
        out = _git(root, "log", "--diff-filter=A", "--format=%h", "-n", "1", "--", rel, check=False)
    except (ReleaseError, ValueError):
        return ""

    return out.strip()


def render_section(root: Path, cfg: Config, version: str, changesets: list[Changeset]) -> str:
    parts = [f"## {version}\n"]

    for bump, title in _SECTIONS:
        group = [c for c in changesets if c.bump == bump]

        if not group:
            continue

        parts.append(f"### {title}\n")

        for cs in group:
            commit = _short_commit(root, cs.path)
            first, *rest = cs.summary.splitlines() or [""]
            lead = f"{commit}: " if commit else ""
            lines = [f"- {lead}{first}"] + [f"  {line}".rstrip() for line in rest]

            parts.append("\n".join(lines) + "\n")

    return "\n".join(parts)


def prepend_changelog(root: Path, cfg: Config, section: str) -> None:
    path = root / cfg.changelog
    header = f"# {cfg.name}\n"

    if path.is_file():
        text = path.read_text(encoding="utf-8")
        body = text[len(header):].lstrip("\n") if text.startswith(header) else text
    else:
        body = ""

    new = header + "\n" + section.rstrip("\n") + "\n" + ("\n" + body if body else "")

    path.write_text(new, encoding="utf-8", newline="\n")


def changelog_section(text: str, version: str) -> str:
    """Return the body of ``## <version>`` in a changelog (without the heading)."""

    out: list[str] = []
    found = False

    for line in text.splitlines():
        if line.rstrip() == f"## {version}":
            found = True
            continue

        if found and line.startswith("## "):
            break

        if found:
            out.append(line)

    return "\n".join(out).strip("\n")


# ============================================================================ #
#                                  Operations                                  #
# ============================================================================ #


def next_version(root: Path, cfg: Config) -> str | None:
    """Version that ``release version`` would produce, or ``None`` if nothing is releasable."""

    bump = highest_bump(pending_changesets(root, cfg))

    if bump == "none":
        return None

    return bump_version(read_version(root, cfg), bump, cfg.scheme)


def apply_version(root: Path, cfg: Config, dry_run: bool = False) -> str:
    changesets = pending_changesets(root, cfg)
    bump = highest_bump(changesets)

    if bump == "none":
        raise ReleaseError("no releasable changesets: add one with `octalfont release add`")

    version = bump_version(read_version(root, cfg), bump, cfg.scheme)

    if dry_run:
        return version

    releasable = [c for c in changesets if not c.empty]
    section = render_section(root, cfg, version, releasable)

    write_version(root, cfg, version)
    prepend_changelog(root, cfg, section)

    for cs in changesets:  # empty changesets are consumed too
        cs.path.unlink()

    return version


def base_version(root: Path, cfg: Config, base: str) -> str:
    text = _git(root, "show", f"{base}:{cfg.version_file}", check=False)

    if not text:
        raise ReleaseError(f"cannot read {cfg.version_file} on {base} (does the branch exist and is it fetched?)")

    return read_version_text(text, cfg)


def verify(root: Path, cfg: Config, base: str) -> list[str]:
    """The release gate. Returns a list of problems (empty = ready)."""

    problems: list[str] = []

    try:
        head = read_version(root, cfg)
    except ReleaseError as exc:
        return [str(exc)]

    try:
        released = base_version(root, cfg, base)
    except ReleaseError as exc:
        return [str(exc)]

    if parse_version(head, cfg.scheme) <= parse_version(released, cfg.scheme):
        problems.append(f"version {head} is not greater than the version already on {base} ({released})")

    changelog = root / cfg.changelog

    if not changelog.is_file() or not changelog_section(changelog.read_text(encoding="utf-8"), head):
        problems.append(f"{cfg.changelog} has no '## {head}' section")

    left = [c.path.name for c in pending_changesets(root, cfg) if not c.empty]

    if left:
        problems.append("unconsumed changesets are still present: " + ", ".join(left))

    return problems


def changed_files(root: Path, base: str, head: str = "HEAD") -> list[tuple[str, str]]:
    out = _git(root, "diff", "--name-status", "--no-renames", f"{base}...{head}")
    result = []

    for line in out.splitlines():
        status, _, name = line.partition("\t")

        result.append((status, name))

    return result


def check_pr(root: Path, cfg: Config, base: str, head: str = "HEAD") -> str | None:
    """Return a problem description if the diff needs a changeset but has none."""

    changes = changed_files(root, base, head)
    added = [n for s, n in changes if s == "A" and n.startswith(f"{CHANGESET_DIR}/") and n.endswith(".md")
             and Path(n).name not in NON_CHANGESET_FILES]

    if added:
        return None

    relevant = [n for s, n in changes if not n.startswith(f"{CHANGESET_DIR}/")
                and any(fnmatch.fnmatch(n, g) for g in cfg.paths)]

    if not relevant:
        return None

    shown = ", ".join(relevant[:5]) + (" ..." if len(relevant) > 5 else "")

    return (f"this change touches release-relevant files ({shown}) but adds no changeset. "
            "Run `octalfont release add` (or `octalfont release add --empty` if no release is needed).")


def list_versions(root: Path, cfg: Config) -> list[tuple[Version, str]]:
    tags = _git(root, "tag", "--list", f"{cfg.tag_prefix}*").split()
    found = []

    for tag in tags:
        try:
            found.append((parse_version(tag[len(cfg.tag_prefix):], cfg.scheme), tag))
        except ReleaseError:
            continue

    return sorted(found)


def previous_tag(root: Path, cfg: Config, version: str) -> str | None:
    target = parse_version(version, cfg.scheme)
    lower = [t for v, t in list_versions(root, cfg) if v < target]

    return lower[-1] if lower else None


# ============================================================================ #
#                                     CLI                                      #
# ============================================================================ #


def _prompt(question: str, choices: tuple[str, ...] | None = None, default: str | None = None) -> str:
    suffix = f" [{'/'.join(choices)}]" if choices else ""
    suffix += f" ({default})" if default else ""

    while True:
        answer = input(f"{question}{suffix}: ").strip() or (default or "")

        if answer and (not choices or answer in choices):
            return answer

        print("  please answer with one of: " + ", ".join(choices) if choices else "  a value is required")


def _root(args: argparse.Namespace) -> Path:
    root = Path(args.project).resolve()

    return root.parent.parent if root.is_file() else root


def cmd_add(args: argparse.Namespace) -> int:
    root = _root(args)
    cfg = Config.load(root)

    if args.empty:
        path = add_changeset(root, cfg, None, name=args.name)
    else:
        bump, summary = args.bump, args.message

        if not bump or not summary:
            if not sys.stdin.isatty():
                raise ReleaseError("--bump and --message are required when not running in a terminal")

            allowed = BUMPS if cfg.scheme == "semver" else ("minor", "major")
            bump = bump or _prompt("Bump level", allowed)
            summary = summary or _prompt("Summary (one line, shown in the changelog)")

        if cfg.scheme == "font" and bump == "patch":
            bump = "minor"

        path = add_changeset(root, cfg, bump, summary, name=args.name)

    print(path.relative_to(root).as_posix())

    return 0


def cmd_status(args: argparse.Namespace) -> int:
    root = _root(args)
    cfg = Config.load(root)
    changesets = pending_changesets(root, cfg)

    if not changesets:
        print("No pending changesets.")
        return 0

    for cs in changesets:
        first = cs.summary.splitlines()[0] if cs.summary else ""
        print(f"{cs.bump:<6} {cs.path.name}  {first}")

    nxt = next_version(root, cfg)

    print(f"\ncurrent {read_version(root, cfg)} -> next {nxt}" if nxt else "\nNothing releasable (only empty changesets).")

    return 0


def cmd_version(args: argparse.Namespace) -> int:
    root = _root(args)
    cfg = Config.load(root)

    print(apply_version(root, cfg, dry_run=args.dry_run))

    return 0


def cmd_next(args: argparse.Namespace) -> int:
    root = _root(args)
    nxt = next_version(root, Config.load(root))

    print(nxt or "")

    return 0


def cmd_current(args: argparse.Namespace) -> int:
    root = _root(args)

    print(read_version(root, Config.load(root)))

    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    root = _root(args)
    cfg = Config.load(root)
    problems = verify(root, cfg, args.base or f"origin/{cfg.release_branch}")

    for p in problems:
        print(f"::error::{p}" if args.github else f"error: {p}")

    if not problems:
        print(f"OK: {read_version(root, cfg)} is ready to release")

    return 1 if problems else 0


def cmd_check(args: argparse.Namespace) -> int:
    root = _root(args)
    cfg = Config.load(root)
    problem = check_pr(root, cfg, args.base or f"origin/{cfg.base_branch}", args.head)

    if problem:
        print(f"::error::{problem}" if args.github else f"error: {problem}")
        return 1

    print("OK: changeset requirements satisfied")

    return 0


def cmd_notes(args: argparse.Namespace) -> int:
    root = _root(args)
    cfg = Config.load(root)
    version = args.version or read_version(root, cfg)
    path = root / cfg.changelog
    text = changelog_section(path.read_text(encoding="utf-8"), version) if path.is_file() else ""

    print(text or f"_No changelog entries found for {version}._")

    return 0


def cmd_previous(args: argparse.Namespace) -> int:
    root = _root(args)
    cfg = Config.load(root)

    print(previous_tag(root, cfg, args.version) or "")

    return 0


def register(sub: "argparse._SubParsersAction") -> None:
    """Attach ``release`` and its sub-commands to the main parser."""
    p = sub.add_parser("release", help="changesets, versioning and release gates")
    rs = p.add_subparsers(dest="release_cmd", required=True)

    a = rs.add_parser("add", help="write a new changeset")
    a.add_argument("--bump", choices=BUMPS)
    a.add_argument("-m", "--message", help="one-line summary for the changelog")
    a.add_argument("--empty", action="store_true", help="empty changeset: no version bump, no changelog entry")
    a.add_argument("--name", help="file name without .md (default: random)")
    a.set_defaults(fn=cmd_add)

    rs.add_parser("status", help="list pending changesets and the resulting version").set_defaults(fn=cmd_status)

    v = rs.add_parser("version", help="consume changesets: bump version, update the changelog")
    v.add_argument("--dry-run", action="store_true", help="print the next version without writing anything")
    v.set_defaults(fn=cmd_version)

    rs.add_parser("next", help="print the version the pending changesets would produce").set_defaults(fn=cmd_next)
    rs.add_parser("current", help="print the version in the version file").set_defaults(fn=cmd_current)

    g = rs.add_parser("verify", help="release gate: version moved forward and is documented")
    g.add_argument("--base", help="ref of the last release (default: origin/<releaseBranch>)")
    g.add_argument("--github", action="store_true", help="emit ::error:: annotations")
    g.set_defaults(fn=cmd_verify)

    c = rs.add_parser("check", help="PR gate: release-relevant changes need a changeset")
    c.add_argument("--base", help="ref of the target branch (default: origin/<baseBranch>)")
    c.add_argument("--head", default="HEAD")
    c.add_argument("--github", action="store_true", help="emit ::error:: annotations")
    c.set_defaults(fn=cmd_check)

    n = rs.add_parser("notes", help="print the changelog section of a version")
    n.add_argument("version", nargs="?")
    n.set_defaults(fn=cmd_notes)

    pr = rs.add_parser("previous", help="print the highest released tag below VERSION")
    pr.add_argument("version")
    pr.set_defaults(fn=cmd_previous)

