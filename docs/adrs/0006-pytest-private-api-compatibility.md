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

The current surface is `_get_checker`, `get_optionflags`,
`_get_continue_on_failure`, `_get_report_choice` and `MultipleDoctestFailures`.
Not everything in the quarantine is equally risky: {class}`pytest.DoctestItem` is
**public** — exported from `pytest` — so subclassing it is ordinary API use. The
collector class filtered out of the multicall result is private, and that filter
is the part that needs a version matrix. `_init_runner_class` is explicitly *not* usable:
`PytestDoctestRunner` is defined inside it
([`_pytest/doctest.py:178-181`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L178-L181))
and is unreachable by name, which is why the `OutcomeException` re-raise,
`BdbQuit` → `outcomes.exit` and `continue_on_failure` handling must be
reimplemented rather than inherited.

## Direction

Quarantine every private import in one module, `pytest_doctest_docutils._compat`,
with a pinned support matrix.

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
Old style needs no floor at all and was verified working on both pytest 7 and 9.

Whichever spelling is used, **name the minimum supported pytest**. The CI matrix
floor is 7 and the package declares no pytest dependency, so today the support
statement exists only in the workflow file.

**Fail on an unsupported pytest only when an affected document is collected**,
not at plugin registration. A `pytest11` plugin that raises at import takes down
sessions whose majority of tests never touch a doctest, and
{doc}`0001-typed-vanilla-doctest-core` and
{doc}`0002-runner-conformance-across-cpython` both reject session-wide startup
failures for the same reason. The error names the pytest version and the missing
symbol, and it names the document that triggered it.

CI carries a job pinned to the minimum supported pytest and one tracking its
prerelease.

Registry construction is not a pytest-private-API concern. The host-neutral
contract, pytest hookspec, Sphinx adapter and xdist manifest are specified in
{doc}`0007-host-plugin-registration-lifecycle`.

## Open

- Whether requiring the built-in plugin should be stated as a hard dependency.
  `-p no:doctest` already fails today with a raw `ValueError` about an unknown
  option, so this is not a regression — but the message should become actionable.
- Whether the probe should accept a *newer* pytest it has not been tested against,
  or refuse it. Refusing is safer and more annoying; for a private-API quarantine
  with a small matrix, safer probably wins.
- What the filtering wrapper should do when the built-in's collector is the *only*
  one for a path — that is the ordinary `--doctest-glob` case this plugin has no
  business touching, so the filter must be scoped to paths it actually claims.
- Whether any of these helpers can be promoted upstream, which would delete the
  quarantine entirely.
