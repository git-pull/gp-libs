# Contributing

Install [git], [uv], and [just].

Clone:

```console
$ git clone https://github.com/git-pull/gp-libs.git
```

```console
$ cd gp-libs
```

Install packages:

```console
$ uv sync --all-extras --dev
```

## Tests

```console
$ just test
```

### Automatically run tests on file save

Use [pytest-watcher]:

```console
$ just start
```

Use [entr(1)] when you want a shell-only watcher:

```console
$ just watch-test
```

[pytest-watcher]: https://github.com/olzhasar/pytest-watcher

## Documentation

Build the docs:

```console
$ just build-docs
```

Start the default preview server:

```console
$ just start-docs
```

[sphinx-autobuild] builds the docs, watches for file changes, and launches the
preview server.

From inside `docs/`, run the local docs justfile directly:

```console
$ just start
```

[sphinx-autobuild]: https://github.com/executablebooks/sphinx-autobuild

### Manual documentation

Build from inside `docs/`:

```console
$ just html
```

Serve the built HTML:

```console
$ just serve
```

Watch and rebuild on file changes:

```console
$ just watch
```

Watch and serve in one terminal:

```console
$ just dev
```

[git]: https://git-scm.com/
[uv]: https://github.com/astral-sh/uv
[just]: https://just.systems/
[entr(1)]: http://eradman.com/entrproject/
