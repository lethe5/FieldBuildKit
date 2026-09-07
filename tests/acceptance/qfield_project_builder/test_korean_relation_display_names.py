"""Korean relation-widget display names on the generated project's real QGIS relations (Section
8.6, FR-QPB-128, AC-QPB-111; Decision Log D-73/D-77).

Covers:
- AC-QPB-111: Given a generated project for any survey type, when each embedded child-relation
  widget's underlying `QgsRelation` is inspected, then its `id()` is unchanged from the existing
  stable relation-ID convention (FR-QPB-056; e.g. `rel_observation_survey`) and its `name()` is
  the corresponding Korean display name from Section 8.6's confirmed mapping — never the raw
  relation-ID string.

Per Decision Log D-77's own "Approval status" line, Section 8.6's Korean relation-display-name
table is now fully stakeholder-confirmed (six of the seven proposed names exactly as proposed; the
seventh, `rel_observation_survey`, corrected from "관찰" to "식물관찰") and `test-designer`/
`implementer` work may proceed against FR-QPB-128/Section 8.6/AC-QPB-111. Unlike the earlier
Decision Log D-56/D-57/D-58 Korean field-alias round, FR-QPB-128's and AC-QPB-111's own body text
was itself updated in place by Decision Log D-77 (struck-through historical "draft proposal, not
yet stakeholder-approved" text plus a live "confirmed by Decision Log D-77" annotation) — so, unlike
that earlier round, no separate "why this round could proceed despite stale wording" note is needed
here.

**Current, pre-fix state confirmed by direct code reading (`qfield_builder/qgis_worker.py`'s
`_add_relations()`):** `relation.setId(fk.relation_id)` and `relation.setName(fk.relation_id)` are
both currently called with the exact same raw string (e.g. `rel_observation_survey`) — the
relation's own stable ID and its separate, human-facing "name" property are identical today. Every
test below is therefore expected to **fail** (not error/skip) once `qfield_builder.acceptance_api.
inspect_relations` exists and is run against the current, not-yet-fixed `_add_relations()` — this is
the correct, expected red state for a not-yet-implemented change; each test's own name-mismatch
assertion is written to fail with a message that names the still-raw relation-ID string it observed
in place of the expected Korean display name.

**Scope: exactly the seven relations Section 8.6 lists — `rel_observation_photo_observation` is
deliberately never mentioned anywhere in this file.** Section 8.6/Decision Log D-73 explicitly
excludes `rel_observation_photo_observation` from its Korean-display-name proposal, because a
separate, related round (Decision Log D-74) removes the `observation_photo` table — and therefore
this relation — entirely for Type 2/3. Whether D-74's schema change has itself landed in
`qfield_builder/schemas.py` as of any given point in this repository's history is immaterial to
this file: no test here asserts anything, positive or negative, about
`rel_observation_photo_observation`'s own existence, absence, `id()`, or `name()` — this file is
scoped, deliberately, to exactly the seven relations `KOREAN_RELATION_DISPLAY_NAMES` (`conftest.py`)
lists, so it is correct regardless of whether that eighth relation currently exists.

See `HARNESS_CONTRACT.md`'s new "Decision Log D-73/D-77" section, function 18
(`inspect_relations`), for why a dedicated PyQGIS-backed harness function is used here rather than
a raw `.qgs` XML regex (unlike AC-QPB-013's `RelationReference` check) — the exact QGIS
project-XML `<relations>` block's attribute-serialization shape was not independently confirmed
against a live QGIS instance, per this project's hard QGIS-isolation rule barring the test-designer
from constructing a `QgsApplication` for any verification purpose; the judgment is delegated to the
harness function's own real-PyQGIS-backed implementation, mirroring the established
`inspect_field_aliases`/`inspect_editor_widget` precedent.

**Disclosed, not-yet-independently-verified technical caveat (Decision Log D-73/D-77, carried
forward unaffected by the Korean-terminology confirmation) is deliberately NOT tested by the
automated tests below.** AC-QPB-111's own text is explicit that it "asserts only the `QgsRelation`
object's own configured `id()`/`name()` values, independently of the disclosed, not-yet-verified
question of exactly which mechanism drives the widget's on-screen rendered label" — whether
`QgsRelation.name()` is actually what QGIS/QField paints on screen for the embedded widget (as
opposed to some other, not-yet-identified override) remains unconfirmed, and confirming it is
implementer-verification work to report back, mirroring the existing Decision Log D-36/FR-QPB-111
convention for this class of uncertainty. A `manual`/`device`-marked placeholder test at the bottom
of this file records this explicitly, rather than silently leaving it untested with no record at
all.
"""
from __future__ import annotations

import pytest

from .conftest import KOREAN_RELATION_DISPLAY_NAMES

pytestmark = pytest.mark.qgis


def _relation_cases():
    cases = []
    ids = []
    for relation_id, info in KOREAN_RELATION_DISPLAY_NAMES.items():
        for survey_type in info["survey_types"]:
            cases.append((survey_type, relation_id, info["display_name"]))
            ids.append(f"{survey_type}-{relation_id}")
    return cases, ids


_RELATION_CASES, _RELATION_IDS = _relation_cases()


# --- AC-QPB-111 ------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "survey_type,relation_id,expected_display_name", _RELATION_CASES, ids=_RELATION_IDS
)
def test_ac111_relation_id_is_unchanged_and_name_is_the_confirmed_korean_display_name(
    inspect_relations, built_project_by_type, survey_type, relation_id, expected_display_name
):
    """FR-QPB-056's stable relation-ID convention is unchanged by this requirement (regression
    guard: `relation_id` must still be present, exactly as before), while the same relation's
    separate `name()` property must be the Section 8.6-confirmed Korean display name — never the
    raw relation-ID string this codebase currently sets it to (`_add_relations()`,
    `qfield_builder/qgis_worker.py`)."""
    result = built_project_by_type(survey_type)
    assert result["success"], result.get("error_message")

    info = inspect_relations(result["project_dir"])

    # Regression guard: the relation's own stable ID (FR-QPB-056) must be completely unaffected
    # by this requirement -- `relation_ids` (keyed, per HARNESS_CONTRACT.md function 18, exactly
    # like `QgsRelationManager.relations()` itself is keyed, by each relation's own `id()`) must
    # still contain this exact ID string.
    assert relation_id in info["relation_ids"], (
        f"AC-QPB-111/FR-QPB-056: expected the stable relation ID {relation_id!r} to still be "
        f"present, unchanged, on the generated {survey_type} project — got relation_ids="
        f"{sorted(info['relation_ids'])!r}"
    )
    assert relation_id in info["names"], (
        f"AC-QPB-111: expected {relation_id!r} to have a configured name() reported for the "
        f"generated {survey_type} project — got names={info['names']!r}"
    )

    actual_display_name = info["names"][relation_id]
    assert actual_display_name == expected_display_name, (
        f"AC-QPB-111/FR-QPB-128: {survey_type}.{relation_id}'s configured display name "
        f"(QgsRelation.name()) must be the Section 8.6-confirmed Korean text "
        f"{expected_display_name!r} (Decision Log D-73/D-77) — got {actual_display_name!r}"
    )
    assert actual_display_name != relation_id, (
        f"AC-QPB-111/FR-QPB-128: {survey_type}.{relation_id}'s configured display name must never "
        f"be the raw relation-ID string itself — got {actual_display_name!r}, exactly the "
        f"pre-fix bug this requirement closes (`relation.setName(fk.relation_id)`, "
        f"`qfield_builder/qgis_worker.py`'s `_add_relations()`)"
    )


# --- Disclosed rendering-mechanism caveat (Decision Log D-73/D-77) -- manual/device placeholder --

@pytest.mark.skip(
    reason=(
        "AC-QPB-111/Section 8.6/Decision Log D-73/D-77 explicitly disclose, and deliberately do "
        "not resolve, whether QgsRelation.name() is actually the mechanism QGIS Desktop/QField "
        "use to paint the on-screen label of an embedded QgsAttributeEditorRelation widget, as "
        "opposed to some other, not-yet-identified override -- not automatable by this harness, "
        "and explicitly recorded as a *plausible but not yet confirmed* mechanism, not a settled "
        "fact (mirroring Decision Log D-36/FR-QPB-111's identical convention for this class of "
        "uncertainty). "
        "\n\nManual QA steps: (1) Build a project for any survey type with a parent/child "
        "relation (e.g. temporary_plots' rel_survey_site). (2) Open the generated project in a "
        "real QGIS Desktop install and, separately, in a real QField session on a device. "
        "(3) Open the parent record's own attribute form (e.g. `site`) and locate the embedded "
        "child-relation widget/tab (e.g. the 'survey' relation). (4) Confirm the widget's own "
        "on-screen label/tab title reads the Section 8.6-confirmed Korean text (e.g. '조사'), not "
        "the raw relation ID (e.g. 'rel_survey_site') and not some other unexpected string. "
        "(5) If the rendered label does not reflect QgsRelation.name() at all -- e.g. QGIS/QField "
        "instead render the *referenced layer's* own name, or some other property entirely -- "
        "report that as a concrete implementer finding per Decision Log D-73, rather than "
        "silently assuming the automated id()/name() checks above are sufficient on their own."
    )
)
def test_ac111_embedded_widget_actually_renders_the_configured_korean_name_on_screen():
    raise AssertionError("should never run while skipped -- see skip reason")
