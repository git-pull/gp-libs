# pytest-xdist

Pinned at [`v3.8.0`](https://github.com/pytest-dev/pytest-xdist/tree/v3.8.0).

## Classification

A controller/worker distribution layer over execnet. All scheduling is integer
indices into a per-worker collection list, and the controller **never collects**.
That single asymmetry is the source of every constraint xdist imposes on a plugin
that wants to keep related tests together.

## Core data structures

```text
controller                              worker (one per process)
  NodeManager -> specs: list[str]         session collects normally
  Scheduling implementation               reports node ids back as STRINGS
    node2collection: dict[node, list[str]]
    node2pending:    dict[node, list[int]]   <- integer indices, not ids
    collection:      list[str]               <- the agreed id list
```

The controller's entire model of the suite is a list of node-id strings that
arrived from a worker. It has no items, no marks, no fixtures and no knowledge of
what any test does. A plugin that needs "these tests share state" therefore cannot
tell the controller so directly — it can only encode the fact *into the node id*
or infer it from string shape.

## Data flow

```text
pytest_cmdline_main   xdist promotes -n N into --dist load (tryfirst)
   |
pytest_sessionstart -> NodeManager.setup_nodes
   |                   pytest_xdist_setupnodes(config, specs)   <- specs already expanded
   v
each worker collects independently
   |
   +-> pytest_xdist_node_collection_finished(node, ids)
   |
   v
Scheduling.add_node_collection(node, ids)
   |  every worker's list must be IDENTICAL, in the same ORDER
   |  mismatch -> log "**Different tests collected, aborting run**"
   |              and assign nothing.  Zero tests execute.
   v
Scheduling.schedule() -> send integer index batches to workers
   |
   v  (on worker crash)
   only the UNCOMPLETED items of the crashed work unit are re-sent
   to a FRESH worker with FRESH process state
```

The abort path is the constraint that matters most. It is not an exception and it
is not loud in the usual sense: the scheduler logs a line, assigns nothing, and
the session ends having run nothing. Any collection-time decision that is not a
pure function of (files on disk, argv, ini) — a timestamp, a PID, a hostname, a
dict iteration order, an evaluated `:skipif:` that depends on the environment —
produces this.

The crash path is the second. Because only uncompleted items of a work unit are
retried, a group whose blocks 1-2 ran before the crash has blocks 3..N re-run
against an empty process, producing a `NameError` cascade attributed to the wrong
cause. Worker restarts are on by default.

## Extension seams

| Seam | Kind |
|---|---|
| `pytest_xdist_make_scheduler(config, log)` | hook — substitute a `Scheduling` implementation |
| `pytest_xdist_node_collection_finished(node, ids)` | hook — observe the agreed id list |
| `pytest_xdist_setupnodes(config, specs)` | hook — receives the already-expanded spec list; never raises |
| `pytest_xdist_auto_num_workers(config)` | hook |
| `LoadScopeScheduling._split_scope(nodeid) -> str` ([`loadscope.py:284`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadscope.py#L284)) | subclass hook — **the only affinity primitive in the codebase** |
| `@pytest.mark.xdist_group(name)` | marker, honoured only under `--dist loadgroup` |

`_split_scope` is worth stating plainly: it is a pure function from a node-id
string to a scope string, and both shipped grouping modes are two-line overrides
of it — [`loadfile.py:35`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadfile.py#L35)
returns the file part, [`loadgroup.py:24`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadgroup.py#L24)
returns the `@`-suffix. `load` and `worksteal` have **no scope concept at any
layer**: `load` slices `pending[:num]` and `worksteal` steals a raw suffix.

So under a user-typed `--dist load`, a plugin has exactly three options: refuse
the run, substitute the scheduler, or make the group not need protecting. There
is no "declare affinity and let the chosen scheduler honour it" API.

The `xdist_group` marker is narrower than it appears. It is applied
[worker-side](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/remote.py#L245-L254),
and only when the worker's own literal `--dist` string is `loadgroup`; it works by
appending `@<group>` to `item._nodeid`. A controller-side scheduler substitution
never reaches a worker, so no `@` suffix is written and every item becomes its own
scope — strictly worse than plain `load`. Node ids copied from a `loadgroup` run
also do not select under `-n0`.

## Configuration

`-n`, `--dist`, `--tx`, `--maxprocesses`, `--max-worker-restart`. Worker counts
come from
[`parse_tx_spec_config`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/workermanage.py#L26-L37),
which builds a *list*:

```python
xspeclist.extend([xspec[i + 1 :]] * num)
```

List multiplication by a negative number yields an empty list, so a negative
multiplier contributes **zero** specs. A re-implementation that sums the integer
instead contributes a negative number, and `--tx -1*popen --tx 2*popen` then
counts 1 where xdist counts 2 — a divergence whose failure direction is
permissive.

`parse_tx_spec_config` raises `pytest.UsageError` when a run names no environment,
so it cannot be called defensively. `pytest_xdist_setupnodes(config, specs)` is
the safe source of the same information: it receives the already-expanded list,
fires during `pytest_sessionstart` — strictly before `pytest_xdist_make_scheduler`
— and never raises.

## What it cannot do

- **Ship a Python object between processes.** Only execnet-serializable builtins
  cross. A live `globs` mapping cannot be shared, which is the whole reason a
  shared doctest namespace is a distribution problem.
- **Tell the controller what an item is.** The controller sees strings.
- **Preserve process state across a worker restart** for the uncompleted tail of a
  work unit.

## Anchors

- [`parse_tx_spec_config`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/workermanage.py#L26-L37)
- [`_split_scope`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadscope.py#L284) ·
  [`loadfile`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadfile.py#L35) ·
  [`loadgroup`](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadgroup.py#L24)
- [`load.schedule` abort](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/load.py#L259) ·
  [`loadscope.schedule` abort](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadscope.py#L359)
- [`xdist_group` node-id append](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/remote.py#L245-L254)
