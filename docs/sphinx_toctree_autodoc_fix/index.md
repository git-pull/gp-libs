(sphinx_toctree_autodoc_fix)=
(sphinx-toctree-signature)=

# ToC + `sphinx.ext.autodoc` fixer

Table of Contents won't generate for `sphinx.ext.autodoc`, see
[sphinx#6316]. This has been an open issue since April 22nd, 2019.

[sphinx#6316]: https://github.com/sphinx-doc/sphinx/issues/6316

## Configuration

In your _conf.py_:

1. Add `'sphinx_toctree_autodoc_fix'` to `extensions`

   ```python
   extensions = [
       # ...
       "sphinx_toctree_autodoc_fix",
   ]
   ```

## API

```{eval-rst}
.. automodule:: sphinx_toctree_autodoc_fix
   :members:
   :show-inheritance:
   :undoc-members:
```
