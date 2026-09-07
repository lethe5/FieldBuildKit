# Traceability Matrix — QField Project Builder, Pl@ntNet API Key Consent-Gated Embedding (D-45)

> Specification: `specs/qfield-project-builder.md`, new Section 13.1a (FR-QPB-114–117), revised
> Section 14.1 (NFR-QPB-071/072, and the revised NFR-QPB-019), and new Section 18.6 acceptance
> criteria AC-QPB-079–082 — all added/revised by Decision Log **D-45**, which extends the VWorld
> online-layer consent-gated key-embedding exception (FR-QPB-073/076–078, Decision Log D-21) to
> the Pl@ntNet API key as a second, independently scoped, closed-list exception (FR-QPB-079,
> revised; NFR-QPB-019, revised).
>
> This is a **third, later test-design round against the same overall specification** as
> `qfield_project_builder.traceability.md` (the approved MVP baseline) and
> `qfield_project_builder_post_mvp_identification.traceability.md` (the Section 13
> guaranteed-manual-baseline round). It is recorded as its own file, not merged into either prior
> file, so neither already-approved traceability record is touched by this round's additions —
> see `tests/acceptance/README.md` for the pointer between all three.
>
> Tests: `tests/acceptance/qfield_project_builder/test_post_mvp_plantnet_key_embedding.py`.
> Test harness contract: `tests/acceptance/qfield_project_builder/HARNESS_CONTRACT.md`'s new
> "Post-MVP: Decision Log D-45" section (the new `plantnet` `build_project` config dict, and the
> `_read_project_variables()` `.qgs`-XML-parsing convention).

This round directly mirrors the already-approved MVP round's VWorld consent-gated key-embedding
tests (`test_basemap_online.py`, AC-QPB-054/055/057/058) for the analogous Pl@ntNet-key
criteria — same structure, same fixture-key-placeholder convention
(`FAKE_PLANTNET_KEY = "ACCEPTANCE-TEST-FAKE-PLANTNET-KEY-0000"`, never a real key value), same
"scan the whole generated project folder for the literal fake key" technique.

## Traceability table

| AC ID / FR / NFR ID | Summary | Test(s) | Automation |
|---|---|---|---|
| AC-QPB-079 | Consent declined -> no Pl@ntNet key embedded anywhere in the generated project (`.qgs` project variables, GeoPackage, `MANIFEST.json`, `VALIDATION_REPORT.json`, `<project_slug>.qml` plugin, logs, temp filenames); identification feature still falls back to manual QField key entry (FR-QPB-116) | `test_post_mvp_plantnet_key_embedding.py::test_ac079_declined_consent_embeds_no_plantnet_key_anywhere` (key-absence scan), `::test_ac079_declined_consent_still_leaves_identification_feature_present` (FR-QPB-116's "feature stays present" half) | auto |
| AC-QPB-080 | Consent accepted -> key embedded ONLY as the `.qgs` project variable named exactly `qpb_plantnet_api_key` (FR-QPB-114); no other artifact contains it | `test_post_mvp_plantnet_key_embedding.py::test_ac080_accepted_consent_embeds_key_only_as_the_project_variable` | auto |
| AC-QPB-081 | `MANIFEST.json` contains only a boolean security-warning flag for the Pl@ntNet embedding, never the key itself, independent of the pre-existing VWorld flag (NFR-QPB-071) | `test_post_mvp_plantnet_key_embedding.py::test_ac081_manifest_contains_only_a_boolean_plantnet_security_warning_flag` (flag presence + no key leakage), `::test_ac081_plantnet_flag_is_independent_of_the_existing_vworld_flag` (independence: Pl@ntNet-only vs. both-embedded) | auto |
| AC-QPB-082 | "Remember this key" (Pl@ntNet) -> OS credential store; else session-only (NFR-QPB-072). **Revised, Decision Log D-53** (Section 18.6): the local storage mechanism changed from the OS credential store (`keyring`) to an application-managed, password-derived, locally-encrypted `credentials.enc` file (shared with the VWorld key, per NFR-QPB-072 revised); the consent-gated opt-in behavior itself is unchanged. See note 1 — this existing test remains valid, unchanged, under that revision. | `test_post_mvp_plantnet_key_embedding.py::test_ac082_remember_key_uses_os_credential_store_not_plaintext` (+ `::test_plantnet_key_not_remembered_by_default_across_sessions`) | auto (proxy — see note 1, mirrors AC-QPB-058's existing note 3) |
| FR-QPB-114 (no separate numbered AC beyond AC-QPB-080 above) | Key embedded only as the `qpb_plantnet_api_key` QGIS project variable; never the GeoPackage, `<project_slug>.qml` source text, `MANIFEST.json` content beyond the boolean flag, `VALIDATION_REPORT.json`, logs, or temp filenames | Same as AC-QPB-080 above | auto |
| FR-QPB-116 (no separate numbered AC beyond AC-QPB-079 above) | Decline path: no embedding anywhere; identification feature still present, usable, requiring manual in-QField key entry | Same as AC-QPB-079 above | auto |
| FR-QPB-079 (revised) / NFR-QPB-019 (revised) (closed, enumerated two-exception list; no dedicated numbered AC) | The VWorld and Pl@ntNet exceptions are independently scoped and the list is closed | Demonstrated jointly by `test_ac081_plantnet_flag_is_independent_of_the_existing_vworld_flag` (both flags coexist independently) and by `test_basemap_online.py`'s existing AC-QPB-054/055/057/058 tests (VWorld exception unaffected/unchanged by this round) | auto (no dedicated new test needed beyond the above; this is a structural/scoping rule, not an independently observable build-time behavior beyond what the two exceptions' own tests already show) |

## Notes on automation approach

1. **AC-QPB-082 — the OS credential store itself is outside this harness's black-box reach**,
   for exactly the same reason already documented for AC-QPB-058 in
   `qfield_project_builder.traceability.md`'s note 3: verifying it would require inspecting the
   running desktop application's OS keychain access, not the generated project artifact. The test
   verifies the artifact-level guarantee (the key is never persisted in plaintext anywhere in the
   delivered project either way, regardless of the "remember this key" choice), which is what
   these acceptance tests can directly observe. Full credential-store round-trip verification
   (actually restarting the desktop application and confirming the key is retrieved from the OS
   keychain) is a supplement for manual/integration QA of the desktop application itself, not the
   generated project, and is not attempted here as an automated test.
   **Update (Decision Log D-53/D-55, 2026-08-25):** the desktop application's own local storage
   mechanism changed from the OS credential store (`keyring`) to an application-managed,
   password-derived, locally-encrypted `credentials.enc` file, shared with the VWorld key. This
   test's reasoning above applies identically to that new mechanism and requires no change. The
   new internal-mechanism criteria this revision introduces (`AC-QPB-089`–`093`/`097`,
   `NFR-QPB-073`) are not addable to this file, for the same reason AC-QPB-082 itself is out of
   this harness's reach, only more so (they concern the desktop application's own internal
   modules directly, not even a proxy artifact check). See the dedicated
   [`qfield_project_builder_credential_storage_mechanism.traceability.md`](qfield_project_builder_credential_storage_mechanism.traceability.md)
   for the full analysis.
2. **AC-QPB-081's "independent" test structure.** NFR-QPB-071 does not name the exact JSON key
   the Pl@ntNet flag must use in `MANIFEST.json` (mirroring the same underspecification already
   accepted for the VWorld flag, NFR-QPB-017, in the MVP round). Rather than guess a literal key
   name for either flag, `test_ac081_plantnet_flag_is_independent_of_the_existing_vworld_flag`
   proves independence structurally: when only the Pl@ntNet key is embedded (no VWorld online
   layer), exactly the Pl@ntNet-named flag is `true`; when both are embedded, a second,
   non-Pl@ntNet-named flag is *also* `true` alongside it. This demonstrates the two flags are
   genuinely distinct and independently toggled without assuming the VWorld flag's exact name.
3. **`_read_project_variables()`'s reliance on the `.qgs` `<properties><Variables>` QStringList
   shape.** This is a standard, documented fact about how QGIS itself serializes project
   variables into a `.qgs` project file (the same class of "known container-format fact, not an
   invented application behavior" already relied on by `test_basemap_online.py` for its
   `&` -> `&amp;` XML-escaping assumption). If a future implementation somehow set the project
   variable through a mechanism that does not produce this standard QGIS serialization shape
   (which would itself be unusual, since QGIS has a single public API for project variables),
   `test_ac080_accepted_consent_embeds_key_only_as_the_project_variable` would fail loudly with a
   clear message (`variables: {}` or similar) rather than silently passing — it is not designed to
   degrade into a weaker substring-only check.

## Ambiguities / gaps found (per the ambiguity-handling procedure)

- **FR-QPB-117's wizard key-collection UI step itself is not covered by this round.** Like the
  prior round's equivalent note for FR-QPB-039 (see
  `qfield_project_builder_post_mvp_identification.traceability.md`'s "Ambiguities" section),
  FR-QPB-117 is Section 6.5 wizard UI/workflow behavior (masking the key in the UI, never logging
  it), not itself a Section 13.1a build-pipeline artifact-generation criterion, and no numbered AC
  in Section 18.6 covers it directly (AC-QPB-079/080 cover the *build-pipeline consequence* of the
  consent decision, not the wizard UI collection step itself). Not tested here; flagged so its
  absence is not mistaken for an oversight. The `plantnet.api_key`/`consent_accepted`/
  `remember_key` config dict this round adds to `build_project()` is a headless stand-in for "the
  wizard already collected this input," exactly mirroring how the MVP round's `basemap.
  vworld_api_key`/`consent_accepted`/`remember_key` config already stands in for FR-QPB-070/076.
- **No genuine ambiguity found in AC-QPB-079–082's own text.** Unlike some earlier rounds (e.g.
  the multi-entry `correct_list` gap, or FR-QPB-109's undefined timestamp/model-version columns),
  these four criteria are each a direct, literal mirror of an already-approved, already-tested
  VWorld criterion (AC-QPB-054/055/057/058), and Decision Log D-45's own text is explicit about
  exactly which artifacts must/must not contain the key. Nothing here required inventing
  unstated behavior.
