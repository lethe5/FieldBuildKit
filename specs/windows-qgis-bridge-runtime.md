# Feature: Windows QGIS dedicated-Python bridge discovery and environment isolation

> Status: DRAFT — awaiting stakeholder review
> Owner: spec-writer
> Last updated: 2026-08-31
> Scope: Windows QGIS/PyQGIS bridge runtime discovery and process-environment hardening

## 1. Summary

The FieldBuild Kit Windows bridge must locate a supported, patch-versioned QGIS 3.44 LTR
installation and run PyQGIS through that installation's dedicated Python interpreter. It must
construct a validated QGIS-specific child-process environment from the official QGIS environment
file, avoid Windows execution-alias/PATH conflicts, and never launch the QGIS GUI merely to
validate the bridge. All new path and environment behavior is Windows-only; the normal macOS
bridge remains unchanged.

The current implementation areas covered by this specification are the Windows branches of
`qfield_builder.qgis_bridge` (`candidate_install_roots`, `_windows_candidates`, `_probe_target`,
`_merged_env`, and bridge dispatch) and the runtime detection path in
`qfield_builder.runtime`. Existing QGIS profile isolation, headless `QgsApplication` setup,
manual-path behavior, and supported-version policy remain in force unless this specification
explicitly changes them.

## 2. Decision Log

- **D-WQGIS-001 (2026-08-31, explicit stakeholder direction):** On Windows, discover patch-
  versioned QGIS folders such as `C:\\Program Files\\QGIS 3.44.13`, prefer the QGIS-owned
  `apps\\Python312\\python.exe`, read `bin\\qgis-ltr-bin.env`, pass the QGIS runtime variables,
  explicitly include `apps\\qgis-ltr\\python`, remove WindowsApps/inherited-PATH conflicts, and
  remove the GUI validation fallback. This decision is Windows-scoped and must not alter the
  normal macOS bridge.

## 3. Functional Requirements

- **FR-WQGIS-001 — patch-versioned discovery:** On Windows, automatic discovery MUST inspect
  standard Program Files roots for directories named `QGIS 3.44.<non-negative integer>` and the
  legacy base name `QGIS 3.44` where present. The discovery MUST support a concrete folder such
  as `C:\\Program Files\\QGIS 3.44.13`; it MUST NOT require an exact unpatched directory name.
  Discovery is non-recursive and limited to the supported standard roots plus the existing
  explicit `QGIS_PREFIX_PATH`/`QGIS_INSTALL_PATH` override and existing OSGeo4W compatibility
  roots.

- **FR-WQGIS-002 — deterministic candidate selection:** An explicit
  `QGIS_PREFIX_PATH`/`QGIS_INSTALL_PATH` override remains first and is validated using the same
  rules as automatic candidates. Among automatically discovered `QGIS 3.44.*` folders, the
  highest numeric patch version MUST be considered first. Ties and non-versioned compatibility
  candidates MUST use a stable, documented case-insensitive absolute-path ordering. A candidate
  that fails validation or PyQGIS probing is skipped and the next deterministic candidate is
  tried; discovery MUST NOT depend on filesystem enumeration order.

- **FR-WQGIS-003 — dedicated interpreter:** For a valid QGIS 3.44 Windows installation, the
  preferred bridge executable MUST be the absolute path
  `<install-root>\\apps\\Python312\\python.exe`. The bridge MUST NOT use the host
  `sys.executable`, a PATH-resolved `python.exe`, or a QGIS GUI executable for the preferred
  Windows path. The dedicated interpreter is used for both validation probes and dispatched
  bridge jobs.

- **FR-WQGIS-004 — official environment-file parsing:** For each Windows candidate, the bridge
  MUST read `<install-root>\\bin\\qgis-ltr-bin.env` as data and construct environment values
  without executing the file as a batch script. The parser MUST accept the assignment forms
  used by the official file (`KEY=VALUE` and `set KEY=VALUE`), ignore blank lines and comments or
  non-assignment command lines, and resolve ordinary `%NAME%` references from the already-known
  environment/assignments without invoking a shell. Only the runtime variables named in
  FR-WQGIS-005 may be imported from this file; arbitrary assignments MUST NOT become arbitrary
  child-process behavior.

- **FR-WQGIS-005 — required child environment:** Every Windows QGIS probe and job launched by
  the bridge MUST receive an environment in which the following variables are explicitly
  controlled rather than inherited as-is: `PYTHONHOME`, `PYTHONPATH`, `QGIS_PREFIX_PATH`,
  `GDAL_DATA`, `QT_PLUGIN_PATH`, and `PATH`. The canonical installation values MUST take
  precedence over conflicting inherited values. `PYTHONHOME` MUST identify the selected QGIS
  Python home; `QGIS_PREFIX_PATH` MUST identify the selected QGIS prefix; `GDAL_DATA` and
  `QT_PLUGIN_PATH` MUST use the validated official-file/installation values; and `PATH` MUST
  begin with the selected QGIS runtime directories.

- **FR-WQGIS-006 — explicit PyQGIS module path:** The effective Windows `PYTHONPATH` MUST
  contain the resolved, actual PyQGIS module directory
  `<install-root>\\apps\\qgis-ltr\\python` as a distinct path entry. It MUST remain present
  even if the official environment file omits it or provides a conflicting `PYTHONPATH`.

- **FR-WQGIS-007 — WindowsApps and PATH isolation:** The effective Windows bridge `PATH` MUST
  remove Windows execution-alias directories, including entries whose normalized path ends in
  `Microsoft\\WindowsApps`, case-insensitively. QGIS-specific entries MUST precede all retained
  non-conflicting system entries. Inherited entries that could shadow the selected QGIS Python
  or QGIS runtime MUST not take precedence over the canonical absolute paths. The bridge MUST
  invoke the dedicated interpreter by absolute path, so executable selection cannot fall back to
  a WindowsApps alias.

- **FR-WQGIS-008 — path and environment validation:** A Windows candidate is usable only when
  its resolved root is a directory and the dedicated interpreter, official environment file,
  QGIS prefix, PyQGIS module directory, and values required for the selected runtime are valid
  paths under the intended installation (or validated official shared/system locations where the
  QGIS installation explicitly requires them). Resolved child paths MUST NOT escape the selected
  root through `..` traversal or symlinks/reparse points. Missing, malformed, non-regular, or
  escaping candidates MUST fail closed and be skipped. Diagnostic messages MAY identify the
  rejected installation path and reason, but MUST NOT dump the complete child environment.

- **FR-WQGIS-009 — headless validation and no GUI fallback:** Windows validation MUST probe
  `import qgis.core` through the dedicated Python interpreter and MUST not launch
  `qgis.exe`, `qgis-bin.exe`, or `qgis-ltr-bin.exe`. Windows bridge candidates MUST NOT include
  a `gui_code` fallback. A validation failure therefore returns a structured unavailable result
  or proceeds to the next candidate without opening a QGIS window. Existing headless
  `QgsApplication` profile-isolation and job lifecycle contracts remain mandatory for a probe or
  dispatched job that reaches them.

- **FR-WQGIS-010 — macOS non-regression:** All new discovery, environment parsing, PATH filtering,
  dedicated-interpreter selection, and no-GUI-fallback logic MUST be guarded by
  `platform.system() == "Windows"`. The existing macOS candidate roots, macOS environment
  construction, Python bridge behavior, and any existing macOS GUI-code compatibility fallback
  MUST remain behaviorally unchanged by this feature. The Windows implementation MUST not read
  Windows installation paths or Windows environment variables while running on macOS.

- **FR-WQGIS-011 — bridge reuse and failure semantics:** Once a validated Windows target is
  selected, subsequent probes/jobs in the same process MUST reuse that target under the existing
  bridge cache semantics. If no candidate successfully validates, the existing structured
  runtime-unavailable behavior remains in force; the bridge MUST not silently use the host Python
  or open a GUI to manufacture a success.

## 4. Constraints

- **C-WQGIS-001:** QGIS 3.44 LTR remains the supported MVP QGIS series and PyQGIS remains a
  machine-provided QGIS dependency; this feature does not install PyQGIS through `pip` and does
  not bundle QGIS.

- **C-WQGIS-002:** The bridge remains a separate local process boundary. No QGIS/PyQGIS import
  is introduced into the PySide6 host process merely to make Windows discovery pass.

- **C-WQGIS-003:** The official `.env` file is configuration input, not executable code. No
  `shell=True`, command interpreter, batch-file wrapper, or GUI launch may be used to parse or
  validate it.

- **C-WQGIS-004:** Existing QGIS profile isolation, transient job data, cancellation/timeout
  behavior, error localization, manual path override contract, and output-secret rules are not
  weakened by changing target discovery or child environment construction.

- **C-WQGIS-005:** The implementation must not globally mutate the host process's `PATH`,
  `PYTHONHOME`, `PYTHONPATH`, `QGIS_PREFIX_PATH`, `GDAL_DATA`, or `QT_PLUGIN_PATH` as a side
  effect of discovering a Windows target. The controlled values apply to the QGIS child process.

- **C-WQGIS-006:** Existing Linux behavior is outside this Windows-specific change and must not
  be altered except for shared helper refactoring that is demonstrably behavior-preserving.

## 5. Assumptions

- **A-WQGIS-001:** The standard Windows installation layout for the supported QGIS 3.44 LTR
  target is the one supplied by the stakeholder: `<root>\\apps\\Python312\\python.exe`,
  `<root>\\apps\\qgis-ltr\\python`, and `<root>\\bin\\qgis-ltr-bin.env`.

- **A-WQGIS-002:** Existing `QGIS_PREFIX_PATH`/`QGIS_INSTALL_PATH` overrides and OSGeo4W roots
  remain supported for compatibility, but a Windows candidate still has to satisfy the new
  dedicated-Python/no-GUI validation contract.

- **A-WQGIS-003:** `%NAME%` expansion in the official environment file is limited to ordinary
  environment/assignment substitution; no command substitution, delayed expansion, or batch
  control-flow semantics are required.

- **A-WQGIS-004:** “QGIS-specific PATH” means the selected QGIS runtime paths, including the
  paths represented by the official environment file and the canonical installation paths,
  precede retained non-conflicting system entries. It does not require removal of every Windows
  system directory needed by the interpreter.

## 6. Edge Cases

- **E-WQGIS-001:** Multiple patch folders exist, for example `QGIS 3.44.7` and
  `QGIS 3.44.13`. The numeric highest patch is tried first; a failed probe falls through to the
  next candidate in deterministic order.

- **E-WQGIS-002:** A folder name matches the patch pattern but lacks the dedicated interpreter,
  environment file, prefix, or PyQGIS directory. It is rejected without launching any GUI and
  discovery continues.

- **E-WQGIS-003:** The official environment file contains comments, `@echo off`, blank lines,
  `set` assignments, quoted values, `%PATH%`, or an unsupported assignment. Only safe supported
  assignments are consumed; unsupported command lines are ignored rather than executed.

- **E-WQGIS-004:** An inherited PATH contains one or more WindowsApps entries, an entry that
  resolves a different Python first, or duplicate QGIS directories. WindowsApps entries are
  removed, canonical QGIS entries remain first, and duplicate path entries are normalized without
  changing the selected target.

- **E-WQGIS-005:** A parsed path is absolute textually but resolves outside the installation by
  traversal or a symlink/reparse point. The candidate fails closed and its complete environment
  is not emitted in diagnostics.

- **E-WQGIS-006:** The selected dedicated Python exists but `import qgis.core` fails or reports a
  malformed probe result. The candidate is rejected and the next deterministic candidate is
  considered; the GUI is never used as a substitute on Windows.

- **E-WQGIS-007:** No Windows candidate is usable. Runtime detection returns the existing
  non-technical unavailable result and does not raise an uncaught exception or open a QGIS
  window.

- **E-WQGIS-008:** The same source code runs on macOS. Windows-only roots, WindowsApps filtering,
  `.env` parsing, and dedicated `Python312` assumptions are not evaluated; the existing macOS
  bridge path is retained.

## 7. Out of Scope

- Installing, upgrading, or bundling QGIS, Python, PyQGIS, GDAL, or Qt.
- Building a Windows installer, signing the executable, or changing the PyInstaller packaging
  layout.
- Changing QGIS version support beyond the existing QGIS 3.44 LTR policy.
- Changing Linux or macOS target discovery, including macOS GUI-code fallback behavior.
- Adding a user-facing QGIS path picker or changing the existing manual-path UI contract.
- Modifying QGIS Desktop, QGIS environment files, Windows registry execution aliases, or the
  user's global PATH. “Remove WindowsApps aliases” in this feature means exclude conflicting
  entries from the bridge child environment, not mutate the operating system.
- Changing QGIS profile isolation, generated project contents, offline maps, MBTiles, report
  generation, identification, or field data behavior.

## 8. Acceptance Criteria

- **AC-WQGIS-001 (automatic patch discovery):** Given a mocked Windows Program Files directory
  containing `QGIS 3.44.7` and `QGIS 3.44.13`, the candidate list contains both valid patch
  candidates, does not require a bare `QGIS 3.44` directory, and orders `3.44.13` before
  `3.44.7` before any lower-priority compatibility root.

- **AC-WQGIS-002 (deterministic selection and fall-through):** Given two valid-looking candidates
  where the highest patch fails PyQGIS probing and the next candidate succeeds, discovery probes
  them in the documented deterministic order and returns the successful candidate. Repeating the
  same test with reversed directory-enumeration order produces the same probe order and result.

- **AC-WQGIS-003 (dedicated Python target):** Given a valid fixture rooted at
  `QGIS 3.44.13`, the selected target executable is the absolute
  `apps/Python312/python.exe`, its target kind is the Python-interpreter kind, and neither
  `sys.executable` nor a PATH-resolved Python is selected.

- **AC-WQGIS-004 (safe official env parsing):** Given a representative
  `bin/qgis-ltr-bin.env` containing `set`/plain assignments, comments, `%PATH%`, and unsupported
  command lines, parsing returns the supported assignment values and performs substitution but
  does not execute commands, spawn a shell, or import an unsupported variable into the child
  environment.

- **AC-WQGIS-005 (required environment values):** Given the same fixture, the environment passed
  to both the import probe and a dispatched job explicitly contains `PYTHONHOME`, `PYTHONPATH`,
  `QGIS_PREFIX_PATH`, `GDAL_DATA`, `QT_PLUGIN_PATH`, and `PATH`; inherited conflicting values
  cannot override the selected QGIS values; and `PYTHONPATH` contains the distinct resolved entry
  `<root>/apps/qgis-ltr/python`.

- **AC-WQGIS-006 (PATH filtering):** Given inherited PATH entries containing a WindowsApps
  directory, a conflicting Python directory, duplicate QGIS entries, and ordinary system paths,
  the effective child PATH contains no normalized WindowsApps entry, places canonical QGIS paths
  first, and invokes the canonical dedicated interpreter by absolute path.

- **AC-WQGIS-007 (path validation):** Given candidates with missing required files, `..` traversal,
  or a symlink/reparse-point child resolving outside the candidate root, validation rejects them
  without probing or launching them. A valid in-root fixture is accepted. Rejection diagnostics
  do not serialize the complete environment or secret values.

- **AC-WQGIS-008 (no Windows GUI launch):** Given a Windows installation whose dedicated Python
  probe fails, the bridge returns an unavailable/failure result or tries the next Python candidate
  without invoking any QGIS GUI executable. A subprocess-spy test observes no `qgis.exe`,
  `qgis-bin.exe`, `qgis-ltr-bin.exe`, or GUI `--code` validation command.

- **AC-WQGIS-009 (no usable installation):** Given no valid Windows candidate, runtime detection
  returns the existing structured unavailable result, does not use the host interpreter, does not
  raise an uncaught exception, and does not create a validation window.

- **AC-WQGIS-010 (cache and job environment):** Given one successfully probed Windows target,
  repeated target lookups reuse the existing cache semantics, while a dispatched job receives the
  same validated QGIS-specific environment and dedicated interpreter contract as the probe.

- **AC-WQGIS-011 (macOS non-regression):** With `platform.system()` set to `Darwin` and the
  existing macOS fixture/mocks, candidate roots, macOS environment values, Python target behavior,
  and existing macOS GUI-code compatibility fallback are unchanged; Windows Program Files,
  WindowsApps, `Python312`, and `qgis-ltr-bin.env` logic are not consulted.

- **AC-WQGIS-012 (host-process isolation):** After Windows discovery and bridge-job setup, the
  host process's PATH and QGIS/Python environment variables remain unchanged, while the child
  process receives the validated values required by AC-WQGIS-005.

## 9. Traceability

| Requirement | Acceptance criteria | Verification focus |
|---|---|---|
| FR-WQGIS-001 | AC-WQGIS-001 | Patch-versioned Program Files discovery |
| FR-WQGIS-002 | AC-WQGIS-002 | Numeric/stable ordering and fall-through |
| FR-WQGIS-003 | AC-WQGIS-003, AC-WQGIS-010 | Dedicated absolute Python target |
| FR-WQGIS-004 | AC-WQGIS-004 | Safe official `.env` parsing |
| FR-WQGIS-005 | AC-WQGIS-005, AC-WQGIS-010 | Explicit child environment |
| FR-WQGIS-006 | AC-WQGIS-005 | Actual PyQGIS module path |
| FR-WQGIS-007 | AC-WQGIS-006 | WindowsApps/PATH conflict removal |
| FR-WQGIS-008 | AC-WQGIS-007 | Root containment and fail-closed validation |
| FR-WQGIS-009 | AC-WQGIS-008, AC-WQGIS-009 | No GUI validation fallback |
| FR-WQGIS-010 | AC-WQGIS-011, AC-WQGIS-012 | macOS isolation and non-regression |
| FR-WQGIS-011 | AC-WQGIS-002, AC-WQGIS-009, AC-WQGIS-010 | Cache and structured failure semantics |
| C-WQGIS-001–006 | AC-WQGIS-005, AC-WQGIS-008, AC-WQGIS-011, AC-WQGIS-012 | Dependency, process, platform, and host-state boundaries |

## 10. Open Questions

None. The requested Windows layout, variables, GUI behavior, path conflict handling, and macOS
boundary are sufficiently precise for acceptance-test design. The implementer may report a
concrete incompatibility in a real QGIS 3.44 patch installation, but resolving a genuinely
different installation layout or expanding supported versions would require a subsequent
specification decision rather than an undocumented fallback.
