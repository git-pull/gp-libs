"""Tests for the doctest core registry."""

from __future__ import annotations

import doctest
import typing as t

import pytest

from doctest_core import (
    BlockKind,
    Phase,
    Provider,
    RegistryClosedError,
    RegistryCollisionError,
    RegistryError,
    build_registry,
)


class RecordingContributor:
    """Register one checker and retain the registrar for the freeze test."""

    provider = Provider(name="tests", version="1")

    def __init__(self, *, replace: bool = False) -> None:
        self.registrar: t.Any = None
        self.replace = replace

    def contribute(self, registrar: t.Any) -> None:
        """Register a checker factory.

        >>> contributor = RecordingContributor()
        >>> contributor.provider.name
        'tests'
        """
        self.registrar = registrar
        registrar.add_output_checker(
            "stdlib",
            doctest.OutputChecker,
            replace=self.replace,
        )


def test_registry_snapshot_is_ordered_and_immutable() -> None:
    """Built-ins freeze in declaration order behind read-only mappings."""
    snapshot = build_registry()

    assert tuple(snapshot.block_kinds) == (
        "doctest",
        "testsetup",
        "testcleanup",
        "testcode",
    )
    assert tuple(snapshot.document_parsers) == ("rst", "myst")
    assert tuple(snapshot.execution_profiles) == ("prompt", "exec")
    assert tuple(snapshot.output_checkers) == ("stdlib",)

    with pytest.raises(TypeError):
        snapshot.output_checkers["other"] = snapshot.output_checkers["stdlib"]  # type: ignore[index]


def test_registry_rejects_implicit_collision() -> None:
    """A contributor cannot silently replace another provider's capability."""
    with pytest.raises(RegistryCollisionError, match=r"stdlib.*builtin.*tests"):
        build_registry([RecordingContributor()])


def test_registry_explicit_replacement_preserves_position() -> None:
    """An explicit replacement retains the incumbent's precedence."""
    contributor = RecordingContributor(replace=True)

    snapshot = build_registry([contributor])

    assert tuple(snapshot.output_checkers) == ("stdlib",)
    assert snapshot.output_checkers["stdlib"].provider == contributor.provider


def test_registry_retained_registrar_closes_after_freeze() -> None:
    """A retained registrar cannot mutate a frozen snapshot."""
    contributor = RecordingContributor(replace=True)
    build_registry([contributor])

    with pytest.raises(RegistryClosedError):
        contributor.registrar.add_output_checker("late", doctest.OutputChecker)


def test_registry_rejects_missing_execution_profile_reference() -> None:
    """A frozen block kind cannot defer a missing-profile KeyError to runtime."""

    class Contributor:
        provider = Provider("broken", "1")

        def contribute(self, registrar: t.Any) -> None:
            """Register a block kind with no executable profile."""
            registrar.add_block_kind(
                "example",
                BlockKind(Phase.TEST, "missing", None),
            )

    with pytest.raises(RegistryError, match=r"example.*broken.*missing"):
        build_registry([Contributor()])


def test_registry_rejects_runnable_output_kind_collision() -> None:
    """One node stamp cannot be both executable and expected output."""

    class Contributor:
        provider = Provider("ambiguous", "1")

        def contribute(self, registrar: t.Any) -> None:
            """Register contradictory executable and output roles."""
            registrar.add_block_kind(
                "example",
                BlockKind(Phase.TEST, "exec", "expected"),
            )
            registrar.add_block_kind(
                "expected",
                BlockKind(Phase.TEST, "exec", None),
            )

    with pytest.raises(
        RegistryCollisionError,
        match=r"example.*ambiguous.*expected.*ambiguous",
    ):
        build_registry([Contributor()])


@pytest.mark.parametrize("output_kind", ["", "Expected", "bad name"])
def test_registry_rejects_invalid_output_kind_reference(output_kind: str) -> None:
    """Cross-references obey the same name grammar as registrations."""

    class Contributor:
        provider = Provider("broken", "1")

        def contribute(self, registrar: t.Any) -> None:
            """Register a block kind with a malformed output reference."""
            registrar.add_block_kind(
                "example",
                BlockKind(Phase.TEST, "exec", output_kind),
            )

    with pytest.raises(RegistryError, match=r"invalid registry name"):
        build_registry([Contributor()])
