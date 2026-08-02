# Bibliography

Every external anchor cited by `docs/adrs/` and these notes, in one place. All
links are pinned to a tag, or — where a project publishes no tags — to a commit
reachable from trunk. Line anchors are only meaningful on a pinned ref and are not
used anywhere else.

## CPython — `v3.14.2`

[`python/cpython @ v3.14.2`](https://github.com/python/cpython/tree/v3.14.2)

### `Lib/doctest.py`

| Symbol | Anchor | Cited for |
|---|---|---|
| `TestResults` | [`:114`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L114) | 2-field namedtuple; `skipped` is an extra attribute |
| `register_optionflag` | [`:153`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L153) | the one append-only, idempotent cross-library registry |
| `_load_testfile` | [`:245`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L245) | private, reached by `doctest_docutils` today |
| `DocTest.__init__` | [`:565`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L565) | **copies** the globs mapping |
| `DocTest.__lt__` | [`:596`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L596) | compares names as text |
| `DocTestParser` | [`:609`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L609) | the injectable parser |
| `_EXAMPLE_RE` | [`:618`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L618) | private, used for prompt sniffing |
| `DocTestFinder` | [`:844`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L844) | the type typeshed names; accepted structurally at runtime |
| `report_*` hooks | [`:1286-1314`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1286-L1314) | the four supported in-loop seams; no `report_skip` here |
| `__run` | [`:1344`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1344) | name-mangled loop; overridable by mechanism |
| `compile(..., "single", ...)` | [`:1400`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1400) | the hard-coded mode `{testcode}` cannot use |
| `__record_outcome` | [`:1485`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1485) | arity and accumulator differ across supported versions |
| `__patched_linecache_getlines` | [`:1501`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1501) | parses the `<doctest name[i]>` filename shape back |
| `run()` save/restore | [`:1534-1573`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1534-L1573) | global interpreter state; not reentrant |
| `summarize` | [`:1590`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1590) | reads the accumulator the owned loop must write |
| `OutputChecker` | [`:1690`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1690) | the documented checker seam |
| `DebugRunner` | [`:1874`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1874) | `report_*` overriding as the sanctioned loop control |
| `testfile` | [`:2091`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L2091) | the API `testdocutils` mirrors |
| `DocTestSuite` | [`:2467`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L2467) | no `isinstance` on `test_finder`; sorts, so results must be real `DocTest`s |
| `DocFileSuite` | [`:2570`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L2570) | no `isinstance` on `parser` |

Documentation: [`Doc/library/doctest.rst`](https://github.com/python/cpython/blob/v3.14.2/Doc/library/doctest.rst).

### `Lib/asyncio/`

| Symbol | Anchor |
|---|---|
| `AbstractEventLoop` | [`events.py:254`](https://github.com/python/cpython/blob/v3.14.2/Lib/asyncio/events.py#L254) |
| `get_event_loop_policy` / `set_event_loop_policy` | [`events.py:804`](https://github.com/python/cpython/blob/v3.14.2/Lib/asyncio/events.py#L804) · [`:817`](https://github.com/python/cpython/blob/v3.14.2/Lib/asyncio/events.py#L817) |
| `BaseEventLoop` | [`base_events.py:417`](https://github.com/python/cpython/blob/v3.14.2/Lib/asyncio/base_events.py#L417) |
| `BaseProtocol` / `Protocol` | [`protocols.py:9`](https://github.com/python/cpython/blob/v3.14.2/Lib/asyncio/protocols.py#L9) · [`:66`](https://github.com/python/cpython/blob/v3.14.2/Lib/asyncio/protocols.py#L66) |
| `BaseTransport` / `Transport` | [`transports.py:9`](https://github.com/python/cpython/blob/v3.14.2/Lib/asyncio/transports.py#L9) · [`:148`](https://github.com/python/cpython/blob/v3.14.2/Lib/asyncio/transports.py#L148) |
| `Runner` / `run` / `_cancel_all_tasks` | [`runners.py:21`](https://github.com/python/cpython/blob/v3.14.2/Lib/asyncio/runners.py#L21) · [`:169`](https://github.com/python/cpython/blob/v3.14.2/Lib/asyncio/runners.py#L169) · [`:207`](https://github.com/python/cpython/blob/v3.14.2/Lib/asyncio/runners.py#L207) |
| `Future` / `Task` | [`futures.py:31`](https://github.com/python/cpython/blob/v3.14.2/Lib/asyncio/futures.py#L31) · [`tasks.py:56`](https://github.com/python/cpython/blob/v3.14.2/Lib/asyncio/tasks.py#L56) |

## pytest — `9.1.1`

[`pytest-dev/pytest @ 9.1.1`](https://github.com/pytest-dev/pytest/tree/9.1.1) ·
[`src/_pytest/doctest.py`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py)

| Symbol | Anchor | Cited for |
|---|---|---|
| `pytest_collect_file` | [`:126`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L126) | not `firstresult` |
| `_is_setup_py` / `_is_main_py` | [`:141`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L141) · [`:155`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L155) | privates imported today |
| `_is_doctest` | [`:148-152`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L148-L152) | claims initpaths **before** `--doctest-glob` |
| `MultipleDoctestFailures` | [`:172`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L172) | the missing per-example result value, worked around |
| `_init_runner_class` / `PytestDoctestRunner` | [`:178`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L178) · [`:181`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L181) | **unreachable by name** |
| `DoctestItem` | [`:251`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L251) | the subclassed item |
| `setup` | [`:288-293`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L288-L293) | `globs.update(...)` in place |
| `runtest` | [`:295-303`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L295-L303) | `clear_globs` defaults to `True` |
| `repr_failure` | [`:317-344`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L317-L344) | reads each failure's own `test` |
| `_get_flag_lookup` | [`:385`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L385) | lazily registers `ALLOW_UNICODE`, `ALLOW_BYTES`, `NUMBER` |
| `get_optionflags` | [`:401`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L401) | read, not re-declared |
| `_get_continue_on_failure` | [`:410`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L410) | private helper imported today |
| `DoctestTextfile` | [`:420-421`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L420-L421) | `obj = None` as a class attribute |
| `_check_all_skipped` | [`:451`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L451) | fires only once the item is running |
| `DoctestModule` / `parsefactories` | [`:500`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L500) · [`:556`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L556) | fixtures defined in the collected `.py`; **not** conftest autouse, which arrives via `FixtureManager.pytest_plugin_registered` |
| `subtests` | [`src/_pytest/subtests.py`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/subtests.py) | builtin since 9.0; the only sanctioned sub-item outcome mechanism, and experimental |
| `_get_checker` | [`:662`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L662) | the checker that would have to be reimplemented |
| `_get_report_choice` | [`:703`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L703) | private helper |
| `doctest_namespace` | [`:721`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L721) | the fixture that survives plugin blocking today |

## pytest-xdist — `v3.8.0`

[`pytest-dev/pytest-xdist @ v3.8.0`](https://github.com/pytest-dev/pytest-xdist/tree/v3.8.0)

| Symbol | Anchor | Cited for |
|---|---|---|
| `parse_tx_spec_config` | [`workermanage.py:26-37`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/workermanage.py#L26-L37) | list `extend`, so a negative multiplier contributes zero |
| `LoadScopeScheduling._split_scope` | [`loadscope.py:284`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadscope.py#L284) | the only affinity primitive |
| `LoadFileScheduling._split_scope` | [`loadfile.py:35`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadfile.py#L35) | two-line override |
| `LoadGroupScheduling._split_scope` | [`loadgroup.py:24`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadgroup.py#L24) | two-line override |
| collection-mismatch abort | [`load.py:259`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/load.py#L259) · [`loadscope.py:359`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadscope.py#L359) | logs and runs zero tests |
| `xdist_group` node-id append | [`remote.py:245-254`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/remote.py#L245-L254) | worker-side, `loadgroup` only |

## pytest-asyncio — `v1.4.0`

[`pytest-dev/pytest-asyncio @ v1.4.0`](https://github.com/pytest-dev/pytest-asyncio/tree/v1.4.0) ·
[`pytest_asyncio/plugin.py`](https://github.com/pytest-dev/pytest-asyncio/blob/v1.4.0/pytest_asyncio/plugin.py)

| Symbol | Anchor | Cited for |
|---|---|---|
| `Mode` | [`:82`](https://github.com/pytest-dev/pytest-asyncio/blob/v1.4.0/pytest_asyncio/plugin.py#L82) | `str` enum so ini, CLI and internal value are one object |
| `PytestAsyncioSpecs` | [`:90`](https://github.com/pytest-dev/pytest-asyncio/blob/v1.4.0/pytest_asyncio/plugin.py#L90) | its own hookspec namespace |
| `pytest_addoption` | [`:108`](https://github.com/pytest-dev/pytest-asyncio/blob/v1.4.0/pytest_asyncio/plugin.py#L108) | every option `default=None` |
| `_make_asyncio_fixture_function` | [`:210`](https://github.com/pytest-dev/pytest-asyncio/blob/v1.4.0/pytest_asyncio/plugin.py#L210) | stamping scope on the function |
| `_get_asyncio_mode` | [`:222`](https://github.com/pytest-dev/pytest-asyncio/blob/v1.4.0/pytest_asyncio/plugin.py#L222) | resolve once, query once |
| `pytest_configure` | [`:295-301`](https://github.com/pytest-dev/pytest-asyncio/blob/v1.4.0/pytest_asyncio/plugin.py#L295-L301) | detecting an unset default via the sentinel |

## Sphinx — `v9.1.0`

[`sphinx-doc/sphinx @ v9.1.0`](https://github.com/sphinx-doc/sphinx/tree/v8.2.3) ·
[`sphinx/ext/doctest.py`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py)

| Symbol | Anchor | Cited for |
|---|---|---|
| `is_allowed_version(spec, version)` | [`:45`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L45) | specifier first — the reverse of the local helper |
| `TestDirective` | [`:66`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L66) | the directive base and its option handling |
| comment nodetype rule | [`:92-93`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L92-L93) | `testsetup`/`testcleanup`/`:hide:` become `nodes.comment` |
| `:options:` gating | [`:111`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L111) | accepted only on `doctest` and `testoutput` |
| `TestGroup` / `add_code` | [`:200`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L200) · [`:207`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L207) | phase ordering; three silent-loss cases |
| `TestCode` | [`:235`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L235) | the parsed unit |
| `SphinxDocTestRunner` | [`:257`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L257) | overrides a private method to swallow an `IndexError` |
| `DocTestBuilder` | [`:292`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L292) | builder coupling |
| `doctest.compile` rebinding | [`:310`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L310) | process-global, never restored |
| `test_doc` | [`:428`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L428) | group resolution and `*` |
| gated-node drop | [`:443-444`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L449-L450) | no outcome, id or count |
| `type = "exec"` for testcode | [`:548`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/ext/doctest.py#L548) | the mode flip |

Documentation: [`doc/usage/extensions/doctest.rst`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/doc/usage/extensions/doctest.rst).
Registry behaviour: [`sphinx/util/docutils.py`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/util/docutils.py),
[`sphinx/application.py`](https://github.com/sphinx-doc/sphinx/blob/v8.2.3/sphinx/application.py).

## MyST-Parser — `v5.1.0`

[`executablebooks/MyST-Parser @ v5.1.0`](https://github.com/executablebooks/MyST-Parser/tree/v5.1.0)

| Symbol | Anchor |
|---|---|
| `create_myst_settings_spec` | [`parsers/docutils_.py:208`](https://github.com/executablebooks/MyST-Parser/blob/v5.1.0/myst_parser/parsers/docutils_.py#L208) |
| `Parser(RstParser)` | [`parsers/docutils_.py:235`](https://github.com/executablebooks/MyST-Parser/blob/v5.1.0/myst_parser/parsers/docutils_.py#L235) |
| `settings_spec` | [`parsers/docutils_.py:241-245`](https://github.com/executablebooks/MyST-Parser/blob/v5.1.0/myst_parser/parsers/docutils_.py#L241-L245) |
| `MdParserConfig` (`myst_enable_extensions`, `myst_fence_as_directive`) | [`config/main.py`](https://github.com/executablebooks/MyST-Parser/blob/v5.1.0/myst_parser/config/main.py) |

## docutils — `docutils-0.21.2` (the version this project pins)

The canonical repository is on
[SourceForge](https://sourceforge.net/p/docutils/code/); the GitHub copies are
third-party mirrors and are not linked here. Anchors name file and symbol at the
tagged release:

| File | Symbol | Cited for |
|---|---|---|
| `docutils/parsers/rst/directives/__init__.py` | `_directives` | the process-global, rebindable registry |
| `docutils/parsers/rst/states.py` | `state_classes`, `doctest_block` line assignment | per-instance substitutability; last-line convention |
| `docutils/utils/__init__.py` | `Reporter.attach_observer`, `system_message` | observation separable from display |
| `docutils/nodes.py` | `Element.attributes`, `literal_block`, `comment`, `doctest_block` | the untyped attribute channel |

Typed surface: [`typeshed stubs/docutils`](https://github.com/python/typeshed/tree/8c7256c/stubs/docutils).

## Prior art

| Project | Ref | Key anchors |
|---|---|---|
| Sybil | [`10.0.1`](https://github.com/simplistix/sybil/tree/10.0.1) | [`sybil.py:155-157`](https://github.com/simplistix/sybil/blob/10.0.1/src/sybil/sybil.py#L155-L157) (positional ids) · [`document.py`](https://github.com/simplistix/sybil/blob/10.0.1/src/sybil/document.py) (one namespace, non-overlap invariant) · [`integration/pytest.py`](https://github.com/simplistix/sybil/blob/10.0.1/src/sybil/integration/pytest.py) (one item per region) · [`region.py`](https://github.com/simplistix/sybil/blob/10.0.1/src/sybil/region.py) · [`testing.py`](https://github.com/simplistix/sybil/blob/10.0.1/src/sybil/testing.py) (public extension-test helpers) |
| xdoctest | [`v1.3.2`](https://github.com/Erotemic/xdoctest/tree/v1.3.2) | [`directive.py:58`](https://github.com/Erotemic/xdoctest/blob/v1.3.2/src/xdoctest/directive.py#L58) (`REQUIRES` carries its reason) · [`plugin.py`](https://github.com/Erotemic/xdoctest/blob/v1.3.2/src/xdoctest/plugin.py) (unregisters pytest's doctest plugin) |
| pytest-examples | [`v0.0.18`](https://github.com/pydantic/pytest-examples/tree/v0.0.18) | [`find_examples.py`](https://github.com/pydantic/pytest-examples/blob/v0.0.18/pytest_examples/find_examples.py) · [`run_code.py`](https://github.com/pydantic/pytest-examples/blob/v0.0.18/pytest_examples/run_code.py) · [`modify_files.py`](https://github.com/pydantic/pytest-examples/blob/v0.0.18/pytest_examples/modify_files.py) (byte offsets, invertible dedent, unguarded splice) |
| typeshed | [`8c7256c`](https://github.com/python/typeshed/tree/8c7256c) | [`stdlib/doctest.pyi`](https://github.com/python/typeshed/blob/8c7256c/stdlib/doctest.pyi) |
