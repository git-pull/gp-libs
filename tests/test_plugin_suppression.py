"""Test pytest plugin suppression and precedence.

Tests for pytest plugin blocking behavior in pytest_doctest_docutils.
Ensures plugin suppression works correctly across pytest 7.x/8.x/9.x.

Ref: pytest's test_pluginmanager.py patterns for plugin blocking tests.
"""

from __future__ import annotations

import re
import textwrap
import typing as t

import _pytest.pytester
import pytest

# Parse pytest version for version-specific tests
PYTEST_VERSION = tuple(int(x) for x in pytest.__version__.split(".")[:2])


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
        test_id="auto-blocks-builtin-doctest",
        cli_args=["--collect-only", "-q"],
        ini_content="",
        expected_tests_collected=1,
        description="pytest_doctest_docutils auto-blocks built-in doctest",
    ),
    PluginSuppressionCase(
        test_id="ini-addopts-no-doctest",
        cli_args=["--collect-only", "-q"],
        ini_content="addopts = -p no:doctest",
        expected_tests_collected=1,
        description="addopts=-p no:doctest in pytest.ini works",
    ),
]


@pytest.mark.parametrize(
    PluginSuppressionCase._fields,
    PLUGIN_SUPPRESSION_CASES,
    ids=[c.test_id for c in PLUGIN_SUPPRESSION_CASES],
)
def test_plugin_suppression(
    pytester: _pytest.pytester.Pytester,
    test_id: str,
    cli_args: list[str],
    ini_content: str,
    expected_tests_collected: int,
    description: str,
) -> None:
    """Test plugin suppression behavior.

    Verifies that pytest_doctest_docutils correctly blocks the built-in
    doctest plugin to prevent duplicate test collection.
    """
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


def test_pytest_configure_blocks_doctest(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """Test that pytest_configure automatically blocks the doctest plugin.

    This tests the core behavior in pytest_doctest_docutils.pytest_configure:
        if config.pluginmanager.has_plugin("doctest"):
            config.pluginmanager.set_blocked("doctest")
    """
    pytester.plugins = ["pytest_doctest_docutils"]

    # Create conftest that checks plugin state after configuration
    pytester.makeconftest(
        textwrap.dedent(
            """
            import pytest

            @pytest.hookimpl(trylast=True)
            def pytest_configure(config):
                # After all pytest_configure hooks run, doctest should be blocked
                pm = config.pluginmanager
                # is_blocked exists in pytest 7+
                if hasattr(pm, 'is_blocked'):
                    # Store result for test to check
                    config._doctest_was_blocked = pm.is_blocked('doctest')
                else:
                    config._doctest_was_blocked = None

            @pytest.fixture
            def doctest_blocked_status(request):
                return getattr(request.config, '_doctest_was_blocked', None)
            """,
        ),
    )

    # Create test that verifies the blocking happened
    pytester.makepyfile(
        test_verify=textwrap.dedent(
            """
            def test_doctest_was_blocked(doctest_blocked_status):
                if doctest_blocked_status is not None:
                    assert doctest_blocked_status is True, (
                        "doctest plugin should be blocked by pytest_doctest_docutils"
                    )
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
        pytest="[pytest]\naddopts=-p no:doctest -vv",
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


# pytest 8.1+ version-specific tests


@requires_pytest_version((8, 1), "pluginmanager.unblock() API")
def test_unblock_api_available(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """Test pluginmanager.unblock() API available in pytest 8.1+.

    Verifies that the unblock() method exists and can be used to
    re-enable a previously blocked plugin.

    Ref: pytest 8.1.0 changelog - pluginmanager.unblock() public API
    """
    pytester.plugins = ["pytest_doctest_docutils"]

    # Create conftest that tests unblock API
    pytester.makeconftest(
        textwrap.dedent(
            """
            import pytest

            @pytest.hookimpl(trylast=True)
            def pytest_configure(config):
                pm = config.pluginmanager

                # Verify unblock method exists
                assert hasattr(pm, 'unblock'), "unblock() API not found"

                # doctest should be blocked by pytest_doctest_docutils
                assert pm.is_blocked('doctest'), "doctest should be blocked"

                # Test unblock API
                result = pm.unblock('doctest')

                # Store results for test verification
                config._unblock_api_exists = True
                config._unblock_result = result
                config._doctest_unblocked = not pm.is_blocked('doctest')

            @pytest.fixture
            def unblock_test_results(request):
                return {
                    'api_exists': getattr(request.config, '_unblock_api_exists', False),
                    'unblock_result': getattr(request.config, '_unblock_result', None),
                    'doctest_unblocked': getattr(
                        request.config, '_doctest_unblocked', False
                    ),
                }
            """,
        ),
    )

    # Create test that verifies unblock worked
    pytester.makepyfile(
        test_verify=textwrap.dedent(
            """
            def test_unblock_api_works(unblock_test_results):
                assert unblock_test_results['api_exists'], "unblock() API should exist"
                assert unblock_test_results['unblock_result'] is True, (
                    "unblock() should return True when successful"
                )
                assert unblock_test_results['doctest_unblocked'], (
                    "doctest should be unblocked after calling unblock()"
                )
            """,
        ),
    )

    result = pytester.runpytest("test_verify.py", "-v")
    result.assert_outcomes(passed=1)
