# Feature: HTML report integrated follow-up hardening — value-safe columns, fallback disclosure, and row-preserving geometry

> Status: DRAFT — awaiting user review and explicit approval
> Owner: spec-writer
> Last updated: 2026-09-02
> Extends without replacing: `specs/html-report-integrated-followup.md`

## 1. Summary

This hardening follow-up makes three previously implicit data-integrity behaviors explicit and
testable. It requires collision suffixes to be applied to both column headers and every row's
corresponding value key without value loss, requires any permitted fallback to disclose its use
and the resulting known or unverifiable completeness limits while retaining successful data, and
requires malformed geometry to be handled per row so that the row's attributes, joins, and
non-geometry counts survive while only its invalid map geometry is excluded.

This specification is additive. Every non-superseded requirement, constraint, assumption, edge
case, acceptance criterion, and decision in `specs/html-report-integrated-followup.md` remains
normative and unchanged, including the approved rule that geometry normalization discards Z/M and
uses valid X/Y only. This task changes specifications only; it does not authorize implementation,
test, fixture, generated-project, Git, or existing approved-spec changes.

## 2. Compatibility and terminology

- **Final column key:** The unique internal key allocated to one logical source column after the
  deterministic collision rule in FR-IRF-011 is applied. It is the single authoritative key used
  by the column definition, every integrated row, detail/export projection, and CSV header/value
  projection for that logical source column.
- **Fallback:** Any fallback path already permitted by the approved baseline and actually used
  because the authoritative/direct data-access path could not provide the intended data. This
  specification does not add or broaden circumstances in which fallback is permitted.
- **Known omission:** A table or row that can be identified as intended input but was not
  collected.
- **Unverifiable scope:** A table set, table, or row set whose presence or completeness cannot be
  established after the direct-access failure. An unknown count must remain described as unknown;
  it must not be represented as zero or complete.
- **Malformed geometry row:** A collected source row whose geometry cannot be parsed, normalized,
  transformed, or serialized as valid X/Y map geometry. Geometry invalidity does not by itself
  invalidate the row's attributes, established FK joins, stable identity, or eligibility for
  source-row-based non-geometry counts and aggregations.

## 3. Functional Requirements

### 3.1 Collision-safe final keys and row values

- **FR-IRF-027 (D-IRF-006 column/value key atomicity):** When two or more logical source columns
  collide and FR-IRF-011 allocates an unsuffixed key and one or more suffixed final column keys,
  the report must create one deterministic source-column-to-final-key mapping before integrated
  rows are serialized. The same mapping must govern the column definition and every row value:
  for every row, each present source value must be stored under the exact final key allocated to
  that source column, including its suffix. A value belonging to a suffixed column must not remain
  only under the unsuffixed key, be written under a different suffix, overwrite another column's
  value, or disappear from the integrated table, detail data, report payload, or CSV. Null,
  empty-string, zero, and false values must retain their original value semantics under the
  allocated final key; the collision process must not convert them into absence or another
  column's value.

### 3.2 Truthful fallback and partial-success reporting

- **FR-IRF-028 (D-IRF-007 fallback disclosure and partial success):** Whenever a fallback already
  permitted by the approved baseline is actually used, including loaded-layer fallback after
  direct GPKG access failure, the generated report must contain a user-visible limitation notice
  that states (a) that fallback occurred, (b) which authoritative/direct access failed or was
  unavailable, (c) every known omitted table and known omitted row or row scope that can be
  identified, and (d) every table or row scope whose completeness cannot be verified. When an
  omitted or unverifiable row count cannot be determined, the report must label the count or
  completeness as unknown/unverified rather than zero or complete. The fallback notice must not
  suppress successfully collected tables or rows: all successful data must continue through the
  existing map, integrated-table, detail, summary/chart, filter/sort, and CSV behavior to the
  extent supported by that data. The report must not claim or imply a complete direct-GPKG
  inventory while any such limitation remains.

### 3.3 Row-preserving malformed geometry handling

- **FR-IRF-029 (D-IRF-008 row-level malformed geometry isolation):** Geometry processing must
  isolate malformed geometry at the source-row level. A malformed geometry must not abort,
  discard, or mark the entire source table as failed. The affected row must retain its stable
  identity, all readable attributes, established FK-joined data, integrated-table/detail/CSV
  presence, and eligibility for every source-row-based non-geometry count or aggregation that it
  would have had with valid geometry. Its geometry must receive a stable invalid-geometry reason
  and be excluded from map rendering; it must not receive fabricated or substitute coordinates.
  Geometry-valid rows from the same table and from other tables must continue to render on the
  map. Geometry-validity counts or limitations must classify the affected row as invalid without
  changing its non-geometry source-row counts. Before validity is assessed, the existing approved
  dimensionality policy remains in force: Z/M ordinates are discarded, valid X/Y is used, and
  missing or malformed X/Y remains invalid even if Z/M exists.

## 4. Constraints

- **C-IRH-001:** This hardening specification is an additive normative extension of
  `specs/html-report-integrated-followup.md`. It does not delete, renumber, reuse, weaken, or
  silently rewrite any existing ID or requirement.
- **C-IRH-002:** Collision resolution may rename only report/output keys under the approved
  deterministic naming policy. It must not mutate source schemas, source field names, or source
  values.
- **C-IRH-003:** Fallback disclosure must be truthful about what is known and unknown. The system
  must not infer nonexistent tables/rows, fabricate counts, or describe an unverifiable scope as
  complete.
- **C-IRH-004:** Malformed-geometry isolation changes only report handling of the affected
  geometry. It must not repair or mutate source geometry, invent a different anchor, alter FK
  relationships, or override the approved Type 1-Type 4 anchor precedence.
- **C-IRH-005:** The approved Z/M removal contract in FR-IRF-026 and AC-IRF-017 remains unchanged.
  This hardening neither preserves Z/M in output geometry nor treats valid Z/M as a substitute
  for invalid or missing X/Y.

## 5. Assumptions

- **A-IRH-001:** The deterministic source schema order and collision suffix allocation remain
  those already defined by FR-IRF-011; this follow-up clarifies value-key consistency and does not
  introduce a new suffix-order algorithm.
- **A-IRH-002:** A failed direct-access path may leave some table or row scope unknowable. In that
  case, explicit unknown/unverified disclosure satisfies the reporting contract; inventing a
  table name or count does not.
- **A-IRH-003:** “Counts are preserved” means that malformed geometry alone does not remove the
  row from source-record counts or non-geometry aggregations. Existing domain filters, orphan
  rules, null handling, and aggregation eligibility remain authoritative.

## 6. Edge Cases

- **E-IRH-001:** Three logical columns collide, and some rows contain zero, false, an empty string,
  null, or no source value. Each column uses its own allocated final key in every row; present
  falsy/null values preserve their semantics, and a genuinely absent source value is not filled
  from a colliding column.
- **E-IRH-002:** A collision is discovered after some rows have already been assembled. Before
  report serialization, all affected row values must still be remapped to the same final keys as
  the finalized column definitions; mixed old/new keys or partially migrated rows are invalid.
- **E-IRH-003:** Direct GPKG access fails, loaded-layer fallback returns some valid rows, and one or
  more registered or possible tables/rows cannot be verified. The successful rows remain usable,
  while the report distinguishes known omissions from unknown/unverified completeness.
- **E-IRH-004:** One table fails or falls back while another table is collected successfully. The
  successful table remains in all applicable report views, and the failed/fallback table's exact
  known or unverifiable limitation is disclosed without turning the entire report into a failure.
- **E-IRH-005:** A table contains valid geometries before and after one malformed geometry. The
  malformed row remains in table/detail/CSV and applicable non-geometry counts, is counted in the
  invalid-geometry limitation, and is absent only from map geometry; both valid rows render.
- **E-IRH-006:** A malformed Type 2/3 anchor row has readable attributes and valid child joins.
  The joined rows and source-based counts remain, but no child geometry is promoted and no
  replacement coordinate is invented contrary to the approved anchor rules.
- **E-IRH-007:** A dimensional geometry contains valid X/Y and additional Z/M ordinates. Z/M is
  removed and the valid X/Y geometry may render. If the same row instead has malformed X/Y, the
  row-preservation rule applies and its geometry is excluded even when Z/M ordinates are valid.

## 7. Out of Scope

- Changing the approved collision normalization or suffix-allocation order.
- Adding new fallback sources or broadening the conditions under which fallback is permitted.
- Guaranteeing completeness when direct GPKG access and available fallback cannot establish it.
- Repairing malformed geometry, partially salvaging malformed geometry components, or deriving
  substitute geometry from attributes, joins, centroids, Z/M ordinates, or other rows.
- Changing Type 1-Type 4 anchor selection, source schemas, source records, or established
  non-geometry aggregation rules.
- Creating or modifying tests, application code, fixtures, generated projects, or Git state.

## 8. Acceptance Criteria

- **AC-IRF-018 (FR-IRF-027 — collision value preservation):** Given at least three logical source
  columns that normalize to the same base key and rows containing distinct sentinel values,
  including zero, false, empty string, and null, when the integrated report and CSV are produced,
  then the column definitions expose deterministic unique keys using the approved suffix order;
  every present value appears under the exact final key allocated to its source column in every
  row, detail/payload projection, and CSV cell; no value appears only under a stale or different
  suffix; and no colliding value is overwritten, shifted to another column, or lost. A repeated
  export with unchanged schema and data produces the same key-to-value mapping.
- **AC-IRF-019 (FR-IRF-028 — fallback disclosure with partial success):** Given a direct GPKG
  access failure that triggers an approved loaded-layer fallback, where fallback returns at least
  one successful table/row and leaves at least one table or row scope known to be omitted or
  impossible to verify, when the report is opened, then a user-visible limitation notice states
  that fallback occurred and identifies the failed direct path; lists each identifiable omitted
  table/row scope; labels every unknowable count or completeness scope as unknown/unverified, not
  zero or complete; and does not claim a complete direct-GPKG inventory. The successfully
  collected data remains present and usable in every applicable map, table, detail, summary/chart,
  filter/sort, and CSV surface.
- **AC-IRF-020 (FR-IRF-029 — malformed geometry row isolation):** Given one spatial table with at
  least two valid-geometry rows and one malformed-geometry row whose attributes, established FK
  joins, and source-based count membership are otherwise valid, when the report is generated,
  then generation and table processing succeed; all three rows retain their attributes and
  applicable joined data in the integrated table, detail data, and CSV; all three contribute to
  the same applicable source-row-based non-geometry counts/aggregations they would contribute to
  absent geometry invalidity; the malformed row has a stable invalid-geometry reason and is
  included in the invalid-geometry limitation count but has no rendered or fabricated geometry;
  and both valid rows render on the map. For dimensional inputs, Z/M is removed before this
  determination, valid X/Y continues to render, and malformed/missing X/Y remains map-invalid.

## 9. Open Questions

None. The stakeholder explicitly fixed all three hardening behaviors in this request. The
existing unresolved questions in `specs/html-report-integrated-followup.md` remain unchanged and
must still be resolved according to that approved baseline where applicable.

## 10. Decision Log

- **D-IRF-006** (2026-09-02, Category B — collision suffix/value-key clarification): The
  stakeholder explicitly required that whenever identical integrated-table column names receive
  suffixes, every row's corresponding value must move to the exact same suffixed key, with no
  value loss. This adds FR-IRF-027 and AC-IRF-018. It clarifies FR-IRF-010/011/014 and AC-IRF-007
  without changing the approved normalization or suffix-allocation order.
- **D-IRF-007** (2026-09-02, Category B — fallback completeness disclosure clarification): The
  stakeholder explicitly required that direct GPKG access failure or another permitted fallback
  be disclosed in the report together with limitations for omitted tables/rows or scopes whose
  completeness cannot be verified, while successful data continues to display. This adds
  FR-IRF-028 and AC-IRF-019. It strengthens the observable contract of FR-IRF-024,
  E-IRF-002/011, and AC-IRF-015 without authorizing new fallback conditions.
- **D-IRF-008** (2026-09-02, Category B — malformed geometry row-isolation clarification): The
  stakeholder explicitly required malformed geometry to be preserved at row granularity rather
  than failing an entire table: attributes, joined data, and applicable counts remain; only the
  invalid geometry is excluded from the map; and other valid rows continue to render. This adds
  FR-IRF-029 and AC-IRF-020. It clarifies FR-IRF-007/009/026 and AC-IRF-005/017 while retaining the
  approved Z/M removal policy exactly.

## 11. References and approval gate

Normative references: `CLAUDE.md`, `docs/change-control.md`,
`specs/html-report-integrated-followup.md`, and `specs/TEMPLATE.md`. The approved baseline's own
normative references remain in force through that specification.

This document remains DRAFT until the user explicitly approves it. After approval, a fresh
test-designer may update acceptance tests and traceability; implementation must wait for the
separate acceptance-test approval gate.
