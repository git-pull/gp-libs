# docutils and MyST-Parser

docutils pinned at `docutils-0.21.2` (canonical repository is on SourceForge; the
GitHub copies are third-party mirrors, so anchors here name file and symbol rather
than a permalink). MyST-Parser pinned at
[`v5.1.0`](https://github.com/executablebooks/MyST-Parser/tree/v5.1.0).

## Classification

The parsing floor. Two front-ends producing one node model, with two different
line-number conventions and one shared, process-global, unscoped extension
registry.

## Core data structures

```text
docutils.nodes.Element            attributes: dict[str, Any]
  literal_block                   a rendered code block
  comment                         what testsetup/testcleanup/:hide: become
  doctest_block                   a bare >>> block in reStructuredText
  .line                           int | None
  .source                         the file the text lives in (None when unset)
  .rawsource                      the pre-render source, when the node kept it

docutils.parsers.rst.Parser
  .state_classes                  an INSTANCE attribute, therefore substitutable
                                  per parse — but NOT scoped in practice: see below

myst_parser.parsers.docutils_.Parser(RstParser)          [v5.1.0:235]
  .settings_spec = (..., create_myst_settings_spec(), *RstParser.settings_spec)
                                                          [v5.1.0:241-245]
```

## The two line conventions

**These are docutils 0.21.2 behaviours.** docutils 0.22 fixed the nested case
upstream and made top-level and nested blocks agree on the **first** line, so any
claim here that does not name a version is a bug in the claim. ADR 0005
(`docs/adrs/0005-line-recovery-for-nested-blocks.md`) covers the floor question.

| Front-end | Construct | `.line` reports (0.21.2) |
|---|---|---|
| reStructuredText | top-level `doctest_block` | its **last** line |
| reStructuredText | any block nested in a directive, list item or block quote | `None`, with `.source` also `None` |
| MyST | fenced block | its **first** line |
| either | a block reached through `.. include::` | numbered against the **included** file |

All four are real and all four have to be normalized by the front-end that knows
which it is. A collector that assumes one convention mis-anchors the other's
blocks; a collector that reads `.line` as a number crashes on the nested case.
This is why `Block.line` in ADR 0001 is nullable and `Block.path` is separate from
the collected document.

## The directive registry

`docutils.parsers.rst.directives` keeps one module-level dict consulted by both
the reStructuredText parser and MyST's `run_directive`. It has no per-document
scoping, no versioning, and no ownership.

Three failure modes follow, and all three have been observed:

1. **It can be rebound, not merely mutated.** Sphinx's `docutils_namespace()`
   restores a snapshot by rebinding the module attribute, so any registration made
   inside that context is discarded *and the dict's object identity changes*. A
   registration guard that caches a boolean is wrong; membership must be
   re-checked against the live dict.
2. **Registrations are overwritten silently.** `Sphinx.add_directive` overrides an
   existing name unconditionally, with only a warning. `sphinx.ext.doctest` loaded
   in the same interpreter therefore replaces a forked directive class with one
   that has different option handling — including the reversed
   `is_allowed_version` argument order.
3. **A missing registration is silent.** An unregistered directive parses to a
   docutils error node, the page still renders, and the collector finds zero
   tests. This is the GH-48 failure shape, and it is the reason ADR 0004 treats
   diagnostics as data.

The defence is not to win the registry. It is to read the *node attributes* —
`testnodetype`, `groups`, `options`, `skipif`, `test`, `hide` — which are
byte-compatible with what `sphinx.ext.doctest` stamps, so a page survives either
class having produced it.

The registry is a smaller instance of the pattern `asyncio` is currently retiring;
see [`14-asyncio.md`](14-asyncio.md).

## MyST configuration

`myst_parser.parsers.docutils_.Parser` subclasses `RstParser` and composes its own
settings spec from `create_myst_settings_spec()`
([`v5.1.0:208`](https://github.com/executablebooks/MyST-Parser/blob/v5.1.0/myst_parser/parsers/docutils_.py#L208),
[`:241-245`](https://github.com/executablebooks/MyST-Parser/blob/v5.1.0/myst_parser/parsers/docutils_.py#L241-L245)).
Driving MyST through that `Parser` is what makes the `myst_*` docutils settings —
including `myst_enable_extensions` and `myst_fence_as_directive` — reachable, and
what makes front-matter configuration merge.

Constructing an `MdParserConfig` by hand and calling `md_parser.render()` against
a bare `make_document()` skips all of it. Colon-fence directives do not exist, a
plain ```` ```python ```` fence is only picked up by a prompt sniff, and the
line-length guard and MyST transforms never run. Those omissions become a decision
rather than an accident once the front-end owns its own configuration.

`myst_fence_as_directive` is also the answer to a real user request: it maps a
bare language fence onto a directive name, so a project that prefers not to write
`{testcode}` can still have its ```` ```python ```` blocks collected.

## Reporter behaviour

Default settings send reporter output to stderr and raise `SystemMessage` at
`halt_level`, aborting mid-parse.

Turning messages into values takes **three** settings, not one. `attach_observer`
is *additive*: the observer receives the message and the warning stream still gets
written. So all of `halt_level` above 4 (both to avoid the abort and because a
halting message bypasses observer notification entirely), `report_level` at 5 or
`warning_stream` disabled to stop the write, and the observer itself.

A `system_message` carries a level and text and **nothing semantically stable** —
no code. So a downstream that wants to suppress or promote by category has to
*classify* the message, and cannot key on an attribute docutils does not provide.
That is the open problem in ADR 0004.

## What it cannot do

- **Scope a directive registration** to one parse, one document or one thread.
- **Scope a `state_classes` substitution either.** `state_classes` is an instance
  attribute, which makes substitution *look* parse-local — but a nested parse
  builds its machine from `nested_sm_kwargs`, so a top-level substitution never
  reaches a nested block, and `RSTState.nested_sm_cache` is a shared **class**
  attribute that leaks substituted classes into later parses. This is why ADR 0005
  abandoned the mechanism.
- **Report a line for every node.** See the table above.
- **Type its own attribute channel.** `Element.attributes` is `dict[str, Any]`, and
  typeshed's stub for `get(key, failobj: _T) -> _T` is actively wrong — it claims
  `_T` even when the key is present holding something else. One narrowing accessor
  at the parse boundary is cheaper and safer than a coercion at every read site.

## Anchors

- MyST: [`docutils_.Parser`](https://github.com/executablebooks/MyST-Parser/blob/v5.1.0/myst_parser/parsers/docutils_.py#L235) ·
  [`create_myst_settings_spec`](https://github.com/executablebooks/MyST-Parser/blob/v5.1.0/myst_parser/parsers/docutils_.py#L208) ·
  [`settings_spec`](https://github.com/executablebooks/MyST-Parser/blob/v5.1.0/myst_parser/parsers/docutils_.py#L241-L245) ·
  [`MdParserConfig`](https://github.com/executablebooks/MyST-Parser/blob/v5.1.0/myst_parser/config/main.py)
- Sphinx's registry snapshot/rebind: [`sphinx/util/docutils.py`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/util/docutils.py) ·
  unconditional override: [`sphinx/application.py`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/application.py)
- docutils: `docutils/parsers/rst/directives/__init__.py` (`_directives`),
  `docutils/parsers/rst/states.py` (`state_classes`, `doctest_block` line
  assignment), `docutils/utils/__init__.py` (`Reporter.attach_observer`,
  `system_message`), at `docutils-0.21.2`.
