# APPROVED Traceability — D-103 shared encrypted-store unlock

> Status: **APPROVED — explicitly approved by the stakeholder on 2026-09-23.** Authority is approved D-103,
> clarified NFR-QPB-073 and clarified AC-QPB-097 in `specs/qfield-project-builder.md`.

| Approved authority | Executable evidence | Boundary |
| --- | --- | --- |
| D-103 / NFR-QPB-073: one successful store-scoped unlock lasts for the process/session | `test_d103_shared_credential_unlock.py::test_ac_qpb097_one_successful_unlock_is_shared_across_pages_revisits_and_review_persistence` seeds one real disposable encrypted store, accepts one prompt, then reads VWorld, Pl@ntNet and ORS through their real page consumers in repeated order | Offscreen desktop UI proxy; no native dialog pixels claimed |
| AC-QPB-097: page revisits and review/build remember persistence do not re-prompt or create another store | Same test revisits all consumers, calls the production review/build persistence boundary with all three remember choices, requires cumulative prompt count 1, reads all updated encrypted values and finds exactly one `credentials.enc` | Does not launch the build subprocess; it exercises the UI-process persistence boundary that precedes it |
| D-103 / AC-QPB-097: cancel and wrong password are not successful unlocks; no invented retry | `test_ac_qpb097_cancel_and_wrong_password_do_not_unlock_or_auto_retry[cancel|wrong-password]` performs one Pl@ntNet retrieval attempt, requires one prompt, locked state and empty field; wrong password retains direct-entry guidance | Separate locked-session cases only; no recovery flow or cross-page retry cadence is specified |

The tests monkeypatch both current and legacy app-data roots below pytest `tmp_path`, clear all unlocked and
session-only state before/after every case, use visibly synthetic values, and make no network call.

Verification at approval: `3 passed` with the repository `.venv`. The system Python collection error for
missing `certifi` is environment-only and is not product evidence.
