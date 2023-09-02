(quickstart)=

# Quickstart

## Installation

For latest official version:

```console
$ pip install --user gp-libs
```

Upgrading:

```console
$ pip install --user --upgrade gplibs
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

via trunk (can break easily):

- [pip]\:

  ```console
  $ pip install --user -e git+https://github.com/git-pull/gp-libs.git#egg=gp-libs
  ```

[pip]: https://pip.pypa.io/en/stable/
