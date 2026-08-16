(adr-0006-pytest-private-api-compatibility)=

# ADR 0006: pytest private API compatibility

Status: Draft
Date: 2026-08-02

## Context

The plugin currently calls `config.pluginmanager.set_blocked("doctest")` and then
imports that same blocked plugin's private helpers, while continuing to read four
ini and CLI options the blocked plugin declared. It works only because
`_pytest/fixtures.py` has no `pytest_plugin_unregistered` handler, so the
already-parsed `doctest_namespace` fixture outlives unregistration. That is an
undocumented behaviour bet on for every collected page.

{doc}`0001-typed-vanilla-doctest-core` inverts the relationship: the built-in
doctest plugin is not blocked, it is *required*. Its checker, its failure repr,
its `--doctest-report` formatting and `doctest_namespace` are all worth keeping,
and reimplementing them was measured as costing roughly three times what it was
budgeted at — `_get_checker` alone returns a checker implementing
`ALLOW_UNICODE`, `ALLOW_BYTES` and `NUMBER` with float-precision handling
([`_pytest/doctest.py:662`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L662)).

Not blocking it exposes a live defect the block was masking.
[`_is_doctest`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L148-L152)
claims any `.txt` or `.rst` **initial path before consulting `--doctest-glob`**:

```python
def _is_doctest(config: Config, path: Path, parent: Collector) -> bool:
    if path.suffix in (".txt", ".rst") and parent.session.isinitpath(path):
        return True
    globs = config.getoption("doctestglob") or ["test*.txt"]
    return any(fnmatch_ex(glob, path) for glob in globs)
```

So `pytest docs/page.rst` is claimed by the built-in plugin regardless of glob
configuration, and `pytest_collect_file` is not `firstresult` — the directory
collector yields the results of *every* implementation for a path. Declining the
path is therefore not sufficient; the duplicate has to be removed.

**Narrowing `--doctest-glob` cannot help**, because `_is_doctest` returns `True`
for an `.rst` initial path *before* it consults the glob at all.

**And removing the duplicate late is too late.** `DoctestTextfile.collect()`
reads and parses the page inside `collect()`, so by the time
`pytest_collection_modifyitems` runs, the built-in has already produced an item —
or already reported a collection error, which deselection cannot retract.

## Question

What private surface is depended on, and how does a pytest release that changes
it fail?

The spike's private surface is `_get_checker`, `get_optionflags`,
`_get_continue_on_failure`, `_get_report_choice`, `DoctestTextfile`,
`MultipleDoctestFailures`, `ReprFailDoctest`, `_pytest._code` representation
classes, and the Darwin capture method on the public item. Not everything in the
quarantine is equally risky:
{class}`pytest.DoctestItem` is **public** from pytest 7.2 onward, so subclassing
it is ordinary API use and establishes the adapter's minimum pytest. The
collector class filtered out of the
multicall result and the representation helpers are private and need a version
matrix. `_init_runner_class` is explicitly not used:
`PytestDoctestRunner` is defined inside it
([`_pytest/doctest.py:178-181`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L178-L181))
and is unreachable by name. The carrier runner never executes; the adapter maps
the core's result records and host exception policy directly, while
`continue_on_failure` is read through the quarantined helper.

## Direction

Quarantine every private import in one adapter-owned module with a pinned
support matrix. The clean-slate package spelling is
`pytest_doctest_docutils._compat`. The spike retains the released flat facade and
therefore uses the top-level `_pytest_doctest_compat`; that is an implementation
compromise, not the preferred namespace.

**Filter the built-in's collector out of the `pytest_collect_file` result, in a
hook wrapper.** The directory collector consumes the multicall result directly,
and returning a modified result from a wrapper is documented and supported.
Filtering there removes the duplicate *before* the built-in collector parses
anything, so neither the duplicate item nor its collection error is ever produced
— which late deselection cannot achieve.

**Use the old-style `hookwrapper=True` with `outcome.force_result()`.** New-style
`wrapper=True` is gated on **pluggy ≥ 1.2**, not on pytest 8 — it works fine
under pytest 7 with a new enough pluggy. But pytest 7 declares only
`pluggy>=0.12,<2.0`, so a resolver may legally install pluggy 1.0 or 1.1, where
`wrapper=True` raises `TypeError` *while importing the plugin* — a session-wide
abort, which this record and {doc}`0001-typed-vanilla-doctest-core` both forbid.
Old style adds no pluggy floor and was verified from pytest 7.2 through 9.

Whichever spelling is used, **name the minimum supported pytest**. The package
declares `pytest>=7.2`, the first release exporting `pytest.DoctestItem`, and the
CI matrix pins that exact floor.

**Fail on an unsupported pytest only when an affected document is collected**,
not at plugin registration. A `pytest11` plugin that raises at import takes down
sessions whose majority of tests never touch a doctest, and
{doc}`0001-typed-vanilla-doctest-core` and
{doc}`0002-runner-conformance-across-cpython` both reject session-wide startup
failures for the same reason. The error names the pytest version and the missing
symbol, and it names the document that triggered it.

The acceptance matrix must carry a job pinned to the minimum supported pytest
and one tracking its prerelease. The spike implements the floor job; the
prerelease probe remains open.

Registry construction is not a pytest-private-API concern. The host-neutral
contract and host lifecycle proposals are specified in
{doc}`0007-host-plugin-registration-lifecycle`.

## Spike result

The old-style collection wrapper works across pytest 7.2, 8.4 and 9.1 and removes only
the built-in collector for documents this plugin claims. The built-in plugin is
required: collecting an affected documentation file, or a Python module through
this adapter's doctest-module mode, raises an actionable usage error when it has
been disabled. Fixture injection and pytest's checker/report options continue to
come from the built-in plugin. The adapter limits its claim to suffixes in the
frozen document-parser registry, so a separate `--doctest-glob=*.foo` remains
owned by pytest's text collector unless a contributor actually registers a
`.foo` parser.

The quarantine is effective as an import boundary, but its symbol binding is
still eager. A supported or newer pytest release missing one of those private
names would fail while the plugin imports rather than when an affected document
is collected. Pytest below the declared 7.2 floor may likewise fail at the public
base-class import. The CI matrix covers released pytest 7.2, 8.4 and 9.1; it does
not yet include a prerelease probe. Those are remaining acceptance gaps, so this
record stays `Draft`.

## Open

- Whether the probe should accept a *newer* pytest it has not been tested against,
  or refuse it. Refusing is safer and more annoying; for a private-API quarantine
  with a small matrix, safer probably wins.
- Whether any of these helpers can be promoted upstream, which would delete the
  quarantine entirely.
