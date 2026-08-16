"""Pure projection from parsed records to immutable group plans."""

from __future__ import annotations

import doctest
import pathlib
import types
import typing as t

from .model import (
    ExampleRecipe,
    ExpectedOutput,
    GroupPlan,
    ParsedBlock,
    ParsedOutput,
    ParseResult,
    Phase,
    ProjectedBlock,
)
from .settings import ProjectionSettings

if t.TYPE_CHECKING:
    from .registry import RegistrySnapshot


class _GroupKey(t.NamedTuple):
    """Collision-free identity for one projected group.

    Attributes
    ----------
    author_name : str or None
        Declared group name, or ``None`` for a generated block group.
    block_ordinal : int or None
        Runnable-block ordinal for a generated group, or ``None`` for a
        declared group.
    """

    author_name: str | None
    block_ordinal: int | None


def _read_only(values: t.Mapping[t.Any, t.Any]) -> t.Mapping[t.Any, t.Any]:
    """Copy a mapping behind a read-only view."""
    return types.MappingProxyType(dict(values))


def _groups_for_block(
    block: ParsedBlock,
    settings: ProjectionSettings,
) -> tuple[_GroupKey, ...]:
    """Resolve an ordinary block's non-wildcard group names."""
    if block.groups:
        return tuple(_GroupKey(group, None) for group in block.groups)
    if settings.ungrouped == "default":
        return (_GroupKey("default", None),)
    return (_GroupKey(None, block.block_ordinal),)


def _test_groups(
    parsed: ParseResult,
    settings: ProjectionSettings,
    registry: RegistrySnapshot,
) -> tuple[_GroupKey, ...]:
    """Return executable group names in first declaration order."""
    groups: list[_GroupKey] = []
    has_wildcard = False
    for block in parsed.blocks:
        registration = registry.block_kinds.get(block.kind)
        if registration is None or registration.value.phase is not Phase.TEST:
            continue
        for group in _groups_for_block(block, settings):
            if group.author_name == "*":
                has_wildcard = True
            elif group not in groups:
                groups.append(group)
    if has_wildcard and not groups:
        groups.append(_GroupKey("default", None))
    return tuple(groups)


def _group_labels(groups: tuple[_GroupKey, ...]) -> dict[_GroupKey, str]:
    """Derive concise unique display labels without changing group identity."""
    reserved = {group.author_name for group in groups if group.author_name is not None}
    labels: dict[_GroupKey, str] = {}
    used: set[str] = set()
    for group in groups:
        if group.author_name is not None:
            label = group.author_name
        else:
            base = f"block-{group.block_ordinal}"
            label = base
            suffix = 1
            while label in reserved or label in used:
                marker = "anonymous" if suffix == 1 else f"anonymous-{suffix}"
                label = f"{base}[{marker}]"
                suffix += 1
        labels[group] = label
        used.add(label)
    return labels


def _destinations(
    block: ParsedBlock,
    *,
    settings: ProjectionSettings,
    groups: tuple[_GroupKey, ...],
) -> tuple[_GroupKey, ...]:
    """Expand one block's declared groups against document groups."""
    declared = _groups_for_block(block, settings)
    if any(group.author_name == "*" for group in declared):
        return groups
    return tuple(group for group in declared if group in groups)


def _output_matches(output: ParsedOutput, group: _GroupKey) -> bool:
    """Return whether an expected-output record belongs to ``group``."""
    return "*" in output.groups or (
        group.author_name is not None and group.author_name in output.groups
    )


def _paired_output(
    block: ParsedBlock,
    output_kind: str,
    group: _GroupKey,
    parsed: ParseResult,
    settings: ProjectionSettings,
    groups: tuple[_GroupKey, ...],
    registry: RegistrySnapshot,
) -> ParsedOutput | None:
    """Find the latest output before the next test block in this group."""
    later_blocks = [
        candidate.document_order
        for candidate in parsed.blocks
        if candidate.document_order > block.document_order
        and candidate.kind in registry.block_kinds
        and registry.block_kinds[candidate.kind].value.phase is Phase.TEST
        and group
        in _destinations(
            candidate,
            settings=settings,
            groups=groups,
        )
    ]
    boundary = min(later_blocks, default=2**63 - 1)
    matches = [
        output
        for output in parsed.outputs
        if output.kind == output_kind
        and block.document_order < output.document_order < boundary
        and _output_matches(output, group)
    ]
    return matches[-1] if matches else None


def _prompt_recipes(block: ParsedBlock) -> tuple[ExampleRecipe, ...]:
    """Project through the unmodified standard-library parser."""
    test = doctest.DocTestParser().get_doctest(
        block.source,
        {},
        "<projection>",
        str(block.path),
        0,
    )
    return tuple(
        ExampleRecipe(
            source=example.source,
            want=example.want,
            exc_msg=example.exc_msg,
            lineno=example.lineno,
            indent=example.indent,
            options=_read_only(example.options),
        )
        for example in test.examples
    )


def _exec_recipe(block: ParsedBlock) -> tuple[ExampleRecipe, ...]:
    """Represent one prompt-free body as a stock example recipe."""
    return (
        ExampleRecipe(
            source=block.source,
            want="",
            exc_msg=None,
            lineno=0,
            indent=0,
            options=_read_only({}),
        ),
    )


def _project_block(
    block: ParsedBlock,
    *,
    group: _GroupKey,
    group_label: str,
    document_name: str,
    parsed: ParseResult,
    settings: ProjectionSettings,
    groups: tuple[_GroupKey, ...],
    registry: RegistrySnapshot,
) -> ProjectedBlock:
    """Create a fresh group-qualified recipe for one parsed block."""
    kind = registry.block_kinds[block.kind].value
    output = (
        _paired_output(
            block,
            kind.pairs_with,
            group,
            parsed,
            settings,
            groups,
            registry,
        )
        if kind.pairs_with
        else None
    )
    expected = (
        ExpectedOutput(
            text=output.text,
            options=_read_only(output.options),
            skipif=output.skipif,
            pyversion=output.pyversion,
        )
        if output is not None
        else None
    )
    examples = (
        _prompt_recipes(block) if kind.profile_name == "prompt" else _exec_recipe(block)
    )
    stem = pathlib.PurePath(document_name).stem
    return ProjectedBlock(
        phase=kind.phase,
        name=f"{stem}::{group_label}[{block.block_ordinal}]",
        block_ordinal=block.block_ordinal,
        examples=examples,
        docstring=block.source,
        filename=str(block.path),
        lineno=None if block.line is None else max(block.line - 1, 0),
        options=_read_only(block.options),
        profile_name=kind.profile_name,
        skipif=block.skipif,
        pyversion=block.pyversion,
        expected=expected,
    )


def project(
    parsed: ParseResult,
    *,
    document_name: str,
    settings: ProjectionSettings | None = None,
    registry: RegistrySnapshot | None = None,
    seed: t.Mapping[str, t.Any] | None = None,
) -> tuple[GroupPlan, ...]:
    """Project inert records into one immutable plan per shared-state group.

    Grouping and pairing are pure: no user code, filesystem access, docutils,
    or host lifecycle object crosses this boundary.

    >>> from .model import ParseResult
    >>> project(ParseResult((), (), ()), document_name="empty.rst")
    ()
    """
    if registry is None:
        from .registry import build_registry

        registry = build_registry()
    settings = settings or ProjectionSettings()
    groups = _test_groups(parsed, settings, registry)
    labels = _group_labels(groups)
    by_group: dict[_GroupKey, list[tuple[int, ProjectedBlock]]] = {
        group: [] for group in groups
    }
    for block in parsed.blocks:
        if block.kind not in registry.block_kinds:
            continue
        for group in _destinations(block, settings=settings, groups=groups):
            projected = _project_block(
                block,
                group=group,
                group_label=labels[group],
                document_name=document_name,
                parsed=parsed,
                settings=settings,
                groups=groups,
                registry=registry,
            )
            if projected.phase is Phase.TEST and not projected.examples:
                continue
            by_group[group].append(
                (
                    block.document_order,
                    projected,
                ),
            )

    frozen_seed = _read_only(seed or {})
    return tuple(
        GroupPlan(
            group=labels[group],
            blocks=tuple(
                block
                for _, block in sorted(
                    by_group[group],
                    key=lambda entry: (entry[1].phase, entry[0]),
                )
            ),
            seed=frozen_seed,
        )
        for group in groups
        if any(block.phase is Phase.TEST for _, block in by_group[group])
    )
