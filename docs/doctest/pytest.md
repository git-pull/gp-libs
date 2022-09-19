(pytest_plugin)=
(pytest_doctest_docutils)=

# pytest plugin

:::{note}

This plugin disables {ref}`pytest's standard doctest plugin <pytest:doctest>`.

:::

The pytest plugin is built on top of the {ref}`doctest_docutils` module, which is in
turn compatible with {mod}`doctest`.

## Using fixtures

Normal pytest convention apply, {ref}`a visible conftest.py must be available <pytest:using-fixtures>`
for the file being tested.

This requires a understanding of `confest.py` - in the same way {ref}`pytest's vanilla doctest plugin <pytest:doctest>` does.

You know your project's package structure best, the follow just serve as examples of new places conftest.py will be needed:

### Example: Root-level `README`

In other words, if you want to test a project's `README.md` in the project root, a `conftest.py` would be needed at the root-level. This also has the benefit of reducing duplication:

    conftest.py
        # content of conftest.py
        import pytest

        @pytest.fixture
        def username():
            return 'username'

    README.rst
        Our project
        -----------

        .. doctest::

            # content of tests/test_something.py
            def test_username(username):
                assert username == 'username'

Now you can do:

```console
$ pytest README.rst
```

### Examples: `docs/`

Let's assume `.md` and `.rst` files in `docs/`, this means you need to import `conftest.py`

    docs/
    	conftest.py
    		# import conftest of project
    		import pytest

    		@pytest.fixture
    		def username():
    			return 'username'

    	usage.rst
    		Our project
    		-----------

    		.. doctest::

    			# content of tests/test_something.py
    			def test_username(username):
    				assert username == 'username'

Now you can do:

```console
$ pytest docs/
```

## File support

### reStructuredText (`.rst`)

```console
$ pytest README.rst
```

```console
$ pytest docs/
```

### Markdown (`.md`)

If you install [myst-parser], doctest will run on .md files.

```console
$ pytest README.md
```

```console
$ pytest docs/
```

[myst-parser]: https://myst-parser.readthedocs.io/en/latest/

## Scanning python files

You can retain {ref}`pytest's standard doctest plugin <pytest:doctest>` of
running doctests in `.py` by passing `--doctest-docutils-modules`:

```console
$ py.test src/ --doctest-docutils-modules
```

You can disable it via `--no-doctest-docutils-modules`:

```console
$ py.test src/ --no-doctest-docutils-modules
```

## Case examples

- [libtmux] ([source](https://github.com/tmux-python/libtmux/tree/v0.15.0post0)):

  - Documentation w/ docutils:

    - [README.md](https://github.com/tmux-python/libtmux/blob/v0.15.0post0/README.md) ([raw](https://github.com/tmux-python/libtmux/raw/v0.15.0post0/README.md))

      _Note: `pytest README.md` requires you have a `conftest.py` directly in the project root_

    - [docs/topics/traversal.md](https://github.com/tmux-python/libtmux/blob/v0.15.0post0/docs/topics/traversal.md) ([raw](https://github.com/tmux-python/libtmux/raw/v0.15.0post0/docs/topics/traversal.md))

  - Configuration:

    - Doctests support pytest fixtures through [`doctest_namespace`](https://docs.pytest.org/en/7.1.x/how-to/doctest.html#doctest-namespace-fixture)

      See [`add_doctest_fixtures()`](https://github.com/tmux-python/libtmux/blob/v0.15.0post0/src/libtmux/conftest.py#L15-L26) in [`src/libtmux/conftest.py`](https://github.com/tmux-python/libtmux/blob/v0.15.0post0/src/libtmux/conftest.py)

[libtmux]: https://libtmux.git-pull.com/

## API

```{eval-rst}
.. automodule:: pytest_doctest_docutils
   :members:
   :show-inheritance:
   :undoc-members:
```
