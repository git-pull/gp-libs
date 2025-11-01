(quickstart)=

# Quickstart

## Installation

For latest official version:

```console
$ pip install --user gp-libs
```

Upgrading:

```console
$ pip install --user --upgrade gp-libs
```

(developmental-releases)=

### Developmental releases

New versions of gp-libs are published to PyPI as alpha, beta, or release candidates.
In their versions you will see notification like `a1`, `b1`, and `rc1`, respectively.
`1.10.0b4` would mean the 4th beta release of `1.10.0` before general availability.

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

via trunk (can break easily):

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
[uv]: https://docs.astral.sh/uv/
[uvx]: https://docs.astral.sh/uv/guides/tools/
