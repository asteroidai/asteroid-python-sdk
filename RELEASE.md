# Release Instructions

Follow these steps to release a new version of the package:

1. **Update the Version Number**
   - Modify the version number in `pyproject.toml` file according to semantic versioning (e.g., `1.0.1`).

2. **[Optional] Run Tests**
   - Ensure all tests pass
   ```bash
   pytest
   ```

3. **Build the Package**
   - Create the distribution packages (source and wheel).
   ```bash
   python -m build
   ```

4. **[Optional] Tag the Release in Git**
   - Create a git tag for the release to track the version in the repository.
   ```bash
   git tag -a v1.0.1 -m "Release version 1.0.1"
   git push origin v1.0.1
   ```

5. **[Optional] Push Changes to Remote**
   - Push your changes and tags to the remote repository.
   ```bash
   git push origin main
   ```

6. **Upload to PyPI**
   - Use `twine` to upload the package to PyPI.
   ```bash
   python -m twine upload dist/* --verbose
   ```

7. **[Optional] Create a GitHub Release**
   - Create a release with the tag and include release notes.


