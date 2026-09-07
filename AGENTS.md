Use repository quality checks appropriate to the requested changes.

## App version policy

- The baseline when this policy was introduced was `0.1.0`. Future increments start from the current version declarations, not from this historical baseline.
- For every future app change (bug fix, feature, or behavior/UI change), increment the app version before considering the change complete, unless the user explicitly asks to keep it unchanged.
- Increment once per completed logical change set, not per file edit or intermediate test/build attempt. Documentation-only changes do not require a version bump.
- Use a patch increment for fixes and small improvements, a minor increment for substantial new features, and a major increment for breaking releases. Reset lower components when incrementing a higher component.
- Keep all version declarations synchronized in the same change:
  - `pyproject.toml`: `[project].version`
  - `qfield_builder/__init__.py`: `__version__`
  - `packaging/qfield_builder.spec`: `APP_VERSION`
- Verify that these three values match and report the old and new versions in the completion summary. Any distributed build must be built from the updated version declarations.
- A version bump does not itself authorize a commit, push, tag, or GitHub release; perform those only when requested.
