"""Doctest module for docutils."""

from __future__ import annotations

import doctest
import logging
import os
import pathlib
import re
import sys
import typing as t

import docutils
from docutils import nodes
from docutils.parsers.rst import Directive, directives
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

from docutils_compat import findall

if t.TYPE_CHECKING:
    import types

    from docutils.nodes import Node, TextElement

logger = logging.getLogger(__name__)


blankline_re = re.compile(r"^\s*<BLANKLINE>", re.MULTILINE)
# Backported from Sphinx commit ad0c343d3 (2025-01-04).
# https://github.com/sphinx-doc/sphinx/commit/ad0c343d3
# Allow optional leading whitespace before doctest directive comments.
doctestopt_re = re.compile(r"[ \t]*#\s*doctest:.+$", re.MULTILINE)

#: How wide a namespace the blocks of one document share when they name no
#: group.
NamespaceScope = t.Literal["block", "document"]

#: Accepted :data:`NamespaceScope` names, narrowest first.
NAMESPACE_SCOPES: tuple[NamespaceScope, ...] = ("block", "document")

#: Scope used when a caller names none: every ungrouped block starts empty.
DEFAULT_NAMESPACE_SCOPE: NamespaceScope = "block"

#: Group a ``.. doctest::`` written without an argument lands in, as in
#: :mod:`sphinx.ext.doctest`. It means the author named no group.
_DEFAULT_GROUP = "default"

#: Group name meaning "every group this document declares", as in
#: :mod:`sphinx.ext.doctest`. It resolves only once the page has been read.
_WILDCARD_GROUP = "*"

#: ``HIDE`` marks a prompt that rendered documentation drops and a test run
#: keeps. It changes no output check, but a page carrying it fails to parse
#: wherever the name is unregistered, so registration happens on import rather
#: than at any one entry point's setup: ``python -m doctest_docutils`` reaches
#: no further than this module, and pytest's own ``DoctestModule`` parses .py
#: docstrings without ever consulting the plugin's flag lookup.
_HIDE_FLAG = doctest.register_optionflag("HIDE")


class NamespaceScopeError(ValueError):
    """Raised when a namespace scope is not one of :data:`NAMESPACE_SCOPES`.

    Examples
    --------
    >>> print(NamespaceScopeError("per-file"))
    Unknown namespace scope: 'per-file'. Expected one of: block, document
    """

    def __init__(self, value: str) -> None:
        super().__init__(
            f"Unknown namespace scope: {value!r}. "
            f"Expected one of: {', '.join(NAMESPACE_SCOPES)}",
        )


class SkipifExpressionError(ValueError):
    """Raised when a block's ``:skipif:`` expression cannot be evaluated.

    Examples
    --------
    >>> error = NameError("name 'platform' is not defined")
    >>> print(SkipifExpressionError("platform.system()", "page.rst", 4, error))
    page.rst:4: :skipif: 'platform.system()' failed: name 'platform' is not defined
    """

    def __init__(
        self,
        expression: str,
        filename: str,
        line: int,
        error: BaseException,
    ) -> None:
        super().__init__(
            f"{filename}:{line}: :skipif: {expression!r} failed: {error}",
        )


def _parse_namespace_scope(value: str) -> NamespaceScope:
    """Return `value` as a :data:`NamespaceScope`, rejecting anything else.

    Parameters
    ----------
    value : str
        Scope name to validate.

    Returns
    -------
    NamespaceScope
        The scope, unchanged.

    Raises
    ------
    NamespaceScopeError
        If `value` names no known scope.

    Examples
    --------
    >>> _parse_namespace_scope("document")
    'document'

    >>> try:
    ...     _parse_namespace_scope("per-file")
    ... except NamespaceScopeError as exc:
    ...     print(exc)
    Unknown namespace scope: 'per-file'. Expected one of: block, document
    """
    if value not in NAMESPACE_SCOPES:
        raise NamespaceScopeError(value)
    return value


def is_allowed_version(version: str, spec: str) -> bool:
    """Check `spec` satisfies `version` or not.

    This obeys PEP-440 specifiers:
    https://peps.python.org/pep-0440/#version-specifiers

    Some examples:

    >>> is_allowed_version('3.3', '<=3.5')
    True
    >>> is_allowed_version('3.3', '<=3.2')
    False
    >>> is_allowed_version('3.3', '>3.2, <4.0')
    True
    """
    return Version(version) in SpecifierSet(spec)


class TestDirective(Directive):
    """Base class for doctest-related directives."""

    has_content = True
    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = True

    def get_source_info(self) -> tuple[str, int]:
        """Get source and line number."""
        return self.state_machine.get_source_and_line(self.lineno)  # type: ignore

    def set_source_info(self, node: Node) -> None:
        """Set source and line number to the node."""
        node.source, node.line = self.get_source_info()

    def run(self) -> list[Node]:
        """Run docutils test directive."""
        # use ordinary docutils nodes for test code: they get special attributes
        # so that our builder recognizes them, and the other builders are happy.
        code = "\n".join(self.content)
        test = None

        if self.name == "doctest":
            if "<BLANKLINE>" in code:
                # convert <BLANKLINE>s to ordinary blank lines for presentation
                test = code
                code = blankline_re.sub("", code)
            if (
                doctestopt_re.search(code)
                and "no-trim-doctest-flags" not in self.options
            ):
                if not test:
                    test = code
                code = doctestopt_re.sub("", code)
        nodetype: type[TextElement] = nodes.literal_block
        if self.name in {"testsetup", "testcleanup"} or "hide" in self.options:
            nodetype = nodes.comment
        if self.arguments:
            groups = [x.strip() for x in self.arguments[0].split(",")]
        else:
            groups = [_DEFAULT_GROUP]
        node = nodetype(code, code, testnodetype=self.name, groups=groups)
        self.set_source_info(node)
        if test is not None:
            # only save if it differs from code
            node["test"] = test
        if self.name == "doctest":
            node["language"] = "pycon3"
        node["options"] = {}
        if self.name in ("doctest") and "options" in self.options:
            # parse doctest-like output comparison flags
            option_strings = self.options["options"].replace(",", " ").split()
            for option in option_strings:
                prefix, option_name = option[0], option[1:]
                if prefix not in "+-":
                    self.state.document.reporter.warning(
                        f"missing '+' or '-' in '{option}' option.",
                        line=self.lineno,
                    )
                    continue
                if option_name not in doctest.OPTIONFLAGS_BY_NAME:
                    self.state.document.reporter.warning(
                        f"'{option_name}' is not a valid option.",
                        line=self.lineno,
                    )
                    continue
                flag = doctest.OPTIONFLAGS_BY_NAME[option[1:]]
                node["options"][flag] = option[0] == "+"
        if self.name == "doctest" and "pyversion" in self.options:
            try:
                spec = self.options["pyversion"]
                python_version = ".".join([str(v) for v in sys.version_info[:3]])
                # Sphinx, which this was ported from, spells the signature
                # (spec, version); gp-libs reversed it. The version goes first.
                if not is_allowed_version(python_version, spec):
                    flag = doctest.OPTIONFLAGS_BY_NAME["SKIP"]
                    node["options"][flag] = True  # Skip the test
            except (InvalidSpecifier, InvalidVersion):
                self.state.document.reporter.warning(
                    f"'{spec}' is not a valid pyversion option",
                    line=self.lineno,
                )
        if "skipif" in self.options:
            node["skipif"] = self.options["skipif"]
        if "trim-doctest-flags" in self.options:
            node["trim_flags"] = True
        elif "no-trim-doctest-flags" in self.options:
            node["trim_flags"] = False
        logger.debug("parsed directive", extra={"doctest_block_type": self.name})
        return [node]


class TestsetupDirective(TestDirective):
    """Test setup directive."""

    option_spec: t.ClassVar = {"skipif": directives.unchanged_required}


class TestcleanupDirective(TestDirective):
    """Test cleanup directive."""

    option_spec: t.ClassVar = {"skipif": directives.unchanged_required}


class DoctestDirective(TestDirective):
    """Doctest directive."""

    option_spec: t.ClassVar = {
        "no-trim-doctest-flags": directives.flag,
        "options": directives.unchanged,
        "pyversion": directives.unchanged_required,
        "skipif": directives.unchanged_required,
        "trim-doctest-flags": directives.flag,
    }


class MockTabDirective(TestDirective):
    """Mock tab directive."""

    def run(self) -> list[Node]:
        """Parse a mock-tabs directive."""
        self.assert_has_content()

        content = nodes.container("", is_div=True, classes=["tab-content"])
        self.state.nested_parse(self.content, self.content_offset, content)
        return [content]


def setup() -> dict[str, t.Any]:
    """Configure doctest for doctest_docutils."""
    directives.register_directive("testsetup", TestsetupDirective)
    directives.register_directive("testcleanup", TestcleanupDirective)
    directives.register_directive("doctest", DoctestDirective)

    # Third party mock directive: sphinx-inline-tabs @ 2022.01.02.beta11
    directives.register_directive("tab", MockTabDirective)
    return {"version": docutils.__version__, "parallel_read_safe": True}


# For backward compatibility, a global instance of a DocTestRunner
# class, updated by testmod.
master = None

parser = doctest.DocTestParser()
_DIRECTIVES_READY = False
_REQUIRED_DIRECTIVES = ("doctest", "testsetup", "testcleanup", "tab")


def _directive_registry() -> dict[str, t.Any]:
    """Return docutils directive registry with typing info."""
    return t.cast(dict[str, t.Any], directives.__dict__["_directives"])


def _ensure_directives_registered() -> None:
    """Register doctest-related directives once per interpreter."""
    global _DIRECTIVES_READY
    registry = _directive_registry()
    missing = any(name not in registry for name in _REQUIRED_DIRECTIVES)
    if _DIRECTIVES_READY and not missing:
        return
    setup()
    _DIRECTIVES_READY = True


def _node_groups(node: nodes.Element) -> list[str]:
    """Return every doctest group a block declares, in the order written.

    Only the directive forms carry a ``groups`` attribute: ``.. doctest:: name``
    in reStructuredText and the ``{doctest} name`` fence in Markdown. Declaring
    a group is the author asking blocks to share a namespace, so it holds at
    every :data:`NamespaceScope`.

    Parameters
    ----------
    node : docutils.nodes.Element
        Node a doctest was collected from.

    Returns
    -------
    list[str]
        Group names, empty for a block that named none.

    Examples
    --------
    >>> from docutils import nodes
    >>> _node_groups(nodes.literal_block("", "", groups=["intro"]))
    ['intro']

    A comma list names every group the block joins:

    >>> _node_groups(nodes.literal_block("", "", groups=["alpha", "beta"]))
    ['alpha', 'beta']

    A directive written without an argument names no group, and a plain fence
    or a reStructuredText doctest block has nowhere to write one:

    >>> _node_groups(nodes.literal_block("", "", groups=["default"]))
    []
    >>> _node_groups(nodes.doctest_block("", ""))
    []
    """
    groups = node.get("groups")
    if not isinstance(groups, list):
        return []
    names = [str(group).strip() for group in groups]
    return [name for name in names if name and name != _DEFAULT_GROUP]


def _namespace_name(
    group: str | None,
    scope: NamespaceScope,
    document_name: str,
    index: int,
) -> str:
    """Return the name of the namespace a block runs in.

    The name is also the key blocks merge under and the pytest node id they
    collect as, so two blocks share a namespace exactly when they share a name.

    Parameters
    ----------
    group : str or None
        Group the block declared, from :func:`_node_groups`.
    scope : NamespaceScope
        Scope chosen for blocks that declared no group.
    document_name : str
        Base name of the document, without its directory.
    index : int
        Position of the block in the document, counted from zero.

    Returns
    -------
    str
        Namespace name.

    Examples
    --------
    A declared group names its own namespace at every scope:

    >>> _namespace_name("intro", "block", "page.md", 0)
    'intro'
    >>> _namespace_name("intro", "document", "page.md", 0)
    'intro'

    A block that declared none is named for its position, or for the page when
    the document shares one namespace:

    >>> _namespace_name(None, "block", "page.md", 3)
    'page.md[3]'
    >>> _namespace_name(None, "document", "page.md", 3)
    'page.md'
    """
    if group is not None:
        return group
    if scope == "document":
        return document_name
    return f"{document_name}[{index}]"


def _node_line(node: nodes.Element) -> int:
    """Return the file line a block reports itself against.

    docutils leaves ``line`` unset on a doctest block nested inside a
    directive, a list item, or a block quote. The node holding it still carries
    one, which puts the block within a few lines of its prompts instead of at
    the top of the page.

    Parameters
    ----------
    node : docutils.nodes.Element
        Node the block was collected from.

    Returns
    -------
    int
        Line to position and report the block against, ``0`` when nothing up
        the tree carries one.

    Examples
    --------
    >>> from docutils import nodes
    >>> block = nodes.doctest_block("", "")
    >>> block.line = 6
    >>> _node_line(block)
    6

    A block the parser left unpositioned borrows the line of whatever holds it:

    >>> nested = nodes.doctest_block("", "")
    >>> admonition = nodes.note("", nested)
    >>> admonition.line = 7
    >>> _node_line(nested)
    7

    >>> _node_line(nodes.doctest_block("", ""))
    0
    """
    current: Node | None = node
    while current is not None:
        if current.line:
            return int(current.line)
        current = current.parent
    return 0


def _skipif(expression: str, globs: dict[str, t.Any]) -> bool:
    """Return whether a block's ``:skipif:`` expression asks to skip the block.

    The expression is Python source read from the document and **evaluated**,
    the contract :mod:`sphinx.ext.doctest` documents. It sees a copy of the
    globals the document starts with — the `globs` handed to
    :meth:`DocutilsDocTestFinder.find` — and nothing the page's own examples
    bound, because it is answered while the page is being read, before any of
    them run.

    Sphinx seeds that namespace from its ``doctest_global_setup`` setting;
    gp-libs has no such setting, so it binds :mod:`sys` instead unless the
    document bound the name itself. Without it the option could not answer the
    two questions it is written for, the Python version and the platform.

    Parameters
    ----------
    expression : str
        Python expression from the directive's ``:skipif:`` option.
    globs : dict[str, typing.Any]
        Globals the document starts with.

    Returns
    -------
    bool
        Whether the block's examples are marked :data:`doctest.SKIP`.

    Examples
    --------
    >>> _skipif("True", {})
    True
    >>> _skipif("False", {})
    False

    :mod:`sys` answers for the interpreter running the page:

    >>> _skipif("sys.version_info < (3, 10)", {})
    False

    The document's starting globals are in scope, and win:

    >>> _skipif("greeting == 'hello'", {"greeting": "hello"})
    True
    """
    # eval is the option's contract, not an oversight: sphinx.ext.doctest
    # defines :skipif: as a Python expression. The expression comes from a
    # document the project already runs as tests, so it grants no reach the
    # page's own examples do not have. It is evaluated while the document is
    # collected, which means ``--collect-only`` runs it too.
    return bool(eval(expression, {"sys": sys, **globs}))


def _merge_blocks(
    blocks: list[doctest.DocTest],
    name: str,
    filename: str,
    globs: dict[str, t.Any],
    keep: list[doctest.DocTest] | None = None,
) -> doctest.DocTest:
    r"""Merge one namespace's blocks into a single test.

    Each block keeps the line docutils reported for it, with blank lines
    standing in for the prose between two blocks, so a merged example reports
    the line it reports on its own and the ``%03d`` gutter of a failure still
    counts up to the failing ``>>>``.

    A block the lines above already reach follows them instead. Two blocks can
    claim overlapping lines: an ``.. include::`` numbers its nodes against the
    included file, and a reStructuredText doctest block reports its *last*
    line, so its examples already report lines further down the page than the
    block occupies.

    Parameters
    ----------
    blocks : list[doctest.DocTest]
        Blocks of one namespace, each parsed on its own, in the order they run.
    name : str
        Namespace name, which becomes the test name.
    filename : str
        Path failures are reported against.
    globs : dict[str, typing.Any]
        Globals the namespace starts with.
    keep : list[doctest.DocTest] or None
        Blocks whose examples the merged test runs, compared by identity.
        `None`, the default, keeps every block. A block left out still
        contributes its source and its spacing, so the blocks around it report
        the lines they reported before and a failure's gutter still shows what
        was passed over — only its examples are dropped.

    Returns
    -------
    doctest.DocTest
        One test, holding the examples of every block in `keep`, laid out
        across the page the blocks came from.

    Examples
    --------
    Two blocks six lines apart keep that distance, and each example reports the
    line its prompt sits on:

    >>> parser = doctest.DocTestParser()
    >>> def block(line, source):
    ...     return parser.get_doctest(source, {}, "page.md", "page.md", line)
    >>> merged = _merge_blocks(
    ...     [block(3, ">>> greeting = 'hello'"),
    ...      block(9, ">>> greeting.upper()\n'HELLO'")],
    ...     "page.md",
    ...     "page.md",
    ...     {},
    ... )
    >>> merged.name, merged.lineno
    ('page.md', 3)
    >>> merged.docstring.splitlines()
    [">>> greeting = 'hello'", '', '', '', '', '', '>>> greeting.upper()', "'HELLO'"]
    >>> [merged.lineno + example.lineno + 1 for example in merged.examples]
    [4, 10]

    A block whose line the one above already covers is appended after it:

    >>> merged = _merge_blocks(
    ...     [block(3, ">>> one = 1\n>>> two = 2\n>>> three = 3"),
    ...      block(4, ">>> one + two")],
    ...     "page.md",
    ...     "page.md",
    ...     {},
    ... )
    >>> merged.docstring.splitlines()
    ['>>> one = 1', '>>> two = 2', '>>> three = 3', '>>> one + two']
    """
    # Laid out by where each block sits on the page, but run in the order
    # given: a namespace hands its blocks over as setup, tests, cleanup, which
    # is rarely the order a reader meets them. Anchoring the text on the caller
    # ordering would report every example against whichever block happened to
    # come first in that sequence.
    in_page_order = sorted(blocks, key=lambda block: block.lineno or 0)
    origin = in_page_order[0].lineno or 0
    lines: list[str] = []
    offsets: dict[int, int] = {}
    for block in in_page_order:
        offset = max((block.lineno or 0) - origin, len(lines))
        lines.extend([""] * (offset - len(lines)))
        lines.extend((block.docstring or "").splitlines())
        offsets[id(block)] = offset
    examples: list[doctest.Example] = []
    for block in blocks:
        # A dropped block still pads and still shows its source, so the blocks
        # after it keep the lines they reported before and a failure's gutter
        # still shows what was passed over. Its examples are left untouched:
        # whoever takes them next positions them itself.
        if keep is not None and not any(block is kept for kept in keep):
            continue
        for example in block.examples:
            example.lineno += offsets[id(block)]
            examples.append(example)
    return doctest.DocTest(
        examples,
        globs,
        name,
        filename,
        origin,
        "\n".join(lines),
    )


class _CollectedBlock(t.NamedTuple):
    """One block of a page, parsed against one namespace.

    Attributes
    ----------
    position : int
        Where the block sits in the document, counted from zero. It is the
        number a block's name carries at ``"block"`` scope, and the number a
        block lifted out of its namespace is named for. Spelled ``position``
        rather than ``index`` because a :class:`tuple` already has an
        ``index``.
    block_type : str
        ``doctest``, ``testsetup``, ``testcleanup``, or the node's tag name.
    test : doctest.DocTest
        The block's examples, with its directive options already merged in.
    """

    position: int
    block_type: str
    test: doctest.DocTest


def _all_examples_skipped(test: doctest.DocTest) -> bool:
    r"""Return whether every example of `test` carries :data:`doctest.SKIP`.

    This is the question ``_pytest.doctest._check_all_skipped`` asks of an item
    before running it, and the answer decides whether pytest reports the item
    ``SKIPPED``. Asking it of a single block says whether that block would
    report, were it an item of its own.

    A block holding no examples answers ``False``: there is nothing in it to
    skip, and nothing for a reader to be told about.

    Parameters
    ----------
    test : doctest.DocTest
        Examples of one block.

    Returns
    -------
    bool
        Whether none of the block's examples is left to run.

    Examples
    --------
    >>> parser = doctest.DocTestParser()
    >>> def block(source):
    ...     return parser.get_doctest(source, {}, "page.rst", "page.rst", 0)

    >>> _all_examples_skipped(block(">>> 1 / 0  # doctest: +SKIP\n"))
    True
    >>> _all_examples_skipped(block(">>> 2 + 2\n4\n"))
    False

    A block only half of whose examples are gated still has one to run:

    >>> _all_examples_skipped(
    ...     block(">>> 1 / 0  # doctest: +SKIP\n>>> 2 + 2\n4\n")
    ... )
    False

    >>> _all_examples_skipped(block("Prose, and no prompts at all.\n"))
    False
    """
    return bool(test.examples) and all(
        example.options.get(doctest.SKIP, False) for example in test.examples
    )


def _split_skipped_blocks(
    blocks: list[_CollectedBlock],
) -> tuple[list[_CollectedBlock], list[_CollectedBlock]]:
    r"""Split a namespace's blocks into the ones it keeps and the ones it lifts out.

    A block whose every example is skipped binds nothing, so the namespace
    reaches the same state with it or without it. Merged in, though, it is
    silent: pytest reports a namespace skipped only when *no* example in it is
    left to run, so one gated block among running ones reports as a pass.
    Lifting it back out gives it an item of its own, which reports.

    A namespace with nothing left to run keeps every block, so it reports
    skipped once as a namespace rather than once per block.

    Parameters
    ----------
    blocks : list[_CollectedBlock]
        Every block of one namespace, in the order it runs.

    Returns
    -------
    tuple[list[_CollectedBlock], list[_CollectedBlock]]
        Blocks the namespace keeps, and blocks that become items of their own.
        The first is never empty: the namespace lifts a block out only when
        another one is left to run.

    Examples
    --------
    >>> parser = doctest.DocTestParser()
    >>> def block(index, source):
    ...     return _CollectedBlock(
    ...         index,
    ...         "doctest",
    ...         parser.get_doctest(source, {}, "page.rst", "page.rst", index),
    ...     )

    The gated block of a namespace that still runs is lifted out:

    >>> kept, lifted = _split_skipped_blocks([
    ...     block(0, ">>> value = 1\n"),
    ...     block(1, ">>> value = 999  # doctest: +SKIP\n"),
    ...     block(2, ">>> value\n1\n"),
    ... ])
    >>> [held.position for held in kept], [held.position for held in lifted]
    ([0, 2], [1])

    A namespace with nothing left to run keeps its blocks, so the one item it
    collects as reports skipped once:

    >>> kept, lifted = _split_skipped_blocks([
    ...     block(0, ">>> 1 / 0  # doctest: +SKIP\n"),
    ...     block(1, ">>> 2 / 0  # doctest: +SKIP\n"),
    ... ])
    >>> [held.position for held in kept], [held.position for held in lifted]
    ([0, 1], [])
    """
    runnable = any(
        not example.options.get(doctest.SKIP, False)
        for held in blocks
        for example in held.test.examples
    )
    if not runnable:
        return list(blocks), []
    return (
        [held for held in blocks if not _all_examples_skipped(held.test)],
        [held for held in blocks if _all_examples_skipped(held.test)],
    )


def _lifted_name(namespace: str, position: int) -> str:
    """Return the name a block lifted out of `namespace` collects under.

    It is the namespace's own name with the block's document position, the
    same ``name[n]`` shape a block that names no group already carries at
    ``"block"`` scope. So a gated block reads the same in ``--collect-only``
    and answers to the same node id whether the page shares a namespace or
    not, and it cannot collide with the namespace it came out of.

    Parameters
    ----------
    namespace : str
        Namespace the block was lifted out of.
    position : int
        Where the block sits in the document, counted from zero.

    Returns
    -------
    str
        Name for the block's own test.

    Examples
    --------
    >>> _lifted_name("intro", 3)
    'intro[3]'

    A page sharing one namespace names its blocks as ``"block"`` scope would:

    >>> _lifted_name("page.md", 3)
    'page.md[3]'
    """
    return f"{namespace}[{position}]"


class DocTestFinderNameDoesNotExist(ValueError):
    """Raised with doctest lookup name not provided."""

    def __init__(self, string: str) -> None:
        super().__init__(
            "DocTestFinder.find: name must be given "
            f"when string.__name__ doesn't exist: {type(string)!r}",
        )


class DocutilsDocTestFinder:
    r"""DocTestFinder for doctest-docutils.

    Class used to extract the DocTests relevant to a docutils file. Doctests are
    extracted from the following directive types: doctest_block (doctest),
    DocTestDirective. Myst-parser is also supported for parsing markdown files.

    Blocks that name the same group — ``.. doctest:: intro`` in
    reStructuredText, ``{doctest} intro`` in Markdown — are one test, so a name
    bound in the group's first block is still bound in its last. Blocks that
    name no group get a namespace each unless `namespace_scope` widens them to
    the page.

    A block whose every example is skipped is the exception: it binds nothing,
    so it comes back as a test of its own, named for its namespace and for
    where it sits on the page, and reports as the skip it is instead of
    vanishing into a namespace that runs.

    Examples
    --------
    Two blocks in group ``intro`` come back as one test named for the group:

    >>> page = "\n".join([
    ...     "```{doctest} intro",
    ...     ">>> greeting = 'hello'",
    ...     "```",
    ...     "",
    ...     "Narrative prose between the blocks.",
    ...     "",
    ...     "```{doctest} intro",
    ...     ">>> greeting.upper()",
    ...     "'HELLO'",
    ...     "```",
    ... ])
    >>> tests = DocutilsDocTestFinder().find(page, "page.md")
    >>> [(test.name, len(test.examples)) for test in tests]
    [('intro', 2)]

    A gated block between them is its own test, named for where it sits:

    >>> gated = page.replace(
    ...     "Narrative prose between the blocks.",
    ...     "```{doctest} intro\n>>> greeting = 'nope'  # doctest: +SKIP\n```",
    ... )
    >>> [(test.name, len(test.examples)) for test in
    ...  DocutilsDocTestFinder().find(gated, "page.md")]
    [('intro', 2), ('intro[1]', 1)]
    """

    def __init__(
        self,
        verbose: bool = False,
        parser: doctest.DocTestParser = parser,
        namespace_scope: NamespaceScope = DEFAULT_NAMESPACE_SCOPE,
    ) -> None:
        """Create a new doctest finder.

        The optional argument `parser` specifies a class or function that should be used
        to create new DocTest objects (or objects that implement the same interface as
        DocTest).  The signature for this factory function should match the signature
        of the DocTest constructor.

        Parameters
        ----------
        verbose : bool
            Log each document as it is searched.
        parser : doctest.DocTestParser
            Parser that turns a block's source into a :class:`doctest.DocTest`.
        namespace_scope : NamespaceScope
            Namespace a block that names no group runs in: ``"block"`` gives it
            one of its own, ``"document"`` shares one across the page.

        Raises
        ------
        NamespaceScopeError
            If `namespace_scope` names no known scope.
        """
        _ensure_directives_registered()
        self._parser = parser
        self._verbose = verbose
        self._namespace_scope = _parse_namespace_scope(namespace_scope)

    def find(
        self,
        string: str,
        name: str | None = None,
        globs: dict[str, t.Any] | None = None,
        extraglobs: dict[str, t.Any] | None = None,
    ) -> list[doctest.DocTest]:
        r"""Return list of the DocTests defined by given string (its parsed directives).

        One DocTest comes back per namespace, plus one for each fully skipped
        block a running namespace lifted out: the blocks that share a namespace
        are merged into one, and the rest stand alone. The globals for each
        DocTest is formed by combining `globs` and `extraglobs` (bindings in
        `extraglobs` override bindings in `globs`).  A new copy of the globals
        dictionary is created for each DocTest.  If `globs` is not specified,
        then it defaults to the module's `__dict__`, if specified, or {} otherwise.
        If `extraglobs` is not specified, then it defaults to {}.

        Tests come back in document order, the order a reader meets the blocks.

        Examples
        --------
        >>> page = "\n".join(f"```python\n>>> {n}\n{n}\n```\n" for n in range(11))
        >>> [test.name for test in DocutilsDocTestFinder().find(page, "page.md")][-2:]
        ['page.md[9]', 'page.md[10]']

        A test is named for the page it came from, never for the path it was
        collected under, so its pytest node id reads the same on every machine:

        >>> finder = DocutilsDocTestFinder()
        >>> [test.name for test in finder.find(">>> 2 + 2\n4\n", "docs/page.rst")]
        ['page.rst[0]']

        A page sharing one namespace names a gated block the same way ``block``
        scope would, so the node id that selects it does not move with the
        scope:

        >>> page = "\n".join([
        ...     "```python", ">>> value = 1", "```", "",
        ...     "```python", ">>> value = 999  # doctest: +SKIP", "```", "",
        ...     "```python", ">>> value", "1", "```",
        ... ])
        >>> shared = DocutilsDocTestFinder(namespace_scope="document")
        >>> [test.name for test in shared.find(page, "page.md")]
        ['page.md', 'page.md[1]']
        >>> [test.name for test in DocutilsDocTestFinder().find(page, "page.md")]
        ['page.md[0]', 'page.md[1]', 'page.md[2]']
        """
        # If name was not specified, then extract it from the string.
        if name is None:
            name = getattr(string, "__name__", None)
            if name is None:
                raise DocTestFinderNameDoesNotExist(string=string)

        # Initialize globals, and merge in extraglobs.
        globs = {} if globs is None else globs.copy()
        if extraglobs is not None:
            globs.update(extraglobs)
        if "__name__" not in globs:
            globs["__name__"] = "__main__"  # provide a default module name

        tests: list[doctest.DocTest] = []
        source_path: pathlib.Path | None = (
            pathlib.Path(name) if name is not None else None
        )
        self._find(tests, string, name, globs, {}, source_path)
        # ``_find`` appends in document-traversal order; leave it that way.
        # ``DocTest.__lt__`` compares names, and a name carries its block index
        # as text, so sorting runs ``page.md[10]`` ahead of ``page.md[1]``.
        return tests

    def _find(
        self,
        tests: list[doctest.DocTest],
        string: str,
        name: str,
        globs: dict[str, t.Any],
        seen: dict[int, int],
        source_path: pathlib.Path | None = None,
    ) -> None:
        """Find tests for the given string, and add them to `tests`."""
        # If we've already processed this string, then ignore it.
        if id(string) in seen:
            return
        seen[id(string)] = 1

        ext = pathlib.Path(name).suffix
        if ext == ".md":
            import myst_parser.parsers.docutils_
            from myst_parser.config.main import MdParserConfig
            from myst_parser.mdit_to_docutils.base import (
                DocutilsRenderer,
                make_document,
            )
            from myst_parser.parsers.mdit import create_md_parser

            DocutilsParser = myst_parser.parsers.docutils_.Parser
            config: MdParserConfig = MdParserConfig(commonmark_only=False)
            md_parser = create_md_parser(config, DocutilsRenderer)

            doc = make_document(
                source_path=str(source_path),
                parser_cls=DocutilsParser,
            )
            md_parser.options["document"] = doc
            md_parser.render(string)
        else:
            import docutils.utils
            from docutils.frontend import OptionParser
            from docutils.parsers.rst import Parser

            parser = Parser()
            settings = OptionParser(components=(Parser,)).get_default_values()

            doc = docutils.utils.new_document(
                source_path=str(source_path),
                settings=settings,
            )
            parser.parse(string, doc)

        def condition(node: Node) -> bool:
            return (
                (
                    isinstance(node, (nodes.literal_block, nodes.comment))
                    and "testnodetype" in node
                )
                or (
                    isinstance(node, nodes.literal_block)
                    and re.match(
                        doctest.DocTestParser._EXAMPLE_RE,  # type:ignore
                        node.astext(),
                    )
                    is not None
                )
                or isinstance(node, nodes.doctest_block)
            )

        document_name = pathlib.Path(name).name
        # Namespaces keep insertion order, so the merged tests come back in the
        # order the reader meets each namespace's first block. Each holds its
        # setup, test, and cleanup blocks apart: sphinx.ext.doctest runs a
        # group's setup before its tests and its cleanup after, whatever order
        # the page wrote them in, and a testsetup exists to be movable.
        namespaces: dict[str, dict[str, list[_CollectedBlock]]] = {}

        block_nodes = list(findall(doc)(condition))
        declared = [
            _node_groups(node)
            for node in block_nodes
            if isinstance(node, nodes.Element)
        ]
        # A block joins every group it names. ``*`` means every group the
        # document declares, so it can only be resolved once the page has been
        # read; a page whose only blocks are wildcards has no group to join, so
        # each keeps its own namespace.
        memberships: list[list[str]] = [
            []
            if _WILDCARD_GROUP in groups
            else (
                groups
                or [
                    _namespace_name(
                        None,
                        self._namespace_scope,
                        document_name,
                        idx,
                    )
                ]
            )
            for idx, groups in enumerate(declared)
        ]
        ordered: list[str] = []
        for names in memberships:
            for candidate in names:
                if candidate not in ordered:
                    ordered.append(candidate)
        for idx, groups in enumerate(declared):
            if _WILDCARD_GROUP in groups:
                memberships[idx] = list(ordered) or [
                    _namespace_name(None, self._namespace_scope, document_name, idx)
                ]

        for idx, node in enumerate(block_nodes):
            assert isinstance(node, nodes.Element)
            block_type = str(node.get("testnodetype", node.tagname))
            lineno = _node_line(node)
            # The block's own flags, before its examples get a say. A true
            # ``:skipif:`` joins them as ``+SKIP``: one spelling of "do not run
            # this" that a reader can predict from the other, and one path
            # through the runner, which keeps the block collected, reported and
            # selectable by node id instead of vanishing from the page.
            options = dict(node.get("options") or {})
            gated = False
            skipif = node.get("skipif")
            if skipif is not None:
                try:
                    gated = _skipif(skipif, globs)
                except Exception as exc:
                    raise SkipifExpressionError(skipif, name, lineno, exc) from exc
                if gated:
                    logger.debug(
                        "doctest block skipped by skipif",
                        extra={
                            "doctest_source_file": name,
                            "doctest_block_type": block_type,
                        },
                    )
            # ``node["test"]`` is the source before the directive trimmed
            # ``# doctest:`` flags out of the code a reader sees. Both
            # spellings have the same line count, so either positions the
            # block the same way.
            source = str(node.get("test") or node.astext())
            for namespace in memberships[idx]:
                logger.debug(
                    "doctest block collected into namespace %s",
                    namespace,
                    extra={
                        "doctest_source_file": name,
                        "doctest_block_type": block_type,
                    },
                )
                # Parsed once per namespace: _merge_blocks shifts
                # ``example.lineno`` in place, so two namespaces sharing one
                # block's examples would shift them twice.
                test = self._get_test(
                    string=source,
                    name=namespace,
                    filename=name,
                    globs=globs,
                    lineno=lineno,
                )
                if options or gated:
                    for example in test.examples:
                        # A directive's ``:options:`` set the block's defaults;
                        # an example's own inline flags win, as in
                        # sphinx.ext.doctest.
                        merged = dict(options)
                        merged.update(example.options)
                        if gated:
                            # A ``:skipif:`` is a gate, not a default.
                            # sphinx.ext.doctest drops the block before its
                            # source is ever read, so nothing written inside it
                            # can turn the gate off — and an example that did
                            # would run on exactly the interpreter or platform
                            # the condition was guarding against.
                            merged[doctest.SKIP] = True
                        example.options = merged
                phases = namespaces.setdefault(
                    namespace,
                    {"testsetup": [], "test": [], "testcleanup": []},
                )
                phases[block_type if block_type in phases else "test"].append(
                    _CollectedBlock(idx, block_type, test),
                )

        # Anchored on the document position of the first block each test holds,
        # so the tests come back in the order a reader meets them. A namespace
        # anchors where it now starts, which is where it started before if it
        # lifted nothing out. Ties — one block joining two groups — keep the
        # order the page declared them in, which a stable sort preserves.
        anchored: list[tuple[int, int, doctest.DocTest]] = []
        for namespace, phases in namespaces.items():
            in_phase_order = [
                *phases["testsetup"],
                *phases["test"],
                *phases["testcleanup"],
            ]
            kept, lifted = _split_skipped_blocks(in_phase_order)
            anchored.append(
                (
                    # Every block anchors its namespace, lifted or not, so
                    # lifting the first one cannot let another namespace
                    # declared below it collect first.
                    min(held.position for held in in_phase_order),
                    # Ties with a block this namespace lifted break toward the
                    # block: it sits at that line, the namespace resumes later.
                    min(held.position for held in kept),
                    # Merged over every block, so the padding a lifted block
                    # contributed stays and the blocks after it keep the lines
                    # they reported before it was lifted.
                    _merge_blocks(
                        [held.test for held in in_phase_order],
                        namespace,
                        name,
                        globs,
                        keep=[held.test for held in kept],
                    ),
                ),
            )
            for held in lifted:
                lifted_name = _lifted_name(namespace, held.position)
                logger.debug(
                    "skipped doctest block lifted out of namespace %s as %s",
                    namespace,
                    lifted_name,
                    extra={
                        "doctest_source_file": name,
                        "doctest_block_type": held.block_type,
                    },
                )
                anchored.append(
                    (
                        held.position,
                        held.position,
                        _merge_blocks([held.test], lifted_name, name, globs),
                    ),
                )
        anchored.sort(key=lambda entry: (entry[0], entry[1]))
        tests.extend(test for _, _, test in anchored)
        logger.debug(
            "parsed document into %d test(s)",
            len(anchored),
            extra={"doctest_source_file": name},
        )
        if self._verbose:
            logger.info(
                "found %d test(s)",
                len(anchored),
                extra={"doctest_source_file": name},
            )

    def _get_test(
        self,
        string: str,
        name: str,
        filename: str,
        globs: dict[str, t.Any],
        lineno: int,
    ) -> doctest.DocTest:
        """Return a DocTest for one block's source."""
        return self._parser.get_doctest(string, globs, name, filename, lineno)


class TestDocutilsPackageRelativeError(Exception):
    """Raise when doctest_docutils is called for package not relative to module."""

    def __init__(self) -> None:
        super().__init__(
            "Package may only be specified for module-relative paths.",
        )


def testdocutils(
    filename: str,
    module_relative: bool = True,
    name: str | None = None,
    package: str | types.ModuleType | None = None,
    globs: dict[str, t.Any] | None = None,
    verbose: bool | None = None,
    report: bool = True,
    optionflags: int = 0,
    extraglobs: dict[str, t.Any] | None = None,
    raise_on_error: bool = False,
    parser: doctest.DocTestParser = parser,
    encoding: str | None = None,
    namespace_scope: NamespaceScope = DEFAULT_NAMESPACE_SCOPE,
) -> doctest.TestResults:
    r"""Docutils-based test entrypoint.

    Based on doctest.testfile at python 3.10

    Parameters
    ----------
    namespace_scope : NamespaceScope
        Namespace the blocks that name no group run in. See
        :class:`DocutilsDocTestFinder`; the other parameters follow
        :func:`doctest.testfile`.

    Returns
    -------
    doctest.TestResults
        Failed examples, and examples attempted.

    Examples
    --------
    A page whose second block reads a name the first one bound fails while each
    block keeps its own namespace, and passes once the page shares one:

    >>> import contextlib, io, pathlib, tempfile
    >>> directory = tempfile.TemporaryDirectory()
    >>> page = pathlib.Path(directory.name) / "page.rst"
    >>> _ = page.write_text(
    ...     ">>> greeting = 'hello'\n\n>>> greeting.upper()\n'HELLO'\n",
    ...     encoding="utf-8",
    ... )

    >>> def run(**kwargs):
    ...     with contextlib.redirect_stdout(io.StringIO()):
    ...         return testdocutils(
    ...             str(page), module_relative=False, report=False, **kwargs
    ...         )

    >>> run()
    TestResults(failed=1, attempted=2)

    >>> run(namespace_scope="document")
    TestResults(failed=0, attempted=2)

    >>> directory.cleanup()
    """
    global master

    if package and not module_relative:
        raise TestDocutilsPackageRelativeError

    # Keep the absolute file paths. This is needed for Include directies to work.
    # The absolute path will be applied to source_path when creating the docutils doc.
    _ensure_directives_registered()
    text, _ = doctest._load_testfile(  # type: ignore
        filename,
        package,
        module_relative,
        encoding or "utf-8",
    )

    # If no name was given, then use the file's name.
    if name is None:
        name = pathlib.Path(filename).stem

    # Assemble the globals.
    globs = {} if globs is None else globs.copy()
    if extraglobs is not None:
        globs.update(extraglobs)
    if "__name__" not in globs:
        globs["__name__"] = "__main__"

    # Find, parse, and run all tests in the given module.
    finder = DocutilsDocTestFinder(namespace_scope=namespace_scope)

    runner: doctest.DebugRunner | doctest.DocTestRunner

    if raise_on_error:
        runner = doctest.DebugRunner(verbose=verbose, optionflags=optionflags)
    else:
        runner = doctest.DocTestRunner(verbose=verbose, optionflags=optionflags)

    for test in finder.find(text, filename, globs=globs, extraglobs=extraglobs):
        runner.run(test)

    if report:
        runner.summarize()

    if master is None:
        master = runner
    else:
        master.merge(runner)

    return doctest.TestResults(runner.failures, runner.tries)


def _test() -> int:
    """Execute doctest module via CLI.

    Port changes from standard library at 3.10:

    - Sets up logging.basicLogging(level=logging.DEBUG) w/ args.verbose
    """
    import argparse

    p = argparse.ArgumentParser(description="doctest runner")
    p.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="logger.debug very verbose output for all tests",
    )
    p.add_argument(
        "--log-level",
        action="store",
        default=False,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Log level",
    )
    p.add_argument(
        "-o",
        "--option",
        action="append",
        choices=doctest.OPTIONFLAGS_BY_NAME.keys(),
        default=[],
        help=(
            "specify a doctest option flag to apply"
            " to the test run; may be specified more"
            " than once to apply multiple options"
        ),
    )
    p.add_argument(
        "-f",
        "--fail-fast",
        action="store_true",
        help=(
            "stop running tests after first failure (this"
            " is a shorthand for -o FAIL_FAST, and is"
            " in addition to any other -o options)"
        ),
    )
    p.add_argument(
        "--docutils",
        action="store_true",
        help=("Force parsing using docutils (reStructuredText, markdown)"),
    )
    p.add_argument(
        "--namespace-scope",
        action="store",
        choices=NAMESPACE_SCOPES,
        default=DEFAULT_NAMESPACE_SCOPE,
        help=(
            "namespace the blocks that name no group run in: block (default,"
            " one each) or document (one for the page); blocks that name a"
            " group always share that group's namespace"
        ),
    )
    p.add_argument("file", nargs="+", help="file containing the tests to run")
    args = p.parse_args()

    testfiles = args.file
    # Verbose used to be handled by the "inspect argv" magic in DocTestRunner,
    # but since we are using argparse we are passing it manually now.
    verbose = args.verbose
    if args.log_level:
        logging.basicConfig(level=args.log_level)
        # Quiet markdown-it
        md_logger = logging.getLogger("markdown_it.rules_block")
        md_logger.setLevel(logging.INFO)
    options = 0
    for option in args.option:
        options |= doctest.OPTIONFLAGS_BY_NAME[option]
    if args.fail_fast:
        options |= doctest.FAIL_FAST
    for filename in testfiles:
        if filename.endswith((".rst", ".md")) or args.docutils:
            _ensure_directives_registered()
            failures, _ = testdocutils(  # type: ignore[misc,unused-ignore]
                filename,
                module_relative=False,
                verbose=verbose,
                optionflags=options,
                namespace_scope=args.namespace_scope,
            )
        elif filename.endswith(".py"):
            # It is a module -- insert its dir into sys.path and try to
            # import it. If it is part of a package, that possibly
            # won't work because of package imports.
            dirname, filename = os.path.split(filename)
            sys.path.insert(0, dirname)
            m = __import__(filename[:-3])
            del sys.path[0]
            failures, _ = doctest.testmod(m, verbose=verbose, optionflags=options)  # type:ignore[misc,unused-ignore]
        else:
            failures, _ = doctest.testfile(  # type:ignore[misc,unused-ignore]
                filename,
                module_relative=False,
                verbose=verbose,
                optionflags=options,
            )
        if failures:
            return 1
    return 0


if __name__ == "__main__":
    setup()
    sys.exit(_test())
