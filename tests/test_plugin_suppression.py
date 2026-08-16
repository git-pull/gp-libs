"""Test pytest doctest collector composition and precedence.

Documentation paths have one owner while pytest's doctest plugin remains
available for Python modules and fixture injection.

Ref: pytest's test_pluginmanager.py patterns for plugin blocking tests.
"""

from __future__ import annotations

import importlib.metadata
import re
import textwrap
import typing as t

import _pytest.pytester
import pytest

# Parse pytest version for version-specific tests
PYTEST_VERSION = tuple(int(x) for x in pytest.__version__.split(".")[:2])


def test_pytest_entry_point_uses_adapter_name() -> None:
    """The installed plugin can be disabled by its module-shaped name."""
    entries = [
        entry
        for entry in importlib.metadata.entry_points(group="pytest11")
        if entry.value == "pytest_doctest_docutils"
    ]

    assert [entry.name for entry in entries] == ["pytest_doctest_docutils"]


def requires_pytest_version(
    min_version: tuple[int, int],
    reason: str,
) -> pytest.MarkDecorator:
    """Skip test if pytest version is below minimum.

    Parameters
    ----------
    min_version : tuple[int, int]
        Minimum (major, minor) pytest version required
    reason : str
        Description of the feature requiring this version

    Returns
    -------
    pytest.MarkDecorator
        A skipif marker for the test
    """
    return pytest.mark.skipif(
        min_version > PYTEST_VERSION,
        reason=f"Requires pytest {'.'.join(map(str, min_version))}+: {reason}",
    )


class PluginSuppressionCase(t.NamedTuple):
    """Test case for plugin suppression behavior."""

    test_id: str
    cli_args: list[str]
    ini_content: str
    expected_tests_collected: int
    description: str


PLUGIN_SUPPRESSION_CASES = [
    PluginSuppressionCase(
        test_id="composes-with-builtin-doctest",
        cli_args=["--collect-only", "-q"],
        ini_content="",
        expected_tests_collected=1,
        description="the adapter filters only the duplicate collector",
    ),
]


@pytest.mark.parametrize(
    PluginSuppressionCase._fields,
    PLUGIN_SUPPRESSION_CASES,
    ids=[c.test_id for c in PLUGIN_SUPPRESSION_CASES],
)
def test_collector_composition(
    pytester: _pytest.pytester.Pytester,
    test_id: str,
    cli_args: list[str],
    ini_content: str,
    expected_tests_collected: int,
    description: str,
) -> None:
    """Verify documentation paths collect exactly once."""
    pytester.plugins = ["pytest_doctest_docutils"]

    # Create pytest.ini if content provided
    if ini_content:
        pytester.makefile(
            ".ini",
            pytest=f"[pytest]\n{ini_content}",
        )

    # Create a simple doctest file
    pytester.makefile(
        ".rst",
        test_doc=textwrap.dedent(
            """
            Example
            =======

            >>> 1 + 1
            2
            """,
        ),
    )

    result = pytester.runpytest(*cli_args, "test_doc.rst")

    # Plugin should not error and should collect the expected tests
    result.assert_outcomes(errors=0)

    # Parse the "N test(s) collected" line from output
    stdout = result.stdout.str()
    match = re.search(r"(\d+) tests? collected", stdout)
    if match:
        tests_collected = int(match.group(1))
    else:
        # If no match, check for "no tests collected" case
        if "no tests collected" in stdout:
            tests_collected = 0
        else:
            pytest.fail(f"Could not parse test count from output:\n{stdout}")

    assert tests_collected == expected_tests_collected, (
        f"Expected {expected_tests_collected} tests, got {tests_collected}. "
        f"Output:\n{stdout}"
    )


class PluginDisableCase(t.NamedTuple):
    """Test case for disabling pytest_doctest_docutils."""

    test_id: str
    cli_args: list[str]
    expected_passed: int
    description: str


PLUGIN_DISABLE_CASES = [
    PluginDisableCase(
        test_id="disable-doctest-docutils-uses-builtin",
        cli_args=["-p", "no:pytest_doctest_docutils", "--doctest-modules"],
        expected_passed=1,
        description="Disabling pytest_doctest_docutils allows builtin doctest",
    ),
]


@pytest.mark.parametrize(
    PluginDisableCase._fields,
    PLUGIN_DISABLE_CASES,
    ids=[c.test_id for c in PLUGIN_DISABLE_CASES],
)
def test_plugin_disable(
    pytester: _pytest.pytester.Pytester,
    test_id: str,
    cli_args: list[str],
    expected_passed: int,
    description: str,
) -> None:
    """Test that pytest_doctest_docutils can be disabled.

    When disabled, the builtin doctest plugin should handle .py files.
    Note: .rst/.md files won't be collected by builtin doctest.
    """
    # Don't register pytest_doctest_docutils plugin
    # This simulates -p no:pytest_doctest_docutils

    # Create a .py file with doctest (builtin doctest handles these)
    pytester.makepyfile(
        test_module=textwrap.dedent(
            '''
            def hello():
                """Say hello.

                >>> hello()
                'hello'
                """
                return "hello"
            ''',
        ),
    )

    result = pytester.runpytest(*cli_args, "test_module.py")
    result.assert_outcomes(passed=expected_passed)


class PluginPrecedenceCase(t.NamedTuple):
    """Test case for plugin precedence behavior."""

    test_id: str
    cli_args: list[str]
    expected_passed: int
    description: str


PLUGIN_PRECEDENCE_CASES = [
    PluginPrecedenceCase(
        test_id="precedence-no-then-yes-reenables",
        cli_args=["-p", "no:doctest", "-p", "doctest", "--doctest-modules"],
        expected_passed=1,
        description="Ref pytest test_blocked_plugin_can_be_used: -p no:X -p X",
    ),
]


@pytest.mark.parametrize(
    PluginPrecedenceCase._fields,
    PLUGIN_PRECEDENCE_CASES,
    ids=[c.test_id for c in PLUGIN_PRECEDENCE_CASES],
)
def test_plugin_precedence(
    pytester: _pytest.pytester.Pytester,
    test_id: str,
    cli_args: list[str],
    expected_passed: int,
    description: str,
) -> None:
    """Test plugin precedence with -p no:X -p X patterns.

    Based on pytest's test_blocked_plugin_can_be_used (test_pluginmanager.py:478-483).
    When a plugin is blocked then re-enabled, it should be available.
    """
    pytester.plugins = ["pytest_doctest_docutils"]

    # Create a .py file
    pytester.makepyfile(
        test_module=textwrap.dedent(
            '''
            def hello():
                """Say hello.

                >>> hello()
                'hello'
                """
                return "hello"
            ''',
        ),
    )

    result = pytester.runpytest(*cli_args, "test_module.py")

    # Should work - the plugin system handles precedence
    result.assert_outcomes(passed=expected_passed)


def test_pytest_configure_keeps_doctest(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """The adapter keeps the built-in doctest plugin registered."""
    pytester.plugins = ["pytest_doctest_docutils"]

    pytester.makeconftest(
        textwrap.dedent(
            """
            import pytest

            @pytest.hookimpl(trylast=True)
            def pytest_configure(config):
                pm = config.pluginmanager
                config._doctest_was_blocked = pm.is_blocked('doctest')
                config._doctest_is_loaded = pm.has_plugin('doctest')

            @pytest.fixture
            def doctest_plugin_status(request):
                return (
                    request.config._doctest_was_blocked,
                    request.config._doctest_is_loaded,
                )
            """,
        ),
    )

    pytester.makepyfile(
        test_verify=textwrap.dedent(
            """
            def test_doctest_is_composed(doctest_plugin_status):
                blocked, loaded = doctest_plugin_status
                assert blocked is False
                assert loaded is True
            """,
        ),
    )

    result = pytester.runpytest("test_verify.py", "-v")
    result.assert_outcomes(passed=1)


class CollectorRoutingCase(t.NamedTuple):
    """Test case for file type collector routing."""

    test_id: str
    filename: str
    file_content: str
    expected_collector_type: str


COLLECTOR_ROUTING_CASES = [
    CollectorRoutingCase(
        test_id="py-uses-DoctestModule",
        filename="test_module.py",
        file_content=textwrap.dedent(
            '''
            def foo():
                """Foo function.

                >>> 1 + 1
                2
                """
                pass
            ''',
        ),
        expected_collector_type="DoctestModule",
    ),
    CollectorRoutingCase(
        test_id="rst-uses-DocTestDocutilsFile",
        filename="test_doc.rst",
        file_content=textwrap.dedent(
            """
            Example
            =======

            >>> 1 + 1
            2
            """,
        ),
        expected_collector_type="DocTestDocutilsFile",
    ),
    CollectorRoutingCase(
        test_id="md-uses-DocTestDocutilsFile",
        filename="test_doc.md",
        file_content=textwrap.dedent(
            """
            # Example

            ```python
            >>> 1 + 1
            2
            ```
            """,
        ),
        expected_collector_type="DocTestDocutilsFile",
    ),
]


@pytest.mark.parametrize(
    CollectorRoutingCase._fields,
    COLLECTOR_ROUTING_CASES,
    ids=[c.test_id for c in COLLECTOR_ROUTING_CASES],
)
def test_collector_routing(
    pytester: _pytest.pytester.Pytester,
    test_id: str,
    filename: str,
    file_content: str,
    expected_collector_type: str,
) -> None:
    """Test that file types are routed to the correct collector.

    - .py files should use DoctestModule (from _pytest.doctest)
    - .rst/.md files should use DocTestDocutilsFile (from pytest_doctest_docutils)
    """
    pytester.plugins = ["pytest_doctest_docutils"]
    pytester.makefile(
        ".ini",
        pytest="[pytest]\naddopts=-vv",
    )

    # Create the test file
    file_path = pytester.path / filename
    file_path.write_text(file_content, encoding="utf-8")

    # Use --collect-only to see collection info
    result = pytester.runpytest(
        "--collect-only",
        "--doctest-docutils-modules",
        str(file_path),
    )

    stdout = result.stdout.str()

    # Verify the expected collector type appears in output
    assert expected_collector_type in stdout, (
        f"Expected collector {expected_collector_type} not found in output:\n{stdout}"
    )


# pytest 8.4+ version-specific tests


@requires_pytest_version((8, 4), "--disable-plugin-autoload flag")
def test_disable_plugin_autoload_flag(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """Test --disable-plugin-autoload CLI flag in pytest 8.4+.

    Verifies that the --disable-plugin-autoload flag is recognized and
    prevents automatic plugin loading via entry points.

    Ref: pytest 8.4.0 changelog - --disable-plugin-autoload CLI flag
    """
    # Create a simple test file
    pytester.makepyfile(
        test_simple=textwrap.dedent(
            """
            def test_pass():
                assert True
            """,
        ),
    )

    # Test that the flag is recognized (doesn't error)
    result = pytester.runpytest(
        "--disable-plugin-autoload",
        "-p",
        "pytest_doctest_docutils",
        "test_simple.py",
        "-v",
    )

    # Should succeed - the flag should be recognized
    result.assert_outcomes(passed=1)


@requires_pytest_version((8, 4), "--disable-plugin-autoload flag")
def test_disable_plugin_autoload_with_explicit_plugin(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """Test --disable-plugin-autoload with explicit plugin loading.

    When --disable-plugin-autoload is used, only explicitly specified
    plugins via -p should be loaded.

    Ref: pytest 8.4.0 changelog - --disable-plugin-autoload CLI flag
    """
    pytester.plugins = ["pytest_doctest_docutils"]

    # Create a doctest file
    pytester.makefile(
        ".rst",
        test_doc=textwrap.dedent(
            """
            Example
            =======

            >>> 1 + 1
            2
            """,
        ),
    )

    # With --disable-plugin-autoload, explicitly load our plugin
    result = pytester.runpytest(
        "--disable-plugin-autoload",
        "-p",
        "pytest_doctest_docutils",
        "test_doc.rst",
        "-v",
    )

    # Should find and run the doctest
    result.assert_outcomes(passed=1)
