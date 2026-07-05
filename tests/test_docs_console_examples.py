"""Tests for documentation console examples."""

from __future__ import annotations

import os
import pathlib
import re
import shlex
import subprocess
import sys
import textwrap
import typing as t

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
CommandPolicy = t.Literal["execute", "validate", "unknown"]


class ConsoleExample(t.NamedTuple):
    """Console example collected from a Markdown page."""

    path: pathlib.Path
    line_number: int
    commands: tuple[str, ...]


class ConsolePolicyCase(t.NamedTuple):
    """Console command classification case."""

    test_id: str
    command: str
    expected_policy: CommandPolicy


POLICY_CASES: tuple[ConsolePolicyCase, ...] = (
    ConsolePolicyCase(
        test_id="existing-doctest-docutils-target",
        command="python -m doctest_docutils README.md -v",
        expected_policy="execute",
    ),
    ConsolePolicyCase(
        test_id="missing-doctest-docutils-target",
        command="python -m doctest_docutils README.rst -v",
        expected_policy="validate",
    ),
    ConsolePolicyCase(
        test_id="pytest-command",
        command="pytest docs/",
        expected_policy="validate",
    ),
    ConsolePolicyCase(
        test_id="install-command",
        command="uv add gp-libs",
        expected_policy="validate",
    ),
    ConsolePolicyCase(
        test_id="stdlib-doctest-help",
        command="python -m doctest --help",
        expected_policy="validate",
    ),
    ConsolePolicyCase(
        test_id="shell-control",
        command="uv run ruff format . && uv run pytest",
        expected_policy="unknown",
    ),
)


def iter_documentation_markdown_files(
    repo_root: pathlib.Path,
) -> t.Iterator[pathlib.Path]:
    """Yield Markdown files that are part of the authored documentation."""
    candidates = [repo_root / "README.md", *(repo_root / "docs").rglob("*.md")]
    for path in sorted(candidates):
        relative = path.relative_to(repo_root)
        if "_build" in relative.parts:
            continue
        if path.name in {"AGENTS.md", "CLAUDE.md"}:
            continue
        yield path


def collect_console_examples(path: pathlib.Path) -> t.Iterator[ConsoleExample]:
    """Collect prompt commands from Markdown console fences."""
    in_console = False
    in_other_fence = False
    fence = ""
    fence_line_number = 0
    command_line_number = 0
    commands: list[str] = []

    lines = path.read_text(encoding="utf-8").splitlines()
    for line_number, line in enumerate(lines, 1):
        stripped = line.lstrip()
        if not in_console:
            if in_other_fence:
                if stripped.startswith(fence) and stripped[len(fence) :].strip() == "":
                    in_other_fence = False
                continue

            match = re.match(r"^(`{3,}|~{3,})\s*console\s*$", stripped)
            if match is not None:
                fence = match.group(1)
                in_console = True
                fence_line_number = line_number
                command_line_number = 0
                commands = []
                continue

            match = re.match(r"^(`{3,}|~{3,})", stripped)
            if match is None:
                continue

            fence = match.group(1)
            in_other_fence = True
            continue

        if stripped.startswith(fence) and stripped[len(fence) :].strip() == "":
            yield ConsoleExample(
                path=path,
                line_number=command_line_number or fence_line_number,
                commands=tuple(commands),
            )
            in_console = False
            continue

        if stripped.startswith("$ "):
            if command_line_number == 0:
                command_line_number = line_number
            commands.append(stripped[2:])


def classify_console_command(
    repo_root: pathlib.Path,
    command: str,
) -> CommandPolicy:
    """Classify whether a docs command is safe to execute in pytest."""
    if _has_shell_control(command):
        return "unknown"

    try:
        parts = shlex.split(command)
    except ValueError:
        return "unknown"

    if not parts:
        return "unknown"

    if len(parts) >= 3 and parts[:3] == ["python", "-m", "doctest_docutils"]:
        target = _first_non_option(parts[3:])
        if target is not None and (repo_root / target).is_file():
            return "execute"
        return "validate"

    if len(parts) >= 3 and parts[:3] == ["python", "-m", "doctest"]:
        return "validate"

    validate_commands = {
        "cd",
        "git",
        "just",
        "pip",
        "pipx",
        "py.test",
        "pytest",
        "uv",
        "uvx",
    }
    if parts[0] in validate_commands:
        return "validate"

    return "unknown"


def _has_shell_control(command: str) -> bool:
    """Return whether a command uses shell control syntax."""
    return bool(re.search(r"&&|\|\||[;|<>]|\$\(|`", command))


def _first_non_option(parts: list[str]) -> str | None:
    """Return the first command part that is not an option."""
    for part in parts:
        if not part.startswith("-"):
            return part
    return None


def run_safe_console_example(
    *,
    repo_root: pathlib.Path,
    example: ConsoleExample,
    tmp_path: pathlib.Path,
) -> str:
    """Execute an allowlisted console example in a temp-home sandbox."""
    command = example.commands[0]
    parts = shlex.split(command)
    target = _first_non_option(parts[3:])
    if target is None:
        return f"{example.path}:{example.line_number}: missing doctest target"

    sandbox = tmp_path / f"{example.path.stem}-{example.line_number}"
    sandbox.mkdir()
    sandbox_home = sandbox / "home"
    sandbox_home.mkdir()

    source = repo_root / target
    if not source.is_file():
        return f"{example.path}:{example.line_number}: missing doctest target {target}"

    target_path = sandbox / target
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    pythonpath_parts = [str(repo_root / "src")]
    if existing_pythonpath:
        pythonpath_parts.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)
    env["HOME"] = str(sandbox_home)

    completed = subprocess.run(
        [sys.executable, "-m", "doctest_docutils", *parts[3:]],
        cwd=sandbox,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if completed.returncode == 0:
        return ""

    return (
        f"{example.path}:{example.line_number}: {command!r} exited "
        f"{completed.returncode}\nstdout:\n{completed.stdout}\nstderr:\n"
        f"{completed.stderr}"
    )


@pytest.mark.parametrize(
    ConsolePolicyCase._fields,
    POLICY_CASES,
    ids=[case.test_id for case in POLICY_CASES],
)
def test_classify_console_commands(
    test_id: str,
    command: str,
    expected_policy: CommandPolicy,
) -> None:
    """Classify executable examples separately from policy-only examples."""
    assert classify_console_command(REPO_ROOT, command) == expected_policy


def test_collect_console_examples_from_markdown(tmp_path: pathlib.Path) -> None:
    """Collect one prompt command per console fence with source line numbers."""
    page = tmp_path / "usage.md"
    page.write_text(
        textwrap.dedent(
            """
            # Usage

            ```console
            $ python -m doctest_docutils README.md -v
            ```

            ```python
            >>> 2 + 2
            4
            ```
            """,
        ).lstrip(),
        encoding="utf-8",
    )

    examples = list(collect_console_examples(page))

    assert [(example.line_number, example.commands) for example in examples] == [
        (4, ("python -m doctest_docutils README.md -v",)),
    ]


def test_collect_console_examples_ignores_nested_markdown_fences(
    tmp_path: pathlib.Path,
) -> None:
    """Ignore illustrative nested console fences inside another fenced block."""
    page = tmp_path / "usage.md"
    page.write_text(
        textwrap.dedent(
            """
            # Usage

            ````markdown
            ```console
            $ unknown nested command
            ```
            ````
            """,
        ).lstrip(),
        encoding="utf-8",
    )

    assert list(collect_console_examples(page)) == []


def test_documentation_console_examples_are_testable(
    tmp_path: pathlib.Path,
) -> None:
    """Validate every published console example and execute safe local examples."""
    failures: list[str] = []
    examples = [
        example
        for path in iter_documentation_markdown_files(REPO_ROOT)
        for example in collect_console_examples(path)
    ]
    assert examples

    for example in examples:
        if len(example.commands) != 1:
            failures.append(
                f"{example.path}:{example.line_number}: "
                "console blocks must contain exactly one prompt command",
            )
            continue

        command = example.commands[0]
        policy = classify_console_command(REPO_ROOT, command)
        if policy == "unknown":
            failures.append(
                f"{example.path}:{example.line_number}: "
                f"unclassified console command: {command}",
            )
            continue

        if policy == "execute":
            result = run_safe_console_example(
                repo_root=REPO_ROOT,
                example=example,
                tmp_path=tmp_path,
            )
            if result:
                failures.append(result)

    assert failures == []
