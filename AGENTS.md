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

### Git Commit Standards

See `.cursor/rules/git-commits.mdc` for detailed commit message standards.

Format commit messages as:
```
Component/File(commit-type[Subcomponent/method]): Concise description

why: Explanation of necessity or impact.
what:
- Specific technical changes made
- Focused on a single topic
```

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
- **ai(rules[LLM type])**: AI Rule Updates

Example:
```
doctest_docutils(feat[parse]): Add support for myst-parser code blocks

why: Enable doctest execution in Markdown documentation files
what:
- Add detection for ```{doctest} fence syntax
- Register myst directives automatically
- Add tests for Markdown doctest parsing
```
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
