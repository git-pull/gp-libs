"""Deterministic construction of immutable doctest-core registries."""

from __future__ import annotations

import doctest
import re
import types
import typing as t

from .contracts import (
    CheckerFactory,
    Contributor,
    DocumentParser,
    ExecutionProfile,
    Provider,
    Registrar,
    Registration,
)
from .model import BlockKind, Phase


class RegistryError(ValueError):
    """Base error for invalid registry construction."""


class RegistryClosedError(RegistryError):
    """Raised when a retained registrar is used after registry freeze."""


class RegistryCollisionError(RegistryError):
    """Raised when a registration would implicitly replace another."""


class RegistrySnapshot(t.NamedTuple):
    """Read-only capability set consumed by pipeline stages.

    Attributes
    ----------
    block_kinds : mapping of str to Registration[BlockKind]
        Projection policies in declaration order.
    document_parsers : mapping of str to Registration[DocumentParser]
        Markup parsers in declaration order.
    execution_profiles : mapping of str to Registration[ExecutionProfile]
        Runtime factories in declaration order.
    output_checkers : mapping of str to Registration[CheckerFactory]
        Checker factories in declaration order.
    """

    block_kinds: t.Mapping[str, Registration[BlockKind]]
    document_parsers: t.Mapping[str, Registration[DocumentParser]]
    execution_profiles: t.Mapping[str, Registration[ExecutionProfile]]
    output_checkers: t.Mapping[str, Registration[CheckerFactory]]


_NAME_PATTERN = re.compile(r"[a-z][a-z0-9_.-]*\Z", flags=re.ASCII)
_BUILTIN_PROVIDER = Provider(name="builtin", version=None)
U = t.TypeVar("U")


def _read_only(
    entries: dict[str, Registration[U]],
) -> t.Mapping[str, Registration[U]]:
    return types.MappingProxyType(dict(entries))


class _RegistryBuilder:
    def __init__(self) -> None:
        self.block_kinds: dict[str, Registration[BlockKind]] = {}
        self.document_parsers: dict[str, Registration[DocumentParser]] = {}
        self.execution_profiles: dict[str, Registration[ExecutionProfile]] = {}
        self.output_checkers: dict[str, Registration[CheckerFactory]] = {}
        self.closed = False

    def registrar(self, provider: Provider) -> _BoundRegistrar:
        self._require_open()
        return _BoundRegistrar(self, provider)

    def close(self) -> None:
        self.closed = True

    def freeze(self) -> RegistrySnapshot:
        self._require_open()
        self._validate_references()
        self.close()
        return RegistrySnapshot(
            block_kinds=_read_only(self.block_kinds),
            document_parsers=_read_only(self.document_parsers),
            execution_profiles=_read_only(self.execution_profiles),
            output_checkers=_read_only(self.output_checkers),
        )

    def _validate_references(self) -> None:
        """Reject block policies that cannot resolve unambiguously."""
        for name, registration in self.block_kinds.items():
            kind = registration.value
            if kind.profile_name not in self.execution_profiles:
                message = (
                    f"block kind {name!r} from provider "
                    f"{registration.provider.name!r} references missing execution "
                    f"profile {kind.profile_name!r}"
                )
                raise RegistryError(message)
            if kind.pairs_with is None:
                continue
            self._validate_name(kind.pairs_with)
            output_collision = self.block_kinds.get(kind.pairs_with)
            if output_collision is not None:
                message = (
                    f"block kind {name!r} from provider "
                    f"{registration.provider.name!r} pairs with {kind.pairs_with!r}, "
                    "which is also a runnable block kind from provider "
                    f"{output_collision.provider.name!r}"
                )
                raise RegistryCollisionError(message)

    def add(
        self,
        category: str,
        entries: dict[str, Registration[U]],
        name: str,
        value: U,
        provider: Provider,
        *,
        replace: bool,
    ) -> None:
        self._require_open()
        self._validate_name(name)
        incumbent = entries.get(name)
        if incumbent is not None and not replace:
            msg = (
                f"{category} {name!r} from provider "
                f"{incumbent.provider.name!r} already exists; provider "
                f"{provider.name!r} must pass replace=True"
            )
            raise RegistryCollisionError(msg)
        entries[name] = Registration(name, value, provider)

    def add_document_parser(
        self,
        name: str,
        parser: DocumentParser,
        provider: Provider,
        *,
        replace: bool,
    ) -> None:
        self._require_open()
        self._validate_name(name)
        for incumbent_name, incumbent in self.document_parsers.items():
            if incumbent_name == name:
                continue
            overlap = parser.suffixes & incumbent.value.suffixes
            if overlap:
                suffixes = ", ".join(sorted(overlap))
                msg = (
                    f"document parser {name!r} from provider "
                    f"{provider.name!r} overlaps {incumbent_name!r} from "
                    f"provider {incumbent.provider.name!r} for {suffixes}"
                )
                raise RegistryCollisionError(msg)
        self.add(
            "document parser",
            self.document_parsers,
            name,
            parser,
            provider,
            replace=replace,
        )

    def _require_open(self) -> None:
        if self.closed:
            msg = "registry registration is closed"
            raise RegistryClosedError(msg)

    @staticmethod
    def _validate_name(name: str) -> None:
        if _NAME_PATTERN.fullmatch(name) is None:
            msg = f"invalid registry name {name!r}; expected [a-z][a-z0-9_.-]*"
            raise RegistryError(msg)


class _BoundRegistrar:
    def __init__(self, builder: _RegistryBuilder, provider: Provider) -> None:
        self._builder = builder
        self._provider = provider

    def add_block_kind(
        self,
        name: str,
        kind: BlockKind,
        *,
        replace: bool = False,
    ) -> None:
        self._builder.add(
            "block kind",
            self._builder.block_kinds,
            name,
            kind,
            self._provider,
            replace=replace,
        )

    def add_document_parser(
        self,
        name: str,
        parser: DocumentParser,
        *,
        replace: bool = False,
    ) -> None:
        self._builder.add_document_parser(
            name,
            parser,
            self._provider,
            replace=replace,
        )

    def add_execution_profile(
        self,
        name: str,
        profile: ExecutionProfile,
        *,
        replace: bool = False,
    ) -> None:
        self._builder.add(
            "execution profile",
            self._builder.execution_profiles,
            name,
            profile,
            self._provider,
            replace=replace,
        )

    def add_output_checker(
        self,
        name: str,
        factory: CheckerFactory,
        *,
        replace: bool = False,
    ) -> None:
        self._builder.add(
            "output checker",
            self._builder.output_checkers,
            name,
            factory,
            self._provider,
            replace=replace,
        )


def _register_builtins(registrar: Registrar) -> None:
    # Import implementations only while constructing a registry. This keeps the
    # foundational contracts independent of parsing and execution modules.
    from .markup import MystDocumentParser, RstDocumentParser
    from .runner import ExecExecutionProfile, PromptExecutionProfile

    registrar.add_block_kind(
        "doctest",
        BlockKind(Phase.TEST, "prompt", None),
    )
    registrar.add_block_kind(
        "testsetup",
        BlockKind(Phase.SETUP, "exec", None),
    )
    registrar.add_block_kind(
        "testcleanup",
        BlockKind(Phase.CLEANUP, "exec", None),
    )
    registrar.add_block_kind(
        "testcode",
        BlockKind(Phase.TEST, "exec", "testoutput"),
    )
    registrar.add_document_parser("rst", RstDocumentParser())
    registrar.add_document_parser("myst", MystDocumentParser())
    registrar.add_execution_profile("prompt", PromptExecutionProfile())
    registrar.add_execution_profile("exec", ExecExecutionProfile())
    registrar.add_output_checker("stdlib", doctest.OutputChecker)


def build_registry(
    contributors: t.Iterable[Contributor] = (),
) -> RegistrySnapshot:
    """Build and freeze a deterministic capability snapshot.

    Built-ins retain their declaration order and contributors are applied once
    in the order supplied by the host.

    Parameters
    ----------
    contributors : iterable of Contributor
        Explicit host-discovered contributions.

    Returns
    -------
    RegistrySnapshot
        Immutable registry mappings and attributed records.

    Raises
    ------
    RegistryCollisionError
        If a contribution replaces a capability without explicit permission.

    Examples
    --------
    >>> tuple(build_registry().output_checkers)
    ('stdlib',)
    """
    builder = _RegistryBuilder()
    try:
        _register_builtins(builder.registrar(_BUILTIN_PROVIDER))
        for contributor in contributors:
            contributor.contribute(builder.registrar(contributor.provider))
        return builder.freeze()
    finally:
        builder.close()
