# Documentation voice

This file covers the *voice* of prose under `docs/` — how to frame a
page so a reader meets the idea before its configuration. It
complements the repository-root `AGENTS.md`, which already governs
code blocks, doctest rules, changelog conventions, and MyST roles.
When the two overlap, the root file wins; this one only answers the
question it leaves open: how should the prose sound?

## Who you are writing for

The default reader is wiring gp-libs into their own project: pointing
pytest at `docs/` with `pytest_doctest_docutils`, running
`python -m doctest_docutils README.md` by hand, or adding
`linkify_issues` to a Sphinx `conf.py`. They are fluent in pytest and
Sphinx as users — `conftest.py`, fixtures, `extensions`, `testpaths` —
and write reStructuredText or Markdown daily, but you cannot assume
they know gp-libs' internals: docutils node traversal, directive
registration, or how the finder decides a block is a doctest.

A second, smaller reader works *on* gp-libs or against its lower
layers: the doctest finder, the docutils compatibility shims,
myst-parser directive registration, or contributing. Serve them too,
but mark their material opt-in ("for the rarer cases", "advanced") so
the default reader knows they can stop. Never make the common case pay
a comprehension tax for the advanced one.

## Voice

- **Second person, present tense, active.** "You point pytest at
  `docs/`", not "Files are collected". Address the reader who is doing
  the thing.
- **Concept before configuration.** Open by saying what the tool *is*
  and what it does for the reader. The `conf.py` key, the pytest
  flag — those are the last details they need, not the first. A page
  that opens with "set these keys" has buried the idea under its
  mechanics.
- **Say when they can stop.** Lead with the default and the
  reassurance: install the plugin and `pytest docs/` just works;
  `issue_url_tpl` is the one setting `linkify_issues` needs. Let a
  skimmer leave after one paragraph.
- **Progressive disclosure.** Order by how many readers need it: the
  default → the one option a few will tune (a custom `issue_re`,
  `--doctest-docutils-modules`) → running `doctest_docutils` directly
  → the docutils machinery underneath. Each step is for a smaller
  audience than the last.
- **Lean on the pipeline.** The reader thinks in a chain: a `.rst` or
  `.md` file is parsed (docutils, with myst-parser for Markdown), its
  examples are collected, then run. It is the mental model the whole
  toolkit hangs on; reinforce that chain when you explain why Markdown
  needs myst-parser or why a fixture needs a visible `conftest.py`.
- **Name the trade-off.** If a choice costs something — the plugin
  disables pytest's standard doctest plugin, Markdown support goes
  through myst-parser, fixtures reach only files a `conftest.py` can
  see — say so, and say what it buys. State it; don't sell it.
- **Frame by concept, not by mechanism.** Don't headline a feature by
  its `conf.py` key or pytest flag in prose; that names the
  implementation surface, the reader's last concern. Name the concept.
  The mechanics vocabulary — the flag spelling, the default regex —
  belongs in a reference block or the API section, and only there.

## Examples that run

Prose examples under `docs/` are doctests, and they actually execute —
`testpaths` in `pyproject.toml` includes `docs`, and pytest collects
them with this repo's own `pytest_doctest_docutils` plugin. The docs
dogfood the tool they describe; a broken example is a failing test.

- Fence a `>>>` session as a ```` ```python ```` block or a
  ```` ```{doctest} ```` directive — the finder collects both, plus
  bare doctest blocks in reST. Use ```` ```console ```` for shell
  commands at a `$` prompt.
- `ELLIPSIS` and `NORMALIZE_WHITESPACE` are on globally via
  `doctest_optionflags`, so variable output can elide with `...`
  without a per-example flag.
- No `doctest_namespace` fixtures are registered for `docs/` — no
  `conftest.py` is visible to it — so keep examples self-contained:
  import what you use inside the block.
- Console fences are checked by
  `tests/test_docs_console_examples.py`. Keep one `$` prompt command per
  block; safe `python -m doctest_docutils ...` examples with existing
  local targets run in a temp-home sandbox, while install, watch,
  server, git, and full-suite commands are policy-validated only.

## What stays precise

Warm the framing, never the facts. Resolution-order lists, default
regex patterns like `issue_re`, exact flag spellings, error strings,
and class or function cross-references carry meaning in their exact
form — leave them alone. The friendly voice belongs in the sentences
*around* a precise block, introducing it, not inside it paraphrasing
it into vagueness.

## Cross-references

Point the advanced reader at the deep-dive rather than inlining it, and
put the link where their interest peaks — on the phrase that made them
curious ("how the finder decides", "the docutils machinery") — not as
a standalone footnote the eye skips. Use the MyST roles listed in the
root `AGENTS.md` (`{class}`, `{meth}`, `{func}`, `{exc}`, `{attr}`,
`{ref}`, `{doc}`). A `{ref}` must match its target's anchor exactly —
anchors mix underscore and hyphen forms across pages
(`doctest_docutils`, `linkify-issues`). `just build-docs` catches a
broken cross-reference; the doctests do not — so build the docs before
you commit.

Link the first prose mention of any symbol that has a useful
destination on that page. This includes Python objects, gp-libs APIs,
pytest and Sphinx concepts with intersphinx destinations, topic pages,
and external tools or projects. Use the most specific target
available: `{class}`, `{meth}`, `{func}`, `{mod}`, `{exc}`, or
`{attr}` for API objects; `{ref}` or `{doc}` for documentation pages
and section anchors; and a Markdown link or reference link for
external projects. After the first linked mention on a page, later
mentions can stay plain unless the distance or context makes another
link useful.

Do not rely on a later reference section to satisfy the first-mention
rule. If the first occurrence would be a heading, grid-card teaser, or
introductory sentence, link that occurrence or retitle the heading so
the first prose mention can carry the link. Leave command examples,
code blocks, and literal configuration values as code; link the
surrounding prose instead.

## A page that does this

`docs/modules/linkify_issues/index.md` is the worked example: a concept-first
intro that says what the extension does (plain-text `#123` becomes a
link) before any `conf.py` key, a two-step default configuration most
readers can stop after, `issue_re` marked as optional tuning for the
smaller audience, an honest close that more complex needs mean
forking, and the API reference last. Read it before reshaping another
page.

## Before you commit

- Does the page open with what the feature *is*, or with how to
  configure it?
- Can a reader who needs only the default stop after the first
  paragraph?
- Is anything framed as "the key/the flag" that should be named by
  concept instead?
- Are the advanced and internals-level parts clearly marked opt-in?
- Do the doctests still run — `uv run pytest docs/` — and did you
  leave every code block, pattern, and cross-reference exact?
- Did `just build-docs` stay clean — no new warning, no broken
  cross-reference?
