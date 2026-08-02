(pytest_doctest_docutils-fixtures)=

# Fixtures

Documentation doctests do not receive ordinary named fixtures as direct
function arguments. Share values through {ref}`doctest_namespace
<pytest:doctest_namespace>` or through autouse fixtures in a visible
`conftest.py`.

## doctest_namespace

Add objects to `doctest_namespace` from a fixture:

```python
import pytest


@pytest.fixture
def add_helpers(doctest_namespace):
    def add(left, right):
        return left + right

    doctest_namespace["add"] = add
```

Then the documentation page can use the helper by name:

```python
add(2, 3)
```

A helper like this one holds nothing, so how long it lives never comes up.
Seeding a *resource* — a server, a connection, a temporary directory — is where
it does, because the fixture's scope decides how long the object a page saved
stays usable. See {ref}`what per-block items cost
<pytest_doctest_docutils-per-block-costs>` before carrying one across several
blocks of a page.

## Autouse fixtures

Autouse fixtures in a visible `conftest.py` are parsed for `.rst` and `.md`
doctest files. Use them for setup that should happen before every example, and
keep the example itself self-contained for the reader.
