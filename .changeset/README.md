# Changesets

Every change that should reach users of the tool is described by a
**changeset**: a small Markdown file in this directory. The release automation
collects them, picks the highest bump level, writes `CHANGELOG.md` and opens the
release pull request. See [RELEASING.md](../RELEASING.md) for the whole flow.

## Add one

```sh
octalfont release add
```

The command asks for the bump level and a one-line summary, then writes
`.changeset/<random-name>.md`:

```md
---
"octalfont": minor
---

Add `octalfont package` to build the Google Fonts release archive.
```

Commit the file together with your change.

| Level   | Use it for                                                         |
|---------|--------------------------------------------------------------------|
| `patch` | Bug fixes and internal changes that do not alter behaviour         |
| `minor` | New commands, options or checks; backwards-compatible changes      |
| `major` | Breaking changes (a renamed command, a changed `font.yaml` format) |

## Nothing to release?

Documentation, CI and test-only pull requests do not need a version bump. Say so
explicitly with an empty changeset, so the check does not ask again:

```sh
octalfont release add --empty
```

## Useful commands

```sh
octalfont release status  # pending changesets and the version they would produce
octalfont release version # (automation) consume changesets, bump, update CHANGELOG.md
```

Do not edit `version` in `pyproject.toml` or `CHANGELOG.md` by hand.
