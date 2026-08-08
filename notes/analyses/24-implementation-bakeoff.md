# Typed doctest core implementation bakeoff

## Question

Can the architecture in ADR 0001 be implemented as a typed, host-neutral core
while retaining stock doctest objects and composing with pytest, docutils, MyST,
Sphinx-resolved doctrees, reruns, and xdist?

## Candidates

### Extend the existing modules

Keeping extraction, grouping, execution, pytest collection, and reporting in the
two existing modules minimizes import changes. It also preserves the current
coupling: projection cannot be tested without docutils, pytest policy leaks into
execution, and mutable `DocTest` instances are likely to survive across reruns.
This shape was rejected.

### Typed core with compatibility adapters

The successful shape is a new `doctest_core` package with thin direct and pytest
adapters:

```text
contributors -> frozen registry
                    |
text/doctree -> extraction -> projection -> group runner
                    |             |              |
               inert records   recipes       fresh DocTests
                                                   |
                                      direct / pytest adapters
```

Extraction returns inert typed records and diagnostics. Projection is pure and
owns grouping, wildcard expansion, phase ordering, pairing, and names. The group
runner materializes fresh stock `doctest.Example` and `doctest.DocTest` objects
for every attempt and keeps the shared mapping inside one scheduled item. Host
adapters own collection, fixtures, exception policy, and presentation.

This shape was selected. It preserves the one invariant that mattered under
reruns and xdist: the unit sharing mutable globals is also the unit the host
schedules.

### Replace doctest semantics wholesale

Owning parsing, examples, comparison, and reporting would make every extension
easy to express, but would discard the compatibility goal. It would also require
reimplementing pytest's checker extensions and CPython's process-state behavior.
The bakeoff found no benefit that justified that compatibility surface.

## What implementation changed in the ADRs

The ordinary prompt lane should delegate to CPython's untouched runner. An
extended `exec` lane should be a separate, bounded runtime. Rebinding
`doctest.compile`, cloning CPython's code object, or overriding its private loop
all attach extended syntax to global or private behavior that the core does not
otherwise need. ADR 0002 now records the two-lane contract.

Practice also required contracts absent from the original data model:

- `ExceptionPolicy` lets a host distinguish ordinary exceptions, host outcomes,
  and aborts that must outrank prior failures without importing pytest into the
  core.
- `Failed` retains the exact checker that compared output so a contributed
  checker also explains its own failure.
- `Registration` is a frozen generic dataclass. A generic `NamedTuple` fails at
  import on Python 3.10.
- A proposed `BlockAttributes` `TypedDict` was rejected as false precision over
  third-party node stamps. Field-level validation narrows into `ParsedBlock` and
  `ParsedOutput`, which are the first owned schema.
- Gates execute inside the group failure boundary, and cleanup runs after setup,
  test, and gate failures.
- Extended compilation uses `dont_inherit=True` and only future flags explicitly
  present in the live group mapping.
- An inline doctest `FAIL_FAST` flag stops the current runtime's example loop;
  a runner-level flag also stops later group blocks despite the host's continue
  policy.
- The core defaults unlabelled blocks to Sphinx's `default` group, while the
  pytest adapter preserves gp-libs' released per-block isolation default.
- The core's failure-continuation default follows doctest and Sphinx; direct and
  pytest hosts override it only for explicit fail-fast or debugger policy.
- The pytest adapter composes with the built-in doctest plugin and filters only
  its duplicate documentation collector. It no longer unregisters the plugin
  whose fixture, checker, options, and rendering it uses.
- The distribution declares its actual pytest 7.2 floor and direct `packaging`
  dependency, and uses `pytest_doctest_docutils` as the pytest entry-point name
  so the standard `-p no:pytest_doctest_docutils` spelling works.
- Sphinx compatibility is extractor compatibility over resolved doctrees, not
  byte-identical directive stamps.
- Expected-output records retain their stamp name. A custom `pairs_with`
  relationship therefore works through extraction and projection rather than
  being nominal registry metadata.
- Freeze validates profile and expected-output references before parsing, and
  anonymous group identities cannot collide with an author-written `block-N`
  group.
- Prompt-free `doctest` directives project no group and produce no passing
  carrier item. Collector filtering is limited to registered parser suffixes,
  leaving unrelated `--doctest-glob` paths to pytest.

## Evidence

| Boundary | Result |
|---|---|
| Full repository suite on Python 3.14 and pytest 9 | 227 passed |
| Full repository suite on Python 3.12 and pytest 8.4 | 227 passed |
| Python 3.10, docutils 0.20.1, and pytest 7.2 floor suite | 224 passed, 3 skipped |
| Rerun isolation | a failed first attempt cannot pass from retained globals |
| xdist | stateful groups pass under `load` and `worksteal` without affinity |
| Sphinx | resolved doctrees retain hidden setup/cleanup nodes and include attribution |
| Extension seam | a contributed checker compares and renders with the same instance |
| pytest-asyncio | a 1.x async autouse fixture populates the doctest namespace |
| Packaging | the core package and `py.typed` are present in wheel-from-sdist validation |

The xdist result proves the item boundary under two schedulers. It does not prove
heterogeneous workers or every distribution mode. The Sphinx result proves
extraction from its resolved tree, not a Sphinx execution lifecycle.

## ADR shortcomings exposed by the bakeoff

The architecture is usable, but these claims remain incomplete:

- The diagnostics core captures, deduplicates, and suppresses known noise, but
  the pytest adapter does not yet fail unsuppressed errors or render warnings.
  Message-substring classification is provisional because docutils supplies no
  stable diagnostic codes. The direct facade also drops the channel, so a
  malformed option's Sphinx-compatible warning is not yet user-visible.
- Partial block skips remain worker-local in `GroupResult`; there is no versioned
  JSON-safe pytest report projection or controller-side terminal summary.
- Sphinx contributor timing and the xdist registry/settings manifest are designs,
  not implemented lifecycle contracts.
- The extended runtime matrix still lacks report-only-first, repeated-call, and
  interactive debugger coverage. Expected-exception output, `SyntaxError`,
  `IGNORE_EXCEPTION_DETAIL`, and inline fail-fast are covered.
- The core avoids CPython's private runner loop but still uses the private
  `DocTestParser._EXAMPLE_RE` and `_EXCEPTION_RE` contracts. Their behavior is
  exercised indirectly, not yet guarded by focused compatibility probes.
- The Python 3.10/Sphinx 8 stack constrains docutils to its pre-0.22 line
  convention. The package now states `<0.22`; supporting docutils 0.22 requires
  the coordinated Python/Sphinx policy change in ADR 0005.
- Standalone MyST root-line recovery cannot prove exact locations inside
  included Markdown files. It refuses to stamp a root line onto an included
  source and retains the parser's ambiguous fallback.
- Profile context-manager entry and exit failures do not yet have phase-aware
  result semantics, and the initial runtime contract has no separate
  profile-decline outcome.
- The direct facade cannot reproduce doctest's complete verbose
  `Trying`/`Expecting`/`ok` stream because successful per-example events are not
  retained. Failure and summary output remain stock-shaped. A cleanup error that
  follows an ordinary doctest mismatch is also retained only in the core result;
  the direct facade has no secondary-outcome rendering channel yet.
- The pytest private-API quarantine binds its symbols eagerly and has no
  prerelease CI probe, so an unsupported pytest can still fail at plugin import.
- The pytest 7.2 floor also requires an older pytest-asyncio test dependency;
  the matrix must pin those versions together rather than installing each
  plugin's newest release independently.
- The legacy adapter is still a flat module, which leaves its private quarantine
  as the top-level `_pytest_doctest_compat` module. A packaged adapter namespace
  would contain that private surface more cleanly.
- A registered block kind and its custom expected-output stamp are preserved
  through projection, but registration alone does not teach reST or MyST a new
  directive.
- Orphan, misplaced, and duplicate `testoutput` records still need explicit
  diagnostics. Pairing itself is group-local and duplicate output follows
  Sphinx's last-one-wins rule. `testcode :pyversion:` is deliberately enforced
  rather than silently ignored as Sphinx does.
- Async pytest fixtures compose with documentation items under pytest-asyncio
  1.x. Its pytest-7-compatible 0.21 line does not await an async autouse fixture
  for this item shape. Async block execution is only represented by the
  execution-profile seam; no async profile was implemented in this spike.
- Document front-matter settings were premature and are deferred.

## Conclusion

Keep the typed core and thin adapters. Do not return to the monolith and do not
base extended execution on CPython's private loop. The ADR's central
one-item-per-shared-group decision survived implementation; its overclaims were
mostly in conformance, diagnostics, host bootstrap, and reporting rather than in
the core boundary itself.
