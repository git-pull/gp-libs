"""Autolinking extension for Sphinx."""

from __future__ import annotations

import re
import typing as t

from docutils import nodes
from sphinx.transforms import SphinxTransform

from docutils_compat import findall

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx

DEFAULT_ISSUE_RE = r"#(?P<issue_id>\d+)"
"""Default pattern to search plain nodes for issues."""


class LinkifyIssues(SphinxTransform):
    """Autolink references for Sphinx."""

    default_priority = 999

    def apply(self) -> None:
        """Apply Sphinx transform."""
        config = self.document.settings.env.config
        issue_re: re.Pattern[str] = (
            re.compile(config.issue_re)
            if isinstance(config.issue_re, str)
            else config.issue_re
        )

        assert issue_re.groups == 1

        def condition(node: nodes.Node) -> bool:
            return (
                isinstance(node, nodes.Text)
                and len(re.findall(issue_re, node.astext())) > 0
            ) and not isinstance(
                node.parent,
                (nodes.literal, nodes.FixedTextElement, nodes.reference),
            )

        for node in findall(self.document)(condition):
            text = node.astext()
            retnodes: list[nodes.reference | nodes.Text] = []
            pos = 0
            for match in issue_re.finditer(text):
                if match.start() > pos:
                    txt = text[pos : match.start()]
                    retnodes.append(nodes.Text(txt))

                refnode = nodes.reference(
                    refuri=f"{config.issue_url_tpl}".format(**match.groupdict()),
                    internal=False,
                    classes=["issue"],
                )
                refnode += nodes.inline(match.group(0), match.group(0))
                retnodes.append(refnode)
                pos = match.end()

            if pos < len(text):
                retnodes.append(nodes.Text(text[pos:]))

            node.parent.replace(node, retnodes)


class SetupDict(t.TypedDict):
    """Setup mapping for Sphinx app."""

    version: str
    parallel_read_safe: bool
    parallel_write_safe: bool


def setup(app: Sphinx) -> SetupDict:
    """Initialize Sphinx extension for linkify_issues."""
    app.add_transform(LinkifyIssues)
    app.add_config_value("issue_re", re.compile(DEFAULT_ISSUE_RE), "env")
    app.add_config_value(
        "issue_url_tpl",
        r"https://github.com/git-pull/gp-libs/issues/{issue_id}",
        "env",
    )

    return SetupDict(
        {
            "version": "0.1",
            "parallel_read_safe": True,
            "parallel_write_safe": True,
        },
    )
