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

## Autouse fixtures

Autouse fixtures in a visible `conftest.py` are parsed for `.rst` and `.md`
doctest files. Use them for setup that should happen before every example, and
keep the example itself self-contained for the reader.
