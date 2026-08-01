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


def _write_ini(
    pytester: _pytest.pytester.Pytester,
    *lines: str,
    addopts: str = "",
) -> None:
    """Write a pytest.ini that keeps the built-in doctest plugin out.

    ``addopts`` appends to that, for a run whose configuration is the thing
    under test.
    """
    pytester.makefile(
        ".ini",
        pytest="\n".join(
            ["[pytest]", f"addopts=-p no:doctest {addopts}".rstrip(), *lines],
        ),
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


GATED_STATE_MD = textwrap.dedent(
    """
# Title

```python
>>> greeting = "hello"
```

```python
>>> greeting = "nope"  # doctest: +SKIP
```

```python
>>> greeting.upper()
'HELLO'
```
    """,
)


def test_a_shared_page_still_reports_its_gated_block(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """A page merged end to end still says which of its blocks did not run.

    Under ``document`` a page with no groups is one namespace, which is where
    a gated block would otherwise disappear: the item passes on the strength
    of the blocks that ran and nothing names the one that did not.
    """
    pytester.plugins = ["pytest_doctest_docutils"]
    _write_ini(pytester, "doctest_docutils_namespace_scope = document")
    (pytester.path / "page.md").write_text(GATED_STATE_MD, encoding="utf-8")

    result = pytester.runpytest("page.md", "-rs", "-v")

    result.assert_outcomes(passed=1, skipped=1)
    result.stdout.fnmatch_lines(
        ["page.md::page.md PASSED*", "page.md::page.md[[]1[]] SKIPPED*"],
        consecutive=True,
    )
    result.stdout.fnmatch_lines(
        ["SKIPPED [[]1[]] *: page.md:*: every example skipped"],
    )


def test_a_gated_block_survives_xdist(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """The item a gated block collects as distributes like any other.

    It is an ordinary item holding one block's examples, so a worker gets all
    of it or none of it, the same property the merged namespace has.
    """
    pytester.plugins = ["pytest_doctest_docutils"]
    _write_ini(pytester, "doctest_docutils_namespace_scope = document")
    (pytester.path / "page.md").write_text(GATED_STATE_MD, encoding="utf-8")
    (pytester.path / "other.md").write_text(GATED_STATE_MD, encoding="utf-8")

    result = pytester.runpytest(str(pytester.path), "-n", "2")

    result.assert_outcomes(passed=2, skipped=2)


class NamespaceItemsOptionCase(t.NamedTuple):
    """Namespace layout driven through the plugin's configuration.

    Attributes
    ----------
    test_id : str
        pytest parametrize id.
    page : str
        Page content, written as ``page.md``.
    ini_lines : list[str]
        Extra lines for the generated ``pytest.ini``.
    cli_args : list[str]
        Extra command-line arguments for the run.
    node_ids : list[str]
        Node ids expected, in collection order.
    passed : int
        Items expected to pass.
    failed : int
        Items expected to fail.
    """

    test_id: str
    page: str
    ini_lines: list[str]
    cli_args: list[str]
    node_ids: list[str]
    passed: int
    failed: int


NAMESPACE_ITEMS_OPTION_CASES = [
    NamespaceItemsOptionCase(
        test_id="unconfigured-merges-a-shared-page",
        page=STATE_MD,
        ini_lines=["doctest_docutils_namespace_scope = document"],
        cli_args=[],
        node_ids=["page.md::page.md"],
        passed=1,
        failed=0,
    ),
    NamespaceItemsOptionCase(
        test_id="ini-per-block-keeps-both-node-ids",
        page=STATE_MD,
        ini_lines=[
            "doctest_docutils_namespace_scope = document",
            "doctest_docutils_namespace_items = per-block",
        ],
        cli_args=[],
        node_ids=["page.md::page.md[0]", "page.md::page.md[1]"],
        passed=2,
        failed=0,
    ),
    NamespaceItemsOptionCase(
        test_id="cli-per-block-keeps-both-node-ids",
        page=STATE_MD,
        ini_lines=["doctest_docutils_namespace_scope = document"],
        cli_args=["--doctest-docutils-namespace-items=per-block"],
        node_ids=["page.md::page.md[0]", "page.md::page.md[1]"],
        passed=2,
        failed=0,
    ),
    NamespaceItemsOptionCase(
        test_id="cli-merged-overrides-ini-per-block",
        page=STATE_MD,
        ini_lines=[
            "doctest_docutils_namespace_scope = document",
            "doctest_docutils_namespace_items = per-block",
        ],
        cli_args=["--doctest-docutils-namespace-items=merged"],
        node_ids=["page.md::page.md"],
        passed=1,
        failed=0,
    ),
    NamespaceItemsOptionCase(
        test_id="per-block-alone-shares-nothing",
        page=STATE_MD,
        ini_lines=["doctest_docutils_namespace_items = per-block"],
        cli_args=[],
        node_ids=["page.md::page.md[0]", "page.md::page.md[1]"],
        passed=1,
        failed=1,
    ),
]


@pytest.mark.parametrize(
    NamespaceItemsOptionCase._fields,
    NAMESPACE_ITEMS_OPTION_CASES,
    ids=[case.test_id for case in NAMESPACE_ITEMS_OPTION_CASES],
)
def test_namespace_items_option(
    pytester: _pytest.pytester.Pytester,
    test_id: str,
    page: str,
    ini_lines: list[str],
    cli_args: list[str],
    node_ids: list[str],
    passed: int,
    failed: int,
) -> None:
    """The layout reaches the finder from the ini file or the flag, flag first.

    Scope and layout are separate questions: the scope says what shares a
    namespace, the layout says whether sharing costs the blocks their node
    ids. Setting only the layout shares nothing, because the default scope
    still gives each block a namespace of its own.
    """
    pytester.plugins = ["pytest_doctest_docutils"]
    _write_ini(pytester, *ini_lines)
    (pytester.path / "page.md").write_text(page, encoding="utf-8")

    items, _ = pytester.inline_genitems("page.md", *cli_args)
    assert [item.nodeid for item in items] == node_ids

    result = pytester.runpytest("page.md", *cli_args)
    result.assert_outcomes(passed=passed, failed=failed)


def test_namespace_items_rejects_an_unknown_ini_value(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """A misspelled layout stops the session once, naming the values it knows."""
    pytester.plugins = ["pytest_doctest_docutils"]
    _write_ini(pytester, "doctest_docutils_namespace_items = one-each")
    (pytester.path / "first.md").write_text(STATE_MD, encoding="utf-8")
    (pytester.path / "second.md").write_text(STATE_MD, encoding="utf-8")

    result = pytester.runpytest(str(pytester.path))

    assert result.ret == pytest.ExitCode.USAGE_ERROR
    result.stderr.fnmatch_lines(
        ["*Unknown namespace items: 'one-each'*merged, per-block*"],
    )


def test_a_per_block_node_id_runs_one_block(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """A node id reaches one block, and says plainly what running it alone costs.

    Reaching a block is the whole point of the layout — ``--lf``, ``-k``, a
    JUnit report and a re-run all work through the id. A block that reads what
    the block above it bound cannot run alone, because nothing bound it: that
    limitation is inherent to running a fragment of a session, so it reports as
    the ``NameError`` it is.
    """
    pytester.plugins = ["pytest_doctest_docutils"]
    _write_ini(
        pytester,
        "doctest_docutils_namespace_scope = document",
        "doctest_docutils_namespace_items = per-block",
    )
    (pytester.path / "page.md").write_text(STATE_MD, encoding="utf-8")

    first = pytester.runpytest("page.md::page.md[0]", "-v")
    first.assert_outcomes(passed=1)
    first.stdout.fnmatch_lines(["page.md::page.md[[]0[]] *"])

    second = pytester.runpytest("page.md::page.md[1]")

    second.assert_outcomes(failed=1)
    second.stdout.fnmatch_lines(["*NameError: name 'greeting' is not defined*"])


def test_per_block_marks_each_namespace_for_loadgroup(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """Every block carries the group its namespace distributes under.

    The plugin can emit the marker but cannot pick the scheduler, so the
    marker is what makes ``--dist loadgroup`` usable. The group is the file
    plus the namespace, because a namespace never reaches past its page.
    """
    pytester.plugins = ["pytest_doctest_docutils"]
    _write_ini(
        pytester,
        "doctest_docutils_namespace_scope = document",
        "doctest_docutils_namespace_items = per-block",
    )
    (pytester.path / "page.md").write_text(STATE_MD, encoding="utf-8")

    items, _ = pytester.inline_genitems("page.md")

    markers = [item.get_closest_marker("xdist_group") for item in items]
    assert [marker.args[0] for marker in markers if marker is not None] == [
        "page.md::page.md",
        "page.md::page.md",
    ]


def test_merged_marks_nothing_for_loadgroup(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """A merged namespace is one item, which no scheduler can split."""
    pytester.plugins = ["pytest_doctest_docutils"]
    _write_ini(pytester, "doctest_docutils_namespace_scope = document")
    (pytester.path / "page.md").write_text(STATE_MD, encoding="utf-8")

    items, _ = pytester.inline_genitems("page.md")

    assert [item.get_closest_marker("xdist_group") for item in items] == [None]


class SplittingSchedulerCase(t.NamedTuple):
    """Invocation naming a scheduler that distributes a namespace by item.

    Attributes
    ----------
    test_id : str
        pytest parametrize id.
    args : list[str]
        Arguments appended to the run.
    addopts : str
        Arguments the ini file carries instead.
    named : str
        Scheduler the refusal is expected to name.
    """

    test_id: str
    args: list[str]
    addopts: str
    named: str


SPLITTING_SCHEDULER_CASES = [
    SplittingSchedulerCase(
        test_id="load-distributes-by-item",
        args=["-n", "2", "--dist", "load"],
        addopts="",
        named="load",
    ),
    SplittingSchedulerCase(
        test_id="worksteal-distributes-then-rebalances",
        args=["-n", "2", "--dist", "worksteal"],
        addopts="",
        named="worksteal",
    ),
    SplittingSchedulerCase(
        test_id="addopts-names-the-scheduler-too",
        args=["-n", "2"],
        addopts="--dist load",
        named="load",
    ),
    SplittingSchedulerCase(
        test_id="multiplied-tx-spells-more-than-one-worker",
        args=["--tx", "2*popen", "--dist", "load"],
        addopts="",
        named="load",
    ),
    SplittingSchedulerCase(
        test_id="multiplied-tx-adds-up-across-specifications",
        args=["--tx", "1*popen", "--tx", "1*popen", "--dist", "load"],
        addopts="",
        named="load",
    ),
    SplittingSchedulerCase(
        test_id="a-count-asking-for-none-takes-none-away",
        args=["--tx", "-1*popen", "--tx", "2*popen", "--dist", "load"],
        addopts="",
        named="load",
    ),
]


@pytest.mark.parametrize(
    SplittingSchedulerCase._fields,
    SPLITTING_SCHEDULER_CASES,
    ids=[case.test_id for case in SPLITTING_SCHEDULER_CASES],
)
def test_per_block_refuses_a_named_splitting_scheduler(
    pytester: _pytest.pytester.Pytester,
    test_id: str,
    args: list[str],
    addopts: str,
    named: str,
) -> None:
    """Naming a scheduler that distributes by item stops the run.

    ``load`` hands a file's items to whichever worker is free and
    ``worksteal`` does the same, then re-balances. A shared globals mapping
    is a Python object and does not cross processes, so the session stops
    rather than reporting a page that is only wrong because of how it was
    scheduled. Asking for one by name is a choice to answer, not to overrule.

    A scheduler asked for through ini ``addopts`` is asked for just as much
    as one typed on the command line — pytest folds ``addopts`` into the
    arguments before parsing them, which is why reading the parsed value
    finds both. It is also why ``sys.argv`` cannot be read instead.
    """
    pytester.plugins = ["pytest_doctest_docutils"]
    _write_ini(
        pytester,
        "doctest_docutils_namespace_scope = document",
        "doctest_docutils_namespace_items = per-block",
        addopts=addopts,
    )
    (pytester.path / "page.md").write_text(STATE_MD, encoding="utf-8")

    result = pytester.runpytest(str(pytester.path), *args)

    assert result.ret == pytest.ExitCode.USAGE_ERROR
    result.stderr.fnmatch_lines([f"*--dist {named} hands a file's items*"])
    result.stderr.fnmatch_lines(["*--dist loadgroup or --dist loadfile*"])


def test_per_block_keeps_a_single_multiplied_worker(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """One worker cannot split a namespace, however the run spelled it.

    ``--tx 1*popen`` asks for the same single environment ``--tx popen``
    does. Counting the multiplier has to leave that run alone, or reading
    the shorthand correctly would cost every one-worker run its scheduler.
    """
    pytester.plugins = ["pytest_doctest_docutils"]
    _write_ini(
        pytester,
        "doctest_docutils_namespace_scope = document",
        "doctest_docutils_namespace_items = per-block",
    )
    (pytester.path / "page.md").write_text(STATE_MD, encoding="utf-8")

    result = pytester.runpytest(
        str(pytester.path),
        "--tx",
        "1*popen",
        "--dist",
        "load",
    )

    result.assert_outcomes(passed=2)


def test_per_block_keeps_workers_for_a_suite_holding_no_page(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """A suite with no page keeps its workers, whatever scheduler it named.

    The layout is a project-wide setting, so a project can carry it in its
    ini while a given run collects only Python tests. Nothing there holds a
    namespace, so there is nothing a scheduler could split and no reason to
    take ``-n`` away — which is why the refusal reads the run's collection
    rather than the setting.
    """
    pytester.plugins = ["pytest_doctest_docutils"]
    _write_ini(
        pytester,
        "doctest_docutils_namespace_scope = document",
        "doctest_docutils_namespace_items = per-block",
    )
    pytester.makepyfile(
        test_python="""
        def test_one() -> None:
            assert True


        def test_two() -> None:
            assert True
        """,
    )

    left_open = pytester.runpytest(str(pytester.path), "-n", "2")
    left_open.assert_outcomes(passed=2)

    named = pytester.runpytest(str(pytester.path), "-n", "2", "--dist", "worksteal")

    named.assert_outcomes(passed=2)


def test_per_block_fills_in_a_scheduler_the_run_left_open(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """``-n`` alone asks for workers, not for a way of filling them.

    pytest-xdist answers it with ``--dist load``, which splits a page. The
    run said nothing about distribution, so file-level scheduling is filled
    in and the page comes through whole beside the Python tests that share
    the session.

    The node ids stay the ones the layout collects. ``loadgroup`` would suit
    the marker the plugin emits, but the group is appended to a node id by
    the worker, from the worker's own ``--dist`` value, so a controller
    cannot reach it — and substituting that scheduler would leave every item
    in a scope of its own and split the page after all.
    """
    pytester.plugins = ["pytest_doctest_docutils"]
    _write_ini(
        pytester,
        "doctest_docutils_namespace_scope = document",
        "doctest_docutils_namespace_items = per-block",
    )
    (pytester.path / "page.md").write_text(STATE_MD, encoding="utf-8")
    (pytester.path / "other.md").write_text(STATE_MD, encoding="utf-8")
    pytester.makepyfile(
        test_python="""
        def test_one() -> None:
            assert True
        """,
    )

    result = pytester.runpytest(str(pytester.path), "-n", "2", "-v")

    result.assert_outcomes(passed=5)
    result.stdout.fnmatch_lines(["*scheduling tests via _PageScheduling*"])
    assert not [line for line in result.stdout.lines if "@page.md" in line]


def test_merged_survives_the_splitting_scheduler(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """The refusal reaches only the layout that needs it."""
    pytester.plugins = ["pytest_doctest_docutils"]
    _write_ini(pytester, "doctest_docutils_namespace_scope = document")
    (pytester.path / "page.md").write_text(STATE_MD, encoding="utf-8")
    (pytester.path / "other.md").write_text(STATE_MD, encoding="utf-8")

    result = pytester.runpytest(str(pytester.path), "-n", "2")

    result.assert_outcomes(passed=2)


class PerBlockSchedulerCase(t.NamedTuple):
    """Distributed run a per-block page comes through whole.

    Attributes
    ----------
    test_id : str
        pytest parametrize id.
    args : list[str]
        Arguments the run is made with.
    passed : int
        Examples expected to pass across every worker.
    """

    test_id: str
    args: list[str]
    passed: int


PER_BLOCK_SCHEDULER_CASES = [
    PerBlockSchedulerCase(
        test_id="loadfile-keeps-a-file-whole",
        args=["-n", "2", "--dist", "loadfile"],
        passed=4,
    ),
    PerBlockSchedulerCase(
        test_id="loadgroup-keeps-a-namespace-whole",
        args=["-n", "2", "--dist", "loadgroup"],
        passed=4,
    ),
    PerBlockSchedulerCase(
        test_id="loadscope-keeps-a-file-whole",
        args=["-n", "2", "--dist", "loadscope"],
        passed=4,
    ),
    PerBlockSchedulerCase(
        test_id="each-repeats-the-suite-per-worker",
        args=["-n", "2", "--dist", "each"],
        passed=8,
    ),
    PerBlockSchedulerCase(
        test_id="one-worker-has-nothing-to-split-against",
        args=["-n", "1"],
        passed=4,
    ),
    PerBlockSchedulerCase(
        test_id="n-alone-leaves-the-scheduler-to-fill-in",
        args=["-n", "2"],
        passed=4,
    ),
    PerBlockSchedulerCase(
        test_id="dist-without-workers-never-distributes",
        args=["--dist", "load"],
        passed=4,
    ),
]


@pytest.mark.parametrize(
    PerBlockSchedulerCase._fields,
    PER_BLOCK_SCHEDULER_CASES,
    ids=[case.test_id for case in PER_BLOCK_SCHEDULER_CASES],
)
def test_per_block_survives_a_scheduler_that_keeps_it_together(
    pytester: _pytest.pytester.Pytester,
    test_id: str,
    args: list[str],
    passed: int,
) -> None:
    """A state-building page passes wherever its namespace stays on one worker.

    ``loadfile`` and ``loadscope`` split on the node id's path; ``loadgroup``
    reads the ``xdist_group`` marker the plugin emits; ``each`` gives every
    worker the whole suite. A run xdist would not distribute at all — one
    worker, or a ``--dist`` value with no workers behind it — is not refused
    either, because there is nothing for it to split a namespace between.
    ``-n`` on its own names no scheduler, so one that keeps a page whole is
    filled in.
    """
    pytester.plugins = ["pytest_doctest_docutils"]
    _write_ini(
        pytester,
        "doctest_docutils_namespace_scope = document",
        "doctest_docutils_namespace_items = per-block",
    )
    (pytester.path / "page.md").write_text(STATE_MD, encoding="utf-8")
    (pytester.path / "other.md").write_text(STATE_MD, encoding="utf-8")

    result = pytester.runpytest(str(pytester.path), *args)

    result.assert_outcomes(passed=passed)


def test_strict_markers_passes_whether_or_not_you_opt_in(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """``xdist_group`` is registered whatever the layout, and pytest-xdist absent.

    A project that never asks for the layout never meets the marker at all.
    One that does, on a machine without pytest-xdist to register the marker
    itself, would otherwise have every item rejected as carrying an unknown
    marker.

    Run out of process because pytest caches known marker names on the global
    ``MarkGenerator``, so an in-process run inherits whatever this suite's own
    session registered and could not tell the two cases apart.
    """
    _write_ini(pytester)
    (pytester.path / "page.md").write_text(STATE_MD, encoding="utf-8")

    unconfigured = pytester.runpytest_subprocess(
        "page.md",
        "--strict-markers",
        "-p",
        "no:xdist",
    )
    unconfigured.assert_outcomes(passed=1, failed=1)

    result = pytester.runpytest_subprocess(
        "page.md",
        "--strict-markers",
        "-p",
        "no:xdist",
        "--doctest-docutils-namespace-items=per-block",
    )

    result.assert_outcomes(passed=1, failed=1)


def test_xdist_group_is_listed_once(pytester: _pytest.pytester.Pytester) -> None:
    """``pytest --markers`` describes the marker once, xdist installed or not.

    pytest-xdist registers ``xdist_group`` itself, so this plugin only fills
    the gap it leaves. Registering unconditionally would list the marker twice
    for every project that has xdist, opted in or not.

    Run out of process for the same reason as the ``--strict-markers`` case:
    marker registration is read back off configuration this suite's own
    session has already populated.
    """
    _write_ini(pytester)

    with_xdist = pytester.runpytest_subprocess("--markers")
    without_xdist = pytester.runpytest_subprocess("--markers", "-p", "no:xdist")

    def listed(result: _pytest.pytester.RunResult) -> list[str]:
        return [
            line
            for line in result.stdout.lines
            if line.startswith("@pytest.mark.xdist_group")
        ]

    assert len(listed(with_xdist)) == 1
    assert listed(without_xdist) == [
        (
            "@pytest.mark.xdist_group(name): keep a namespace's blocks on one"
            " pytest-xdist worker under --dist loadgroup"
        ),
    ]


def test_per_block_collects_under_collect_only(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """``--collect-only`` is never refused: xdist skips itself when only collecting.

    A project carrying ``-n`` in its ``addopts`` has to be able to enumerate
    its own suite, and no example runs, so no namespace is ever shared.
    """
    pytester.plugins = ["pytest_doctest_docutils"]
    _write_ini(
        pytester,
        "doctest_docutils_namespace_scope = document",
        "doctest_docutils_namespace_items = per-block",
    )
    (pytester.path / "page.md").write_text(STATE_MD, encoding="utf-8")

    result = pytester.runpytest(str(pytester.path), "--collect-only", "-q", "-n", "2")

    assert result.ret == pytest.ExitCode.OK
    result.stdout.fnmatch_lines(["page.md::page.md[[]0[]]", "page.md::page.md[[]1[]]"])


def test_per_block_reports_the_layout_it_resolved(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """The header says which layout ran, and says nothing when it is the usual one."""
    pytester.plugins = ["pytest_doctest_docutils"]
    _write_ini(pytester, "doctest_docutils_namespace_scope = document")
    (pytester.path / "page.md").write_text(STATE_MD, encoding="utf-8")

    quiet = pytester.runpytest("page.md")
    assert not [
        line for line in quiet.stdout.lines if line.startswith("doctest-docutils:")
    ]

    result = pytester.runpytest(
        "page.md",
        "--doctest-docutils-namespace-items=per-block",
    )

    result.stdout.fnmatch_lines(
        ["doctest-docutils: namespace items: per-block, namespace scope: document"],
    )


DOCTEST_NAMESPACE_CONFTEST = textwrap.dedent(
    """
from typing import Any, Dict
import pytest

@pytest.fixture(autouse=True)
def add_doctest_fixtures(doctest_namespace: Dict[str, Any]):
    doctest_namespace["add"] = lambda a, b: a + b
    """,
)

FIXTURE_USING_MD = textwrap.dedent(
    """
# Title

```python
>>> add(1, 2)
3
```

Prose between the blocks.

```python
>>> add(3, 4)
7
```
    """,
)


@pytest.mark.parametrize(
    ("test_id", "items", "passed"),
    [
        ("merged", "merged", 1),
        ("per-block", "per-block", 2),
    ],
    ids=["merged", "per-block"],
)
def test_doctest_namespace_reaches_every_block(
    pytester: _pytest.pytester.Pytester,
    test_id: str,
    items: str,
    passed: int,
) -> None:
    """A fixture seeded into the namespace is in scope for every block of it.

    pytest merges the fixture into ``dtest.globs`` at item setup. Merged, that
    happens once for the namespace; per block it happens once per block, into
    the one mapping they share.
    """
    pytester.plugins = ["pytest_doctest_docutils"]
    _write_ini(
        pytester,
        "doctest_docutils_namespace_scope = document",
        f"doctest_docutils_namespace_items = {items}",
    )
    pytester.makeconftest(DOCTEST_NAMESPACE_CONFTEST)
    (pytester.path / "page.md").write_text(FIXTURE_USING_MD, encoding="utf-8")

    result = pytester.runpytest("page.md")

    result.assert_outcomes(passed=passed)


TORN_DOWN_FIXTURE_CONFTEST = textwrap.dedent(
    """
from typing import Any, Dict
import pytest


class Server:
    def __init__(self) -> None:
        self.alive = True


@pytest.fixture(autouse=True)
def server(doctest_namespace: Dict[str, Any]):
    running = Server()
    doctest_namespace["server"] = running
    yield running
    running.alive = False
    """,
)

CARRIED_FIXTURE_MD = textwrap.dedent(
    """
# Title

```python
>>> kept = server
>>> kept.alive
True
```

Prose between the blocks.

```python
>>> kept.alive
True
```
    """,
)


@pytest.mark.parametrize(
    ("test_id", "items", "passed", "failed"),
    [
        ("merged", "merged", 1, 0),
        ("per-block", "per-block", 1, 1),
    ],
    ids=["merged", "per-block"],
)
def test_per_block_finalizes_a_fixture_between_blocks(
    pytester: _pytest.pytester.Pytester,
    test_id: str,
    items: str,
    passed: int,
    failed: int,
) -> None:
    """A namespace shares the mapping, not the lifetime of what a fixture made.

    Per block, each block is its own item, so a function-scoped fixture tears
    down between them. An object one block bound out of that fixture is
    finalized before the next block reads it, which merged is a single item
    and so never happens.
    """
    pytester.plugins = ["pytest_doctest_docutils"]
    _write_ini(
        pytester,
        "doctest_docutils_namespace_scope = document",
        f"doctest_docutils_namespace_items = {items}",
    )
    pytester.makeconftest(TORN_DOWN_FIXTURE_CONFTEST)
    (pytester.path / "page.md").write_text(CARRIED_FIXTURE_MD, encoding="utf-8")

    result = pytester.runpytest("page.md")

    result.assert_outcomes(passed=passed, failed=failed)


def test_per_block_still_reports_a_gated_block(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """A gated block reports skipped, and the block after it still runs.

    Merged, a gated block has to be lifted out of its namespace to report at
    all; per block it is already an item, and it is marked before setup either
    way, so its fixtures never run for a block that executes nothing.
    """
    pytester.plugins = ["pytest_doctest_docutils"]
    _write_ini(
        pytester,
        "doctest_docutils_namespace_scope = document",
        "doctest_docutils_namespace_items = per-block",
    )
    (pytester.path / "page.md").write_text(GATED_STATE_MD, encoding="utf-8")

    result = pytester.runpytest("page.md", "-rs", "-v")

    result.assert_outcomes(passed=2, skipped=1)
    result.stdout.fnmatch_lines(
        [
            "page.md::page.md[[]0[]] PASSED*",
            "page.md::page.md[[]1[]] SKIPPED*",
            "page.md::page.md[[]2[]] PASSED*",
        ],
        consecutive=True,
    )
    result.stdout.fnmatch_lines(
        ["SKIPPED [[]1[]] *: page.md:*: every example skipped"],
    )


def test_merged_keeps_a_failure_through_a_retry(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """A retry re-runs a merged namespace whole, so a real failure stands.

    The retry rebuilds the namespace from its first block, which is what makes
    the default layout safe to combine with a test-retry plugin. Under
    ``per-block`` a retry re-runs only the block that failed, against the
    mapping that block already changed.
    """
    pytester.plugins = ["pytest_doctest_docutils"]
    _write_ini(pytester)
    (pytester.path / "page.rst").write_text(
        textwrap.dedent(
            """
            Title
            =====

            .. doctest:: demo

                >>> seen = []

            .. doctest:: demo

                >>> seen.append(1)
                >>> len(seen)
                2
            """,
        ),
        encoding="utf-8",
    )

    result = pytester.runpytest("page.rst", "--reruns", "2")

    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*1 failed*2 rerun*"])


def test_per_block_refuses_a_repeated_block(
    pytester: _pytest.pytester.Pytester,
) -> None:
    """A block run twice is refused rather than trusted.

    A retry re-runs one block against the globals it already changed, so an
    expectation that comes true on the second attempt would report as a pass.
    The namespace cannot be rebuilt for one block alone, so the repeat fails
    with a message naming the way out.
    """
    pytester.plugins = ["pytest_doctest_docutils"]
    _write_ini(pytester, "doctest_docutils_namespace_items = per-block")
    (pytester.path / "page.rst").write_text(
        textwrap.dedent(
            """
            Title
            =====

            .. doctest:: demo

                >>> seen = []

            .. doctest:: demo

                >>> seen.append(1)
                >>> len(seen)
                2
            """,
        ),
        encoding="utf-8",
    )

    result = pytester.runpytest("page.rst", "--reruns", "2")

    result.assert_outcomes(passed=1, failed=1)
    result.stdout.fnmatch_lines(
        ["*was run twice against a namespace laid out per block*"]
    )
