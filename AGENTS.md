Use repository quality checks appropriate to the requested changes.

## Branch and merge workflow

- For every new change, create a dedicated working branch from `main` before editing; do not
  make changes directly on `main`. Continue related work on its existing working branch.
- Implement, review the diff, and run checks appropriate to the change on that branch.
  Documentation-only changes require a content review and `git diff --check`, not app tests.
- Commit and merge the completed change into local `main` only after the relevant checks pass
  and no known issue or required verification remains unresolved for that change. If verification
  is blocked or fails, keep the work on its branch and report the blocker; do not treat it as passed.
- Record pre-existing unrelated test failures separately. Never silently waive a failing check
  or merge incomplete work merely to finish the task.
- The user has authorized this local branch, test, commit, and merge workflow for future changes.
  Pushes, tags, GitHub releases, and remote repository settings still require a user request.
- Preserve existing user work and shared history; do not reset or rewrite `main` to establish
  this workflow. After merging, report the branch, commit, verification result, and merge status.

## App version policy

- User override (2026-09-08): keep the app at `0.2.8` until the user explicitly requests a
  version change. This takes precedence over the automatic increment rules below.

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

## Verification responsibilities

- The user performs QField application verification. The agent is responsible for appropriate
  automated tests, build checks and generated-output checks; operating QField is not a required
  agent task. Record user-reported QField results separately from automated test results and
  never claim unperformed runtime checks as passed.
- Verify optional inputs both omitted and supplied, using small synthetic fixtures; test a
  relocated generated folder to catch absolute source-path dependencies.
- For live Pl@ntNet/VWorld checks, use the application's existing encrypted credential store.
  Ask the user to unlock it directly in the app when needed; never request secrets in chat,
  print keys, log request URLs containing keys, commit credentials, or bypass encryption.
  Use a temporary test project and report actual API outcomes separately from mocked tests.
  Keep automated unit tests isolated from real credentials and external services.
