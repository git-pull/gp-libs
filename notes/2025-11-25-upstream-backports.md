# Upstream Doctest Backport Audit Report

**Date:** 2025-11-25
**Audited Repositories:**
- CPython doctest: `~/study/c/cpython/Lib/doctest.py`
- pytest doctest plugin: `~/study/python/pytest/src/_pytest/doctest.py`
- Sphinx doctest extension: `~/work/reStructuredText/sphinx/sphinx/ext/doctest.py`

## Executive Summary

After comprehensive audit of **115 commits** across all three upstream sources (CPython 27, pytest 35, Sphinx 53), **only 2 backports are needed**:

1. pytest `9cd14b4ff` (2024-02-06) - Autouse fixtures fix
2. Sphinx `ad0c343d3` (2025-01-04) - Regex whitespace fix

### Key Architectural Insight

**gp-libs' `DocutilsDocTestFinder` is NOT a subclass of `doctest.DocTestFinder`**. It's a completely different implementation:
- Parses reStructuredText/Markdown documents using docutils/myst-parser
- Extracts doctest blocks from markup nodes (not Python source inspection)
- Uses `doctest.DocTestParser.get_doctest()` to create `DocTest` objects
- Delegates test execution to standard `doctest.DocTestRunner`

CPython fixes to `_from_module()`, `_find_lineno()`, and `_find()` don't apply because gp-libs doesn't use these methods.

**Note:** The `_from_module()` method at lines 402-426 of `doctest_docutils.py` is dead code - it's never called and would fail if called (calls `super()._from_module()` but no parent class has this method). This could be cleaned up separately.

---

## Backports Required (Chronological Order)

### 1. pytest Autouse Fixtures Fix (2024-02-06)

**Source:** pytest commit `9cd14b4ff`
**GitHub:** https://github.com/pytest-dev/pytest/commit/9cd14b4ff
**Issue:** pytest-dev/pytest#11929
**Type:** Bug Fix

**Problem:** Autouse fixtures defined in `conftest.py` may not be picked up for doctest collection because `_nodeid_autousenames` is consulted at collection time before fixtures are parsed.

**File:** `src/pytest_doctest_docutils.py`

**Change:** Add after line ~307 in `DocTestDocutilsFile.collect()`:
```python
# While doctests in .rst/.md files don't support fixtures directly,
# we still need to pick up autouse fixtures.
# Backported from pytest commit 9cd14b4ff (2024-02-06).
# https://github.com/pytest-dev/pytest/commit/9cd14b4ff
self.session._fixturemanager.parsefactories(self)
```

---

### 2. Sphinx Doctest Flag Regex Fix (2025-01-04)

**Source:** Sphinx commit `ad0c343d3`
**GitHub:** https://github.com/sphinx-doc/sphinx/pull/13164
**Type:** Bug Fix

**Problem:** The `doctestopt_re` regex doesn't match leading whitespace before `# doctest:`, causing trailing whitespace in rendered output when flags are trimmed.

**File:** `src/doctest_docutils.py` line 33

**Before:**
```python
doctestopt_re = re.compile(r"#\s*doctest:.+$", re.MULTILINE)
```

**After:**
```python
doctestopt_re = re.compile(r"[ \t]*#\s*doctest:.+$", re.MULTILINE)
```

---

## Comprehensive Commit Audit

### CPython doctest.py (27 commits since 2022-01-01)

| Date | Commit | Type | Description | Applicable? | Reason |
|------|--------|------|-------------|-------------|--------|
| 2025-07-25 | `fece15d29f2` | bug fix | cached functions lineno | NO | Uses `_find_lineno()` - gp-libs gets line numbers from docutils nodes |
| 2025-07-15 | `cb59eaefeda` | docs | testmod docstring | NO | Documentation only |
| 2025-05-31 | `ad39f017881` | feature | unittest subtests | AUTO | Uses `DocTestCase` - gp-libs uses pytest |
| 2025-05-30 | `cb8a72b301f` | bug fix | unittest error report | AUTO | Uses `DocTestCase` - gp-libs uses pytest |
| 2025-05-05 | `4ac916ae33b` | feature | argparse color | NO | Unrelated module |
| 2025-01-20 | `6f167d71347` | refactor | color detection stdout | AUTO | Internal to `DocTestRunner` - inherited via stdlib |
| 2024-09-24 | `af8403a58db` | feature | pdb commands arg | NO | Unrelated module |
| 2024-05-22 | `ef172521a9e` | style | docstring backticks | NO | Documentation/style only |
| 2024-05-01 | `3b3f8dea575` | refactor | colorize module move | AUTO | Internal refactoring - inherited via stdlib |
| 2024-04-24 | `345e1e04ec7` | test | color test resilience | NO | Test changes only |
| 2024-04-24 | `975081b11e0` | feature | color output | AUTO | `DocTestRunner` feature - inherited via Python 3.13+ |
| 2024-04-10 | `4bb7d121bc0` | bug fix | wrapped builtin fix | NO | Uses `_find_lineno()` - gp-libs doesn't use this |
| 2024-03-28 | `29829b58a83` | bug fix | skip reporting | AUTO | Uses `DocTestCase` - gp-libs uses pytest |
| 2024-03-27 | `ce00de4c8cd` | style | pluralization | AUTO | `DocTestRunner.summarize()` - inherited via stdlib |
| 2024-02-19 | `872cc9957a9` | bug fix | -OO mode fix | AUTO | Uses `DocTestCase` - gp-libs uses pytest |
| 2024-02-14 | `bb791c7728e` | bug fix | decorated fn lineno | NO | Uses `_find_lineno()` - gp-libs doesn't use this |
| 2023-12-15 | `8f8f0f97e12` | bug fix | property lineno | NO | Uses `_find_lineno()` - gp-libs doesn't use this |
| 2023-11-25 | `fbb9027a037` | bug fix | DocTest.__lt__ None | AUTO | `DocTest` class - inherited via stdlib |
| 2023-11-04 | `18c954849bc` | bug fix | SyntaxError subclass | AUTO | `DocTestRunner.__run()` - inherited via stdlib |
| 2023-10-21 | `fd60549c0ac` | bug fix | exception notes | AUTO | `DocTestRunner.__run()` - inherited via stdlib |
| 2023-09-02 | `4f9b706c6f5` | feature | skip counting | AUTO | `TestResults`/`DocTestRunner` - inherited via stdlib |
| 2023-08-07 | `85793278793` | bug fix | regex escape class | NO | Uses `_find_lineno()` - gp-libs doesn't use this |
| 2023-01-13 | `b5d43479503` | refactor | getframemodulename | NO | Internal CPython change |
| 2022-12-30 | `79c10b7da84` | bug fix | MethodWrapperType | NO | Uses `_from_module()` - gp-libs doesn't call this |
| 2022-05-19 | `8db2b3b6878` | bug fix | empty DocTest lineno | NO | Uses `_find_lineno()` - gp-libs doesn't use this |
| 2022-03-22 | `7ba7eae5080` | bug fix | globs teardown | AUTO | Uses `DocTestCase` - gp-libs uses pytest |
| 2022-01-08 | `0fc58c1e051` | refactor | CodeType simplify | NO | Uses `_find_lineno()` - gp-libs doesn't use this |

**Summary:** 0 backports needed. 14 AUTO-inherited via stdlib, 13 NOT applicable.

---

### pytest doctest.py (35 commits since 2022-01-01)

| Date | Commit | Type | Description | Applicable? | Reason |
|------|--------|------|-------------|-------------|--------|
| 2025-09-12 | `bb712f151` | version | Drop Python 3.9 | NO | Version support change |
| 2024-11-29 | `17c5bbbda` | style | %r specifiers | NO | Style fix - internal to pytest |
| 2024-11-20 | `1bacc0007` | typing | re namespace | NO | Typing style - internal to pytest |
| 2024-11-10 | `05ed0d0f9` | typing | deprecated-typing-alias | NO | Typing compat - internal to pytest |
| 2024-11-10 | `a4cb74e86` | chore | CI after py3.8 drop | NO | CI/docs change |
| 2024-08-29 | `c947145fb` | compat | typing.Self fix | NO | Typing compat - internal to pytest |
| 2024-08-14 | `b08b41cef` | chore | pre-commit update | NO | Tooling update |
| 2024-06-17 | `9295f9fff` | style | `__future__` annotations | CONSIDER | Style modernization - could match |
| 2024-06-18 | `49374ec7a` | bug fix | patch condition fix | NO | `MockAwareDocTestFinder` - gp-libs uses `DocutilsDocTestFinder` |
| 2024-06-07 | `f94109937` | refactor | finder cleanup | NO | `MockAwareDocTestFinder` - gp-libs uses `DocutilsDocTestFinder` |
| 2024-05-27 | `48cb8a2b3` | chore | pre-commit update | NO | Tooling update |
| 2024-04-30 | `4788165e6` | style | format specifiers | NO | Style fix - internal to pytest |
| 2024-03-13 | `c0532dda1` | chore | pre-commit update | NO | Tooling update |
| 2024-02-23 | `010ce2ab0` | typing | from_parent return types | AUTO | Typing - inherited via `DoctestItem` |
| 2024-02-06 | `9cd14b4ff` | bug fix | autouse fixtures | **BACKPORT** | **DocTestDocutilsFile needs this!** |
| 2024-02-06 | `6e5008f19` | refactor | module import | AUTO | `DoctestModule` - inherited for .py files |
| 2024-01-31 | `4588653b2` | chore | migrate to ruff | NO | Tooling change |
| 2024-01-28 | `878af85ae` | typing | disallow untyped defs | NO | Typing strictness - internal to pytest |
| 2024-01-13 | `06dbd3c21` | refactor | conftest handling | AUTO | `DoctestModule` - inherited for .py files |
| 2023-09-08 | `6ad9499c9` | typing | missing annotations | NO | Typing - internal to pytest |
| 2023-09-08 | `2ed2e9208` | typing | remove Optionals | NO | Typing - internal to pytest |
| 2023-09-08 | `ab63ebb3d` | refactor | inline _setup_fixtures | AUTO | `DoctestItem` - inherited |
| 2023-09-08 | `b3a981d38` | refactor | fixture funcargs | AUTO | Fixture internals - inherited |
| 2023-09-07 | `e787d2ed4` | merge | cached_property PR | AUTO | Merge commit |
| 2023-09-01 | `82bd63d31` | feature | fixturenames field | AUTO | `DoctestItem` - inherited |
| 2023-08-20 | `a357c7abc` | test | coverage ignore | NO | Test coverage change |
| 2023-08-19 | `7a625481d` | review | PR suggestions | AUTO | Part of cached_property work |
| 2023-08-19 | `ebd571bb1` | refactor | _from_module move | NO | `MockAwareDocTestFinder` - gp-libs uses different finder |
| 2023-08-16 | `d4fb6ac9f` | bug fix | cached_property | NO | `MockAwareDocTestFinder` - gp-libs has own implementation |
| 2023-07-16 | `9e164fc4f` | refactor | FixtureRequest abstract | AUTO | Fixture internals - inherited |
| 2023-07-10 | `01f38aca4` | docs | fixture comments | NO | Documentation only |
| 2023-02-07 | `59e7d2bbc` | chore | pre-commit update | NO | Tooling update |
| 2022-10-07 | `8e7ce60c7` | typing | export DoctestItem | AUTO | **Authored by Tony Narlock** - typing export |
| 2022-06-29 | `c34eaaaa1` | bug fix | importmode pass | AUTO | `DoctestModule` - inherited for .py files |
| 2022-05-31 | `e54c6a136` | docs | code-highlight default | NO | Documentation only |
| 2022-05-10 | `231e22063` | docs | docstrings move | NO | Documentation only |
| 2022-01-31 | `9d2ffe207` | chore | pre-commit fixes | NO | Tooling update |

**Summary:** 1 backport needed (`9cd14b4ff`). 12 AUTO-inherited, 22 NOT applicable.

---

### Sphinx doctest.py (53 commits since 2022-01-01)

| Date | Commit | Type | Description | Applicable? | Reason |
|------|--------|------|-------------|-------------|--------|
| 2025-09-01 | `14717292b` | bug fix | default group config | NO | Sphinx builder-specific |
| 2025-06-07 | `3044d6753` | refactor | avoid self.app | NO | Sphinx builder-specific |
| 2025-06-06 | `77a0d6658` | refactor | extract nested functions | NO | Sphinx builder-specific |
| 2025-06-03 | `987ccb2a9` | style | str.partition | NO | Style - internal to Sphinx |
| 2025-03-24 | `5831b3eea` | feature | doctest_fail_fast | NO | Already via pytest `-x` and `continue_on_failure` |
| 2025-02-10 | `f96904146` | typing | config valid_types | NO | Sphinx config system |
| 2025-01-22 | `2d41d43ce` | typing | no-any-generics | NO | Typing - internal to Sphinx |
| 2025-01-16 | `a56fdad70` | refactor | colour module | NO | Sphinx console module |
| 2025-01-14 | `c4daa95c0` | style | Ruff D category | NO | Linting rules |
| 2025-01-13 | `f6d1665f8` | typing | frozensets | NO | Typing - internal to Sphinx |
| 2025-01-12 | `72ce43619` | typing | runtime typing imports | NO | Typing - internal to Sphinx |
| 2025-01-07 | `44aced1ab` | docs | confval directives | NO | Documentation only |
| 2025-01-04 | `ad0c343d3` | bug fix | regex whitespace | **BACKPORT** | **doctestopt_re used directly!** |
| 2025-01-02 | `b5f9ac8af` | style | RUF100 lint | NO | Linting rules |
| 2024-12-17 | `01d993b35` | style | auto formatting | NO | Formatting only |
| 2024-11-03 | `7801bd77b` | style | os.path absolute | NO | Import style |
| 2024-10-19 | `e58dd58f3` | style | PLR6201 lint | NO | Linting rules |
| 2024-10-10 | `d135d2eba` | typing | Builder.write final | NO | Sphinx builder-specific |
| 2024-08-13 | `fadb6b10c` | bug fix | --fail-on-warnings | NO | Sphinx CLI-specific |
| 2024-07-23 | `de15d61a4` | refactor | pathlib usage | NO | Sphinx project module |
| 2024-07-22 | `9e3f4521d` | version | Drop Python 3.9 | NO | Version support change |
| 2024-04-01 | `cb8a28dd7` | typing | color stubs | NO | Typing - internal to Sphinx |
| 2024-03-23 | `22cee4209` | typing | types-docutils | NO | Typing stubs change |
| 2024-03-22 | `6c92c5c0f` | chore | ruff version bump | NO | Tooling update |
| 2024-03-21 | `d59b15837` | typing | ExtensionMetadata | NO | Typing - internal to Sphinx |
| 2024-03-03 | `7f582a56b` | bug fix | resource leak | NO | Sphinx builder file handle - gp-libs doesn't have this |
| 2024-02-01 | `aff95789a` | chore | Ruff 0.2.0 config | NO | Tooling update |
| 2024-01-16 | `55f308998` | style | str.join | NO | Style - internal to Sphinx |
| 2024-01-14 | `f7fbfaa47` | style | pydocstyle rules | NO | Linting rules |
| 2024-01-03 | `259118d18` | typing | valid_types narrow | NO | Typing - internal to Sphinx |
| 2024-01-03 | `19b295051` | typing | rebuild narrow | NO | Typing - internal to Sphinx |
| 2023-08-13 | `f844055dd` | style | SIM115 context | NO | Style - internal to Sphinx |
| 2023-08-13 | `9bcf1d8bb` | style | TCH001 import | NO | Import organization |
| 2023-08-13 | `36012b7d9` | style | TCH002 import | NO | Import organization |
| 2023-07-28 | `92e60b3f1` | typing | type:ignore params | NO | Typing - internal to Sphinx |
| 2023-07-28 | `ff20efcd7` | refactor | show_successes tweaks | NO | Follow-up to show_successes feature |
| 2023-07-28 | `aef544515` | feature | doctest_show_successes | NO | pytest handles verbosity natively |
| 2023-07-25 | `ad61e4115` | version | Drop Python 3.8 | NO | Version support change |
| 2023-07-23 | `4de540efb` | typing | strict optional | NO | Typing - internal to Sphinx |
| 2023-02-17 | `c8f4a03da` | style | COM812 fix | NO | Linting rules |
| 2023-01-02 | `4032070e8` | style | pyupgrade | NO | Style modernization - Sphinx specific |
| 2023-01-01 | `14a9289d7` | style | PEP 604 types | CONSIDER | Style modernization - could match |
| 2022-12-30 | `26f79b0d2` | style | PEP 595 types | NO | PEP 595 is about datetime |
| 2022-12-30 | `f4c8a0a68` | style | `__future__` annotations | CONSIDER | Style modernization - could match |
| 2022-12-29 | `7fb45a905` | style | bandit checks | NO | Security linting |
| 2022-12-29 | `b89c33fc0` | style | pygrep-hooks | NO | Linting rules |
| 2022-09-25 | `9ced73631` | bug fix | highlighting lexers | NO | Sphinx highlighting-specific |
| 2022-09-08 | `ba548f713` | docs | is_allowed_version | NO | **Authored by Tony Narlock** - Different parameter order in gp-libs |
| 2022-07-18 | `a504ac610` | typing | typing strictness | NO | Typing - internal to Sphinx |
| 2022-03-24 | `a432bf8c1` | docs | PEP links | NO | Documentation only |
| 2022-02-20 | `6bb7b891a` | style | copyright fields | NO | Style - internal to Sphinx |
| 2022-02-20 | `b691ebcc3` | style | PEP 257 docstrings | NO | Docstring style |
| 2022-02-20 | `5694e0ce6` | style | docstring indent | NO | Docstring style |
| 2022-02-20 | `4f5a3269a` | style | docstring first line | NO | Docstring style |
| 2022-02-19 | `6b8bccec5` | style | module titles | NO | Docstring style |
| 2022-01-02 | `05a898ecb` | compat | Node.findall | NO | Already in `docutils_compat.py` |

**Summary:** 1 backport needed (`ad0c343d3`). 0 AUTO-inherited, 52 NOT applicable.

---

## Summary Statistics

| Repository | Total Commits | Backport Needed | Auto-Inherited | Not Applicable |
|------------|--------------|-----------------|----------------|----------------|
| CPython | 27 | 0 | 14 | 13 |
| pytest | 35 | 1 | 12 | 22 |
| Sphinx | 53 | 1 | 0 | 52 |
| **Total** | **115** | **2** | **26** | **87** |

## Applicability Legend

- **BACKPORT**: Needs to be manually backported to gp-libs
- **AUTO**: Automatically inherited via stdlib/pytest dependency upgrades
- **NO**: Not applicable to gp-libs architecture
- **CONSIDER**: Optional style modernization (not a bug fix)

## Optional: Style Modernization (Separate Effort)

Some commits marked "CONSIDER" could be applied as style modernization:
- `9295f9fff` (pytest) / `f4c8a0a68` (Sphinx): `from __future__ import annotations` - **Already in gp-libs**
- `14a9289d7` (Sphinx): PEP 604 types (`X | Y` instead of `Union[X, Y]`)

These are style choices, not bug fixes or API compatibility issues.
