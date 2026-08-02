# CPython `doctest`

Pinned at [`v3.14.2`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py).

## Classification

A four-stage pipeline of unannotated classes, whose documented extension surface
is six classes plus three injection slots and four reporting hooks. The per-example
loop — the thing every extender eventually wants — is not among them.

## Core data structures

```text
Example      source, want, exc_msg, lineno, indent, options
   |         lineno is 0-based, relative to the start of the containing string
   v
DocTest      examples, globs, name, filename, lineno, docstring
   |         globs is COPIED by __init__; __lt__ compares name as TEXT
   v
TestResults  namedtuple(failed, attempted), with `skipped` as an EXTRA attribute
```

Three properties of these are load-bearing for anything built on top:

**`DocTest.__init__` copies the globs mapping**
([`:565`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L565)).
Passing a shared dict through the constructor has no effect whatsoever. A shared
mapping must be assigned to `test.globs` after construction, and the runner must
be given `clear_globs=False` or it empties the mapping in its `finally`.

**`__lt__` compares names as text**
([`:596`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L596)).
Any name carrying a position as text sorts `[10]` before `[1]`. This fails
silently: every test passes, in the wrong order.

**`TestResults` carries `skipped` outside the tuple**
([`:114`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L114)),
with a `repr` that falls back to the plain namedtuple form when it is zero.
Promoting it to a third field would break every `failures, tries = runner.run(...)`
unpack in the ecosystem, including `doctest._test()` itself.

## Data flow

```text
source string
   |  DocTestParser.parse       -> list[str | Example], alternating,
   |                               reconstructing the input exactly
   |  DocTestParser.get_doctest -> DocTest
   v
DocTestFinder.find(obj)         -> list[DocTest]
   |  recurses into __test__, tracks a seen-map by id()
   v
DocTestRunner.run(test, compileflags, out, clear_globs)
   |    saves sys.stdout, pdb.set_trace, linecache.getlines,
   |    sys.displayhook, _colorize.can_colorize; pops PYTHON_COLORS
   |    and FORCE_COLOR from os.environ; restores all in finally
   |
   +--> __run(test, compileflags, out)          <- name-mangled
          for each example:
            merge test-level and example-level optionflags
            SKIP? -> continue BEFORE report_start; still counts as attempted
            compile(source, "<doctest %s[%d]>" % (test.name, n),
                    "single", flags, dont_inherit=True)
            exec in test.globs
            OutputChecker.check_output(want, got, flags)
            report_success / report_failure / report_unexpected_exception
          __record_outcome(...)
```

The `parse()` contract is not incidental. It must return alternating `str` and
`Example` reconstructing the input, because `script_from_examples()` walks the
`str` pieces to build the prose comments in a debugging script. `Example.indent`
is computed against the original string — after `expandtabs`, before dedent — so a
post-dedent indent shifts every reported column.

## Extension seams

| Seam | Kind | Documented |
|---|---|---|
| `DocTestParser` subclass, injected as `parser=` | nominal | yes |
| `DocTestFinder` subclass, injected as `test_finder=` | nominal | yes |
| `OutputChecker.check_output` / `output_difference`, injected as `checker=` | nominal | yes |
| `report_start`, `report_success`, `report_failure`, `report_unexpected_exception` ([`:1286-1314`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1286-L1314)) | subclass hook | yes |
| `register_optionflag` / `OPTIONFLAGS_BY_NAME` ([`:153`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L153)) | process-global registry | yes |
| `setUp` / `tearDown` on `DocTestSuite` / `DocFileSuite` | callable param | yes |
| `__run` ([`:1344`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1344)) | **name-mangled** | no |
| `__record_outcome` ([`:1485`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1485)) | **name-mangled** | no |
| `__patched_linecache_getlines` ([`:1501`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1501)) | **name-mangled** | no |
| `_load_testfile` ([`:245`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L245)), `_EXAMPLE_RE` ([`:618`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L618)) | private | no |

The name-mangled three are the interesting entry. Mangling rewrites the *call
site* at compile time, so `self._DocTestRunner__run(...)` inside `run()` is an
ordinary attribute lookup that resolves through the subclass's MRO. Defining
`_DocTestRunner__run` in a subclass therefore takes over the loop — verified on
3.14.2 with `run()` untouched. It is not an override point by *design*, but it is
one by *mechanism*, and that distinction is what lets a downstream own the loop
without cloning a code object or patching a module global.

`register_optionflag` is the only genuinely cross-library extension point in the
module. Its ints are `1 << len(OPTIONFLAGS_BY_NAME)`, so they are
registration-order dependent, typeshed hard-codes the builtin values, and an
unregistered flag name makes a page fail to **parse** rather than to run.

## Configuration

There is none, in the modern sense. Behaviour is set by optionflags, which arrive
from three places with a fixed precedence: the runner's constructor, the
`DocTest`'s per-example `options` dict, and the inline `# doctest: +FLAG` comment
parsed out of the example source. `set_unittest_reportflags` mutates a module
global. `doctest.master` accumulates results across invocations — the
documentation calls it advanced tomfoolery.

## What it cannot do

- **Run a multi-statement body.** `"single"` mode rejects it, and `"exec"` mode
  suppresses expression echo, which empties every `want`. This one fact is the
  origin of every downstream monkeypatch of `doctest.compile`.
- **Report a per-example result as a value.** Outcomes exist only as counters and
  as text pushed through `out`. pytest works around this by repurposing `out` from
  a write-callable into a *list*; Sphinx works around it by not producing machine-
  readable results at all.
- **Share a globs mapping across `DocTest`s** without the caller assigning
  `test.globs` post-construction and passing `clear_globs=False`.
- **Be reentrant or thread-safe.** `run()` mutates interpreter globals for its
  duration ([`:1534-1573`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1534-L1573)).
- **Report a skip as an outcome.** `SKIP` short-circuits before `report_start`.
  There is no `report_skip` at v3.14.2; it appears in later prereleases, so a
  downstream loop must probe rather than assume.

## Anchors

- [`TestResults`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L114) ·
  [`register_optionflag`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L153) ·
  [`_load_testfile`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L245)
- [`DocTest.__init__` globs copy](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L565) ·
  [`DocTest.__lt__`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L596)
- [`DocTestParser`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L609) ·
  [`_EXAMPLE_RE`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L618) ·
  [`DocTestFinder`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L844)
- [`report_*` hooks](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1286-L1314) ·
  [`__run`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1344) ·
  [`compile(..., "single", ...)`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1400)
- [`__record_outcome`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1485) ·
  [`__patched_linecache_getlines`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1501) ·
  [`run()` global-state save/restore](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1534-L1573)
- [`OutputChecker`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1690) ·
  [`DebugRunner`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L1874) ·
  [`testfile`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L2091) ·
  [`DocTestSuite`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L2467) ·
  [`DocFileSuite`](https://github.com/python/cpython/blob/v3.14.2/Lib/doctest.py#L2570)
- Typed contract: [`typeshed stdlib/doctest.pyi`](https://github.com/python/typeshed/blob/8c7256c/stdlib/doctest.pyi)
