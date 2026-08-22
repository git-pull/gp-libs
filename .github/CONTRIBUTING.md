# Contributing

Thanks for looking. gp-libs is pre-1.0 (`0.0.x`); a minor version bump may
still carry a breaking change. Bug reports with a reproduction, and notes on
where the documentation misled you, are the most useful contributions right
now.

How this project writes prose — README, `CHANGES`, release notes, commit
messages, docstrings, source comments, and log messages — is set out
separately in [WRITING.md](WRITING.md). Read that before changing any of it.
The constraints every change is held to, and the map of what is where, are in
[AGENTS.md](../AGENTS.md).

## Getting set up

Install [git], [uv], and [just].

```console
$ git clone https://github.com/git-pull/gp-libs.git
```

```console
$ cd gp-libs
```

```console
$ uv sync --all-extras --dev
```

[git]: https://git-scm.com/
[uv]: https://github.com/astral-sh/uv
[just]: https://just.systems/

## The gates

Format:

```console
$ uv run ruff format .
```

Lint:

```console
$ uv run ruff check . --fix --show-fixes
```

Type-check — strict mypy across `src/` and `tests/`:

```console
$ uv run mypy .
```

Test:

```console
$ uv run pytest
```

**Imports.** Namespace stdlib imports — `import enum`, not
`from enum import Enum` — so a call site reads `enum.Enum`. Third-party
packages may use `from X import Y`. For typing, `import typing as t` and
access via the namespace: `t.NamedTuple`, `t.TYPE_CHECKING`. Every file
starts with `from __future__ import annotations`; ruff's isort
`required-imports` (`pyproject.toml`) enforces that one, the rest is
convention ruff does not check.

Documentation is a gate, not a courtesy. Examples in `src/*.py` docstrings
and under `docs/` are executed by `uv run pytest`, because `testpaths` in
`pyproject.toml` lists `tests`, `docs`, and `src`; `README.md` is not in
`testpaths`, so its three `>>> ` examples do not currently run under CI.
There is no separate doctest step for the paths that are collected — a
green `pytest` is the proof. Which blocks qualify, and the one mistake that
silently removes a test, are in
[WRITING.md](WRITING.md#documented-examples-that-run).

Before claiming a test or a gate works, show it failing. A gate that has
never been red is an assumption.

CI (`.github/workflows/tests.yml`) runs the equivalent of the four commands
above (`ruff check .`, `ruff format . --check`, `mypy .`,
`py.test --cov=./ --cov-report=xml`) across a matrix of Python 3.10-3.14,
docutils 0.20 and 0.22.4, and pytest 8 and 9 — gp-libs supports a wider
version span than most consumers of it, because everything downstream
depends on this collector staying compatible.

## Tests

Write tests as standalone functions, not classes — no `class TestFoo:`
groupings. Use descriptive function names and file organization instead.

Prefer fixtures from `tests/conftest.py` over `monkeypatch` and
`unittest.mock` when one exists; document in the test docstring why a
standard fixture was not used for an exceptional case. Use `tmp_path`
(`pathlib.Path`) over `tempfile`, and `monkeypatch` over `unittest.mock`
when you do need one.

`tests/conftest.py` also provides the Sphinx `app_params`/`make_app_params`
fixtures (via `pytest_plugins = ["sphinx.testing.fixtures", "pytester"]`)
for tests that build a throwaway Sphinx app — used by
`tests/test_linkify_issues.py` and the plugin-suppression tests.
`tests/regressions/` holds one file per historical bug, named for its
issue.

Run continuously with [pytest-watcher]:

```console
$ just start
```

Or with [entr(1)] when you want a shell-only watcher:

```console
$ just watch-test
```

[pytest-watcher]: https://github.com/olzhasar/pytest-watcher
[entr(1)]: http://eradman.com/entrproject/

## Documentation

Build the docs:

```console
$ just build-docs
```

Start the default preview server, which watches for file changes:

```console
$ just start-docs
```

From inside `docs/`, the local `docs/justfile` has finer-grained recipes:
`just html` builds once, `just serve` serves the built output, `just watch`
rebuilds on change, `just dev` watches and serves together, and
`just design` disables incremental builds while you edit static assets.

`docs/conf.py` also enables `sphinx.ext.doctest` with a
`doctest_global_setup` that imports `is_allowed_version` and
`pytest_ignore_collect`, so the `{doctest}` blocks under `docs/` are valid
input to Sphinx's own doctest builder as well as to pytest. Run it with
`just -f docs/justfile doctest`. Neither `tests.yml` nor `docs.yml` invokes
that recipe — it is a manual, local-only check, not a CI gate. `just
build-docs` is what CI runs, and it is also the only thing that catches a
broken `{ref}`/`{doc}` cross-reference; the doctests do not.

## Releasing

gp-libs is pre-1.0: minor version bumps may include breaking changes. [uv]
handles virtualenv creation, package requirements, versioning, building,
and publishing — there is no `setup.py` or requirements file.

1. Update `CHANGES` with release notes.
2. Bump the version in `src/gp_libs.py` and `pyproject.toml`.
3. Create the release commit:

   ```console
   $ git commit -m 'Tag v0.1.1'
   ```

4. Push the branch for review:

   ```console
   $ git push
   ```

5. After review, the release owner creates and pushes the tag. Never
   create tags. Never push tags. The owner handles tagging and tag pushes,
   because a tag triggers the publish workflow. See
   [Release commits](WRITING.md#release-commits).

## Pull requests

One subject per pull request. Unrelated cleanup found along the way
belongs in its own commit, and usually in its own pull request.

Discuss a substantial change via an issue before making it.

Commit format is in [WRITING.md](WRITING.md#commits).

## Decorum

- Participants will be tolerant of opposing views.
- Participants must ensure that their language and actions are free of
  personal attacks and disparaging personal remarks.
- When interpreting the words and actions of others, participants should
  always assume good intentions.
- Behaviour which can be reasonably considered harassment will not be
  tolerated.

Based on [Ruby's Community Conduct Guideline](https://www.ruby-lang.org/en/conduct/).

## Security

Please do not open a public issue for a vulnerability. Report it privately
through GitHub:
<https://github.com/git-pull/gp-libs/security/advisories/new>.
