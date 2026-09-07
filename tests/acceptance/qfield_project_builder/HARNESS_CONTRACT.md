# Test Harness Contract — QField Project Builder acceptance tests

> Authored by: `test-designer`, from `specs/qfield-project-builder.md` (approved MVP baseline).
> This file is **not** additional product specification. It documents the minimal, stable
> Python entry points these acceptance tests call into the application under test. No
> application code exists yet at the time these tests were written; the `implementer` role is
> expected to expose this surface (wrapping whatever internal architecture it chooses) so that
> the tests below are executable. Everything *behind* this surface (module layout, class names,
> the exact IPC mechanism between the PySide6 UI process and the PyQGIS worker process per
> Open Question O-1, etc.) is explicitly left to the implementer.
>
> Rationale for why a contract is necessary at all: the specification describes user-facing
> wizard behavior and generated-artifact behavior, not a Python API. Because the architecture
> (`docs/architecture.md`, FR-QPB-010) already requires that all QGIS/PyQGIS/GDAL project
> generation be callable independently of the PySide6 GUI (it runs in a separate headless
> worker process), a headless, GUI-independent build entry point is not an invented product
> behavior — it is implied by the approved architecture. Wherever the generated *artifacts*
> are themselves inspectable standard formats (SQLite GeoPackage, MBTiles, `.qgs` XML, JSON),
> these tests read those files directly with standard-library/well-known tooling instead of
> inventing a bespoke inspection API, to minimize invented surface.

## Module: `qfield_builder.acceptance_api`

All functions below must be importable from this module. `pytest.importorskip` is used, so if
this module does not yet exist, the tests **skip** (not error/fail) — this is the expected state
before implementation exists.

### 1. `check_runtime(force_missing: bool = False) -> dict`

Wraps FR-QPB-008/FR-QPB-009 (QGIS/PyQGIS/GDAL runtime detection and verification).

- Returns `{"available": bool, "message": str}`.
- `message` must be non-technical/actionable when `available` is `False` (E-QPB-002).
- `force_missing=True` must deterministically simulate "no compatible QGIS installation found"
  regardless of the actual host environment, so that AC-QPB-029 is testable on a machine that
  *does* have QGIS installed, and so the rest of the suite can still run there. This is a test
  seam, not a product feature.

### 2. `derive_project_slug(display_name: str) -> dict`

Wraps FR-QPB-021/FR-QPB-021a (`project_display_name` → `project_slug` derivation/validation).

- On success: `{"ok": True, "slug": str}`. `slug` must be ASCII letters/digits/hyphens/
  underscores only, non-blank, ≤64 characters.
- On rejection: `{"ok": False, "error_code": str, "message": str}`, where `error_code` is one of
  `"blank"`, `"path_traversal"`, `"reserved_filename"`, `"too_long"` (implementer may add finer
  codes; tests only assert `ok is False` for rejected inputs, plus specific codes where the
  distinction is spec-relevant).

### 3. `estimate_offline_basemap_size(bbox: dict, min_zoom: int, max_zoom: int, representative_tile_bytes: float) -> dict`

Wraps FR-QPB-081/FR-QPB-082/DR-QPB-060 (pre-generation tile-count/size estimation and the 900 MiB
acceptance threshold). `bbox` is `{"min_lon": float, "min_lat": float, "max_lon": float, "max_lat": float}`
in EPSG:4326. `representative_tile_bytes` is a test-supplied stand-in for the "representative
`Content-Length` sample" the real implementation would otherwise measure from VWorld — this
avoids requiring live network access to test the estimation *logic*.

- Returns `{"tile_count": int, "estimated_bytes": int, "exceeds_pregeneration_threshold": bool}`.
- `exceeds_pregeneration_threshold` must be `True` iff the (implementer-chosen, conservative)
  estimate exceeds 900 MiB (943,718,400 bytes), per DR-QPB-060.

### 4. `build_project(config: dict, output_dir: str) -> dict`

The headless equivalent of a user completing the six-step wizard (Section 6) and clicking
"Build" (FR-QPB-041). Must perform real GeoPackage/`.qgs`/basemap/transfer-folder generation
using the detected QGIS/PyQGIS runtime — no GUI interaction required to invoke it.

Returns:

```
{
  "success": bool,
  "cancelled": bool,
  "project_dir": str | None,
  "project_id": str | None,
  "project_slug": str | None,
  "qgs_path": str | None,
  "gpkg_path": str | None,
  "attachments_dir": str | None,
  "basemap_dir": str | None,
  "manifest_security_warning": bool | None,
  "error_code": str | None,
  "error_message": str | None,
}
```

`MANIFEST.json`, `VALIDATION_REPORT.json`, and `README_TRANSFER_KO.md` are read by the tests
directly from `project_dir` (their names are fixed by FR-QPB-090/092/093/094, which use them as
literal file names throughout, unlike the flexible-named `.qgs`/`.gpkg`/`attachments/`/`basemap/`
roles for which `build_project` reports the actual paths it used).

`config` keys (all optional except where noted; unset optional keys use the wizard's documented
defaults):

- `project_display_name` (str, **required**) — FR-QPB-020.
- `description` (str)
- `project_crs` (str, EPSG code, default `"EPSG:5186"`) — FR-QPB-020.
- `storage_crs` (str, EPSG code, default `"EPSG:4326"`) — FR-QPB-020, DR-QPB-008.
- `survey_type` (str, **required**, one of `"simple_inventory"`, `"temporary_plots"`,
  `"permanent_plots"`, `"vegetation_mapping"`) — FR-QPB-023.
- `sites` (list of dicts, when applicable to `survey_type`) — each
  `{"site_name": str, "geom_wkt": str}` (Polygon/MultiPolygon WKT in `storage_crs`), representing
  drawn-map input (FR-QPB-025). A parallel `sites_upload` key (see below) exercises the
  file-upload input path instead.
- `sites_upload` (dict, alternative to `sites`) —
  `{"format": "gpkg" | "shapefile" | "zipped_shapefile", "path": str, "attribute_mapping": {"site_name": <source field>}}`.
  For Shapefile formats an optional `encoding` (`"cp949"` or `"utf-8"`) selects the DBF
  character encoding; it defaults to `"cp949"`.
- `plots` (list of dicts, for `permanent_plots`) — each
  `{"plot_name": str, "geom_wkt": str, "plot_size": str}` (Point WKT).
- `temporary_plot_seed_points` (list of dicts, for `temporary_plots`, optional) — each
  `{"site_name": str, "geom_wkt": str, "plot_size": str}`, exercised for FR-QPB-033 (seed survey
  records with empty `survey_date`/`surveyor` until field collection).
- `basemap` (dict, **required**) —
  - `mode`: `"online"` | `"offline"` | `"none"`.
  - online: `vworld_api_key` (str), `layer` (one of `Base`/`White`/`Midnight`/`Hybrid`/`Satellite`),
    `consent_accepted` (bool, FR-QPB-076), `remember_key` (bool, NFR-QPB-018).
  - offline: `bbox`, `min_zoom`, `max_zoom`, `vworld_api_key`, and a non-blank `layer` selected
    from the same supported VWorld layer set as online (`Base`/`White`/`Midnight`/`Hybrid`/
    `Satellite` in the current fixture), plus exactly one of:
    - `tile_source: "vworld"` (real network; tests using this are marked `network` and skipped
      by default), or
    - `tile_source: {"fake": {"mode": "success" | "quota_error" | "auth_error" | "rate_limit_error", "tile_bytes": int}}`
      — a deterministic fault-injection double standing in for the real VWorld tile-download
      client, used to test FR-QPB-088/AC-QPB-052/E-QPB-013 without live network or quota
      consumption. This is a test seam analogous to dependency injection; it does not change
      the production default (real VWorld) when omitted.
- `identification_enabled` (bool, default `False`) — FR-QPB-037/038; MVP tests always leave this
  `False` or omitted, since the identification subsystem itself is post-MVP and out of scope.
- `_test_cancel_after_phase` (str, optional test-only hook) — if set to a recognized build phase
  name (e.g. `"basemap_download"`), the build must cancel itself immediately after entering that
  phase, exercising FR-QPB-041/E-QPB-010 deterministically instead of racing a real cancellation.
- `_test_force_missing_runtime` (bool, optional test-only hook) — if `True`, `build_project` must
  take the same "no compatible QGIS installation" failure path it would take on a real machine
  lacking QGIS (FR-QPB-009/E-QPB-002), regardless of the actual host environment. This lets
  AC-QPB-029 be exercised deterministically on a machine that *does* have QGIS installed (needed
  for the rest of the suite to run there at all).

On naming rejection, missing-runtime, existing-output-directory, invalid-geometry, or
offline-size-exceeded conditions, `build_project` must return `success: False` with a non-null
`error_code` (matching the codes documented per-test below) rather than raising an uncaught
exception, no partially-generated project left at `output_dir` (E-QPB-009), and no partially
generated project left even when `cancelled` is `True` (E-QPB-010).

### 5. `attempt_feature_save(project_dir: str, layer_name: str, attributes: dict, geometry_wkt: str | None = None) -> dict`

Attempts to save a single feature (new row) on the named layer within the generated project,
going through the same field-constraint validation the project's own attribute-form
configuration enforces (FR-QPB-057's "hard constraints, not only UI labels" — i.e. QGIS field
constraints such as `QgsFieldConstraints`, not merely UI widget behavior, and not a bypass of
them via raw SQL). Used for single-feature/single-field validation rules (e.g. `cover` range,
required non-empty text, optional photo fields), not cross-table relation-cardinality rules.

Returns `{"accepted": bool, "rejected_field": str | None, "rejected_reason": str | None, "generated_uuid": str | None}`.
`generated_uuid` is the value assigned to the layer's UUID identifier column (DR-QPB-005: normally
auto-generated via the `uuid('WithoutBraces')` default expression rather than supplied by the
caller) for an accepted save, so a test can reference the created row from a subsequent related
insert; it is `None` when `accepted` is `False`.

### 6. `validate_project(project_dir: str) -> dict`

Wraps re-opening/validating an *existing* generated project (FR-QPB-094, Section 17), used both
for the moved-folder case (NFR-QPB-021, AC-QPB-010/024) and for re-running manifest/missing-file
detection against a deliberately mutated folder (AC-QPB-027, AC-QPB-031). Must use the same
headless QGIS/PyQGIS runtime as `build_project`, not merely re-parse `VALIDATION_REPORT.json`.

Returns `{"opens_without_repair_warning": bool, "missing_layer_warning": bool, "issues": [{"code": str, "message": str}]}`.

`issues[*].code` must include (at minimum) the following stable identifiers, tied 1:1 to the
specification checks in Section 12/18 that `VALIDATION_REPORT.json` (FR-QPB-094) is required to
confirm — this list exists purely so these acceptance tests can assert on a stable string rather
than fuzzy-matching free-text messages; it does not add new product behavior beyond what Section
12/18 already requires be checked:

| code | condition it flags | spec basis |
|---|---|---|
| `missing_manifest_file` | `MANIFEST.json` references an attachment, plugin, database, or basemap file that is declared as part of the project but is absent from the project folder | FR-QPB-092, AC-QPB-027 |
| `broken_attachment_reference` | a `survey_photo`/`plot_photo` record, or a Type 1 `inventory_observation`/Type 2-3 `observation` record's `leaf_photo_path`/`flower_photo_path`/`fruit_photo_path` column (**Decision Log D-74, 2026-08-28: `observation_photo` no longer exists for Type 2/3 — these three inline `observation` columns are its replacement, added here alongside Type 1's own identical, pre-existing columns**), has a non-null, well-formed relative `path`/column value, but the file that path resolves to is absent from the project folder. This is layer-below `missing_manifest_file`: it is about a GeoPackage photo *record's* stored reference going stale, not about a manifest-declared file being absent (that is `missing_manifest_file`, above), and it is distinct from the path itself being invalid (that is `invalid_attachment_path`, below). A record with **zero** populated photo fields/related photo rows never produces this issue — see the D-23/D-74 note below | FR-QPB-092, AC-QPB-009 |
| `invalid_attachment_path` | a `survey_photo`/`plot_photo` record, or a Type 1/Type 2-3 `leaf_photo_path`/`flower_photo_path`/`fruit_photo_path` column (same Decision Log D-74 scope note as `broken_attachment_reference` above), has a stored `path`/column value that is itself not a valid relative attachment path — e.g. an empty string, whitespace-only, an absolute path (POSIX, Windows drive-letter, or UNC), a `file://` URI, or a `..` traversal that escapes the project root — as opposed to a well-formed relative path whose target file happens to be absent (that is `broken_attachment_reference`, above). A record with **zero** populated photo fields/related photo rows never produces this issue. See "Save-time vs. `validate_project`-only enforcement for `invalid_attachment_path`" below for exactly which of these shapes `attempt_feature_save` is also expected to reject at save time, versus which are caught only by `validate_project` | DR-QPB-012, AC-QPB-009 |
| `cover_out_of_range` | a stored `cover` value is outside `0`–`100` | AC-QPB-007 |
| `foreign_key_violation` | `PRAGMA foreign_key_check` found a violation | DR-QPB-011, AC-QPB-004 |

Note (revised; Decision Log D-23; further revised, Decision Log D-74, 2026-08-28): there is
deliberately **no** `missing_required_child_photo`-style code. A Type-2 `survey` or Type-3 `plot`
record with zero related photo rows, or a Type 1/2/3 observation-layer record
(`inventory_observation`/`observation`) with zero of its three photo-path columns populated, is
valid and must never be reported as an issue by `validate_project()` — in particular, it must
never produce a `broken_attachment_reference` or `invalid_attachment_path` issue, since there is no
photo record/populated column whose path could be broken or invalid in the first place — see
DR-QPB-030/040 (survey/plot; unaffected by D-74), DR-QPB-074/075 (Type 2/3 `observation`'s three
inline columns; new, D-74, superseding the struck-through DR-QPB-031/042's `observation_photo`-based
framing), DR-QPB-020/021 (Type 1's identical, pre-existing `inventory_observation` rule),
NFR-QPB-041, and AC-QPB-009 (narrowed)/AC-QPB-114 (new). Only a photo record/populated column that
*does* exist is ever examined: if its path is malformed, that is `invalid_attachment_path`; if its
path is well-formed but the referenced file is missing from the project folder, that is
`broken_attachment_reference` (both above). `missing_manifest_file` is a separate, manifest-level
check (AC-QPB-027) and is orthogonal to whether any photo records/populated columns exist at all.

### Save-time (`attempt_feature_save`) vs. `validate_project`-only enforcement for `invalid_attachment_path`

Not every malformed-path shape covered by `invalid_attachment_path` is enforced identically by
both layers. This split is deliberate and documented here so the implementer is not left to guess
at, or asymmetrically half-implement, this behavior:

| Malformed shape | Example | `attempt_feature_save` (save-time) | `validate_project` |
|---|---|---|---|
| empty string | `""` | must reject | must report `invalid_attachment_path` (e.g. imported/corrupted data that bypassed the form) |
| whitespace-only | `"   "` | must reject | must report `invalid_attachment_path` |
| POSIX absolute path | `/etc/photos/leaf.jpg` | must reject | must report `invalid_attachment_path` |
| Windows drive-letter absolute path | `C:\Users\x\leaf.jpg` | must reject | must report `invalid_attachment_path` |
| UNC / network path | `\\server\share\leaf.jpg` | must reject | must report `invalid_attachment_path` |
| `file://` URI | `file:///Users/x/leaf.jpg` | must reject | must report `invalid_attachment_path` |
| `..` traversal escaping the project root | `../../outside/leaf.jpg` | **not required/asserted at save time** (validate_project-only) | must report `invalid_attachment_path` |

Rationale: the first six shapes are purely syntactic — a leading `/`, an `[A-Za-z]:` drive prefix,
a leading `\\` UNC prefix, a `file://` scheme, or blank/whitespace text are all detectable by a
static, per-feature QGIS field-constraint expression (e.g. via `regexp_match`/`trim`/`length` in
a `QgsFieldConstraints` expression constraint) that needs nothing beyond the candidate string
itself. FR-QPB-057 already requires "hard constraints, not only UI labels" for mandatory
attributes, and none of these six checks requires filesystem or project-location context, so
`attempt_feature_save` is expected, and these tests assert, that the generated form rejects all six
at save time.

`..`-traversal is different in kind. Whether a relative path such as `../../outside/leaf.jpg`
actually escapes the project root depends on resolving it against the *actual* project folder
location and normalizing it (`os.path.normpath`/`Path.resolve()`-equivalent semantics) — that is
filesystem/project-location-aware logic. `validate_project()` already has `project_dir` in hand and
can safely resolve/normalize the stored path against it, so it is required to catch this case. A
single static per-feature field-constraint expression evaluated by the QGIS attribute form does not
have that same context, and a naive substring check for `".."` inside such an expression is not a
reliable substitute (e.g. it cannot distinguish a path segment `..` from an unrelated filename that
merely contains two literal dots, and it has no way to know how many directory levels the stored
path is nested under before deciding whether a given number of `..` segments actually escapes the
root). Given that, these tests do not assume the generated form rejects traversal at save time, and
do not assert either outcome for `attempt_feature_save` on this specific shape — only that
`validate_project()` catches it. If a future implementer chooses to also enforce this at save time,
that is a superset of what is asserted here and would not break these tests.

## Post-MVP: Section 13 (Pl@ntNet / KTSN / Occurrence Probability) harness additions

> Added by a later `test-designer` round (2026-08-15) covering the "guaranteed-manual baseline"
> slice of Section 13 authorized by Decision Log D-31–D-36: FR-QPB-100/101 (project-scoped
> `.qml` plugin + embedded `QML Widget` action), FR-QPB-104 (Pl@ntNet request shape), FR-QPB-106/
> 107 (KTSN direct match + accepted-name resolution), FR-QPB-112 (reference-data bundling).
> **A genuine architectural split governs this section — read it before touching these tests.**
> Some of Section 13 is generated/prepared by this project's own Python desktop build pipeline
> (testable the same way the MVP surface above is: real `build_project()` output, inspected
> directly). Other parts of Section 13 (the KTSN matching *rules*, the Pl@ntNet request-shape
> *rules*) describe logic that will ultimately ship as QML/JavaScript running inside QField
> itself — this project has **no QField/QML runtime or test harness of any kind**. For those, the
> functions below are an explicit, narrowly-scoped exception: **pure-Python reference
> implementations of the rules**, authorized specifically because (a) the stakeholder explicitly
> authorized starting KTSN validation work against the real, now-confirmed reference fixtures
> (Decision Log D-34), and (b) a real Pl@ntNet API key now exists for live verification of the
> request/response contract (Decision Log D-32). **Passing these Python tests validates that the
> rules are correct against real data/a real API — it is not, and must never be treated as, a
> substitute for confirming the eventual QML implementation behaves identically.** That residual
> confirmation remains QML-runtime-dependent and is out of this harness's reach; see
> `test_post_mvp_manual_qfield_runtime.py` for what is explicitly left as documented manual/
> `device` QA instead of being silently skipped or falsely claimed as covered.

### 7. `build_plantnet_identify_request(photo_paths: list[str], organs: list[str], project: str = "all") -> dict`

> **2026-09-07 D-98 amendment:** Omit `nb-results` from both reference helpers and the
> shipped QML request. No client-side truncation is permitted before or after canonical
> Korean-name filtering. Historical live observations and D-54 notes below do not impose
> a current result count. See specification Section 13.2a; provider defaults remain external.

A **pure-Python reference implementation of FR-QPB-104's client-side request-shape rules only**
— performs no network I/O. It is not the shipped mechanism (Pl@ntNet is called from the embedded
`QML Widget` via QML's own native `XMLHttpRequest`, FR-QPB-101); it exists so the *rules*
themselves (no application-imposed result limit, one `organs` value per photo in matching order, at most
five photos, JPEG/PNG only) are verifiable offline against real, test-designer-confirmed API
behavior (see function 8 below and its live-verification note).

- On success: `{"ok": True, "url": str, "method": "POST", "query": {"project": str, "include-related-images": True}, "organs": list[str], "photo_paths": list[str]}`.
  `url` must be of the confirmed real endpoint family `https://my-api.plantnet.org/v2/identify/{project}`
  — this exact base URL (not `my.plantnet.org`, which 404s) and the `api-key`/`nb-results`
  query-parameter authentication scheme were live-confirmed by the test-designer against the real
  API on 2026-08-15 using the real key in `QPB_TEST_PLANTNET_API_KEY` (see function 8's
  docstring-equivalent note); this specification note (FR-QPB-104) previously left the base URL
  and auth scheme as "must be confirmed," which this round's live check now resolves.
  `nb-results` must be absent (FR-QPB-104, D-98). Do not enforce a replacement fixed count.
- On rejection: `{"ok": False, "error_code": str, "message": str}`. Required `error_code` values:
  `"organ_count_mismatch"` (`len(organs) != len(photo_paths)`), `"too_many_photos"` (more than 5
  photos), `"unsupported_photo_format"` (an extension other than `.jpg`/`.jpeg`/`.png`).
- Must never place raw photo *bytes* in its return value (only paths/filenames) — this is the
  request-construction-layer counterpart of FR-QPB-104's "never log photo binary data"; the
  separate concern of the running application never actually *logging* whatever it sends is an
  application-logging behavior outside what a pure request-shape function can prove, and is not
  asserted here.

> **2026-08-25 addendum (Decision Log D-54; FR-QPB-104, further revised; AC-QPB-094):** the
> success-path `query` dict must also carry `"include-related-images": True` (a Python `bool`,
> mirroring the existing `"nb-results": 3` int convention — the literal lowercase query-string
> text `"true"` the real HTTP request must eventually carry is a URL-encoding-layer concern
> downstream of this reference-shape function, exactly like `nb-results`'s own int-to-`"3"`-text
> conversion). This must always be `True` — the function must not accept a caller override for
> this, mirroring `nb-results`'s own non-overridable-constant treatment. `api-key` remains outside
> this function's own return shape, unchanged (see this section's existing text above — `api-key`
> is supplied only at real call time, via function 8's `api_key` argument). See new
> `test_requests_related_images_are_included` in `test_post_mvp_plantnet_request_shape.py`.

### 8. `call_plantnet_identify(photo_paths: list[str], organs: list[str], api_key: str, project: str = "all") -> dict`

A **test-only, real-network-calling reference implementation**, used exclusively by the
`network`-marked live test (mirrors the role `qfield_builder.vworld.fetch_supported_layers` plays
for the existing live VWorld test — a real production function, actually invoked with a real key,
skipped by default). Performs a real HTTPS POST to the request built by function 7's rules.

Returns `{"http_status": int, "body": dict | None, "raw_text": str}`; `body` is the parsed JSON
response (both the success envelope and the error envelope are JSON — live-confirmed, see below).
Must never log/print `api_key` or raw photo bytes.

**Live-verification note (2026-08-15, partially closes the live-verification portion of Open
Question O-14/Decision Log D-32; performed by the test-designer using the real key already
present locally in the gitignored `.env` as `QPB_TEST_PLANTNET_API_KEY` — the literal key value
was never written to any file, only referenced by environment-variable name, exactly as
`QPB_TEST_VWORLD_API_KEY` already is):**

- Real endpoint: `https://my-api.plantnet.org/v2/identify/{project}` (POST, multipart form body
  with an `organs` field per photo and an `images` file per photo). `https://my.plantnet.org/...`
  returns HTTP 404 and must not be used.
- Auth scheme: `api-key` **query parameter** (not an `Authorization` header).
- `nb-results` is also a query parameter; requesting `nb-results=3` returns exactly 3 results
  (confirmed with a synthetic, dependency-free-generated PNG test image — a real API account
  quota was not spent on a real plant photo for this schema-confirmation purpose).
- Success response envelope keys (confirmed live): `query`, `predictedOrgans`, `language`,
  `preferedReferential`, `bestMatch`, `results`, `version`, `remainingIdentificationRequests`.
  Each `results[*]` entry has `score` (float, 0–1) and `species.scientificNameWithoutAuthor`/
  `scientificNameAuthorship`/`scientificName` (confirming FR-QPB-104's
  `species.scientificNameWithoutAuthor` field path is correct) plus `genus`/`family`/
  `commonNames`. **Results were already returned in descending-`score` order by the real API** —
  supporting AC-QPB-040's "ordered by descending Pl@ntNet score" as a property of the API
  response itself, not something the client must additionally sort.
- Auth-failure response (confirmed live, invalid key): HTTP `401`, JSON body
  `{"statusCode": 401, "error": "Unauthorized", "message": "Bad token", "attributes": {"error": "Bad token"}}`.

### 9. `match_ktsn(scientific_name_without_author: str, csv_path: str) -> dict`

A **pure-Python reference implementation of FR-QPB-106 (direct match) + FR-QPB-107
(accepted-name resolution)**, validated against real slices of the actual, stakeholder-confirmed
(Decision Log D-34) reference CSV at `storage/reference/tables/tb_leco_nib_ktsn_dtl_gat.csv`. As
with function 7/8, this validates the *rules* against real data; it is not the shipped mechanism
(which will run as embedded QML) and is not a substitute for QML-runtime verification.

Returns:

```
{
  "direct_match_found": bool,
  "direct_row_ktsn": str | None,
  "direct_korean_name": str | None,          # taxon_kor_nm of the directly matched row
  "direct_taxon_jm_nm": str | None,
  "accepted_resolution_attempted": bool,      # only True when direct_match_found is True
  "accepted_resolved": bool,
  "accepted_ktsn": str | None,
  "accepted_korean_name": str | None,
  "accepted_scientific_name": str | None,     # <em> tags removed (FR-QPB-107)
  "ambiguous": bool,                          # KTSN vs KTNS present with different values
  "ambiguous_reason": str | None,
  "unresolved_reason": str | None,            # e.g. "correct_list_empty", "correct_list_malformed",
                                                # "correct_list_missing_ktsn_key", "accepted_ktsn_not_found_in_csv"
}
```

Matching/resolution rules (restating FR-QPB-106/107 precisely, since this is the contract the
tests assert against):

- Normalize the candidate name by trimming and collapsing internal whitespace. Normalize each
  CSV `taxon_full_nm` by removing literal `<em>`/`</em>` tags, trimming, and collapsing
  whitespace. An exact match (no fuzzy matching) on these normalized forms is the direct match.
  No match -> `direct_match_found: False`, `direct_korean_name: None` (never fabricated).
- If `direct_match_found` and the matched row's `taxon_jm_nm == '정명'`, that row **is** the
  accepted record (`accepted_resolved: True`, `accepted_ktsn`/`accepted_korean_name`/
  `accepted_scientific_name` all equal to the direct match's own values) — `correct_list` is not
  consulted in this case.
- Otherwise (`taxon_jm_nm != '정명'`): parse the matched row's own `correct_list` as JSON. If
  parsing fails, or the value is empty/absent, `accepted_resolved: False` with `unresolved_reason`
  set accordingly, and the
  direct match is retained. If valid, read the `KTSN` key (canonical) or `KTNS` (defensive legacy
  fallback only when `KTSN` is absent) from the (first) entry; if **both** keys are present with
  **different** values, `ambiguous: True` and `accepted_resolved: False` — never silently pick
  one. If neither key is present, `accepted_resolved: False` with
  `unresolved_reason: "correct_list_missing_ktsn_key"`. Look up the resolved KTSN value in the
  CSV's own `ktsn` column; if not found, `accepted_resolved: False` with
  `unresolved_reason: "accepted_ktsn_not_found_in_csv"`. If found, populate `accepted_ktsn`/
  `accepted_korean_name` (`taxon_kor_nm`)/`accepted_scientific_name` (`taxon_full_nm`, tags
  stripped) from that row.

**Historical note:** the earlier deliberate gap around multi-entry `correct_list` values is
superseded by D-88's additive seam below. The original function remains unchanged for backwards
compatibility with the pre-D-40 contract; new recursive/NIBR assertions use the D-88-aware seam.

### D-88 addendum: `match_ktsn_with_national_list(scientific_name_without_author: str, csv_path: str, national_ktsn_set: set[str] | None = None) -> dict`

This additive pure-Python reference seam mirrors `match_ktsn` (function 9), but applies the
approved FR-QPB-107/D-40/D-42 national-list rule to a multi-entry `correct_list` at **every
recursive hop**. A candidate whose `KTSN`/`KTNS` is the sole member of `national_ktsn_set` is
selected and traversal continues; zero or multiple national-list matches are ambiguous. The
returned dictionary has the same keys and direct-match semantics as `match_ktsn`, and accepted
fields may be populated only from a terminal row whose `taxon_jm_nm` is exactly `정명`.

For D-88, traversal must also detect repeated KTSN values (including self-reference), missing or
malformed/non-array/empty `correct_list`, unusable candidate keys, conflicting `KTSN`/`KTNS`
values, missing target rows, and must stop after at most 64 transitions. Failure retains the
direct-match fields and leaves accepted fields unavailable while exposing the existing unresolved
or ambiguous indication; it never returns an intermediate non-`정명` row.

### 10. `inspect_identification_widget(project_dir: str, layer_name: str) -> dict`

PyQGIS-backed (like `validate_project`), wraps AC-QPB-070. Inspects the given layer (e.g.
`inventory_observation` or `observation`) in the generated project for the embedded `QML Widget`
"Identify attached photos" action.

Returns `{"qml_widget_field_found": bool, "qml_widget_field_name": str | None, "embedded_in_attribute_form": bool, "qml_code_present": bool, "qml_code": str}`.

> **2026-08-24 addendum (Decision Log D-50/D-51; FR-QPB-109 further revised/AC-QPB-046 further
> revised):** the `qml_code` key is new. It must return the exact raw QML/JavaScript source text
> of the embedded widget's `QgsAttributeEditorQmlElement.qmlCode()` (the same underlying value
> `qml_code_present` already checked for truthiness/non-blankness internally, per this project's
> own pre-existing `qfield_builder/identification_inspect.py` implementation) — `""` when
> `qml_widget_field_found` is `False`. This is required so that new, purely structural
> `test_fr109_*` tests in `test_post_mvp_identification_plugin.py` can assert on the *literal
> content* of the generated QML (e.g. whether it actually calls `FileUtils.writeFileContent(...)`
> to write the pending write-back request FR-QPB-109 (further revised; Decision Log D-50/D-51)
> now requires), not merely whether some non-empty QML source exists at all, which is all
> `qml_code_present` alone can prove. This mirrors the existing rationale for exposing generated
> artifacts directly (see this file's top-of-document rationale note) rather than inventing a new,
> separate inspection API; it only widens an already-existing function's return contract by one
> field. No other part of this function's existing contract changes.

**Exact editor-widget-type-string note (deliberately not hardcoded in the tests as a raw XML
string — see rationale):** `docs.qfield.org`'s attribute-form documentation (cited by Decision Log
D-31) confirms "QML Widget" as a real QGIS/QField editor-widget type, backed by the
`QgsQmlWidgetWrapper` C++ class — independently confirmed present during test design by
inspecting (read-only `strings`/`grep`, never executed) the installed QGIS-LTR 3.34 framework
binaries on the test-designer's machine, which also show the human-facing labels `"QML Widget"`/
`"QML Code"` and the `setQmlCode()` method matching FR-QPB-101's QML-source-configuration need.
This project's own already-implemented code (`qgis_worker.py`) establishes a working, confirmed
naming pattern for these registered ID strings: `QgsRelationReferenceWidgetWrapper` ->
`"RelationReference"`, and the "Attachment" widget maps to `"ExternalResource"` — both already
used successfully in this exact codebase. By the same `Qgs<X>WidgetWrapper` -> `"<X>"` pattern,
`QgsQmlWidgetWrapper` implies the registered ID `"Qml"`, but this specific inference was **not**
independently confirmed against a live QGIS editor-widget-registry query (this project's hard
QGIS-isolation rule bars the test-designer from constructing a `QgsApplication` for any reason,
including this one) or a canonical QField/QGIS document listing it verbatim. Rather than the
acceptance tests hardcoding a literal string inferred this way, `inspect_identification_widget`
itself (implemented by someone with real PyQGIS runtime access) is responsible for recognizing
whichever the true registered type string is; the tests only assert on the booleans above.

### 11. `run_ktsn_reference_pipeline(csv_path: str, xlsx_path: str | None = None, through_step: int = 5) -> dict`

> Added by a later `test-designer` round (2026-08-23) covering Decision Log D-48's five-step
> KTSN reference-table row-filtering pipeline (FR-QPB-118, further revised, complete five-step
> form) and the acceptance criteria it makes independently testable: AC-QPB-084 (Step 1),
> AC-QPB-085 (Step 2), AC-QPB-087 (Step 3), AC-QPB-086 (Step 4), plus the updated AC-QPB-071/
> AC-QPB-083 (the full five-step pipeline's final bundled output).

A **pure-Python reference implementation of FR-QPB-118 (further revised; Decision Log D-48)'s
five ordered row-filtering/extraction steps**, run directly against a given CSV (and, from Step 4
onward, an xlsx workbook), independently of `build_project()`'s full generated-project pipeline.
This exists for exactly the same reason function 9 (`match_ktsn`) does: some of this criterion's
own required assertions (e.g. AC-QPB-084's "when Step 1's filtering runs against \[the real, full
source CSV\] in isolation, then it produces exactly 32,251 surviving rows") are about an
*intermediate* stage of a five-step pipeline that `build_project()`'s own contract only ever
exposes the *final* (Step 5, fully bundled) output of — there is no way to observe "only Steps 1-2
have run" through `build_project()`/the bundled `reference/ktsn_lookup.csv` alone, since Steps 3-5
would already have reduced it further by the time a generated project can be inspected. This
function is the mechanism that makes each step's own row count and inclusion/exclusion rules
independently observable and testable, mirroring this same round's real, full-CSV/full-xlsx
verification wherever the criterion's own wording requires it (AC-QPB-084/085/087's "given the
real, full source CSV..." clauses; AC-QPB-086's "given the real NIBR xlsx workbook's `관속식물류`
sheet..." clause), while also supporting small, synthetic, fast fixtures for each step's own
edge-case rules.

**Unlike function 9, this is not merely validating a rule that will ship as QML** — Decision Log
D-48's own text is explicit that "this filter is computed once, at build time,... entirely in pure
Python within `reference_bundle.py`'s build-time extraction step, and **never** at runtime
on-device." This function's real, shipped counterpart is therefore expected to be an ordinary,
desktop-build-time Python function (unlike `match_ktsn`/`build_plantnet_identify_request`, which
describe QML-runtime rules this project has no way to execute directly) — `build_project()`'s own
`reference/ktsn_lookup.csv` output (via `bundle_reference_data()`/`_extract_ktsn_lookup_csv()` in
`qfield_builder/reference_bundle.py`, as of this round's authoring, pre-D-48) is expected to
become the actual caller of whatever internal implementation backs this same five-step logic.
This function is a thin, test-only wrapper the implementer is free to build directly on top of
that same internal logic — it does not need a second, independent implementation of the five
steps, only a Python entry point that exposes intermediate stages for testing.

**Parameters:**

- `csv_path`: path to a KTSN reference CSV in the same column shape as
  `storage/reference/tables/tb_leco_nib_ktsn_dtl_gat.csv` — at minimum, a header row naming
  `ktsn`, `p_ktsn`, `rank_id`, `r200_nm`, `taxon_full_nm`, `taxon_kor_nm`, `taxon_jm_nm`, and
  `correct_list` (a fixture CSV used only for an early-step test does not need every one of the
  real file's ~50 columns, only these 8 plus whichever of FR-QPB-105's 5 required columns are not
  already in that list).
- `xlsx_path`: path to a workbook in the same shape as
  `storage/reference/tables/2025년 국가생물종목록_v1.0.xlsx`, specifically containing a sheet
  named exactly `관속식물류` whose **row 1** contains a cell with the literal text `학명`
  identifying the scientific-name column (confirmed, by direct inspection of the real workbook
  during this round's test design, to be at column index 26/column `AA` in the real file — an
  implementation may hardcode that confirmed real-file offset, mirroring
  `reference_bundle.py`'s own existing `NATIONAL_LIST_XLSX_DATA_START_ROW = 3` convention for the
  sibling `62,604종` sheet, or locate it by scanning row 1 for the literal `학명` header cell;
  both are conformant, since both correctly locate the same column in the real workbook), a `KTSN`
  value in **column A** (index 0) of the same row, and data rows starting at **row 3** (rows 1-2
  are header/metadata rows in the real workbook, confirmed by direct inspection). Required
  (must not be `None`, and must resolve to a sheet/columns in this shape) whenever
  `through_step >= 4`; ignored when `through_step <= 3`.
- `through_step`: an integer from 1 to 5 inclusive, selecting how many of the five ordered steps
  (Step 1 Plantae-subtree filter; Step 2 `rank_id >= 700` filter; Step 3 seven-phylum
  vascular-plant allowlist; Step 4 duplicate-scientific-name canonical-KTSN resolution; Step 5
  column extraction) to run, in order, stopping after the named step.

**Returns** `{"rows": [...], "row_count": int}`.

- When `through_step < 5`: each element of `rows` is a `dict` keyed by **every** column name
  present in `csv_path`'s own header row (i.e. the row survives with all of its original source
  columns intact, unreduced — Step 5's column projection has not run yet). This is what lets a
  test assert, e.g., "every surviving row's `rank_id` parses as an integer `>= 700`" after Step 2,
  or "every surviving row's `r200_nm` is one of the seven allowlisted phyla" after Step 3 —
  properties that are no longer observable once Step 5 has reduced a row to only its 5 lookup
  columns.
- When `through_step == 5`: each element of `rows` is a `dict` keyed by exactly the 5 lookup
  columns (`ktsn`, `taxon_full_nm`, `taxon_kor_nm`, `taxon_jm_nm`, `correct_list`, in that order),
  identical in content to what `reference/ktsn_lookup.csv` would contain for this same
  `csv_path`/`xlsx_path` pair via `build_project()`.
- `row_count` is always `len(rows)`.

**Step semantics (restating Decision Log D-48/FR-QPB-118 precisely, since this is the contract
the tests assert against):**

- **Step 1:** a row survives iff, starting from its own `p_ktsn` value and repeatedly looking up
  the next row by treating each `p_ktsn` value as another row's `ktsn`, the chain reaches the
  literal string `"120000098391"` in a finite number of hops. A chain that terminates (an empty/
  blank/absent `p_ktsn` before reaching `120000098391`), that is broken (a `p_ktsn` value that does
  not match any row's own `ktsn` in the same file), or that cycles back on itself without ever
  reaching `120000098391`, excludes the row. The row whose own `ktsn` literally equals
  `"120000098391"` is not itself required to exist in `csv_path` (it does not, in the real
  species-detail table) and is never itself "surviving" by this rule alone — only rows that
  reach it via at least one `p_ktsn` hop do.
- **Step 2:** of the rows surviving Step 1, a row survives iff its own `rank_id` value parses as
  a base-10 integer that is `>= 700`. A missing, blank, or non-integer-parsing `rank_id` excludes
  the row.
- **Step 3:** of the rows surviving Step 2, a row survives iff its own `r200_nm` value is exactly
  one of `Magnoliophyta`, `Pteridophyta`, `Pinophyta`, `Filicophyta`, `Lycopodiophyta`,
  `Psilophyta`, `Sphenophyta`. A missing or blank `r200_nm` excludes the row. **See this round's
  traceability-file ambiguity note regarding a small number of real-file rows whose `r200_nm`
  value carries stray literal quote characters as an apparent upstream data artifact — this
  contract states only the literal seven-value match FR-QPB-118's own text requires; no additional
  normalization beyond that is specified here.**
- **Step 4:** of the rows surviving Step 3, group by `taxon_full_nm` after removing literal
  `<em>`/`</em>` tags and collapsing/trimming whitespace (identical to `qfield_builder.ktsn_match`'s
  `_normalize`/`_EM_TAG_RE`). Groups of size 1 survive unchanged. For a group of size `> 1`: look up
  the same normalized name (after applying the identical `<em>`-stripping/whitespace normalization
  to the xlsx's own `학명` values) in `xlsx_path`'s `관속식물류` sheet; collect the distinct `KTSN`
  values (coerced to string for comparison, since `openpyxl` may read a numeric-looking `KTSN`
  cell as an `int`/`float`) found for that normalized name. If exactly one distinct `KTSN` value is
  found, **and** it equals one of the group's own rows' `ktsn` values, keep only that one row (drop
  the other(s)); in every other case (name absent from the sheet; more than one distinct `KTSN`
  value found; or the one value found matches none of the group's own `ktsn` values), drop the
  entire group (zero rows survive for that name) — never a fallback tie-break of any kind.
- **Step 5:** of the rows surviving Step 4, project each row down to exactly the 5 columns
  `ktsn`, `taxon_full_nm`, `taxon_kor_nm`, `taxon_jm_nm`, `correct_list`, verbatim (no
  reformatting/renormalization beyond the projection itself — mirrors
  `reference_bundle._extract_ktsn_lookup_csv`'s existing, already-implemented, pre-D-48 behavior).

**Failure modes:** this function assumes `csv_path` already exists and passes FR-QPB-105's
required-column validation, and (when `through_step >= 4`) that `xlsx_path` exists and its
`관속식물류` sheet/columns are well-formed — callers needing to exercise FR-QPB-105's/FR-QPB-118's
own early-failure error envelope (missing/malformed source CSV; missing/malformed NIBR xlsx) use
the existing, separate `build_project()`-based failure-mode tests instead (this function is not
required to reproduce `build_project()`'s own user-facing error-message contract). Reasonable
failure behavior for a genuinely missing/malformed input (e.g. raising `FileNotFoundError`/
`ValueError`) is left to the implementer; no test in this round asserts a specific exception type
or message from this function.

### `build_project` config additions for this round

## Post-MVP: Decision Log D-95 canonical KTSN workbook harness additions

> Added by the clean-room test-designer round for the approved D-95 canonical-reference
> migration. These seams expose validation and pure data-contract behavior without prescribing
> the production module layout. The canonical workbook is read from the repository as a
> read-only fixture by the tests; temporary `.xlsx` files are created only inside a test's
> temporary directory for upload and failure cases.

### 21. `inspect_ktsn_source_candidates(reference_tables_dir: str, upload_path: str | None = None, confirmed_path: str | None = None, sample_limit: int = 3) -> dict`

Headless equivalent of the wizard's D-95 source-confirmation step. It must enumerate `.xlsx`
files afresh on each call under `reference_tables_dir` (never directory order or a stale cache),
and must not enumerate the legacy CSV as a candidate. The exact canonical filename is the
recommended candidate when present, but `selected` remains `None` and `can_continue` remains
`False` until a validated path is explicitly passed as `confirmed_path`.

Each `candidates` entry contains at least `filename`, `extension`, `sheet_name`, `header_rows`,
`sample_rows`, `validation_status`, and `source_kind`. `sample_rows` is bounded by
`sample_limit` and exposes at least `status`, `scientific_name`, `korean_name`, and extracted
string `ktsn`. The result contains `recommended_filename`, `selected`, `candidates`, and
`can_continue`. A legacy/mismatched workbook may be listed for user review but cannot be selected
as valid or silently used as a fallback. When `upload_path` is provided, `upload` has the same
preview/validation shape and `source_kind == "user_upload"`; an upload also requires explicit
confirmation. Missing candidates, invalid extension, or invalid workbook must produce an
actionable error and `can_continue == False`.

### 22. `ingest_canonical_workbook(workbook_path: str, source_kind: str = "bundled_candidate", expected_sha256: str | None = None) -> dict`

Runs the complete D-95 canonical workbook validation/materialization contract without creating a
project. On success it returns `success`, `sheet_name`, `header_rows`, `data_start_row`,
`source_columns`, `logical_columns`, `taxon_groups`, `row_count`, `accepted_count`,
`synonym_count`, `rows`, and `provenance`. `rows` are ordered by workbook source row and use the
DR-QPB-079 logical fields, including all five rank pairs, raw `scientific_name`, derived
normalization/authority fields, `accepted_ktsn`, original `source_url`, and 1-based
`source_row`. KTSN and source No values are strings (`No == "-"` is retained for synonyms).

For the real `Rpt_2026-08-29_List.xlsx` fixture the success result must report `Data Sheet`,
header rows `[1, 2]`, data start row `3`, 8,042 rows, 4,673 accepted rows, and 3,369 synonym
rows. All rows must be `관속식물류`; the two-level header is metadata, not a data row. A synonym
belongs to the most recent preceding accepted row, and its own KTSN/raw name/URL remain distinct.

On invalid or missing input it returns `success == False`, nonempty `error_code` and
`error_message`, no `partial_rows`, and no promoted project. It accepts `.xlsx` only, does not
execute formulas/macros, rejects missing required columns/subcolumns, non-vascular groups,
invalid status/No transitions, orphan synonyms, malformed or duplicate URL/KTSN identities, and
invalid URL prefix/remainder.

When `expected_sha256` is supplied, it is the hash captured at source confirmation. A mismatch
must return the same fail-closed error envelope rather than ingesting, reusing, or promoting the
changed source.

`provenance` must contain `source_filename`, `source_kind`, `sha256`, `byte_size`, selection
timestamp, `sheet_name`, `header_rows`, `data_start_row`, schema/pipeline revisions, source-row
count, accepted/synonym counts, and validation result. It must not contain workbook rows,
secrets, or an invented semantic dataset version.

### 23. `normalize_canonical_scientific_name(value: str) -> dict` and `extract_canonical_ktsn(url: str) -> dict`

These are pure seams for the exact R-equivalent transformation in Section 13.3a. The normalizer
returns exactly `scientific_name_normalized`, `scientific_name_without_authority`, and `authority`:
collapse whitespace; normalize spaces immediately inside/around parentheses; trim; remove the
first genus token before authority detection; then begin authority at the first whitespace-
preceded uppercase letter or `(`. If no marker exists, authority is the empty string and the
normalized full name is the comparison key. The input raw cell is not returned as a replacement
for the source value and must remain preserved by ingestion.

The URL seam removes only the literal prefix
`https://species.nibr.go.kr/species-detail/`, returns the original `source_url`, and returns the
nonblank remainder as a string `ktsn`. Any other prefix, empty remainder, or duplicate KTSN is a
fatal ingestion error.

### 24. `match_canonical_ktsn(scientific_name_without_authority: str, rows: list[dict]) -> dict`

Pure reference seam for FR-QPB-142. It matches exactly on
`scientific_name_without_authority` across accepted and synonym rows. A synonym resolves to its
row's `accepted_ktsn`, and the selected scientific value is the accepted row's preserved raw
`scientific_name` (authority included). A comparison-key collision across distinct accepted
groups returns `ambiguous == True` and leaves accepted/selected values unset; it never guesses.
The return shape includes at least `matched`, `matched_ktsn`, `taxon_status`, `accepted_ktsn`,
`selected_korean_name`, `selected_scientific_name`, and
`selected_scientific_name_without_authority`.

### 25. `inspect_canonical_reference_layers(project_dir: str) -> dict`

PyQGIS-backed inspection seam for AC-QPB-140. It returns entries named
`ktsn_taxonomy_reference` and `ktsn_accepted_name_lookup`, each with at least `display_name`,
`fields`, `row_count`, `read_only`, `identifiable`, and `indexes`, plus `reference_group` in
layer-tree order. The taxonomy table must expose the DR-QPB-079 logical schema and all supplied
Phylum/Class/Order/Family/Genus scientific/Korean values; the accepted table contains only
`정명` rows and remains a compatibility projection, not a second source of truth.

### 26. `aggregate_taxonomy_report(observations: list[dict], taxonomy_rows: list[dict] | None, survey_type: str) -> dict`

Pure report-contract seam for FR-QPB-141. For Types 1–3 it resolves synonym KTSNs through
`accepted_ktsn` exactly once, counts distinct observation records before the reference lookup,
and returns one bucket per `(rank, scientific_name, korean_name)` with at least
`observation_count` and `distinct_ktsn_count`. Missing/blank/ambiguous KTSN or rank labels retain
the ordinary observation and produce a limitation; they do not abort. Type 4 returns no taxonomy
aggregation and marks it `not_applicable`. `taxonomy_rows is None` models an old project without
the new table: ordinary report data is retained and `taxonomy_reference_unavailable` is emitted;
the seam must not read a legacy CSV implicitly.

### Existing `build_project` config additions (continued)

- `identification_enabled` (bool) — already documented above (MVP section); reused unchanged.
  Set `True` to exercise FR-QPB-100/101/112's generation paths.
- ~~No `plantnet_api_key` build-time config field exists, deliberately: FR-QPB-079 requires that no
  generated-project artifact ever contain the Pl@ntNet key in any form (unlike the one narrow,
  consent-gated VWorld online-layer exception, FR-QPB-073). The key is a QField-runtime-entered
  secret (per FR-QPB-039/FR-QPB-101's "request permission... before activation"), never a
  build-pipeline input.~~ — **superseded, not deleted; see the new "Post-MVP: Decision Log D-45"
  section below.** Decision Log D-45 explicitly supersedes FR-QPB-079's original blanket exclusion
  for this one, narrowly scoped, consent-gated Pl@ntNet-key-embedding case (FR-QPB-114–117), so a
  build-time config surface for it is now required to make AC-QPB-079–082 testable.
- `_test_reference_data_dir` (str, optional test-only hook, new): if set, `build_project` must use
  this directory in place of the configured `REFERENCE_DATA_DIR` (`.env.example`) when resolving
  the KTSN CSV/probability-raster reference assets (FR-QPB-105/FR-QPB-112), expecting the same
  `<dir>/tables/tb_leco_nib_ktsn_dtl_gat.csv` / `<dir>/rasters/bce_inverse_corrected_probability_maps/*.tif`
  layout as the real `storage/reference/` scaffold. This lets tests exercise FR-QPB-105's missing/
  malformed-CSV failure paths, and a fast bundling-*mechanism* check, without needing to read the
  full real ~247 MB dataset on every test run. AC-QPB-071's own "matches the source scaffold's
  copies in full" claim is still verified separately, once, directly against the real
  `storage/reference/` location (no override), per the task's explicit instruction not to
  substitute a cropped/partial dataset for that specific claim.
- **`_test_reference_data_dir` addendum (Decision Log D-48, 2026-08-23):** because Step 4 of
  FR-QPB-118 (further revised)'s five-step pipeline depends on the same NIBR xlsx workbook
  already required by FR-QPB-113/Decision Log D-40/D-41 (`storage/reference/tables/
  2025년 국가생물종목록_v1.0.xlsx`), any `_test_reference_data_dir` override used for an
  `identification_enabled=True` build must now also provide a `<dir>/tables/
  2025년 국가생물종목록_v1.0.xlsx` file containing a well-formed `관속식물류` sheet (see function
  11 above), or the build must fail early exactly as FR-QPB-118 (further revised) itself requires
  when that dependency is missing/malformed. Every fixture directory this round's tests use for an
  identification-enabled `build_project()` call includes such a file (see the individual fixture
  directories under `fixtures/`); this addendum does not add a dedicated acceptance test asserting
  the xlsx-missing-therefore-Step-4-fails-early failure mode itself, since no AC-QPB-### number in
  this round's assigned scope names that specific failure path — see the traceability file's
  "Ambiguities / gaps found" section for this flagged, out-of-scope gap.

## Post-MVP: Decision Log D-45 (Pl@ntNet API key consent-gated embedding) harness additions

> Added by a later `test-designer` round (2026-08-18) covering FR-QPB-114–117/NFR-QPB-071/072
> (Section 13.1a/14.1) and AC-QPB-079–082 (Section 18.6), mirroring the existing VWorld
> online-layer consent-gated key-embedding exception (FR-QPB-073/076–078, Decision Log D-21) for
> the Pl@ntNet API key. This is a **build-pipeline artifact-generation concern** — whether/where
> the build pipeline writes the key into the generated project — of exactly the same kind already
> tested for VWorld in `test_basemap_online.py`; it is not itself QField/QML runtime behavior (the
> QML side's own `expression.evaluate("@qpb_plantnet_api_key")` read, and the manual-entry
> fallback prompt, remain out of this harness's reach, same as the rest of Section 13's QML-side
> behavior).

### `build_project` config addition: `plantnet` (dict, optional)

Mirrors the existing `basemap` online-mode shape (`vworld_api_key`/`consent_accepted`/
`remember_key`) for the Pl@ntNet key. Only meaningful when `identification_enabled` is `True`.

- `api_key` (str) — the Pl@ntNet API key, mirroring FR-QPB-117's wizard-collected secret input.
- `consent_accepted` (bool) — mirrors FR-QPB-076's VWorld consent-checkbox flag, but gates the
  new FR-QPB-115 Pl@ntNet-key-embedding consent step instead.
- `remember_key` (bool) — mirrors NFR-QPB-018's VWorld "Remember this key" flag, but governs
  NFR-QPB-072's Pl@ntNet local-retention persistence instead. **Wording note (Decision Log
  D-53, 2026-08-25):** NFR-QPB-018/NFR-QPB-072 were each revised so the desktop application's own
  local storage mechanism for a remembered key is no longer the OS credential store — this
  `remember_key` config field's *meaning* for `build_project()` (whether the build pipeline may
  ever write the plaintext key into the generated project either way — it must not, per
  FR-QPB-116/AC-QPB-079) is unaffected; only the stale "OS credential store" phrasing here is
  corrected. See
  `../qfield_project_builder_credential_storage_mechanism.traceability.md` for the full analysis
  of what this decision does and does not change at this harness's level.

When `consent_accepted` is `True`, `build_project` must set a QGIS project variable named exactly
`qpb_plantnet_api_key` on the generated `.qgs` project, holding the key (FR-QPB-114), and must not
write the key anywhere else in the generated project. When `consent_accepted` is `False`, the key
must not be embedded anywhere in the generated project (FR-QPB-116); the identification feature
(the `<project_slug>.qml` plugin and its embedded `QML Widget` action, FR-QPB-100/101) must still
be generated and present, unaffected.

**Reading the embedded project variable back out (test-only convention, not a new harness
function):** `.qgs` project variables are serialized by QGIS as a standard
`<properties><Variables><variableNames type="QStringList">`/`<variableValues type="QStringList">`
parallel-list XML shape — a documented fact about the `.qgs` container format itself (the same
class of format-level fact this suite's existing VWorld test already relies on for `&` ->
`&amp;` XML escaping), not an invented application behavior. `test_post_mvp_plantnet_key_embedding.
py`'s `_read_project_variables()` helper parses this directly with `xml.etree.ElementTree` rather
than a bespoke new `acceptance_api` function, consistent with this project's existing preference
for reading generated artifacts directly wherever they are themselves an inspectable standard
format (see this file's own opening rationale).

### MANIFEST.json: a second, independent boolean flag

NFR-QPB-071 requires a boolean security-warning flag for the Pl@ntNet embedding, independent of
the pre-existing VWorld online-layer flag (NFR-QPB-017) — a project may carry either, both, or
neither. As with the existing VWorld flag (see `test_ac057_manifest_contains_only_a_boolean_
security_warning_flag` in `test_basemap_online.py`), the exact JSON key name for either flag is
not specified anywhere in the approved specification, so these tests do not hardcode one; they
scan `MANIFEST.json`'s own flattened structure for boolean-valued keys whose path contains
`"security"`, `"credential"`, or `"warning"` (mirroring the existing convention exactly), and
additionally require the Pl@ntNet-specific flag's key path to contain `"plantnet"` — the only way
to test the "independent of the VWorld flag" half of NFR-QPB-071 at all is for the two flags to be
distinguishable by name, and `"plantnet"` is the most literal, spec-faithful name to look for
(mirroring the criterion's own wording, "the Pl@ntNet embedding").

## New (Decision Log D-56/D-57/D-58): Korean field-alias harness addition (AC-QPB-098)

> Added by a later `test-designer` round (2026-08-26) covering new DR-QPB-071 (Section 7), new
> FR-QPB-119 (Section 9, additively cross-referenced from FR-QPB-057), new Section 8.5 (the
> per-survey-type Korean field-alias table), and new AC-QPB-098 (Section 18.2) — Decision Log
> D-56 proposed the mapping, D-57 confirmed all ten originally-flagged Medium-confidence terms
> verbatim, and D-58 confirmed the one remaining open sub-question (the Type-3 `plot_id`
> foreign-key label's "고정" prefix) verbatim as well. Per Decision Log D-57's own "Approval
> status" line, Section 8.5's table is now fully stakeholder-confirmed and
> `test-designer`/`implementer` work may proceed against it, notwithstanding that
> DR-QPB-071/FR-QPB-119/AC-QPB-098's own inline requirement text was not itself textually edited
> and still literally reads "draft proposal, not yet stakeholder-approved" — Decision Log
> D-57/D-58 are explicit that only Section 8.5's own per-field confidence/status markers and the
> D-56 "Approval status" line change, not the requirement IDs' own body text.
>
> **Corrected by a later `test-designer` round (2026-08-26; Decision Log D-59).** The version of
> function 12's return-value description originally written by the round above incorrectly stated
> that `fid` (like geometry columns) is never a member of a real layer's `layer.fields()`. Decision
> Log D-59 confirms `fid` genuinely *is* a member of `layer.fields()` for every generated
> GeoPackage layer (it is a real physical OGC-required primary-key column), and that its exclusion
> from Section 8.5's alias proposal rests on a different, unrelated basis (the pre-existing
> `_build_drag_and_drop_form` form-tree mechanism) than geometry columns' genuine absence from
> `layer.fields()`. Function 12's description below, `conftest.py`'s `KOREAN_FIELD_ALIASES`
> docstring, and `test_korean_field_aliases.py::test_every_layer_field_is_accounted_for_by_
> exactly_one_alias_expectation` are all corrected accordingly by this same round; see
> `../qfield_project_builder_korean_field_aliases.traceability.md`'s own correction note for the
> full record of what changed and why.

### 12. `inspect_field_aliases(project_dir: str, layer_name: str) -> dict`

PyQGIS-backed (like `validate_project`/`inspect_identification_widget`), wraps
DR-QPB-071/FR-QPB-119/Section 8.5/AC-QPB-098. Opens the generated project through the same real,
headless QGIS/PyQGIS runtime those two functions already use, locates the named vector layer, and
reads back each of its fields' currently configured alias via QGIS's own field-alias mechanism —
the same mechanism FR-QPB-119 requires the build pipeline use to *set* the alias
(`QgsVectorLayer.setFieldAlias(index, alias)`).

Returns `{"field_names": list[str], "aliases": dict[str, str]}`.

- `field_names` is `[f.name() for f in layer.fields()]`, in the layer's own field order. Per
  Section 8.5's own scoping note, geometry columns are never modeled as a `ColumnDef`/`QgsField`
  at all and are therefore never members of `layer.fields()` in the first place — this function
  does not need to, and must not, filter them out itself; their absence from `field_names` is
  simply a fact about the layer's own field collection.
  **`fid` is different (corrected by Decision Log D-59, 2026-08-26 — an earlier version of this
  section incorrectly grouped `fid` together with geometry columns above; it does not belong in
  that group).** `fid` *is* a genuine member of `layer.fields()` for every generated GeoPackage
  layer — the OGC-required physical `"fid" INTEGER PRIMARY KEY AUTOINCREMENT` column (DR-QPB-002)
  — so `field_names` must include it, and this function must not filter it out either. It
  receives no Korean alias, but for a different, unrelated reason than the UUID primary key's own
  DR-QPB-071 "meaningless label for a field a surveyor never sees" reasoning: it is a non-domain
  physical key that Section 8.5's alias proposal simply does not assign one to, and it is
  separately excluded from the *visible* attribute-editor form tree by the pre-existing,
  unrelated `_build_drag_and_drop_form` mechanism (`qfield_builder/qgis_worker.py`). See Decision
  Log D-59 for the full correction record.
  This key exists so a test can assert the *complete* field set present on a layer independently
  of alias content (e.g. confirming no field is silently missing an alias expectation of any
  kind — the UUID primary-key's own "no alias" expectation, an in-scope field's specific
  confirmed-Korean-text expectation, or `fid`'s own distinct "present, no alias, out of
  DR-QPB-071/Section 8.5's proposal scope entirely" expectation).
- `aliases` has exactly one entry per name in `field_names`. The value is whatever
  `QgsVectorLayer.fields().field(<name>).alias()` (equivalently, `QgsField.alias()`) actually
  returns for that field, **not** `QgsVectorLayer.attributeDisplayName()`. This distinction is
  required, not stylistic: `QgsField.alias()` returns an empty string `""` when no alias has been
  explicitly set on that field, whereas `attributeDisplayName()`'s entire purpose is to *substitute
  the field's own name* as a display fallback when no alias is set — using the latter here would
  make an intentionally-unset alias (the UUID primary-key case, DR-QPB-071) indistinguishable from
  a set-but-coincidentally-identical-to-the-field-name alias, defeating AC-QPB-098's own explicit
  negative assertion ("it has no alias set"). Implementations must use the former.

**Why a dedicated harness function, rather than a raw `.qgs` XML regex (unlike AC-QPB-013's
`RelationReference` check).** QGIS project XML does have a well-known, long-standing per-layer
`<aliases>`/`<alias field="..." name="..." index="N"/>` block, and it was tempting to assert on it
directly the same way `test_qgis_project_config.py::test_ac013_foreign_key_field_uses_relation_
reference_widget` does for the `RelationReference` widget-type string. The test-designer did not
do this because, unlike `"RelationReference"` (a string this codebase's own already-working
`qgis_worker.py` code independently confirms is correct, cited directly in that test), the exact
`<aliases>` XML shape was not independently confirmed against a live QGIS instance during this
round — and this project's hard QGIS-isolation rule bars the test-designer from constructing a
`QgsApplication` for any verification purpose, including this one. Rather than hardcode a
possibly-wrong XML shape into an assertion, the judgment is delegated to this harness function's
own real-PyQGIS-backed implementation, mirroring the established precedent
`inspect_identification_widget` (function 10 above) already set for exactly this situation
(see that function's own "Exact editor-widget-type-string note").

## New (Decision Log D-64–D-69, 2026-08-26 stakeholder-decisions round) harness additions

> Added by a later `test-designer` round covering: `FR-QPB-106`/`FR-QPB-109` (further revised;
> Decision Log D-60/D-64, standardized `taxon_full_nm`-derived scientific name); `FR-QPB-011`
> (further revised)/`FR-QPB-120`/`FR-QPB-121`/new `FR-QPB-123`/`NFR-QPB-080` (Decision Log D-61/
> D-65, symbol styling + Tabler icon search/embedding); new `DR-QPB-072`/`FR-QPB-124`–`127`
> (Decision Log D-66/D-67/D-68, the bundled accepted-name lookup table, its `ValueRelation`
> widget, and the derived read-only `selected_scientific_name`/`selected_ktsn` fields);
> `FR-QPB-122` (Decision Log D-63/D-69, `ValueMap` widget for `identification_status`). New
> AC-QPB-099–108 (excluding the already-assigned AC-QPB-098, D-56/57/58's Korean-alias criterion)
> are covered by this round.

### `match_ktsn` (function 9) — new `direct_scientific_name` return key (Decision Log D-60/D-64)

FR-QPB-106 (revised) adds a `direct_scientific_name` value to the direct-match branch, mirroring
the existing `direct_korean_name` field exactly: the matched row's own `taxon_full_nm`, with
`<em>`/`</em>` tags removed, populated whenever a direct match is found (independent of whether
accepted-name resolution, FR-QPB-107, itself succeeds). `match_ktsn`'s existing return contract
(function 9 above) gains one new key:

- `direct_scientific_name: str | None` — the direct match's own `taxon_full_nm` with `<em>`/`</em>`
  tags removed, trimmed/whitespace-collapsed exactly like `accepted_scientific_name` already is;
  `None` when `direct_match_found` is `False`.

This is a purely additive extension to an already-existing pure-Python reference function — every
other key in `match_ktsn`'s return contract, and every existing rule, is unchanged. As with the
rest of function 9, this validates the *rule* against real data; the shipped mechanism is the QML
mirror (`qpbMatchKtsn`), which AC-QPB-099 (below) checks structurally instead.

### AC-QPB-099 — structural QML check only (no new harness function)

AC-QPB-099 itself names the QML functions to inspect (`qpbHandlePlantNetResponse`/`qpbMatchKtsn`/
`qpbSelectCandidate`) — this is covered by the existing `inspect_identification_widget()` (function
10)'s `qml_code` field, exactly like the existing `test_fr109_*`/`test_ac088_*`/`test_ac095_*`
structural checks in `test_post_mvp_identification_plugin.py`. No harness-contract change is
required for this criterion.

### New function 13: `fetch_tabler_icon_svg(icon_name: str) -> dict`

A **test-only, real-network-calling reference implementation**, used exclusively by the one
`network`-marked live test confirming Tabler's public SVG-source endpoint, mirroring the role
`call_plantnet_identify`/`qfield_builder.vworld.fetch_supported_layers` play for their own
respective live endpoints (function 8 above). Performs a real HTTPS GET for the named icon's SVG
file against Tabler's public source (`github.com/tabler/tabler-icons`, confirmed MIT-licensed, no
API key required — Decision Log D-65's orchestrator-confirmed research).

Returns `{"http_status": int, "content_type": str | None, "svg_text": str | None}`.

**Not independently re-verified live by this test-designer round** (unlike the VWorld/Pl@ntNet
precedent, where a prior round called the real endpoint itself with a real key during test design):
this round had no reason to spend a live network call confirming a no-auth, public static-file
host during authoring, and the exact download URL shape (e.g. whether it is
`raw.githubusercontent.com/tabler/tabler-icons/.../icons/outline/<name>.svg` or a different path
under the same repository) is therefore **not asserted as confirmed** by this contract — that is
implementer work to confirm and report back, exactly like FR-QPB-111's on-device-raster-sampling
caveat and FR-QPB-124's own disclosed five-result-cap caveat. The one `network`-marked test using
this function is written to assert only the *general shape* of a successful response (HTTP 200, an
`image/svg+xml`-family content type, and `svg_text` starting with `<svg` or `<?xml`), not a specific
URL template.

### New function 14: `search_bundled_tabler_icon_names(query: str) -> dict`

A **pure, offline, GUI-independent reference implementation of FR-QPB-121's client-side
filter-as-you-type logic** — performs no network I/O, mirroring `derive_project_slug`/
`estimate_offline_basemap_size`'s existing precedent for exposing wizard-adjacent pure logic
independently of the PySide6 GUI event loop this harness otherwise cannot reach (HARNESS_CONTRACT's
own "what these tests deliberately do not invent" list already excludes "UI widget/event names" —
this function exposes the underlying *filtering algorithm* only, not any UI event).

- Filters the real, build-time-bundled static index of Tabler icon names (Decision Log D-65: ~6,184
  names at time of research) by a simple case-insensitive substring/prefix match against `query`.
- Returns `{"matches": list[str], "total_bundled_names": int}`. `total_bundled_names` is the size of
  the complete bundled index, independent of `query` — used to confirm the index is real and
  non-trivial (not a stub/empty list) without hardcoding the exact confirmed count into a test
  assertion (that count may drift as Tabler's own icon set changes over time; unlike the KTSN
  reference CSV, this specification does not treat ~6,184 as a hard, must-match figure — Decision
  Log D-65's own text says "at time of research").
- Must never perform a network request of any kind — this is the offline half of FR-QPB-121;
  fetching a *selected* icon's SVG content (the one permitted network request, FR-QPB-011(d)) is a
  distinct, separate action from searching, covered instead by `build_project`'s `symbol_styling`
  config (below), not by this function.

### New function 15: `inspect_layer_renderer(project_dir: str, layer_name: str) -> dict`

PyQGIS-backed (like `validate_project`/`inspect_field_aliases`), wraps FR-QPB-120/FR-QPB-121/
AC-QPB-100/AC-QPB-101/AC-QPB-104. Opens the generated project through the same real, headless
QGIS/PyQGIS runtime those functions already use, locates the named vector layer, and reports a
small set of **semantic, derived** facts about its configured renderer/symbol — mirroring
`inspect_identification_widget`/`inspect_field_aliases`'s own established convention of returning
booleans/derived facts rather than raw internal QGIS config dicts or XML, so that the exact
internal QGIS symbol-layer-property key spelling (not independently confirmed against a live QGIS
instance by this test-designer round, for the same reason function 10's own note declines to
hardcode the "QML Widget" registered type string) is not baked into a test assertion:

Returns:

```
{
  "renderer_class": str,             # QGIS's own renderer class name, e.g. "QgsSingleSymbolRenderer",
                                      # "QgsRuleBasedRenderer"
  "symbol_layer_types": list[str],   # e.g. ["SimpleFill"], ["SimpleMarker"], ["SvgMarker"]
  "marker_shape": str | None,        # populated only when a "SimpleMarker" symbol layer is present,
                                      # e.g. "circle"
  "svg_relative_path": str | None,   # populated only when an "SvgMarker" symbol layer is present:
                                      # the project-relative path (relative to project_dir) the
                                      # marker symbol's SVG file reference resolves to
}
```

This function deliberately does **not** attempt to characterize an exact fill/outline color or
"is this deliberately configured vs. QGIS's own random default" as a boolean — FR-QPB-120's own
text does not mandate a specific color, and this test-designer round has no way to independently
confirm what QGIS's own unmodified default single-symbol color/outline actually looks like without
a live QGIS instance (the same hard QGIS-isolation rule that governs every other harness-design
choice in this file). Tests instead confirm the **structural** shape FR-QPB-120 does state
literally ("a single flat fill color plus a thin, contrasting outline" -> one `SimpleFill` symbol
layer, not a rule-based/categorized/graduated renderer, not a gradient/pattern fill; "a small,
solid circle marker" -> one `SimpleMarker` symbol layer with `marker_shape == "circle"`), mirroring
this suite's existing, comparably loose AC-QPB-015 renderer check (`test_geopackage_schema_by_type.
py::test_ac015_community_symbology_rule_exists_in_qgs_project`), not a pixel/color-exact check.

### New function 16: `inspect_editor_widget(project_dir: str, layer_name: str, field_name: str) -> dict`

PyQGIS-backed, wraps FR-QPB-122/FR-QPB-124/FR-QPB-125/AC-QPB-103/AC-QPB-105/AC-QPB-107. A
general-purpose editor-widget/default-value inspector, generalizing `inspect_field_aliases`'s own
established "delegate exact-QGIS-internals judgment to a real-PyQGIS-backed function, return
semantic derived facts" convention to widget *type*/*configuration* rather than only alias text —
used here instead of a raw `.qgs` XML regex (unlike AC-QPB-013's already-independently-confirmed
`"RelationReference"` regex) because neither `"ValueRelation"` nor the exact `QgsDefaultValue`/
`applyOnUpdate` XML serialization shape has been independently confirmed against a live QGIS
instance by this test-designer round (this project's hard QGIS-isolation rule bars constructing a
`QgsApplication` for that purpose, exactly as it already does for function 10's "QML Widget"
registered-ID-string case). `"ValueMap"` is already present in this codebase's own shipped
`_configure_widget_for_column` (the `organ` field), but is routed through this same function too,
for consistency, rather than cherry-picking which already-shipped widget strings get raw-regex
treatment and which get a dedicated function.

Returns:

```
{
  "widget_type": str,                      # QGIS's own registered editor-widget-type ID string,
                                            # exactly as configured (e.g. via
                                            # QgsEditorWidgetSetup.type()) — "" when no explicit
                                            # widget was ever configured (falls through to QGIS's
                                            # own plain default text-edit widget)
  "value_map": dict[str, str] | None,      # populated only when widget_type is the ValueMap widget:
                                            # the configured value -> display-label map
  "referenced_layer_name": str | None,     # populated only for a relation-backed widget
                                            # (ValueRelation/RelationReference): the QGIS layer
                                            # name/table the widget's own configuration points at
  "has_filter_or_completer_config": bool | None,  # populated only for a ValueRelation widget: True
                                            # iff the widget's own configuration enables a completer
                                            # and/or a non-empty filter expression (QGIS's
                                            # "UseCompleter"/"FilterExpression"-family ValueRelation
                                            # configuration)
  "default_value_expression": str | None,  # the field's configured QgsDefaultValue expression text,
                                            # or None if none is set
  "apply_on_update": bool | None,          # the field's configured QgsDefaultValue.applyOnUpdate
                                            # flag; None if no default value expression is set at all
  "is_read_only": bool | None,             # the field's own edit-form read-only flag
                                            # (QgsEditFormConfig.readOnly(idx))
}
```

### New function 17: `derive_accepted_name_lookup_table(csv_path: str, xlsx_path: str | None = None) -> dict`

A **pure-Python reference implementation of FR-QPB-126's row-derivation rule**, mirroring function
11 (`run_ktsn_reference_pipeline`)'s own "ordinary, desktop-build-time Python function, not
QML-runtime behavior" framing exactly — FR-QPB-126's own text is explicit that this filter, like
FR-QPB-118's, runs once, at build time, never on-device. This function (1) reuses the identical
Steps 1–4 computation `run_ktsn_reference_pipeline(csv_path, xlsx_path, through_step=4)` already
exposes (Plantae-kingdom-subtree filter; species-level-and-below rank filter; vascular-plants-only
phylum allowlist; duplicate-scientific-name canonical-KTSN resolution); then (2) applies the new
Step 5 this entry adds: keeping only rows whose `taxon_jm_nm` value is exactly `정명`, excluding a
row with a missing/blank `taxon_jm_nm` value; then (3) projects each surviving row down to exactly
3 columns.

Returns `{"rows": [{"ktsn": str, "taxon_kor_nm": str, "taxon_full_nm": str}], "row_count": int}`.

- `ktsn` is preserved as a string, exactly as `run_ktsn_reference_pipeline`'s own Step 4 output
  already preserves it (mirrors FR-QPB-118's own already-established string-preservation rule,
  DR-QPB-072's key column).
- `taxon_full_nm` has `<em>`/`</em>` tags removed (mirrors FR-QPB-106/107's existing tag-stripping
  rule, restated by FR-QPB-126).
- `taxon_kor_nm` is carried through verbatim from the source row (may legitimately be an empty
  string — the real reference CSV contains rows with a blank Korean name; FR-QPB-126 does not
  require a non-empty Korean name).

This is a test-only reference implementation of the *rule*; the real, shipped mechanism is expected
to be an ordinary build-time Python function inside `qfield_builder/reference_bundle.py` (or
equivalent), whose actual output is bundled into the generated GeoPackage as DR-QPB-072's table —
separately confirmed via `build_project()` (below), not only via this pure-Python function, exactly
mirroring the existing `match_ktsn`/QML-widget and `run_ktsn_reference_pipeline`/
`reference/ktsn_lookup.csv` "rule in Python, artifact via build_project" split this harness already
uses twice.

### `build_project` config/return additions for this round

- `symbol_styling` (dict, optional; Decision Log D-65) —
  - `mode`: `"minimalist"` (default when this key is omitted entirely) | `"tabler_icon"`.
  - when `"tabler_icon"`: `tabler_icon_name` (str, the icon selected from the offline bundled
    index) and `tabler_svg_fetch` (dict, **required** in this mode) —
    `{"fake": {"mode": "success" | "network_error" | "http_error" | "timeout", "svg_content": str}}`
    — a deterministic fault-injection double for the single SVG-fetch request FR-QPB-011(d)
    permits, mirroring the existing `basemap.tile_source.fake` convention exactly (function/config
    precedent already established in this harness for VWorld tile downloads). This is a test seam,
    analogous to dependency injection; it does not change the production default (a real fetch
    against Tabler's public source, exercised only by function 13's own standalone `network`-marked
    live test, never through `build_project` itself — mirroring how the real VWorld tile download is
    exercised via a separate `network`-marked path, not through `build_project`'s own fake-double
    tests).
  - `"mode": "success"` produces an on-disk SVG file the build embeds; `"network_error"`/
    `"http_error"`/`"timeout"` simulate a failed fetch, exercising FR-QPB-121's documented
    "generation is not blocked; the minimalist default remains in use" fallback.
- New return keys on `build_project`'s result dict —
  - `symbols_dir` (str | None) — the folder inside the generated project's own output where a
    downloaded Tabler icon's SVG file is embedded (e.g. a new `symbols/` subfolder of the project
    root, per FR-QPB-121's own example), when `symbol_styling.mode == "tabler_icon"` and the fetch
    succeeded; `None` when the minimalist default was used (no selection, offline, or a failed
    fetch).
  - `ktsn_lookup_table_name` (str | None; Decision Log D-66/D-67/D-68) — the actual GeoPackage
    table name the build pipeline used for DR-QPB-072's bundled accepted-name lookup table, for a
    Types 1–3 build; `None` for a Type 4 (`vegetation_mapping`) build (DR-QPB-072's own explicit
    Type 4 exclusion) or for a build that failed before reaching this stage. Exposed the same way
    `gpkg_path`/`qgs_path`/`attachments_dir`/`basemap_dir` already are, per this file's own
    top-of-document rationale (expose generated artifacts directly rather than inventing a bespoke
    inspection API), since DR-QPB-072/FR-QPB-126 do not mandate a specific literal table name.

**Flagged interaction, not silently resolved — `_test_reference_data_dir`/FR-QPB-127's
unconditional-bundling scope vs. this suite's own pre-existing `make_base_config()`/
`built_project_by_type()` fixture defaults.** FR-QPB-127 (Decision Log D-68) makes the accepted-name
lookup table's build-time derivation/bundling, and therefore FR-QPB-105's reused source-CSV
presence/required-column fail-early validation, run unconditionally for **every** Types 1–3 build —
independent of `identification_enabled`. This suite's own pre-existing `make_base_config()`
(`conftest.py`) and the `built_project_by_type`/`isolated_project_by_type` fixtures built on top of
it — used by dozens of already-approved MVP tests across this entire suite — default to
`identification_enabled=False` **and supply no `_test_reference_data_dir` override at all**,
meaning a Types 1–3 build made through those fixtures would, once FR-QPB-127 is implemented, resolve
reference data from the real, production-default `REFERENCE_DATA_DIR` location — gitignored,
machine-local data this repository's own existing fixtures (`real_ktsn_csv_path`/
`real_nibr_xlsx_path`/etc.) already document as "not guaranteed present on a fresh checkout." This
specification does not state whether the intended production default `REFERENCE_DATA_DIR` is meant
to always be present in every environment a Types 1–3 project can be built in (Decision Log D-44
confirms only that the *distributed, packaged* macOS application always bundles the complete
`storage/reference/` tree — a separate fact about release packaging, not about a developer/CI
working tree) — see this round's traceability file for the full ambiguity report. This round's own
new tests (below) avoid the ambiguity entirely by always passing an explicit
`_test_reference_data_dir` override (reusing the existing `REFERENCE_DATA_VALID_SAMPLE_DIR`
fixture); **no existing shared fixture default (`make_base_config`/`built_project_by_type`) is
changed by this round**, since doing so would silently pick a resolution to this open question
rather than reporting it.

**Addendum (Decision Log D-70, "Use Option (c)"; this housekeeping now performed by a later,
separate `test-designer` round):** the ambiguity above is resolved at the specification level —
this is a confirmed, accepted operational precondition, not a spec relaxation — and the
mechanical fixture-default housekeeping this section's own last sentence deferred has now been
done: `make_base_config()` (`conftest.py`) now includes a default `_test_reference_data_dir`
override pointing at `REFERENCE_DATA_VALID_SAMPLE_DIR`, so every Types 1-3 project built through
`make_base_config`/`built_project_by_type`/`isolated_project_by_type` with no explicit
per-test override now resolves reference data from that small, synthetic, always-present
scaffold, instead of the real, gitignored, production-default `REFERENCE_DATA_DIR`. This is a
no-op today (DR-QPB-072/FR-QPB-127's own build-pipeline code does not exist yet), verified by an
identical full-suite pass/fail comparison before and after this change (see this round's own
completion report for the exact counts).

**One genuine, identified interaction, flagged rather than silently fixed, per this round's own
explicit scope (shared fixture defaults only, not per-test files):**
`test_post_mvp_reference_bundling.py::test_ac071_full_real_reference_dataset_extraction_and_raster_bundling`
deliberately calls its own local `_build_with_identification` helper with no `reference_data_dir`
argument specifically so that helper's `if reference_data_dir is not None:` guard leaves
`_test_reference_data_dir` completely unset, so `build_project()` falls through to the real
production `REFERENCE_DATA_DIR` (guarded by the `real_ktsn_csv_path`/`real_probability_raster_dir`/
`real_nibr_xlsx_path` fixtures, which skip this test entirely on a machine lacking the real,
gitignored `storage/reference/` scaffold) — this is the one test that asserts the true, complete,
real-world 212,397 -> 20,914 row-count transformation end-to-end, and it does so specifically by
*not* overriding. Because that helper builds its config via `make_base_config("simple_inventory")`
internally, and `make_base_config()` now always sets `_test_reference_data_dir`, this helper's own
"no argument passed -> no override configured" assumption is no longer true: the key is now always
present (pointing at the small `REFERENCE_DATA_VALID_SAMPLE_DIR` sample) by the time
`build_project()` sees it, regardless of whether an explicit `reference_data_dir` argument was
passed to the helper. On a machine where the real `storage/reference/` scaffold is present (this
was confirmed true on the orchestrator's own local development machine, matching Decision Log
D-70's own text), this test's `assert len(lookup_rows) == 20_914` now fails, because it exercises
the small sample's few rows instead of the real dataset — a direct, fully understood consequence
of this round's own fixture-default change, not an unrelated regression, and not something this
round silently patches by editing that test file's own helper or assertion. **This is reported
here as an open item for a future round to resolve** (e.g., by having that one local helper
explicitly reset `config["_test_reference_data_dir"] = None` when no override argument is given,
restoring its original "no override -> real production default" behavior, since `build_project()`'s
own `_resolve_reference_data_dir()` already treats a falsy override the same as an absent one) —
not resolved by this round, which is scoped to the shared fixture default only.

## New (test-designer conformance-gap round, 2026-08-27): `check_runtime` manual QGIS-path-override extension (FR-QPB-008)

> Added by a later `test-designer` round confirming and closing a real, zero-coverage conformance
> gap against the already-approved MVP baseline. FR-QPB-008 (Section 5.2, Decision Log D-10)
> reads: "The application must attempt automatic detection of a supported QGIS installation, and
> must allow the user to select the QGIS installation path manually when automatic detection
> fails." No prior round ever implemented or tested the manual-override half of this requirement:
> `qfield_builder/runtime.py`'s own `_NON_TECHNICAL_MISSING_MESSAGE` already names a `'QGIS 설치
> 위치 선택...'` ("Select QGIS install location...") option verbatim, but as of this round no such
> option exists anywhere in the codebase (no UI control, and `detect_qgis_installation()`/
> `check_runtime()` accept no path-override parameter at all). This is a Category A conformance
> defect against an already-approved requirement (per this project's own change-control
> categories), not a specification change; the specification's own FR-QPB-008/FR-QPB-009 text is
> unchanged and is the sole source of the contract below. This section extends function 1's own
> pre-existing return-shape/`force_missing` contract additively, mirroring this file's own
> established convention for extending, rather than rewriting, an already-existing function's
> contract (see the `match_ktsn`/function 9 `direct_scientific_name` addendum above for the exact
> same pattern). New tests: `test_qgis_manual_path_override.py`. New traceability file:
> `../qfield_project_builder_qgis_manual_path_override.traceability.md`.

### Function 1 (`check_runtime`) — signature and return-shape extension

Extends the existing `check_runtime(force_missing: bool = False) -> dict` (documented above) to:

```
check_runtime(force_missing: bool = False, manual_path: str | None = None) -> dict
```

- **New parameter `manual_path`** (`str | None`, default `None`): a user-supplied filesystem path
  to a candidate QGIS Desktop installation directory, mirroring what a UI-collected "select QGIS
  install location" folder-picker result would be. An empty string must be treated identically to
  `None` (no override supplied) — a UI control whose folder-picker comes back empty/cancelled must
  never be treated as "the user selected `''` as their QGIS path."
- **Precedence, restating FR-QPB-008's own "manual...when automatic detection fails" wording
  precisely, since this is the contract the tests assert against:** automatic detection is always
  attempted first, exactly as today. If automatic detection already succeeds, `manual_path`
  (valid or not) must be ignored and `available: True` reported from the automatic result,
  unaffected — manual override is a fallback for when automatic detection has already failed, not
  a first-class replacement for it. Only when automatic detection fails is `manual_path` (if
  non-blank) consulted: the implementation must attempt to verify a genuinely working QGIS/PyQGIS
  environment specifically rooted at that path — the same kind of real, subprocess-based
  `qgis_bridge` verification `detect_qgis_installation()` already performs for its own standard
  per-OS candidate roots, never a "plausible directory exists" check alone, mirroring this
  module's own existing rule (restated verbatim from `runtime.py`'s own module docstring):
  "`available=True` is only ever reported once \[a real PyQGIS import\] confirmation has actually
  happened." On success: `available: True`. On failure (the path does not exist, is not a QGIS
  installation, or its PyQGIS environment does not actually import): `available: False`, with a
  message distinct from the generic no-installation-found message (see below).
- **`force_missing` (test-only seam, semantics clarified/extended, not changed for any existing
  caller):** when `manual_path` is not supplied (unchanged from today), `force_missing=True`
  continues to mean exactly what it always has — unconditionally report `{"available": False,
  "message": <the existing generic message>}`, regardless of the real host machine's own QGIS
  state. The pre-existing `test_missing_runtime_produces_a_clear_actionable_error_not_a_crash`
  test (`test_runtime_detection.py`) is unaffected by this extension and must continue to pass
  unmodified. When `manual_path` **is** also supplied, `force_missing=True` must instead mean
  "treat automatic detection as having failed, deterministically, regardless of the real host
  machine's own QGIS state, but still consult `manual_path` exactly as it would after a genuine
  automatic-detection failure" — this is what makes the manual-override mechanism's own effect
  independently, deterministically testable, isolated from whether the actual machine running the
  suite happens to already have a working QGIS install, mirroring the existing, already-approved
  `_test_force_missing_runtime` seam's role in `build_project()`.
- **New return key `qgis_prefix_path`** (`str | None`): the verified install path, surfacing the
  internal `RuntimeInfo.qgis_prefix_path` dataclass field `check_runtime()`'s own pre-existing
  implementation already computes internally but has never exposed through `RuntimeInfo.as_dict()`
  (see `runtime.py`). Present as a key in every return value; `None` whenever `available` is
  `False`, or when `available` is `True` via the "PyQGIS already importable in the current
  process" detection branch (which has no separate install directory to report); populated
  whenever `available` is `True` via a bridge-verified install (automatic or manual). This exists
  so a caller — and this round's own tests — can discover an already-verified real install path
  to use as a known-good manual-override target, since this harness has no way to fabricate a
  working fake QGIS installation directory (mirrors this file's own established "cannot simulate a
  fully working PyQGIS environment without a real one" rationale, already relied on by the
  existing `qgis`-marked `test_detected_qgis_344_lts_passes_verification_without_pip_installed_
  pyqgis` test).

### What these new tests deliberately do not invent

- The exact wording of the failure message shown for a rejected manual path (Korean text is an
  implementation-authored, domain-facing detail, per this file's own established convention
  elsewhere) — tests only assert it is non-blank, non-technical (no jargon), and distinct from the
  generic "no installation found anywhere" message already shown before any manual path was ever
  supplied.
- The literal on-screen wizard/error-dialog control ("a button," "a menu item," a folder-picker
  dialog's exact appearance) that lets a real user actually reach and invoke this mechanism —
  documented as a `manual`-marked placeholder instead (see the traceability file), mirroring this
  file's own established "wizard's own... sequencing as a literal, on-screen UI fact" exclusion
  (AC-QPB-104's placeholder) exactly.
- Whether the manual-path verification, when it fails, additionally reports *why* (e.g.
  distinguishing "path does not exist" from "path exists but is not a QGIS install" from "path is
  a QGIS install but PyQGIS itself does not import") via a structured `error_code`-style field —
  FR-QPB-009 only requires "a clear, non-technical error message," not a structured reason code,
  and no other `check_runtime()` failure path in this codebase has one either (unlike
  `build_project()`'s own `error_code`); this round does not invent one.

## New (test-designer round, 2026-08-27): root layer-tree group stacking order (Decision Log D-71, AC-QPB-110)

> Added by a later `test-designer` round covering FR-QPB-055 (revised; Decision Log D-71) and new
> AC-QPB-110 (Section 18.2): "Basemap" must be the last (highest-index) of the three required root
> layer-tree groups (`Survey data`, `Basemap`, `Reference`) within the root `QgsLayerTreeGroup`'s
> own `children()` order, so it renders beneath both other groups. New test:
> `test_qgis_project_config.py::test_ac110_basemap_group_is_last_of_the_three_required_root_groups_
> by_children_index`, parametrized across all four survey types.

**No new `acceptance_api` function.** As with `test_post_mvp_plantnet_key_embedding.py`'s
`_read_project_variables()` convention (see that section above), this criterion is checked by
parsing the generated `.qgs` XML directly with `xml.etree.ElementTree`, since the shape relied on
is a documented, confirmed fact about the `.qgs` container format itself, not an invented
application behavior. Confirmed by this round's own direct inspection of a real, freshly generated
project's `.qgs` output (via `build_project()`, never by constructing a `QgsApplication` directly):
the `<qgis>` root element has exactly one direct-child `<layer-tree-group>` element (the layer
tree's own root group, itself carrying no `name` attribute), whose own direct children include one
`<layer-tree-group name="...">` element per top-level group, in the same document order as that
group's real `QgsLayerTreeGroup.children()` index order. A layer loaded inside a group (e.g. the
KTSN lookup layer inside "Reference," DR-QPB-072) is serialized as a nested `<layer-tree-layer>`
element — a descendant of that group's own `<layer-tree-group>` element, not a direct child of the
*root* `<layer-tree-group>` — so scoping `ElementTree.findall("layer-tree-group")` to the root
group element alone (never `.//layer-tree-group`, which would also match nested groups) correctly
isolates just the three top-level groups this criterion is about. See the new test's own module
comment in `test_qgis_project_config.py` for the full rationale.

## New (test-designer round, 2026-08-28): Type 2/3 `observation_photo` removal (Decision Log D-74/D-78, AC-QPB-112/113/114)

> Added by a later `test-designer` round covering new `DR-QPB-074`-`DR-QPB-077` (Section 8.2/8.3),
> new `AC-QPB-112`/`AC-QPB-114` (Section 18.1), new `AC-QPB-113` (Section 18.6, post-MVP), and the
> narrowed `AC-QPB-009`: Type 2/3's `observation_photo` table (and its relation,
> `rel_observation_photo_observation`) is removed entirely, replaced by three inline photo-path
> columns on `observation` itself, mirroring Type 1's `inventory_observation` exactly. New file:
> `test_observation_photo_removal.py`. See
> `../qfield_project_builder_observation_photo_removal.traceability.md` for the full round record.

**No new `acceptance_api` function.** This round reuses three pre-existing harness functions
unchanged — `attempt_feature_save`/`validate_project` (functions 5/6), `inspect_editor_widget`
(function 16), and `inspect_identification_widget` (function 10, specifically its pre-existing
`qml_code` field) — plus direct `sqlite3` inspection of the generated GeoPackage and a plain
substring search against the generated `.qgs` project's own text for relation-ID presence/absence,
mirroring the identical "no new function needed, read the generated artifact's own inspectable
format directly" precedent the immediately preceding "root layer-tree group stacking order" section
above already set. The two attachment-path issue codes' documented conditions (`broken_attachment_
reference`/`invalid_attachment_path`, both above, in function 6's own section) were updated in
place to name Type 2/3's `observation`'s new columns alongside Type 1's already-documented
identical columns, since both codes' underlying mechanism is column-name-agnostic (any column with
`is_attachment_path=True`) and was already documented as applying to Type 1's columns before this
round.

## New (Decision Log D-73/D-77): Korean relation-widget display names (FR-QPB-128, Section 8.6, AC-QPB-111)

> Added by a later `test-designer` round covering new `FR-QPB-128` (Section 9) and new
> `AC-QPB-111` (Section 18.2): every relation embedded as a `QgsAttributeEditorRelation` widget in
> a parent record's own attribute form (FR-QPB-056/FR-QPB-057) must receive a Korean display name,
> set via the relation's own separate, human-facing "name" property (`QgsRelation.setName()`) —
> never its stable `id()` (`QgsRelation.setId()`), which remains completely unchanged and
> continues to govern every existing cross-reference. Section 8.6 records the specific,
> stakeholder-confirmed Korean name for each of the seven in-scope relations (Decision Log D-73
> proposed the mapping; Decision Log D-77 confirmed six of the seven exactly as proposed and
> corrected the seventh, `rel_observation_survey`: "관찰" → "식물관찰"). New file:
> `test_korean_relation_display_names.py`. See
> `../qfield_project_builder_korean_relation_display_names.traceability.md` for the full round
> record.

### New function 18: `inspect_relations(project_dir: str) -> dict`

PyQGIS-backed (like `inspect_field_aliases`/`inspect_editor_widget`, functions 12/16), wraps
FR-QPB-128/Section 8.6/AC-QPB-111. Opens the generated project through the same real, headless
QGIS/PyQGIS runtime those functions already use, and reads back every relation currently
registered on the project's own `QgsProject.relationManager()` — the same manager
`_add_relations()` (`qfield_builder/qgis_worker.py`) already populates one relation into, per
foreign key (FR-QPB-056), and the same manager `_build_drag_and_drop_form()` looks up by ID to
embed a `QgsAttributeEditorRelation` widget into each parent's own form.

Returns:

```
{
  "relation_ids": list[str],  # every relation ID currently present in the project — i.e. every
                              # key of project.relationManager().relations() — unaffected in
                              # substance by FR-QPB-128, which changes only a relation's name(),
                              # never which relations exist or their own id()
  "names": dict[str, str],   # relation_id -> that same relation's own QgsRelation.name(), exactly
                              # as currently configured: the human-facing "display name" property
                              # FR-QPB-128 requires be a Korean-language name (Section 8.6) instead
                              # of the raw relation-ID string it is identical to today
                              # (`relation.setName(fk.relation_id)`, `qgis_worker.py`'s
                              # `_add_relations()`)
}
```

- `relation_ids` and the keys of `names` are the same set — one entry per relation currently
  registered on the project, keyed by the relation's own `id()` (also the dict key
  `QgsRelationManager.relations()` itself already uses, so no separate lookup-by-ID step can
  introduce a mismatch between the two).
- This function deliberately reports **every** relation present on the project, not only the
  relations Section 8.6 names — mirroring `inspect_field_aliases`'s own established "report the
  complete set, let the test decide what's in/out of scope" convention (function 12) — so a test
  can independently confirm the complete relation-ID set is unaffected by this requirement, not
  merely that the specific relations this round happened to enumerate look right.

**Why a dedicated harness function, rather than a raw `.qgs` XML regex (mirrors function 12's
identical rationale, unlike AC-QPB-013's `RelationReference` check).** QGIS project XML does have
a well-known `<relations><relation id="..." name="..." .../></relations>` block, and asserting on
it directly — the same way `test_ac013_foreign_key_field_uses_relation_reference_widget` already
asserts on the unrelated `"RelationReference"` widget-type string — was considered. It was not
done, for the same reason `inspect_field_aliases` was not built as a raw XML regex either: the
exact `<relations>` XML attribute-serialization shape was not independently confirmed against a
live QGIS instance during this round, and this project's hard QGIS-isolation rule bars the
test-designer from constructing a `QgsApplication` for any verification purpose, including this
one. The judgment is delegated instead to this harness function's own real-PyQGIS-backed
implementation, which reads `QgsRelation.id()`/`QgsRelation.name()` directly off the live
`QgsRelationManager` — the exact mechanism AC-QPB-111's own text names ("when each embedded
child-relation widget's underlying `QgsRelation` is inspected") — mirroring the established
`inspect_field_aliases`/`inspect_editor_widget` precedent.

**Disclosed caveat this function deliberately does not, and cannot, resolve (Decision Log
D-73/D-77; carried forward, unaffected by the Korean-terminology confirmation).** AC-QPB-111's own
text is explicit that it "asserts only the `QgsRelation` object's own configured `id()`/`name()`
values, independently of the disclosed, not-yet-verified question of exactly which mechanism
drives the widget's on-screen rendered label." `inspect_relations` reads `QgsRelation.name()`
directly — the most plausible, code-grounded mechanism Decision Log D-73 identifies — but whether
that value is actually what QGIS/QField paints on screen for the embedded widget, as opposed to
some other, not-yet-identified override, remains unconfirmed by this round and is out of scope for
every test built on this function. Confirming it is implementer-verification work to report back,
mirroring this project's existing convention for this class of uncertainty (Decision Log
D-36/FR-QPB-111). A `manual`/`device`-marked placeholder test records this explicitly (see the new
test file) rather than silently leaving it untested with no record at all.

## New (Decision Log D-80/D-84): Korean layer display names (DR-QPB-078, FR-QPB-130, Section 8.7, AC-QPB-118)

> Added by a later `test-designer` round covering new `DR-QPB-078` (Section 7) and new
> `FR-QPB-130` (Section 9) — Decision Log D-80 identified the gap (every generated domain
> survey-data layer must receive a Korean-language display name via `QgsMapLayer.setName()`,
> replacing the raw GeoPackage table name QGIS/QField otherwise shows) and proposed Section 8.7's
> per-survey-type Korean layer-display-name table plus a separate KTSN-lookup-layer "bonus row";
> Decision Log D-84 confirmed both tables in full — every row exactly as proposed, except `site`,
> corrected from "사이트" to "조사지" in all three of its occurrences (Types 2/3/4) — and, as a
> directly traceable consequence of that same confirmation, extended DR-QPB-078/FR-QPB-130/
> AC-QPB-118's own governed scope to also include the bundled KTSN accepted-name lookup table
> (DR-QPB-072), for every Types 1-3 project. New `AC-QPB-118` (Section 18.2) makes this criterion
> independently testable. New file: `test_korean_layer_display_names.py`. See
> `../qfield_project_builder_korean_layer_display_names.traceability.md` for the full round
> record.

### New function 19: `inspect_layer_names(project_dir: str) -> dict`

PyQGIS-backed (like `inspect_field_aliases`/`inspect_relations`, functions 12/18), wraps
DR-QPB-078/FR-QPB-130/Section 8.7/AC-QPB-118. Opens the generated project through the same real,
headless QGIS/PyQGIS runtime those functions already use, and reads back every GeoPackage-table-
backed layer's own currently configured name (`QgsMapLayer.name()`) — the property
`_add_domain_layers()`/`_add_ktsn_lookup_layer()` (`qfield_builder/qgis_worker.py`) currently leave
at the raw GeoPackage table name (via `QgsVectorLayer(uri, table_name, "ogr")`'s third constructor
argument, never subsequently overridden by a `.setName()` call) and this requirement requires be
set to the Section 8.7-confirmed Korean text instead.

Returns:

```
{
  "table_names": list[str],  # every underlying GeoPackage table name this project currently has a
                             # layer loaded for -- every domain layer (DR-QPB-078) and, for a
                             # Types 1-3 project, the KTSN accepted-name lookup layer (DR-QPB-072,
                             # Decision Log D-84's scope extension) -- parsed from each such
                             # layer's own OGR data source, not from the layer's own current
                             # `.name()`, which is exactly the property this requirement changes
                             # and therefore cannot be used as a stable lookup key (see rationale
                             # below)
  "names": dict[str, str],  # table_name -> that same layer's own currently configured
                             # QgsMapLayer.name(), exactly as currently configured
}
```

- `table_names` and the keys of `names` are the same set — one entry per GeoPackage-table-backed
  layer currently loaded on the project, keyed by the underlying table name, mirroring
  `inspect_relations`'s own "same set" convention for `relation_ids`/`names` (function 18).
- This function reports **every** GeoPackage-table-backed layer present on the project — every
  domain layer plus the KTSN lookup layer where present — not only the ones Section 8.7 happens to
  name, mirroring `inspect_field_aliases`/`inspect_relations`'s own established "report the
  complete set, let the test decide what's in/out of scope" convention (functions 12/18).
- Deliberately excludes any layer that is *not* backed by a real GeoPackage-table data source with
  a `layername=` connection parameter — in particular, the online/offline basemap layer (a
  WMTS/XYZ/raster-tile source, never a GeoPackage vector layer) is never a member of
  `table_names`/`names` at all, by construction, not by an explicit filter this function's own
  implementation must remember to apply. This naturally scopes the function's own output to
  exactly DR-QPB-078 (revised)/FR-QPB-130 (revised)/AC-QPB-118 (revised)'s own governed scope
  (every `TableDef`-backed domain layer, plus the KTSN lookup layer) without an explicit allowlist
  — Section 8.7's own explicit "not addressed by this proposal" carve-out (the basemap layer's own
  name; the three layer-tree group names, which are not layers at all) is therefore honored by
  this function's own natural scope, not by a special case this round had to invent.

**Why table names are identified via each layer's own data source, never via its current
`.name()` (unlike every pre-existing by-`layer_name`-parameter harness function, e.g.
`inspect_field_aliases`/`inspect_editor_widget`/`inspect_layer_renderer`, functions 12/15/16).**
Every one of those pre-existing functions takes a `layer_name: str` parameter and locates the
layer via `lyr.name() == layer_name` — safe only because, until this round's own requirement is
implemented, a layer's own name and its underlying table name are one and the same string. This
round's own requirement makes that no longer true: once a domain layer's own name becomes its
Section 8.7-confirmed Korean text, `lyr.name() == "site"` (for example) would never match again.
This function is therefore deliberately designed around each layer's own OGR **data source**
instead — the same connection-string convention this exact codebase's own `_add_domain_layers()`/
`_add_ktsn_lookup_layer()` already, confirmedly (by direct code reading — the same class of
"confirmed by reading this codebase's own already-working code" grounding this file's own top-of-
document rationale already uses for, e.g., the `"RelationReference"` widget-type string)
construct verbatim: `uri = f"{gpkg_path}|layername={table_name}"`. A real, working implementation
of this function is expected to recover each layer's own originating table name from that same
data-source string (e.g. via `layer.source()`/`layer.dataProvider().dataSourceUri()`, or QGIS's
own `QgsDataSourceUri` parsing helper for the OGR provider) — the exact parsing mechanism is left
to the implementer, mirroring this file's own established "delegate the exact QGIS-internals
judgment to a real-PyQGIS-backed function" convention (functions 12/16/18's own identical
rationale), since the specific API call that best recovers it was not independently confirmed
against a live QGIS instance during this round (this project's hard QGIS-isolation rule bars the
test-designer from constructing a `QgsApplication` for any verification purpose, including this
one).

**Flagged, not silently resolved: this same by-`.name()`-lookup problem already exists in three
pre-existing harness functions, and implementing this round's own requirement will surface it.**
See the traceability file's own "Flagged interaction with this suite's own pre-existing name-based
layer lookups" section for the full report — `inspect_field_aliases`/`inspect_editor_widget`/
`inspect_layer_renderer` (and the `_evaluate_default_values_after_setting_attribute_pyqgis`
test-support helper in `editor_widget_inspect.py`) all locate a layer via
`lyr.name() == layer_name`, and every existing caller across this suite passes the *raw table
name* as that argument. This round's own new `inspect_layer_names` function is deliberately immune
to this problem (see above), but does not fix the three pre-existing functions themselves, or the
dozens of existing tests that call them by table name — that is out of this round's own
`tests/acceptance/`-only scope (those three functions live in application source modules) and is
reported as a finding for a future round to address deliberately.

## New (Decision Log D-76): live Tabler icon preview-fetch during search (FR-QPB-011(d)(ii), NFR-QPB-080 clauses (5)-(8), AC-QPB-117)

> Added by a later `test-designer` round covering Decision Log D-76 — the stakeholder's explicit
> choice of Decision Log D-72's disclosed option (b) ("live per-result SVG fetch during search"),
> superseding one specific clause of the already-approved FR-QPB-011(d)/NFR-QPB-080 (Decision Log
> D-65) to permit a second, independently scoped, narrower network-fetch trigger: fetching preview
> SVG content, live, for the currently visible/matched results of an in-progress Step 6 icon
> search, debounced as the user types — never an unbounded background prefetch of the entire
> ~5,130-name bundled index, never for a result not currently rendered on screen. NFR-QPB-080
> gains new clauses (5)-(8) (User-Agent parity with the existing selection-fetch request;
> debouncing; bounded concurrency; graceful, non-blocking, non-crashing degradation on
> failure/offline). New `AC-QPB-117` (Section 18.2) makes the graceful-degradation half
> independently testable; `AC-QPB-101` is annotated (not altered in substance) to note the
> fetch-on-selection mechanism it already covers is now one of two independently permitted fetch
> triggers. See `../qfield_project_builder_tabler_icon_preview_fetch.traceability.md` for the full
> round record, including the routed `tests/unit/` contract table for the parts of this mechanism
> that are not reachable from this file's black-box, `tests/acceptance/`-only convention.

### New function 20: `fetch_tabler_icon_preview_svgs(icon_names: list[str], preview_svg_fetch: dict) -> dict`

A **pure, offline, GUI-independent reference implementation of the "fetch a preview SVG for each
of a given set of currently visible/matched icon names, degrading gracefully per name on failure"
logic** — mirrors `search_bundled_tabler_icon_names`'s (function 14) own precedent for exposing a
pure, GUI-independent piece of this feature's logic headlessly, independently of the PySide6
keystroke/debounce event this harness otherwise cannot reach, and mirrors
`resolve_svg_fetch`/`_fake_svg_fetch`'s own existing fake-double convention for the sibling
selection-fetch mechanism (`symbol_styling.tabler_svg_fetch.fake`).

**`preview_svg_fetch` is fake-double-only in this test-only harness function — there is no "real
network" mode, `preview_svg_fetch["fake"]` is always required.** This mirrors this suite's own
already-established convention (see `qfield_project_builder_symbol_styling.traceability.md`'s
"Design choices" note) that `build_project()`'s own `symbol_styling.tabler_svg_fetch` config is
likewise fake-double-only in every acceptance test — the real production dispatch mechanism (real
HTTP calls, real debounce timing, real bounded concurrency, the real compliant `User-Agent`
header) is implementer code exercised by the real wizard widget, not by this reference function.
The preview-fetch's real network destination is the identical Tabler public SVG source
`fetch_tabler_icon_svg` (function 13) already independently exercises for the sibling
selection-fetch trigger — no new live-network endpoint-shape confirmation is required for this
round; see this round's traceability file for why no new `network`-marked test is added.

`preview_svg_fetch["fake"]` shape:

```
{
  "default": {"mode": "success" | "network_error" | "http_error" | "timeout", "svg_content": str},
  "overrides": {              # optional
    "<icon_name>": {"mode": ..., "svg_content": str},   # same shape as "default", per-name
  },
}
```

`"default"` is applied to every name in `icon_names` not individually listed in `"overrides"`.
`mode`/`svg_content` have the identical meaning `_fake_svg_fetch`'s own `tabler_svg_fetch.fake`
convention already gives them (function 13/15's sibling selection-fetch double) — `"success"`
requires `svg_content`; the three failure modes ignore it. The `"overrides"` map is what lets a
test exercise "one visible result's preview fetch fails while a sibling result's own preview
succeeds" — directly exercising AC-QPB-117's own "a missing/failed preview must simply show no
image... for **that one result**" per-result granularity, not merely an all-or-nothing batch
outcome.

Returns:

```
{
  "requested_names": list[str],   # == icon_names, unchanged, unexpanded, in the same order --
                                   # confirms this function never silently expands its own fetch
                                   # scope beyond the exact names it was given (FR-QPB-011(d)(ii):
                                   # "never an unbounded background prefetch of the entire
                                   # ~5,130-name bundled index, and never fetched for a result
                                   # that is not currently visible on screen")
  "previews": {
    <icon_name>: {"success": bool, "svg_content": str | None, "error": str | None},
    ...   # exactly one entry per name in icon_names, always present regardless of that specific
          # name's own fetch outcome -- one name's failure never raises, never omits, and never
          # blocks any other name's own entry from being reported (AC-QPB-117's "never block
          # search, never block selection, never crash" applied at this function's own,
          # per-batch level)
  },
}
```

**Deliberately excluded from this function's own return contract: true concurrent-dispatch
behavior (NFR-QPB-080 clause (7)) and the debounce timing itself (clause (6)).** A synchronous,
fake-double-only reference function has no meaningful way to demonstrate *real* concurrent HTTP
dispatch (a thread-pool/async-task bound is only observable against a real, non-fake dispatch
mechanism) or *real* debounce timing (an inherently PySide6-`QTimer`/keystroke-event fact) — both
are, instead, fully specified in this round's own traceability file as a routed `tests/unit/`
contract, rather than invented here as a synthetic concurrency/timing model this reference
function's own fake double cannot actually exercise meaningfully. The same determination applies
to NFR-QPB-080 clause (5)'s `User-Agent` header requirement — an internal HTTP-client-construction
detail this suite has never been able to reach from any acceptance test, for either the existing
selection-fetch request (see the pre-existing "what these tests deliberately do not invent" bullet
below) or this new preview-fetch request; also routed to `tests/unit/`.

## New (Decision Log D-83/D-85/D-87): unconditional "Export HTML Report" project plugin (FR-QPB-038/090/100/133/134, AC-QPB-123–127)

> Added by a later `test-designer` round covering Decision Log D-83 (the stakeholder's direct
> instruction adding an "Export HTML Report" button to the `<project_slug>.qml` project-plugin
> sidecar, generating a standalone HTML project/schema-summary-plus-collected-field-data report on
> demand) and Decision Log D-85 (closing former Open Question O-40: the sidecar's own generation
> trigger was broadened), as further revised by approved Decision Log D-87. D-87 closes O-42 as
> **always present, no toggle**: every build emits the shared sidecar/report mechanism, while its
> identification reminder and write-back polling `Timer` remain conditional on
> `identification_enabled = true`. See
> `../qfield_project_builder_html_report_export.traceability.md` for the full mapping. Only O-41,
> the full-record GeoPackage-read-from-QML feasibility question, remains open.

### AC-QPB-123/124/125/127 — generated-sidecar checks only (no new harness function or config key)

Exactly like `AC-QPB-099`'s own precedent above, these criteria are covered by reading the
generated `<project_slug>.qml` project-plugin sidecar file directly off disk — the same file
`build_project()` (function 4) already writes, and the same file
`test_post_mvp_identification_plugin.py`'s own `test_ac069_*` tests and
`identification_project_plugin_source` fixture already read via
`Path(result["project_dir"]) / f"{slug}.qml"`. No `qfield_builder.acceptance_api` surface change is
required. The tests do not pass or define any report-enable field: D-87 expressly says none
exists. AC-QPB-123 runs all four survey types with identification both disabled and enabled;
AC-QPB-127 executes both identification-content branches and inspects the reminder/Timer boundary.

### AC-QPB-126 — manual/`device`-marked placeholder (no harness function; gated on Open Question O-41)

Whether the generated report's content actually reflects the project's real, current schema
summary and collected records requires a real device (or QGIS Desktop, subject to the existing
Decision Log D-46 rendering-scope caveat) and is additionally gated on Open Question O-41 (whether
QField's own QML execution context can enumerate/read an entire layer's worth of GeoPackage feature
data at all). Documented as a skipped `device`-marked placeholder in
`test_html_report_export.py`, mirroring `test_post_mvp_manual_qfield_runtime.py`'s established
convention.

### FR-QPB-038 regression premise revised by D-87

`test_post_mvp_identification_plugin.py` no longer asserts that identification-disabled builds
contain no `.qml` sidecar. Its replacement uses the same existing `build_project()` output and
asserts the D-87 boundary: slug-named sidecar and report mechanism present; identification reminder
and polling `Timer` absent. This preserves the negative FR-QPB-038 coverage without contradicting
unconditional FR-QPB-090/100/133.

## HTML report integrated follow-up hardening fixture renderer (AC-IRF-018–020)

The additive hardening suite uses one narrow, headless adapter:

### `render_html_report_fixture(fixture: dict) -> dict`

This adapter must execute the **same production column allocation, row projection, direct/fallback
limitation reporting, geometry normalization, FK-joined projection, source-row aggregation, map
feature selection, filter/sort, and CSV serialization paths used by the generated integrated HTML
report**. It may wrap or evaluate the generated sidecar/report code, but it must not implement a
parallel test-only version of those rules or manufacture expected snapshots. It must not construct
a `QgsApplication` in the acceptance-test process. If production execution requires QGIS, it must
use the suite's existing isolated bridge.

The input is a synthetic report fixture and may contain:

- `source_columns`: schema-ordered entries with `id`, `source_table`, `source_field`, and
  `schema_order`. Row `values` are keyed by `id`, so two logical columns remain distinguishable
  before final-key allocation.
- `source_rows`: entries with `source_row_id`, `values`, optional
  `established_fk_join_column_ids`, and optional geometry as
  `{"format": "wkt", "value": str}`. A missing key in `values` is genuinely absent; a present
  key with `None`, `0`, `False`, or `""` retains that distinct source value.
- `direct_access`: optional direct-path status, path label, and failure reason.
- `fallback`: optional loaded-layer fallback source, rows, known omissions, and unverifiable
  scopes. Unverifiable counts use `None`; the adapter must not coerce them to zero.
- `actions`: optional deterministic filter and sort actions, addressed by source-column ID.

The returned dictionary contains at least:

```text
{
  "success": bool,
  "error_message": str | None,
  "column_definitions": [
    {"source_column_id": str, "key": str, ...},
  ],
  "integrated_rows": [{"source_row_id": str, "values": dict}],
  "detail_rows": [{"source_row_id": str, "values": dict}],
  "payload_rows": [{"source_row_id": str, "values": dict}],
  "csv_text": str,
  "map_feature_ids": [str],
  "normalized_geometry_by_row": {str: GeoJSON_geometry | None},
  "invalid_geometries": [{"source_row_id": str, "reason": str}],
  "geometry_limitations": {"invalid_count": int, ...},
  "source_table_processing_succeeded": bool,
  "summary": {"source_row_count": int, ...},
  "charts": {"species_occurrence": {str: int}, ...},
  "filter_result_ids": [str],
  "sort_result_ids": [str],
  "fallback": {
    "used": bool,
    "source": str | None,
    "failed_direct_path": str | None,
  },
  "limitations": {
    "known_omissions": [{"kind": "table" | "row", "identifier": str}],
    "unverifiable_scopes": [
      {"identifier": str, "count": None, "completeness": "unknown"},
    ],
  },
  "limitation_notice_text": str,
  "inventory_status": str,
  "claims_complete_direct_inventory": bool,
}
```

Rows in the three projections and CSV are actual report-output rows, not a reflection of the
input dictionaries. `column_definitions` is the authoritative source-column-to-final-key mapping.
The map and normalized-geometry fields are parsed from actual map output; summaries/charts and
filter/sort IDs are produced by their real report paths. The notice text is the actual
user-visible limitation notice. Extra diagnostic fields are allowed, but they do not substitute
for any required observable result above.

For fixtures with no direct-access failure, fallback fields may report their inactive defaults.
For a direct-access failure, every known omission and unverifiable scope supplied by the actual
collection result must be represented both structurally and in `limitation_notice_text`. For a
successful valid Point ZM input, `normalized_geometry_by_row` contains two-dimensional GeoJSON
coordinates only. A malformed/non-finite X/Y input produces `None`, a stable invalid reason, and
no map feature even when its Z/M ordinates are valid.

## What these tests deliberately do *not* invent

- Internal module/class names, the IPC mechanism (O-1), UI widget/event names, or anything about
  the PySide6 wizard's own code structure.
- Exact QGIS/OS/GDAL/QField patch-version numbers (O-9) — see the traceability notes for
  AC-QPB-016/022/032, which are blocked on this open item rather than guessed.
- Any post-MVP (Pl@ntNet/KTSN/probability) behavior **except** the guaranteed-manual-baseline
  slice covered by this round (see the "Post-MVP: Section 13" section above): FR-QPB-100/101/104/
  106/107/112. FR-QPB-102 (automatic/silent identification) remains completely untested, by
  design — the spec itself defers it, and no test here implies it exists. FR-QPB-108/109/111's
  actual runtime behavior (as opposed to the pure-rule validation above) is QML-runtime-dependent
  and is documented as manual/`device` QA in `test_post_mvp_manual_qfield_runtime.py`, not
  invented as an automatable Python mechanism.
- Which single entry of a multi-entry `correct_list` JSON array is canonical (see function 9's
  "known, deliberately-uncovered specification gap" note).
- The exact registered QGIS editor-widget-type-ID string for "QML Widget" (see function 10's
  note) — inferred, not asserted as fact, and not hardcoded into a test assertion.
- The exact registered QGIS editor-widget-type-ID string for "ValueRelation," or the exact
  `QgsDefaultValue`/`applyOnUpdate` XML serialization shape (Decision Log D-66/D-67; see function 16's
  note) — delegated to a dedicated harness function's own real-PyQGIS-backed judgment, not hardcoded.
- Whether QGIS's/QField's actual `ValueRelation` widget implementation supports a live, as-you-type
  filter capped at exactly five displayed results (FR-QPB-124's own disclosed caveat) — tests check
  only that a filter/completer configuration exists, never that a specific five-result cap is
  enforced at runtime.
- The internal HTTP-client construction details of the single Tabler SVG-fetch request (whether it
  carries a compliant `User-Agent` header; whether it retries automatically on failure) —
  FR-QPB-011(d)/NFR-QPB-080's own safeguards for this. This is an internal desktop-application
  HTTP-client mechanism, not a generated-project artifact this harness's black-box convention can
  reach (no different in kind from Decision Log D-53/D-55's own credential-storage precedent, see
  `tests/acceptance/README.md`'s "Local credential-storage-mechanism change" section) — routed to
  the `implementer` role's own unit-test mandate, not this file's acceptance-test scope. See this
  round's traceability file for the full determination.
- The wizard's own Step 6/Step 7 sequencing as a literal, on-screen UI fact (AC-QPB-104's first
  clause) — a PySide6-wizard-UI-content fact, not a generated-project artifact or a pure,
  GUI-independent logic function (unlike FR-QPB-121's own offline search-filter logic, which
  function 14 does expose headlessly) — documented as a `manual`-marked placeholder instead, per
  this file's own "what these tests deliberately do not invent" precedent for UI widget/event facts.
- Genuine, live, cross-session confirmation that changing `selected_korean_name` on an existing,
  already-saved feature reopened later in a real running QGIS Desktop/QField session actually
  re-derives `selected_scientific_name`/`selected_ktsn` (FR-QPB-125's own "works identically... for
  an existing, already-saved feature reopened later" claim) — the underlying field-level
  configuration (`QgsDefaultValue`/`applyOnUpdate`/read-only) is structurally verified via function
  16 (and applies, by construction, identically to every feature of a layer, new or reopened, since
  it is layer-level configuration, not a per-feature/per-session mechanism); genuinely *exercising*
  QGIS's/QField's own live-default-value re-evaluation engine end-to-end requires a real, running
  editing session this harness cannot drive, and is documented as a `manual`-marked placeholder.
- The literal on-screen wizard/error-dialog control that lets a real user reach and invoke
  FR-QPB-008's manual QGIS-install-path override (a button, menu action, or folder-picker dialog
  reachable from the missing-runtime error state) — a PySide6-wizard-UI-content/reachability fact,
  not a generated-project artifact; the underlying verification logic it would call is instead
  exposed headlessly via `check_runtime(manual_path=...)` (see this file's own "New (test-designer
  conformance-gap round, 2026-08-27)" section) and tested directly. Documented as a
  `manual`-marked placeholder, mirroring the AC-QPB-104 precedent immediately above.
- Whether `QgsRelation.name()` is actually the mechanism QGIS/QField uses to paint the on-screen
  label of an embedded `QgsAttributeEditorRelation` widget (Decision Log D-73/D-77's own disclosed,
  not-yet-independently-verified caveat, carried forward unaffected by the Korean-terminology
  confirmation) — `inspect_relations` (function 18) and every test built on it check only the
  `QgsRelation` object's own configured `id()`/`name()` values, exactly as AC-QPB-111's own text
  scopes it; confirming the rendered label itself is documented as a `manual`/`device`-marked
  placeholder, mirroring Decision Log D-36/FR-QPB-111's identical convention for this class of
  uncertainty.
- The exact QGIS/PyQGIS API call (`layer.source()`, `layer.dataProvider().dataSourceUri()`,
  `QgsDataSourceUri` parsing, or otherwise) a real implementation of `inspect_layer_names`
  (function 19; Decision Log D-80/D-84) uses to recover a layer's own underlying GeoPackage table
  name from its data source — delegated to that harness function's own real-PyQGIS-backed
  implementation, not hardcoded, mirroring the established `inspect_field_aliases`/
  `inspect_relations` precedent.
- Whether/how the three pre-existing by-`layer_name`-parameter harness functions
  (`inspect_field_aliases`/`inspect_editor_widget`/`inspect_layer_renderer`) and their existing
  callers get updated once a domain layer's own name is no longer identical to its underlying
  table name (Decision Log D-80/D-84's own new requirement) — flagged as a real, identified
  interaction for a future round to resolve deliberately (see
  `../qfield_project_builder_korean_layer_display_names.traceability.md`'s "Flagged interaction..."
  section), not silently patched by this round.
- Whether the online/offline basemap layer's own name, or the three English-named root
  layer-tree *group* names (`Survey data`/`Basemap`/`Reference`, FR-QPB-055), should also receive
  Korean-language treatment — Section 8.7's own text explicitly leaves both undecided (Open
  Question O-39, narrowed but not closed by Decision Log D-84); this round's own negative-control
  test only confirms the group names are *currently* unaffected, and asserts nothing about whether
  they *should* be, one way or the other, in the future.
- The internal HTTP-client construction, debounce-timing, and concurrency-bounding mechanism of
  the new live preview-fetch request (Decision Log D-76; FR-QPB-011(d)(ii)/NFR-QPB-080 clauses
  (5)-(7)) — whether it carries the same compliant `User-Agent` header as the existing
  selection-fetch request; whether the real `SymbolStylingPage` debounces it (a `QTimer`/
  keystroke-event fact) rather than firing on every keystroke; whether its real dispatch mechanism
  bounds true concurrent in-flight requests to a small, reasonable number. Exactly the same class
  of internal desktop-application mechanism as the pre-existing bullet above for the sibling
  selection-fetch request (and, before that, Decision Log D-53/D-55's own credential-storage
  precedent) — not a generated-project artifact, and (for debounce/concurrency specifically) not
  even reachable via a synchronous fake double the way the selection-fetch's own `User-Agent`
  header at least conceivably could be with a real network call. Routed to the `implementer`
  role's own `tests/unit/` mandate in full; see this round's traceability file for the exact,
  fully specified contract table (`tests/unit/test_wizard.py`/`tests/unit/test_symbol_styling.py`).
  The one part of this new fetch trigger that *is* a pure, GUI-independent logic function — "given
  a set of currently visible/matched names, fetch each one's preview, degrading gracefully per
  name on failure, never expanding beyond the given set" — *is* exposed headlessly and *is* tested
  here, via new function 20 (`fetch_tabler_icon_preview_svgs`), mirroring function 14's own
  precedent exactly.
- Whether the real, on-screen Step 6 results list actually renders a visible image thumbnail next
  to each result once its preview fetch succeeds (as opposed to merely not crashing/blocking when
  it fails or is unavailable, which new `AC-QPB-117`/function 20 above do cover) — a literal,
  on-screen PySide6 rendering fact, not a generated-project artifact or a pure, GUI-independent
  logic function; documented as a `manual`-marked placeholder, mirroring the AC-QPB-104 precedent
  above.

## New (FieldBuild Standalone five-fix integration): exact display-expression inspection

The five-fix acceptance suite adds one narrow harness function:

### `inspect_display_expressions(project_dir: str) -> dict`

This function opens the generated project through the harness's existing isolated PyQGIS path and
returns:

```text
{"display_expressions": {"observation": str, "survey": str}}
```

`observation` is required for Type 2/3 projects and `survey` is required for Type 2/3/4 projects.
The function must inspect the actual configured QGIS layer display expressions, not source-code
constants or a test fixture. A missing layer/key is an implementation error for the applicable
survey type. The function must use the same isolation machinery as `build_project()` and must not
construct a QGIS application in the acceptance test process.

The acceptance tests compare the returned strings literally against the approved
`fieldbuild-kit-five-fixes` specification contracts; this function deliberately does not evaluate
the expressions or invent blank/NULL normalization.

## Post-MVP: single multiband occurrence-probability raster (AC-MPR-001–014)

The multiband acceptance slice adds five narrow, repository-isolated seams. These functions are
test-harness adapters, not additional product requirements; they may delegate to the production
build/runtime implementation or to an isolated inspection helper, but they must not silently
weaken validation or manufacture successful results.

### `validate_probability_raster_sources(source_dir: str) -> dict`

Validates the regular files in the supplied probability-map source directory against the
species filename pattern. The complete non-empty set of matching files is authoritative for
that invocation; there is no fixed expected species count. It returns at least:

```text
{
  "ok": bool,
  "error_code": str | None,
  "message": str,
  "discovered_species_count": int,
  "excluded_files": list[str],
}
```

On success, `discovered_species_count` is the number of matching regular files and is greater
than zero. The result must never treat
`bce_inverse_corrected_richness_5km_uncalibrated.tif` or another nonmatching file as a species
band. Missing/unreadable directories, zero matching files, and invalid discovered rasters fail
closed with a non-empty `error_code` and `message`; changing only the positive number of valid
matching files is not an error.

### `build_probability_stack(source_dir: str, project_dir: str) -> dict`

Builds the stack and band-index artifacts atomically beneath the supplied project directory. On
success it returns `success: True`, `stack_path` ending in
`reference/rasters/occurrence_probability_multiband.tif`, and `index_path` ending in
`reference/rasters/occurrence_probability_bands.json`. On validation failure it returns
`success: False`, a stable `error_code`, and leaves no partial stack or index.

### `inspect_probability_stack(stack_path: str, source_dir: str) -> dict`

Inspects the actual output and source rasters without opening a QGIS project. It returns
`valid`, `band_count`, `source_files_represented_once`,
`pixel_crosscheck.values_match`, `pixel_crosscheck.nodata_match`, and
`metadata.nodata`. The cross-check must cover a representative pixel set across all
`discovered_species_count` bands, not just stack metadata.

### `inspect_probability_project(project_dir: str) -> dict`

Reopens the generated project through the existing isolated project-inspection path and returns
`probability_layers`, `probability_layer_tree_nodes`, `reference_files`, `band_index_mapping`,
`manifest`, and `absolute_path_leaks`; `manifest.band_count` equals the source inventory's
`discovered_species_count`, and each probability-layer entry includes `valid` and `datasource`.
The inspection must count both registry entries and tree nodes, and must detect
per-species/hidden lookup layers as well as absolute source, credential, or photo paths.

### `sample_probability_candidate(project_dir: str, korean_name: str, location: dict) -> dict`

Samples a known candidate through the project-local stack/index seam and returns
`{"available": bool, "value": number | None, ...}`. It is used only after copying a generated
project to a new root, so the test proves the relative stack/index paths work without the source
directory. It must use the exact normalized Korean-name band mapping and must not reconstruct a
per-species filename.

The existing `build_project(config, output_dir)` acceptance seam additionally accepts the
test-only `_test_probability_raster_source_dir` configuration key. This allows the acceptance
suite to exercise inventories with different positive discovered counts while production
continues to use the authoritative
`storage/reference/rasters/bce_inverse_corrected_probability_maps/` directory. The override does
not establish a test-only fixed count and must obey the same dynamic discovery and fail-closed
validation rules as production.

## Markers used (registered in `conftest.py`)

- `qgis` — requires a real, working QGIS/PyQGIS runtime (`check_runtime()["available"]`); skipped
  automatically when unavailable.
- `network` — would require live network access to the real VWorld API; skipped by default.
- `device` — requires a physical iOS/Android device running QField; not automated here.
- `manual` — requires human/GUI/installer interaction not automatable via this harness.

## HTML report integrated data/map/summary/theme fixture renderer (AC-IHRM-001–013)

The approved integrated-data-map-summary-theme slice adds one narrow headless adapter:

### `render_html_report_integrated_fixture(fixture: dict) -> dict`

This adapter must invoke the **same production integrated-report collection, join/column
allocation, geometry/map selection, direct-source card aggregation, fallback disclosure, CSV, and
generated-report DOM/event paths** used by the standalone report. It may reuse or extend
`render_html_report_fixture`, but it must not implement a parallel test-only report model or
manufacture expected result snapshots. It must not construct `QgsApplication` in the acceptance
process; if production collection requires QGIS, it must use the existing isolated bridge.

All fixture data is synthetic and in-memory. This adapter never authorizes access to the
user-owned `Downloads/test2.*` artifacts, a browser profile, or a real QGIS profile.

In addition to the input accepted by `render_html_report_fixture`, it accepts:

- `survey_type`: one of `simple_inventory`, `temporary_plots`, `permanent_plots`, or
  `vegetation_mapping`.
- `source_columns[*].semantic_identity`: optional approved semantic-alias identity. Source rows
  remain keyed by `id`; a missing key is distinct from a present `None`, `0`, `False`, or `""`.
- `direct_sources`: table-name mapping to `{"schema_present": bool, "records": [dict, ...]}`.
  This is the direct schema-defined card source, not a replacement for `source_rows`, which remain
  joined table/detail/map/CSV rows and may deliberately fan out a direct source record.
- `spatial_metadata`: metadata entries containing `table`, `geometry_column`, `geometry_type`,
  `source_crs`, and source-row `record_ids`; `qgis_spatial_layers` supplies matching loaded
  layer/table/geometry-column/CRS identity. `coordinate_transform_available: False` exercises the
  EPSG:4326 identity path.
- `theme_interaction`: optional `initial_theme`, `storage_available`, ordered `actions`
  (`click`, keyboard `Enter`/`Space`, and `reopen`), and a serializable report `state` that must
  remain unchanged by theme actions.

The returned dictionary contains the existing renderer fields plus at least:

```text
{
  "source_to_final_key": {source_column_id: final_key},
  "source_to_canonical_provenance": {source_column_id: object},
  "source_value_presence": {source_row_id: {source_column_id: bool}},
  "column_definitions": [
    {"key": str, "source_column_id": str, "source_column_ids": [str, ...], ...},
  ],
  "semantic_collision_notices": [{"semantic_identity": str, ...}],
  "spatial_metadata": [
    {"table": str, "geometry_column": str, "geometry_type": str,
     "source_crs": str, "non_null_geometry_count": int},
  ],
  "map_features": [
    {"source_row_id": str, "stable_source_id": str,
     "geometry": GeoJSON_geometry, "joined_attributes": dict},
  ],
  "map_empty_notice_present": bool,
  "fallback": {
    "used": bool, "source": str | None, "failed_direct_path": str | None,
    "successful_reads": [{"table": str, "row_count": int}],
  },
  "overview_cards": [
    {"label": str, "value": int | "해당 레벨 부재",
     "direct_source_layer": str, "source_field": str | None, "basis": str},
  ],
  "integrated_table": {
    "present": bool, "state": "populated" | "empty_data" | "collection_error" |
             "join_error" | "render_error", "header_keys": [str, ...],
  },
  "theme_states": [
    {"theme": "light" | "dark", "document_element_theme": "light" | "dark",
     "aria_pressed": bool, "label": str, "css_variables": dict, "report_state": dict},
  ],
  "saved_theme_preference": "light" | "dark" | None,
}
```

`source_to_final_key` is authoritative in every projection, action, and CSV header. Equal semantic
sources may map to one final key only under the approved equality/presence rule; different present
values (including present `null` versus non-empty) require separate source-provenanced final keys
and a collision notice. `overview_cards` must be computed only from `direct_sources`, so joined
fan-out never changes them. `limitations` must retain stable invalid-geometry reasons and date or
KTSN exclusion counts.

For `theme_interaction`, each returned state must be a snapshot from the report's actual DOM/event
path: keyboard and click activations update `document.documentElement`, computed CSS variables,
the button label, and `aria-pressed`; a `reopen` action reads stored preference only when storage
is available. The supplied report-state snapshot, joined source data, and CSV headers must not
change merely because the theme changes.

## Superseded FieldBuild Standalone QField HTML report refresh fixture renderer (AC-FBKR-002–007)

> Superseded by the provider-runtime bridge immediately following this historical section.
> Its abstract `source_rows`/`spatial_records`/`analytics_input` inputs and its derived result
> envelope are no longer accepted for AC-FBKR-002–007. They remain below only to explain the
> replacement boundary; they are not an implementation option.

The FieldBuild Standalone refresh adds one narrow, headless acceptance adapter:

### `render_html_report_refresh_fixture(fixture: dict) -> dict`

This adapter must invoke the **same production direct GeoPackage collection, permitted QField
loaded-layer fallback, geometry serialization/CRS handling, spatial-anchor selection, joins,
normal-report/Diagnostics rendering, CSV export, analytics-card construction, and report
DOM/event paths** as the exported local HTML report. It may extend either existing report-fixture
adapter, but it must not implement a parallel test-only report model, fabricate expected snapshots,
or turn a fixture outcome into a bypass of the physical QField gate. It must not construct a
`QgsApplication` in the acceptance-test process; production QGIS work uses the existing isolated
bridge.

All input is synthetic and in memory. This adapter must never access the user-owned evidence
fixture, a Downloads folder, a QGIS/browser profile, or a device. The device-only AC-FBKR-001
remains in the skipped manual test and is deliberately outside this adapter's scope.

The input accepts the existing report-fixture row/column fields plus:

- `survey_type`: one of `simple_inventory`, `temporary_plots`, `permanent_plots`, or
  `vegetation_mapping`.
- `collection`: synthetic status for `direct` (`available`, optional `failure`/`location`) and
  permitted `fallback` (`enabled`, `source`, optional successful reads, omissions, and unverified
  scopes). A direct-unavailable fixture must use the fallback only when `fallback.enabled` is
  true; it must not invent another source.
- `spatial_records`: source records with `record_id`, table, source CRS, and runtime geometry.
  Geometry can state an explicit `is_empty`, a preferred export outcome, local WKT-compatible
  fallback, or GeoJSON-shaped source geometry. This models input capability/outcome; it does not
  prescribe the implementation's private serializer.
- `anchor_contexts`: source UUID/FK-linked contexts. The production anchor policy must select
  Type 1 inventory observation; Type 2 site separately plus survey; Type 3 site separately plus
  plot, with only linked-survey geometry fallback; and Type 4 community only. Other supplied
  coordinates (attribute, photo, nearby, or child-observation) are negative controls and cannot
  become map geometry.
- `analytics_input`: synthetic source values for the fixed card matrix. `render_viewports` asks
  for snapshots at the supplied CSS widths. `runtime_settings` supplies an offline/key/reduced-
  motion action sequence. No supplied VWorld key may be rendered or exported.

The returned dictionary contains actual parsed output/snapshots, at least:

```text
{
  "success": bool,
  "error_message": str | None,
  "geometry_outcomes": [
    {"record_id": str, "outcome": "valid" | "actual_empty" |
       "serialization_failure" | "transform_failure" | "malformed_xy" |
       "unsupported_geometry" | str,
     "reason_ko": str, "collection_path": "direct" | "fallback",
     "transform_attempted": bool, "geometry": GeoJSON | None}
  ],
  "map_feature_ids": [str],
  "map_features": [
    {"feature_id": str, "anchor_table": str, "anchor_record_id": str,
     "geometry_source_record_id": str, "collection_path": "direct" | "fallback",
     "geometry": GeoJSON}
  ],
  "csv_text": str,
  "normal_view": {
    "text": str, "status_text": str, "table_headers": [str],
    "table_record_ids": [str], "rows_by_record_id": {str: {"fields": [
      {"label": str, "value": object}
    ]}}, "diagnostics_closed_by_default": bool, "diagnostics_text_visible": bool
  },
  "diagnostics": {
    "closed_by_default": bool, "keyboard_operable": bool,
    "collection_path": str, "direct_access_failed": bool,
    "successful_reads": [object], "known_omissions": [object],
    "unverified_scopes": [object], "claims_complete_direct_inventory": bool
  },
  "analytics": {
    "section_visible": bool, "toc_entry_visible": bool,
    "cards": [{"kind": str, "title_ko": str, "basis_ko": str,
      "limitation_text_ko": str, "text_equivalent": [object],
      "accessible_chart": {"has_non_color_encoding": bool,
        "keyboard_operable": bool, "focus_indicator_visible": bool},
      "print_text_equivalent_visible": bool}],
    "responsive_grid": {"card_container": "grid", "viewports": [
      {"width": int, "page_horizontal_overflow": bool}
    ]}
  },
  "controls": {"vworld_visible": bool, "vworld_control_kind": str | None,
               "vworld_key_embedded": bool},
  "retained_behavior": {
    "local_map_feature_ids": [str],
    "table": {"filter_result_ids": [str], "keyboard_sort_result_ids": [str]},
    "csv": {"all_record_ids": [str], "filtered_record_ids": [str]},
    "theme": {"current": "light" | "dark"},
    "print": {"diagnostics_included": bool},
    "reduced_motion": {"motion_reduced": bool},
    "keyboard": {"table_sort_operable": bool, "diagnostics_operable": bool},
    "no_network_required_for_local_operations": bool
  }
}
```

All GeoJSON returned for a valid report feature is WGS84 longitude/latitude XY only, including
recursive polygon coordinates. An explicit source null/empty is the sole route to
`actual_empty`; unavailable direct access, serializer exceptions, unsupported preferred export,
unknown CRS, and transform failure must retain their distinct non-empty outcomes. Every supplied
source row remains represented in the normal integrated table and CSV even if its map geometry
fails. Result text/payload/CSV/map-popup/diagnostic snapshots must contain no iOS sandbox absolute
path, credential, API key, attachment, or photo content.

## FieldBuild Standalone QField HTML report refresh provider-runtime bridge (AC-FBKR-002–007)

### `render_html_report_refresh_fixture(fixture: dict) -> dict`

This is a narrow test adapter around the **shipped** report, not a reference report model. It must:

1. instantiate QGIS/QField-shaped mocks from `fixture["qgis_provider"]`;
2. evaluate the exact QML collector containing `qpbBuildHtmlReport()` with those mocks;
3. call that shipped `qpbBuildHtmlReport()` exactly once and retain its actual
   `qpbLastReportPayload` and returned HTML; and
4. evaluate the scripts embedded in that returned HTML in a DOM-capable Node runtime, applying
   the requested offline actions to that exact document before returning DOM observations.

The adapter may extract/evaluate the generated QML JavaScript in Node with QML global shims, but
it must not copy, port, or selectively reimplement the collector, serializer, join logic, chart
logic, HTML template, CSV logic, or DOM event handlers in Python/Node. The source string executed
for collection must come from the same generated QML/template path used by the shipping plugin;
the source string executed for rendering must be the HTML returned by that invocation. A missing
Node/DOM/QML-compatible runtime is an adapter failure, not permission to fall back to the old
Python renderer or a fabricated snapshot.

The fixture has exactly these top-level keys:

```text
{
  "qgis_provider": { ... },
  "html_runtime": { ... }
}
```

The adapter must reject, rather than ignore, any retired top-level key:
`source_columns`, `source_rows`, `spatial_records`, `anchor_contexts`, `analytics_input`,
`collection`, `runtime_settings`, `diagnostic_inputs`, or prebuilt HTML/payload/snapshot keys.

### Provider-shaped fixture input

`qgis_provider.project` supplies only project metadata needed to select the real generated report
definition: `survey_type` (`simple_inventory`, `temporary_plots`, `permanent_plots`, or
`vegetation_mapping`) and `project_slug`. The bridge must derive table definitions, UUID fields,
FKs, labels, geometry columns/types, and report template from shipped production sources; the
fixture must not provide a substitute report definition or anchor map.

`qgis_provider.loaded_layers` is a list of mocked `QgsVectorLayer` objects:

```text
{
  "name": "inventory_observation",        // real schema table/layer name
  "fields": ["inventory_id", ...],         // provider field names
  "geometry_column": "geom" | null,
  "geometry_type": "POINT" | "MULTIPOLYGON" | null,
  "crs_authid": "EPSG:4326" | "UNKNOWN:LOCAL" | ...,
  "features": [
    {
      "attributes": {"inventory_id": "inventory-01", ...},
      "geometry": {
        "isNull": bool, "isEmpty": bool,
        "asJson": {"return": GeoJSON} | {"throw": str},
        "asWkb": {"return": [byte, ...]} | {"throw": str}
      } | null,
      "layer_crs_authid": str                 // optional per-feature test override
    }
  ]
}
```

The mock exposes the production-facing members (`name`, `fields`, `crs().authid()`,
`geometryColumn`, `LayerUtils.createFeatureIterator`, `feature.attribute(name)`, and either
callable or property-form `feature.geometry`) without precomputing a geometry outcome. The
`geometry` descriptor only controls what those QGIS geometry methods return or throw. An explicit
`isNull`/`isEmpty` result is the only fixture representation of actual emptiness. `asJson` and
`asWkb` model QField runtime API availability; they do not name a desired report outcome.

`qgis_provider.direct_gpkg` controls the existing read-only direct collection path. `available`
is a boolean; when true, `tables` provides GeoPackage-style table metadata and unclassified SQL
rows (`name`, `columns`, `geometry_column`, `geometry_type`, `srs_id`, `rows`). The SQL shim must
answer the exact metadata/PRAGMA/SELECT calls the shipped collector makes from that data. When
false it exposes no SQL bridge, so the shipped fallback discovery executes. Optional
`row_crs_overrides` is a mock-provider CRS response keyed by the schema primary-key value; it is
only for testing per-feature CRS behavior and must still flow through the collector's CRS path.
Direct rows retain declared primary-key/FK columns and geometry-column values; they never contain
`outcome`, normalized GeoJSON, joined rows, anchors, analytic values, or report-ready labels.

`qgis_provider.runtime_capabilities.coordinate_transform` controls whether the mocked QML
`QgsCoordinateTransform`/`QgsCoordinateReferenceSystem` APIs exist. A WGS84 feature must succeed
without them. `html_runtime` supplies offline DOM conditions only: `network_available`,
`viewport_widths`, optional private `runtime_vworld_key`, `prefers_reduced_motion`, and the action
sequence (`filter`, keyboard sort, theme, Diagnostics, print, CSV). A supplied VWorld key is a
runtime-only mock value and must not occur in QML payload, returned HTML, DOM text, CSV, or result
snapshots.

### Required returned observations

The returned value has no adapter-derived report state. It exposes only the execution provenance,
the actual QML payload, and parsed observations from the resulting document:

```text
{
  "success": bool,
  "error_message": str | null,
  "bridge": {
    "qml": {
      "qpb_build_html_report_called": true,
      "report_payload": object                 // serialized qpbLastReportPayload
    },
    "html": {
      "generated_from_qpb_build_html_report": true,
      "document": {
        "normal": {"text": str, "status_text": str},
        "diagnostics": {"closed_by_default": bool, "keyboard_operable": bool,
                        "claims_complete_direct_inventory": bool},
        "map": {"feature_anchor_uuids": [str]},
        "table": {"joined_row_uuids": [str], "rows": [{"fields": [{"label": str, "value": object}]}]},
        "csv": {"all_row_uuids": [str], "filtered_row_uuids": [str]},
        "analytics": {"section_visible": bool, "toc_entry_visible": bool,
                      "cards": [{"kind": str, "title_ko": str, "basis_ko": str,
                                  "text_equivalent": [object], "keyboard_operable": bool,
                                  "focus_indicator_visible": bool,
                                  "print_text_equivalent_visible": bool}],
                      "viewports": [{"width": int, "page_horizontal_overflow": bool}]},
        "controls": {"vworld_visible": bool, "vworld_key_embedded": bool},
        "interactions": {"local_operations_used_network": bool,
                           "keyboard_table_sort_operable": bool, "diagnostics_operable": bool,
                           "theme": "light" | "dark", "reduced_motion": bool,
                           "print_diagnostics_included": bool}
      }
    }
  }
}
```

The QML payload is inspectable only to prove collection/anchor geometry came from the exact
collector. Tests must use schema primary-key values (`inventory_id`, `site_id`, `survey_id`,
`plot_id`, `observation_id`, `community_id`) when linking payload records to DOM observations;
they must not invent generic `record_id` fields. Normal-view assertions inspect the document only,
so internal identities cannot be treated as user-visible output.

All collection is synthetic, in memory, read-only, offline, and repository-local. The bridge must
not access a user-owned report, Downloads, a QGIS/browser profile, simulator, physical device, or
network. AC-FBKR-001 remains the skipped physical iPhone/QField manual gate and is outside this
adapter's scope.
