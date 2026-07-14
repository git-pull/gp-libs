"""Test pytest plugin for doctest_docutils."""

from __future__ import annotations

import textwrap
import typing as t

import pytest

if t.TYPE_CHECKING:
    import _pytest.pytester

FixtureFileDict = dict[str, str]


class PytestDocTestFinderFixture(t.NamedTuple):
    """Pytest fixture for DocTestFinder."""

    # pytest
    test_id: str

    # Content
    files: FixtureFileDict
    tests_found: int


FIXTURES = [
    #
    # Docutils
    #
    PytestDocTestFinderFixture(
        test_id="reST-doctest_block",
        files={
            "example.rst": textwrap.dedent(
                """
>>> 4 + 4
8
        """,
            ),
        },
        tests_found=1,
    ),
    PytestDocTestFinderFixture(
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
    #
    # Markdown / myst-parser
    #
    PytestDocTestFinderFixture(
        test_id="MyST-doctest_block",
        files={
            "example.md": textwrap.dedent(
                """
```
>>> 4 + 4
8
```
        """,
            ),
        },
        tests_found=1,
    ),
    PytestDocTestFinderFixture(
        test_id="MyST-doctest_block-indented",
        files={
            "example.md": textwrap.dedent(
                """
Here's a test:

    >>> 4 + 4
    8
        """,
            ),
        },
        tests_found=1,
    ),
    PytestDocTestFinderFixture(
        test_id="MyST-doctest_directive-colons",
        files={
            "example.md": textwrap.dedent(
                """
:::{doctest}

    >>> 4 + 4
    8
:::
        """,
            ),
        },
        tests_found=1,
    ),
    PytestDocTestFinderFixture(
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
    PytestDocTestFinderFixture(
        test_id="MyST-doctest_directive-eval-rst-colons",
        files={
            "example.md": textwrap.dedent(
                """
:::{eval-rst}

   .. doctest::

      >>> 4 + 4
      8
:::
        """,
            ),
        },
        tests_found=1,
    ),
    PytestDocTestFinderFixture(
        test_id="MyST-doctest_directive-eval-rst-backticks",
        files={
            "example.md": textwrap.dedent(
                """
```{eval-rst}

   .. doctest::

      >>> 4 + 4
      8
```
        """,
            ),
        },
        tests_found=1,
    ),
    #
    # .py should still work
    #
    PytestDocTestFinderFixture(
        test_id="python-reST-doctest_block",
        files={
            "example.py": textwrap.dedent(
                """
def hello(statement: str) -> None:
    '''Say hello.

    >>> hello(f'hello world {2 * 3}')
    hello world 6
    '''
    print(statement)

        """,
            ),
        },
        tests_found=1,
    ),
    # sphinx-inline-tabs
    PytestDocTestFinderFixture(
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


@pytest.mark.parametrize(
    PytestDocTestFinderFixture._fields,
    FIXTURES,
    ids=[f.test_id for f in FIXTURES],
)
def test_pluginDocutilsDocTestFinder(
    pytester: _pytest.pytester.Pytester,
    test_id: str,
    files: FixtureFileDict,
    tests_found: int,
) -> None:
    """Verify DocTestFinder's collection of doctests."""
    # Initialize variables
    pytester.plugins = ["pytest_doctest_docutils"]
    pytester.makefile(
        ".ini",
        pytest=textwrap.dedent(
            """
[pytest]
addopts=-p no:doctest -vv

        """.strip(),
        ),
    )
    tests_path = pytester.path / "tests"
    first_test_key = next(iter(files.keys()))
    first_test_filename = str(tests_path / first_test_key)

    # Setup Files
    tests_path.mkdir()
    for file_name, text in files.items():
        rst_file = tests_path / file_name
        rst_file.write_text(
            text,
            encoding="utf-8",
        )

    # Test
    result = pytester.runpytest(str(first_test_filename), "--doctest-docutils-modules")
    result.assert_outcomes(passed=tests_found)


def test_conftest_py(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """Test pytest plugin with python file doctests."""
    # Initialize variables
    pytester.plugins = ["pytest_doctest_docutils"]
    pytester.makefile(
        ".ini",
        pytest=textwrap.dedent(
            """
[pytest]
addopts=-p no:doctest -vv

        """.strip(),
        ),
    )
    pytester.makeconftest(
        textwrap.dedent(
            r"""
from typing import Any, Dict
import pathlib
import pytest
from _pytest.fixtures import SubRequest

@pytest.fixture(autouse=True)
def add_doctest_fixtures(
    request: SubRequest,
    doctest_namespace: Dict[str, Any],
    tmp_path: pathlib.Path,
):
    def add(a: int, b: int) -> int:
        return a + b
    doctest_namespace["add"] = add
    """,
        ),
    )
    tests_path = pytester.path / "tests"
    files = {
        "example.py": textwrap.dedent(
            """
def hello(statement: str) -> None:
    '''Say hello.

    >>> hello(add(1, 2))
    3
    '''
    print(statement)

        """,
        ),
    }
    first_test_key = next(iter(files.keys()))
    first_test_filename = str(tests_path / first_test_key)

    # Setup Files
    tests_path.mkdir()
    for file_name, text in files.items():
        rst_file = tests_path / file_name
        rst_file.write_text(
            text,
            encoding="utf-8",
        )

    result = pytester.runpytest(str(first_test_filename), "--doctest-modules")
    result.assert_outcomes(passed=1)

    # Test
    result = pytester.runpytest(str(first_test_filename), "--doctest-docutils-modules")
    result.assert_outcomes(passed=1)


def test_conftest_md(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """Test pytest plugin with doctests in markdown."""
    # Initialize variables
    pytester.plugins = ["pytest_doctest_docutils"]
    pytester.makefile(
        ".ini",
        pytest=textwrap.dedent(
            """
[pytest]
addopts=-p no:doctest -vv

        """.strip(),
        ),
    )
    pytester.makeconftest(
        textwrap.dedent(
            r"""
from typing import Any, Dict
import pathlib
import pytest
from _pytest.fixtures import SubRequest

@pytest.fixture(autouse=True)
def add_doctest_fixtures(
    request: SubRequest,
    doctest_namespace: Dict[str, Any],
    tmp_path: pathlib.Path,
):
    def add(a: int, b: int) -> int:
        return a + b
    doctest_namespace["add"] = add
    """,
        ),
    )
    tests_path = pytester.path / "tests"
    files = {
        "example.md": textwrap.dedent(
            """
```python
>>> def hello(statement: str) -> None:
...     '''Say hello.'''
...     print(statement)
>>> hello(add(1, 2))
3
```

Anything else to say?

```python
>>> new_var = 3 + 3
>>> add(new_var, 0)
6
```

The latest:
```python
>>> add = lambda a, b: a + b
>>> add(5, 1)
6
```

The rest:
```python
>>> add = lambda a, b: a + b
>>> add(5, 1)
6
```
        """,
        ),
    }
    first_test_key = next(iter(files.keys()))
    first_test_filename = str(tests_path / first_test_key)

    # Setup Files
    tests_path.mkdir()
    for file_name, text in files.items():
        md_file = tests_path / file_name
        md_file.write_text(
            text,
            encoding="utf-8",
        )

    result = pytester.runpytest(str(first_test_filename), "--doctest-modules")
    result.assert_outcomes(passed=4)

    # Test
    result = pytester.runpytest(str(first_test_filename), "--doctest-docutils-modules")
    result.assert_outcomes(passed=4)


class IgnoreBuildFixture(t.NamedTuple):
    """Fixture for Sphinx ``_build/`` collection-ignore tests."""

    test_id: str

    # Path (relative to ``docs/``) of the build artifact that must be ignored.
    artifact_path: str


IGNORE_BUILD_FIXTURES = [
    IgnoreBuildFixture(test_id="build-root", artifact_path="_build/history.md"),
    IgnoreBuildFixture(
        test_id="build-html-subdir",
        artifact_path="_build/html/history.md",
    ),
]


@pytest.mark.parametrize(
    IgnoreBuildFixture._fields,
    IGNORE_BUILD_FIXTURES,
    ids=[f.test_id for f in IGNORE_BUILD_FIXTURES],
)
def test_ignore_build_artifacts(
    pytester: _pytest.pytester.Pytester,
    test_id: str,
    artifact_path: str,
) -> None:
    """Sphinx build artifacts under ``_build/`` are skipped during collection.

    Sphinx copies sources into ``docs/_build/`` verbatim, keeping relative
    ``{include}`` directives that no longer resolve from the build tree. Those
    copies must not be collected, otherwise the broken include aborts the whole
    session with a docutils ``SystemMessage`` during collection.
    """
    pytester.plugins = ["pytest_doctest_docutils"]
    pytester.makefile(
        ".ini",
        pytest=textwrap.dedent(
            """
[pytest]
addopts=-p no:doctest -vv

        """.strip(),
        ),
    )
    docs_path = pytester.path / "docs"
    docs_path.mkdir()

    # A genuine source doctest that should still be collected.
    (docs_path / "example.md").write_text(
        textwrap.dedent(
            """
```
>>> 4 + 4
8
```
        """,
        ),
        encoding="utf-8",
    )

    # A build artifact whose relative include cannot resolve.
    artifact = docs_path / artifact_path
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(
        textwrap.dedent(
            """
```{include} ../CHANGES

```
        """,
        ),
        encoding="utf-8",
    )

    result = pytester.runpytest(str(docs_path), "--doctest-docutils-modules")
    result.assert_outcomes(passed=1)


def test_hide_optionflag_py_docstring(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """``# doctest: +HIDE`` parses and runs as a no-op in a .py docstring.

    ``HIDE`` is registered so documentation tooling can mark a setup example to
    drop from rendered output. Without the registration, collection would raise
    ``ValueError: ... invalid option: '+HIDE'``. Here it must simply run.
    """
    pytester.plugins = ["pytest_doctest_docutils"]
    pytester.makefile(
        ".ini",
        pytest=textwrap.dedent(
            """
[pytest]
addopts=-p no:doctest
        """.strip(),
        ),
    )
    example = pytester.path / "example.py"
    example.write_text(
        textwrap.dedent(
            '''
def demo() -> int:
    """Return a computed value.

    >>> base = 40  # doctest: +HIDE
    >>> base + 2
    42
    """
    return 42
        ''',
        ),
        encoding="utf-8",
    )

    result = pytester.runpytest(str(example), "--doctest-docutils-modules")
    result.assert_outcomes(passed=1)
