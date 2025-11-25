"""Regression test for autouse fixtures with doctest files.

Backported from pytest commit 9cd14b4ff (2024-02-06).
https://github.com/pytest-dev/pytest/commit/9cd14b4ff

The original pytest test verified autouse fixtures defined in the same .py module
as the doctest get picked up properly. For gp-libs, DocTestDocutilsFile handles
.rst/.md files where fixtures can only come from conftest.py (not from the
document itself).

This test verifies that autouse fixtures from conftest.py are properly discovered
for .rst and .md doctest files across different fixture scopes.

Refs: pytest-dev/pytest#11929
"""

from __future__ import annotations

import textwrap
import typing as t

import _pytest.pytester
import pytest


class AutouseFixtureTestCase(t.NamedTuple):
    """Test fixture for autouse fixtures with doctest files."""

    test_id: str
    scope: str
    file_ext: str
    file_content: str


RST_DOCTEST_CONTENT = textwrap.dedent(
    """
Example
=======

.. doctest::

   >>> get_value()
   'fixture ran'
    """,
)

MD_DOCTEST_CONTENT = textwrap.dedent(
    """
# Example

```{doctest}
>>> get_value()
'fixture ran'
```
    """,
)

SCOPES = ["module", "session", "class", "function"]

FIXTURES = [
    AutouseFixtureTestCase(
        test_id=f"{scope}-rst",
        scope=scope,
        file_ext=".rst",
        file_content=RST_DOCTEST_CONTENT,
    )
    for scope in SCOPES
] + [
    AutouseFixtureTestCase(
        test_id=f"{scope}-md",
        scope=scope,
        file_ext=".md",
        file_content=MD_DOCTEST_CONTENT,
    )
    for scope in SCOPES
]


@pytest.mark.parametrize(
    AutouseFixtureTestCase._fields,
    FIXTURES,
    ids=[f.test_id for f in FIXTURES],
)
def test_autouse_fixtures_with_doctest_files(
    pytester: _pytest.pytester.Pytester,
    test_id: str,
    scope: str,
    file_ext: str,
    file_content: str,
) -> None:
    """Autouse fixtures from conftest.py work with .rst/.md doctest files.

    Regression test for pytest-dev/pytest#11929.
    Backported from pytest commit 9cd14b4ff (2024-02-06).
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

    # Create conftest with autouse fixture that sets a global value
    pytester.makeconftest(
        textwrap.dedent(
            f"""
import pytest

VALUE = "fixture did not run"

@pytest.fixture(autouse=True, scope="{scope}")
def set_value():
    global VALUE
    VALUE = "fixture ran"

@pytest.fixture(autouse=True)
def add_get_value_to_doctest_namespace(doctest_namespace):
    def get_value():
        return VALUE
    doctest_namespace["get_value"] = get_value
            """,
        ),
    )

    # Create the doctest file
    tests_path = pytester.path / "tests"
    tests_path.mkdir()
    test_file = tests_path / f"example{file_ext}"
    test_file.write_text(file_content, encoding="utf-8")

    result = pytester.runpytest(str(test_file))
    result.assert_outcomes(passed=1)
