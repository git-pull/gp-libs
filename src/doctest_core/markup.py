"""Docutils and MyST front ends for doctest core."""

from __future__ import annotations

import doctest
import io
import pathlib
import re
import textwrap
import typing as t
import warnings

from docutils import nodes
from docutils.frontend import OptionParser
from docutils.parsers.rst import Directive, Parser, directives
from docutils.utils import new_document

from .model import Diagnostic, ParsedBlock, ParsedOutput, ParseResult
from .settings import ParseSettings

if t.TYPE_CHECKING:
    from .contracts import DocumentParser
    from .registry import RegistrySnapshot


_BLANKLINE_RE = re.compile(r"^\s*<BLANKLINE>", re.MULTILINE)
_DOCTEST_OPTION_RE = re.compile(r"[ \t]*#\s*doctest:.+$", re.MULTILINE)
_TEST_KINDS = frozenset(
    {"doctest", "testsetup", "testcleanup", "testcode", "testoutput"},
)
_REQUIRED_DIRECTIVES = (*sorted(_TEST_KINDS), "tab")


class _TestDirective(Directive):
    """Create nodes carrying the Sphinx doctest attribute vocabulary."""

    has_content = True
    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = True

    def run(self) -> list[nodes.Node]:
        """Return one node stamped with inert doctest metadata."""
        code = "\n".join(self.content)
        test = code
        trim = "no-trim-doctest-flags" not in self.options
        if self.name == "doctest" and trim:
            display = _BLANKLINE_RE.sub("", code)
            display = _DOCTEST_OPTION_RE.sub("", display)
        else:
            display = code

        node_type: type[nodes.TextElement] = nodes.literal_block
        hidden = "hide" in self.options
        if self.name in {"testsetup", "testcleanup"} or hidden:
            node_type = nodes.comment

        groups = (
            [item.strip() for item in self.arguments[0].split(",")]
            if self.arguments
            else ["default"]
        )
        node = node_type(
            display,
            display,
            testnodetype=self.name,
            groups=groups,
            hidden=hidden,
        )
        source, line = self.state_machine.get_source_and_line(self.lineno)
        node.source = source
        node.line = line
        node["testline"] = self.content_offset + 1
        if test != display:
            node["test"] = test
        if self.name == "doctest":
            node["language"] = "pycon3"

        node["options"] = self._parse_options()
        for key in ("skipif", "pyversion"):
            if key in self.options:
                node[key] = self.options[key]
        if "trim-doctest-flags" in self.options:
            node["trim_flags"] = True
        elif "no-trim-doctest-flags" in self.options:
            node["trim_flags"] = False
        return [node]

    def _parse_options(self) -> dict[int, bool]:
        """Parse Sphinx ``:options:`` into doctest's integer flag mapping."""
        parsed: dict[int, bool] = {}
        value = self.options.get("options")
        if not isinstance(value, str):
            return parsed
        for option in value.replace(",", " ").split():
            if len(option) < 2 or option[0] not in "+-":
                self.state.document.reporter.warning(
                    f"missing '+' or '-' in '{option}' option",
                    line=self.lineno,
                )
                continue
            flag = doctest.OPTIONFLAGS_BY_NAME.get(option[1:])
            if flag is None:
                self.state.document.reporter.warning(
                    f"'{option[1:]}' is not a valid doctest option",
                    line=self.lineno,
                )
                continue
            parsed[flag] = option[0] == "+"
        return parsed


class TestsetupDirective(_TestDirective):
    """Parse a Sphinx-compatible ``testsetup`` directive."""

    option_spec: t.ClassVar = {
        "hide": directives.flag,
        "skipif": directives.unchanged_required,
    }


class TestcleanupDirective(_TestDirective):
    """Parse a Sphinx-compatible ``testcleanup`` directive."""

    option_spec: t.ClassVar = {
        "hide": directives.flag,
        "skipif": directives.unchanged_required,
    }


class DoctestDirective(_TestDirective):
    """Parse a Sphinx-compatible ``doctest`` directive."""

    option_spec: t.ClassVar = {
        "hide": directives.flag,
        "no-trim-doctest-flags": directives.flag,
        "options": directives.unchanged,
        "pyversion": directives.unchanged_required,
        "skipif": directives.unchanged_required,
        "trim-doctest-flags": directives.flag,
    }


class TestcodeDirective(_TestDirective):
    """Parse a Sphinx-compatible ``testcode`` directive."""

    option_spec: t.ClassVar = {
        "hide": directives.flag,
        "no-trim-doctest-flags": directives.flag,
        "pyversion": directives.unchanged_required,
        "skipif": directives.unchanged_required,
        "trim-doctest-flags": directives.flag,
    }


class TestoutputDirective(_TestDirective):
    """Parse a Sphinx-compatible ``testoutput`` directive."""

    option_spec: t.ClassVar = {
        "hide": directives.flag,
        "no-trim-doctest-flags": directives.flag,
        "options": directives.unchanged,
        "pyversion": directives.unchanged_required,
        "skipif": directives.unchanged_required,
        "trim-doctest-flags": directives.flag,
    }


class MockTabDirective(Directive):
    """Parse tab content when sphinx-inline-tabs is not installed."""

    has_content = True

    def run(self) -> list[nodes.Node]:
        """Return a transparent container around nested content."""
        self.assert_has_content()
        content = nodes.container("", is_div=True, classes=["tab-content"])
        self.state.nested_parse(self.content, self.content_offset, content)
        return [content]


_DIRECTIVE_TYPES: t.Mapping[str, type[Directive]] = {
    "doctest": DoctestDirective,
    "testsetup": TestsetupDirective,
    "testcleanup": TestcleanupDirective,
    "testcode": TestcodeDirective,
    "testoutput": TestoutputDirective,
    "tab": MockTabDirective,
}


def ensure_directives_registered() -> None:
    """Register missing standalone directives without replacing Sphinx's.

    >>> ensure_directives_registered()
    >>> all(name in directives._directives for name in _REQUIRED_DIRECTIVES)
    True
    """
    registry = t.cast(dict[str, t.Any], directives.__dict__["_directives"])
    for name, directive in _DIRECTIVE_TYPES.items():
        if name not in registry:
            directives.register_directive(name, directive)


def _settings(parser_type: type[Parser]) -> t.Any:
    """Build quiet docutils settings while retaining reporter messages."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        settings = OptionParser(components=(parser_type,)).get_default_values()
    settings.report_level = 5
    settings.halt_level = 6
    settings.warning_stream = io.StringIO()
    return settings


def _diagnostic_from_message(message: nodes.system_message) -> Diagnostic:
    """Convert one docutils system message to a typed diagnostic."""
    level_number = int(message.get("level", 1))
    level: t.Literal["info", "warning", "error"]
    if level_number >= 3:
        level = "error"
    elif level_number >= 2:
        level = "warning"
    else:
        level = "info"
    text = message.astext()
    code = None
    if "Unknown interpreted text role" in text or "No role entry for" in text:
        code = "docutils.unknown-role"
    elif "Unknown directive type" in text or "No directive entry for" in text:
        code = "docutils.unknown-directive"
    return Diagnostic(
        level=level,
        code=code,
        message=text,
        path=pathlib.Path(message.source or "<string>"),
        line=message.line,
    )


def _attach_diagnostics(document: nodes.document) -> list[Diagnostic]:
    """Attach an observer and return its mutable capture list."""
    captured: list[Diagnostic] = []

    def observe(message: nodes.system_message) -> None:
        captured.append(_diagnostic_from_message(message))

    document.reporter.attach_observer(observe)
    return captured


class RstDocumentParser:
    """Parse reStructuredText into a docutils document."""

    suffixes: t.ClassVar = frozenset({".rst", ".txt"})

    def parse(
        self,
        text: str,
        path: pathlib.Path,
        *,
        settings: ParseSettings,
    ) -> tuple[nodes.document, tuple[Diagnostic, ...]]:
        """Parse text and return its doctree and diagnostics."""
        del settings
        ensure_directives_registered()
        parser = Parser()
        document = new_document(str(path), settings=_settings(Parser))
        captured = _attach_diagnostics(document)
        parser.parse(text, document)
        return document, tuple(captured)


class MystDocumentParser:
    """Parse MyST Markdown into a docutils document."""

    suffixes: t.ClassVar = frozenset({".md"})

    def parse(
        self,
        text: str,
        path: pathlib.Path,
        *,
        settings: ParseSettings,
    ) -> tuple[nodes.document, tuple[Diagnostic, ...]]:
        """Parse text and return its doctree and diagnostics."""
        del settings
        from myst_parser.config.main import MdParserConfig
        from myst_parser.mdit_to_docutils.base import DocutilsRenderer
        from myst_parser.parsers.docutils_ import Parser as MystParser
        from myst_parser.parsers.mdit import create_md_parser

        ensure_directives_registered()
        document = new_document(str(path), settings=_settings(MystParser))
        captured = _attach_diagnostics(document)
        parser = create_md_parser(
            MdParserConfig(commonmark_only=False),
            DocutilsRenderer,
        )
        parser.options["document"] = document
        parser.render(text)
        _stamp_myst_source_lines(document, text)
        return document, tuple(captured)


def _normalize_body(value: str) -> str:
    """Dedent a node body and preserve the executable trailing newline."""
    body = textwrap.dedent(value).strip("\n")
    return f"{body}\n" if body else ""


def _groups(node: nodes.Element) -> tuple[str, ...]:
    """Narrow a node's untyped group attribute."""
    value: object = node.get("groups", ())
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple)):
        values = t.cast(list[object] | tuple[object, ...], value)
        return tuple(str(item) for item in values)
    return ()


def _options(node: nodes.Element) -> t.Mapping[int, bool]:
    """Narrow and copy a node's untyped option mapping."""
    value: object = node.get("options", {})
    if not isinstance(value, dict):
        return {}
    options = t.cast(dict[object, object], value)
    return {
        flag: bool(enabled)
        for flag, enabled in options.items()
        if isinstance(flag, int)
    }


def _optional_text(node: nodes.Element, name: str) -> str | None:
    """Validate an optional text attribute at the typed-model boundary.

    >>> node = nodes.literal_block("", "", skipif="enabled")
    >>> _optional_text(node, "skipif")
    'enabled'
    """
    value: object = node.get(name)
    if value is None or isinstance(value, str):
        return value
    message = f"{name} node attribute must be str or None, got {type(value).__name__}"
    raise TypeError(message)


def _node_kind(node: nodes.Node) -> str | None:
    """Return the registered kind represented by a doctree node."""
    if isinstance(node, nodes.Element):
        stamped = node.get("testnodetype")
        if isinstance(stamped, str) and stamped:
            return stamped
    if isinstance(node, nodes.doctest_block):
        return "doctest"
    if isinstance(node, nodes.literal_block) and re.match(
        doctest.DocTestParser._EXAMPLE_RE,  # type: ignore[attr-defined]
        node.astext(),
    ):
        return "doctest"
    return None


def _stamp_myst_source_lines(doctree: nodes.document, text: str) -> None:
    r"""Retain root-document body lines lost from MyST literal-block nodes.

    >>> tree = new_document("guide.md")
    >>> node = nodes.literal_block(">>> 1 + 1\n2\n", ">>> 1 + 1\n2\n")
    >>> node.source, node.line = "guide.md", 1
    >>> tree += node
    >>> _stamp_myst_source_lines(tree, "```\n>>> 1 + 1\n2\n```\n")
    >>> node["doctest_core_line"]
    2
    """
    lines = text.splitlines()
    document_source = doctree.current_source or doctree.get("source")
    for node in doctree.findall(nodes.literal_block):
        if _node_kind(node) is None or node.line is None:
            continue
        if document_source and node.source != document_source:
            continue
        source = _normalize_body(str(node.get("test", node.astext())))
        if not source:
            continue
        first_line = source.splitlines()[0].strip()
        for index in range(max(node.line - 1, 0), len(lines)):
            if lines[index].strip() == first_line:
                node["doctest_core_line"] = index + 1
                break


def _node_line(node: nodes.Element, source: str) -> int | None:
    """Normalize parser-specific line conventions to the first body line."""
    if ":docstring of " in pathlib.Path(node.source or "").name:
        return None
    core_line = node.get("doctest_core_line")
    if isinstance(core_line, int):
        return core_line
    suffix = pathlib.Path(node.source or "").suffix
    if suffix == ".md" and isinstance(node, nodes.literal_block):
        if node.line is None:
            return None
        local_testline = node.get("testline")
        if isinstance(local_testline, int):
            return node.line + local_testline
        return node.line + 1
    testline = node.get("testline")
    if isinstance(testline, int):
        return testline
    if node.line is None:
        return None
    if isinstance(node, nodes.doctest_block) and suffix != ".md":
        return node.line - len(source.rstrip("\n").splitlines()) + 1
    return node.line


def extract_blocks(
    doctree: nodes.document,
    *,
    settings: ParseSettings | None = None,
    registry: RegistrySnapshot | None = None,
) -> ParseResult:
    """Extract typed doctest records from an existing resolved doctree.

    >>> from docutils import nodes
    >>> tree = nodes.document("", "")
    >>> extract_blocks(tree).blocks
    ()
    """
    if registry is None:
        from .registry import build_registry

        registry = build_registry()
    settings = settings or ParseSettings()
    output_kinds = frozenset(
        registration.value.pairs_with
        for registration in registry.block_kinds.values()
        if registration.value.pairs_with is not None
    )
    blocks: list[ParsedBlock] = []
    outputs: list[ParsedOutput] = []
    block_ordinal = 0
    document_order = 0
    for node in doctree.findall():
        kind = _node_kind(node)
        if kind is None or not isinstance(node, nodes.Element):
            continue
        source = _normalize_body(str(node.get("test", node.astext())))
        path = pathlib.Path(node.source or doctree.source or "<string>")
        line = _node_line(node, source)
        groups = _groups(node)
        options = _options(node)
        skipif = _optional_text(node, "skipif")
        pyversion = _optional_text(node, "pyversion")
        if kind in output_kinds:
            outputs.append(
                ParsedOutput(
                    kind=kind,
                    text=source,
                    path=path,
                    line=line,
                    document_order=document_order,
                    groups=groups,
                    options=options,
                    skipif=skipif,
                    pyversion=pyversion,
                ),
            )
        elif kind in registry.block_kinds:
            blocks.append(
                ParsedBlock(
                    kind=kind,
                    source=source,
                    path=path,
                    line=line,
                    document_order=document_order,
                    block_ordinal=block_ordinal,
                    groups=groups,
                    options=options,
                    skipif=skipif,
                    pyversion=pyversion,
                    hidden=isinstance(node, nodes.comment)
                    or bool(node.get("hidden", False)),
                ),
            )
            block_ordinal += 1
        document_order += 1

    diagnostics = tuple(
        diagnostic
        for node in doctree.findall(nodes.system_message)
        if (diagnostic := _diagnostic_from_message(node)).code
        not in settings.suppressed_diagnostics
    )
    return ParseResult(tuple(blocks), tuple(outputs), diagnostics)


def _parser_for_path(
    path: pathlib.Path,
    registry: RegistrySnapshot,
) -> DocumentParser:
    """Select one parser by its declared suffix."""
    matches = [
        registration.value
        for registration in registry.document_parsers.values()
        if path.suffix in registration.value.suffixes
    ]
    if len(matches) != 1:
        message = f"expected one document parser for suffix {path.suffix!r}"
        raise ValueError(message)
    return matches[0]


def _merge_diagnostics(
    parser_diagnostics: t.Iterable[Diagnostic],
    tree_diagnostics: t.Iterable[Diagnostic],
    settings: ParseSettings,
) -> tuple[Diagnostic, ...]:
    """Merge parser channels and prefer tree copies with source provenance.

    >>> diagnostic = Diagnostic("error", "example", "bad", pathlib.Path("x"), 1)
    >>> merged = _merge_diagnostics((diagnostic,), (diagnostic,), ParseSettings())
    >>> (len(merged), merged[0].line)
    (1, 1)
    """
    tree = [
        diagnostic
        for diagnostic in tree_diagnostics
        if diagnostic.code not in settings.suppressed_diagnostics
    ]
    unmatched_tree = [
        (diagnostic.level, diagnostic.code, diagnostic.message) for diagnostic in tree
    ]
    merged: list[Diagnostic] = []
    for diagnostic in parser_diagnostics:
        if diagnostic.code in settings.suppressed_diagnostics:
            continue
        key = (diagnostic.level, diagnostic.code, diagnostic.message)
        try:
            matched_index = unmatched_tree.index(key)
        except ValueError:
            merged.append(diagnostic)
        else:
            unmatched_tree.pop(matched_index)
    merged.extend(tree)
    return tuple(merged)


def parse_document(
    text: str,
    path: pathlib.Path,
    *,
    settings: ParseSettings | None = None,
    registry: RegistrySnapshot | None = None,
) -> ParseResult:
    r"""Parse and extract a documentation page through the frozen registry.

    >>> parse_document('>>> 1 + 1\n2\n', pathlib.Path('x.rst')).blocks[0].kind
    'doctest'
    """
    if registry is None:
        from .registry import build_registry

        registry = build_registry()
    settings = settings or ParseSettings()
    parser = _parser_for_path(path, registry)
    doctree, parser_diagnostics = parser.parse(text, path, settings=settings)
    extracted = extract_blocks(doctree, settings=settings, registry=registry)
    return ParseResult(
        blocks=extracted.blocks,
        outputs=extracted.outputs,
        diagnostics=_merge_diagnostics(
            parser_diagnostics,
            extracted.diagnostics,
            settings,
        ),
    )
