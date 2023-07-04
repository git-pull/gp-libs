import pathlib
import sys
import typing as t

import pytest
from sphinx.testing.path import path as sphinx_path

pytest_plugins = ["sphinx.testing.fixtures", "pytester"]

AppParams = t.Tuple[t.Any, t.Dict[str, t.Any]]

if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    from typing_extensions import Protocol


class MakeAppParams(Protocol):
    def __call__(
        self,
        #: index content
        index: t.Optional[t.Union[t.IO[str], str]] = ...,
        *args: object,
        **kwargs: t.Any,
    ) -> AppParams:
        ...


@pytest.fixture(scope="function")
def make_app_params(
    request: pytest.FixtureRequest,
    app_params: AppParams,
    tmp_path: pathlib.Path,
) -> t.Generator[t.Callable[[t.Any], AppParams], None, None]:
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

    yield fn
