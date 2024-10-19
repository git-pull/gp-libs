"""Conftest.py (root-level).

We keep this in root pytest fixtures in pytest's doctest plugin to be available, as well
as avoiding conftest.py from being included in the wheel, in addition to pytest_plugin
for pytester only being available via the root directory.

See "pytest_plugins in non-top-level conftest files" in
https://docs.pytest.org/en/stable/deprecations.html
"""

import pathlib
import typing as t

import pytest
from sphinx.testing.path import path as sphinx_path

pytest_plugins = ["sphinx.testing.fixtures", "pytester"]

AppParams = t.Tuple[t.Any, t.Dict[str, t.Any]]


class MakeAppParams(t.Protocol):
    """Typing protocol for sphinx make_app_params."""

    def __call__(
        self,
        #: index content
        index: t.Optional[t.Union[t.IO[str], str]] = ...,
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
) -> t.Callable[[t.Any], AppParams]:
    """Return Sphinx App factory, accepts custom params."""

    def fn(
        #: index content
        index: t.Optional[t.Union[t.IO[str], str]] = None,
        *args: object,
        **kwargs: t.Any,
    ) -> AppParams:
        args, kws = app_params
        kws.setdefault("confoverrides", {})
        kws.setdefault("buildername", "html")
        kws.setdefault("status", None)
        kws.setdefault("warning", None)
        kws.setdefault("freshenv", True)
        kws["srcdir"] = sphinx_path(tmp_path)

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

        (kws["srcdir"] / "conf.py").write_text("", encoding="utf8")
        if index is not None:
            (kws["srcdir"] / "index.rst").write_text(index, encoding="utf8")

        return args, kws

    return fn
