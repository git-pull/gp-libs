# `_pytest.doctest`

Pinned at [`9.1.1`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py).

## Classification

A deliberately thin adapter. It owns two collectors and one item, and delegates
every piece of domain knowledge to stdlib `DocTest`/`Example`/`DocTestFailure`. It
overrides exactly the seams it needs and invents no parallel abstraction. It is
the reference implementation of how to integrate with `doctest` rather than
replace it, and the model this project's pytest layer should resemble.

## Core data structures

```text
DoctestItem(Item)          dtest: DocTest, runner: DocTestRunner, fixture_request
   |                       obj = None  (class attribute)
DoctestTextfile(Module)    obj = None; one DocTest for the whole file
DoctestModule(Module)      one DocTest per docstring; calls parsefactories
MultipleDoctestFailures    carries a list; the workaround for stdlib having no
                           per-example result value
ReprFailDoctest            (ReprFileLocation, lines) pairs
```

`obj = None` as a *class* attribute
([`:421`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L421))
is what keeps `Module` from trying to import a `.txt`/`.rst` file. Subclassing
`Module` rather than `File` is what makes `scope="module"` fixtures resolve
against the page — a page collector *is* the module scope. `parsefactories`
([`:556`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L556))
is what makes autouse fixtures from a visible `conftest.py` apply at all.

## Data flow

```text
pytest_collect_file(file_path, parent)            [:126]
   |  .py  -> DoctestModule   (when --doctest-modules)
   |  else -> DoctestTextfile (when _is_doctest)
   v
Collector.collect() -> DoctestItem.from_parent(...) per non-empty DocTest
   |                   an EMPTY DocTest is never yielded            [:451]
   v
DoctestItem.setup()                                                 [:288]
   |  fixture request is filled, then: self.dtest.globs.update(globs)
   |  -> the mapping must be MUTABLE and must survive collection
   v
DoctestItem.runtest()                                               [:295]
   |  _check_all_skipped(self.dtest)   -> outcomes.skip if every example is SKIP
   |  self.runner.run(self.dtest, out=failures)
   |                      ^^^ `out` is a LIST, not a write-callable.
   |                      clear_globs defaults to True.
   |  raise MultipleDoctestFailures(failures)
   v
DoctestItem.repr_failure(excinfo)                                   [:317]
      for failure in failures:                                      [:337]
          lineno = test.lineno + example.lineno + 1                 [:344]
```

Two details in that flow decide a great deal for anything built on it.

**`out` is repurposed as a list.** The most important consumer of stdlib's runner
deliberately violates typeshed's `_Out = Callable[[str], object]`, marked with a
`# type: ignore[arg-type]`, so that `report_failure` can append rather than write.
Any claim that a "typed vanilla core" can narrow `out` honestly has to reckon with
the fact that the ecosystem's largest caller does not.

**`repr_failure` reads each failure's own `test`.** Locations are computed
per failure inside the loop, not once per item. That is what makes N `DocTest`s
under one item report N correct locations with no override — the fact ADR 0001 is
built on.

## Extension seams

| Seam | Kind |
|---|---|
| `--doctest-modules`, `--doctest-glob`, `--doctest-continue-on-failure`, `--doctest-report`, `doctest_optionflags`, `doctest_encoding` | ini/CLI, declared by the always-loaded plugin |
| `doctest_namespace` session fixture ([`:721`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L721)) | fixture |
| `_get_flag_lookup` ([`:385`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L385)) | private; lazily registers `ALLOW_UNICODE`, `ALLOW_BYTES`, `NUMBER` |
| `_get_checker` ([`:662`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L662)) | private; returns the checker implementing those flags |
| `_get_continue_on_failure` ([`:410`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L410)), `_get_report_choice` ([`:703`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L703)) | private |
| `PytestDoctestRunner` ([`:181`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L181)) | **unreachable** — defined inside `_init_runner_class()` ([`:178`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L178)) |

That last row matters more than it looks. `PytestDoctestRunner` is where the
`OutcomeException` re-raise, the `bdb.BdbQuit` → `outcomes.exit` conversion, and
the `continue_on_failure` buffering live. Because it is defined inside a function
and never bound at module scope, a downstream cannot import or subclass it. Any
design that assumes those behaviours "come for free" by subclassing `DoctestItem`
is wrong: the item supplies the *plumbing*, but the runner supplies the
*behaviour*, and only the plumbing is reachable.

## Configuration

`pytest_addoption` in this module declares six settings that the plugin reads back
through helpers. A third-party plugin may **read** them but must not re-declare
them — re-adding an existing option raises at option-parsing time. Conversely,
suppressing the built-in plugin before `pytest_configure` (`-p no:doctest`)
removes the options entirely, and any downstream read of them then fails.

## What it cannot do

- **Collect a page with directives.** It has no document model at all; a `.rst`
  file is one string handed to `DocTestParser`.
- **Share state across items.** `runtest()` runs with `clear_globs=True`.
- **Decline a path it has claimed.** `_is_doctest`
  ([`:148-152`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L148-L152))
  returns `True` for any `.txt`/`.rst` **initial path before consulting
  `--doctest-glob`**, and `pytest_collect_file` is not `firstresult`, so a
  third-party collector claiming the same path gets its items collected
  *alongside* — not instead of — the built-in's.

## Anchors

- [`pytest_collect_file`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L126) ·
  [`_is_doctest`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L148-L152) ·
  [`_is_setup_py`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L141) ·
  [`_is_main_py`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L155)
- [`_init_runner_class`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L178) ·
  [`PytestDoctestRunner`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L181) ·
  [`MultipleDoctestFailures`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L172)
- [`DoctestItem`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L251) ·
  [`setup`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L288-L293) ·
  [`runtest`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L295-L303) ·
  [`repr_failure`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L317-L344)
- [`get_optionflags`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L401) ·
  [`_check_all_skipped`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L451) ·
  [`DoctestTextfile`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L420) ·
  [`DoctestModule`](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/doctest.py#L500)
