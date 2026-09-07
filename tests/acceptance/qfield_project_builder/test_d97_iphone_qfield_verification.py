"""D-97 iPhone-QField acceptance gates that no local runner can automate.

The structural counterparts are AC-QPB-147 checks in
``test_qfield_plugin_toolbar_icons.py``. These skipped tests deliberately require recorded manual
evidence from QField on an iPhone; source, URI, XML, QGIS Desktop, and simulated-device results do
not satisfy them.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.device


@pytest.mark.skip(
    reason=(
        "AC-QPB-146 / FR-QPB-072 (further clarified; Decision Log D-97) requires real iPhone "
        "QField verification and cannot be automated by this harness. "
        "\n\nManual QA steps: (1) Build an online project with the selected VWorld layer "
        "Satellite, a VWorld key accepted for that WMTS service, and the existing key-embedding "
        "consent accepted. (2) Transfer that unchanged project to an iPhone running QField and "
        "use a network connection able to reach VWorld. (3) Open the project and confirm the map "
        "renders Satellite imagery. (4) Confirm QField shows no missing-layer, repair-data-source, "
        "or equivalent source-repair warning. (5) Record the application/project build identity, "
        "QField version, iOS version, selected layer (Satellite), network condition, and pass/fail "
        "observations. Do not record or attach the VWorld key. A parsed URI/XML or desktop-QGIS "
        "result is not a substitute for this iPhone result."
    )
)
def test_ac146_iphone_qfield_satellite_renders_without_source_repair_warning():
    raise AssertionError("should never run while skipped -- see skip reason")


@pytest.mark.skip(
    reason=(
        "AC-QPB-148 / FR-QPB-143 (Decision Log D-97) requires real iPhone QField visual and "
        "VoiceOver verification and cannot be automated by this harness. "
        "\n\nManual QA steps: (1) Build an identification-enabled project and transfer that "
        "unchanged project to an iPhone running QField. (2) Show its plugin toolbar. (3) Confirm "
        "exactly two nonblank 48px-by-48px icon-only targets appear: report export and plant "
        "identification. Confirm neither has visible button text and no duplicate toolbar control "
        "appears. (4) Activate each target and confirm it invokes its existing action. (5) Inspect "
        "the controls with VoiceOver (or the equivalent iPhone accessibility inspector) and "
        "confirm "
        "the names are exactly 'HTML 보고서 내보내기' and '사진으로 식물 동정'. (6) Record the "
        "application/project build identity, QField version, iOS version, and pass/fail "
        "observations. "
        "Do not record or attach any VWorld or Pl@ntNet key. Source inspection is not a substitute "
        "for this iPhone result."
    )
)
def test_ac148_iphone_qfield_toolbar_icons_are_nonblank_nonduplicated_and_accessible():
    raise AssertionError("should never run while skipped -- see skip reason")
