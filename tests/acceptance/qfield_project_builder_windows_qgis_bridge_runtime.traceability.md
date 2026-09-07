# Windows QGIS dedicated-Python bridge acceptance traceability

Specification: [`specs/windows-qgis-bridge-runtime.md`](../../../specs/windows-qgis-bridge-runtime.md)

Tests: [`test_windows_qgis_bridge_runtime.py`](qfield_project_builder/test_windows_qgis_bridge_runtime.py)

The suite is deterministic on the macOS development host.  It creates temporary QGIS-shaped
directories, forces `platform.system()` to the required branch, injects inherited environment
values, and spies on `subprocess.run`.  It never requires a Windows installation, QGIS Desktop,
the Windows registry, a command shell, or network access.  Private bridge helpers are used where
the specification intentionally constrains target discovery and child-process construction;
subprocess-spy assertions cover the observable process boundary.

| Acceptance criterion | Test(s) | Coverage |
|---|---|---|
| AC-WQGIS-001 | `test_ac_wqgis_001_discovers_patch_folders_and_orders_highest_patch_first` | Program Files patch folders, legacy bare name, numeric ordering |
| AC-WQGIS-002 | `test_ac_wqgis_002_selection_is_deterministic_and_falls_through_after_probe_failure` | Probe order independent of enumeration order and fall-through |
| AC-WQGIS-003 | `test_ac_wqgis_003_uses_absolute_qgis_owned_python_not_host_or_gui` | Absolute `apps/Python312/python.exe`, target kind, no GUI/host Python |
| AC-WQGIS-004 | `test_ac_wqgis_004_parses_official_env_as_data_and_filters_unsupported_assignments` | Plain/set assignments, comments, `%NAME%`, unsupported commands/variables, no shell |
| AC-WQGIS-005 | `test_ac_wqgis_005_probe_and_job_receive_all_canonical_environment_values` | Required child env on probe and job, inherited conflict precedence, PyQGIS path |
| AC-WQGIS-006 | `test_ac_wqgis_006_removes_windowsapps_and_keeps_qgis_paths_first` | WindowsApps removal, QGIS-first PATH, absolute executable |
| AC-WQGIS-007 | `test_ac_wqgis_007_rejects_invalid_installations_before_probe` | Missing paths, escaping/symlink paths, no probe, no complete-env diagnostic serialization |
| AC-WQGIS-008 | `test_ac_wqgis_008_failed_python_probe_never_launches_a_windows_qgis_gui` | Failed dedicated-Python import, no GUI executable or `--code` fallback |
| AC-WQGIS-009 | `test_ac_wqgis_009_no_usable_installation_returns_structured_unavailable_result` | Structured unavailable runtime result and no host-Python fallback |
| AC-WQGIS-010 | `test_ac_wqgis_010_successful_target_is_cached_and_job_reuses_it` | Per-process target cache and same target on dispatched job |
| AC-WQGIS-011 | `test_ac_wqgis_011_macos_branch_never_consults_windows_logic` | Darwin roots/candidate branch and preserved macOS compatibility boundary |
| AC-WQGIS-012 | `test_ac_wqgis_012_discovery_and_job_setup_do_not_mutate_host_environment` | Host env unchanged; child-only QGIS values |

The tests intentionally fail against an implementation that retains exact unpatched Windows roots,
uses wrapper/GUI fallbacks, imports the host PATH, or does not validate containment.  Those failures
are required signals for the implementer and are not skipped merely because this host is macOS.
