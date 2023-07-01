import pathlib
import typing as t

import pytest
from sphinx.testing.util import SphinxTestApp

if t.TYPE_CHECKING:
    from .conftest import MakeAppParams


class LinkTestFixture(t.NamedTuple):
    # pytest
    test_id: str

    # Extension configuration
    issue_url_tpl: str

    # Content
    text: str
    issue_id: str  # For assertions


FIXTURES = [
    LinkTestFixture(
        test_id="Plain issue",
        issue_url_tpl="https://github.com/org/repo/issues/{issue_id}",
        text="#10",
        issue_id="10",
    ),
    LinkTestFixture(
        test_id="Text preceding issue",
        issue_url_tpl="https://github.com/org/repo/issues/{issue_id}",
        text="Test #11.",
        issue_id="11",
    ),
]


@pytest.mark.parametrize(
    LinkTestFixture._fields, FIXTURES, ids=[f.test_id for f in FIXTURES]
)
def test_links_show(
    make_app: t.Callable[[t.Any], SphinxTestApp],
    make_app_params: "MakeAppParams",
    test_id: str,
    issue_url_tpl: str,
    text: str,
    issue_id: str,
) -> None:
    args, kwargs = make_app_params(
        index=text,
        confoverrides={"issue_url_tpl": issue_url_tpl, "extensions": "linkify_issues"},
    )
    app = make_app(*args, **kwargs)
    app.build()

    content = (pathlib.Path(app.outdir) / "index.html").read_text(encoding="utf8")
    assert issue_url_tpl.format(issue_id=issue_id) in content
