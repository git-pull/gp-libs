# Releasing

## Version policy

gp-libs is pre-1.0. Minor version bumps may include breaking changes.

## Release process

[uv] handles virtualenv creation, package requirements, versioning,
building, and publishing. There is no `setup.py` or requirements file.

1. Update `CHANGES` with release notes.

2. Bump version in `src/gp_libs.py` and `pyproject.toml`.

3. Create the release commit:

   ```console
   $ git commit -m 'Tag v0.1.1'
   ```

4. Push the branch for review:

   ```console
   $ git push
   ```

5. After review, the release owner creates and pushes the `v0.1.1` tag. Tags
   trigger the publish workflow.

[uv]: https://github.com/astral-sh/uv
