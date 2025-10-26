"""Regression reproducer for https://github.com/git-pull/gp-libs/issues/48.

Docutils/myst-parser do not know about ``.. doctest::`` (or related) directives
until :func:`doctest_docutils.setup` registers them.  The Arch Linux packaging
environment executes ``pytest`` without importing our pytest plugin, so the
directives are missing and ``DocutilsDocTestFinder`` returns zero doctests.

These tests intentionally exercise that scenario by purging the docutils
directive registry before running the finder.
"""

from __future__ import annotations

import doctest
import textwrap
import typing as t

import pytest
from docutils.parsers.rst import directives

import doctest_docutils

if t.TYPE_CHECKING:
    import pathlib

FixtureFileDict = dict[str, str]


class GhIssue48Fixture(t.NamedTuple):
    """Test fixture for reproducing GH-48."""

    test_id: str
    files: FixtureFileDict
    tests_found: int


FIXTURES = [
    GhIssue48Fixture(
        test_id="reST-doctest_directive",
        files={
            "example.rst": textwrap.dedent(
                """
.. doctest::

   >>> 4 + 4
   8
                """,
            ),
        },
        tests_found=1,
    ),
    GhIssue48Fixture(
        test_id="MyST-doctest_directive-backticks",
        files={
            "example.md": textwrap.dedent(
                """
```{doctest}

    >>> 4 + 4
    8
```
                """,
            ),
        },
        tests_found=1,
    ),
    GhIssue48Fixture(
        test_id="MyST-doctest_block-python--sphinx-inline-tabs",
        files={
            "example.md": textwrap.dedent(
                """
````{tab} example tab
```python
>>> 4 + 4
8
```
````

````{tab} example second
```python
>>> 4 + 2
6
```
````
                """,
            ),
        },
        tests_found=2,
    ),
]


def _directive_registry() -> dict[str, t.Any]:
    """Return the docutils directive registry with typing hints."""
    # Access via __dict__ keeps Ruff happy and satisfies mypy with cast.
    return t.cast(dict[str, t.Any], directives.__dict__["_directives"])


@pytest.fixture()
def purge_doctest_directives() -> t.Iterator[None]:
    """Remove doctest-related directives to mimic Arch packaging env."""
    saved: dict[str, t.Any] = {}
    target_directives = ("doctest", "testsetup", "testcleanup", "tab")
    registry = _directive_registry()
    for name in target_directives:
        if name in registry:
            saved[name] = registry[name]
            registry.pop(name, None)
    try:
        yield
    finally:
        registry.update(saved)


@pytest.mark.parametrize(
    GhIssue48Fixture._fields,
    FIXTURES,
    ids=[fixture.test_id for fixture in FIXTURES],
)
@pytest.mark.parametrize("file_path_mode", ["relative", "absolute"])
@pytest.mark.xfail(
    reason="GH-48: directives are not registered unless doctest_docutils.setup() runs",
    strict=False,
)
def test_docutils_doctest_finder_without_registered_directives(
    purge_doctest_directives: None,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    test_id: str,
    files: FixtureFileDict,
    tests_found: int,
    file_path_mode: str,
) -> None:
    """Recreate Arch Linux failure by skipping doctest_docutils.setup()."""
    tests_path = tmp_path / "tests"
    tests_path.mkdir()
    first_test_key = next(iter(files.keys()))
    first_test_filename: str | pathlib.Path = first_test_key

    if file_path_mode == "absolute":
        first_test_filename = tests_path / first_test_filename
    elif file_path_mode != "relative":  # pragma: no cover - defensive guard
        error_message = f"Unsupported file_path_mode: {file_path_mode}"
        raise ValueError(error_message)

    for file_name, text in files.items():
        (tests_path / file_name).write_text(text, encoding="utf-8")

    if file_path_mode == "relative":
        monkeypatch.chdir(tests_path)

    finder = doctest_docutils.DocutilsDocTestFinder()
    text, _ = doctest._load_testfile(  # type: ignore[attr-defined]
        str(first_test_filename),
        package=None,
        module_relative=False,
        encoding="utf-8",
    )
    tests = finder.find(text, str(first_test_filename))
    tests.sort(key=lambda doctest_case: doctest_case.name)

    assert len(tests) == tests_found

    for test in tests:
        doctest.DebugRunner(verbose=False).run(test)
