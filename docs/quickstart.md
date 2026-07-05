(quickstart)=

# Quickstart

## Installation

Install the latest official release:

```console
$ pip install --user gp-libs
```

Upgrade an existing install:

```console
$ pip install --user --upgrade gp-libs
```

(developmental-releases)=

### Developmental releases

New versions of gp-libs are published to [PyPI] as alpha, beta, or release
candidates.
Their versions include markers such as `a1`, `b1`, and `rc1`, respectively.
`1.10.0b4` means the fourth beta release of `1.10.0` before general
availability.

- [pip]\:

  ```console
  $ pip install --user --upgrade --pre gp-libs
  ```

- [pipx]\:

  ```console
  $ pipx install --suffix=@next 'gp-libs' --pip-args '\--pre' --force
  ```

- [uv]\:

  ```console
  $ uv add gp-libs --prerelease allow
  ```

- [uvx]\:

  ```console
  $ uvx --from 'gp-libs' --prerelease allow gp-libs
  ```

Install from trunk when you need unreleased work. These installs can break:

- [pip]\:

  ```console
  $ pip install --user -e git+https://github.com/git-pull/gp-libs.git#egg=gp-libs
  ```

- [pipx]\:

  ```console
  $ pipx install --suffix=@master 'gp-libs @ git+https://github.com/git-pull/gp-libs.git@master' --force
  ```

- [uv]\:

  ```console
  $ uv add gp-libs --from git+https://github.com/git-pull/gp-libs.git
  ```

[pip]: https://pip.pypa.io/en/stable/
[pipx]: https://pypa.github.io/pipx/docs/
[PyPI]: https://pypi.org/
[uv]: https://docs.astral.sh/uv/
[uvx]: https://docs.astral.sh/uv/guides/tools/
