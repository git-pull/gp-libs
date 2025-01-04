"""Helpers for cross compatibility across dependency versions."""

from __future__ import annotations

import typing as t

if t.TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from docutils.nodes import Node

    _N = t.TypeVar("_N", bound=Node)


def findall(node: type[_N]) -> Callable[..., Iterable[_N]]:
    """Iterate through nodes.

    nodes.findall() replaces traverse in docutils v0.18.
    findall is an iterator.

    Based on myst_parser v0.18.1's:
    https://github.com/executablebooks/MyST-Parser/blob/v0.18.1/myst_parser/_compat.py
    """
    return getattr(node, "findall", node.traverse)
