import pathlib
import textwrap
import typing as t

import pytest

import _pytest.pytester

FixtureFileDict = t.Dict[str, str]


class PytestDocTestFinderFixture(t.NamedTuple):
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
        """
            )
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
        """
            )
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
        """
            )
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
        """
            )
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
        """
            )
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
        """
            )
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
        """
            )
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
        """
            )
        },
        tests_found=1,
    ),
]


@pytest.mark.parametrize(
    PytestDocTestFinderFixture._fields, FIXTURES, ids=[f.test_id for f in FIXTURES]
)
def test_pluginDocutilsDocTestFinder(
    pytester: _pytest.pytester.Pytester,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    test_id: str,
    files: FixtureFileDict,
    tests_found: int,
) -> None:
    # Initialize variables
    pytester.plugins = ["pytest_doctest_docutils"]
    pytester.makefile(".ini", pytest="[pytest]\naddopts=-p no:doctest -vv\n")
    tests_path = tmp_path / "tests"
    first_test_key = list(files.keys())[0]
    first_test_filename = str(tests_path / first_test_key)

    # Setup: Files
    tests_path.mkdir()
    for file_name, text in files.items():
        rst_file = tests_path / file_name
        rst_file.write_text(
            text,
            encoding="utf-8",
        )

    # Test
    result = pytester.runpytest(str(first_test_filename))
    result.assert_outcomes(passed=tests_found)
