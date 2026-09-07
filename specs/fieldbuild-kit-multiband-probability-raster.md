# Feature: Single multiband occurrence-probability GeoTIFF

> Status: DRAFT (revised) — awaiting user review and approval  
> Owner: spec-writer  
> Last updated: 2026-09-06
> Extends: `specs/qfield-project-builder.md`,
> `specs/fieldbuild-kit-identification-probability-raster-fallback.md`, and
> `specs/fieldbuild-kit-probability-raster-generation-timeout.md`

## 1. Summary

Replace the current per-species probability-raster runtime contract with one multiband
GeoTIFF built from the authoritative species TIFF set. Each Korean common name maps to one
deterministic band number; generated QGIS projects register only that multiband raster, and
runtime sampling selects the band from the resolved Korean common name.

This specification is authoritative for probability-raster packaging, QGIS registration, and
sampling. It supersedes only the earlier requirements to copy/read one TIFF per species and to
register zero probability-raster layers. Existing identification behavior, authoritative
locations, value validation, NoData handling, candidate-local fallback, and persistence remain
unchanged.

## 2. Decision Log

- **D-MPR-001** (2026-09-01, Category C stakeholder-approved product change with a Category A
  performance/conformance correction): The user's explicit direction is to replace the current
  probability-raster runtime approach with **one multiband GeoTIFF made from the complete species
  TIFF inventory**, register that one raster in generated QGIS projects, and sample by **Korean
  common name → band number**. The purpose is to preserve in-field probability sampling while
  avoiding thousands of QGIS layers and the resulting project-build timeouts.

  This decision supersedes the per-species-file and zero-probability-layer-registration portions
  of the two predecessor specs named above, including `FR-PRF-001`, `FR-PRF-016`,
  `FR-PRG-001`–`FR-PRG-005`, `FR-PRG-007`, `C-PRG-001`–`C-PRG-002`, and their directly
  corresponding acceptance assertions. It does not supersede the predecessor specs' location,
  value, NoData, invalid-data, timeout/watchdog, non-blocking, persistence, relative-path, or
  Type 4 boundary rules unless this document states a replacement explicitly.

  The initial decision used a fixed expected inventory count and separately excluded
  `bce_inverse_corrected_richness_5km_uncalibrated.tif`. The implementation must not silently
  assign the richness raster a species band.

  **Superseded in part by D-MPR-002 and D-MPR-003:** the originally fixed species-count
  expectation is no longer authoritative. The single-stack architecture and all non-count
  requirements remain in force.

- **D-MPR-002** (2026-09-01, Category C stakeholder-approved product change): The user's
  subsequent instruction established the files matching
  `bce_inverse_corrected_probability_{Korean common name}.tif` in the current source folder as
  the authoritative species inventory using a fixed count observed at that time. The separate
  `bce_inverse_corrected_richness_5km_uncalibrated.tif` remains excluded. This decision
  superseded only D-MPR-001's initial fixed count; the stack, index, manifest, validation,
  sampling, and compatibility contracts otherwise remained unchanged.

  **Superseded by D-MPR-003:** no fixed species count is authoritative.

- **D-MPR-003** (2026-09-01, Category C stakeholder-approved product change): The user explicitly
  instructed, “개수를 한정해서 명시하지 말고 … 폴더에 있는 개수만큼 쓰는걸로 하자,”
  thereby removing every fixed species-count requirement. At build time, the authoritative
  inventory is the complete set of species TIFFs discovered in the configured source directory
  whose basenames match `bce_inverse_corrected_probability_{Korean common name}.tif`. The number
  of those files is `discovered_species_count`, and the stack, index, manifest, validation, and
  performance contracts use that value rather than a repository-wide constant. Every discovered
  file must then pass validation; an invalid discovered file fails the complete inventory rather
  than reducing the count. The separate richness TIFF and all other nonmatching files remain
  excluded. This decision supersedes the fixed-count portions of D-MPR-001 and D-MPR-002 without
  changing the single-stack architecture or any location, sampling, persistence, compatibility,
  and fail-closed requirements.

## 3. Functional Requirements

### 3.1 Build-time source validation and stack creation

- **FR-MPR-001:** For an identification-enabled Type 1, Type 2, or Type 3 project, the build
  must use `storage/reference/rasters/bce_inverse_corrected_probability_maps/` as the default
  source inventory directory (currently resolved as
  `/Users/tory/vibe_coding/qfield_builder/storage/reference/rasters/bce_inverse_corrected_probability_maps/`
  in the development workspace). A species source file is a regular file whose basename matches
  `bce_inverse_corrected_probability_{Korean common name}.tif`. Files that do not match this
  species pattern, including `bce_inverse_corrected_richness_5km_uncalibrated.tif`, are not
  probability bands and must not be included in the stack. The number of matching files found
  during validation is `discovered_species_count`.

- **FR-MPR-002:** `discovered_species_count` must be greater than zero. The build must fail before
  producing a deliverable if the source directory is missing, is not a readable directory, has
  no matching species files, changes such that a discovered file is missing before it is read,
  a species filename yields an empty name, two names collide after Unicode NFC normalization, or
  any discovered source file is empty, unreadable, or not a valid single-band raster. The failure
  must identify the validation reason and must not produce a partial stack, partial index, or
  partial generated project. Nonmatching files are excluded and reported but do not by
  themselves make an otherwise valid non-empty inventory fail.

- **FR-MPR-003:** All `discovered_species_count` source rasters must have compatible stack
  geometry: identical width, height, geotransform/pixel grid, CRS, single-band layout, numeric
  data type, and NoData
  convention. The build must fail clearly on incompatibility; it must not silently reproject,
  resample, mosaic, average, crop, or otherwise alter a source raster to force compatibility.

- **FR-MPR-004:** The build must create one project-relative GeoTIFF at
  `reference/rasters/occurrence_probability_multiband.tif`. It must contain exactly
  `discovered_species_count` bands, with every discovered source species raster copied into
  exactly one output band. For every source pixel, the corresponding output-band value and
  NoData state must equal the source value; the output uses the source probability scale and
  NoData sentinel (`0.0`–`1.0`, with `-9999` as NoData).

- **FR-MPR-005:** Band order must be deterministic: sort the source Korean common names after
  Unicode NFC normalization using the repository's stable lexical ordering, then assign band
  numbers starting at 1. The same validated source inventory must always produce the same
  Korean-name-to-band mapping, independent of filesystem directory order.

- **FR-MPR-006:** The build must create
  `reference/rasters/occurrence_probability_bands.json` beside the stack. The file must contain
  the project-relative stack path, `band_count` equal to `discovered_species_count`, and an exact
  mapping from each normalized Korean common name to its 1-based band number. The mapping must
  contain exactly `discovered_species_count` entries and use every integer band number in
  `1..discovered_species_count` exactly once. It must not contain absolute source paths,
  credentials, or photo paths.

### 3.2 Generated QGIS project registration and packaging

- **FR-MPR-007:** An identification-enabled Type 1, Type 2, or Type 3 generated QGIS project
  must register exactly one probability raster: the multiband GeoTIFF from FR-MPR-004, using a
  project-relative datasource. The registered layer must be a valid QGIS raster layer and must
  be placed in the existing reference-raster layer/group location used by the project.

- **FR-MPR-008:** The generated QGIS project must contain exactly one probability-raster map
  layer and exactly one corresponding layer-tree node. No per-species `QgsRasterLayer`, hidden
  lookup layer, per-species layer-tree node, or equivalent registration is permitted. The one
  multiband reference layer follows the project's existing default visibility policy.

- **FR-MPR-009:** The generated project's `reference/` folder must contain the multiband TIFF
  and band-index JSON, and must not contain any individual species TIFFs. The manifest or
  equivalent validation artifact must list the two project-relative outputs and a band count
  equal to `discovered_species_count`; it must not list or reference an absolute source path.

- **FR-MPR-010:** If identification is disabled, the existing conditional behavior is preserved:
  the probability stack, band index, probability layer, and probability runtime path are not
  added solely because the project has Type 1–3 survey data. Type 4 projects remain outside the
  plant-photo identification and occurrence-probability scope.

### 3.3 Runtime band lookup and sampling

- **FR-MPR-011:** When a Pl@ntNet candidate has a resolved Korean common name, runtime must
  normalize it to Unicode NFC, look it up exactly in `occurrence_probability_bands.json`, and use
  the resulting 1-based band number to sample the project-local multiband GeoTIFF. Runtime must
  not reconstruct a per-species filename, open an individual species TIFF, use scientific name
  or KTSN as the raster key, or depend on filesystem enumeration.

- **FR-MPR-012 (revised; D-PRF-003):** Sampling must use the existing authoritative location
  rules: Type 1 uses the current `inventory_observation` geometry; Type 2 uses the `survey`
  location; Type 3 uses only the current `plot` location, including current in-memory plot
  geometry before its plot and survey are saved. Missing/invalid Type 3 plot geometry makes
  probability unavailable without a survey fallback. The location is transformed from project
  CRS to the stack CRS before sampling. EXIF GPS, device GPS, attachment metadata,
  provider-invented locations, and site centroids must not be used.

- **FR-MPR-013:** A valid sampled value in the inclusive range `0.0`–`1.0` is a valid occurrence
  probability, including exactly `0.0`. Exactly `-9999`, NoData, a missing band mapping, a
  missing/unreadable stack, an invalid CRS, an invalid or out-of-extent location, a non-finite
  value, or any other out-of-range value must produce probability unavailable—not zero, a clamped
  value, or an invented value—and must preserve the existing diagnostic reason where available.

- **FR-MPR-014:** Probability sampling must remain bounded and non-blocking. A missing species
  mapping, stack-read failure, sampler exception, or sampler timeout affects only that candidate;
  Pl@ntNet identification, candidate display, candidate selection, write-back, and normal save
  must continue. Probability success/failure must not be written as identification success/failure.

- **FR-MPR-015:** When a candidate is selected, the existing occurrence-probability storage and
  display rules remain in force: store a valid 0–1 value when available, otherwise store null or
  the existing unavailable representation. Existing Korean-name write-back, derived scientific
  name/KTSN lookup, identification status, UUID/FK/relation isolation, save/reopen behavior, and
  Type 1–3 location semantics must not change.

### 3.4 Build performance and compatibility boundary

- **FR-MPR-016:** On the default source inventory present at build/test time, normal project
  generation must process all `discovered_species_count` valid species rasters, register the
  resulting stack once, and return successfully within the existing 180-second QGIS bridge job
  timeout. A `worker_timeout` is not a successful result. Stack construction may be performed
  once at build time, but it must not open/register one QGIS map layer per source file.

- **FR-MPR-017:** This change applies to newly generated projects only. It does not migrate,
  rewrite, or delete raster files or layer registrations in previously generated projects.

## 4. Constraints

- **C-MPR-001:** The deliverable raster source inventory is the complete non-empty set of valid
  matching species probability TIFFs discovered in the default source directory at validation
  time. No fixed species count is permitted. Non-species TIFFs in the source directory are
  excluded and must be reported as such.
- **C-MPR-002:** The generated project has one and only one probability-raster QGIS layer. The
  old per-species layer-registration approach is prohibited.
- **C-MPR-003:** The generated project contains one multiband GeoTIFF and one band-index file,
  not thousands of per-species TIFF files and not a silent partial subset.
- **C-MPR-004:** Band lookup is exact Korean common name → 1-based band number. Fuzzy matching,
  scientific-name matching, KTSN matching, and filesystem enumeration are not substitutes.
- **C-MPR-005:** Source pixel values, grid, CRS, and NoData semantics are preserved; reprojection
  or resampling is not an implicit build workaround.
- **C-MPR-006:** All generated-project paths are project-relative. Absolute source paths,
  credentials, and photo paths must not be written to the project, manifest, index, logs, or
  validation report.
- **C-MPR-007:** Existing `0.0`/`1.0` range, `-9999` NoData, invalid-location, out-of-extent,
  candidate-local-unavailable, bounded-timeout, and non-blocking identification contracts remain
  mandatory.
- **C-MPR-008:** The 180-second bridge timeout is the measurable generation bound for the full
  default inventory discovered at build/test time; performance must be achieved without
  weakening validation or silently omitting any discovered species raster.

## 5. Assumptions

- **A-MPR-001:** The authoritative species inventory is determined dynamically from all matching
  species files in the default source directory. The separate richness TIFF is not part of that
  inventory and does not belong in the stack.
- **A-MPR-002:** The dynamically discovered species rasters share one compatible single-band
  grid and the existing probability conventions (`0.0`–`1.0`, `-9999` NoData). If this is false,
  FR-MPR-003 requires a fail-early result rather than an inferred transformation.
- **A-MPR-003:** Existing KTSN/accepted-name resolution returns the Korean common name that is
  the source filename's species key, with Unicode canonical-equivalence normalization sufficient
  for the NFC index lookup.
- **A-MPR-004:** QGIS and the target QField runtime can read a project-local multiband GeoTIFF
  and select a band by integer index. The exact provider/API used to perform the bounded sample
  remains an implementation choice if the observable contract is met.
- **A-MPR-005:** The existing identification-enabled trigger and Type 4 exclusion remain
  unchanged; this feature changes the raster representation and registration count only.

## 6. Edge Cases

- **E-MPR-001:** The source directory contains any positive number of matching species-pattern
  TIFFs plus the richness TIFF or other nonmatching files. The validator excludes and reports
  the nonmatching files, accepts every valid matching species file, sets
  `discovered_species_count` to their count, and creates a stack with that many bands. A changed
  positive count is not itself a validation failure.
- **E-MPR-011:** The source directory is absent, unreadable, not a directory, or contains zero
  matching species files. Validation fails closed before stack/index/project publication and
  reports the inventory problem.
- **E-MPR-012:** Enumeration discovers a matching species file but it disappears, becomes
  unreadable, or changes into an invalid raster before validation/copy completes. The build fails
  atomically; it must not reduce `discovered_species_count`, silently omit the file, or publish a
  shortened stack and index.
- **E-MPR-002:** Two source filenames produce the same NFC Korean common name. The build fails
  with the colliding names; it does not choose a band arbitrarily or merge their values.
- **E-MPR-003:** A source file is missing, empty, corrupt, multi-band, or incompatible with the
  common grid. The build fails atomically and does not ship a shortened or partially populated
  stack.
- **E-MPR-004:** A candidate's resolved Korean common name has no band-index entry. That
  candidate alone receives probability unavailable; other candidates continue to sample.
- **E-MPR-005:** The index exists but contains a non-integer, zero, negative, duplicate, or
  out-of-range band number, or its stack path is not the required relative path. The runtime
  treats the mapping as invalid for that candidate and reports probability unavailable; it does
  not guess a band.
- **E-MPR-006:** A sampled pixel is exactly `0.0`, exactly `-9999`, NoData, non-finite, outside
  `0.0`–`1.0`, or outside the raster extent. The existing valid-zero, unavailable, and invalid-
  value rules apply without clamping or zero fabrication.
- **E-MPR-007 (revised; D-PRF-003):** Type 1 geometry is absent/invalid, Type 2 survey location
  is absent/invalid, or Type 3 plot location is absent/invalid. Identification continues and only
  probability becomes unavailable; no survey, photo, or device location is substituted for Type 3.
- **E-MPR-008:** Several candidates resolve to different bands and one band samples successfully
  while another is unavailable. Availability and values remain candidate-specific; the valid
  result is not erased by the unavailable result.
- **E-MPR-009:** The stack layer is missing from the project, unreadable after project transfer,
  or no longer valid on reopen. The runtime reports bounded probability unavailability and keeps
  the identification and save flow usable; it does not recreate thousands of layers.
- **E-MPR-010:** A Type 4 community record or an identification-disabled project is processed.
  No probability stack, probability layer, or new photo-identification target is added.

## 7. Out of Scope

- Changing the probability model, source probability values, CRS, grid, NoData sentinel, or
  scientific meaning of the supplied rasters.
- Reprojecting, resampling, mosaicking, cropping, aggregating, or downsampling source species
  rasters to make an incompatible inventory fit.
- Bundling the individual species TIFFs into newly generated projects.
- Requiring direct per-species TIFF reads, per-species QGIS layers, a virtual-raster substitute,
  or a new external probability provider.
- Changing Pl@ntNet requests, KTSN/accepted-name resolution, candidate UI, write-back algorithms,
  GeoPackage schema, UUID/FK/relation rules, or Type 4 behavior.
- Migrating previously generated projects.
- Allowing EXIF GPS, device GPS, attachment metadata, provider-invented locations, or site
  centroids as probability locations.

## 8. Acceptance Criteria

- **AC-MPR-001:** Given the default source directory contains `N > 0` valid species-pattern TIFFs
  plus the separate richness TIFF or other nonmatching files, when validation and stack creation
  run, then `discovered_species_count` equals `N`, nonmatching files are excluded and reported,
  all `N` matching files are accepted, and no per-species generated-project outputs are created.
  Repeating with a different positive valid count succeeds with that newly discovered count.
  Given a missing/unreadable source directory, zero matching species files, or a missing,
  unreadable, empty, corrupt, multi-band, duplicate-key, or incompatible discovered file,
  validation reports the specific reason and produces no deliverable.
- **AC-MPR-002:** Given a validated inventory with `discovered_species_count = N`, when the stack
  is inspected, then `reference/rasters/occurrence_probability_multiband.tif` contains exactly
  `N` bands, each discovered source raster is represented exactly once, and a cross-check of
  representative pixels across every band preserves source values and NoData state.
- **AC-MPR-003:** Given the same inventory, when the band index is inspected, then
  `reference/rasters/occurrence_probability_bands.json` has `band_count` equal to
  `discovered_species_count`, maps every normalized Korean common name to exactly one integer
  band in `1..discovered_species_count`, contains no omitted names, duplicate keys, or duplicate
  band numbers, and yields identical results across two builds with the same files but different
  filesystem enumeration order.
- **AC-MPR-004:** Given an identification-enabled Type 1, Type 2, or Type 3 build, when the
  generated project and manifest are inspected, then the project contains the stack and index
  at the required relative paths, contains no individual species TIFF, and contains no absolute
  source path, credential, or photo path in the generated probability artifacts.
- **AC-MPR-005:** Given that generated project, when its QGIS layer registry and layer tree are
  inspected, then exactly one valid probability-raster map layer and exactly one corresponding
  layer-tree node exist, the datasource resolves to the project-local multiband GeoTIFF, and no
  per-species or hidden lookup raster layer exists.
- **AC-MPR-006:** Given the full valid default inventory discovered at test time, when normal
  generation runs through the QGIS bridge, then it processes all `discovered_species_count`
  files, returns success within 180 seconds, does not return `worker_timeout`, and performs one
  probability-raster registration rather than one registration per species.
- **AC-MPR-007:** Given a candidate with a known Korean common name and a test coordinate whose
  expected source value is known, when runtime sampling runs, then it reads the shared stack at
  the exact index-file band and returns the expected 0–1 value without opening a per-species
  filename or relying on filesystem enumeration.
- **AC-MPR-008:** Given a candidate whose Korean common name is absent from the index, when
  probability enrichment runs, then only that candidate is marked probability unavailable and
  the candidate list, other candidate samples, selection, write-back, and save remain usable.
- **AC-MPR-009:** Given a valid location and a sample of exactly `0.0`, when enrichment runs,
  then `0.0` is displayed/stored as a valid probability. Given `-9999`, NoData, an out-of-range
  value, non-finite data, invalid CRS, or an out-of-extent location, then probability is
  unavailable or invalid per the existing rule and is never silently changed to zero or clamped.
- **AC-MPR-010 (revised; D-PRF-003):** Given Type 1, Type 2, and Type 3 records, when sampling
  runs, then the authoritative locations are respectively inventory geometry, survey location,
  and plot location only, transformed to the stack CRS; an unsaved Type 3 plot/survey flow uses
  current in-memory plot geometry. Missing/invalid Type 3 plot geometry makes probability
  unavailable without a survey fallback; EXIF/device/photo metadata is not used.
- **AC-MPR-011:** Given a missing/invalid location, mapping failure, stack-read exception, or
  sampler timeout, when identification runs, then the flow remains bounded and usable, the
  candidate is retained, and existing identification/write-back/save semantics are unchanged.
- **AC-MPR-012:** Given multiple candidates with mixed successful and unavailable band samples,
  when candidates are displayed and one is selected, then each candidate retains its own
  probability state, the valid value remains visible, and the selected record stores only the
  selected candidate's valid value or unavailable representation without changing UUID/FK/
  relation data.
- **AC-MPR-013:** Given a Type 4 project or an identification-disabled project, when it is
  generated and reopened, then no occurrence-probability stack, probability layer, or new
  plant-photo identification target is present.
- **AC-MPR-014:** Given a newly generated project copied to another supported machine/device,
  when it is reopened and a known candidate is sampled, then the relative stack and index paths
  resolve without the original source directory, and no per-species layer is recreated.

## 9. Traceability

| Requirement | Acceptance criteria |
|---|---|
| FR-MPR-001–006 | AC-MPR-001–003 |
| FR-MPR-007–010 | AC-MPR-004–006, AC-MPR-013–014 |
| FR-MPR-011–015 | AC-MPR-007–012, AC-MPR-014 |
| FR-MPR-016–017 | AC-MPR-006, AC-MPR-013–014 |
| C-MPR-001–008 | AC-MPR-001–006, AC-MPR-009, AC-MPR-011, AC-MPR-014 |

## 10. Open Questions

- None. D-MPR-003 defines the inventory and all count-dependent outputs dynamically through
  `discovered_species_count`; the richness TIFF remains excluded regardless of inventory size.
