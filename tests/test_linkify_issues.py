import pathlib
import typing as t

import pytest

from sphinx.testing.util import SphinxTestApp

if t.TYPE_CHECKING:
    from .conftest import MakeAppParams


class LinkTestFixture(t.NamedTuple):
    issue_url_tpl: str
    text: str
    issue_id: str


@pytest.mark.parametrize(
    LinkTestFixture._fields,
    [
        LinkTestFixture(
            issue_url_tpl="https://github.com/org/repo/issues/{issue_id}",
            text="#10",
            issue_id="10",
        ),
        LinkTestFixture(
            issue_url_tpl="https://github.com/org/repo/issues/{issue_id}",
            text="Test #11.",
            issue_id="11",
        ),
    ],
)
def test_links_show(
    make_app: t.Callable[[t.Any], SphinxTestApp],
    make_linkify_issues_test_app_params: "MakeAppParams",
    issue_url_tpl: str,
    text: str,
    issue_id: str,
) -> None:
    args, kwargs = make_linkify_issues_test_app_params(
        index=text,
        confoverrides={"issue_url_tpl": issue_url_tpl},
    )
    app = make_app(*args, **kwargs)
    app.build()

    content = (pathlib.Path(app.outdir) / "index.html").read_text(encoding="utf8")
    assert issue_url_tpl.format(issue_id=issue_id) in content
