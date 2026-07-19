# AGENTS.md

This file provides guidance to AI agents (including Claude Code, Cursor, and other LLM-powered tools) when working with code in this repository.

## CRITICAL REQUIREMENTS

### Test Success
- ALL tests MUST pass for code to be considered complete and working
- Never describe code as "working as expected" if there are ANY failing tests
- Even if specific feature tests pass, failing tests elsewhere indicate broken functionality
- Changes that break existing tests must be fixed before considering implementation complete
- A successful implementation must pass linting, type checking, AND all existing tests

## Project Overview

gp-libs is a Python library providing internal utilities and extensions for git-pull projects. It focuses on extending Sphinx documentation and pytest functionality with support for docutils-compatible markup formats.

Key features:
- **doctest_docutils**: Reimplementation of Python's doctest with support for reStructuredText and Markdown
- **pytest_doctest_docutils**: pytest plugin for running doctests in documentation files
- **linkify_issues**: Sphinx extension that converts issue references (e.g., `#123`) to hyperlinks
- Supports testing doctest examples in `.rst` and `.md` files
- Powers documentation testing across the git-pull ecosystem

## Development Environment

This project uses:
- Python 3.10+
- [just](https://github.com/casey/just) for command running (see also https://just.systems/)
- [uv](https://github.com/astral-sh/uv) for dependency management
- [ruff](https://github.com/astral-sh/ruff) for linting and formatting
- [mypy](https://github.com/python/mypy) for type checking
- [pytest](https://docs.pytest.org/) for testing
  - [pytest-watcher](https://github.com/olzhasar/pytest-watcher) for continuous testing

## Common Commands

### Setting Up Environment

```bash
# Install dependencies
uv pip install --editable .
uv pip sync

# Install with development dependencies
uv pip install --editable . -G dev
```

### Running Tests

```bash
# Run all tests
just test
# or directly with pytest
uv run pytest

# Run a single test file
uv run pytest tests/test_doctest_docutils.py

# Run a specific test
uv run pytest tests/test_doctest_docutils.py::test_function_name

# Run tests with test watcher
just start
# or
uv run ptw .

# Run tests with doctests
uv run ptw . --now --doctest-modules
```

### Linting and Type Checking

```bash
# Run ruff for linting
just ruff
# or directly
uv run ruff check .

# Format code with ruff
just ruff-format
# or directly
uv run ruff format .

# Run ruff linting with auto-fixes
uv run ruff check . --fix --show-fixes

# Run mypy for type checking
just mypy
# or directly
uv run mypy src tests

# Watch mode for linting (using entr)
just watch-ruff
just watch-mypy
```

### Development Workflow

Follow this workflow for code changes (see `.cursor/rules/dev-loop.mdc`):

1. **Format First**: `uv run ruff format .`
2. **Run Tests**: `uv run pytest`
3. **Run Linting**: `uv run ruff check . --fix --show-fixes`
4. **Check Types**: `uv run mypy`
5. **Verify Tests Again**: `uv run pytest`

### Documentation

```bash
# Build documentation
just build-docs

# Start documentation server with auto-reload
just start-docs

# Update documentation CSS/JS
just design-docs
```

## Code Architecture

gp-libs provides utilities for documentation testing and Sphinx extensions:

```
src/
├── doctest_docutils.py          # Core doctest reimplementation
├── pytest_doctest_docutils.py   # pytest plugin
├── linkify_issues.py            # Sphinx extension
├── docutils_compat.py           # Compatibility layer
└── gp_libs.py                   # Package metadata
```

### Core Modules

1. **doctest_docutils** (`src/doctest_docutils.py`)
   - Reimplementation of Python's standard library `doctest` module
   - Supports docutils-compatible markup (reStructuredText and Markdown)
   - Handles `doctest_block`, `.. doctest::` directive, and ` ```{doctest} ` code blocks
   - PEP-440 version specifier support for conditional tests
   - Can be run directly: `python -m doctest_docutils README.md -v`

2. **pytest_doctest_docutils** (`src/pytest_doctest_docutils.py`)
   - pytest plugin integrating doctest_docutils with pytest
   - Collects and runs doctests from `.rst` and `.md` files
   - Full pytest fixture and conftest.py support
   - Registered as `pytest11` entry point

3. **linkify_issues** (`src/linkify_issues.py`)
   - Sphinx extension for automatic issue linking
   - Converts `#123` references to clickable hyperlinks
   - Configured via `issue_url_tpl` in Sphinx conf.py

4. **docutils_compat** (`src/docutils_compat.py`)
   - Compatibility layer for cross-version docutils support
   - Provides `findall()` abstraction for different docutils versions

5. **gp_libs** (`src/gp_libs.py`)
   - Package metadata (version, title, author, URLs)

## Testing Strategy

gp-libs uses pytest for testing with custom fixtures. The test suite includes:

- Unit tests for doctest parsing and execution
- Integration tests for pytest plugin functionality
- Sphinx app factory for testing extensions

### Test Structure

```
tests/
├── test_doctest_docutils.py       # Tests for doctest module
├── test_pytest_doctest_docutils.py # Tests for pytest plugin
├── test_linkify_issues.py         # Tests for linkify extension
├── conftest.py                    # Fixtures and sphinx app factory
└── regressions/                   # Regression tests
```

### Testing Guidelines

1. **Use functional tests only**: Write tests as standalone functions, not classes. Avoid `class TestFoo:` groupings - use descriptive function names and file organization instead.

2. **Use existing fixtures over mocks** (see `.cursor/rules/dev-loop.mdc`)
   - Use fixtures from conftest.py instead of `monkeypatch` and `MagicMock` when available
   - Document in test docstrings why standard fixtures weren't used for exceptional cases

3. **Preferred pytest patterns**
   - Use `tmp_path` (pathlib.Path) fixture over Python's `tempfile`
   - Use `monkeypatch` fixture over `unittest.mock`

4. **Running tests continuously**
   - Use pytest-watcher during development: `uv run ptw .`
   - For doctests: `uv run ptw . --now --doctest-modules`

## Coding Standards

For detailed coding standards, refer to `.cursor/rules/dev-loop.mdc`. Key highlights:

### Imports

- **Use namespace imports for stdlib**: `import enum` instead of `from enum import Enum`; third-party packages may use `from X import Y`
- **For typing**, use `import typing as t` and access via namespace: `t.NamedTuple`, etc.
- **Use `from __future__ import annotations`** at the top of all Python files

### Docstrings

Follow NumPy docstring style for all functions and methods (see `.cursor/rules/dev-loop.mdc`):

```python
"""Short description of the function or class.

Detailed description using reStructuredText format.

Parameters
----------
param1 : type
    Description of param1
param2 : type
    Description of param2

Returns
-------
type
    Description of return value
"""
```

### Doctests

**All functions and methods MUST have working doctests.** Doctests serve as both documentation and tests.

**CRITICAL RULES:**
- Doctests MUST actually execute - never comment out function calls or use placeholder output
- Doctests MUST NOT be converted to `.. code-block::` as a workaround (code-blocks don't run)
- If you cannot create a working doctest, **STOP and ask for help**

**Available tools for doctests:**
- `doctest_namespace` fixtures: `tmp_path` (add more via `conftest.py`)
- Ellipsis for variable output: `# doctest: +ELLIPSIS`
- PEP-440 version specifiers via `is_allowed_version()` for version-conditional tests

**`# doctest: +SKIP` is NOT permitted** - it's just another workaround that doesn't test anything. Use the fixtures and ellipsis patterns properly.

**Simple doctest example:**
```python
>>> is_allowed_version('3.3', '<=3.5')
True
>>> is_allowed_version('3.3', '>3.2, <4.0')
True
```

**When output varies, use ellipsis:**
```python
>>> parse_document(content)  # doctest: +ELLIPSIS
<docutils.nodes.document ...>
```

**Additional guidelines:**
1. Use narrative descriptions for test sections rather than inline comments
2. Move complex examples to dedicated test files at `tests/examples/<path_to_module>/test_<example>.py`
3. Keep doctests simple and focused on demonstrating usage
4. Add blank lines between test sections for improved readability

### Logging Standards

These rules guide future logging changes; existing code may not yet conform.

#### Logger setup

- Use `logging.getLogger(__name__)` in every module
- Add `NullHandler` in library `__init__.py` files
- Never configure handlers, levels, or formatters in library code — that's the application's job

#### Structured context via `extra`

Pass structured data on every log call where useful for filtering, searching, or test assertions.

**Core keys** (stable, scalar, safe at any log level):

| Key | Type | Context |
|-----|------|---------|
| `doctest_source_file` | `str` | doctest source path (.rst, .md, .py) |
| `doctest_block_type` | `str` | block type (doctest_block, code fence) |
| `sphinx_extension` | `str` | Sphinx extension name |

Treat established keys as compatibility-sensitive — downstream users may build dashboards and alerts on them. Change deliberately.

#### Key naming rules

- `snake_case`, not dotted; project-specific prefixes (`doctest_`, `sphinx_`)
- Prefer stable scalars; avoid ad-hoc objects

#### Lazy formatting

`logger.debug("msg %s", val)` not f-strings. Two rationales:
- Deferred string interpolation: skipped entirely when level is filtered
- Aggregator message template grouping: `"Running %s"` is one signature grouped ×10,000; f-strings make each line unique

When computing `val` itself is expensive, guard with `if logger.isEnabledFor(logging.DEBUG)`.

#### stacklevel for wrappers

Increment for each wrapper layer so `%(filename)s:%(lineno)d` and OTel `code.filepath` point to the real caller. Verify whenever call depth changes.

#### Log levels

| Level | Use for | Examples |
|-------|---------|----------|
| `DEBUG` | Internal mechanics | Doctest parsing, node traversal steps |
| `INFO` | Lifecycle, user-visible operations | Extension loaded, document processed |
| `WARNING` | Recoverable issues, deprecation | Deprecated directive, missing optional dependency |
| `ERROR` | Failures that stop an operation | Parse error, invalid configuration |

#### Message style

- Lowercase, past tense for events: `"extension loaded"`, `"parse error"`
- No trailing punctuation
- Keep messages short; put details in `extra`, not the message string

#### Exception logging

- Use `logger.exception()` only inside `except` blocks when you are **not** re-raising
- Use `logger.error(..., exc_info=True)` when you need the traceback outside an `except` block
- Avoid `logger.exception()` followed by `raise` — this duplicates the traceback. Either add context via `extra` that would otherwise be lost, or let the exception propagate

#### Testing logs

Assert on `caplog.records` attributes, not string matching on `caplog.text`:
- Scope capture: `caplog.at_level(logging.DEBUG, logger="doctest_docutils")`
- Filter records rather than index by position: `[r for r in caplog.records if hasattr(r, "doctest_source_file")]`
- Assert on schema: `record.sphinx_extension == "doctest_docutils"` not `"doctest_docutils" in caplog.text`
- `caplog.record_tuples` cannot access extra fields — always use `caplog.records`

#### Avoid

- f-strings/`.format()` in log calls
- Unguarded logging in hot loops (guard with `isEnabledFor()`)
- Catch-log-reraise without adding new context
- `print()` for diagnostics
- Logging secret env var values (log key names only)
- Non-scalar ad-hoc objects in `extra`
- Requiring custom `extra` fields in format strings without safe defaults (missing keys raise `KeyError`)

### Git Commit Standards

See `.cursor/rules/git-commits.mdc` for detailed commit message standards.

Format commit messages as:
```
Scope(type[detail]): concise description

why: Explanation of necessity or impact.

what:
- Specific technical changes made
- Focused on a single topic
```

Keep the subject ≤50 chars (excluding any trailing `(#NN)` PR ref); wrap
body lines at ≤72 chars. Separate the `why:` and `what:` blocks with a
blank line.

Common commit types:
- **feat**: New features or enhancements
- **fix**: Bug fixes
- **refactor**: Code restructuring without functional change
- **docs**: Documentation updates
- **chore**: Maintenance (dependencies, tooling, config)
- **test**: Test-related updates
- **style**: Code style and formatting
- **py(deps)**: Dependencies
- **py(deps[dev])**: Dev Dependencies
- **ai(rules[AGENTS])**: AI rule updates
- **ai(claude[rules])**: Claude Code rules (CLAUDE.md)
- **ai(claude[command])**: Claude Code command changes

Example:
```
doctest_docutils(feat[parse]): Add support for myst-parser code blocks

why: Enable doctest execution in Markdown documentation files

what:
- Add detection for ```{doctest} fence syntax
- Register myst directives automatically
- Add tests for Markdown doctest parsing
```
#### Release commits

Never create tags. Never push tags. The user handles tagging and tag
pushes (tags trigger the CI publish workflow).

Release commit subjects are plain and short: `Tag v<version>`. Put
the detailed why/what in the commit body. Don't use the
`Scope(type[detail]):` format for releases — don't bury the lede.

For multi-line commits, use heredoc to preserve formatting:
```bash
git commit -m "$(cat <<'EOF'
feat(Component[method]) add feature description

why: Explanation of the change.

what:
- First change
- Second change
EOF
)"
```

## Documentation Standards

### Code Blocks in Documentation

When writing documentation (README, CHANGES, docs/), follow these rules for code blocks:

**One command per code block.** This makes commands individually copyable.

**Put explanations outside the code block**, not as comments inside.

Good:

Run the tests:

```console
$ uv run pytest
```

Run with coverage:

```console
$ uv run pytest --cov
```

Bad:

```console
# Run the tests
$ uv run pytest

# Run with coverage
$ uv run pytest --cov
```

### Changelog Conventions

These rules apply when authoring entries in `CHANGES`, which is rendered as the Sphinx changelog page. Modeled on Django's release-notes shape — deliverables get titles and prose, not bullets. Older entries used a flat `### Section` + bullet shape; new entries follow the Django shape below.

**Release entry boilerplate.** Every release header is `## gp-libs X.Y.Z (YYYY-MM-DD)`. The file opens with a `## gp-libs X.Y.Z (unreleased)` placeholder block fenced by `<!-- KEEP THIS PLACEHOLDER ... -->` and `<!-- END PLACEHOLDER ... -->` HTML comments — new release entries land immediately below the END marker, never above it.

**Open with a multi-sentence lead paragraph.** Plain prose, no italic. Open with the version as sentence subject (*"gp-libs X.Y.Z ships …"*) so the lead is self-contained when excerpted. Two to four sentences telling the reader what shipped and who cares — user-visible takeaways, not internal mechanism. Cross-reference detail docs with `{ref}` to keep the lead compact.

**Lead paragraphs are release-time material — off-limits to branches and PRs.** The unreleased entry carries no lead paragraph and no version summary: sections only (`### Breaking changes`, `### What's new` deliverables, `### Fixes`, …). Speaking for the release — what the version "is", "ships", or "focuses on" — is presumptuous before its scope is final; only the person cutting the release writes that, and only when the user explicitly asks to release. Never write or edit a lead from a feature branch, and never ask or imply that a release should happen.

**Each deliverable is a section, not a bullet.** Inside `### What's new`, every distinct deliverable gets a `#### Deliverable title (#NN)` heading naming it in user vocabulary, followed by 1-3 prose paragraphs explaining what shipped. Don't wrap a paragraph in `- ` — bullets are for enumerable lists, not paragraph containers. Cross-link detail docs (`See {ref}\`foo\` for details.`) so prose stays focused.

**The deliverable test.** Before writing an entry, ask: "What's the deliverable, in user vocabulary?" If you can't answer in one sentence, the entry isn't ready. Mechanism (helper internals, byte counters, schema-validation locations) belongs in PR descriptions and code comments, not the changelog.

**Fixed subheadings**, in this order when present: `### Breaking changes`, `### Dependencies`, `### What's new`, `### Fixes`, `### Documentation`, `### Development`. Dev tooling (helper scripts, internal automation) lives under `### Development`. For breaking changes, show the migration path with concrete inline code (e.g. a `# Before` / `# After` fenced code block). Dependency floor bumps use the form ``Minimum `pkg>=X.Y.Z` (was `>=X.Y.W`)``.

**PR refs `(#NN)`** sit in each deliverable's `####` heading.

**When bullets are appropriate.** Catch-all sections (`### Fixes`, occasionally `### Documentation`) with 3+ genuinely small items use bullets — one line each, never paragraphs. If a bullet swells past two lines, promote it to a `#### Title (#NN)` heading with prose body.

**Anti-patterns.**

- Fragile metrics: token ceilings, third-party version pins, percent benchmarks, exact byte counts. Describe the *capability*, not the math.
- Internal jargon: private symbols (leading-underscore identifiers), algorithm names exposed for the first time, backend scaffolding.
- Walls of text dressed up as bullets.
- Buried breaking changes — they get their own subheading at the top of the entry.

**Always link autodoc'd APIs.** Any class, method, function, exception, or attribute that has its own rendered page must be cited via the appropriate role (`{class}`, `{meth}`, `{func}`, `{exc}`, `{attr}`) — never with plain backticks. Doc pages without explicit ref labels use `{doc}`. Plain backticks are correct for code syntax, env vars, parameter names, and file paths that aren't doc pages — anything without an autodoc destination.

**MyST roles.** Class references use `{class}`, methods use `{meth}`, functions use `{func}`, exceptions use `{exc}`, attributes use `{attr}`, internal anchors use `{ref}`, doc-path links use `{doc}`.

**Summarization style.** When a user asks "what changed in the latest version?" or similar, lead with the entry's lead paragraph (paraphrased if needed), followed by each `####` deliverable heading under `### What's new` with a one-sentence summary. Cite `(#NN)` only if the user asks for source links. Don't invent versions, dates, or numbers not present in `CHANGES`. Don't quote line numbers or file offsets — those shift as the file evolves.

## Debugging Tips

See `.cursor/rules/avoid-debug-loops.mdc` for detailed debugging guidance.

When stuck in debugging loops:

1. **Pause and acknowledge the loop**
2. **Minimize to MVP**: Remove all debugging cruft and experimental code
3. **Document the issue** comprehensively for a fresh approach
4. **Format for portability** (using quadruple backticks)

## Sphinx/Docutils-Specific Considerations

### Directive Registration

- Use `_ensure_directives_registered()` to auto-register required directives
- Supports myst-parser directives (`{doctest}`, `{tab}`)
- Handles both reStructuredText and Markdown syntax

### Document Parsing

- Uses docutils for parsing `.rst` files
- Uses myst-parser for parsing `.md` files
- Both formats support doctest blocks

### linkify_issues Configuration

In your Sphinx `conf.py`:
```python
extensions = ["linkify_issues"]
issue_url_tpl = 'https://github.com/git-pull/gp-libs/issues/{issue_id}'
```

## References

- Documentation: https://gp-libs.git-pull.com/
- GitHub: https://github.com/git-pull/gp-libs
- PyPI: https://pypi.org/project/gp-libs/

## AI Slop Prevention

Treat AI slop as **review-hostile noise**, not as proof that text or
code is wrong. The goal is to maximize information density by removing
artifacts that make the repository harder to trust or navigate.

### The Anti-Slop Rubric

Before committing, audit all AI-assisted changes for these noise
patterns:

- **AI Signatures:** Remove "Generated by", footers, conversational
  filler ("Certainly!", "Here is..."), unexplained emojis (🤖, ✨), and
  AI-tool metadata.
- **Brittle References:** Avoid hard-coded line numbers, fragile
  file/test counts, dated "as of" claims, bare SHAs, and local
  absolute paths unless they are strict evidentiary artifacts (e.g.,
  benchmark logs).
- **Diff Narration:** Do not restate what moved, was renamed, or was
  removed in artifacts the downstream reader holds: code, docstrings,
  README, CHANGES, PR descriptions, or release notes. The diff and
  commit message already carry this history.
- **Branch-Internal Narrative:** Do not mention intermediate branch
  states, abandoned approaches, or "no longer" behavior unless users
  of a published release actually experienced the old state (**The
  Published-Release Test**).
- **Low-Value Scaffolding:** Remove ownerless TODOs (`TODO: revisit`),
  unused future-proofing, debug artifacts, and defensive wrappers that
  do not protect a currently reachable failure mode.
- **Prose Inflation:** Replace generic AI "tells" like *comprehensive,
  robust, seamless, production-ready, leverage, delve, tapestry,* and
  *best practices* with concrete descriptions of behavior,
  constraints, or trade-offs.
- **Coded Labels:** Write rules, options, and findings as plain
  imperatives. Don't tag them with codes like `[R1]`, `A1`, or
  `Option B` in artifacts a human reads — the reader shouldn't have to
  decode an index. Internal agent bookkeeping may use ids; shipped text
  may not.

### Preservation & Context

**When unsure, leave the text in place and ask.** Subjective cleanup
must never be a reason to remove load-bearing rationale.

- **Preserve the "Why":** You MUST NOT delete comments that document
  invariants, protocol constraints, platform quirks, security
  boundaries, and upstream workarounds.
- **Evidence is Immune:** Preserve exact counts, dates, and SHAs when
  they serve as evidence in benchmark results, release notes, stack
  traces, or lockfiles.
- **Behavior Over Inventory:** A useful description explains what
  changed for the *system or user*; it does not provide an inventory
  of files or functions the diff already shows.

### The Published-Release Test

Long-running branches accumulate tactical decisions — renames,
refactors, attempts-then-reverts. When deciding what counts as
branch-internal, use trunk or the parent branch as the baseline — not
intermediate states inside the current branch. Ask:

> Did users of the most recently published release ever experience
> this old name, old behavior, or bug?

If the answer is **no**, it is branch-internal narrative. Move it to
the commit message and describe only the final state in the artifact.

**Keep in shipped artifacts:**
- Deprecations and migration guides for symbols that actually shipped.
- `### Fixes` entries for bugs that affected users of a published
  release.
- Comments explaining *why the current code looks this way*
  (invariants, platform quirks) that make sense to a reader who never
  saw the previous version.

### Cleanup in Hindsight

When applying these rules retroactively from inside a feature branch,
first establish scope by diffing against the parent branch (or trunk)
to identify which commits this branch actually introduced. Then:

- **In-branch commits:** Prompt the user with two options: `fixup!`
  commits with `git rebase --autosquash` to address each causal commit
  at its source, or a single cleanup commit at branch tip.
- **Trunk/Parent commits:** Default to leaving them alone. Act only on
  explicit user instruction. If the user opts in, fold the cleanup
  into a single commit at branch tip; do not rewrite shared history.
- **Scope guard:** If cleaning prior slop would touch a colleague's
  work or expand the branch beyond its stated goal, stay in lane:
  protect the current goal and leave prior slop alone.

### Change Discipline

- Make the smallest coherent change that solves the verified problem;
  keep unrelated cleanup out of it.
- Reuse an existing file, component, helper, API, or test before adding
  a new one. Modify in place when the change fits the file's
  responsibility.
- Keep new APIs private until a caller outside the module needs them.
- Add a file only for a durable boundary — a distinct responsibility,
  independent reuse, or splitting an oversized high-touch module — not
  for a single-use helper or a one-line re-export.

### Keep Instructions Lean

Treat this file like code and prune it.

- Delete a line whose removal would not cause a mistake.
- Move multi-step procedures into skills, path-specific rules into
  nested AGENTS.md files, and hard limits into hooks or CI.
- Keep only non-obvious, broadly applicable defaults here. Anything a
  reader can infer from the code, a manifest, or a linter does not
  belong.
