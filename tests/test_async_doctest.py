"""Tests for async doctest support.

These tests verify that top-level await works in doctests without requiring
asyncio.run() boilerplate. Tests cover both RST and Markdown formats.
"""

from __future__ import annotations

import textwrap
import typing as t

import _pytest.pytester
import pytest

from doctest_docutils import AsyncDocTestRunner, DocutilsDocTestFinder

if t.TYPE_CHECKING:
    import pathlib

# Type alias for fixture file content
FixtureFileDict = dict[str, str]


# =============================================================================
# Fixtures: Basic async doctests
# =============================================================================


class AsyncDoctestFixture(t.NamedTuple):
    """Test fixture for async doctest functionality."""

    test_id: str
    file_ext: str
    content: str
    expected_passed: int


def _rst_content(body: str) -> str:
    """Wrap doctest body in RST format.

    Parameters
    ----------
    body : str
        The doctest example code to embed

    Returns
    -------
    str
        RST document with title and doctest body
    """
    return f"""\
Test
====

{body}
"""


def _md_content(body: str) -> str:
    """Wrap doctest body in Markdown format.

    Parameters
    ----------
    body : str
        The doctest example code to embed

    Returns
    -------
    str
        Markdown document with heading and fenced code block
    """
    return f"""\
# Test

```python
{body}
```
"""


# Doctest bodies (format-agnostic)
TOP_LEVEL_AWAIT_BODY = """\
>>> import asyncio
>>> await asyncio.sleep(0)
>>> 1 + 1
2"""

ASYNC_RETURN_VALUE_BODY = """\
>>> import asyncio
>>> async def get_value():
...     await asyncio.sleep(0)
...     return 42
>>> await get_value()
42"""

MIXED_SYNC_ASYNC_BODY = """\
>>> x = 1
>>> import asyncio
>>> await asyncio.sleep(0)
>>> x + 1
2
>>> y = await asyncio.sleep(0) or 10
>>> y
10"""

STATE_PERSISTENCE_BODY = """\
>>> import asyncio
>>> async def set_value():
...     global shared_value
...     await asyncio.sleep(0)
...     shared_value = 'hello'
>>> await set_value()
>>> shared_value
'hello'"""

ASYNC_CONTEXT_MANAGER_BODY = """\
>>> import asyncio
>>> class AsyncCM:
...     async def __aenter__(self):
...         await asyncio.sleep(0)
...         return 'entered'
...     async def __aexit__(self, *args):
...         await asyncio.sleep(0)
>>> async with AsyncCM() as value:
...     print(value)
entered"""

ASYNC_FOR_BODY = """\
>>> import asyncio
>>> async def async_range(n):
...     for i in range(n):
...         await asyncio.sleep(0)
...         yield i
>>> result = []
>>> async for x in async_range(3):
...     result.append(x)
>>> result
[0, 1, 2]"""

ASYNC_COMPREHENSION_BODY = """\
>>> import asyncio
>>> async def async_range(n):
...     for i in range(n):
...         await asyncio.sleep(0)
...         yield i
>>> [x async for x in async_range(3)]
[0, 1, 2]"""

EXPECTED_EXCEPTION_BODY = """\
>>> import asyncio
>>> async def raise_error():
...     await asyncio.sleep(0)
...     raise ValueError('test error')
>>> await raise_error()
Traceback (most recent call last):
    ...
ValueError: test error"""

SYNC_CODE_BODY = """\
>>> 1 + 1
2
>>> x = 'hello'
>>> x.upper()
'HELLO'"""


BASIC_ASYNC_FIXTURES: list[AsyncDoctestFixture] = [
    # Top-level await
    AsyncDoctestFixture(
        test_id="top-level-await-rst",
        file_ext=".rst",
        content=_rst_content(TOP_LEVEL_AWAIT_BODY),
        expected_passed=3,
    ),
    AsyncDoctestFixture(
        test_id="top-level-await-md",
        file_ext=".md",
        content=_md_content(TOP_LEVEL_AWAIT_BODY),
        expected_passed=3,
    ),
    # Async return value
    AsyncDoctestFixture(
        test_id="async-return-value-rst",
        file_ext=".rst",
        content=_rst_content(ASYNC_RETURN_VALUE_BODY),
        expected_passed=3,
    ),
    AsyncDoctestFixture(
        test_id="async-return-value-md",
        file_ext=".md",
        content=_md_content(ASYNC_RETURN_VALUE_BODY),
        expected_passed=3,
    ),
    # Mixed sync/async
    AsyncDoctestFixture(
        test_id="mixed-sync-async-rst",
        file_ext=".rst",
        content=_rst_content(MIXED_SYNC_ASYNC_BODY),
        expected_passed=6,
    ),
    AsyncDoctestFixture(
        test_id="mixed-sync-async-md",
        file_ext=".md",
        content=_md_content(MIXED_SYNC_ASYNC_BODY),
        expected_passed=6,
    ),
    # State persistence
    AsyncDoctestFixture(
        test_id="state-persistence-rst",
        file_ext=".rst",
        content=_rst_content(STATE_PERSISTENCE_BODY),
        expected_passed=4,
    ),
    AsyncDoctestFixture(
        test_id="state-persistence-md",
        file_ext=".md",
        content=_md_content(STATE_PERSISTENCE_BODY),
        expected_passed=4,
    ),
    # Sync code still works
    AsyncDoctestFixture(
        test_id="sync-code-rst",
        file_ext=".rst",
        content=_rst_content(SYNC_CODE_BODY),
        expected_passed=3,
    ),
    AsyncDoctestFixture(
        test_id="sync-code-md",
        file_ext=".md",
        content=_md_content(SYNC_CODE_BODY),
        expected_passed=3,
    ),
]

ADVANCED_ASYNC_FIXTURES: list[AsyncDoctestFixture] = [
    # Async context manager
    AsyncDoctestFixture(
        test_id="async-context-manager-rst",
        file_ext=".rst",
        content=_rst_content(ASYNC_CONTEXT_MANAGER_BODY),
        expected_passed=3,
    ),
    AsyncDoctestFixture(
        test_id="async-context-manager-md",
        file_ext=".md",
        content=_md_content(ASYNC_CONTEXT_MANAGER_BODY),
        expected_passed=3,
    ),
    # Async for
    AsyncDoctestFixture(
        test_id="async-for-rst",
        file_ext=".rst",
        content=_rst_content(ASYNC_FOR_BODY),
        expected_passed=5,
    ),
    AsyncDoctestFixture(
        test_id="async-for-md",
        file_ext=".md",
        content=_md_content(ASYNC_FOR_BODY),
        expected_passed=5,
    ),
    # Async comprehension
    AsyncDoctestFixture(
        test_id="async-comprehension-rst",
        file_ext=".rst",
        content=_rst_content(ASYNC_COMPREHENSION_BODY),
        expected_passed=3,
    ),
    AsyncDoctestFixture(
        test_id="async-comprehension-md",
        file_ext=".md",
        content=_md_content(ASYNC_COMPREHENSION_BODY),
        expected_passed=3,
    ),
    # Expected exception
    AsyncDoctestFixture(
        test_id="expected-exception-rst",
        file_ext=".rst",
        content=_rst_content(EXPECTED_EXCEPTION_BODY),
        expected_passed=3,
    ),
    AsyncDoctestFixture(
        test_id="expected-exception-md",
        file_ext=".md",
        content=_md_content(EXPECTED_EXCEPTION_BODY),
        expected_passed=3,
    ),
]


# =============================================================================
# Fixtures: Plugin integration tests
# =============================================================================


class AsyncPluginFixture(t.NamedTuple):
    """Test fixture for async doctest pytest plugin integration."""

    test_id: str
    file_ext: str
    content: str
    expected_passed: int


PLUGIN_FIXTURES: list[AsyncPluginFixture] = [
    AsyncPluginFixture(
        test_id="plugin-async-rst",
        file_ext=".rst",
        content=_rst_content(TOP_LEVEL_AWAIT_BODY),
        expected_passed=1,  # One doctest file
    ),
    AsyncPluginFixture(
        test_id="plugin-async-md",
        file_ext=".md",
        content=_md_content(TOP_LEVEL_AWAIT_BODY),
        expected_passed=1,
    ),
]


# =============================================================================
# Tests: Basic async doctests using run_doctest_docutils
# =============================================================================


@pytest.mark.parametrize(
    AsyncDoctestFixture._fields,
    BASIC_ASYNC_FIXTURES,
    ids=[f.test_id for f in BASIC_ASYNC_FIXTURES],
)
def test_async_doctest_basic(
    tmp_path: pathlib.Path,
    test_id: str,
    file_ext: str,
    content: str,
    expected_passed: int,
) -> None:
    """Test basic async doctest functionality with top-level await."""
    doc = tmp_path / f"test{file_ext}"
    doc.write_text(content)

    finder = DocutilsDocTestFinder()
    runner = AsyncDocTestRunner(verbose=False)

    text = doc.read_text()
    total_attempted = 0
    total_failed = 0

    for test in finder.find(text, str(doc)):
        result = runner.run(test)
        total_attempted += result.attempted
        total_failed += result.failed

    assert total_failed == 0, f"Expected no failures, got {total_failed}"
    assert total_attempted == expected_passed, (
        f"Expected {expected_passed} examples, got {total_attempted}"
    )


@pytest.mark.parametrize(
    AsyncDoctestFixture._fields,
    ADVANCED_ASYNC_FIXTURES,
    ids=[f.test_id for f in ADVANCED_ASYNC_FIXTURES],
)
def test_async_doctest_advanced(
    tmp_path: pathlib.Path,
    test_id: str,
    file_ext: str,
    content: str,
    expected_passed: int,
) -> None:
    """Test advanced async doctest scenarios."""
    doc = tmp_path / f"test{file_ext}"
    doc.write_text(content)

    finder = DocutilsDocTestFinder()
    runner = AsyncDocTestRunner(verbose=False)

    text = doc.read_text()
    total_attempted = 0
    total_failed = 0

    for test in finder.find(text, str(doc)):
        result = runner.run(test)
        total_attempted += result.attempted
        total_failed += result.failed

    assert total_failed == 0, f"Expected no failures, got {total_failed}"
    assert total_attempted == expected_passed, (
        f"Expected {expected_passed} examples, got {total_attempted}"
    )


# =============================================================================
# Tests: Plugin integration using pytester
# =============================================================================


@pytest.mark.parametrize(
    AsyncPluginFixture._fields,
    PLUGIN_FIXTURES,
    ids=[f.test_id for f in PLUGIN_FIXTURES],
)
def test_async_doctest_plugin(
    pytester: _pytest.pytester.Pytester,
    test_id: str,
    file_ext: str,
    content: str,
    expected_passed: int,
) -> None:
    """Test async doctest collection and execution via pytest plugin."""
    pytester.plugins = ["pytest_doctest_docutils"]
    pytester.makefile(
        ".ini",
        pytest=textwrap.dedent("""
            [pytest]
            addopts = --doctest-glob=*.rst --doctest-glob=*.md
        """),
    )

    # Create test file
    test_file = pytester.path / f"test{file_ext}"
    test_file.write_text(content)

    result = pytester.runpytest(str(test_file))
    result.assert_outcomes(passed=expected_passed)


def test_async_doctest_plugin_with_conftest(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """Test async doctest with conftest fixtures via pytest plugin."""
    pytester.plugins = ["pytest_doctest_docutils"]
    pytester.makefile(
        ".ini",
        pytest=textwrap.dedent("""
            [pytest]
            addopts = --doctest-glob=*.rst --doctest-glob=*.md
        """),
    )

    # Create conftest with doctest_namespace fixture
    pytester.makeconftest(
        textwrap.dedent("""
            import asyncio
            import pytest

            @pytest.fixture(autouse=True)
            def add_doctest_fixtures(doctest_namespace):
                async def async_add(a, b):
                    await asyncio.sleep(0)
                    return a + b
                doctest_namespace["async_add"] = async_add
                doctest_namespace["asyncio"] = asyncio
        """),
    )

    # Create test file using the fixture
    test_content = _rst_content("""\
>>> result = await async_add(2, 3)
>>> result
5""")

    test_file = pytester.path / "test.rst"
    test_file.write_text(test_content)

    result = pytester.runpytest(str(test_file))
    result.assert_outcomes(passed=1)


def test_async_doctest_plugin_failure_reporting(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """Test that async doctest failures are properly reported."""
    pytester.plugins = ["pytest_doctest_docutils"]
    pytester.makefile(
        ".ini",
        pytest=textwrap.dedent("""
            [pytest]
            addopts = --doctest-glob=*.rst
        """),
    )

    # Create test file with intentional failure
    test_content = _rst_content("""\
>>> import asyncio
>>> async def wrong():
...     await asyncio.sleep(0)
...     return 999
>>> await wrong()
42""")

    test_file = pytester.path / "test.rst"
    test_file.write_text(test_content)

    result = pytester.runpytest(str(test_file))
    result.assert_outcomes(failed=1)


# =============================================================================
# Tests: Direct AsyncDocTestRunner usage
# =============================================================================


def test_async_runner_state_persists(tmp_path: pathlib.Path) -> None:
    """Test that state persists across async examples in same DocTest block."""
    doc = tmp_path / "test.rst"
    doc.write_text("""\
>>> import asyncio
>>> counter = 0
>>> async def increment():
...     global counter
...     await asyncio.sleep(0)
...     counter += 1
>>> await increment()
>>> await increment()
>>> counter
2
""")

    finder = DocutilsDocTestFinder()
    runner = AsyncDocTestRunner(verbose=False)

    text = doc.read_text()
    for test in finder.find(text, str(doc)):
        result = runner.run(test)
        assert result.failed == 0, "State should persist across examples"


def test_async_runner_handles_sync_and_async(tmp_path: pathlib.Path) -> None:
    """Test that sync and async code both work correctly."""
    doc = tmp_path / "test.rst"
    doc.write_text("""\
>>> sync_value = 'hello'
>>> import asyncio
>>> async def async_upper(s):
...     await asyncio.sleep(0)
...     return s.upper()
>>> await async_upper(sync_value)
'HELLO'
>>> sync_value
'hello'
""")

    finder = DocutilsDocTestFinder()
    runner = AsyncDocTestRunner(verbose=False)

    text = doc.read_text()
    for test in finder.find(text, str(doc)):
        result = runner.run(test)
        assert result.failed == 0, "Both sync and async should work"
