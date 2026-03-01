"""Conftest.py (root-level).

We keep this in root pytest fixtures in pytest's doctest plugin to be available, as well
as avoiding conftest.py from being included in the wheel, in addition to pytest_plugin
for pytester only being available via the root directory.

See "pytest_plugins in non-top-level conftest files" in
https://docs.pytest.org/en/stable/deprecations.html
"""

from __future__ import annotations

import asyncio
import pathlib
import typing as t

import pytest

if t.TYPE_CHECKING:
    from collections.abc import Callable

pytest_plugins = ["sphinx.testing.fixtures", "pytester"]

AppParams = tuple[t.Any, dict[str, t.Any]]


class MakeAppParams(t.Protocol):
    """Typing protocol for sphinx make_app_params."""

    def __call__(
        self,
        #: index content
        index: t.IO[str] | str | None = ...,
        *args: object,
        **kwargs: t.Any,
    ) -> AppParams:
        """Create Sphinx App factory with params."""
        ...


@pytest.fixture
def make_app_params(
    request: pytest.FixtureRequest,
    app_params: AppParams,
    tmp_path: pathlib.Path,
) -> Callable[[t.Any], AppParams]:
    """Return Sphinx App factory, accepts custom params."""

    def fn(
        #: index content
        index: t.IO[str] | str | None = None,
        *args: object,
        **kwargs: t.Any,
    ) -> AppParams:
        args, kws = app_params
        kws.setdefault("confoverrides", {})
        kws.setdefault("buildername", "html")
        kws.setdefault("status", None)
        kws.setdefault("warning", None)
        kws.setdefault("freshenv", True)
        kws["srcdir"] = pathlib.Path(tmp_path)

        for k, v in kwargs.items():
            if k == "confoverrides":
                assert isinstance(v, dict)
                if "extensions" not in v:
                    v["extensions"] = []
                if "html_theme" not in v:
                    v["html_theme"] = "epub"
                if "html_theme_options" not in v:
                    v["html_theme_options"] = {"footer": False, "relbar1": False}

                kws["confoverrides"].update(**v)

        conf_file = kws["srcdir"] / "conf.py"
        conf_file.write_text("", encoding="utf8")
        if index is not None:
            index_file = kws["srcdir"] / "index.rst"
            index_file.write_text(index, encoding="utf8")

        return args, kws

    return fn


@pytest.fixture(autouse=True)
def doctest_namespace(doctest_namespace: dict[str, t.Any]) -> dict[str, t.Any]:
    """Inject common fixtures into doctest namespace.

    Provides:
    - asyncio: The asyncio module for async doctests
    """
    doctest_namespace["asyncio"] = asyncio
    return doctest_namespace
