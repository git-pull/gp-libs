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


STATE_MD = textwrap.dedent(
    """
# Title

```python
>>> greeting = "hello"
>>> greeting
'hello'
```

Narrative prose between the two blocks.

```python
>>> greeting.upper()
'HELLO'
```
    """,
)

SHARED_GROUP_REST = textwrap.dedent(
    """
Title
=====

.. doctest:: intro

    >>> greeting = "hello"

Narrative prose.

.. doctest:: intro

    >>> greeting.upper()
    'HELLO'
    """,
)


def _write_ini(pytester: _pytest.pytester.Pytester, *lines: str) -> None:
    """Write a pytest.ini that keeps the built-in doctest plugin out."""
    pytester.makefile(
        ".ini",
        pytest="\n".join(["[pytest]", "addopts=-p no:doctest", *lines]),
    )


class NamespaceCollectionCase(t.NamedTuple):
    """Page and the items it collects.

    Attributes
    ----------
    test_id : str
        pytest parametrize id.
    file_name : str
        Page written into the pytester directory.
    page : str
        Page content.
    node_ids : list[str]
        Node ids expected, in collection order.
    """

    test_id: str
    file_name: str
    page: str
    node_ids: list[str]


NAMESPACE_COLLECTION_CASES = [
    NamespaceCollectionCase(
        test_id="group-collects-as-one-item",
        file_name="page.rst",
        page=SHARED_GROUP_REST,
        node_ids=["page.rst::intro"],
    ),
    NamespaceCollectionCase(
        test_id="markdown-group-collects-as-one-item",
        file_name="page.md",
        page=textwrap.dedent(
            """
# Title

```{doctest} intro
>>> greeting = "hello"
```

Narrative prose.

```{doctest} intro
>>> greeting.upper()
'HELLO'
```
            """,
        ),
        node_ids=["page.md::intro"],
    ),
    NamespaceCollectionCase(
        test_id="distinct-groups-collect-separately",
        file_name="page.rst",
        page=textwrap.dedent(
            """
Title
=====

.. doctest:: alpha

    >>> alpha_only = 1

.. doctest:: beta

    >>> alpha_only
    Traceback (most recent call last):
    NameError: name 'alpha_only' is not defined
            """,
        ),
        node_ids=["page.rst::alpha", "page.rst::beta"],
    ),
    NamespaceCollectionCase(
        test_id="ungrouped-blocks-collect-one-item-each",
        file_name="page.md",
        page="\n".join(f"```python\n>>> {n}\n{n}\n```\n" for n in range(12)),
        node_ids=[f"page.md::page.md[{n}]" for n in range(12)],
    ),
]


@pytest.mark.parametrize(
    NamespaceCollectionCase._fields,
    NAMESPACE_COLLECTION_CASES,
    ids=[case.test_id for case in NAMESPACE_COLLECTION_CASES],
)
def test_namespace_collection(
    pytester: _pytest.pytester.Pytester,
    test_id: str,
    file_name: str,
    page: str,
    node_ids: list[str],
) -> None:
    """A page collects one item per namespace, in the order it reads.

    The node id carries the namespace and nothing machine-specific, so it can
    be written into a ``--deselect`` and survive the trip to another checkout.
    """
    pytester.plugins = ["pytest_doctest_docutils"]
    _write_ini(pytester)
    (pytester.path / file_name).write_text(page, encoding="utf-8")

    items, _ = pytester.inline_genitems(file_name)

    assert [item.nodeid for item in items] == node_ids

    result = pytester.runpytest(file_name)
    result.assert_outcomes(passed=len(node_ids))


def test_node_id_selects_one_namespace(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """Running a node id runs exactly the namespace it names."""
    pytester.plugins = ["pytest_doctest_docutils"]
    _write_ini(pytester)
    (pytester.path / "page.rst").write_text(SHARED_GROUP_REST, encoding="utf-8")

    result = pytester.runpytest("page.rst::intro", "-v")

    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines(["page.rst::intro *"])


def test_group_stops_at_the_document(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """The same group name on two pages is two namespaces.

    Groups are read per document, as they are in :mod:`sphinx.ext.doctest`, so
    one page cannot reach into the state another built.
    """
    pytester.plugins = ["pytest_doctest_docutils"]
    _write_ini(pytester)
    (pytester.path / "first.rst").write_text(
        ".. doctest:: intro\n\n    >>> only_in_first = 1\n",
        encoding="utf-8",
    )
    (pytester.path / "second.rst").write_text(
        textwrap.dedent(
            """
.. doctest:: intro

    >>> only_in_first
    Traceback (most recent call last):
    NameError: name 'only_in_first' is not defined
            """,
        ),
        encoding="utf-8",
    )

    result = pytester.runpytest(str(pytester.path))

    result.assert_outcomes(passed=2)


class NamespaceScopeOptionCase(t.NamedTuple):
    """Namespace scope driven through the plugin's configuration.

    Attributes
    ----------
    test_id : str
        pytest parametrize id.
    file_name : str
        Page written into the pytester directory.
    page : str
        Page content.
    ini_scope : str
        Value for the ``doctest_docutils_namespace_scope`` ini option, empty to
        leave it unset.
    cli_args : list[str]
        Extra command-line arguments for the run.
    passed : int
        Items expected to pass.
    failed : int
        Items expected to fail.
    """

    test_id: str
    file_name: str
    page: str
    ini_scope: str
    cli_args: list[str]
    passed: int
    failed: int


NAMESPACE_SCOPE_OPTION_CASES = [
    NamespaceScopeOptionCase(
        test_id="unconfigured-keeps-blocks-apart",
        file_name="page.md",
        page=STATE_MD,
        ini_scope="",
        cli_args=[],
        passed=1,
        failed=1,
    ),
    NamespaceScopeOptionCase(
        test_id="ini-document-shares-the-page",
        file_name="page.md",
        page=STATE_MD,
        ini_scope="document",
        cli_args=[],
        passed=1,
        failed=0,
    ),
    NamespaceScopeOptionCase(
        test_id="cli-document-shares-the-page",
        file_name="page.md",
        page=STATE_MD,
        ini_scope="",
        cli_args=["--doctest-docutils-namespace-scope=document"],
        passed=1,
        failed=0,
    ),
    NamespaceScopeOptionCase(
        test_id="cli-block-overrides-ini-document",
        file_name="page.md",
        page=STATE_MD,
        ini_scope="document",
        cli_args=["--doctest-docutils-namespace-scope=block"],
        passed=1,
        failed=1,
    ),
    NamespaceScopeOptionCase(
        test_id="a-group-shares-whatever-the-scope-says",
        file_name="page.rst",
        page=SHARED_GROUP_REST,
        ini_scope="block",
        cli_args=[],
        passed=1,
        failed=0,
    ),
]


@pytest.mark.parametrize(
    NamespaceScopeOptionCase._fields,
    NAMESPACE_SCOPE_OPTION_CASES,
    ids=[case.test_id for case in NAMESPACE_SCOPE_OPTION_CASES],
)
def test_namespace_scope_option(
    pytester: _pytest.pytester.Pytester,
    test_id: str,
    file_name: str,
    page: str,
    ini_scope: str,
    cli_args: list[str],
    passed: int,
    failed: int,
) -> None:
    """The scope reaches the finder from the ini file or the flag, flag first."""
    pytester.plugins = ["pytest_doctest_docutils"]
    _write_ini(
        pytester,
        *([f"doctest_docutils_namespace_scope = {ini_scope}"] if ini_scope else []),
    )
    (pytester.path / file_name).write_text(page, encoding="utf-8")

    result = pytester.runpytest(file_name, *cli_args)

    result.assert_outcomes(passed=passed, failed=failed)


def test_namespace_scope_rejects_an_unknown_ini_value(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """A misspelled scope stops the session once, naming the values it knows."""
    pytester.plugins = ["pytest_doctest_docutils"]
    _write_ini(pytester, "doctest_docutils_namespace_scope = per-file")
    (pytester.path / "first.md").write_text(STATE_MD, encoding="utf-8")
    (pytester.path / "second.md").write_text(STATE_MD, encoding="utf-8")

    result = pytester.runpytest(str(pytester.path))

    assert result.ret == pytest.ExitCode.USAGE_ERROR
    result.stderr.fnmatch_lines(
        ["*Unknown namespace scope: 'per-file'*block, document*"],
    )
    assert (
        len(
            [line for line in result.stderr.lines if "Unknown namespace scope" in line],
        )
        == 1
    )


def test_document_scope_survives_xdist(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """A shared page passes when pytest splits the session across workers.

    A namespace is one item, so no worker can be handed half of one. This is
    the property that decided the design, which is why ``pytest-xdist`` is a
    development dependency rather than something to skip around when absent.
    """
    pytester.plugins = ["pytest_doctest_docutils"]
    _write_ini(pytester, "doctest_docutils_namespace_scope = document")
    (pytester.path / "page.md").write_text(STATE_MD, encoding="utf-8")
    (pytester.path / "other.md").write_text(STATE_MD, encoding="utf-8")

    result = pytester.runpytest(str(pytester.path), "-n", "2")

    result.assert_outcomes(passed=2)
