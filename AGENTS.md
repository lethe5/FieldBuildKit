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

## QField runtime verification

- For changes affecting generated projects, the agent must open newly generated projects in
  `/Applications/qfield.app` on macOS and exercise the affected forms, edits, save/reopen,
  project plugin and relevant layers. On Windows use the installed QField desktop application.
- Do not delegate routine manual testing to the user or mark static XML/unit checks as a QField
  runtime pass. Record the QField version, scenarios exercised, evidence and any concrete blocker.
  Desktop verification does not establish iOS/Android compatibility.
- Verify optional inputs both omitted and supplied, using small synthetic fixtures; test a
  relocated generated folder to catch absolute source-path dependencies.
- For live Pl@ntNet/VWorld checks, use the application's existing encrypted credential store.
  Ask the user to unlock it directly in the app when needed; never request secrets in chat,
  print keys, log request URLs containing keys, commit credentials, or bypass encryption.
  Use a temporary test project and report actual API outcomes separately from mocked tests.
  Keep automated unit tests isolated from real credentials and external services.
