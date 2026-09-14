# FieldBuild Kit — agent instructions

## Project identity and working location

- Product/display name: **FieldBuild Kit**. Repository: **lethe5/FieldBuildKit**.
- The user's primary checkout is `D:\오민우 Project\vibe_coding\fieldbuild_standalone`.
  Do not work in the sibling legacy checkout unless the user explicitly requests it.
  Dedicated Git worktrees of this repository are allowed for isolated work.
- `qfield_builder/` is this repository's **internal Python package**, not a dependency on
  the sibling project. The command `fieldbuild-kit` imports `qfield_builder.ui.app:main`.
  `packaging/qfield_builder.spec` is the current build recipe filename.
- Keep product names distinct from code paths. Use FieldBuild Kit in user-facing text and
  FieldBuildKit for the repository. Keep real package/file paths in technical instructions.
  Do not rename the package, build recipe, QPB format identifiers, bundle ID, app-data directory,
  or encrypted-store identifiers as a cosmetic replacement. An internal rename needs a coordinated
  migration of imports, entry points, packaging, tests, and compatibility contracts.
- Current identity/compatibility rationale: `docs/independence.md`.
  Current runtime: `docs/standalone.md`. Older specs record history; do not revive superseded
  QGIS Desktop dependencies or credential migration.

## Authority and reconciliation

These instructions consolidate the legacy CLAUDE.md workflow into this repository.
They are self-contained; no missing `.claude/agents/` definitions are required.

- Explicit user instructions override repository process defaults within their stated scope.
  Preserve approvals already given; do not request the same approval again.
- An instruction to build a feature approves its scope, not an unseen resulting specification
  or acceptance-test artifact. Unless the user explicitly waives a stage, use the gates below.
- The existing standing authorization for local branches, checks, commits and merges remains
  effective. It supersedes the imported CLAUDE.md requirement to ask again before every local
  commit. This does **not** waive specification approval, acceptance-test approval or review.
- Legacy CLAUDE.md's dated "Current status" section is historical, not current project state.
  Determine current status from Git and the relevant artifacts; never copy that section as live status.

## Four clean-room roles

The main agent is the **orchestrator**. Use fresh subagents for substantive role work.
Do not have the orchestrator write the specification, acceptance tests or application code
in place of the appropriate role. Small, low-risk housekeeping and explicitly requested
agent-instruction maintenance may be performed directly by the orchestrator.

| Role | Inputs | Responsibility and write scope |
| --- | --- | --- |
| spec-writer | User requirements, existing spec, relevant shared docs | Elicit gaps; write `specs/<feature>.md` and necessary shared `docs/` changes; stable FR/DR/NFR/AC and Decision Log IDs; no application code or tests |
| test-designer | Approved spec and relevant shared docs | Write executable acceptance tests, test design and criterion-to-test traceability under `tests/acceptance/`; no application code or changed requirements |
| implementer | Approved spec/tests, shared docs, current repository; structured findings on retries | Application code and implementation-level tests (normally `tests/unit/`); never weaken approved spec/acceptance expectations |
| reviewer | Approved spec/tests, current code, Git diff, raw verification output | Read-only overall/per-criterion PASS/FAIL, evidence, blockers and reproduction steps; no edits |

Role boundaries also apply to small product changes. Do not split off a "housekeeping"
label to bypass substantive specification, testing or independent-review work.

## Stage procedure

1. Invoke a fresh spec-writer to produce/update the feature specification.
2. Present the concrete specification and wait for explicit user approval.
   Keep it marked DRAFT until that artifact is approved.
3. Invoke a fresh test-designer with only approved specification artifacts and shared docs.
   Produce acceptance tests, test design and traceability.
4. Present those concrete artifacts and wait for explicit user approval.
5. Invoke a fresh implementer with approved spec, approved tests, shared docs and current source.
6. Run the documented checks appropriate to the change; preserve exact commands and raw output.
7. Invoke a fresh read-only reviewer with approved artifacts, current code/diff and raw check output.
8. If FAIL, invoke a new fresh implementer with approved spec/tests, current source, verification
   results and structured findings. Do not pass earlier role conversations or attempted solutions.
9. Re-run checks and invoke a new fresh reviewer. Allow at most three implementer/reviewer
   attempts total. If the third still fails, stop and report unresolved findings.
10. Commit accepted slices and merge only after the relevant checks and review pass.

Never silently alter an approved requirement/test to make review pass. Report a specification
or test defect and route it back through spec-writer/test-designer with explicit artifact approval.
Do not claim that writing tests, skipping tests or merely inspecting QML proves runtime behavior.

## Context isolation and handoffs

- Each role invocation is a new subagent. With Codex collaboration tools, use `fork_turns="none"`
  and supply the role, repository path, user requirements where applicable, and allowed artifact
  paths. Do not fork the orchestrator's full conversation into a clean-room role.
- No cross-role transcripts, hidden reviewer expectations, scratch notes or attempted-solution
  history. Handoffs use approved repository artifacts, current source/diff, raw verification output
  and structured review findings only.
- Do not resume/reuse a role invocation across stage boundaries or for a retry.
- No concurrency across roles: implementation and review must not overlap. Finish one role stage
  before invoking the next. The orchestrator can perform independent read-only checks while a role runs.
- This is context/workflow separation, **not** an operating-system sandbox. Do not claim that
  role scope technically prevents all out-of-scope reads.
- Subagents must not run Git-mutating commands, including staging, commits, branches, merges,
  worktrees, resets, tags or pushes. Read-only Git inspection is allowed. The orchestrator owns Git.

## User-feedback triage and change control

Classify each distinct request before acting; users need not classify it themselves.

- A. Conformance defect: fix code against the existing approved requirement; add regression coverage.
- B. Specification ambiguity/omission: spec-writer records a stable clarification; update tests/traceability.
- C. User-directed product change: record the authorized change and superseded rules without erasing
  history. Scope approval does not remove the artifact gates above. Inferred changes need user approval.
- D. UX refinement: record durable presentation rules in UI guidance; do not change domain behavior.
- E. Internal tooling/hardening: use engineering docs and focused checks; avoid new product-spec rules
  unless a user-visible contract changes.
- F. Pre-existing/unrelated issue: record separately, with evidence and impact.

Briefly state the category and reason. Ask only for meaningful ambiguity, a required stage approval,
or an action outside existing authorization. Detailed reconciliation: `docs/change-control.md`.

## Branches, checkpoints and merging

- For every new change create a dedicated branch from `main` before editing. Continue related work
  on its existing branch. Preserve unrelated work; use an isolated worktree when appropriate.
- Checkpoint only approved artifacts: spec/docs after specification approval, acceptance artifacts
  after acceptance approval, implementation after reviewer PASS. Keep these checkpoints separate.
- Leave implementation uncommitted during review so its actual working diff can be inspected.
  Never commit DRAFT or otherwise unapproved artifacts.
- Before committing, report the staged file list and diff summary. The standing local-workflow
  authorization means no additional per-commit question is needed.
- Commit and merge to local `main` only when relevant checks and review pass and no required
  verification remains unresolved. If blocked/failing, retain the branch and report it.
- Record unrelated/pre-existing test failures separately; never silently waive a failing check.
- Preserve user work/history: do not reset or rewrite `main` to establish this workflow.
- Pushes, tags, releases and remote settings require explicit user authorization. Push approval
  is per push; local merge authorization does not authorize a push.
- Report branch, commit, validation and merge status on completion.

## Version policy

- When a version change is authorized, use patch for fixes, minor for new features and major for
  breaking changes; increment once per logical change. Documentation-only work needs no bump.
- Check these actual implementation paths for synchronized versions:
  - `pyproject.toml`: `[project].version`
  - `qfield_builder/__init__.py`: `__version__` (internal package)
  - `packaging/qfield_builder.spec`: `APP_VERSION` (build recipe)
- Report old/new versions. Build any distributed artifact from synchronized declarations.
  A version change alone never authorizes a push, tag or release.

## Verification and data safety

- Use checks appropriate to the change. Documentation-only work requires content review and
  `git diff --check`, not app tests.
- The agent owns relevant automated tests, build checks and generated-output checks.
  QField application/device verification is performed by the user. Report user-observed results
  separately and never mark unperformed runtime checks PASS.
- For changed optional inputs, test omitted and supplied values with small synthetic fixtures.
  Relocate a generated project folder to catch absolute source-path dependencies.
- Keep unit tests isolated from real secrets/services. Live Pl@ntNet/VWorld checks use the existing
  encrypted credential store; the user unlocks it directly in the app if necessary.
  Never request secrets in chat, print keys, log key-bearing URLs, commit credentials or bypass encryption.
  Use temporary test projects and distinguish actual service results from mocked tests.
- Never delete, reset or modify a user's QGIS/QField profile or unrelated app settings during tests.
  Use disposable test directories and preserve user data.

## Documentation map

- `docs/product.md`: cross-feature product requirements.
- `docs/architecture.md`: shared architecture decisions.
- `specs/<feature>.md`: integrated feature spec, decisions and acceptance criteria; use `specs/TEMPLATE.md`.
- `tests/acceptance/`: executable acceptance tests, test design and per-feature traceability.
- Review verdicts are conversational/PR output by default. Do not create a permanent reviews directory
  unless the user requests it.
