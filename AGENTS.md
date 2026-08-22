# AGENTS.md

gp-libs is the doctest and documentation-testing tooling for the git-pull
fleet: it makes `>>> ` examples in `.py`, `.rst`, and `.md` files runnable
as pytest tests, and links issue references in Sphinx docs. Other repos in
the fleet depend on its collector; treat its public behaviour as shared
infrastructure, not this repo's private concern.

Follow the conventions already in the tree, and keep a change scoped to
what was asked for.

## What is here

| Path | What it is |
| ---- | ---------- |
| `src/doctest_docutils.py` | doctest reimplementation that parses reStructuredText and Markdown |
| `src/pytest_doctest_docutils.py` | pytest plugin (`pytest11` entry point, key `sphinx`) that collects those doctests |
| `src/linkify_issues.py` | Sphinx extension: `#123` becomes an issue link |
| `src/docutils_compat.py` | cross-version docutils compatibility shim (`findall`) |
| `src/gp_libs.py` | package metadata (version, title, URLs) |
| `tests/` | unit and regression tests; `tests/conftest.py` provides Sphinx app fixtures |
| `docs/` | Sphinx/MyST documentation; dogfoods the doctest collector it documents |
| `CHANGES` | changelog, rendered at `docs/history.md` |

## Which policy applies

- Documentation, user-facing text, `CHANGES`, release notes, commit
  messages, docstrings, and source comments:
  [.github/WRITING.md](.github/WRITING.md)
- Environment, the gates, tests, documentation builds, releases, and pull
  requests: [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md)

Each of those is the single home for its subject. Where a rule seems to be
stated twice, the file listed above is the one that governs.

## Change discipline

- Make the smallest coherent change that solves the verified problem; keep
  unrelated cleanup out of it.
- Reuse an existing file, helper, API, or test before adding a new one.
- Add a file only for a durable boundary — a distinct responsibility,
  independent reuse, or splitting an oversized module — not for a
  single-use helper or a one-line re-export.
- Add a test for every user-visible behaviour change, and a `CHANGES`
  entry for every change to the public API, CLI, configuration, or
  output.
- A passing gate is evidence only once it has been shown capable of
  failing. Pair a new test with a deliberate break that proves it bites.

`.py` files delegate straight to pytest's own `DoctestModule`; `.rst` and
`.md` files go through this package's own `DocutilsDocTestFinder`. Of the
non-stdlib doctest flags the pytest plugin registers, only `HIDE` is a
gp-libs invention — `ALLOW_UNICODE`, `ALLOW_BYTES`, and `NUMBER` are
borrowed from pytest's own (blocked) doctest plugin to keep behaviour
consistent. See
[Documented examples that run](.github/WRITING.md#documented-examples-that-run)
before changing collection, directive, or flag behaviour — it is the
fullest account of the mechanism in the fleet, and other repos rely on it
staying accurate.

## References

- Documentation: <https://gp-libs.git-pull.com/>
- GitHub: <https://github.com/git-pull/gp-libs>
- PyPI: <https://pypi.org/project/gp-libs/>
