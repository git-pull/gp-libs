"""Sphinx configuration for gp_libs."""

from __future__ import annotations

import pathlib
import sys

from gp_sphinx.config import make_linkcode_resolve, merge_sphinx_config

import gp_libs

# Get the project root dir, which is the parent dir of this
cwd = pathlib.Path(__file__).parent
project_root = cwd.parent

sys.path.insert(0, str(project_root))

# package data
about: dict[str, str] = {}
with (project_root / "src" / "gp_libs.py").open() as fp:
    exec(fp.read(), about)

conf = merge_sphinx_config(
    project=about["__title__"],
    version=about["__version__"],
    copyright=about["__copyright__"],
    source_repository=f"{about['__github__']}/",
    docs_url=about["__docs__"],
    source_branch="master",
    light_logo="img/icons/logo.svg",
    dark_logo="img/icons/logo-dark.svg",
    intersphinx_mapping={
        "py": ("https://docs.python.org/", None),
        "pytest": ("https://docs.pytest.org/en/stable/", None),
        "sphinx": ("https://www.sphinx-doc.org/en/master/", None),
    },
    linkcode_resolve=make_linkcode_resolve(gp_libs, about["__github__"], src_dir=""),
    html_favicon="_static/img/icons/favicon.ico",
    html_extra_path=["manifest.json"],
    rediraffe_redirects="redirects.txt",
)
globals().update(conf)
