(doctest_docutils-how-to)=

# How-to

## Run a Markdown file

Use the module command with the file path:

```console
$ python -m doctest_docutils README.md
```

## Run a reStructuredText file

Use the same command for `.rst` files:

```console
$ python -m doctest_docutils README.rst
```

## See collected examples

Pass `-v` for verbose standard-library doctest output:

```console
$ python -m doctest_docutils README.md -v
```

## Compare with stdlib doctest

Use the stdlib command when you are checking Python modules or plain text that
does not need docutils parsing:

```console
$ python -m doctest --help
```

Use {mod}`doctest_docutils` when the examples live inside Markdown or
reStructuredText structure that {mod}`doctest` would otherwise treat as plain
text.
