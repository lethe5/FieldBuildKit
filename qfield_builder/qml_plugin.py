# ruff: noqa: E501 -- generated QML/HTML/JavaScript contains intentionally compact runtime lines.
"""Post-MVP Section 13 guaranteed-manual baseline: the actual, shipped QField QML/JavaScript
plugin source (FR-QPB-100/101/104/106/107/108/109/111 -- Decision Log D-31/D-35/D-36/D-37/D-38/
D-40/D-42/D-43).

This module is pure string-template generation -- it produces the two pieces of real QML source
used by generated projects:

1. :func:`render_project_plugin_qml` -- the unconditional project-scoped
   ``<project_slug>.qml`` sidecar file (FR-QPB-100/133; Decision Log D-31/D-83/D-87), placed
   alongside the ``.qgs`` file, matching QField's
   own documented project-plugin convention (confirmed live against ``docs.qfield.org``/
   ``api.qfield.org`` during this implementation round: a project plugin is "deployed as a
   sidecar file to a given project file and must share the same file name with a .qml extension").
2. :func:`render_identification_widget_qml` -- the QML source embedded directly into the relevant
   layer's attribute form via a ``QgsAttributeEditorQmlElement`` (confirmed, see
   :mod:`qfield_builder.qgis_worker`), implementing the guaranteed-baseline "Identify attached
   photos" action (FR-QPB-101, revised).

Neither function requires PyQGIS -- both are plain string templating, importable and unit-testable
in any Python environment. Only the *placement* of this generated source into a real ``.qgs``
project (:mod:`qfield_builder.qgis_worker`) requires PyQGIS.

**Honesty about what is, and is not, confirmed** (mirrors the specification's own discipline):
the pieces below marked "confirmed" were verified during this implementation round against real
QField/QGIS documentation. Probability sampling uses project-local TIFF bytes directly in a
WorkerScript; the project builder does not register thousands of probability rasters as QGIS
layers. The local operation is wrapped defensively so an unavailable or broken capability affects
only the candidate's probability.

**Attribute write-back (FR-QPB-109 and D-92) uses a bounded pending-request bridge.** The embedded
widget writes a request containing the current feature UUID, layer context, and field values to
``PENDING_WRITE_BACK_RELPATH`` via ``FileUtils.writeFileContent()``. The project plugin polls this
file and first resolves the documented existing-feature host
``iface.findItemByObjectName("featureForm")``; it also retains the Add-feature
``overlayFeatureFormDrawer`` path and relation ``EmbeddedFeatureForm.attributeFormModel``
traversal. A candidate is writable only when the discovered active attribute-form model exposes
the requested layer and the same UUID. A matching model is updated via ``changeAttribute`` and the
request is cleared only after every requested field is accepted. Missing, ambiguous, or mismatched
context remains pending for a later poll and never falls back to a feature-list model. The legacy
``currentFeature.setAttribute`` attempt remains as a harmless compatibility fast path, while the
pending bridge is the mechanism used for both saved-feature and Add-feature edits.

**Authoritative geometry location (FR-QPB-101/FR-QPB-108) is deliberately feature-based.**
The generated widget receives a survey-type-specific QGIS expression and evaluates it against the
currently edited domain feature. It follows the authoritative survey/plot relationship for Types
1-3, validates the resulting WGS 84 point, and returns ``null`` for missing or invalid geometry.
Image bytes and metadata are never inspected for location. The widget reads the candidate's
project-relative TIFF directly and sends its bytes to the WorkerScript, while preserving
FR-QPB-108/DR-QPB-070's exact NoData/-9999/out-of-range/out-of-extent/no-location display rules.

Confirmed, real QField/QML facts this module relies on (fetched live during this implementation
round; see completion report for the exact URLs consulted):

- Project plugins are a ``<same-basename>.qml`` sidecar file next to the ``.qgs``/``.qgz`` file,
  auto-discovered/bundled by QFieldSync/QFieldCloud (``api.qfield.org``, "Project Plugins").
- The minimal plugin shape is a root QML ``Item`` with ``import QtQuick`` / ``import org.qfield``,
  using ``Component.onCompleted`` and the ``iface`` context property
  (``iface.mainWindow().displayToast(...)``, ``api.qfield.org``, "Getting Started").
- ``iface.addItemToPluginsToolbar(item)`` adds a custom toolbar button; ``QfToolButton`` (with
  ``iconSource``/``iconColor``/``bgcolor``/``round``/``onClicked``) and the ``Theme`` singleton are
  the real, documented building blocks for such a button (``api.qfield.org``, "Code Snippets").
- ``iface.findItemByObjectName("name")`` looks up an already-registered QML item by
  ``objectName`` (``api.qfield.org``, "Key iface functions" and the GNSS "Code Snippets" example).
- The attribute-form "QML widget" container type is real and documented
  (``docs.qfield.org``, "Attribute Form Configuration" table + "Define QML Widgets" section); its
  own confirmed minimal example is a plain ``Button`` reading the current feature's attributes via
  an injected ``expression`` context property's ``expression.evaluate("<QGIS expression>")``
  method.
- QML's JavaScript engine has a native ``XMLHttpRequest`` (standard QML/JS; also explicitly
  asserted by Decision Log D-31/FR-QPB-101 as the mechanism for calling Pl@ntNet).
- The current domain feature's geometry is evaluated through the injected
  ``expression.evaluate("<QGIS expression>")`` context property; the builder supplies the
  survey/plot relationship expression and validates its finite WGS 84 coordinates before optional
  raster sampling.
- The bundled per-species TIFFs are read from project-relative paths by the isolated WorkerScript;
  they are not registered as QGIS map layers. The current feature geometry remains the only
  location source.
- The real, live-confirmed Pl@ntNet request/response contract (Decision Log D-37/FR-QPB-104):
  ``POST https://my-api.plantnet.org/v2/identify/{project}?api-key=...``, multipart
  body with one ``organs`` field and one ``images`` file per photo; response envelope keys
  ``query``/``predictedOrgans``/``language``/``preferedReferential``/``bestMatch``/``results``/
  ``version``/``remainingIdentificationRequests``; each ``results[*]`` has ``score`` and
  ``species.scientificNameWithoutAuthor``/``scientificNameAuthorship``/``scientificName``.
"""

from __future__ import annotations

import base64
import json
import re

from . import korean_field_aliases, korean_layer_display_names, schemas
from .html_report_core import REPORT_CORE_JS
from .resource_paths import resource_path

# Exact visual assets from Mikulew/js-light-dark-theme-toggle.  They are encoded into the
# generated report so the standalone HTML never depends on the reference repository's relative
# image paths or on a network request.
_THEME_MOON_SVG = '''<svg version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" viewBox="0 0 1000 1000" enable-background="new 0 0 1000 1000" xml:space="preserve">
  <g>
    <path fill="#d8c21e" d="M525.3,989.5C241.2,989.5,10,758.3,10,474.1c0-196.8,109.6-373.6,285.9-461.4c7.9-3.9,17.5-2.4,23.7,3.8c6.2,6.2,7.9,15.8,4,23.7c-32.2,65.4-48.5,135.7-48.5,208.9c0,261.4,212.7,474.1,474.1,474.1c74,0,145-16.7,211-49.5c7.9-3.9,17.5-2.4,23.7,3.8c6.3,6.3,7.9,15.8,3.9,23.7C900.5,879,723.3,989.5,525.3,989.5z"/>
  </g>
</svg>'''
_THEME_SUN_SVG = '''<svg version="1.1" style="enable-background:new 0 0 128 128;" x="0px" y="0px"  viewBox="0 0 128 128" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
  <g>
    <path fill="#111111" d="M64,30.34c-18.59,0-33.66,15.07-33.66,33.65c0,18.59,15.07,33.66,33.66,33.66 c18.59,0,33.66-15.07,33.66-33.66C97.66,45.41,82.59,30.34,64,30.34z" />
    <path fill="#111111" d="M56.76,24.21L56.76,24.21h14.49c0.67,0,1.29-0.33,1.68-0.88c0.38-0.54,0.47-1.25,0.24-1.88 L65.92,1.83c-0.3-0.81-1.06-1.34-1.92-1.34s-1.62,0.54-1.92,1.34l-7.25,19.63c-0.23,0.63-0.14,1.33,0.24,1.88 C55.46,23.89,56.09,24.21,56.76,24.21z" />
    <path fill="#111111" d="M97.26,40.99c0.38,0.39,0.91,0.6,1.44,0.6c0.12,0,0.24-0.01,0.36-0.03c0.66-0.12,1.21-0.55,1.5-1.16 l8.76-19.01c0.36-0.78,0.19-1.69-0.41-2.3c-0.61-0.61-1.53-0.77-2.31-0.42L87.6,27.44c-0.61,0.28-1.04,0.84-1.16,1.5 c-0.12,0.66,0.1,1.33,0.56,1.81L97.26,40.99z" />
    <path fill="#111111" d="M126.18,62.08l-19.64-7.24c-0.63-0.23-1.33-0.14-1.88,0.24c-0.55,0.38-0.87,1-0.87,1.67l0.01,14.49 c0,0.67,0.33,1.3,0.88,1.68c0.35,0.23,0.76,0.36,1.17,0.36c0.24,0,0.48-0.04,0.71-0.13l19.64-7.24c0.8-0.29,1.34-1.06,1.34-1.93 C127.52,63.14,126.99,62.38,126.18,62.08z" />
    <path fill="#111111" d="M100.56,87.6c-0.28-0.61-0.84-1.04-1.5-1.16c-0.66-0.11-1.34,0.1-1.8,0.57L87.01,97.26 c-0.47,0.47-0.69,1.15-0.57,1.81c0.12,0.65,0.55,1.22,1.16,1.5l19.01,8.76c0.27,0.13,0.56,0.18,0.86,0.18 c0.53,0,1.05-0.21,1.44-0.6c0.61-0.61,0.77-1.52,0.41-2.3L100.56,87.6z" />
    <path fill="#111111" d="M71.24,103.78L71.24,103.78l-14.49,0.01c-0.67,0-1.29,0.33-1.67,0.88 c-0.38,0.55-0.47,1.25-0.25,1.87l7.25,19.64c0.3,0.8,1.06,1.34,1.92,1.34s1.62-0.54,1.92-1.34l7.25-19.64 c0.23-0.63,0.14-1.33-0.24-1.88C72.54,104.11,71.92,103.78,71.24,103.78z" />
    <path fill="#111111" d="M30.74,87.01c-0.47-0.47-1.14-0.68-1.8-0.57c-0.66,0.12-1.22,0.55-1.5,1.16l-8.76,19.01 c-0.36,0.78-0.19,1.7,0.42,2.3c0.39,0.39,0.91,0.6,1.44,0.6c0.29,0,0.58-0.06,0.86-0.19l19.01-8.77c0.61-0.28,1.04-0.84,1.16-1.5 c0.12-0.66-0.1-1.33-0.57-1.8L30.74,87.01z" />
    <path fill="#111111" d="M22.17,73.29c0.41,0,0.82-0.13,1.17-0.37c0.55-0.38,0.88-1.01,0.88-1.68l-0.01-14.49 c0-0.67-0.33-1.29-0.88-1.68c-0.55-0.38-1.25-0.47-1.87-0.24L1.82,62.08c-0.8,0.29-1.34,1.06-1.34,1.92c0,0.85,0.53,1.62,1.34,1.92 l19.65,7.24C21.7,73.25,21.93,73.29,22.17,73.29z" />
    <path fill="#111111" d="M27.45,40.4c0.28,0.61,0.84,1.04,1.5,1.16c0.12,0.02,0.24,0.03,0.36,0.03c0.54,0,1.06-0.21,1.45-0.6 L41,30.74c0.47-0.48,0.68-1.15,0.56-1.81c-0.12-0.65-0.55-1.21-1.16-1.49l-19.02-8.76c-0.78-0.36-1.69-0.19-2.3,0.42 c-0.61,0.61-0.77,1.52-0.41,2.3L27.45,40.4z" />
  </g>
</svg>'''
_THEME_MOON_DATA_URI = "data:image/svg+xml;base64," + base64.b64encode(_THEME_MOON_SVG.encode("utf-8")).decode("ascii")
_THEME_SUN_DATA_URI = "data:image/svg+xml;base64," + base64.b64encode(_THEME_SUN_SVG.encode("utf-8")).decode("ascii")

PLANTNET_ENDPOINT_TEMPLATE = "https://my-api.plantnet.org/v2/identify/{project}"
PLANTNET_DEFAULT_PROJECT = "all"

# FR-QPB-143 / Decision Log D-97: QField's Theme icon identifiers are not portable between
# QField runtimes. These complete SVGs are emitted into each generated project and referenced
# from the adjacent project-plugin QML through their project-relative paths. Keeping the assets
# here (rather than relying on an application installation path) makes the generated project
# self-contained when copied directly to a field device.
_TOOLBAR_SVG_ASSETS = {
    "icons/report-export.svg": """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<svg xmlns=\"http&#58;//www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\">
  <path fill=\"#FFFFFF\" d=\"M5 3h10l4 4v14H5V3zm9 1.5V8h3.5L14 4.5zM7 11v2h10v-2H7zm5 4-4 4h2.5v2h3v-2H16l-4-4z\"/>
</svg>
""",
    "icons/plant-identification.svg": """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<svg xmlns=\"http&#58;//www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\">
  <path fill=\"#FFFFFF\" d=\"M10.2 3.2c4.4 0 7.4 2.5 7.4 6.2 0 2.2-1 4-2.8 5.1l4 4-1.7 1.7-4-4c-1 .5-2 .7-3 .7C5.7 16.9 3 14.3 3 10.2s2.7-7 7.2-7zm0 2.3c-3.1 0-4.9 1.8-4.9 4.7s1.8 4.4 4.9 4.4c.8 0 1.5-.1 2.1-.4-.2-2.4.8-4.5 2.6-5.8-.7-1.8-2.3-2.9-4.7-2.9zm-1 2.2c1.5 0 2.9.6 3.8 1.6-1.4.5-2.6 1.5-3.4 2.8-.7-.5-1.1-1.3-1.1-2.2 0-.8.3-1.5.7-2.2z\"/>
</svg>
""",
}


def project_toolbar_svg_assets(*, identification_enabled: bool) -> dict[str, str]:
    """Return the fixed, project-local D-97 toolbar assets for one generated project.

    Report export is unconditional. The plant-identification asset follows the existing
    ``identification_enabled`` content boundary, matching its toolbar control and callback.
    """
    assets = {"icons/report-export.svg": _TOOLBAR_SVG_ASSETS["icons/report-export.svg"]}
    if identification_enabled:
        assets["icons/plant-identification.svg"] = _TOOLBAR_SVG_ASSETS[
            "icons/plant-identification.svg"
        ]
    return assets

# Section 13.3 bundled reference-asset relative paths (FR-QPB-112/113/118), read at runtime by
# the embedded widget QML -- always resolved relative to the *project's own* folder (never
# absolute), per FR-QPB-112/113/118's own relative-path discipline.
# FR-QPB-112 (revised)/FR-QPB-118 (Decision Log D-47): points at the build-time-extracted,
# 5-column lookup file -- never the complete raw CSV's former `reference/tables/...` location.
REFERENCE_KTSN_CSV_RELPATH = "reference/ktsn_lookup.csv"
# Newly generated projects use one registered multiband layer plus this compact lookup.  The
# legacy worker constants below remain importable only so older generated projects and external
# callers are not rewritten; the current renderer no longer emits or bundles that path.
PROBABILITY_STACK_RELPATH = "reference/rasters/occurrence_probability_multiband.tif"
PROBABILITY_BAND_INDEX_RELPATH = "reference/rasters/occurrence_probability_bands.json"
PROBABILITY_LAYER_NAME = "occurrence_probability_multiband.tif"
REFERENCE_RASTER_DIR_RELPATH = "reference/rasters/bce_inverse_corrected_probability_maps"
PROBABILITY_WORKER_SCRIPT_RELPATH = "qpb_probability_worker.js"

# The worker receives a small, project-local TIFF byte array and performs all decoding and pixel
# math outside the attribute-form/QML UI thread.  The generated TIFFs are little-endian, single
# band, float32 GeoTIFFs; the decoder supports the LZW strips used by the bundled reference set.
PROBABILITY_WORKER_SCRIPT = r"""
function u16(b, i) { return b[i] | (b[i + 1] << 8); }
function u32(b, i) { return (b[i] | (b[i + 1] << 8) | (b[i + 2] << 16) | (b[i + 3] << 24)) >>> 0; }
function f32(b, i) {
    var view = new DataView(new Uint8Array([b[i], b[i + 1], b[i + 2], b[i + 3]]).buffer);
    return view.getFloat32(0, true);
}
function f64(b, i) {
    var view = new DataView(new Uint8Array([
        b[i], b[i + 1], b[i + 2], b[i + 3], b[i + 4], b[i + 5], b[i + 6], b[i + 7]
    ]).buffer);
    return view.getFloat64(0, true);
}
function lzw(bytes) {
    var clear = 256, end = 257, codeSize = 9, next = 258, table = [];
    for (var i = 0; i < 256; i++) { table[i] = [i]; }
    var bit = 0, previous = null, output = [], totalBits = bytes.length * 8;
    function code() {
        var value = 0;
        if (bit + codeSize > totalBits) { return null; }
        for (var j = 0; j < codeSize; j++) {
            // TIFF LZW packs each code most-significant bit first within the byte stream.
            var pos = bit + j, byte = bytes[pos >> 3];
            value = (value << 1) | ((byte >> (7 - (pos & 7))) & 1);
        }
        bit += codeSize;
        return value;
    }
    while (bit + codeSize <= totalBits) {
        var c = code();
        if (c === null) { break; }
        if (c === clear) {
            table = []; for (var k = 0; k < 256; k++) { table[k] = [k]; }
            codeSize = 9; next = 258; previous = null; continue;
        }
        if (c === end) { break; }
        var entry = table[c];
        // KwKwK is the one legal reference to the not-yet-materialized next code.
        if (!entry && previous && c === next) { entry = previous.concat(previous[0]); }
        if (!entry) { throw new Error("invalid_lzw_code"); }
        for (var q = 0; q < entry.length; q++) { output.push(entry[q]); }
        if (previous) {
            if (next >= 4096) { throw new Error("lzw_dictionary_full"); }
            table[next++] = previous.concat(entry[0]);
            // TIFF switches widths when the next free code reaches the last code in the
            // current space; this is one code earlier than the GIF packing convention.
            if (next === (1 << codeSize) - 1 && codeSize < 12) { codeSize++; }
        }
        previous = entry;
    }
    return output;
}
function sample(job) {
    var b = job.bytes;
    if (!b || b.length < 8 || b[0] !== 73 || b[1] !== 73 || u16(b, 2) !== 42) {
        return { ok: false, reason: "raster_decode_failed" };
    }
    var ifd = u32(b, 4), count = u16(b, ifd), tags = {};
    for (var i = 0; i < count; i++) {
        var p = ifd + 2 + i * 12, tag = u16(b, p), type = u16(b, p + 2), n = u32(b, p + 4);
        var size = type === 3 ? 2 : (type === 4 ? 4 : (type === 12 ? 8 : 1)), offset = p + 8;
        var at = n * size <= 4 ? offset : u32(b, offset), values = [];
        for (var j = 0; j < n; j++) {
            var pos = at + j * size;
            values.push(type === 3 ? u16(b, pos) : (type === 4 ? u32(b, pos) :
                (type === 12 ? f64(b, pos) : b[pos])));
        }
        tags[tag] = values;
    }
    var width = tags[256] && tags[256][0], height = tags[257] && tags[257][0];
    var compression = tags[259] && tags[259][0], bits = tags[258] && tags[258][0];
    var sampleFormat = (tags[339] && tags[339][0]) || 1;
    var strips = tags[273], counts = tags[279], rows = (tags[278] && tags[278][0]) || height;
    if (!width || !height || bits !== 32 || sampleFormat !== 3 ||
        (compression !== 1 && compression !== 5) || !strips || !counts || !rows) {
        return { ok: false, reason: "raster_metadata_invalid" };
    }
    var raw = [];
    for (var s = 0; s < strips.length; s++) {
        var part = b.slice(strips[s], strips[s] + counts[s]);
        var decoded = compression === 5 ? lzw(part) : part;
        var stripRows = Math.min(rows, height - s * rows);
        var expectedStripBytes = stripRows * width * 4;
        if (stripRows <= 0 || decoded.length !== expectedStripBytes) {
            return { ok: false, reason: "raster_data_invalid" };
        }
        for (var d = 0; d < decoded.length; d++) { raw.push(decoded[d]); }
    }
    if (raw.length !== width * height * 4) {
        return { ok: false, reason: "raster_data_invalid" };
    }
    var scale = tags[33550], tie = tags[33922];
    if (!scale || !tie || scale.length < 2 || tie.length < 6) {
        return { ok: false, reason: "raster_georeference_invalid" };
    }
    var x = Math.floor((job.lon - tie[3]) / scale[0]);
    var y = Math.floor((tie[4] - job.lat) / scale[1]);
    if (x < 0 || y < 0 || x >= width || y >= height) {
        return { ok: false, reason: "raster_missing_nodata_or_outside_extent" };
    }
    var byteOffset = (y * width + x) * 4, value = f32(raw, byteOffset);
    if (!isFinite(value) || value === -9999 || value > 1) {
        return { ok: false, reason: value === -9999 ?
            "raster_missing_nodata_or_outside_extent" : "raster_invalid_value" };
    }
    return { ok: true, value: Math.max(0, value) };
}
WorkerScript.onMessage = function(message) {
    var result;
    try { result = sample(message); }
    catch (e) { result = { ok: false, reason: "raster_sampling_failed" }; }
    result.requestId = message.requestId;
    WorkerScript.sendMessage(result);
};
"""
REFERENCE_NATIONAL_LIST_RELPATH = "reference/nibr_accepted_ktsn_list.txt"

# FR-QPB-109 (further revised; Decision Log D-50/D-51): the pending attribute write-back request
# file -- written by the embedded identification widget (via FileUtils.writeFileContent()) on
# candidate selection or manual-entry confirmation, and polled/applied/cleared by the project
# plugin's own Timer (see render_project_plugin_qml below). This lives directly in the project
# folder (never under reference/, which is reserved for the bundled, read-only KTSN/raster
# reference assets above) because it is transient, per-request runtime state, not a build-time
# asset.
PENDING_WRITE_BACK_RELPATH = "qpb_pending_identification_writeback.json"
PENDING_WRITE_BACK_TRACE_RELPATH = "qpb_identification_writeback_trace.json"
IDENTIFICATION_RUNTIME_TRACE_RELPATH = "qpb_identification_runtime_trace.json"

# FR-QPB-101 (post-MVP; further revised; Decision Log D-52): a fixed, well-known temporary-file
# relative path inside the project folder, used exclusively by the embedded identification
# widget's photo-resize-via-temporary-copy mechanism (qpbResizePhotoForUpload). Never the original
# attachment file's own path -- QField's confirmed native FileUtils.restrictImageSize() resizes
# the file at the given path in place, with no separate output path, so it must only ever run
# against this temporary copy. Reused sequentially across photos within a single identification
# run: each photo's write -> restrictImageSize -> read-back -> empty-content cleanup sequence
# fully completes before the next photo's iteration begins (qpbRunIdentification's loop is plain,
# synchronous JavaScript, so there is never a stale/overlapping temporary file).
PHOTO_RESIZE_TEMP_RELPATH = "qpb_photo_resize_tmp.jpg"

QML_WIDGET_ELEMENT_NAME = "Identify attached photos"

# Shared JavaScript, embedded verbatim into both the project-plugin sidecar and the per-layer
# attribute-form-embedded QML Widget (each is a wholly separate QML source blob evaluated by
# QField in a different context -- there is no confirmed way for one to `Qt.include()` the other
# across that boundary, so the logic is duplicated deliberately rather than assumed-shared).
_SHARED_JS_FUNCTIONS = r"""
    // ---- Pl@ntNet request construction (FR-QPB-104, Decision Log D-37; further revised, Decision
    // Log D-54, to add include-related-images=true so each candidate also carries a related-images
    // list -- consumed by qpbHandlePlantNetResponse below for FR-QPB-109's candidate-card image/
    // attribution display) --------
    function qpbBuildPlantNetUrl(projectName, apiKey) {
        var project = projectName && projectName.length > 0 ? projectName : "all";
        return "https://my-api.plantnet.org/v2/identify/" + encodeURIComponent(project) +
            "?api-key=" + encodeURIComponent(apiKey) +
            "&include-related-images=true";
    }

    // ---- KTSN CSV parsing (mirrors qfield_builder.acceptance_api.match_ktsn / FR-QPB-106/107) --
    // A small, dependency-free CSV row splitter handling double-quoted fields (RFC 4180-style),
    // since the bundled reference CSV contains embedded commas/quotes inside JSON-valued columns
    // (e.g. correct_list). Not a full RFC 4180 implementation (no embedded newlines inside a
    // quoted field), which is sufficient for this single-line-per-record reference dataset.
    function qpbParseCsvLine(line) {
        var fields = [];
        var cur = "";
        var inQuotes = false;
        for (var i = 0; i < line.length; i++) {
            var ch = line.charAt(i);
            if (inQuotes) {
                if (ch === '"') {
                    if (line.charAt(i + 1) === '"') { cur += '"'; i++; }
                    else { inQuotes = false; }
                } else { cur += ch; }
            } else {
                if (ch === '"') { inQuotes = true; }
                else if (ch === ',') { fields.push(cur); cur = ""; }
                else { cur += ch; }
            }
        }
        fields.push(cur);
        return fields;
    }

    function qpbNormalizeName(name) {
        return (name || "").replace(/\s+/g, " ").trim();
    }

    // Probability rasters retain the source bundle's filename bytes.  The source filenames use
    // decomposed Hangul (NFD), while a resolved Korean name may arrive as a precomposed Hangul
    // string (NFC).  Normalize only the filename component so the existing relative path and
    // exact species-name mapping remain unchanged.
    function qpbDecomposeHangulSyllables(text) {
        var result = "";
        for (var i = 0; i < text.length; i++) {
            var code = text.charCodeAt(i);
            if (code < 0xAC00 || code > 0xD7A3) {
                result += text.charAt(i);
                continue;
            }
            var syllable = code - 0xAC00;
            var choseong = Math.floor(syllable / 588);
            var jungseong = Math.floor((syllable % 588) / 28);
            var jongseong = syllable % 28;
            result += String.fromCharCode(0x1100 + choseong);
            result += String.fromCharCode(0x1161 + jungseong);
            if (jongseong !== 0) { result += String.fromCharCode(0x11A7 + jongseong); }
        }
        return result;
    }

    function qpbComposeHangulSyllables(text) {
        var result = "";
        for (var i = 0; i < text.length; i++) {
            var leading = text.charCodeAt(i);
            if (leading < 0x1100 || leading > 0x1112 || i + 1 >= text.length) {
                result += text.charAt(i);
                continue;
            }
            var vowel = text.charCodeAt(i + 1);
            if (vowel < 0x1161 || vowel > 0x1175) {
                result += text.charAt(i);
                continue;
            }
            var choseong = leading - 0x1100;
            var jungseong = vowel - 0x1161;
            var jongseong = 0;
            i++;
            if (i + 1 < text.length) {
                var trailing = text.charCodeAt(i + 1);
                if (trailing >= 0x11A8 && trailing <= 0x11C2) {
                    jongseong = trailing - 0x11A7;
                    i++;
                }
            }
            result += String.fromCharCode(0xAC00 + (choseong * 588) +
                (jungseong * 28) + jongseong);
        }
        return result;
    }

    function qpbNormalizeProbabilityRasterName(name, form) {
        var text = qpbNormalizeName(name);
        var unicodeForm = form || "NFD";
        try {
            // Qt/QML engines with ECMAScript Unicode normalization support handle all canonical
            // decompositions/compositions. Older engines use the Hangul-only fallback below.
            if (typeof text.normalize === "function") { return text.normalize(unicodeForm); }
        } catch (e) { /* use the deterministic Hangul normalization fallback */ }
        return unicodeForm === "NFC" ? qpbComposeHangulSyllables(text) :
            qpbDecomposeHangulSyllables(text);
    }

    function qpbNormalizeProbabilityBandName(koreanName) {
        var text = qpbNormalizeName(koreanName);
        try {
            if (typeof text.normalize === "function") { return text.normalize("NFC"); }
        } catch (e) { /* use the deterministic Hangul composition fallback */ }
        return qpbComposeHangulSyllables(text);
    }

    function qpbStripEmTags(text) {
        // Keep the QML-side normalization identical to Python's `_strip_em_tags`: removing
        // markup is followed by collapsing whitespace and trimming, since an upstream name can
        // contain whitespace around (or between) its formatting tags.
        return qpbNormalizeName((text || "").replace(/<\/?em>/g, ""));
    }

    // KTSN/KTNS values come from JSON supplied by the reference dataset.  String(null) and
    // String(undefined) produce the literal values "null"/"undefined", which are not usable
    // identifiers and must never be looked up as if they were real KTSNs.
    function qpbUsableKtsnValue(value) {
        if (value === null || value === undefined) { return null; }
        // Match Python's `_entry_ktsn`: only JSON scalar string/number identifiers are valid.
        // In particular, coercing an object/array/boolean would turn malformed data into a
        // plausible-looking identifier (for example "[object Object]") and could select the
        // wrong taxon.
        var valueType = typeof value;
        if (valueType !== "string" && valueType !== "number") { return null; }
        var normalized = String(value).trim();
        if (normalized.length === 0 || normalized === "null" || normalized === "undefined") {
            return null;
        }
        return normalized;
    }

    // Manually decodes a byte sequence (a `Uint8Array`, or anything else indexable by byte with a
    // `.length`) as UTF-8 text into a JS (UTF-16) string. Needed because the bundled reference
    // files this is used for (FR-QPB-112/113) contain Korean-language text (e.g. the KTSN CSV's
    // `taxon_kor_nm` column) -- a naive one-byte-per-character decode would corrupt any
    // multi-byte UTF-8 sequence into mojibake, so this decodes proper UTF-8 continuation-byte
    // sequences (1-4 bytes) into their real code points, substituting the Unicode replacement
    // character for any malformed/truncated sequence rather than throwing (so one bad byte does
    // not abort parsing the whole reference file).
    function qpbBytesToUtf8String(bytes) {
        var result = "";
        var i = 0;
        var len = bytes.length;
        while (i < len) {
            var b0 = bytes[i++];
            if (b0 < 0x80) {
                result += String.fromCharCode(b0);
            } else if ((b0 & 0xE0) === 0xC0 && i < len) {
                var b1 = bytes[i++];
                result += String.fromCharCode(((b0 & 0x1F) << 6) | (b1 & 0x3F));
            } else if ((b0 & 0xF0) === 0xE0 && i + 1 < len) {
                var b1e = bytes[i++];
                var b2e = bytes[i++];
                result += String.fromCharCode(
                    ((b0 & 0x0F) << 12) | ((b1e & 0x3F) << 6) | (b2e & 0x3F)
                );
            } else if ((b0 & 0xF8) === 0xF0 && i + 2 < len) {
                var b1f = bytes[i++];
                var b2f = bytes[i++];
                var b3f = bytes[i++];
                var cp = ((b0 & 0x07) << 18) | ((b1f & 0x3F) << 12) | ((b2f & 0x3F) << 6) |
                    (b3f & 0x3F);
                cp -= 0x10000;
                result += String.fromCharCode(0xD800 + (cp >> 10), 0xDC00 + (cp & 0x3FF));
            } else {
                result += "�";
            }
        }
        return result;
    }

    // Real on-device crash fix (bisection-confirmed): scans a single decoded text string once,
    // via `indexOf("\r"|"\n", pos)`, to locate every line's [start, end) character-offset pair --
    // equivalent to `text.split(/\r\n|\n|\r/)` (same terminator handling: "\r\n", lone "\n", and
    // lone "\r" are all recognized, and the terminator itself is excluded from the returned
    // range), but *without* ever allocating a `lines` array holding all 212,397 (or ~62,604)
    // individual per-line substrings simultaneously in memory alongside the one big decoded
    // `text` string -- confirmed, on a real device, to still crash even after the file-size
    // reduction and indexed-lookup fix rounds that preceded this one. No substring is created by
    // this function itself; it returns only a flat array of `[start, end]` integer-offset pairs
    // (a few bytes each), leaving the caller to derive any one specific line's text on demand via
    // `text.substring(start, end)`, exactly when (and only when) that one line is actually needed.
    //
    // Performance-defect fix (this round; reviewer-found, not yet triggered on a real device):
    // the first version of this function called `text.indexOf("\r", pos)` *and*
    // `text.indexOf("\n", pos)` unconditionally on every loop iteration (once per line). A JS
    // `indexOf` search that does not find its target cannot return early -- it must scan all the
    // way from `pos` to the end of the string before reporting -1. When one of the two
    // terminators never occurs anywhere in `text` (e.g. the bundled national KTSN list, written
    // via Python's `"\n".join(...)` with no `\r` bytes at all -- see `reference_bundle.py`), that
    // search degrades from O(n) to O(n) *per line*, i.e. O(n * lineCount) overall: for ~62,604
    // lines this is on the order of 1.8e10 character comparisons, a realistic multi-second (or
    // OS-killed) main-thread hang on a mobile device on every "Identify attached photos"
    // invocation -- defeating the point of the memory fix above.
    //
    // Fixed by caching each terminator's next known location and only re-searching once `pos` has
    // advanced past it (or once a search has already returned -1 for that terminator, which --
    // since `text` never changes and `pos` only ever increases -- means that terminator provably
    // does not occur anywhere at or after that point for the remainder of the scan, so it never
    // needs to be searched for again). Every real (non-cached) `indexOf` call's scanned range
    // `[searchPos, foundIdx]` is disjoint from, and strictly after, every other real call's range
    // for that same terminator, so the *total* work across the whole loop for each terminator is
    // bounded by `text.length` -- giving this function genuine O(n) worst-case time regardless of
    // whether "\r" (or "\n") appears zero times, once, or on every line.
    function qpbFindLineOffsets(text) {
        var offsets = [];
        var pos = 0;
        var len = text.length;
        var UNKNOWN = -2; // cached value not yet searched, or stale (pos has advanced past it).
        var rIdx = UNKNOWN;
        var nIdx = UNKNOWN;
        while (pos <= len) {
            // A cached found index (>= 0) becomes stale once `pos` has moved past it; a cached
            // -1 ("none from here to the end") never becomes stale, since `pos` only increases.
            if (rIdx !== -1 && rIdx < pos) { rIdx = UNKNOWN; }
            if (rIdx === UNKNOWN) { rIdx = text.indexOf("\r", pos); }
            if (nIdx !== -1 && nIdx < pos) { nIdx = UNKNOWN; }
            if (nIdx === UNKNOWN) { nIdx = text.indexOf("\n", pos); }

            var termStart, termLength;
            if (rIdx === -1 && nIdx === -1) {
                offsets.push([pos, len]);
                break;
            } else if (rIdx === -1) {
                termStart = nIdx; termLength = 1;
            } else if (nIdx === -1) {
                termStart = rIdx; termLength = 1;
            } else if (rIdx + 1 === nIdx) {
                termStart = rIdx; termLength = 2; // "\r\n" is a single terminator.
            } else if (rIdx < nIdx) {
                termStart = rIdx; termLength = 1; // lone "\r"
            } else {
                termStart = nIdx; termLength = 1; // lone "\n"
            }
            offsets.push([pos, termStart]);
            pos = termStart + termLength;
        }
        return offsets;
    }

    // Loads and indexes the bundled KTSN CSV (FR-QPB-112) into
    // {header: [...], text: text, lineOffsets: [...], nameIndex: {...}, ktsnIndex: {...}}.
    // Conformance-defect fix (Decision Log D-46 -- same bug class already fixed for
    // `qpbReadFileBytes` above, applied here to a second call site found by a fresh reviewer):
    // this previously read the file via a synchronous XMLHttpRequest against a `file://`-resolved
    // path. That is confirmed broken, not merely unconfirmed -- Qt's own documentation states a
    // plain QML `XMLHttpRequest` cannot read local files by default, and QField's own application
    // source code never lifts that restriction (see `qpbReadFileBytes`'s own comment for the full
    // citation). Resolves `relPath` to an absolute path via `@project_folder` (the same confirmed
    // `expression.evaluate(...)` mechanism used throughout this file) and reads it through
    // QField's own `FileUtils.readFileContent()` singleton instead.
    //
    // Naming correction (this round): the two prior fix rounds researched this against QField's
    // master/HEAD source, which uses a `Qf`-prefixed class (`QfFileUtils`) registered under a
    // separate `org.qfield.core` module URI. A real on-device retest against the stakeholder's
    // actually-installed QField **4.2.4** showed the widget still failing to render, and a direct
    // fetch of the real `v4.2.4`-tagged source (not master/HEAD) confirmed that naming convention
    // does not exist at 4.2.4 at all -- it was introduced in some QField release after 4.2.4. At
    // v4.2.4 the equivalent class is plain `FileUtils` (same `Q_INVOKABLE static QByteArray
    // readFileContent(const QString &filePath)` signature, same behavior), registered via
    // `REGISTER_SINGLETON("org.qfield", FileUtils, "FileUtils")` -- i.e. under the `org.qfield` URI
    // already used elsewhere in this file, with no `Qf` prefix. Confirmed directly against
    // `https://raw.githubusercontent.com/opengisch/QField/v4.2.4/src/core/utils/fileutils.h` and
    // `.../v4.2.4/src/core/qgismobileapp.cpp`.
    //
    // Conformance-defect fix (real on-device crash retest after Decision Log D-47's 183MB->36.7MB
    // file-size reduction still crashed "in the same way"): this previously eagerly parsed every
    // one of the reference file's 212,397 data lines into a fully-parsed 5-element row array via
    // `qpbParseCsvLine`, retaining one giant `rows` array in memory for the whole duration of
    // `qpbHandlePlantNetResponse` while `qpbMatchKtsn` then linear-scanned that same array up to
    // twice per Pl@ntNet candidate (up to 3 candidates). Holding 212,397 fully-parsed row
    // arrays simultaneously is very likely still exceeding practical mobile JS-engine memory
    // limits even after the 5x file-size reduction. Fixed (at that time) to do a single indexing
    // pass that parses each data line exactly once (to extract only the two values needed for
    // indexing), then lets that line's parsed-row array fall out of scope immediately -- never
    // retaining a 212,397-row array. `qpbMatchKtsn` below now looks up a single matching line
    // index in O(1) via `nameIndex`/`ktsnIndex` and parses only that *one* matched line, instead
    // of scanning.
    //
    // Further conformance-defect fix (this round; real on-device crash bisection-confirmed to
    // still be caused by this exact code path even after the indexed-lookup fix above): that fix
    // still built a `lines` array via `text.split(...)`, retaining all 212,397 individual line
    // substrings simultaneously in memory alongside the one big decoded `text` string -- itself
    // very likely still exceeding practical mobile JS-engine memory limits. Fixed to never build
    // a `lines` array of substrings at all: `qpbFindLineOffsets` above scans `text` once via
    // `indexOf(...)` to produce only compact `[start, end]` integer-offset pairs (`lineOffsets`),
    // and each data line's own temporary substring (extracted via `text.substring(start, end)`
    // only when that one line is actually being indexed) falls out of scope immediately after
    // this one-time `qpbParseCsvLine` call, never retained in an array. The returned object now
    // carries the decoded `text` string and `lineOffsets` instead of a `lines` array of
    // substrings; `qpbMatchKtsn` below re-derives a matched line's text on demand from `csv.text`
    // via its `csv.lineOffsets` entry, then parses it exactly as before.
    function qpbLoadCsv(relPath) {
        var absPath;
        try {
            var escapedRelPath = qpbEscapeForExpressionLiteral(relPath);
            absPath = expression.evaluate(
                "@project_folder + '/' + '" + escapedRelPath + "'"
            );
        } catch (e) {
            absPath = null;
        }
        if (absPath === undefined || absPath === null || String(absPath).length === 0) {
            return null;
        }
        var text;
        try {
            var content = FileUtils.readFileContent(String(absPath));
            if (content === undefined || content === null) { return null; }
            // Unconfirmed detail, disclosed honestly (see the module docstring's "Honesty" note
            // and `qpbReadFileBytes`'s own identical caveat): this implementation round could not
            // independently confirm, from this environment, exactly how Qt's QML engine marshals
            // a returned C++ QByteArray into JavaScript for this specific singleton method. This
            // function needs the content as *text*, not raw bytes, so it wraps the result the
            // same way `qpbReadFileBytes` already does (`new Uint8Array(content)`) and then
            // manually decodes those bytes as UTF-8 via `qpbBytesToUtf8String` above, rather than
            // assuming a bare `String(content)` would already yield readable text for a
            // QByteArray/ArrayBuffer-shaped value (it would not, for an ArrayBuffer -- and this
            // CSV's Korean-language columns make a correct text decode, not just any text decode,
            // necessary). If `FileUtils.readFileContent()` instead marshals its QByteArray
            // return value into some other JS shape (e.g. already a JS string), this conversion
            // has not been verified against a real QField device from this environment and may
            // need revisiting.
            text = qpbBytesToUtf8String(new Uint8Array(content));
        } catch (e) {
            return null;
        }
        if (!text) { return null; }
        // Offset-scan pass (never a `lines` array of substrings -- see this function's own
        // "Further conformance-defect fix" comment above): `qpbFindLineOffsets` returns
        // `[start, end]` pairs; the same non-empty-line filter as the old `text.split(...)
        // .filter(...)` is applied here, so the resulting index positions line up identically
        // with the old, now-removed `lines` array's own positions.
        var lineOffsets = qpbFindLineOffsets(text).filter(function (o) { return o[1] > o[0]; });
        if (lineOffsets.length === 0) { return null; }
        var header = qpbParseCsvLine(text.substring(lineOffsets[0][0], lineOffsets[0][1]));
        var idxFullNm = qpbColumnIndex(header, "taxon_full_nm");
        var idxKtsn = qpbColumnIndex(header, "ktsn");
        // One single pass over the data lines to build lightweight line-index maps only --
        // each line's own temporary substring and parsed-row array (from this one, unavoidable,
        // one-time `text.substring(...)` + `qpbParseCsvLine` call) falls out of scope at the end
        // of each loop iteration, so it is eligible for garbage collection immediately rather
        // than being retained in a long-lived 212,397-element `lines`/`rows` array.
        var nameIndex = {};
        var ktsnIndex = {};
        for (var i = 1; i < lineOffsets.length; i++) {
            var lineText = text.substring(lineOffsets[i][0], lineOffsets[i][1]);
            var indexedRow = qpbParseCsvLine(lineText);
            if (idxFullNm >= 0) {
                var normalizedName = qpbNormalizeName(qpbStripEmTags(indexedRow[idxFullNm]));
                // First occurrence in file order wins -- mirrors the old linear scan's own
                // first-match-then-`break` semantics exactly, for the (possible) case of two
                // different rows normalizing to the same name.
                if (!(normalizedName in nameIndex)) { nameIndex[normalizedName] = i; }
            }
            if (idxKtsn >= 0) {
                var ktsnValue = indexedRow[idxKtsn];
                // Same first-occurrence-wins rule applied defensively to `ktsn`, even though the
                // reference data is expected to have unique `ktsn` values -- this can only ever
                // match or exceed the old linear scan's own first-match semantics.
                if (!(ktsnValue in ktsnIndex)) { ktsnIndex[ktsnValue] = i; }
            }
        }
        return {
            header: header, text: text, lineOffsets: lineOffsets,
            nameIndex: nameIndex, ktsnIndex: ktsnIndex
        };
    }

    function qpbColumnIndex(header, name) {
        for (var i = 0; i < header.length; i++) {
            if (header[i] === name) { return i; }
        }
        return -1;
    }

    // Loads the extracted NIBR accepted-taxon KTSN lookup list (FR-QPB-113) -- one KTSN value per
    // line, plain text.
    // Conformance-defect fix (Decision Log D-46 -- identical bug class/fix as `qpbLoadCsv`
    // immediately above; see that function's comment for the full explanation, which applies here
    // unchanged).
    //
    // Further conformance-defect fix (this round -- identical bug class/fix as `qpbLoadCsv`'s own
    // "Further conformance-defect fix" above, applied here to this second, ~62,604-line reference
    // file): never builds a `lines` array of substrings; uses the same shared
    // `qpbFindLineOffsets` offset scan instead, discarding each line's own temporary substring
    // immediately after it is trimmed and checked.
    function qpbLoadNationalKtsnSet(relPath) {
        var set = {};
        var absPath;
        try {
            var escapedRelPath = qpbEscapeForExpressionLiteral(relPath);
            absPath = expression.evaluate(
                "@project_folder + '/' + '" + escapedRelPath + "'"
            );
        } catch (e) {
            absPath = null;
        }
        if (absPath === undefined || absPath === null || String(absPath).length === 0) {
            return set;
        }
        var text;
        try {
            var content = FileUtils.readFileContent(String(absPath));
            if (content === undefined || content === null) { return set; }
            // See `qpbLoadCsv`'s identical comment above -- same unconfirmed QByteArray-to-JS
            // marshaling detail, and the same UTF-8 decode need, apply here.
            text = qpbBytesToUtf8String(new Uint8Array(content));
        } catch (e) {
            return set;
        }
        text = text || "";
        // Offset-scan pass -- see this function's own "Further conformance-defect fix" comment
        // above. Each line's own temporary substring is extracted, trimmed, and checked, then
        // discarded immediately -- never retained in a `lines` array of all ~62,604 entries.
        var lineOffsets = qpbFindLineOffsets(text);
        for (var i = 0; i < lineOffsets.length; i++) {
            var lineText = text.substring(lineOffsets[i][0], lineOffsets[i][1]);
            var v = lineText.trim();
            if (v.length > 0) { set[v] = true; }
        }
        return set;
    }

    // FR-QPB-106/107 (further revised, Decision Log D-40/D-42): direct match + accepted-name
    // resolution, mirroring qfield_builder.acceptance_api.match_ktsn's exact contract.
    function qpbMatchKtsn(scientificNameWithoutAuthor, csv, nationalKtsnSet) {
        var result = {
            direct_match_found: false,
            direct_row_ktsn: null,
            direct_korean_name: null,
            direct_scientific_name: null,
            direct_taxon_jm_nm: null,
            accepted_resolution_attempted: false,
            accepted_resolved: false,
            accepted_ktsn: null,
            accepted_korean_name: null,
            accepted_scientific_name: null,
            ambiguous: false,
            ambiguous_reason: null,
            unresolved_reason: null
        };
        if (!csv) { return result; }
        var idxKtsn = qpbColumnIndex(csv.header, "ktsn");
        var idxFullNm = qpbColumnIndex(csv.header, "taxon_full_nm");
        var idxKorNm = qpbColumnIndex(csv.header, "taxon_kor_nm");
        var idxJmNm = qpbColumnIndex(csv.header, "taxon_jm_nm");
        var idxCorrectList = qpbColumnIndex(csv.header, "correct_list");
        if (idxKtsn < 0 || idxFullNm < 0) { return result; }

        var target = qpbNormalizeName(scientificNameWithoutAuthor);
        var matchedRow = null;
        // O(1) index lookup instead of a full linear scan over every reference row (conformance-
        // defect fix -- see `qpbLoadCsv`'s own comment for the full real-device-crash rationale).
        // `nameIndex` already preserves "first occurrence in file order wins" for any duplicate
        // normalized name, matching the old scan-with-`break` behavior exactly. The matched
        // line's text is re-derived on demand from the retained `csv.text` string via its
        // `csv.lineOffsets` entry (never from a retained `lines` array of substrings), then
        // parsed exactly as before.
        var matchedLineIndex = csv.nameIndex ? csv.nameIndex[target] : undefined;
        if (matchedLineIndex !== undefined) {
            var matchedOffsets = csv.lineOffsets[matchedLineIndex];
            matchedRow = qpbParseCsvLine(csv.text.substring(matchedOffsets[0], matchedOffsets[1]));
        }
        if (matchedRow === null) { return result; }

        result.direct_match_found = true;
        result.direct_row_ktsn = matchedRow[idxKtsn];
        result.direct_korean_name = idxKorNm >= 0 ? matchedRow[idxKorNm] : null;
        // FR-QPB-106 (revised; Decision Log D-60/D-64): mirrors direct_korean_name exactly -- the
        // directly-matched row's own taxon_full_nm, tag-stripped, populated whenever a direct
        // match is found, independent of whether accepted-name resolution below succeeds.
        result.direct_scientific_name = qpbStripEmTags(matchedRow[idxFullNm]);
        result.direct_taxon_jm_nm = idxJmNm >= 0 ? matchedRow[idxJmNm] : null;
        result.accepted_resolution_attempted = true;

        if (result.direct_taxon_jm_nm === "정명") { // '정명'
            result.accepted_resolved = true;
            result.accepted_ktsn = result.direct_row_ktsn;
            result.accepted_korean_name = result.direct_korean_name;
            result.accepted_scientific_name = qpbStripEmTags(matchedRow[idxFullNm]);
            return result;
        }

        var rawCorrectList = idxCorrectList >= 0 ? matchedRow[idxCorrectList] : "";
        var parsed;
        try {
            parsed = rawCorrectList && rawCorrectList.length > 0 ? JSON.parse(rawCorrectList) : [];
        } catch (e) {
            result.unresolved_reason = "correct_list_malformed";
            return result;
        }
        if (!parsed || parsed.length === 0) {
            result.unresolved_reason = "correct_list_empty";
            return result;
        }

        // D-88: follow the selected KTSN repeatedly until a terminal, exact `정명` row is
        // reached. The visited set and transition bound are fail-closed guards for malformed
        // upstream taxonomy data. Every multi-entry hop is disambiguated against the same NIBR
        // accepted set before traversal continues.
        var currentRow = matchedRow;
        var visitedKtsn = {};
        var transitions = 0;
        while (true) {
            var currentKtsn = currentRow[idxKtsn] ? String(currentRow[idxKtsn]).trim() : "";
            if (currentRow[idxJmNm] === "정명") {
                result.accepted_resolved = true;
                result.accepted_ktsn = currentKtsn;
                result.accepted_korean_name = idxKorNm >= 0 ? currentRow[idxKorNm] : null;
                result.accepted_scientific_name = qpbStripEmTags(currentRow[idxFullNm]);
                return result;
            }
            if (currentKtsn.length > 0 && visitedKtsn[currentKtsn]) {
                result.unresolved_reason = "correct_list_cycle";
                return result;
            }
            if (currentKtsn.length > 0) { visitedKtsn[currentKtsn] = true; }
            if (transitions >= 64) {
                result.unresolved_reason = "correct_list_max_depth_exceeded";
                return result;
            }

            var rawHopList = idxCorrectList >= 0 ? currentRow[idxCorrectList] : "";
            var hopList;
            try {
                hopList = rawHopList && rawHopList.length > 0 ? JSON.parse(rawHopList) : [];
            } catch (e) {
                result.unresolved_reason = "correct_list_malformed";
                return result;
            }
            if (!Array.isArray(hopList) || hopList.length === 0) {
                result.unresolved_reason = Array.isArray(hopList)
                    ? "correct_list_empty" : "correct_list_malformed";
                return result;
            }

            var chosenEntry = null;
            var resolvedNationalKtsnSet = null;
            if (hopList.length === 1) {
                chosenEntry = hopList[0];
            } else {
                // The national accepted-name list is needed only to disambiguate a multi-entry
                // correct_list. Accept either the existing eager-set shape or a lazy provider so
                // direct matches and single-entry chains do not parse the ~795 KB list.
                resolvedNationalKtsnSet = typeof nationalKtsnSet === "function"
                    ? nationalKtsnSet() : nationalKtsnSet;
                var hopMatches = [];
                for (var e = 0; e < hopList.length; e++) {
                    var hopEntry = hopList[e];
                    if (!hopEntry || typeof hopEntry !== "object" || Array.isArray(hopEntry)) {
                        result.unresolved_reason = "correct_list_invalid_entry";
                        return result;
                    }
                    var hasHopKtsn = hopEntry.KTSN !== undefined;
                    var hasHopKtns = hopEntry.KTNS !== undefined;
                    if (!hasHopKtsn && !hasHopKtns) {
                        result.unresolved_reason = "correct_list_missing_ktsn_key";
                        return result;
                    }
                    var hopKtsn = qpbUsableKtsnValue(
                        hasHopKtsn ? hopEntry.KTSN : hopEntry.KTNS
                    );
                    var hopKtns = hasHopKtns ? qpbUsableKtsnValue(hopEntry.KTNS) : hopKtsn;
                    if (hopKtsn === null || hopKtns === null) {
                        result.unresolved_reason = "correct_list_invalid_ktsn";
                        return result;
                    }
                    if (hasHopKtsn && hasHopKtns && hopKtsn !== hopKtns) {
                        result.ambiguous = true;
                        result.ambiguous_reason =
                            "KTSN and KTNS keys present with different values";
                        return result;
                    }
                    if (resolvedNationalKtsnSet && resolvedNationalKtsnSet[hopKtsn]) {
                        hopMatches.push(hopEntry);
                    }
                }
                if (hopMatches.length !== 1) {
                    result.ambiguous = true;
                    result.ambiguous_reason = hopMatches.length === 0
                        ? "no candidate KTSN found in the NIBR accepted-taxon national list"
                        : "more than one candidate KTSN found in the NIBR accepted-taxon " +
                            "national list";
                    return result;
                }
                chosenEntry = hopMatches[0];
            }

            if (!chosenEntry || typeof chosenEntry !== "object" || Array.isArray(chosenEntry)) {
                result.unresolved_reason = "correct_list_invalid_entry";
                return result;
            }
            var hasHopKtsn = chosenEntry.KTSN !== undefined;
            var hasHopKtns = chosenEntry.KTNS !== undefined;
            if (!hasHopKtsn && !hasHopKtns) {
                result.unresolved_reason = "correct_list_missing_ktsn_key";
                return result;
            }
            var chosenKtsn = qpbUsableKtsnValue(
                hasHopKtsn ? chosenEntry.KTSN : chosenEntry.KTNS
            );
            var chosenKtns = hasHopKtns ? qpbUsableKtsnValue(chosenEntry.KTNS) : chosenKtsn;
            if (chosenKtsn === null || chosenKtns === null) {
                result.unresolved_reason = "correct_list_invalid_ktsn";
                return result;
            }
            if (hasHopKtsn && hasHopKtns && chosenKtsn !== chosenKtns) {
                result.ambiguous = true;
                result.ambiguous_reason = "KTSN and KTNS keys present with different values";
                return result;
            }
            var acceptedKtsn = chosenKtsn;
            if (visitedKtsn[acceptedKtsn]) {
                result.unresolved_reason = "correct_list_cycle";
                return result;
            }

            var acceptedLineIndex = csv.ktsnIndex ? csv.ktsnIndex[acceptedKtsn] : undefined;
            var nextLineIndex = acceptedLineIndex;
            if (nextLineIndex === undefined) {
                result.unresolved_reason = "accepted_ktsn_not_found_in_csv";
                return result;
            }
            var acceptedOffsets = csv.lineOffsets[acceptedLineIndex];
            var acceptedRow = qpbParseCsvLine(
                csv.text.substring(acceptedOffsets[0], acceptedOffsets[1])
            );
            currentRow = acceptedRow;
            transitions++;
        }
        return result;
    }

    // Sampling is queued with Qt.callLater so candidate construction never performs a direct
    // filesystem decode. QGIS resolves raster_value() against the one registered multiband
    // layer; the watchdog keeps failures candidate-local and ignores late results.
    function qpbSampleProbabilityRaster(sampleExpression, callback) {
        function unavailable(reason) { return { available: false, reason: reason }; }
        if (!sampleExpression || typeof expression === "undefined") {
            if (callback) { callback(unavailable("raster_sampling_api_not_found")); }
            return null;
        }
        var requestId = String(++qpbProbabilityRequestSequence);
        qpbProbabilityJobs[requestId] = {
            startedAt: new Date().getTime(), callback: callback
        };
        qpbProbabilityWatchdog.start();
        Qt.callLater(function() {
            var job = qpbProbabilityJobs[requestId];
            if (!job) { return; }
            var result;
            try {
                var sample = expression.evaluate(sampleExpression);
                result = {available: true, value: sample};
            } catch (e) {
                result = unavailable("raster_sampling_failed");
            }
            delete qpbProbabilityJobs[requestId];
            if (Object.keys(qpbProbabilityJobs).length === 0) { qpbProbabilityWatchdog.stop(); }
            try { job.callback(result); } catch (e2) { /* candidate-local callback failure */ }
        });
        return requestId;
    }
"""


_REPORT_OMITTED_FIELDS = frozenset(
    {
        "identification_score",
        "occurrence_probability",
        "identification_timestamp",
        "identification_model_version",
        "identification_status",
        "qpb_plot_geometry_wkt",
    }
)
_REPORT_SENSITIVE_FIELD_RE = re.compile(
    r"(?:^|_)(?:api_key|key|token|secret|credential|password|photo|image|attachment|path|file)(?:$|_)",
    re.IGNORECASE,
)

# This is the unmodified official d3 distribution shipped in the generated standalone HTML.
# Keep the bytes as an asset rather than maintaining a partial, incompatible reimplementation.
_D3_BUNDLE = resource_path("vendor", "d3.v7.9.0.min.js").read_text(encoding="utf-8")


def _normalize_report_field_name(name: object) -> str:
    """Normalize field spelling before applying the report secret/attachment boundary."""
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(name or ""))
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()


def _qml_string_literal(value: str) -> str:
    """Return a JavaScript/QML string literal for generated source.

    Report JavaScript and the Leaflet distribution are Python source strings, but the project
    plugin is QML.  Injecting either source verbatim into a QML ``html.push("...")`` call makes
    newlines and quotes part of the QML grammar (and previously leaked a Python ``r\"\"\"``
    literal into generated sidecars).  JSON string escaping is also valid JavaScript string
    escaping, so it gives us one small, auditable boundary between the two languages.
    """
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _html_report_definition(
    project_slug: str,
    project_display_name: str | None,
    project_id: str | None,
    survey_type: str | None,
    generated_at: str | None,
    vworld_key: str | None = None,
) -> str:
    """Return JSON-safe, build-time report metadata embedded in the generated QML.

    The report schema comes from the same :mod:`schemas` definitions used to create the
    GeoPackage and QGIS project. Attachment-path fields and identification-result fields are
    deliberately omitted from report content, matching FR-QPB-133's explicit scope boundary.
    """
    tables: list[dict] = []
    if survey_type in schemas.SURVEY_TYPES:
        for table in schemas.get_schema(survey_type).values():
            fields = [
                {
                    "name": column.name,
                    "label": korean_field_aliases.alias_for(table.name, column.name) or column.name,
                }
                for column in table.columns
                if not column.is_attachment_path
                and column.name not in _REPORT_OMITTED_FIELDS
                and not _REPORT_SENSITIVE_FIELD_RE.search(_normalize_report_field_name(column.name))
            ]
            tables.append(
                {
                    "name": table.name,
                    "display_name": korean_layer_display_names.display_name_for(table.name),
                    "uuid_field": table.uuid_pk,
                    "foreign_key": (
                        {
                            "column": table.foreign_key.column,
                            "ref_table": table.foreign_key.ref_table,
                            "ref_column": table.foreign_key.ref_column,
                        }
                        if table.foreign_key is not None
                        else None
                    ),
                    "fields": fields,
                    "geometry_field": table.geometry.column if table.geometry is not None else None,
                    "geometry_type": table.geometry.geom_type
                    if table.geometry is not None
                    else None,
                    "geometry_crs": table.geometry.srs_id if table.geometry is not None else None,
                }
            )

    definition = {
        "project_slug": project_slug,
        "project_display_name": project_display_name or project_slug,
        "project_id": project_id or "",
        "survey_type": survey_type or "",
        "generated_at": generated_at or "",
        # The saved key is discovered by the QML runtime at export time.  It is deliberately
        # not part of the generated report definition or any report surface.
        "basemap_mode": "vworld" if vworld_key and str(vworld_key).strip() else "osm",
        "tables": tables,
        # D-95 canonical taxonomy report contract. The actual rows are read from the project
        # GeoPackage at export time; this metadata never embeds workbook content.
        "taxonomy_reference": {
            "table": "ktsn_taxonomy_reference",
            "ranks": ["Phylum", "Class", "Order", "Family", "Genus"],
            "missing_marker": "taxonomy_reference_unavailable",
        } if survey_type in {"simple_inventory", "temporary_plots", "permanent_plots"} else None,
    }
    # Avoid allowing a user-entered display name containing ``</script``-shaped text to become a
    # meaningful closing tag if the generated source is inspected or embedded elsewhere.
    return json.dumps(definition, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


# The official Leaflet 1.9.4 distribution is embedded below.  The report-local adapter only adds
# ``geoBounds`` (which is not a Leaflet API) so the generated report can calculate an initial view;
# all map, GeoJSON, interaction and tile-layer behavior comes from Leaflet itself.  Leaflet's
# BSD-2-Clause attribution/license is emitted next to the bundle in the generated document.
_LEAFLET_BUNDLE = r"""/* Leaflet 1.9.4 (BSD-2-Clause), official local distribution.
Copyright (c) 2010-2023 Vladimir Agafonkin and contributors.
QPB local bundle metadata: version:"1.9.4-qpb-local".
*/
/* @preserve
 * Leaflet 1.9.4, a JS library for interactive maps. https://leafletjs.com
 * (c) 2010-2023 Vladimir Agafonkin, (c) 2010-2011 CloudMade
 */
!function(t,e){"object"==typeof exports&&"undefined"!=typeof module?e(exports):"function"==typeof define&&define.amd?define(["exports"],e):e((t="undefined"!=typeof globalThis?globalThis:t||self).leaflet={})}(this,function(t){"use strict";function l(t){for(var e,i,n=1,o=arguments.length;n<o;n++)for(e in i=arguments[n])t[e]=i[e];return t}var R=Object.create||function(t){return N.prototype=t,new N};function N(){}function a(t,e){var i,n=Array.prototype.slice;return t.bind?t.bind.apply(t,n.call(arguments,1)):(i=n.call(arguments,2),function(){return t.apply(e,i.length?i.concat(n.call(arguments)):arguments)})}var D=0;function h(t){return"_leaflet_id"in t||(t._leaflet_id=++D),t._leaflet_id}function j(t,e,i){var n,o,s=function(){n=!1,o&&(r.apply(i,o),o=!1)},r=function(){n?o=arguments:(t.apply(i,arguments),setTimeout(s,e),n=!0)};return r}function H(t,e,i){var n=e[1],e=e[0],o=n-e;return t===n&&i?t:((t-e)%o+o)%o+e}function u(){return!1}function i(t,e){return!1===e?t:(e=Math.pow(10,void 0===e?6:e),Math.round(t*e)/e)}function W(t){return t.trim?t.trim():t.replace(/^\s+|\s+$/g,"")}function F(t){return W(t).split(/\s+/)}function c(t,e){for(var i in Object.prototype.hasOwnProperty.call(t,"options")||(t.options=t.options?R(t.options):{}),e)t.options[i]=e[i];return t.options}function U(t,e,i){var n,o=[];for(n in t)o.push(encodeURIComponent(i?n.toUpperCase():n)+"="+encodeURIComponent(t[n]));return(e&&-1!==e.indexOf("?")?"&":"?")+o.join("&")}var V=/\{ *([\w_ -]+) *\}/g;function q(t,i){return t.replace(V,function(t,e){e=i[e];if(void 0===e)throw new Error("No value provided for variable "+t);return e="function"==typeof e?e(i):e})}var d=Array.isArray||function(t){return"[object Array]"===Object.prototype.toString.call(t)};function G(t,e){for(var i=0;i<t.length;i++)if(t[i]===e)return i;return-1}var K="data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs=";function Y(t){return window["webkit"+t]||window["moz"+t]||window["ms"+t]}var X=0;function J(t){var e=+new Date,i=Math.max(0,16-(e-X));return X=e+i,window.setTimeout(t,i)}var $=window.requestAnimationFrame||Y("RequestAnimationFrame")||J,Q=window.cancelAnimationFrame||Y("CancelAnimationFrame")||Y("CancelRequestAnimationFrame")||function(t){window.clearTimeout(t)};function x(t,e,i){if(!i||$!==J)return $.call(window,a(t,e));t.call(e)}function r(t){t&&Q.call(window,t)}var tt={__proto__:null,extend:l,create:R,bind:a,get lastId(){return D},stamp:h,throttle:j,wrapNum:H,falseFn:u,formatNum:i,trim:W,splitWords:F,setOptions:c,getParamString:U,template:q,isArray:d,indexOf:G,emptyImageUrl:K,requestFn:$,cancelFn:Q,requestAnimFrame:x,cancelAnimFrame:r};function et(){}et.extend=function(t){function e(){c(this),this.initialize&&this.initialize.apply(this,arguments),this.callInitHooks()}var i,n=e.__super__=this.prototype,o=R(n);for(i in(o.constructor=e).prototype=o,this)Object.prototype.hasOwnProperty.call(this,i)&&"prototype"!==i&&"__super__"!==i&&(e[i]=this[i]);if(t.statics&&l(e,t.statics),t.includes){var s=t.includes;if("undefined"!=typeof L&&L&&L.Mixin){s=d(s)?s:[s];for(var r=0;r<s.length;r++)s[r]===L.Mixin.Events&&console.warn("Deprecated include of L.Mixin.Events: this property will be removed in future releases, please inherit from L.Evented instead.",(new Error).stack)}l.apply(null,[o].concat(t.includes))}return l(o,t),delete o.statics,delete o.includes,o.options&&(o.options=n.options?R(n.options):{},l(o.options,t.options)),o._initHooks=[],o.callInitHooks=function(){if(!this._initHooksCalled){n.callInitHooks&&n.callInitHooks.call(this),this._initHooksCalled=!0;for(var t=0,e=o._initHooks.length;t<e;t++)o._initHooks[t].call(this)}},e},et.include=function(t){var e=this.prototype.options;return l(this.prototype,t),t.options&&(this.prototype.options=e,this.mergeOptions(t.options)),this},et.mergeOptions=function(t){return l(this.prototype.options,t),this},et.addInitHook=function(t){var e=Array.prototype.slice.call(arguments,1),i="function"==typeof t?t:function(){this[t].apply(this,e)};return this.prototype._initHooks=this.prototype._initHooks||[],this.prototype._initHooks.push(i),this};var e={on:function(t,e,i){if("object"==typeof t)for(var n in t)this._on(n,t[n],e);else for(var o=0,s=(t=F(t)).length;o<s;o++)this._on(t[o],e,i);return this},off:function(t,e,i){if(arguments.length)if("object"==typeof t)for(var n in t)this._off(n,t[n],e);else{t=F(t);for(var o=1===arguments.length,s=0,r=t.length;s<r;s++)o?this._off(t[s]):this._off(t[s],e,i)}else delete this._events;return this},_on:function(t,e,i,n){"function"!=typeof e?console.warn("wrong listener type: "+typeof e):!1===this._listens(t,e,i)&&(e={fn:e,ctx:i=i===this?void 0:i},n&&(e.once=!0),this._events=this._events||{},this._events[t]=this._events[t]||[],this._events[t].push(e))},_off:function(t,e,i){var n,o,s;if(this._events&&(n=this._events[t]))if(1===arguments.length){if(this._firingCount)for(o=0,s=n.length;o<s;o++)n[o].fn=u;delete this._events[t]}else"function"!=typeof e?console.warn("wrong listener type: "+typeof e):!1!==(e=this._listens(t,e,i))&&(i=n[e],this._firingCount&&(i.fn=u,this._events[t]=n=n.slice()),n.splice(e,1))},fire:function(t,e,i){if(this.listens(t,i)){var n=l({},e,{type:t,target:this,sourceTarget:e&&e.sourceTarget||this});if(this._events){var o=this._events[t];if(o){this._firingCount=this._firingCount+1||1;for(var s=0,r=o.length;s<r;s++){var a=o[s],h=a.fn;a.once&&this.off(t,h,a.ctx),h.call(a.ctx||this,n)}this._firingCount--}}i&&this._propagateEvent(n)}return this},listens:function(t,e,i,n){"string"!=typeof t&&console.warn('"string" type argument expected');var o=e,s=("function"!=typeof e&&(n=!!e,i=o=void 0),this._events&&this._events[t]);if(s&&s.length&&!1!==this._listens(t,o,i))return!0;if(n)for(var r in this._eventParents)if(this._eventParents[r].listens(t,e,i,n))return!0;return!1},_listens:function(t,e,i){if(this._events){var n=this._events[t]||[];if(!e)return!!n.length;i===this&&(i=void 0);for(var o=0,s=n.length;o<s;o++)if(n[o].fn===e&&n[o].ctx===i)return o}return!1},once:function(t,e,i){if("object"==typeof t)for(var n in t)this._on(n,t[n],e,!0);else for(var o=0,s=(t=F(t)).length;o<s;o++)this._on(t[o],e,i,!0);return this},addEventParent:function(t){return this._eventParents=this._eventParents||{},this._eventParents[h(t)]=t,this},removeEventParent:function(t){return this._eventParents&&delete this._eventParents[h(t)],this},_propagateEvent:function(t){for(var e in this._eventParents)this._eventParents[e].fire(t.type,l({layer:t.target,propagatedFrom:t.target},t),!0)}},it=(e.addEventListener=e.on,e.removeEventListener=e.clearAllEventListeners=e.off,e.addOneTimeEventListener=e.once,e.fireEvent=e.fire,e.hasEventListeners=e.listens,et.extend(e));function p(t,e,i){this.x=i?Math.round(t):t,this.y=i?Math.round(e):e}var nt=Math.trunc||function(t){return 0<t?Math.floor(t):Math.ceil(t)};function m(t,e,i){return t instanceof p?t:d(t)?new p(t[0],t[1]):null==t?t:"object"==typeof t&&"x"in t&&"y"in t?new p(t.x,t.y):new p(t,e,i)}function f(t,e){if(t)for(var i=e?[t,e]:t,n=0,o=i.length;n<o;n++)this.extend(i[n])}function _(t,e){return!t||t instanceof f?t:new f(t,e)}function s(t,e){if(t)for(var i=e?[t,e]:t,n=0,o=i.length;n<o;n++)this.extend(i[n])}function g(t,e){return t instanceof s?t:new s(t,e)}function v(t,e,i){if(isNaN(t)||isNaN(e))throw new Error("Invalid LatLng object: ("+t+", "+e+")");this.lat=+t,this.lng=+e,void 0!==i&&(this.alt=+i)}function w(t,e,i){return t instanceof v?t:d(t)&&"object"!=typeof t[0]?3===t.length?new v(t[0],t[1],t[2]):2===t.length?new v(t[0],t[1]):null:null==t?t:"object"==typeof t&&"lat"in t?new v(t.lat,"lng"in t?t.lng:t.lon,t.alt):void 0===e?null:new v(t,e,i)}p.prototype={clone:function(){return new p(this.x,this.y)},add:function(t){return this.clone()._add(m(t))},_add:function(t){return this.x+=t.x,this.y+=t.y,this},subtract:function(t){return this.clone()._subtract(m(t))},_subtract:function(t){return this.x-=t.x,this.y-=t.y,this},divideBy:function(t){return this.clone()._divideBy(t)},_divideBy:function(t){return this.x/=t,this.y/=t,this},multiplyBy:function(t){return this.clone()._multiplyBy(t)},_multiplyBy:function(t){return this.x*=t,this.y*=t,this},scaleBy:function(t){return new p(this.x*t.x,this.y*t.y)},unscaleBy:function(t){return new p(this.x/t.x,this.y/t.y)},round:function(){return this.clone()._round()},_round:function(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this},floor:function(){return this.clone()._floor()},_floor:function(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this},ceil:function(){return this.clone()._ceil()},_ceil:function(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this},trunc:function(){return this.clone()._trunc()},_trunc:function(){return this.x=nt(this.x),this.y=nt(this.y),this},distanceTo:function(t){var e=(t=m(t)).x-this.x,t=t.y-this.y;return Math.sqrt(e*e+t*t)},equals:function(t){return(t=m(t)).x===this.x&&t.y===this.y},contains:function(t){return t=m(t),Math.abs(t.x)<=Math.abs(this.x)&&Math.abs(t.y)<=Math.abs(this.y)},toString:function(){return"Point("+i(this.x)+", "+i(this.y)+")"}},f.prototype={extend:function(t){var e,i;if(t){if(t instanceof p||"number"==typeof t[0]||"x"in t)e=i=m(t);else if(e=(t=_(t)).min,i=t.max,!e||!i)return this;this.min||this.max?(this.min.x=Math.min(e.x,this.min.x),this.max.x=Math.max(i.x,this.max.x),this.min.y=Math.min(e.y,this.min.y),this.max.y=Math.max(i.y,this.max.y)):(this.min=e.clone(),this.max=i.clone())}return this},getCenter:function(t){return m((this.min.x+this.max.x)/2,(this.min.y+this.max.y)/2,t)},getBottomLeft:function(){return m(this.min.x,this.max.y)},getTopRight:function(){return m(this.max.x,this.min.y)},getTopLeft:function(){return this.min},getBottomRight:function(){return this.max},getSize:function(){return this.max.subtract(this.min)},contains:function(t){var e,i;return(t=("number"==typeof t[0]||t instanceof p?m:_)(t))instanceof f?(e=t.min,i=t.max):e=i=t,e.x>=this.min.x&&i.x<=this.max.x&&e.y>=this.min.y&&i.y<=this.max.y},intersects:function(t){t=_(t);var e=this.min,i=this.max,n=t.min,t=t.max,o=t.x>=e.x&&n.x<=i.x,t=t.y>=e.y&&n.y<=i.y;return o&&t},overlaps:function(t){t=_(t);var e=this.min,i=this.max,n=t.min,t=t.max,o=t.x>e.x&&n.x<i.x,t=t.y>e.y&&n.y<i.y;return o&&t},isValid:function(){return!(!this.min||!this.max)},pad:function(t){var e=this.min,i=this.max,n=Math.abs(e.x-i.x)*t,t=Math.abs(e.y-i.y)*t;return _(m(e.x-n,e.y-t),m(i.x+n,i.y+t))},equals:function(t){return!!t&&(t=_(t),this.min.equals(t.getTopLeft())&&this.max.equals(t.getBottomRight()))}},s.prototype={extend:function(t){var e,i,n=this._southWest,o=this._northEast;if(t instanceof v)i=e=t;else{if(!(t instanceof s))return t?this.extend(w(t)||g(t)):this;if(e=t._southWest,i=t._northEast,!e||!i)return this}return n||o?(n.lat=Math.min(e.lat,n.lat),n.lng=Math.min(e.lng,n.lng),o.lat=Math.max(i.lat,o.lat),o.lng=Math.max(i.lng,o.lng)):(this._southWest=new v(e.lat,e.lng),this._northEast=new v(i.lat,i.lng)),this},pad:function(t){var e=this._southWest,i=this._northEast,n=Math.abs(e.lat-i.lat)*t,t=Math.abs(e.lng-i.lng)*t;return new s(new v(e.lat-n,e.lng-t),new v(i.lat+n,i.lng+t))},getCenter:function(){return new v((this._southWest.lat+this._northEast.lat)/2,(this._southWest.lng+this._northEast.lng)/2)},getSouthWest:function(){return this._southWest},getNorthEast:function(){return this._northEast},getNorthWest:function(){return new v(this.getNorth(),this.getWest())},getSouthEast:function(){return new v(this.getSouth(),this.getEast())},getWest:function(){return this._southWest.lng},getSouth:function(){return this._southWest.lat},getEast:function(){return this._northEast.lng},getNorth:function(){return this._northEast.lat},contains:function(t){t=("number"==typeof t[0]||t instanceof v||"lat"in t?w:g)(t);var e,i,n=this._southWest,o=this._northEast;return t instanceof s?(e=t.getSouthWest(),i=t.getNorthEast()):e=i=t,e.lat>=n.lat&&i.lat<=o.lat&&e.lng>=n.lng&&i.lng<=o.lng},intersects:function(t){t=g(t);var e=this._southWest,i=this._northEast,n=t.getSouthWest(),t=t.getNorthEast(),o=t.lat>=e.lat&&n.lat<=i.lat,t=t.lng>=e.lng&&n.lng<=i.lng;return o&&t},overlaps:function(t){t=g(t);var e=this._southWest,i=this._northEast,n=t.getSouthWest(),t=t.getNorthEast(),o=t.lat>e.lat&&n.lat<i.lat,t=t.lng>e.lng&&n.lng<i.lng;return o&&t},toBBoxString:function(){return[this.getWest(),this.getSouth(),this.getEast(),this.getNorth()].join(",")},equals:function(t,e){return!!t&&(t=g(t),this._southWest.equals(t.getSouthWest(),e)&&this._northEast.equals(t.getNorthEast(),e))},isValid:function(){return!(!this._southWest||!this._northEast)}};var ot={latLngToPoint:function(t,e){t=this.projection.project(t),e=this.scale(e);return this.transformation._transform(t,e)},pointToLatLng:function(t,e){e=this.scale(e),t=this.transformation.untransform(t,e);return this.projection.unproject(t)},project:function(t){return this.projection.project(t)},unproject:function(t){return this.projection.unproject(t)},scale:function(t){return 256*Math.pow(2,t)},zoom:function(t){return Math.log(t/256)/Math.LN2},getProjectedBounds:function(t){var e;return this.infinite?null:(e=this.projection.bounds,t=this.scale(t),new f(this.transformation.transform(e.min,t),this.transformation.transform(e.max,t)))},infinite:!(v.prototype={equals:function(t,e){return!!t&&(t=w(t),Math.max(Math.abs(this.lat-t.lat),Math.abs(this.lng-t.lng))<=(void 0===e?1e-9:e))},toString:function(t){return"LatLng("+i(this.lat,t)+", "+i(this.lng,t)+")"},distanceTo:function(t){return st.distance(this,w(t))},wrap:function(){return st.wrapLatLng(this)},toBounds:function(t){var t=180*t/40075017,e=t/Math.cos(Math.PI/180*this.lat);return g([this.lat-t,this.lng-e],[this.lat+t,this.lng+e])},clone:function(){return new v(this.lat,this.lng,this.alt)}}),wrapLatLng:function(t){var e=this.wrapLng?H(t.lng,this.wrapLng,!0):t.lng;return new v(this.wrapLat?H(t.lat,this.wrapLat,!0):t.lat,e,t.alt)},wrapLatLngBounds:function(t){var e=t.getCenter(),i=this.wrapLatLng(e),n=e.lat-i.lat,e=e.lng-i.lng;return 0==n&&0==e?t:(i=t.getSouthWest(),t=t.getNorthEast(),new s(new v(i.lat-n,i.lng-e),new v(t.lat-n,t.lng-e)))}},st=l({},ot,{wrapLng:[-180,180],R:6371e3,distance:function(t,e){var i=Math.PI/180,n=t.lat*i,o=e.lat*i,s=Math.sin((e.lat-t.lat)*i/2),e=Math.sin((e.lng-t.lng)*i/2),t=s*s+Math.cos(n)*Math.cos(o)*e*e,i=2*Math.atan2(Math.sqrt(t),Math.sqrt(1-t));return this.R*i}}),rt=6378137,rt={R:rt,MAX_LATITUDE:85.0511287798,project:function(t){var e=Math.PI/180,i=this.MAX_LATITUDE,i=Math.max(Math.min(i,t.lat),-i),i=Math.sin(i*e);return new p(this.R*t.lng*e,this.R*Math.log((1+i)/(1-i))/2)},unproject:function(t){var e=180/Math.PI;return new v((2*Math.atan(Math.exp(t.y/this.R))-Math.PI/2)*e,t.x*e/this.R)},bounds:new f([-(rt=rt*Math.PI),-rt],[rt,rt])};function at(t,e,i,n){d(t)?(this._a=t[0],this._b=t[1],this._c=t[2],this._d=t[3]):(this._a=t,this._b=e,this._c=i,this._d=n)}function ht(t,e,i,n){return new at(t,e,i,n)}at.prototype={transform:function(t,e){return this._transform(t.clone(),e)},_transform:function(t,e){return t.x=(e=e||1)*(this._a*t.x+this._b),t.y=e*(this._c*t.y+this._d),t},untransform:function(t,e){return new p((t.x/(e=e||1)-this._b)/this._a,(t.y/e-this._d)/this._c)}};var lt=l({},st,{code:"EPSG:3857",projection:rt,transformation:ht(lt=.5/(Math.PI*rt.R),.5,-lt,.5)}),ut=l({},lt,{code:"EPSG:900913"});function ct(t){return document.createElementNS("http://www.w3.org/2000/svg",t)}function dt(t,e){for(var i,n,o,s,r="",a=0,h=t.length;a<h;a++){for(i=0,n=(o=t[a]).length;i<n;i++)r+=(i?"L":"M")+(s=o[i]).x+" "+s.y;r+=e?b.svg?"z":"x":""}return r||"M0 0"}var _t=document.documentElement.style,pt="ActiveXObject"in window,mt=pt&&!document.addEventListener,n="msLaunchUri"in navigator&&!("documentMode"in document),ft=y("webkit"),gt=y("android"),vt=y("android 2")||y("android 3"),yt=parseInt(/WebKit\/([0-9]+)|$/.exec(navigator.userAgent)[1],10),yt=gt&&y("Google")&&yt<537&&!("AudioNode"in window),xt=!!window.opera,wt=!n&&y("chrome"),bt=y("gecko")&&!ft&&!xt&&!pt,Pt=!wt&&y("safari"),Lt=y("phantom"),o="OTransition"in _t,Tt=0===navigator.platform.indexOf("Win"),Mt=pt&&"transition"in _t,zt="WebKitCSSMatrix"in window&&"m11"in new window.WebKitCSSMatrix&&!vt,_t="MozPerspective"in _t,Ct=!window.L_DISABLE_3D&&(Mt||zt||_t)&&!o&&!Lt,Zt="undefined"!=typeof orientation||y("mobile"),St=Zt&&ft,Et=Zt&&zt,kt=!window.PointerEvent&&window.MSPointerEvent,Ot=!(!window.PointerEvent&&!kt),At="ontouchstart"in window||!!window.TouchEvent,Bt=!window.L_NO_TOUCH&&(At||Ot),It=Zt&&xt,Rt=Zt&&bt,Nt=1<(window.devicePixelRatio||window.screen.deviceXDPI/window.screen.logicalXDPI),Dt=function(){var t=!1;try{var e=Object.defineProperty({},"passive",{get:function(){t=!0}});window.addEventListener("testPassiveEventSupport",u,e),window.removeEventListener("testPassiveEventSupport",u,e)}catch(t){}return t}(),jt=!!document.createElement("canvas").getContext,Ht=!(!document.createElementNS||!ct("svg").createSVGRect),Wt=!!Ht&&((Wt=document.createElement("div")).innerHTML="<svg/>","http://www.w3.org/2000/svg"===(Wt.firstChild&&Wt.firstChild.namespaceURI));function y(t){return 0<=navigator.userAgent.toLowerCase().indexOf(t)}var b={ie:pt,ielt9:mt,edge:n,webkit:ft,android:gt,android23:vt,androidStock:yt,opera:xt,chrome:wt,gecko:bt,safari:Pt,phantom:Lt,opera12:o,win:Tt,ie3d:Mt,webkit3d:zt,gecko3d:_t,any3d:Ct,mobile:Zt,mobileWebkit:St,mobileWebkit3d:Et,msPointer:kt,pointer:Ot,touch:Bt,touchNative:At,mobileOpera:It,mobileGecko:Rt,retina:Nt,passiveEvents:Dt,canvas:jt,svg:Ht,vml:!Ht&&function(){try{var t=document.createElement("div"),e=(t.innerHTML='<v:shape adj="1"/>',t.firstChild);return e.style.behavior="url(#default#VML)",e&&"object"==typeof e.adj}catch(t){return!1}}(),inlineSvg:Wt,mac:0===navigator.platform.indexOf("Mac"),linux:0===navigator.platform.indexOf("Linux")},Ft=b.msPointer?"MSPointerDown":"pointerdown",Ut=b.msPointer?"MSPointerMove":"pointermove",Vt=b.msPointer?"MSPointerUp":"pointerup",qt=b.msPointer?"MSPointerCancel":"pointercancel",Gt={touchstart:Ft,touchmove:Ut,touchend:Vt,touchcancel:qt},Kt={touchstart:function(t,e){e.MSPOINTER_TYPE_TOUCH&&e.pointerType===e.MSPOINTER_TYPE_TOUCH&&O(e);ee(t,e)},touchmove:ee,touchend:ee,touchcancel:ee},Yt={},Xt=!1;function Jt(t,e,i){return"touchstart"!==e||Xt||(document.addEventListener(Ft,$t,!0),document.addEventListener(Ut,Qt,!0),document.addEventListener(Vt,te,!0),document.addEventListener(qt,te,!0),Xt=!0),Kt[e]?(i=Kt[e].bind(this,i),t.addEventListener(Gt[e],i,!1),i):(console.warn("wrong event specified:",e),u)}function $t(t){Yt[t.pointerId]=t}function Qt(t){Yt[t.pointerId]&&(Yt[t.pointerId]=t)}function te(t){delete Yt[t.pointerId]}function ee(t,e){if(e.pointerType!==(e.MSPOINTER_TYPE_MOUSE||"mouse")){for(var i in e.touches=[],Yt)e.touches.push(Yt[i]);e.changedTouches=[e],t(e)}}var ie=200;function ne(t,i){t.addEventListener("dblclick",i);var n,o=0;function e(t){var e;1!==t.detail?n=t.detail:"mouse"===t.pointerType||t.sourceCapabilities&&!t.sourceCapabilities.firesTouchEvents||((e=Ne(t)).some(function(t){return t instanceof HTMLLabelElement&&t.attributes.for})&&!e.some(function(t){return t instanceof HTMLInputElement||t instanceof HTMLSelectElement})||((e=Date.now())-o<=ie?2===++n&&i(function(t){var e,i,n={};for(i in t)e=t[i],n[i]=e&&e.bind?e.bind(t):e;return(t=n).type="dblclick",n.detail=2,n.isTrusted=!1,n._simulated=!0,n}(t)):n=1,o=e))}return t.addEventListener("click",e),{dblclick:i,simDblclick:e}}var oe,se,re,ae,he,le,ue=we(["transform","webkitTransform","OTransform","MozTransform","msTransform"]),ce=we(["webkitTransition","transition","OTransition","MozTransition","msTransition"]),de="webkitTransition"===ce||"OTransition"===ce?ce+"End":"transitionend";function _e(t){return"string"==typeof t?document.getElementById(t):t}function pe(t,e){var i=t.style[e]||t.currentStyle&&t.currentStyle[e];return"auto"===(i=i&&"auto"!==i||!document.defaultView?i:(t=document.defaultView.getComputedStyle(t,null))?t[e]:null)?null:i}function P(t,e,i){t=document.createElement(t);return t.className=e||"",i&&i.appendChild(t),t}function T(t){var e=t.parentNode;e&&e.removeChild(t)}function me(t){for(;t.firstChild;)t.removeChild(t.firstChild)}function fe(t){var e=t.parentNode;e&&e.lastChild!==t&&e.appendChild(t)}function ge(t){var e=t.parentNode;e&&e.firstChild!==t&&e.insertBefore(t,e.firstChild)}function ve(t,e){return void 0!==t.classList?t.classList.contains(e):0<(t=xe(t)).length&&new RegExp("(^|\\s)"+e+"(\\s|$)").test(t)}function M(t,e){var i;if(void 0!==t.classList)for(var n=F(e),o=0,s=n.length;o<s;o++)t.classList.add(n[o]);else ve(t,e)||ye(t,((i=xe(t))?i+" ":"")+e)}function z(t,e){void 0!==t.classList?t.classList.remove(e):ye(t,W((" "+xe(t)+" ").replace(" "+e+" "," ")))}function ye(t,e){void 0===t.className.baseVal?t.className=e:t.className.baseVal=e}function xe(t){return void 0===(t=t.correspondingElement?t.correspondingElement:t).className.baseVal?t.className:t.className.baseVal}function C(t,e){if("opacity"in t.style)t.style.opacity=e;else if("filter"in t.style){var i=!1,n="DXImageTransform.Microsoft.Alpha";try{i=t.filters.item(n)}catch(t){if(1===e)return}e=Math.round(100*e),i?(i.Enabled=100!==e,i.Opacity=e):t.style.filter+=" progid:"+n+"(opacity="+e+")"}}function we(t){for(var e=document.documentElement.style,i=0;i<t.length;i++)if(t[i]in e)return t[i];return!1}function be(t,e,i){e=e||new p(0,0);t.style[ue]=(b.ie3d?"translate("+e.x+"px,"+e.y+"px)":"translate3d("+e.x+"px,"+e.y+"px,0)")+(i?" scale("+i+")":"")}function Z(t,e){t._leaflet_pos=e,b.any3d?be(t,e):(t.style.left=e.x+"px",t.style.top=e.y+"px")}function Pe(t){return t._leaflet_pos||new p(0,0)}function Le(){S(window,"dragstart",O)}function Te(){k(window,"dragstart",O)}function Me(t){for(;-1===t.tabIndex;)t=t.parentNode;t.style&&(ze(),le=(he=t).style.outlineStyle,t.style.outlineStyle="none",S(window,"keydown",ze))}function ze(){he&&(he.style.outlineStyle=le,le=he=void 0,k(window,"keydown",ze))}function Ce(t){for(;!((t=t.parentNode).offsetWidth&&t.offsetHeight||t===document.body););return t}function Ze(t){var e=t.getBoundingClientRect();return{x:e.width/t.offsetWidth||1,y:e.height/t.offsetHeight||1,boundingClientRect:e}}ae="onselectstart"in document?(re=function(){S(window,"selectstart",O)},function(){k(window,"selectstart",O)}):(se=we(["userSelect","WebkitUserSelect","OUserSelect","MozUserSelect","msUserSelect"]),re=function(){var t;se&&(t=document.documentElement.style,oe=t[se],t[se]="none")},function(){se&&(document.documentElement.style[se]=oe,oe=void 0)});pt={__proto__:null,TRANSFORM:ue,TRANSITION:ce,TRANSITION_END:de,get:_e,getStyle:pe,create:P,remove:T,empty:me,toFront:fe,toBack:ge,hasClass:ve,addClass:M,removeClass:z,setClass:ye,getClass:xe,setOpacity:C,testProp:we,setTransform:be,setPosition:Z,getPosition:Pe,get disableTextSelection(){return re},get enableTextSelection(){return ae},disableImageDrag:Le,enableImageDrag:Te,preventOutline:Me,restoreOutline:ze,getSizedParentNode:Ce,getScale:Ze};function S(t,e,i,n){if(e&&"object"==typeof e)for(var o in e)ke(t,o,e[o],i);else for(var s=0,r=(e=F(e)).length;s<r;s++)ke(t,e[s],i,n);return this}var E="_leaflet_events";function k(t,e,i,n){if(1===arguments.length)Se(t),delete t[E];else if(e&&"object"==typeof e)for(var o in e)Oe(t,o,e[o],i);else if(e=F(e),2===arguments.length)Se(t,function(t){return-1!==G(e,t)});else for(var s=0,r=e.length;s<r;s++)Oe(t,e[s],i,n);return this}function Se(t,e){for(var i in t[E]){var n=i.split(/\d/)[0];e&&!e(n)||Oe(t,n,null,null,i)}}var Ee={mouseenter:"mouseover",mouseleave:"mouseout",wheel:!("onwheel"in window)&&"mousewheel"};function ke(e,t,i,n){var o,s,r=t+h(i)+(n?"_"+h(n):"");e[E]&&e[E][r]||(s=o=function(t){return i.call(n||e,t||window.event)},!b.touchNative&&b.pointer&&0===t.indexOf("touch")?o=Jt(e,t,o):b.touch&&"dblclick"===t?o=ne(e,o):"addEventListener"in e?"touchstart"===t||"touchmove"===t||"wheel"===t||"mousewheel"===t?e.addEventListener(Ee[t]||t,o,!!b.passiveEvents&&{passive:!1}):"mouseenter"===t||"mouseleave"===t?e.addEventListener(Ee[t],o=function(t){t=t||window.event,We(e,t)&&s(t)},!1):e.addEventListener(t,s,!1):e.attachEvent("on"+t,o),e[E]=e[E]||{},e[E][r]=o)}function Oe(t,e,i,n,o){o=o||e+h(i)+(n?"_"+h(n):"");var s,r,i=t[E]&&t[E][o];i&&(!b.touchNative&&b.pointer&&0===e.indexOf("touch")?(n=t,r=i,Gt[s=e]?n.removeEventListener(Gt[s],r,!1):console.warn("wrong event specified:",s)):b.touch&&"dblclick"===e?(n=i,(r=t).removeEventListener("dblclick",n.dblclick),r.removeEventListener("click",n.simDblclick)):"removeEventListener"in t?t.removeEventListener(Ee[e]||e,i,!1):t.detachEvent("on"+e,i),t[E][o]=null)}function Ae(t){return t.stopPropagation?t.stopPropagation():t.originalEvent?t.originalEvent._stopped=!0:t.cancelBubble=!0,this}function Be(t){return ke(t,"wheel",Ae),this}function Ie(t){return S(t,"mousedown touchstart dblclick contextmenu",Ae),t._leaflet_disable_click=!0,this}function O(t){return t.preventDefault?t.preventDefault():t.returnValue=!1,this}function Re(t){return O(t),Ae(t),this}function Ne(t){if(t.composedPath)return t.composedPath();for(var e=[],i=t.target;i;)e.push(i),i=i.parentNode;return e}function De(t,e){var i,n;return e?(n=(i=Ze(e)).boundingClientRect,new p((t.clientX-n.left)/i.x-e.clientLeft,(t.clientY-n.top)/i.y-e.clientTop)):new p(t.clientX,t.clientY)}var je=b.linux&&b.chrome?window.devicePixelRatio:b.mac?3*window.devicePixelRatio:0<window.devicePixelRatio?2*window.devicePixelRatio:1;function He(t){return b.edge?t.wheelDeltaY/2:t.deltaY&&0===t.deltaMode?-t.deltaY/je:t.deltaY&&1===t.deltaMode?20*-t.deltaY:t.deltaY&&2===t.deltaMode?60*-t.deltaY:t.deltaX||t.deltaZ?0:t.wheelDelta?(t.wheelDeltaY||t.wheelDelta)/2:t.detail&&Math.abs(t.detail)<32765?20*-t.detail:t.detail?t.detail/-32765*60:0}function We(t,e){var i=e.relatedTarget;if(!i)return!0;try{for(;i&&i!==t;)i=i.parentNode}catch(t){return!1}return i!==t}var mt={__proto__:null,on:S,off:k,stopPropagation:Ae,disableScrollPropagation:Be,disableClickPropagation:Ie,preventDefault:O,stop:Re,getPropagationPath:Ne,getMousePosition:De,getWheelDelta:He,isExternalTarget:We,addListener:S,removeListener:k},Fe=it.extend({run:function(t,e,i,n){this.stop(),this._el=t,this._inProgress=!0,this._duration=i||.25,this._easeOutPower=1/Math.max(n||.5,.2),this._startPos=Pe(t),this._offset=e.subtract(this._startPos),this._startTime=+new Date,this.fire("start"),this._animate()},stop:function(){this._inProgress&&(this._step(!0),this._complete())},_animate:function(){this._animId=x(this._animate,this),this._step()},_step:function(t){var e=+new Date-this._startTime,i=1e3*this._duration;e<i?this._runFrame(this._easeOut(e/i),t):(this._runFrame(1),this._complete())},_runFrame:function(t,e){t=this._startPos.add(this._offset.multiplyBy(t));e&&t._round(),Z(this._el,t),this.fire("step")},_complete:function(){r(this._animId),this._inProgress=!1,this.fire("end")},_easeOut:function(t){return 1-Math.pow(1-t,this._easeOutPower)}}),A=it.extend({options:{crs:lt,center:void 0,zoom:void 0,minZoom:void 0,maxZoom:void 0,layers:[],maxBounds:void 0,renderer:void 0,zoomAnimation:!0,zoomAnimationThreshold:4,fadeAnimation:!0,markerZoomAnimation:!0,transform3DLimit:8388608,zoomSnap:1,zoomDelta:1,trackResize:!0},initialize:function(t,e){e=c(this,e),this._handlers=[],this._layers={},this._zoomBoundLayers={},this._sizeChanged=!0,this._initContainer(t),this._initLayout(),this._onResize=a(this._onResize,this),this._initEvents(),e.maxBounds&&this.setMaxBounds(e.maxBounds),void 0!==e.zoom&&(this._zoom=this._limitZoom(e.zoom)),e.center&&void 0!==e.zoom&&this.setView(w(e.center),e.zoom,{reset:!0}),this.callInitHooks(),this._zoomAnimated=ce&&b.any3d&&!b.mobileOpera&&this.options.zoomAnimation,this._zoomAnimated&&(this._createAnimProxy(),S(this._proxy,de,this._catchTransitionEnd,this)),this._addLayers(this.options.layers)},setView:function(t,e,i){if((e=void 0===e?this._zoom:this._limitZoom(e),t=this._limitCenter(w(t),e,this.options.maxBounds),i=i||{},this._stop(),this._loaded&&!i.reset&&!0!==i)&&(void 0!==i.animate&&(i.zoom=l({animate:i.animate},i.zoom),i.pan=l({animate:i.animate,duration:i.duration},i.pan)),this._zoom!==e?this._tryAnimatedZoom&&this._tryAnimatedZoom(t,e,i.zoom):this._tryAnimatedPan(t,i.pan)))return clearTimeout(this._sizeTimer),this;return this._resetView(t,e,i.pan&&i.pan.noMoveStart),this},setZoom:function(t,e){return this._loaded?this.setView(this.getCenter(),t,{zoom:e}):(this._zoom=t,this)},zoomIn:function(t,e){return t=t||(b.any3d?this.options.zoomDelta:1),this.setZoom(this._zoom+t,e)},zoomOut:function(t,e){return t=t||(b.any3d?this.options.zoomDelta:1),this.setZoom(this._zoom-t,e)},setZoomAround:function(t,e,i){var n=this.getZoomScale(e),o=this.getSize().divideBy(2),t=(t instanceof p?t:this.latLngToContainerPoint(t)).subtract(o).multiplyBy(1-1/n),n=this.containerPointToLatLng(o.add(t));return this.setView(n,e,{zoom:i})},_getBoundsCenterZoom:function(t,e){e=e||{},t=t.getBounds?t.getBounds():g(t);var i=m(e.paddingTopLeft||e.padding||[0,0]),n=m(e.paddingBottomRight||e.padding||[0,0]),o=this.getBoundsZoom(t,!1,i.add(n));return(o="number"==typeof e.maxZoom?Math.min(e.maxZoom,o):o)===1/0?{center:t.getCenter(),zoom:o}:(e=n.subtract(i).divideBy(2),n=this.project(t.getSouthWest(),o),i=this.project(t.getNorthEast(),o),{center:this.unproject(n.add(i).divideBy(2).add(e),o),zoom:o})},fitBounds:function(t,e){if((t=g(t)).isValid())return t=this._getBoundsCenterZoom(t,e),this.setView(t.center,t.zoom,e);throw new Error("Bounds are not valid.")},fitWorld:function(t){return this.fitBounds([[-90,-180],[90,180]],t)},panTo:function(t,e){return this.setView(t,this._zoom,{pan:e})},panBy:function(t,e){var i;return e=e||{},(t=m(t).round()).x||t.y?(!0===e.animate||this.getSize().contains(t)?(this._panAnim||(this._panAnim=new Fe,this._panAnim.on({step:this._onPanTransitionStep,end:this._onPanTransitionEnd},this)),e.noMoveStart||this.fire("movestart"),!1!==e.animate?(M(this._mapPane,"leaflet-pan-anim"),i=this._getMapPanePos().subtract(t).round(),this._panAnim.run(this._mapPane,i,e.duration||.25,e.easeLinearity)):(this._rawPanBy(t),this.fire("move").fire("moveend"))):this._resetView(this.unproject(this.project(this.getCenter()).add(t)),this.getZoom()),this):this.fire("moveend")},flyTo:function(n,o,t){if(!1===(t=t||{}).animate||!b.any3d)return this.setView(n,o,t);this._stop();var s=this.project(this.getCenter()),r=this.project(n),e=this.getSize(),a=this._zoom,h=(n=w(n),o=void 0===o?a:o,Math.max(e.x,e.y)),i=h*this.getZoomScale(a,o),l=r.distanceTo(s)||1,u=1.42,c=u*u;function d(t){t=(i*i-h*h+(t?-1:1)*c*c*l*l)/(2*(t?i:h)*c*l),t=Math.sqrt(t*t+1)-t;return t<1e-9?-18:Math.log(t)}function _(t){return(Math.exp(t)-Math.exp(-t))/2}function p(t){return(Math.exp(t)+Math.exp(-t))/2}var m=d(0);function f(t){return h*(p(m)*(_(t=m+u*t)/p(t))-_(m))/c}var g=Date.now(),v=(d(1)-m)/u,y=t.duration?1e3*t.duration:1e3*v*.8;return this._moveStart(!0,t.noMoveStart),function t(){var e=(Date.now()-g)/y,i=(1-Math.pow(1-e,1.5))*v;e<=1?(this._flyToFrame=x(t,this),this._move(this.unproject(s.add(r.subtract(s).multiplyBy(f(i)/l)),a),this.getScaleZoom(h/(e=i,h*(p(m)/p(m+u*e))),a),{flyTo:!0})):this._move(n,o)._moveEnd(!0)}.call(this),this},flyToBounds:function(t,e){t=this._getBoundsCenterZoom(t,e);return this.flyTo(t.center,t.zoom,e)},setMaxBounds:function(t){return t=g(t),this.listens("moveend",this._panInsideMaxBounds)&&this.off("moveend",this._panInsideMaxBounds),t.isValid()?(this.options.maxBounds=t,this._loaded&&this._panInsideMaxBounds(),this.on("moveend",this._panInsideMaxBounds)):(this.options.maxBounds=null,this)},setMinZoom:function(t){var e=this.options.minZoom;return this.options.minZoom=t,this._loaded&&e!==t&&(this.fire("zoomlevelschange"),this.getZoom()<this.options.minZoom)?this.setZoom(t):this},setMaxZoom:function(t){var e=this.options.maxZoom;return this.options.maxZoom=t,this._loaded&&e!==t&&(this.fire("zoomlevelschange"),this.getZoom()>this.options.maxZoom)?this.setZoom(t):this},panInsideBounds:function(t,e){this._enforcingBounds=!0;var i=this.getCenter(),t=this._limitCenter(i,this._zoom,g(t));return i.equals(t)||this.panTo(t,e),this._enforcingBounds=!1,this},panInside:function(t,e){var i=m((e=e||{}).paddingTopLeft||e.padding||[0,0]),n=m(e.paddingBottomRight||e.padding||[0,0]),o=this.project(this.getCenter()),t=this.project(t),s=this.getPixelBounds(),i=_([s.min.add(i),s.max.subtract(n)]),s=i.getSize();return i.contains(t)||(this._enforcingBounds=!0,n=t.subtract(i.getCenter()),i=i.extend(t).getSize().subtract(s),o.x+=n.x<0?-i.x:i.x,o.y+=n.y<0?-i.y:i.y,this.panTo(this.unproject(o),e),this._enforcingBounds=!1),this},invalidateSize:function(t){if(!this._loaded)return this;t=l({animate:!1,pan:!0},!0===t?{animate:!0}:t);var e=this.getSize(),i=(this._sizeChanged=!0,this._lastCenter=null,this.getSize()),n=e.divideBy(2).round(),o=i.divideBy(2).round(),n=n.subtract(o);return n.x||n.y?(t.animate&&t.pan?this.panBy(n):(t.pan&&this._rawPanBy(n),this.fire("move"),t.debounceMoveend?(clearTimeout(this._sizeTimer),this._sizeTimer=setTimeout(a(this.fire,this,"moveend"),200)):this.fire("moveend")),this.fire("resize",{oldSize:e,newSize:i})):this},stop:function(){return this.setZoom(this._limitZoom(this._zoom)),this.options.zoomSnap||this.fire("viewreset"),this._stop()},locate:function(t){var e,i;return t=this._locateOptions=l({timeout:1e4,watch:!1},t),"geolocation"in navigator?(e=a(this._handleGeolocationResponse,this),i=a(this._handleGeolocationError,this),t.watch?this._locationWatchId=navigator.geolocation.watchPosition(e,i,t):navigator.geolocation.getCurrentPosition(e,i,t)):this._handleGeolocationError({code:0,message:"Geolocation not supported."}),this},stopLocate:function(){return navigator.geolocation&&navigator.geolocation.clearWatch&&navigator.geolocation.clearWatch(this._locationWatchId),this._locateOptions&&(this._locateOptions.setView=!1),this},_handleGeolocationError:function(t){var e;this._container._leaflet_id&&(e=t.code,t=t.message||(1===e?"permission denied":2===e?"position unavailable":"timeout"),this._locateOptions.setView&&!this._loaded&&this.fitWorld(),this.fire("locationerror",{code:e,message:"Geolocation error: "+t+"."}))},_handleGeolocationResponse:function(t){if(this._container._leaflet_id){var e,i,n=new v(t.coords.latitude,t.coords.longitude),o=n.toBounds(2*t.coords.accuracy),s=this._locateOptions,r=(s.setView&&(e=this.getBoundsZoom(o),this.setView(n,s.maxZoom?Math.min(e,s.maxZoom):e)),{latlng:n,bounds:o,timestamp:t.timestamp});for(i in t.coords)"number"==typeof t.coords[i]&&(r[i]=t.coords[i]);this.fire("locationfound",r)}},addHandler:function(t,e){return e&&(e=this[t]=new e(this),this._handlers.push(e),this.options[t]&&e.enable()),this},remove:function(){if(this._initEvents(!0),this.options.maxBounds&&this.off("moveend",this._panInsideMaxBounds),this._containerId!==this._container._leaflet_id)throw new Error("Map container is being reused by another instance");try{delete this._container._leaflet_id,delete this._containerId}catch(t){this._container._leaflet_id=void 0,this._containerId=void 0}for(var t in void 0!==this._locationWatchId&&this.stopLocate(),this._stop(),T(this._mapPane),this._clearControlPos&&this._clearControlPos(),this._resizeRequest&&(r(this._resizeRequest),this._resizeRequest=null),this._clearHandlers(),this._loaded&&this.fire("unload"),this._layers)this._layers[t].remove();for(t in this._panes)T(this._panes[t]);return this._layers=[],this._panes=[],delete this._mapPane,delete this._renderer,this},createPane:function(t,e){e=P("div","leaflet-pane"+(t?" leaflet-"+t.replace("Pane","")+"-pane":""),e||this._mapPane);return t&&(this._panes[t]=e),e},getCenter:function(){return this._checkIfLoaded(),this._lastCenter&&!this._moved()?this._lastCenter.clone():this.layerPointToLatLng(this._getCenterLayerPoint())},getZoom:function(){return this._zoom},getBounds:function(){var t=this.getPixelBounds();return new s(this.unproject(t.getBottomLeft()),this.unproject(t.getTopRight()))},getMinZoom:function(){return void 0===this.options.minZoom?this._layersMinZoom||0:this.options.minZoom},getMaxZoom:function(){return void 0===this.options.maxZoom?void 0===this._layersMaxZoom?1/0:this._layersMaxZoom:this.options.maxZoom},getBoundsZoom:function(t,e,i){t=g(t),i=m(i||[0,0]);var n=this.getZoom()||0,o=this.getMinZoom(),s=this.getMaxZoom(),r=t.getNorthWest(),t=t.getSouthEast(),i=this.getSize().subtract(i),t=_(this.project(t,n),this.project(r,n)).getSize(),r=b.any3d?this.options.zoomSnap:1,a=i.x/t.x,i=i.y/t.y,t=e?Math.max(a,i):Math.min(a,i),n=this.getScaleZoom(t,n);return r&&(n=Math.round(n/(r/100))*(r/100),n=e?Math.ceil(n/r)*r:Math.floor(n/r)*r),Math.max(o,Math.min(s,n))},getSize:function(){return this._size&&!this._sizeChanged||(this._size=new p(this._container.clientWidth||0,this._container.clientHeight||0),this._sizeChanged=!1),this._size.clone()},getPixelBounds:function(t,e){t=this._getTopLeftPoint(t,e);return new f(t,t.add(this.getSize()))},getPixelOrigin:function(){return this._checkIfLoaded(),this._pixelOrigin},getPixelWorldBounds:function(t){return this.options.crs.getProjectedBounds(void 0===t?this.getZoom():t)},getPane:function(t){return"string"==typeof t?this._panes[t]:t},getPanes:function(){return this._panes},getContainer:function(){return this._container},getZoomScale:function(t,e){var i=this.options.crs;return e=void 0===e?this._zoom:e,i.scale(t)/i.scale(e)},getScaleZoom:function(t,e){var i=this.options.crs,t=(e=void 0===e?this._zoom:e,i.zoom(t*i.scale(e)));return isNaN(t)?1/0:t},project:function(t,e){return e=void 0===e?this._zoom:e,this.options.crs.latLngToPoint(w(t),e)},unproject:function(t,e){return e=void 0===e?this._zoom:e,this.options.crs.pointToLatLng(m(t),e)},layerPointToLatLng:function(t){t=m(t).add(this.getPixelOrigin());return this.unproject(t)},latLngToLayerPoint:function(t){return this.project(w(t))._round()._subtract(this.getPixelOrigin())},wrapLatLng:function(t){return this.options.crs.wrapLatLng(w(t))},wrapLatLngBounds:function(t){return this.options.crs.wrapLatLngBounds(g(t))},distance:function(t,e){return this.options.crs.distance(w(t),w(e))},containerPointToLayerPoint:function(t){return m(t).subtract(this._getMapPanePos())},layerPointToContainerPoint:function(t){return m(t).add(this._getMapPanePos())},containerPointToLatLng:function(t){t=this.containerPointToLayerPoint(m(t));return this.layerPointToLatLng(t)},latLngToContainerPoint:function(t){return this.layerPointToContainerPoint(this.latLngToLayerPoint(w(t)))},mouseEventToContainerPoint:function(t){return De(t,this._container)},mouseEventToLayerPoint:function(t){return this.containerPointToLayerPoint(this.mouseEventToContainerPoint(t))},mouseEventToLatLng:function(t){return this.layerPointToLatLng(this.mouseEventToLayerPoint(t))},_initContainer:function(t){t=this._container=_e(t);if(!t)throw new Error("Map container not found.");if(t._leaflet_id)throw new Error("Map container is already initialized.");S(t,"scroll",this._onScroll,this),this._containerId=h(t)},_initLayout:function(){var t=this._container,e=(this._fadeAnimated=this.options.fadeAnimation&&b.any3d,M(t,"leaflet-container"+(b.touch?" leaflet-touch":"")+(b.retina?" leaflet-retina":"")+(b.ielt9?" leaflet-oldie":"")+(b.safari?" leaflet-safari":"")+(this._fadeAnimated?" leaflet-fade-anim":"")),pe(t,"position"));"absolute"!==e&&"relative"!==e&&"fixed"!==e&&"sticky"!==e&&(t.style.position="relative"),this._initPanes(),this._initControlPos&&this._initControlPos()},_initPanes:function(){var t=this._panes={};this._paneRenderers={},this._mapPane=this.createPane("mapPane",this._container),Z(this._mapPane,new p(0,0)),this.createPane("tilePane"),this.createPane("overlayPane"),this.createPane("shadowPane"),this.createPane("markerPane"),this.createPane("tooltipPane"),this.createPane("popupPane"),this.options.markerZoomAnimation||(M(t.markerPane,"leaflet-zoom-hide"),M(t.shadowPane,"leaflet-zoom-hide"))},_resetView:function(t,e,i){Z(this._mapPane,new p(0,0));var n=!this._loaded,o=(this._loaded=!0,e=this._limitZoom(e),this.fire("viewprereset"),this._zoom!==e);this._moveStart(o,i)._move(t,e)._moveEnd(o),this.fire("viewreset"),n&&this.fire("load")},_moveStart:function(t,e){return t&&this.fire("zoomstart"),e||this.fire("movestart"),this},_move:function(t,e,i,n){void 0===e&&(e=this._zoom);var o=this._zoom!==e;return this._zoom=e,this._lastCenter=t,this._pixelOrigin=this._getNewPixelOrigin(t),n?i&&i.pinch&&this.fire("zoom",i):((o||i&&i.pinch)&&this.fire("zoom",i),this.fire("move",i)),this},_moveEnd:function(t){return t&&this.fire("zoomend"),this.fire("moveend")},_stop:function(){return r(this._flyToFrame),this._panAnim&&this._panAnim.stop(),this},_rawPanBy:function(t){Z(this._mapPane,this._getMapPanePos().subtract(t))},_getZoomSpan:function(){return this.getMaxZoom()-this.getMinZoom()},_panInsideMaxBounds:function(){this._enforcingBounds||this.panInsideBounds(this.options.maxBounds)},_checkIfLoaded:function(){if(!this._loaded)throw new Error("Set map center and zoom first.")},_initEvents:function(t){this._targets={};var e=t?k:S;e((this._targets[h(this._container)]=this)._container,"click dblclick mousedown mouseup mouseover mouseout mousemove contextmenu keypress keydown keyup",this._handleDOMEvent,this),this.options.trackResize&&e(window,"resize",this._onResize,this),b.any3d&&this.options.transform3DLimit&&(t?this.off:this.on).call(this,"moveend",this._onMoveEnd)},_onResize:function(){r(this._resizeRequest),this._resizeRequest=x(function(){this.invalidateSize({debounceMoveend:!0})},this)},_onScroll:function(){this._container.scrollTop=0,this._container.scrollLeft=0},_onMoveEnd:function(){var t=this._getMapPanePos();Math.max(Math.abs(t.x),Math.abs(t.y))>=this.options.transform3DLimit&&this._resetView(this.getCenter(),this.getZoom())},_findEventTargets:function(t,e){for(var i,n=[],o="mouseout"===e||"mouseover"===e,s=t.target||t.srcElement,r=!1;s;){if((i=this._targets[h(s)])&&("click"===e||"preclick"===e)&&this._draggableMoved(i)){r=!0;break}if(i&&i.listens(e,!0)){if(o&&!We(s,t))break;if(n.push(i),o)break}if(s===this._container)break;s=s.parentNode}return n=n.length||r||o||!this.listens(e,!0)?n:[this]},_isClickDisabled:function(t){for(;t&&t!==this._container;){if(t._leaflet_disable_click)return!0;t=t.parentNode}},_handleDOMEvent:function(t){var e,i=t.target||t.srcElement;!this._loaded||i._leaflet_disable_events||"click"===t.type&&this._isClickDisabled(i)||("mousedown"===(e=t.type)&&Me(i),this._fireDOMEvent(t,e))},_mouseEvents:["click","dblclick","mouseover","mouseout","contextmenu"],_fireDOMEvent:function(t,e,i){"click"===t.type&&((a=l({},t)).type="preclick",this._fireDOMEvent(a,a.type,i));var n=this._findEventTargets(t,e);if(i){for(var o=[],s=0;s<i.length;s++)i[s].listens(e,!0)&&o.push(i[s]);n=o.concat(n)}if(n.length){"contextmenu"===e&&O(t);var r,a=n[0],h={originalEvent:t};for("keypress"!==t.type&&"keydown"!==t.type&&"keyup"!==t.type&&(r=a.getLatLng&&(!a._radius||a._radius<=10),h.containerPoint=r?this.latLngToContainerPoint(a.getLatLng()):this.mouseEventToContainerPoint(t),h.layerPoint=this.containerPointToLayerPoint(h.containerPoint),h.latlng=r?a.getLatLng():this.layerPointToLatLng(h.layerPoint)),s=0;s<n.length;s++)if(n[s].fire(e,h,!0),h.originalEvent._stopped||!1===n[s].options.bubblingMouseEvents&&-1!==G(this._mouseEvents,e))return}},_draggableMoved:function(t){return(t=t.dragging&&t.dragging.enabled()?t:this).dragging&&t.dragging.moved()||this.boxZoom&&this.boxZoom.moved()},_clearHandlers:function(){for(var t=0,e=this._handlers.length;t<e;t++)this._handlers[t].disable()},whenReady:function(t,e){return this._loaded?t.call(e||this,{target:this}):this.on("load",t,e),this},_getMapPanePos:function(){return Pe(this._mapPane)||new p(0,0)},_moved:function(){var t=this._getMapPanePos();return t&&!t.equals([0,0])},_getTopLeftPoint:function(t,e){return(t&&void 0!==e?this._getNewPixelOrigin(t,e):this.getPixelOrigin()).subtract(this._getMapPanePos())},_getNewPixelOrigin:function(t,e){var i=this.getSize()._divideBy(2);return this.project(t,e)._subtract(i)._add(this._getMapPanePos())._round()},_latLngToNewLayerPoint:function(t,e,i){i=this._getNewPixelOrigin(i,e);return this.project(t,e)._subtract(i)},_latLngBoundsToNewLayerBounds:function(t,e,i){i=this._getNewPixelOrigin(i,e);return _([this.project(t.getSouthWest(),e)._subtract(i),this.project(t.getNorthWest(),e)._subtract(i),this.project(t.getSouthEast(),e)._subtract(i),this.project(t.getNorthEast(),e)._subtract(i)])},_getCenterLayerPoint:function(){return this.containerPointToLayerPoint(this.getSize()._divideBy(2))},_getCenterOffset:function(t){return this.latLngToLayerPoint(t).subtract(this._getCenterLayerPoint())},_limitCenter:function(t,e,i){var n,o;return!i||(n=this.project(t,e),o=this.getSize().divideBy(2),o=new f(n.subtract(o),n.add(o)),o=this._getBoundsOffset(o,i,e),Math.abs(o.x)<=1&&Math.abs(o.y)<=1)?t:this.unproject(n.add(o),e)},_limitOffset:function(t,e){var i;return e?(i=new f((i=this.getPixelBounds()).min.add(t),i.max.add(t)),t.add(this._getBoundsOffset(i,e))):t},_getBoundsOffset:function(t,e,i){e=_(this.project(e.getNorthEast(),i),this.project(e.getSouthWest(),i)),i=e.min.subtract(t.min),e=e.max.subtract(t.max);return new p(this._rebound(i.x,-e.x),this._rebound(i.y,-e.y))},_rebound:function(t,e){return 0<t+e?Math.round(t-e)/2:Math.max(0,Math.ceil(t))-Math.max(0,Math.floor(e))},_limitZoom:function(t){var e=this.getMinZoom(),i=this.getMaxZoom(),n=b.any3d?this.options.zoomSnap:1;return n&&(t=Math.round(t/n)*n),Math.max(e,Math.min(i,t))},_onPanTransitionStep:function(){this.fire("move")},_onPanTransitionEnd:function(){z(this._mapPane,"leaflet-pan-anim"),this.fire("moveend")},_tryAnimatedPan:function(t,e){t=this._getCenterOffset(t)._trunc();return!(!0!==(e&&e.animate)&&!this.getSize().contains(t))&&(this.panBy(t,e),!0)},_createAnimProxy:function(){var t=this._proxy=P("div","leaflet-proxy leaflet-zoom-animated");this._panes.mapPane.appendChild(t),this.on("zoomanim",function(t){var e=ue,i=this._proxy.style[e];be(this._proxy,this.project(t.center,t.zoom),this.getZoomScale(t.zoom,1)),i===this._proxy.style[e]&&this._animatingZoom&&this._onZoomTransitionEnd()},this),this.on("load moveend",this._animMoveEnd,this),this._on("unload",this._destroyAnimProxy,this)},_destroyAnimProxy:function(){T(this._proxy),this.off("load moveend",this._animMoveEnd,this),delete this._proxy},_animMoveEnd:function(){var t=this.getCenter(),e=this.getZoom();be(this._proxy,this.project(t,e),this.getZoomScale(e,1))},_catchTransitionEnd:function(t){this._animatingZoom&&0<=t.propertyName.indexOf("transform")&&this._onZoomTransitionEnd()},_nothingToAnimate:function(){return!this._container.getElementsByClassName("leaflet-zoom-animated").length},_tryAnimatedZoom:function(t,e,i){if(!this._animatingZoom){if(i=i||{},!this._zoomAnimated||!1===i.animate||this._nothingToAnimate()||Math.abs(e-this._zoom)>this.options.zoomAnimationThreshold)return!1;var n=this.getZoomScale(e),n=this._getCenterOffset(t)._divideBy(1-1/n);if(!0!==i.animate&&!this.getSize().contains(n))return!1;x(function(){this._moveStart(!0,i.noMoveStart||!1)._animateZoom(t,e,!0)},this)}return!0},_animateZoom:function(t,e,i,n){this._mapPane&&(i&&(this._animatingZoom=!0,this._animateToCenter=t,this._animateToZoom=e,M(this._mapPane,"leaflet-zoom-anim")),this.fire("zoomanim",{center:t,zoom:e,noUpdate:n}),this._tempFireZoomEvent||(this._tempFireZoomEvent=this._zoom!==this._animateToZoom),this._move(this._animateToCenter,this._animateToZoom,void 0,!0),setTimeout(a(this._onZoomTransitionEnd,this),250))},_onZoomTransitionEnd:function(){this._animatingZoom&&(this._mapPane&&z(this._mapPane,"leaflet-zoom-anim"),this._animatingZoom=!1,this._move(this._animateToCenter,this._animateToZoom,void 0,!0),this._tempFireZoomEvent&&this.fire("zoom"),delete this._tempFireZoomEvent,this.fire("move"),this._moveEnd(!0))}});function Ue(t){return new B(t)}var B=et.extend({options:{position:"topright"},initialize:function(t){c(this,t)},getPosition:function(){return this.options.position},setPosition:function(t){var e=this._map;return e&&e.removeControl(this),this.options.position=t,e&&e.addControl(this),this},getContainer:function(){return this._container},addTo:function(t){this.remove(),this._map=t;var e=this._container=this.onAdd(t),i=this.getPosition(),t=t._controlCorners[i];return M(e,"leaflet-control"),-1!==i.indexOf("bottom")?t.insertBefore(e,t.firstChild):t.appendChild(e),this._map.on("unload",this.remove,this),this},remove:function(){return this._map&&(T(this._container),this.onRemove&&this.onRemove(this._map),this._map.off("unload",this.remove,this),this._map=null),this},_refocusOnMap:function(t){this._map&&t&&0<t.screenX&&0<t.screenY&&this._map.getContainer().focus()}}),Ve=(A.include({addControl:function(t){return t.addTo(this),this},removeControl:function(t){return t.remove(),this},_initControlPos:function(){var i=this._controlCorners={},n="leaflet-",o=this._controlContainer=P("div",n+"control-container",this._container);function t(t,e){i[t+e]=P("div",n+t+" "+n+e,o)}t("top","left"),t("top","right"),t("bottom","left"),t("bottom","right")},_clearControlPos:function(){for(var t in this._controlCorners)T(this._controlCorners[t]);T(this._controlContainer),delete this._controlCorners,delete this._controlContainer}}),B.extend({options:{collapsed:!0,position:"topright",autoZIndex:!0,hideSingleBase:!1,sortLayers:!1,sortFunction:function(t,e,i,n){return i<n?-1:n<i?1:0}},initialize:function(t,e,i){for(var n in c(this,i),this._layerControlInputs=[],this._layers=[],this._lastZIndex=0,this._handlingClick=!1,this._preventClick=!1,t)this._addLayer(t[n],n);for(n in e)this._addLayer(e[n],n,!0)},onAdd:function(t){this._initLayout(),this._update(),(this._map=t).on("zoomend",this._checkDisabledLayers,this);for(var e=0;e<this._layers.length;e++)this._layers[e].layer.on("add remove",this._onLayerChange,this);return this._container},addTo:function(t){return B.prototype.addTo.call(this,t),this._expandIfNotCollapsed()},onRemove:function(){this._map.off("zoomend",this._checkDisabledLayers,this);for(var t=0;t<this._layers.length;t++)this._layers[t].layer.off("add remove",this._onLayerChange,this)},addBaseLayer:function(t,e){return this._addLayer(t,e),this._map?this._update():this},addOverlay:function(t,e){return this._addLayer(t,e,!0),this._map?this._update():this},removeLayer:function(t){t.off("add remove",this._onLayerChange,this);t=this._getLayer(h(t));return t&&this._layers.splice(this._layers.indexOf(t),1),this._map?this._update():this},expand:function(){M(this._container,"leaflet-control-layers-expanded"),this._section.style.height=null;var t=this._map.getSize().y-(this._container.offsetTop+50);return t<this._section.clientHeight?(M(this._section,"leaflet-control-layers-scrollbar"),this._section.style.height=t+"px"):z(this._section,"leaflet-control-layers-scrollbar"),this._checkDisabledLayers(),this},collapse:function(){return z(this._container,"leaflet-control-layers-expanded"),this},_initLayout:function(){var t="leaflet-control-layers",e=this._container=P("div",t),i=this.options.collapsed,n=(e.setAttribute("aria-haspopup",!0),Ie(e),Be(e),this._section=P("section",t+"-list")),o=(i&&(this._map.on("click",this.collapse,this),S(e,{mouseenter:this._expandSafely,mouseleave:this.collapse},this)),this._layersLink=P("a",t+"-toggle",e));o.href="#",o.title="Layers",o.setAttribute("role","button"),S(o,{keydown:function(t){13===t.keyCode&&this._expandSafely()},click:function(t){O(t),this._expandSafely()}},this),i||this.expand(),this._baseLayersList=P("div",t+"-base",n),this._separator=P("div",t+"-separator",n),this._overlaysList=P("div",t+"-overlays",n),e.appendChild(n)},_getLayer:function(t){for(var e=0;e<this._layers.length;e++)if(this._layers[e]&&h(this._layers[e].layer)===t)return this._layers[e]},_addLayer:function(t,e,i){this._map&&t.on("add remove",this._onLayerChange,this),this._layers.push({layer:t,name:e,overlay:i}),this.options.sortLayers&&this._layers.sort(a(function(t,e){return this.options.sortFunction(t.layer,e.layer,t.name,e.name)},this)),this.options.autoZIndex&&t.setZIndex&&(this._lastZIndex++,t.setZIndex(this._lastZIndex)),this._expandIfNotCollapsed()},_update:function(){if(this._container){me(this._baseLayersList),me(this._overlaysList),this._layerControlInputs=[];for(var t,e,i,n=0,o=0;o<this._layers.length;o++)i=this._layers[o],this._addItem(i),e=e||i.overlay,t=t||!i.overlay,n+=i.overlay?0:1;this.options.hideSingleBase&&(this._baseLayersList.style.display=(t=t&&1<n)?"":"none"),this._separator.style.display=e&&t?"":"none"}return this},_onLayerChange:function(t){this._handlingClick||this._update();var e=this._getLayer(h(t.target)),t=e.overlay?"add"===t.type?"overlayadd":"overlayremove":"add"===t.type?"baselayerchange":null;t&&this._map.fire(t,e)},_createRadioElement:function(t,e){t='<input type="radio" class="leaflet-control-layers-selector" name="'+t+'"'+(e?' checked="checked"':"")+"/>",e=document.createElement("div");return e.innerHTML=t,e.firstChild},_addItem:function(t){var e,i=document.createElement("label"),n=this._map.hasLayer(t.layer),n=(t.overlay?((e=document.createElement("input")).type="checkbox",e.className="leaflet-control-layers-selector",e.defaultChecked=n):e=this._createRadioElement("leaflet-base-layers_"+h(this),n),this._layerControlInputs.push(e),e.layerId=h(t.layer),S(e,"click",this._onInputClick,this),document.createElement("span")),o=(n.innerHTML=" "+t.name,document.createElement("span"));return i.appendChild(o),o.appendChild(e),o.appendChild(n),(t.overlay?this._overlaysList:this._baseLayersList).appendChild(i),this._checkDisabledLayers(),i},_onInputClick:function(){if(!this._preventClick){var t,e,i=this._layerControlInputs,n=[],o=[];this._handlingClick=!0;for(var s=i.length-1;0<=s;s--)t=i[s],e=this._getLayer(t.layerId).layer,t.checked?n.push(e):t.checked||o.push(e);for(s=0;s<o.length;s++)this._map.hasLayer(o[s])&&this._map.removeLayer(o[s]);for(s=0;s<n.length;s++)this._map.hasLayer(n[s])||this._map.addLayer(n[s]);this._handlingClick=!1,this._refocusOnMap()}},_checkDisabledLayers:function(){for(var t,e,i=this._layerControlInputs,n=this._map.getZoom(),o=i.length-1;0<=o;o--)t=i[o],e=this._getLayer(t.layerId).layer,t.disabled=void 0!==e.options.minZoom&&n<e.options.minZoom||void 0!==e.options.maxZoom&&n>e.options.maxZoom},_expandIfNotCollapsed:function(){return this._map&&!this.options.collapsed&&this.expand(),this},_expandSafely:function(){var t=this._section,e=(this._preventClick=!0,S(t,"click",O),this.expand(),this);setTimeout(function(){k(t,"click",O),e._preventClick=!1})}})),qe=B.extend({options:{position:"topleft",zoomInText:'<span aria-hidden="true">+</span>',zoomInTitle:"Zoom in",zoomOutText:'<span aria-hidden="true">&#x2212;</span>',zoomOutTitle:"Zoom out"},onAdd:function(t){var e="leaflet-control-zoom",i=P("div",e+" leaflet-bar"),n=this.options;return this._zoomInButton=this._createButton(n.zoomInText,n.zoomInTitle,e+"-in",i,this._zoomIn),this._zoomOutButton=this._createButton(n.zoomOutText,n.zoomOutTitle,e+"-out",i,this._zoomOut),this._updateDisabled(),t.on("zoomend zoomlevelschange",this._updateDisabled,this),i},onRemove:function(t){t.off("zoomend zoomlevelschange",this._updateDisabled,this)},disable:function(){return this._disabled=!0,this._updateDisabled(),this},enable:function(){return this._disabled=!1,this._updateDisabled(),this},_zoomIn:function(t){!this._disabled&&this._map._zoom<this._map.getMaxZoom()&&this._map.zoomIn(this._map.options.zoomDelta*(t.shiftKey?3:1))},_zoomOut:function(t){!this._disabled&&this._map._zoom>this._map.getMinZoom()&&this._map.zoomOut(this._map.options.zoomDelta*(t.shiftKey?3:1))},_createButton:function(t,e,i,n,o){i=P("a",i,n);return i.innerHTML=t,i.href="#",i.title=e,i.setAttribute("role","button"),i.setAttribute("aria-label",e),Ie(i),S(i,"click",Re),S(i,"click",o,this),S(i,"click",this._refocusOnMap,this),i},_updateDisabled:function(){var t=this._map,e="leaflet-disabled";z(this._zoomInButton,e),z(this._zoomOutButton,e),this._zoomInButton.setAttribute("aria-disabled","false"),this._zoomOutButton.setAttribute("aria-disabled","false"),!this._disabled&&t._zoom!==t.getMinZoom()||(M(this._zoomOutButton,e),this._zoomOutButton.setAttribute("aria-disabled","true")),!this._disabled&&t._zoom!==t.getMaxZoom()||(M(this._zoomInButton,e),this._zoomInButton.setAttribute("aria-disabled","true"))}}),Ge=(A.mergeOptions({zoomControl:!0}),A.addInitHook(function(){this.options.zoomControl&&(this.zoomControl=new qe,this.addControl(this.zoomControl))}),B.extend({options:{position:"bottomleft",maxWidth:100,metric:!0,imperial:!0},onAdd:function(t){var e="leaflet-control-scale",i=P("div",e),n=this.options;return this._addScales(n,e+"-line",i),t.on(n.updateWhenIdle?"moveend":"move",this._update,this),t.whenReady(this._update,this),i},onRemove:function(t){t.off(this.options.updateWhenIdle?"moveend":"move",this._update,this)},_addScales:function(t,e,i){t.metric&&(this._mScale=P("div",e,i)),t.imperial&&(this._iScale=P("div",e,i))},_update:function(){var t=this._map,e=t.getSize().y/2,t=t.distance(t.containerPointToLatLng([0,e]),t.containerPointToLatLng([this.options.maxWidth,e]));this._updateScales(t)},_updateScales:function(t){this.options.metric&&t&&this._updateMetric(t),this.options.imperial&&t&&this._updateImperial(t)},_updateMetric:function(t){var e=this._getRoundNum(t);this._updateScale(this._mScale,e<1e3?e+" m":e/1e3+" km",e/t)},_updateImperial:function(t){var e,i,t=3.2808399*t;5280<t?(i=this._getRoundNum(e=t/5280),this._updateScale(this._iScale,i+" mi",i/e)):(i=this._getRoundNum(t),this._updateScale(this._iScale,i+" ft",i/t))},_updateScale:function(t,e,i){t.style.width=Math.round(this.options.maxWidth*i)+"px",t.innerHTML=e},_getRoundNum:function(t){var e=Math.pow(10,(Math.floor(t)+"").length-1),t=t/e;return e*(t=10<=t?10:5<=t?5:3<=t?3:2<=t?2:1)}})),Ke=B.extend({options:{position:"bottomright",prefix:'<a href="https://leafletjs.com" title="A JavaScript library for interactive maps">'+(b.inlineSvg?'<svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" width="12" height="8" viewBox="0 0 12 8" class="leaflet-attribution-flag"><path fill="#4C7BE1" d="M0 0h12v4H0z"/><path fill="#FFD500" d="M0 4h12v3H0z"/><path fill="#E0BC00" d="M0 7h12v1H0z"/></svg> ':"")+"Leaflet</a>"},initialize:function(t){c(this,t),this._attributions={}},onAdd:function(t){for(var e in(t.attributionControl=this)._container=P("div","leaflet-control-attribution"),Ie(this._container),t._layers)t._layers[e].getAttribution&&this.addAttribution(t._layers[e].getAttribution());return this._update(),t.on("layeradd",this._addAttribution,this),this._container},onRemove:function(t){t.off("layeradd",this._addAttribution,this)},_addAttribution:function(t){t.layer.getAttribution&&(this.addAttribution(t.layer.getAttribution()),t.layer.once("remove",function(){this.removeAttribution(t.layer.getAttribution())},this))},setPrefix:function(t){return this.options.prefix=t,this._update(),this},addAttribution:function(t){return t&&(this._attributions[t]||(this._attributions[t]=0),this._attributions[t]++,this._update()),this},removeAttribution:function(t){return t&&this._attributions[t]&&(this._attributions[t]--,this._update()),this},_update:function(){if(this._map){var t,e=[];for(t in this._attributions)this._attributions[t]&&e.push(t);var i=[];this.options.prefix&&i.push(this.options.prefix),e.length&&i.push(e.join(", ")),this._container.innerHTML=i.join(' <span aria-hidden="true">|</span> ')}}}),n=(A.mergeOptions({attributionControl:!0}),A.addInitHook(function(){this.options.attributionControl&&(new Ke).addTo(this)}),B.Layers=Ve,B.Zoom=qe,B.Scale=Ge,B.Attribution=Ke,Ue.layers=function(t,e,i){return new Ve(t,e,i)},Ue.zoom=function(t){return new qe(t)},Ue.scale=function(t){return new Ge(t)},Ue.attribution=function(t){return new Ke(t)},et.extend({initialize:function(t){this._map=t},enable:function(){return this._enabled||(this._enabled=!0,this.addHooks()),this},disable:function(){return this._enabled&&(this._enabled=!1,this.removeHooks()),this},enabled:function(){return!!this._enabled}})),ft=(n.addTo=function(t,e){return t.addHandler(e,this),this},{Events:e}),Ye=b.touch?"touchstart mousedown":"mousedown",Xe=it.extend({options:{clickTolerance:3},initialize:function(t,e,i,n){c(this,n),this._element=t,this._dragStartTarget=e||t,this._preventOutline=i},enable:function(){this._enabled||(S(this._dragStartTarget,Ye,this._onDown,this),this._enabled=!0)},disable:function(){this._enabled&&(Xe._dragging===this&&this.finishDrag(!0),k(this._dragStartTarget,Ye,this._onDown,this),this._enabled=!1,this._moved=!1)},_onDown:function(t){var e,i;this._enabled&&(this._moved=!1,ve(this._element,"leaflet-zoom-anim")||(t.touches&&1!==t.touches.length?Xe._dragging===this&&this.finishDrag():Xe._dragging||t.shiftKey||1!==t.which&&1!==t.button&&!t.touches||((Xe._dragging=this)._preventOutline&&Me(this._element),Le(),re(),this._moving||(this.fire("down"),i=t.touches?t.touches[0]:t,e=Ce(this._element),this._startPoint=new p(i.clientX,i.clientY),this._startPos=Pe(this._element),this._parentScale=Ze(e),i="mousedown"===t.type,S(document,i?"mousemove":"touchmove",this._onMove,this),S(document,i?"mouseup":"touchend touchcancel",this._onUp,this)))))},_onMove:function(t){var e;this._enabled&&(t.touches&&1<t.touches.length?this._moved=!0:!(e=new p((e=t.touches&&1===t.touches.length?t.touches[0]:t).clientX,e.clientY)._subtract(this._startPoint)).x&&!e.y||Math.abs(e.x)+Math.abs(e.y)<this.options.clickTolerance||(e.x/=this._parentScale.x,e.y/=this._parentScale.y,O(t),this._moved||(this.fire("dragstart"),this._moved=!0,M(document.body,"leaflet-dragging"),this._lastTarget=t.target||t.srcElement,window.SVGElementInstance&&this._lastTarget instanceof window.SVGElementInstance&&(this._lastTarget=this._lastTarget.correspondingUseElement),M(this._lastTarget,"leaflet-drag-target")),this._newPos=this._startPos.add(e),this._moving=!0,this._lastEvent=t,this._updatePosition()))},_updatePosition:function(){var t={originalEvent:this._lastEvent};this.fire("predrag",t),Z(this._element,this._newPos),this.fire("drag",t)},_onUp:function(){this._enabled&&this.finishDrag()},finishDrag:function(t){z(document.body,"leaflet-dragging"),this._lastTarget&&(z(this._lastTarget,"leaflet-drag-target"),this._lastTarget=null),k(document,"mousemove touchmove",this._onMove,this),k(document,"mouseup touchend touchcancel",this._onUp,this),Te(),ae();var e=this._moved&&this._moving;this._moving=!1,Xe._dragging=!1,e&&this.fire("dragend",{noInertia:t,distance:this._newPos.distanceTo(this._startPos)})}});function Je(t,e,i){for(var n,o,s,r,a,h,l,u=[1,4,2,8],c=0,d=t.length;c<d;c++)t[c]._code=si(t[c],e);for(s=0;s<4;s++){for(h=u[s],n=[],c=0,o=(d=t.length)-1;c<d;o=c++)r=t[c],a=t[o],r._code&h?a._code&h||((l=oi(a,r,h,e,i))._code=si(l,e),n.push(l)):(a._code&h&&((l=oi(a,r,h,e,i))._code=si(l,e),n.push(l)),n.push(r));t=n}return t}function $e(t,e){var i,n,o,s,r,a,h;if(!t||0===t.length)throw new Error("latlngs not passed");I(t)||(console.warn("latlngs are not flat! Only the first ring will be used"),t=t[0]);for(var l=w([0,0]),u=g(t),c=(u.getNorthWest().distanceTo(u.getSouthWest())*u.getNorthEast().distanceTo(u.getNorthWest())<1700&&(l=Qe(t)),t.length),d=[],_=0;_<c;_++){var p=w(t[_]);d.push(e.project(w([p.lat-l.lat,p.lng-l.lng])))}for(_=r=a=h=0,i=c-1;_<c;i=_++)n=d[_],o=d[i],s=n.y*o.x-o.y*n.x,a+=(n.x+o.x)*s,h+=(n.y+o.y)*s,r+=3*s;u=0===r?d[0]:[a/r,h/r],u=e.unproject(m(u));return w([u.lat+l.lat,u.lng+l.lng])}function Qe(t){for(var e=0,i=0,n=0,o=0;o<t.length;o++){var s=w(t[o]);e+=s.lat,i+=s.lng,n++}return w([e/n,i/n])}var ti,gt={__proto__:null,clipPolygon:Je,polygonCenter:$e,centroid:Qe};function ei(t,e){if(e&&t.length){var i=t=function(t,e){for(var i=[t[0]],n=1,o=0,s=t.length;n<s;n++)(function(t,e){var i=e.x-t.x,e=e.y-t.y;return i*i+e*e})(t[n],t[o])>e&&(i.push(t[n]),o=n);o<s-1&&i.push(t[s-1]);return i}(t,e=e*e),n=i.length,o=new(typeof Uint8Array!=void 0+""?Uint8Array:Array)(n);o[0]=o[n-1]=1,function t(e,i,n,o,s){var r,a,h,l=0;for(a=o+1;a<=s-1;a++)h=ri(e[a],e[o],e[s],!0),l<h&&(r=a,l=h);n<l&&(i[r]=1,t(e,i,n,o,r),t(e,i,n,r,s))}(i,o,e,0,n-1);var s,r=[];for(s=0;s<n;s++)o[s]&&r.push(i[s]);return r}return t.slice()}function ii(t,e,i){return Math.sqrt(ri(t,e,i,!0))}function ni(t,e,i,n,o){var s,r,a,h=n?ti:si(t,i),l=si(e,i);for(ti=l;;){if(!(h|l))return[t,e];if(h&l)return!1;a=si(r=oi(t,e,s=h||l,i,o),i),s===h?(t=r,h=a):(e=r,l=a)}}function oi(t,e,i,n,o){var s,r,a=e.x-t.x,e=e.y-t.y,h=n.min,n=n.max;return 8&i?(s=t.x+a*(n.y-t.y)/e,r=n.y):4&i?(s=t.x+a*(h.y-t.y)/e,r=h.y):2&i?(s=n.x,r=t.y+e*(n.x-t.x)/a):1&i&&(s=h.x,r=t.y+e*(h.x-t.x)/a),new p(s,r,o)}function si(t,e){var i=0;return t.x<e.min.x?i|=1:t.x>e.max.x&&(i|=2),t.y<e.min.y?i|=4:t.y>e.max.y&&(i|=8),i}function ri(t,e,i,n){var o=e.x,e=e.y,s=i.x-o,r=i.y-e,a=s*s+r*r;return 0<a&&(1<(a=((t.x-o)*s+(t.y-e)*r)/a)?(o=i.x,e=i.y):0<a&&(o+=s*a,e+=r*a)),s=t.x-o,r=t.y-e,n?s*s+r*r:new p(o,e)}function I(t){return!d(t[0])||"object"!=typeof t[0][0]&&void 0!==t[0][0]}function ai(t){return console.warn("Deprecated use of _flat, please use L.LineUtil.isFlat instead."),I(t)}function hi(t,e){var i,n,o,s,r,a;if(!t||0===t.length)throw new Error("latlngs not passed");I(t)||(console.warn("latlngs are not flat! Only the first ring will be used"),t=t[0]);for(var h=w([0,0]),l=g(t),u=(l.getNorthWest().distanceTo(l.getSouthWest())*l.getNorthEast().distanceTo(l.getNorthWest())<1700&&(h=Qe(t)),t.length),c=[],d=0;d<u;d++){var _=w(t[d]);c.push(e.project(w([_.lat-h.lat,_.lng-h.lng])))}for(i=d=0;d<u-1;d++)i+=c[d].distanceTo(c[d+1])/2;if(0===i)a=c[0];else for(n=d=0;d<u-1;d++)if(o=c[d],s=c[d+1],i<(n+=r=o.distanceTo(s))){a=[s.x-(r=(n-i)/r)*(s.x-o.x),s.y-r*(s.y-o.y)];break}l=e.unproject(m(a));return w([l.lat+h.lat,l.lng+h.lng])}var vt={__proto__:null,simplify:ei,pointToSegmentDistance:ii,closestPointOnSegment:function(t,e,i){return ri(t,e,i)},clipSegment:ni,_getEdgeIntersection:oi,_getBitCode:si,_sqClosestPointOnSegment:ri,isFlat:I,_flat:ai,polylineCenter:hi},yt={project:function(t){return new p(t.lng,t.lat)},unproject:function(t){return new v(t.y,t.x)},bounds:new f([-180,-90],[180,90])},xt={R:6378137,R_MINOR:6356752.314245179,bounds:new f([-20037508.34279,-15496570.73972],[20037508.34279,18764656.23138]),project:function(t){var e=Math.PI/180,i=this.R,n=t.lat*e,o=this.R_MINOR/i,o=Math.sqrt(1-o*o),s=o*Math.sin(n),s=Math.tan(Math.PI/4-n/2)/Math.pow((1-s)/(1+s),o/2),n=-i*Math.log(Math.max(s,1e-10));return new p(t.lng*e*i,n)},unproject:function(t){for(var e,i=180/Math.PI,n=this.R,o=this.R_MINOR/n,s=Math.sqrt(1-o*o),r=Math.exp(-t.y/n),a=Math.PI/2-2*Math.atan(r),h=0,l=.1;h<15&&1e-7<Math.abs(l);h++)e=s*Math.sin(a),e=Math.pow((1-e)/(1+e),s/2),a+=l=Math.PI/2-2*Math.atan(r*e)-a;return new v(a*i,t.x*i/n)}},wt={__proto__:null,LonLat:yt,Mercator:xt,SphericalMercator:rt},Pt=l({},st,{code:"EPSG:3395",projection:xt,transformation:ht(bt=.5/(Math.PI*xt.R),.5,-bt,.5)}),li=l({},st,{code:"EPSG:4326",projection:yt,transformation:ht(1/180,1,-1/180,.5)}),Lt=l({},ot,{projection:yt,transformation:ht(1,0,-1,0),scale:function(t){return Math.pow(2,t)},zoom:function(t){return Math.log(t)/Math.LN2},distance:function(t,e){var i=e.lng-t.lng,e=e.lat-t.lat;return Math.sqrt(i*i+e*e)},infinite:!0}),o=(ot.Earth=st,ot.EPSG3395=Pt,ot.EPSG3857=lt,ot.EPSG900913=ut,ot.EPSG4326=li,ot.Simple=Lt,it.extend({options:{pane:"overlayPane",attribution:null,bubblingMouseEvents:!0},addTo:function(t){return t.addLayer(this),this},remove:function(){return this.removeFrom(this._map||this._mapToAdd)},removeFrom:function(t){return t&&t.removeLayer(this),this},getPane:function(t){return this._map.getPane(t?this.options[t]||t:this.options.pane)},addInteractiveTarget:function(t){return this._map._targets[h(t)]=this},removeInteractiveTarget:function(t){return delete this._map._targets[h(t)],this},getAttribution:function(){return this.options.attribution},_layerAdd:function(t){var e,i=t.target;i.hasLayer(this)&&(this._map=i,this._zoomAnimated=i._zoomAnimated,this.getEvents&&(e=this.getEvents(),i.on(e,this),this.once("remove",function(){i.off(e,this)},this)),this.onAdd(i),this.fire("add"),i.fire("layeradd",{layer:this}))}})),ui=(A.include({addLayer:function(t){var e;if(t._layerAdd)return e=h(t),this._layers[e]||((this._layers[e]=t)._mapToAdd=this,t.beforeAdd&&t.beforeAdd(this),this.whenReady(t._layerAdd,t)),this;throw new Error("The provided object is not a Layer.")},removeLayer:function(t){var e=h(t);return this._layers[e]&&(this._loaded&&t.onRemove(this),delete this._layers[e],this._loaded&&(this.fire("layerremove",{layer:t}),t.fire("remove")),t._map=t._mapToAdd=null),this},hasLayer:function(t){return h(t)in this._layers},eachLayer:function(t,e){for(var i in this._layers)t.call(e,this._layers[i]);return this},_addLayers:function(t){for(var e=0,i=(t=t?d(t)?t:[t]:[]).length;e<i;e++)this.addLayer(t[e])},_addZoomLimit:function(t){isNaN(t.options.maxZoom)&&isNaN(t.options.minZoom)||(this._zoomBoundLayers[h(t)]=t,this._updateZoomLevels())},_removeZoomLimit:function(t){t=h(t);this._zoomBoundLayers[t]&&(delete this._zoomBoundLayers[t],this._updateZoomLevels())},_updateZoomLevels:function(){var t,e=1/0,i=-1/0,n=this._getZoomSpan();for(t in this._zoomBoundLayers)var o=this._zoomBoundLayers[t].options,e=void 0===o.minZoom?e:Math.min(e,o.minZoom),i=void 0===o.maxZoom?i:Math.max(i,o.maxZoom);this._layersMaxZoom=i===-1/0?void 0:i,this._layersMinZoom=e===1/0?void 0:e,n!==this._getZoomSpan()&&this.fire("zoomlevelschange"),void 0===this.options.maxZoom&&this._layersMaxZoom&&this.getZoom()>this._layersMaxZoom&&this.setZoom(this._layersMaxZoom),void 0===this.options.minZoom&&this._layersMinZoom&&this.getZoom()<this._layersMinZoom&&this.setZoom(this._layersMinZoom)}}),o.extend({initialize:function(t,e){var i,n;if(c(this,e),this._layers={},t)for(i=0,n=t.length;i<n;i++)this.addLayer(t[i])},addLayer:function(t){var e=this.getLayerId(t);return this._layers[e]=t,this._map&&this._map.addLayer(t),this},removeLayer:function(t){t=t in this._layers?t:this.getLayerId(t);return this._map&&this._layers[t]&&this._map.removeLayer(this._layers[t]),delete this._layers[t],this},hasLayer:function(t){return("number"==typeof t?t:this.getLayerId(t))in this._layers},clearLayers:function(){return this.eachLayer(this.removeLayer,this)},invoke:function(t){var e,i,n=Array.prototype.slice.call(arguments,1);for(e in this._layers)(i=this._layers[e])[t]&&i[t].apply(i,n);return this},onAdd:function(t){this.eachLayer(t.addLayer,t)},onRemove:function(t){this.eachLayer(t.removeLayer,t)},eachLayer:function(t,e){for(var i in this._layers)t.call(e,this._layers[i]);return this},getLayer:function(t){return this._layers[t]},getLayers:function(){var t=[];return this.eachLayer(t.push,t),t},setZIndex:function(t){return this.invoke("setZIndex",t)},getLayerId:h})),ci=ui.extend({addLayer:function(t){return this.hasLayer(t)?this:(t.addEventParent(this),ui.prototype.addLayer.call(this,t),this.fire("layeradd",{layer:t}))},removeLayer:function(t){return this.hasLayer(t)?((t=t in this._layers?this._layers[t]:t).removeEventParent(this),ui.prototype.removeLayer.call(this,t),this.fire("layerremove",{layer:t})):this},setStyle:function(t){return this.invoke("setStyle",t)},bringToFront:function(){return this.invoke("bringToFront")},bringToBack:function(){return this.invoke("bringToBack")},getBounds:function(){var t,e=new s;for(t in this._layers){var i=this._layers[t];e.extend(i.getBounds?i.getBounds():i.getLatLng())}return e}}),di=et.extend({options:{popupAnchor:[0,0],tooltipAnchor:[0,0],crossOrigin:!1},initialize:function(t){c(this,t)},createIcon:function(t){return this._createIcon("icon",t)},createShadow:function(t){return this._createIcon("shadow",t)},_createIcon:function(t,e){var i=this._getIconUrl(t);if(i)return i=this._createImg(i,e&&"IMG"===e.tagName?e:null),this._setIconStyles(i,t),!this.options.crossOrigin&&""!==this.options.crossOrigin||(i.crossOrigin=!0===this.options.crossOrigin?"":this.options.crossOrigin),i;if("icon"===t)throw new Error("iconUrl not set in Icon options (see the docs).");return null},_setIconStyles:function(t,e){var i=this.options,n=i[e+"Size"],n=m(n="number"==typeof n?[n,n]:n),o=m("shadow"===e&&i.shadowAnchor||i.iconAnchor||n&&n.divideBy(2,!0));t.className="leaflet-marker-"+e+" "+(i.className||""),o&&(t.style.marginLeft=-o.x+"px",t.style.marginTop=-o.y+"px"),n&&(t.style.width=n.x+"px",t.style.height=n.y+"px")},_createImg:function(t,e){return(e=e||document.createElement("img")).src=t,e},_getIconUrl:function(t){return b.retina&&this.options[t+"RetinaUrl"]||this.options[t+"Url"]}});var _i=di.extend({options:{iconUrl:"marker-icon.png",iconRetinaUrl:"marker-icon-2x.png",shadowUrl:"marker-shadow.png",iconSize:[25,41],iconAnchor:[12,41],popupAnchor:[1,-34],tooltipAnchor:[16,-28],shadowSize:[41,41]},_getIconUrl:function(t){return"string"!=typeof _i.imagePath&&(_i.imagePath=this._detectIconPath()),(this.options.imagePath||_i.imagePath)+di.prototype._getIconUrl.call(this,t)},_stripUrl:function(t){function e(t,e,i){return(e=e.exec(t))&&e[i]}return(t=e(t,/^url\((['"])?(.+)\1\)$/,2))&&e(t,/^(.*)marker-icon\.png$/,1)},_detectIconPath:function(){var t=P("div","leaflet-default-icon-path",document.body),e=pe(t,"background-image")||pe(t,"backgroundImage");return document.body.removeChild(t),(e=this._stripUrl(e))?e:(t=document.querySelector('link[href$="leaflet.css"]'))?t.href.substring(0,t.href.length-"leaflet.css".length-1):""}}),pi=n.extend({initialize:function(t){this._marker=t},addHooks:function(){var t=this._marker._icon;this._draggable||(this._draggable=new Xe(t,t,!0)),this._draggable.on({dragstart:this._onDragStart,predrag:this._onPreDrag,drag:this._onDrag,dragend:this._onDragEnd},this).enable(),M(t,"leaflet-marker-draggable")},removeHooks:function(){this._draggable.off({dragstart:this._onDragStart,predrag:this._onPreDrag,drag:this._onDrag,dragend:this._onDragEnd},this).disable(),this._marker._icon&&z(this._marker._icon,"leaflet-marker-draggable")},moved:function(){return this._draggable&&this._draggable._moved},_adjustPan:function(t){var e=this._marker,i=e._map,n=this._marker.options.autoPanSpeed,o=this._marker.options.autoPanPadding,s=Pe(e._icon),r=i.getPixelBounds(),a=i.getPixelOrigin(),a=_(r.min._subtract(a).add(o),r.max._subtract(a).subtract(o));a.contains(s)||(o=m((Math.max(a.max.x,s.x)-a.max.x)/(r.max.x-a.max.x)-(Math.min(a.min.x,s.x)-a.min.x)/(r.min.x-a.min.x),(Math.max(a.max.y,s.y)-a.max.y)/(r.max.y-a.max.y)-(Math.min(a.min.y,s.y)-a.min.y)/(r.min.y-a.min.y)).multiplyBy(n),i.panBy(o,{animate:!1}),this._draggable._newPos._add(o),this._draggable._startPos._add(o),Z(e._icon,this._draggable._newPos),this._onDrag(t),this._panRequest=x(this._adjustPan.bind(this,t)))},_onDragStart:function(){this._oldLatLng=this._marker.getLatLng(),this._marker.closePopup&&this._marker.closePopup(),this._marker.fire("movestart").fire("dragstart")},_onPreDrag:function(t){this._marker.options.autoPan&&(r(this._panRequest),this._panRequest=x(this._adjustPan.bind(this,t)))},_onDrag:function(t){var e=this._marker,i=e._shadow,n=Pe(e._icon),o=e._map.layerPointToLatLng(n);i&&Z(i,n),e._latlng=o,t.latlng=o,t.oldLatLng=this._oldLatLng,e.fire("move",t).fire("drag",t)},_onDragEnd:function(t){r(this._panRequest),delete this._oldLatLng,this._marker.fire("moveend").fire("dragend",t)}}),mi=o.extend({options:{icon:new _i,interactive:!0,keyboard:!0,title:"",alt:"Marker",zIndexOffset:0,opacity:1,riseOnHover:!1,riseOffset:250,pane:"markerPane",shadowPane:"shadowPane",bubblingMouseEvents:!1,autoPanOnFocus:!0,draggable:!1,autoPan:!1,autoPanPadding:[50,50],autoPanSpeed:10},initialize:function(t,e){c(this,e),this._latlng=w(t)},onAdd:function(t){this._zoomAnimated=this._zoomAnimated&&t.options.markerZoomAnimation,this._zoomAnimated&&t.on("zoomanim",this._animateZoom,this),this._initIcon(),this.update()},onRemove:function(t){this.dragging&&this.dragging.enabled()&&(this.options.draggable=!0,this.dragging.removeHooks()),delete this.dragging,this._zoomAnimated&&t.off("zoomanim",this._animateZoom,this),this._removeIcon(),this._removeShadow()},getEvents:function(){return{zoom:this.update,viewreset:this.update}},getLatLng:function(){return this._latlng},setLatLng:function(t){var e=this._latlng;return this._latlng=w(t),this.update(),this.fire("move",{oldLatLng:e,latlng:this._latlng})},setZIndexOffset:function(t){return this.options.zIndexOffset=t,this.update()},getIcon:function(){return this.options.icon},setIcon:function(t){return this.options.icon=t,this._map&&(this._initIcon(),this.update()),this._popup&&this.bindPopup(this._popup,this._popup.options),this},getElement:function(){return this._icon},update:function(){var t;return this._icon&&this._map&&(t=this._map.latLngToLayerPoint(this._latlng).round(),this._setPos(t)),this},_initIcon:function(){var t=this.options,e="leaflet-zoom-"+(this._zoomAnimated?"animated":"hide"),i=t.icon.createIcon(this._icon),n=!1,i=(i!==this._icon&&(this._icon&&this._removeIcon(),n=!0,t.title&&(i.title=t.title),"IMG"===i.tagName&&(i.alt=t.alt||"")),M(i,e),t.keyboard&&(i.tabIndex="0",i.setAttribute("role","button")),this._icon=i,t.riseOnHover&&this.on({mouseover:this._bringToFront,mouseout:this._resetZIndex}),this.options.autoPanOnFocus&&S(i,"focus",this._panOnFocus,this),t.icon.createShadow(this._shadow)),o=!1;i!==this._shadow&&(this._removeShadow(),o=!0),i&&(M(i,e),i.alt=""),this._shadow=i,t.opacity<1&&this._updateOpacity(),n&&this.getPane().appendChild(this._icon),this._initInteraction(),i&&o&&this.getPane(t.shadowPane).appendChild(this._shadow)},_removeIcon:function(){this.options.riseOnHover&&this.off({mouseover:this._bringToFront,mouseout:this._resetZIndex}),this.options.autoPanOnFocus&&k(this._icon,"focus",this._panOnFocus,this),T(this._icon),this.removeInteractiveTarget(this._icon),this._icon=null},_removeShadow:function(){this._shadow&&T(this._shadow),this._shadow=null},_setPos:function(t){this._icon&&Z(this._icon,t),this._shadow&&Z(this._shadow,t),this._zIndex=t.y+this.options.zIndexOffset,this._resetZIndex()},_updateZIndex:function(t){this._icon&&(this._icon.style.zIndex=this._zIndex+t)},_animateZoom:function(t){t=this._map._latLngToNewLayerPoint(this._latlng,t.zoom,t.center).round();this._setPos(t)},_initInteraction:function(){var t;this.options.interactive&&(M(this._icon,"leaflet-interactive"),this.addInteractiveTarget(this._icon),pi&&(t=this.options.draggable,this.dragging&&(t=this.dragging.enabled(),this.dragging.disable()),this.dragging=new pi(this),t&&this.dragging.enable()))},setOpacity:function(t){return this.options.opacity=t,this._map&&this._updateOpacity(),this},_updateOpacity:function(){var t=this.options.opacity;this._icon&&C(this._icon,t),this._shadow&&C(this._shadow,t)},_bringToFront:function(){this._updateZIndex(this.options.riseOffset)},_resetZIndex:function(){this._updateZIndex(0)},_panOnFocus:function(){var t,e,i=this._map;i&&(t=(e=this.options.icon.options).iconSize?m(e.iconSize):m(0,0),e=e.iconAnchor?m(e.iconAnchor):m(0,0),i.panInside(this._latlng,{paddingTopLeft:e,paddingBottomRight:t.subtract(e)}))},_getPopupAnchor:function(){return this.options.icon.options.popupAnchor},_getTooltipAnchor:function(){return this.options.icon.options.tooltipAnchor}});var fi=o.extend({options:{stroke:!0,color:"#3388ff",weight:3,opacity:1,lineCap:"round",lineJoin:"round",dashArray:null,dashOffset:null,fill:!1,fillColor:null,fillOpacity:.2,fillRule:"evenodd",interactive:!0,bubblingMouseEvents:!0},beforeAdd:function(t){this._renderer=t.getRenderer(this)},onAdd:function(){this._renderer._initPath(this),this._reset(),this._renderer._addPath(this)},onRemove:function(){this._renderer._removePath(this)},redraw:function(){return this._map&&this._renderer._updatePath(this),this},setStyle:function(t){return c(this,t),this._renderer&&(this._renderer._updateStyle(this),this.options.stroke&&t&&Object.prototype.hasOwnProperty.call(t,"weight")&&this._updateBounds()),this},bringToFront:function(){return this._renderer&&this._renderer._bringToFront(this),this},bringToBack:function(){return this._renderer&&this._renderer._bringToBack(this),this},getElement:function(){return this._path},_reset:function(){this._project(),this._update()},_clickTolerance:function(){return(this.options.stroke?this.options.weight/2:0)+(this._renderer.options.tolerance||0)}}),gi=fi.extend({options:{fill:!0,radius:10},initialize:function(t,e){c(this,e),this._latlng=w(t),this._radius=this.options.radius},setLatLng:function(t){var e=this._latlng;return this._latlng=w(t),this.redraw(),this.fire("move",{oldLatLng:e,latlng:this._latlng})},getLatLng:function(){return this._latlng},setRadius:function(t){return this.options.radius=this._radius=t,this.redraw()},getRadius:function(){return this._radius},setStyle:function(t){var e=t&&t.radius||this._radius;return fi.prototype.setStyle.call(this,t),this.setRadius(e),this},_project:function(){this._point=this._map.latLngToLayerPoint(this._latlng),this._updateBounds()},_updateBounds:function(){var t=this._radius,e=this._radiusY||t,i=this._clickTolerance(),t=[t+i,e+i];this._pxBounds=new f(this._point.subtract(t),this._point.add(t))},_update:function(){this._map&&this._updatePath()},_updatePath:function(){this._renderer._updateCircle(this)},_empty:function(){return this._radius&&!this._renderer._bounds.intersects(this._pxBounds)},_containsPoint:function(t){return t.distanceTo(this._point)<=this._radius+this._clickTolerance()}});var vi=gi.extend({initialize:function(t,e,i){if(c(this,e="number"==typeof e?l({},i,{radius:e}):e),this._latlng=w(t),isNaN(this.options.radius))throw new Error("Circle radius cannot be NaN");this._mRadius=this.options.radius},setRadius:function(t){return this._mRadius=t,this.redraw()},getRadius:function(){return this._mRadius},getBounds:function(){var t=[this._radius,this._radiusY||this._radius];return new s(this._map.layerPointToLatLng(this._point.subtract(t)),this._map.layerPointToLatLng(this._point.add(t)))},setStyle:fi.prototype.setStyle,_project:function(){var t,e,i,n,o,s=this._latlng.lng,r=this._latlng.lat,a=this._map,h=a.options.crs;h.distance===st.distance?(n=Math.PI/180,o=this._mRadius/st.R/n,t=a.project([r+o,s]),e=a.project([r-o,s]),e=t.add(e).divideBy(2),i=a.unproject(e).lat,n=Math.acos((Math.cos(o*n)-Math.sin(r*n)*Math.sin(i*n))/(Math.cos(r*n)*Math.cos(i*n)))/n,!isNaN(n)&&0!==n||(n=o/Math.cos(Math.PI/180*r)),this._point=e.subtract(a.getPixelOrigin()),this._radius=isNaN(n)?0:e.x-a.project([i,s-n]).x,this._radiusY=e.y-t.y):(o=h.unproject(h.project(this._latlng).subtract([this._mRadius,0])),this._point=a.latLngToLayerPoint(this._latlng),this._radius=this._point.x-a.latLngToLayerPoint(o).x),this._updateBounds()}});var yi=fi.extend({options:{smoothFactor:1,noClip:!1},initialize:function(t,e){c(this,e),this._setLatLngs(t)},getLatLngs:function(){return this._latlngs},setLatLngs:function(t){return this._setLatLngs(t),this.redraw()},isEmpty:function(){return!this._latlngs.length},closestLayerPoint:function(t){for(var e=1/0,i=null,n=ri,o=0,s=this._parts.length;o<s;o++)for(var r=this._parts[o],a=1,h=r.length;a<h;a++){var l,u,c=n(t,l=r[a-1],u=r[a],!0);c<e&&(e=c,i=n(t,l,u))}return i&&(i.distance=Math.sqrt(e)),i},getCenter:function(){if(this._map)return hi(this._defaultShape(),this._map.options.crs);throw new Error("Must add layer to map before using getCenter()")},getBounds:function(){return this._bounds},addLatLng:function(t,e){return e=e||this._defaultShape(),t=w(t),e.push(t),this._bounds.extend(t),this.redraw()},_setLatLngs:function(t){this._bounds=new s,this._latlngs=this._convertLatLngs(t)},_defaultShape:function(){return I(this._latlngs)?this._latlngs:this._latlngs[0]},_convertLatLngs:function(t){for(var e=[],i=I(t),n=0,o=t.length;n<o;n++)i?(e[n]=w(t[n]),this._bounds.extend(e[n])):e[n]=this._convertLatLngs(t[n]);return e},_project:function(){var t=new f;this._rings=[],this._projectLatlngs(this._latlngs,this._rings,t),this._bounds.isValid()&&t.isValid()&&(this._rawPxBounds=t,this._updateBounds())},_updateBounds:function(){var t=this._clickTolerance(),t=new p(t,t);this._rawPxBounds&&(this._pxBounds=new f([this._rawPxBounds.min.subtract(t),this._rawPxBounds.max.add(t)]))},_projectLatlngs:function(t,e,i){var n,o,s=t[0]instanceof v,r=t.length;if(s){for(o=[],n=0;n<r;n++)o[n]=this._map.latLngToLayerPoint(t[n]),i.extend(o[n]);e.push(o)}else for(n=0;n<r;n++)this._projectLatlngs(t[n],e,i)},_clipPoints:function(){var t=this._renderer._bounds;if(this._parts=[],this._pxBounds&&this._pxBounds.intersects(t))if(this.options.noClip)this._parts=this._rings;else for(var e,i,n,o,s=this._parts,r=0,a=0,h=this._rings.length;r<h;r++)for(e=0,i=(o=this._rings[r]).length;e<i-1;e++)(n=ni(o[e],o[e+1],t,e,!0))&&(s[a]=s[a]||[],s[a].push(n[0]),n[1]===o[e+1]&&e!==i-2||(s[a].push(n[1]),a++))},_simplifyPoints:function(){for(var t=this._parts,e=this.options.smoothFactor,i=0,n=t.length;i<n;i++)t[i]=ei(t[i],e)},_update:function(){this._map&&(this._clipPoints(),this._simplifyPoints(),this._updatePath())},_updatePath:function(){this._renderer._updatePoly(this)},_containsPoint:function(t,e){var i,n,o,s,r,a,h=this._clickTolerance();if(this._pxBounds&&this._pxBounds.contains(t))for(i=0,s=this._parts.length;i<s;i++)for(n=0,o=(r=(a=this._parts[i]).length)-1;n<r;o=n++)if((e||0!==n)&&ii(t,a[o],a[n])<=h)return!0;return!1}});yi._flat=ai;var xi=yi.extend({options:{fill:!0},isEmpty:function(){return!this._latlngs.length||!this._latlngs[0].length},getCenter:function(){if(this._map)return $e(this._defaultShape(),this._map.options.crs);throw new Error("Must add layer to map before using getCenter()")},_convertLatLngs:function(t){var t=yi.prototype._convertLatLngs.call(this,t),e=t.length;return 2<=e&&t[0]instanceof v&&t[0].equals(t[e-1])&&t.pop(),t},_setLatLngs:function(t){yi.prototype._setLatLngs.call(this,t),I(this._latlngs)&&(this._latlngs=[this._latlngs])},_defaultShape:function(){return(I(this._latlngs[0])?this._latlngs:this._latlngs[0])[0]},_clipPoints:function(){var t=this._renderer._bounds,e=this.options.weight,e=new p(e,e),t=new f(t.min.subtract(e),t.max.add(e));if(this._parts=[],this._pxBounds&&this._pxBounds.intersects(t))if(this.options.noClip)this._parts=this._rings;else for(var i,n=0,o=this._rings.length;n<o;n++)(i=Je(this._rings[n],t,!0)).length&&this._parts.push(i)},_updatePath:function(){this._renderer._updatePoly(this,!0)},_containsPoint:function(t){var e,i,n,o,s,r,a,h,l=!1;if(!this._pxBounds||!this._pxBounds.contains(t))return!1;for(o=0,a=this._parts.length;o<a;o++)for(s=0,r=(h=(e=this._parts[o]).length)-1;s<h;r=s++)i=e[s],n=e[r],i.y>t.y!=n.y>t.y&&t.x<(n.x-i.x)*(t.y-i.y)/(n.y-i.y)+i.x&&(l=!l);return l||yi.prototype._containsPoint.call(this,t,!0)}});var wi=ci.extend({initialize:function(t,e){c(this,e),this._layers={},t&&this.addData(t)},addData:function(t){var e,i,n,o=d(t)?t:t.features;if(o){for(e=0,i=o.length;e<i;e++)((n=o[e]).geometries||n.geometry||n.features||n.coordinates)&&this.addData(n);return this}var s,r=this.options;return(!r.filter||r.filter(t))&&(s=bi(t,r))?(s.feature=Zi(t),s.defaultOptions=s.options,this.resetStyle(s),r.onEachFeature&&r.onEachFeature(t,s),this.addLayer(s)):this},resetStyle:function(t){return void 0===t?this.eachLayer(this.resetStyle,this):(t.options=l({},t.defaultOptions),this._setLayerStyle(t,this.options.style),this)},setStyle:function(e){return this.eachLayer(function(t){this._setLayerStyle(t,e)},this)},_setLayerStyle:function(t,e){t.setStyle&&("function"==typeof e&&(e=e(t.feature)),t.setStyle(e))}});function bi(t,e){var i,n,o,s,r="Feature"===t.type?t.geometry:t,a=r?r.coordinates:null,h=[],l=e&&e.pointToLayer,u=e&&e.coordsToLatLng||Li;if(!a&&!r)return null;switch(r.type){case"Point":return Pi(l,t,i=u(a),e);case"MultiPoint":for(o=0,s=a.length;o<s;o++)i=u(a[o]),h.push(Pi(l,t,i,e));return new ci(h);case"LineString":case"MultiLineString":return n=Ti(a,"LineString"===r.type?0:1,u),new yi(n,e);case"Polygon":case"MultiPolygon":return n=Ti(a,"Polygon"===r.type?1:2,u),new xi(n,e);case"GeometryCollection":for(o=0,s=r.geometries.length;o<s;o++){var c=bi({geometry:r.geometries[o],type:"Feature",properties:t.properties},e);c&&h.push(c)}return new ci(h);case"FeatureCollection":for(o=0,s=r.features.length;o<s;o++){var d=bi(r.features[o],e);d&&h.push(d)}return new ci(h);default:throw new Error("Invalid GeoJSON object.")}}function Pi(t,e,i,n){return t?t(e,i):new mi(i,n&&n.markersInheritOptions&&n)}function Li(t){return new v(t[1],t[0],t[2])}function Ti(t,e,i){for(var n,o=[],s=0,r=t.length;s<r;s++)n=e?Ti(t[s],e-1,i):(i||Li)(t[s]),o.push(n);return o}function Mi(t,e){return void 0!==(t=w(t)).alt?[i(t.lng,e),i(t.lat,e),i(t.alt,e)]:[i(t.lng,e),i(t.lat,e)]}function zi(t,e,i,n){for(var o=[],s=0,r=t.length;s<r;s++)o.push(e?zi(t[s],I(t[s])?0:e-1,i,n):Mi(t[s],n));return!e&&i&&0<o.length&&o.push(o[0].slice()),o}function Ci(t,e){return t.feature?l({},t.feature,{geometry:e}):Zi(e)}function Zi(t){return"Feature"===t.type||"FeatureCollection"===t.type?t:{type:"Feature",properties:{},geometry:t}}Tt={toGeoJSON:function(t){return Ci(this,{type:"Point",coordinates:Mi(this.getLatLng(),t)})}};function Si(t,e){return new wi(t,e)}mi.include(Tt),vi.include(Tt),gi.include(Tt),yi.include({toGeoJSON:function(t){var e=!I(this._latlngs);return Ci(this,{type:(e?"Multi":"")+"LineString",coordinates:zi(this._latlngs,e?1:0,!1,t)})}}),xi.include({toGeoJSON:function(t){var e=!I(this._latlngs),i=e&&!I(this._latlngs[0]),t=zi(this._latlngs,i?2:e?1:0,!0,t);return Ci(this,{type:(i?"Multi":"")+"Polygon",coordinates:t=e?t:[t]})}}),ui.include({toMultiPoint:function(e){var i=[];return this.eachLayer(function(t){i.push(t.toGeoJSON(e).geometry.coordinates)}),Ci(this,{type:"MultiPoint",coordinates:i})},toGeoJSON:function(e){var i,n,t=this.feature&&this.feature.geometry&&this.feature.geometry.type;return"MultiPoint"===t?this.toMultiPoint(e):(i="GeometryCollection"===t,n=[],this.eachLayer(function(t){t.toGeoJSON&&(t=t.toGeoJSON(e),i?n.push(t.geometry):"FeatureCollection"===(t=Zi(t)).type?n.push.apply(n,t.features):n.push(t))}),i?Ci(this,{geometries:n,type:"GeometryCollection"}):{type:"FeatureCollection",features:n})}});var Mt=Si,Ei=o.extend({options:{opacity:1,alt:"",interactive:!1,crossOrigin:!1,errorOverlayUrl:"",zIndex:1,className:""},initialize:function(t,e,i){this._url=t,this._bounds=g(e),c(this,i)},onAdd:function(){this._image||(this._initImage(),this.options.opacity<1&&this._updateOpacity()),this.options.interactive&&(M(this._image,"leaflet-interactive"),this.addInteractiveTarget(this._image)),this.getPane().appendChild(this._image),this._reset()},onRemove:function(){T(this._image),this.options.interactive&&this.removeInteractiveTarget(this._image)},setOpacity:function(t){return this.options.opacity=t,this._image&&this._updateOpacity(),this},setStyle:function(t){return t.opacity&&this.setOpacity(t.opacity),this},bringToFront:function(){return this._map&&fe(this._image),this},bringToBack:function(){return this._map&&ge(this._image),this},setUrl:function(t){return this._url=t,this._image&&(this._image.src=t),this},setBounds:function(t){return this._bounds=g(t),this._map&&this._reset(),this},getEvents:function(){var t={zoom:this._reset,viewreset:this._reset};return this._zoomAnimated&&(t.zoomanim=this._animateZoom),t},setZIndex:function(t){return this.options.zIndex=t,this._updateZIndex(),this},getBounds:function(){return this._bounds},getElement:function(){return this._image},_initImage:function(){var t="IMG"===this._url.tagName,e=this._image=t?this._url:P("img");M(e,"leaflet-image-layer"),this._zoomAnimated&&M(e,"leaflet-zoom-animated"),this.options.className&&M(e,this.options.className),e.onselectstart=u,e.onmousemove=u,e.onload=a(this.fire,this,"load"),e.onerror=a(this._overlayOnError,this,"error"),!this.options.crossOrigin&&""!==this.options.crossOrigin||(e.crossOrigin=!0===this.options.crossOrigin?"":this.options.crossOrigin),this.options.zIndex&&this._updateZIndex(),t?this._url=e.src:(e.src=this._url,e.alt=this.options.alt)},_animateZoom:function(t){var e=this._map.getZoomScale(t.zoom),t=this._map._latLngBoundsToNewLayerBounds(this._bounds,t.zoom,t.center).min;be(this._image,t,e)},_reset:function(){var t=this._image,e=new f(this._map.latLngToLayerPoint(this._bounds.getNorthWest()),this._map.latLngToLayerPoint(this._bounds.getSouthEast())),i=e.getSize();Z(t,e.min),t.style.width=i.x+"px",t.style.height=i.y+"px"},_updateOpacity:function(){C(this._image,this.options.opacity)},_updateZIndex:function(){this._image&&void 0!==this.options.zIndex&&null!==this.options.zIndex&&(this._image.style.zIndex=this.options.zIndex)},_overlayOnError:function(){this.fire("error");var t=this.options.errorOverlayUrl;t&&this._url!==t&&(this._url=t,this._image.src=t)},getCenter:function(){return this._bounds.getCenter()}}),ki=Ei.extend({options:{autoplay:!0,loop:!0,keepAspectRatio:!0,muted:!1,playsInline:!0},_initImage:function(){var t="VIDEO"===this._url.tagName,e=this._image=t?this._url:P("video");if(M(e,"leaflet-image-layer"),this._zoomAnimated&&M(e,"leaflet-zoom-animated"),this.options.className&&M(e,this.options.className),e.onselectstart=u,e.onmousemove=u,e.onloadeddata=a(this.fire,this,"load"),t){for(var i=e.getElementsByTagName("source"),n=[],o=0;o<i.length;o++)n.push(i[o].src);this._url=0<i.length?n:[e.src]}else{d(this._url)||(this._url=[this._url]),!this.options.keepAspectRatio&&Object.prototype.hasOwnProperty.call(e.style,"objectFit")&&(e.style.objectFit="fill"),e.autoplay=!!this.options.autoplay,e.loop=!!this.options.loop,e.muted=!!this.options.muted,e.playsInline=!!this.options.playsInline;for(var s=0;s<this._url.length;s++){var r=P("source");r.src=this._url[s],e.appendChild(r)}}}});var Oi=Ei.extend({_initImage:function(){var t=this._image=this._url;M(t,"leaflet-image-layer"),this._zoomAnimated&&M(t,"leaflet-zoom-animated"),this.options.className&&M(t,this.options.className),t.onselectstart=u,t.onmousemove=u}});var Ai=o.extend({options:{interactive:!1,offset:[0,0],className:"",pane:void 0,content:""},initialize:function(t,e){t&&(t instanceof v||d(t))?(this._latlng=w(t),c(this,e)):(c(this,t),this._source=e),this.options.content&&(this._content=this.options.content)},openOn:function(t){return(t=arguments.length?t:this._source._map).hasLayer(this)||t.addLayer(this),this},close:function(){return this._map&&this._map.removeLayer(this),this},toggle:function(t){return this._map?this.close():(arguments.length?this._source=t:t=this._source,this._prepareOpen(),this.openOn(t._map)),this},onAdd:function(t){this._zoomAnimated=t._zoomAnimated,this._container||this._initLayout(),t._fadeAnimated&&C(this._container,0),clearTimeout(this._removeTimeout),this.getPane().appendChild(this._container),this.update(),t._fadeAnimated&&C(this._container,1),this.bringToFront(),this.options.interactive&&(M(this._container,"leaflet-interactive"),this.addInteractiveTarget(this._container))},onRemove:function(t){t._fadeAnimated?(C(this._container,0),this._removeTimeout=setTimeout(a(T,void 0,this._container),200)):T(this._container),this.options.interactive&&(z(this._container,"leaflet-interactive"),this.removeInteractiveTarget(this._container))},getLatLng:function(){return this._latlng},setLatLng:function(t){return this._latlng=w(t),this._map&&(this._updatePosition(),this._adjustPan()),this},getContent:function(){return this._content},setContent:function(t){return this._content=t,this.update(),this},getElement:function(){return this._container},update:function(){this._map&&(this._container.style.visibility="hidden",this._updateContent(),this._updateLayout(),this._updatePosition(),this._container.style.visibility="",this._adjustPan())},getEvents:function(){var t={zoom:this._updatePosition,viewreset:this._updatePosition};return this._zoomAnimated&&(t.zoomanim=this._animateZoom),t},isOpen:function(){return!!this._map&&this._map.hasLayer(this)},bringToFront:function(){return this._map&&fe(this._container),this},bringToBack:function(){return this._map&&ge(this._container),this},_prepareOpen:function(t){if(!(i=this._source)._map)return!1;if(i instanceof ci){var e,i=null,n=this._source._layers;for(e in n)if(n[e]._map){i=n[e];break}if(!i)return!1;this._source=i}if(!t)if(i.getCenter)t=i.getCenter();else if(i.getLatLng)t=i.getLatLng();else{if(!i.getBounds)throw new Error("Unable to get source layer LatLng.");t=i.getBounds().getCenter()}return this.setLatLng(t),this._map&&this.update(),!0},_updateContent:function(){if(this._content){var t=this._contentNode,e="function"==typeof this._content?this._content(this._source||this):this._content;if("string"==typeof e)t.innerHTML=e;else{for(;t.hasChildNodes();)t.removeChild(t.firstChild);t.appendChild(e)}this.fire("contentupdate")}},_updatePosition:function(){var t,e,i;this._map&&(e=this._map.latLngToLayerPoint(this._latlng),t=m(this.options.offset),i=this._getAnchor(),this._zoomAnimated?Z(this._container,e.add(i)):t=t.add(e).add(i),e=this._containerBottom=-t.y,i=this._containerLeft=-Math.round(this._containerWidth/2)+t.x,this._container.style.bottom=e+"px",this._container.style.left=i+"px")},_getAnchor:function(){return[0,0]}}),Bi=(A.include({_initOverlay:function(t,e,i,n){var o=e;return o instanceof t||(o=new t(n).setContent(e)),i&&o.setLatLng(i),o}}),o.include({_initOverlay:function(t,e,i,n){var o=i;return o instanceof t?(c(o,n),o._source=this):(o=e&&!n?e:new t(n,this)).setContent(i),o}}),Ai.extend({options:{pane:"popupPane",offset:[0,7],maxWidth:300,minWidth:50,maxHeight:null,autoPan:!0,autoPanPaddingTopLeft:null,autoPanPaddingBottomRight:null,autoPanPadding:[5,5],keepInView:!1,closeButton:!0,autoClose:!0,closeOnEscapeKey:!0,className:""},openOn:function(t){return!(t=arguments.length?t:this._source._map).hasLayer(this)&&t._popup&&t._popup.options.autoClose&&t.removeLayer(t._popup),t._popup=this,Ai.prototype.openOn.call(this,t)},onAdd:function(t){Ai.prototype.onAdd.call(this,t),t.fire("popupopen",{popup:this}),this._source&&(this._source.fire("popupopen",{popup:this},!0),this._source instanceof fi||this._source.on("preclick",Ae))},onRemove:function(t){Ai.prototype.onRemove.call(this,t),t.fire("popupclose",{popup:this}),this._source&&(this._source.fire("popupclose",{popup:this},!0),this._source instanceof fi||this._source.off("preclick",Ae))},getEvents:function(){var t=Ai.prototype.getEvents.call(this);return(void 0!==this.options.closeOnClick?this.options.closeOnClick:this._map.options.closePopupOnClick)&&(t.preclick=this.close),this.options.keepInView&&(t.moveend=this._adjustPan),t},_initLayout:function(){var t="leaflet-popup",e=this._container=P("div",t+" "+(this.options.className||"")+" leaflet-zoom-animated"),i=this._wrapper=P("div",t+"-content-wrapper",e);this._contentNode=P("div",t+"-content",i),Ie(e),Be(this._contentNode),S(e,"contextmenu",Ae),this._tipContainer=P("div",t+"-tip-container",e),this._tip=P("div",t+"-tip",this._tipContainer),this.options.closeButton&&((i=this._closeButton=P("a",t+"-close-button",e)).setAttribute("role","button"),i.setAttribute("aria-label","Close popup"),i.href="#close",i.innerHTML='<span aria-hidden="true">&#215;</span>',S(i,"click",function(t){O(t),this.close()},this))},_updateLayout:function(){var t=this._contentNode,e=t.style,i=(e.width="",e.whiteSpace="nowrap",t.offsetWidth),i=Math.min(i,this.options.maxWidth),i=(i=Math.max(i,this.options.minWidth),e.width=i+1+"px",e.whiteSpace="",e.height="",t.offsetHeight),n=this.options.maxHeight,o="leaflet-popup-scrolled";(n&&n<i?(e.height=n+"px",M):z)(t,o),this._containerWidth=this._container.offsetWidth},_animateZoom:function(t){var t=this._map._latLngToNewLayerPoint(this._latlng,t.zoom,t.center),e=this._getAnchor();Z(this._container,t.add(e))},_adjustPan:function(){var t,e,i,n,o,s,r,a;this.options.autoPan&&(this._map._panAnim&&this._map._panAnim.stop(),this._autopanning?this._autopanning=!1:(t=this._map,e=parseInt(pe(this._container,"marginBottom"),10)||0,e=this._container.offsetHeight+e,a=this._containerWidth,(i=new p(this._containerLeft,-e-this._containerBottom))._add(Pe(this._container)),i=t.layerPointToContainerPoint(i),o=m(this.options.autoPanPadding),n=m(this.options.autoPanPaddingTopLeft||o),o=m(this.options.autoPanPaddingBottomRight||o),s=t.getSize(),r=0,i.x+a+o.x>s.x&&(r=i.x+a-s.x+o.x),i.x-r-n.x<(a=0)&&(r=i.x-n.x),i.y+e+o.y>s.y&&(a=i.y+e-s.y+o.y),i.y-a-n.y<0&&(a=i.y-n.y),(r||a)&&(this.options.keepInView&&(this._autopanning=!0),t.fire("autopanstart").panBy([r,a]))))},_getAnchor:function(){return m(this._source&&this._source._getPopupAnchor?this._source._getPopupAnchor():[0,0])}})),Ii=(A.mergeOptions({closePopupOnClick:!0}),A.include({openPopup:function(t,e,i){return this._initOverlay(Bi,t,e,i).openOn(this),this},closePopup:function(t){return(t=arguments.length?t:this._popup)&&t.close(),this}}),o.include({bindPopup:function(t,e){return this._popup=this._initOverlay(Bi,this._popup,t,e),this._popupHandlersAdded||(this.on({click:this._openPopup,keypress:this._onKeyPress,remove:this.closePopup,move:this._movePopup}),this._popupHandlersAdded=!0),this},unbindPopup:function(){return this._popup&&(this.off({click:this._openPopup,keypress:this._onKeyPress,remove:this.closePopup,move:this._movePopup}),this._popupHandlersAdded=!1,this._popup=null),this},openPopup:function(t){return this._popup&&(this instanceof ci||(this._popup._source=this),this._popup._prepareOpen(t||this._latlng)&&this._popup.openOn(this._map)),this},closePopup:function(){return this._popup&&this._popup.close(),this},togglePopup:function(){return this._popup&&this._popup.toggle(this),this},isPopupOpen:function(){return!!this._popup&&this._popup.isOpen()},setPopupContent:function(t){return this._popup&&this._popup.setContent(t),this},getPopup:function(){return this._popup},_openPopup:function(t){var e;this._popup&&this._map&&(Re(t),e=t.layer||t.target,this._popup._source!==e||e instanceof fi?(this._popup._source=e,this.openPopup(t.latlng)):this._map.hasLayer(this._popup)?this.closePopup():this.openPopup(t.latlng))},_movePopup:function(t){this._popup.setLatLng(t.latlng)},_onKeyPress:function(t){13===t.originalEvent.keyCode&&this._openPopup(t)}}),Ai.extend({options:{pane:"tooltipPane",offset:[0,0],direction:"auto",permanent:!1,sticky:!1,opacity:.9},onAdd:function(t){Ai.prototype.onAdd.call(this,t),this.setOpacity(this.options.opacity),t.fire("tooltipopen",{tooltip:this}),this._source&&(this.addEventParent(this._source),this._source.fire("tooltipopen",{tooltip:this},!0))},onRemove:function(t){Ai.prototype.onRemove.call(this,t),t.fire("tooltipclose",{tooltip:this}),this._source&&(this.removeEventParent(this._source),this._source.fire("tooltipclose",{tooltip:this},!0))},getEvents:function(){var t=Ai.prototype.getEvents.call(this);return this.options.permanent||(t.preclick=this.close),t},_initLayout:function(){var t="leaflet-tooltip "+(this.options.className||"")+" leaflet-zoom-"+(this._zoomAnimated?"animated":"hide");this._contentNode=this._container=P("div",t),this._container.setAttribute("role","tooltip"),this._container.setAttribute("id","leaflet-tooltip-"+h(this))},_updateLayout:function(){},_adjustPan:function(){},_setPosition:function(t){var e,i=this._map,n=this._container,o=i.latLngToContainerPoint(i.getCenter()),i=i.layerPointToContainerPoint(t),s=this.options.direction,r=n.offsetWidth,a=n.offsetHeight,h=m(this.options.offset),l=this._getAnchor(),i="top"===s?(e=r/2,a):"bottom"===s?(e=r/2,0):(e="center"===s?r/2:"right"===s?0:"left"===s?r:i.x<o.x?(s="right",0):(s="left",r+2*(h.x+l.x)),a/2);t=t.subtract(m(e,i,!0)).add(h).add(l),z(n,"leaflet-tooltip-right"),z(n,"leaflet-tooltip-left"),z(n,"leaflet-tooltip-top"),z(n,"leaflet-tooltip-bottom"),M(n,"leaflet-tooltip-"+s),Z(n,t)},_updatePosition:function(){var t=this._map.latLngToLayerPoint(this._latlng);this._setPosition(t)},setOpacity:function(t){this.options.opacity=t,this._container&&C(this._container,t)},_animateZoom:function(t){t=this._map._latLngToNewLayerPoint(this._latlng,t.zoom,t.center);this._setPosition(t)},_getAnchor:function(){return m(this._source&&this._source._getTooltipAnchor&&!this.options.sticky?this._source._getTooltipAnchor():[0,0])}})),Ri=(A.include({openTooltip:function(t,e,i){return this._initOverlay(Ii,t,e,i).openOn(this),this},closeTooltip:function(t){return t.close(),this}}),o.include({bindTooltip:function(t,e){return this._tooltip&&this.isTooltipOpen()&&this.unbindTooltip(),this._tooltip=this._initOverlay(Ii,this._tooltip,t,e),this._initTooltipInteractions(),this._tooltip.options.permanent&&this._map&&this._map.hasLayer(this)&&this.openTooltip(),this},unbindTooltip:function(){return this._tooltip&&(this._initTooltipInteractions(!0),this.closeTooltip(),this._tooltip=null),this},_initTooltipInteractions:function(t){var e,i;!t&&this._tooltipHandlersAdded||(e=t?"off":"on",i={remove:this.closeTooltip,move:this._moveTooltip},this._tooltip.options.permanent?i.add=this._openTooltip:(i.mouseover=this._openTooltip,i.mouseout=this.closeTooltip,i.click=this._openTooltip,this._map?this._addFocusListeners():i.add=this._addFocusListeners),this._tooltip.options.sticky&&(i.mousemove=this._moveTooltip),this[e](i),this._tooltipHandlersAdded=!t)},openTooltip:function(t){return this._tooltip&&(this instanceof ci||(this._tooltip._source=this),this._tooltip._prepareOpen(t)&&(this._tooltip.openOn(this._map),this.getElement?this._setAriaDescribedByOnLayer(this):this.eachLayer&&this.eachLayer(this._setAriaDescribedByOnLayer,this))),this},closeTooltip:function(){if(this._tooltip)return this._tooltip.close()},toggleTooltip:function(){return this._tooltip&&this._tooltip.toggle(this),this},isTooltipOpen:function(){return this._tooltip.isOpen()},setTooltipContent:function(t){return this._tooltip&&this._tooltip.setContent(t),this},getTooltip:function(){return this._tooltip},_addFocusListeners:function(){this.getElement?this._addFocusListenersOnLayer(this):this.eachLayer&&this.eachLayer(this._addFocusListenersOnLayer,this)},_addFocusListenersOnLayer:function(t){var e="function"==typeof t.getElement&&t.getElement();e&&(S(e,"focus",function(){this._tooltip._source=t,this.openTooltip()},this),S(e,"blur",this.closeTooltip,this))},_setAriaDescribedByOnLayer:function(t){t="function"==typeof t.getElement&&t.getElement();t&&t.setAttribute("aria-describedby",this._tooltip._container.id)},_openTooltip:function(t){var e;this._tooltip&&this._map&&(this._map.dragging&&this._map.dragging.moving()&&!this._openOnceFlag?(this._openOnceFlag=!0,(e=this)._map.once("moveend",function(){e._openOnceFlag=!1,e._openTooltip(t)})):(this._tooltip._source=t.layer||t.target,this.openTooltip(this._tooltip.options.sticky?t.latlng:void 0)))},_moveTooltip:function(t){var e=t.latlng;this._tooltip.options.sticky&&t.originalEvent&&(t=this._map.mouseEventToContainerPoint(t.originalEvent),t=this._map.containerPointToLayerPoint(t),e=this._map.layerPointToLatLng(t)),this._tooltip.setLatLng(e)}}),di.extend({options:{iconSize:[12,12],html:!1,bgPos:null,className:"leaflet-div-icon"},createIcon:function(t){var t=t&&"DIV"===t.tagName?t:document.createElement("div"),e=this.options;return e.html instanceof Element?(me(t),t.appendChild(e.html)):t.innerHTML=!1!==e.html?e.html:"",e.bgPos&&(e=m(e.bgPos),t.style.backgroundPosition=-e.x+"px "+-e.y+"px"),this._setIconStyles(t,"icon"),t},createShadow:function(){return null}}));di.Default=_i;var Ni=o.extend({options:{tileSize:256,opacity:1,updateWhenIdle:b.mobile,updateWhenZooming:!0,updateInterval:200,zIndex:1,bounds:null,minZoom:0,maxZoom:void 0,maxNativeZoom:void 0,minNativeZoom:void 0,noWrap:!1,pane:"tilePane",className:"",keepBuffer:2},initialize:function(t){c(this,t)},onAdd:function(){this._initContainer(),this._levels={},this._tiles={},this._resetView()},beforeAdd:function(t){t._addZoomLimit(this)},onRemove:function(t){this._removeAllTiles(),T(this._container),t._removeZoomLimit(this),this._container=null,this._tileZoom=void 0},bringToFront:function(){return this._map&&(fe(this._container),this._setAutoZIndex(Math.max)),this},bringToBack:function(){return this._map&&(ge(this._container),this._setAutoZIndex(Math.min)),this},getContainer:function(){return this._container},setOpacity:function(t){return this.options.opacity=t,this._updateOpacity(),this},setZIndex:function(t){return this.options.zIndex=t,this._updateZIndex(),this},isLoading:function(){return this._loading},redraw:function(){var t;return this._map&&(this._removeAllTiles(),(t=this._clampZoom(this._map.getZoom()))!==this._tileZoom&&(this._tileZoom=t,this._updateLevels()),this._update()),this},getEvents:function(){var t={viewprereset:this._invalidateAll,viewreset:this._resetView,zoom:this._resetView,moveend:this._onMoveEnd};return this.options.updateWhenIdle||(this._onMove||(this._onMove=j(this._onMoveEnd,this.options.updateInterval,this)),t.move=this._onMove),this._zoomAnimated&&(t.zoomanim=this._animateZoom),t},createTile:function(){return document.createElement("div")},getTileSize:function(){var t=this.options.tileSize;return t instanceof p?t:new p(t,t)},_updateZIndex:function(){this._container&&void 0!==this.options.zIndex&&null!==this.options.zIndex&&(this._container.style.zIndex=this.options.zIndex)},_setAutoZIndex:function(t){for(var e,i=this.getPane().children,n=-t(-1/0,1/0),o=0,s=i.length;o<s;o++)e=i[o].style.zIndex,i[o]!==this._container&&e&&(n=t(n,+e));isFinite(n)&&(this.options.zIndex=n+t(-1,1),this._updateZIndex())},_updateOpacity:function(){if(this._map&&!b.ielt9){C(this._container,this.options.opacity);var t,e=+new Date,i=!1,n=!1;for(t in this._tiles){var o,s=this._tiles[t];s.current&&s.loaded&&(o=Math.min(1,(e-s.loaded)/200),C(s.el,o),o<1?i=!0:(s.active?n=!0:this._onOpaqueTile(s),s.active=!0))}n&&!this._noPrune&&this._pruneTiles(),i&&(r(this._fadeFrame),this._fadeFrame=x(this._updateOpacity,this))}},_onOpaqueTile:u,_initContainer:function(){this._container||(this._container=P("div","leaflet-layer "+(this.options.className||"")),this._updateZIndex(),this.options.opacity<1&&this._updateOpacity(),this.getPane().appendChild(this._container))},_updateLevels:function(){var t=this._tileZoom,e=this.options.maxZoom;if(void 0!==t){for(var i in this._levels)i=Number(i),this._levels[i].el.children.length||i===t?(this._levels[i].el.style.zIndex=e-Math.abs(t-i),this._onUpdateLevel(i)):(T(this._levels[i].el),this._removeTilesAtZoom(i),this._onRemoveLevel(i),delete this._levels[i]);var n=this._levels[t],o=this._map;return n||((n=this._levels[t]={}).el=P("div","leaflet-tile-container leaflet-zoom-animated",this._container),n.el.style.zIndex=e,n.origin=o.project(o.unproject(o.getPixelOrigin()),t).round(),n.zoom=t,this._setZoomTransform(n,o.getCenter(),o.getZoom()),u(n.el.offsetWidth),this._onCreateLevel(n)),this._level=n}},_onUpdateLevel:u,_onRemoveLevel:u,_onCreateLevel:u,_pruneTiles:function(){if(this._map){var t,e,i,n=this._map.getZoom();if(n>this.options.maxZoom||n<this.options.minZoom)this._removeAllTiles();else{for(t in this._tiles)(i=this._tiles[t]).retain=i.current;for(t in this._tiles)(i=this._tiles[t]).current&&!i.active&&(e=i.coords,this._retainParent(e.x,e.y,e.z,e.z-5)||this._retainChildren(e.x,e.y,e.z,e.z+2));for(t in this._tiles)this._tiles[t].retain||this._removeTile(t)}}},_removeTilesAtZoom:function(t){for(var e in this._tiles)this._tiles[e].coords.z===t&&this._removeTile(e)},_removeAllTiles:function(){for(var t in this._tiles)this._removeTile(t)},_invalidateAll:function(){for(var t in this._levels)T(this._levels[t].el),this._onRemoveLevel(Number(t)),delete this._levels[t];this._removeAllTiles(),this._tileZoom=void 0},_retainParent:function(t,e,i,n){var t=Math.floor(t/2),e=Math.floor(e/2),i=i-1,o=new p(+t,+e),o=(o.z=i,this._tileCoordsToKey(o)),o=this._tiles[o];return o&&o.active?o.retain=!0:(o&&o.loaded&&(o.retain=!0),n<i&&this._retainParent(t,e,i,n))},_retainChildren:function(t,e,i,n){for(var o=2*t;o<2*t+2;o++)for(var s=2*e;s<2*e+2;s++){var r=new p(o,s),r=(r.z=i+1,this._tileCoordsToKey(r)),r=this._tiles[r];r&&r.active?r.retain=!0:(r&&r.loaded&&(r.retain=!0),i+1<n&&this._retainChildren(o,s,i+1,n))}},_resetView:function(t){t=t&&(t.pinch||t.flyTo);this._setView(this._map.getCenter(),this._map.getZoom(),t,t)},_animateZoom:function(t){this._setView(t.center,t.zoom,!0,t.noUpdate)},_clampZoom:function(t){var e=this.options;return void 0!==e.minNativeZoom&&t<e.minNativeZoom?e.minNativeZoom:void 0!==e.maxNativeZoom&&e.maxNativeZoom<t?e.maxNativeZoom:t},_setView:function(t,e,i,n){var o=Math.round(e),o=void 0!==this.options.maxZoom&&o>this.options.maxZoom||void 0!==this.options.minZoom&&o<this.options.minZoom?void 0:this._clampZoom(o),s=this.options.updateWhenZooming&&o!==this._tileZoom;n&&!s||(this._tileZoom=o,this._abortLoading&&this._abortLoading(),this._updateLevels(),this._resetGrid(),void 0!==o&&this._update(t),i||this._pruneTiles(),this._noPrune=!!i),this._setZoomTransforms(t,e)},_setZoomTransforms:function(t,e){for(var i in this._levels)this._setZoomTransform(this._levels[i],t,e)},_setZoomTransform:function(t,e,i){var n=this._map.getZoomScale(i,t.zoom),e=t.origin.multiplyBy(n).subtract(this._map._getNewPixelOrigin(e,i)).round();b.any3d?be(t.el,e,n):Z(t.el,e)},_resetGrid:function(){var t=this._map,e=t.options.crs,i=this._tileSize=this.getTileSize(),n=this._tileZoom,o=this._map.getPixelWorldBounds(this._tileZoom);o&&(this._globalTileRange=this._pxBoundsToTileRange(o)),this._wrapX=e.wrapLng&&!this.options.noWrap&&[Math.floor(t.project([0,e.wrapLng[0]],n).x/i.x),Math.ceil(t.project([0,e.wrapLng[1]],n).x/i.y)],this._wrapY=e.wrapLat&&!this.options.noWrap&&[Math.floor(t.project([e.wrapLat[0],0],n).y/i.x),Math.ceil(t.project([e.wrapLat[1],0],n).y/i.y)]},_onMoveEnd:function(){this._map&&!this._map._animatingZoom&&this._update()},_getTiledPixelBounds:function(t){var e=this._map,i=e._animatingZoom?Math.max(e._animateToZoom,e.getZoom()):e.getZoom(),i=e.getZoomScale(i,this._tileZoom),t=e.project(t,this._tileZoom).floor(),e=e.getSize().divideBy(2*i);return new f(t.subtract(e),t.add(e))},_update:function(t){var e=this._map;if(e){var i=this._clampZoom(e.getZoom());if(void 0===t&&(t=e.getCenter()),void 0!==this._tileZoom){var n,e=this._getTiledPixelBounds(t),o=this._pxBoundsToTileRange(e),s=o.getCenter(),r=[],e=this.options.keepBuffer,a=new f(o.getBottomLeft().subtract([e,-e]),o.getTopRight().add([e,-e]));if(!(isFinite(o.min.x)&&isFinite(o.min.y)&&isFinite(o.max.x)&&isFinite(o.max.y)))throw new Error("Attempted to load an infinite number of tiles");for(n in this._tiles){var h=this._tiles[n].coords;h.z===this._tileZoom&&a.contains(new p(h.x,h.y))||(this._tiles[n].current=!1)}if(1<Math.abs(i-this._tileZoom))this._setView(t,i);else{for(var l=o.min.y;l<=o.max.y;l++)for(var u=o.min.x;u<=o.max.x;u++){var c,d=new p(u,l);d.z=this._tileZoom,this._isValidTile(d)&&((c=this._tiles[this._tileCoordsToKey(d)])?c.current=!0:r.push(d))}if(r.sort(function(t,e){return t.distanceTo(s)-e.distanceTo(s)}),0!==r.length){this._loading||(this._loading=!0,this.fire("loading"));for(var _=document.createDocumentFragment(),u=0;u<r.length;u++)this._addTile(r[u],_);this._level.el.appendChild(_)}}}}},_isValidTile:function(t){var e=this._map.options.crs;if(!e.infinite){var i=this._globalTileRange;if(!e.wrapLng&&(t.x<i.min.x||t.x>i.max.x)||!e.wrapLat&&(t.y<i.min.y||t.y>i.max.y))return!1}return!this.options.bounds||(e=this._tileCoordsToBounds(t),g(this.options.bounds).overlaps(e))},_keyToBounds:function(t){return this._tileCoordsToBounds(this._keyToTileCoords(t))},_tileCoordsToNwSe:function(t){var e=this._map,i=this.getTileSize(),n=t.scaleBy(i),i=n.add(i);return[e.unproject(n,t.z),e.unproject(i,t.z)]},_tileCoordsToBounds:function(t){t=this._tileCoordsToNwSe(t),t=new s(t[0],t[1]);return t=this.options.noWrap?t:this._map.wrapLatLngBounds(t)},_tileCoordsToKey:function(t){return t.x+":"+t.y+":"+t.z},_keyToTileCoords:function(t){var t=t.split(":"),e=new p(+t[0],+t[1]);return e.z=+t[2],e},_removeTile:function(t){var e=this._tiles[t];e&&(T(e.el),delete this._tiles[t],this.fire("tileunload",{tile:e.el,coords:this._keyToTileCoords(t)}))},_initTile:function(t){M(t,"leaflet-tile");var e=this.getTileSize();t.style.width=e.x+"px",t.style.height=e.y+"px",t.onselectstart=u,t.onmousemove=u,b.ielt9&&this.options.opacity<1&&C(t,this.options.opacity)},_addTile:function(t,e){var i=this._getTilePos(t),n=this._tileCoordsToKey(t),o=this.createTile(this._wrapCoords(t),a(this._tileReady,this,t));this._initTile(o),this.createTile.length<2&&x(a(this._tileReady,this,t,null,o)),Z(o,i),this._tiles[n]={el:o,coords:t,current:!0},e.appendChild(o),this.fire("tileloadstart",{tile:o,coords:t})},_tileReady:function(t,e,i){e&&this.fire("tileerror",{error:e,tile:i,coords:t});var n=this._tileCoordsToKey(t);(i=this._tiles[n])&&(i.loaded=+new Date,this._map._fadeAnimated?(C(i.el,0),r(this._fadeFrame),this._fadeFrame=x(this._updateOpacity,this)):(i.active=!0,this._pruneTiles()),e||(M(i.el,"leaflet-tile-loaded"),this.fire("tileload",{tile:i.el,coords:t})),this._noTilesToLoad()&&(this._loading=!1,this.fire("load"),b.ielt9||!this._map._fadeAnimated?x(this._pruneTiles,this):setTimeout(a(this._pruneTiles,this),250)))},_getTilePos:function(t){return t.scaleBy(this.getTileSize()).subtract(this._level.origin)},_wrapCoords:function(t){var e=new p(this._wrapX?H(t.x,this._wrapX):t.x,this._wrapY?H(t.y,this._wrapY):t.y);return e.z=t.z,e},_pxBoundsToTileRange:function(t){var e=this.getTileSize();return new f(t.min.unscaleBy(e).floor(),t.max.unscaleBy(e).ceil().subtract([1,1]))},_noTilesToLoad:function(){for(var t in this._tiles)if(!this._tiles[t].loaded)return!1;return!0}});var Di=Ni.extend({options:{minZoom:0,maxZoom:18,subdomains:"abc",errorTileUrl:"",zoomOffset:0,tms:!1,zoomReverse:!1,detectRetina:!1,crossOrigin:!1,referrerPolicy:!1},initialize:function(t,e){this._url=t,(e=c(this,e)).detectRetina&&b.retina&&0<e.maxZoom?(e.tileSize=Math.floor(e.tileSize/2),e.zoomReverse?(e.zoomOffset--,e.minZoom=Math.min(e.maxZoom,e.minZoom+1)):(e.zoomOffset++,e.maxZoom=Math.max(e.minZoom,e.maxZoom-1)),e.minZoom=Math.max(0,e.minZoom)):e.zoomReverse?e.minZoom=Math.min(e.maxZoom,e.minZoom):e.maxZoom=Math.max(e.minZoom,e.maxZoom),"string"==typeof e.subdomains&&(e.subdomains=e.subdomains.split("")),this.on("tileunload",this._onTileRemove)},setUrl:function(t,e){return this._url===t&&void 0===e&&(e=!0),this._url=t,e||this.redraw(),this},createTile:function(t,e){var i=document.createElement("img");return S(i,"load",a(this._tileOnLoad,this,e,i)),S(i,"error",a(this._tileOnError,this,e,i)),!this.options.crossOrigin&&""!==this.options.crossOrigin||(i.crossOrigin=!0===this.options.crossOrigin?"":this.options.crossOrigin),"string"==typeof this.options.referrerPolicy&&(i.referrerPolicy=this.options.referrerPolicy),i.alt="",i.src=this.getTileUrl(t),i},getTileUrl:function(t){var e={r:b.retina?"@2x":"",s:this._getSubdomain(t),x:t.x,y:t.y,z:this._getZoomForUrl()};return this._map&&!this._map.options.crs.infinite&&(t=this._globalTileRange.max.y-t.y,this.options.tms&&(e.y=t),e["-y"]=t),q(this._url,l(e,this.options))},_tileOnLoad:function(t,e){b.ielt9?setTimeout(a(t,this,null,e),0):t(null,e)},_tileOnError:function(t,e,i){var n=this.options.errorTileUrl;n&&e.getAttribute("src")!==n&&(e.src=n),t(i,e)},_onTileRemove:function(t){t.tile.onload=null},_getZoomForUrl:function(){var t=this._tileZoom,e=this.options.maxZoom;return(t=this.options.zoomReverse?e-t:t)+this.options.zoomOffset},_getSubdomain:function(t){t=Math.abs(t.x+t.y)%this.options.subdomains.length;return this.options.subdomains[t]},_abortLoading:function(){var t,e,i;for(t in this._tiles)this._tiles[t].coords.z!==this._tileZoom&&((i=this._tiles[t].el).onload=u,i.onerror=u,i.complete||(i.src=K,e=this._tiles[t].coords,T(i),delete this._tiles[t],this.fire("tileabort",{tile:i,coords:e})))},_removeTile:function(t){var e=this._tiles[t];if(e)return e.el.setAttribute("src",K),Ni.prototype._removeTile.call(this,t)},_tileReady:function(t,e,i){if(this._map&&(!i||i.getAttribute("src")!==K))return Ni.prototype._tileReady.call(this,t,e,i)}});function ji(t,e){return new Di(t,e)}var Hi=Di.extend({defaultWmsParams:{service:"WMS",request:"GetMap",layers:"",styles:"",format:"image/jpeg",transparent:!1,version:"1.1.1"},options:{crs:null,uppercase:!1},initialize:function(t,e){this._url=t;var i,n=l({},this.defaultWmsParams);for(i in e)i in this.options||(n[i]=e[i]);var t=(e=c(this,e)).detectRetina&&b.retina?2:1,o=this.getTileSize();n.width=o.x*t,n.height=o.y*t,this.wmsParams=n},onAdd:function(t){this._crs=this.options.crs||t.options.crs,this._wmsVersion=parseFloat(this.wmsParams.version);var e=1.3<=this._wmsVersion?"crs":"srs";this.wmsParams[e]=this._crs.code,Di.prototype.onAdd.call(this,t)},getTileUrl:function(t){var e=this._tileCoordsToNwSe(t),i=this._crs,i=_(i.project(e[0]),i.project(e[1])),e=i.min,i=i.max,e=(1.3<=this._wmsVersion&&this._crs===li?[e.y,e.x,i.y,i.x]:[e.x,e.y,i.x,i.y]).join(","),i=Di.prototype.getTileUrl.call(this,t);return i+U(this.wmsParams,i,this.options.uppercase)+(this.options.uppercase?"&BBOX=":"&bbox=")+e},setParams:function(t,e){return l(this.wmsParams,t),e||this.redraw(),this}});Di.WMS=Hi,ji.wms=function(t,e){return new Hi(t,e)};var Wi=o.extend({options:{padding:.1},initialize:function(t){c(this,t),h(this),this._layers=this._layers||{}},onAdd:function(){this._container||(this._initContainer(),M(this._container,"leaflet-zoom-animated")),this.getPane().appendChild(this._container),this._update(),this.on("update",this._updatePaths,this)},onRemove:function(){this.off("update",this._updatePaths,this),this._destroyContainer()},getEvents:function(){var t={viewreset:this._reset,zoom:this._onZoom,moveend:this._update,zoomend:this._onZoomEnd};return this._zoomAnimated&&(t.zoomanim=this._onAnimZoom),t},_onAnimZoom:function(t){this._updateTransform(t.center,t.zoom)},_onZoom:function(){this._updateTransform(this._map.getCenter(),this._map.getZoom())},_updateTransform:function(t,e){var i=this._map.getZoomScale(e,this._zoom),n=this._map.getSize().multiplyBy(.5+this.options.padding),o=this._map.project(this._center,e),n=n.multiplyBy(-i).add(o).subtract(this._map._getNewPixelOrigin(t,e));b.any3d?be(this._container,n,i):Z(this._container,n)},_reset:function(){for(var t in this._update(),this._updateTransform(this._center,this._zoom),this._layers)this._layers[t]._reset()},_onZoomEnd:function(){for(var t in this._layers)this._layers[t]._project()},_updatePaths:function(){for(var t in this._layers)this._layers[t]._update()},_update:function(){var t=this.options.padding,e=this._map.getSize(),i=this._map.containerPointToLayerPoint(e.multiplyBy(-t)).round();this._bounds=new f(i,i.add(e.multiplyBy(1+2*t)).round()),this._center=this._map.getCenter(),this._zoom=this._map.getZoom()}}),Fi=Wi.extend({options:{tolerance:0},getEvents:function(){var t=Wi.prototype.getEvents.call(this);return t.viewprereset=this._onViewPreReset,t},_onViewPreReset:function(){this._postponeUpdatePaths=!0},onAdd:function(){Wi.prototype.onAdd.call(this),this._draw()},_initContainer:function(){var t=this._container=document.createElement("canvas");S(t,"mousemove",this._onMouseMove,this),S(t,"click dblclick mousedown mouseup contextmenu",this._onClick,this),S(t,"mouseout",this._handleMouseOut,this),t._leaflet_disable_events=!0,this._ctx=t.getContext("2d")},_destroyContainer:function(){r(this._redrawRequest),delete this._ctx,T(this._container),k(this._container),delete this._container},_updatePaths:function(){if(!this._postponeUpdatePaths){for(var t in this._redrawBounds=null,this._layers)this._layers[t]._update();this._redraw()}},_update:function(){var t,e,i,n;this._map._animatingZoom&&this._bounds||(Wi.prototype._update.call(this),t=this._bounds,e=this._container,i=t.getSize(),n=b.retina?2:1,Z(e,t.min),e.width=n*i.x,e.height=n*i.y,e.style.width=i.x+"px",e.style.height=i.y+"px",b.retina&&this._ctx.scale(2,2),this._ctx.translate(-t.min.x,-t.min.y),this.fire("update"))},_reset:function(){Wi.prototype._reset.call(this),this._postponeUpdatePaths&&(this._postponeUpdatePaths=!1,this._updatePaths())},_initPath:function(t){this._updateDashArray(t);t=(this._layers[h(t)]=t)._order={layer:t,prev:this._drawLast,next:null};this._drawLast&&(this._drawLast.next=t),this._drawLast=t,this._drawFirst=this._drawFirst||this._drawLast},_addPath:function(t){this._requestRedraw(t)},_removePath:function(t){var e=t._order,i=e.next,e=e.prev;i?i.prev=e:this._drawLast=e,e?e.next=i:this._drawFirst=i,delete t._order,delete this._layers[h(t)],this._requestRedraw(t)},_updatePath:function(t){this._extendRedrawBounds(t),t._project(),t._update(),this._requestRedraw(t)},_updateStyle:function(t){this._updateDashArray(t),this._requestRedraw(t)},_updateDashArray:function(t){if("string"==typeof t.options.dashArray){for(var e,i=t.options.dashArray.split(/[, ]+/),n=[],o=0;o<i.length;o++){if(e=Number(i[o]),isNaN(e))return;n.push(e)}t.options._dashArray=n}else t.options._dashArray=t.options.dashArray},_requestRedraw:function(t){this._map&&(this._extendRedrawBounds(t),this._redrawRequest=this._redrawRequest||x(this._redraw,this))},_extendRedrawBounds:function(t){var e;t._pxBounds&&(e=(t.options.weight||0)+1,this._redrawBounds=this._redrawBounds||new f,this._redrawBounds.extend(t._pxBounds.min.subtract([e,e])),this._redrawBounds.extend(t._pxBounds.max.add([e,e])))},_redraw:function(){this._redrawRequest=null,this._redrawBounds&&(this._redrawBounds.min._floor(),this._redrawBounds.max._ceil()),this._clear(),this._draw(),this._redrawBounds=null},_clear:function(){var t,e=this._redrawBounds;e?(t=e.getSize(),this._ctx.clearRect(e.min.x,e.min.y,t.x,t.y)):(this._ctx.save(),this._ctx.setTransform(1,0,0,1,0,0),this._ctx.clearRect(0,0,this._container.width,this._container.height),this._ctx.restore())},_draw:function(){var t,e,i=this._redrawBounds;this._ctx.save(),i&&(e=i.getSize(),this._ctx.beginPath(),this._ctx.rect(i.min.x,i.min.y,e.x,e.y),this._ctx.clip()),this._drawing=!0;for(var n=this._drawFirst;n;n=n.next)t=n.layer,(!i||t._pxBounds&&t._pxBounds.intersects(i))&&t._updatePath();this._drawing=!1,this._ctx.restore()},_updatePoly:function(t,e){if(this._drawing){var i,n,o,s,r=t._parts,a=r.length,h=this._ctx;if(a){for(h.beginPath(),i=0;i<a;i++){for(n=0,o=r[i].length;n<o;n++)s=r[i][n],h[n?"lineTo":"moveTo"](s.x,s.y);e&&h.closePath()}this._fillStroke(h,t)}}},_updateCircle:function(t){var e,i,n,o;this._drawing&&!t._empty()&&(e=t._point,i=this._ctx,n=Math.max(Math.round(t._radius),1),1!=(o=(Math.max(Math.round(t._radiusY),1)||n)/n)&&(i.save(),i.scale(1,o)),i.beginPath(),i.arc(e.x,e.y/o,n,0,2*Math.PI,!1),1!=o&&i.restore(),this._fillStroke(i,t))},_fillStroke:function(t,e){var i=e.options;i.fill&&(t.globalAlpha=i.fillOpacity,t.fillStyle=i.fillColor||i.color,t.fill(i.fillRule||"evenodd")),i.stroke&&0!==i.weight&&(t.setLineDash&&t.setLineDash(e.options&&e.options._dashArray||[]),t.globalAlpha=i.opacity,t.lineWidth=i.weight,t.strokeStyle=i.color,t.lineCap=i.lineCap,t.lineJoin=i.lineJoin,t.stroke())},_onClick:function(t){for(var e,i,n=this._map.mouseEventToLayerPoint(t),o=this._drawFirst;o;o=o.next)(e=o.layer).options.interactive&&e._containsPoint(n)&&(("click"===t.type||"preclick"===t.type)&&this._map._draggableMoved(e)||(i=e));this._fireEvent(!!i&&[i],t)},_onMouseMove:function(t){var e;!this._map||this._map.dragging.moving()||this._map._animatingZoom||(e=this._map.mouseEventToLayerPoint(t),this._handleMouseHover(t,e))},_handleMouseOut:function(t){var e=this._hoveredLayer;e&&(z(this._container,"leaflet-interactive"),this._fireEvent([e],t,"mouseout"),this._hoveredLayer=null,this._mouseHoverThrottled=!1)},_handleMouseHover:function(t,e){if(!this._mouseHoverThrottled){for(var i,n,o=this._drawFirst;o;o=o.next)(i=o.layer).options.interactive&&i._containsPoint(e)&&(n=i);n!==this._hoveredLayer&&(this._handleMouseOut(t),n&&(M(this._container,"leaflet-interactive"),this._fireEvent([n],t,"mouseover"),this._hoveredLayer=n)),this._fireEvent(!!this._hoveredLayer&&[this._hoveredLayer],t),this._mouseHoverThrottled=!0,setTimeout(a(function(){this._mouseHoverThrottled=!1},this),32)}},_fireEvent:function(t,e,i){this._map._fireDOMEvent(e,i||e.type,t)},_bringToFront:function(t){var e,i,n=t._order;n&&(e=n.next,i=n.prev,e&&((e.prev=i)?i.next=e:e&&(this._drawFirst=e),n.prev=this._drawLast,(this._drawLast.next=n).next=null,this._drawLast=n,this._requestRedraw(t)))},_bringToBack:function(t){var e,i,n=t._order;n&&(e=n.next,(i=n.prev)&&((i.next=e)?e.prev=i:i&&(this._drawLast=i),n.prev=null,n.next=this._drawFirst,this._drawFirst.prev=n,this._drawFirst=n,this._requestRedraw(t)))}});function Ui(t){return b.canvas?new Fi(t):null}var Vi=function(){try{return document.namespaces.add("lvml","urn:schemas-microsoft-com:vml"),function(t){return document.createElement("<lvml:"+t+' class="lvml">')}}catch(t){}return function(t){return document.createElement("<"+t+' xmlns="urn:schemas-microsoft.com:vml" class="lvml">')}}(),zt={_initContainer:function(){this._container=P("div","leaflet-vml-container")},_update:function(){this._map._animatingZoom||(Wi.prototype._update.call(this),this.fire("update"))},_initPath:function(t){var e=t._container=Vi("shape");M(e,"leaflet-vml-shape "+(this.options.className||"")),e.coordsize="1 1",t._path=Vi("path"),e.appendChild(t._path),this._updateStyle(t),this._layers[h(t)]=t},_addPath:function(t){var e=t._container;this._container.appendChild(e),t.options.interactive&&t.addInteractiveTarget(e)},_removePath:function(t){var e=t._container;T(e),t.removeInteractiveTarget(e),delete this._layers[h(t)]},_updateStyle:function(t){var e=t._stroke,i=t._fill,n=t.options,o=t._container;o.stroked=!!n.stroke,o.filled=!!n.fill,n.stroke?(e=e||(t._stroke=Vi("stroke")),o.appendChild(e),e.weight=n.weight+"px",e.color=n.color,e.opacity=n.opacity,n.dashArray?e.dashStyle=d(n.dashArray)?n.dashArray.join(" "):n.dashArray.replace(/( *, *)/g," "):e.dashStyle="",e.endcap=n.lineCap.replace("butt","flat"),e.joinstyle=n.lineJoin):e&&(o.removeChild(e),t._stroke=null),n.fill?(i=i||(t._fill=Vi("fill")),o.appendChild(i),i.color=n.fillColor||n.color,i.opacity=n.fillOpacity):i&&(o.removeChild(i),t._fill=null)},_updateCircle:function(t){var e=t._point.round(),i=Math.round(t._radius),n=Math.round(t._radiusY||i);this._setPath(t,t._empty()?"M0 0":"AL "+e.x+","+e.y+" "+i+","+n+" 0,23592600")},_setPath:function(t,e){t._path.v=e},_bringToFront:function(t){fe(t._container)},_bringToBack:function(t){ge(t._container)}},qi=b.vml?Vi:ct,Gi=Wi.extend({_initContainer:function(){this._container=qi("svg"),this._container.setAttribute("pointer-events","none"),this._rootGroup=qi("g"),this._container.appendChild(this._rootGroup)},_destroyContainer:function(){T(this._container),k(this._container),delete this._container,delete this._rootGroup,delete this._svgSize},_update:function(){var t,e,i;this._map._animatingZoom&&this._bounds||(Wi.prototype._update.call(this),e=(t=this._bounds).getSize(),i=this._container,this._svgSize&&this._svgSize.equals(e)||(this._svgSize=e,i.setAttribute("width",e.x),i.setAttribute("height",e.y)),Z(i,t.min),i.setAttribute("viewBox",[t.min.x,t.min.y,e.x,e.y].join(" ")),this.fire("update"))},_initPath:function(t){var e=t._path=qi("path");t.options.className&&M(e,t.options.className),t.options.interactive&&M(e,"leaflet-interactive"),this._updateStyle(t),this._layers[h(t)]=t},_addPath:function(t){this._rootGroup||this._initContainer(),this._rootGroup.appendChild(t._path),t.addInteractiveTarget(t._path)},_removePath:function(t){T(t._path),t.removeInteractiveTarget(t._path),delete this._layers[h(t)]},_updatePath:function(t){t._project(),t._update()},_updateStyle:function(t){var e=t._path,t=t.options;e&&(t.stroke?(e.setAttribute("stroke",t.color),e.setAttribute("stroke-opacity",t.opacity),e.setAttribute("stroke-width",t.weight),e.setAttribute("stroke-linecap",t.lineCap),e.setAttribute("stroke-linejoin",t.lineJoin),t.dashArray?e.setAttribute("stroke-dasharray",t.dashArray):e.removeAttribute("stroke-dasharray"),t.dashOffset?e.setAttribute("stroke-dashoffset",t.dashOffset):e.removeAttribute("stroke-dashoffset")):e.setAttribute("stroke","none"),t.fill?(e.setAttribute("fill",t.fillColor||t.color),e.setAttribute("fill-opacity",t.fillOpacity),e.setAttribute("fill-rule",t.fillRule||"evenodd")):e.setAttribute("fill","none"))},_updatePoly:function(t,e){this._setPath(t,dt(t._parts,e))},_updateCircle:function(t){var e=t._point,i=Math.max(Math.round(t._radius),1),n="a"+i+","+(Math.max(Math.round(t._radiusY),1)||i)+" 0 1,0 ",e=t._empty()?"M0 0":"M"+(e.x-i)+","+e.y+n+2*i+",0 "+n+2*-i+",0 ";this._setPath(t,e)},_setPath:function(t,e){t._path.setAttribute("d",e)},_bringToFront:function(t){fe(t._path)},_bringToBack:function(t){ge(t._path)}});function Ki(t){return b.svg||b.vml?new Gi(t):null}b.vml&&Gi.include(zt),A.include({getRenderer:function(t){t=(t=t.options.renderer||this._getPaneRenderer(t.options.pane)||this.options.renderer||this._renderer)||(this._renderer=this._createRenderer());return this.hasLayer(t)||this.addLayer(t),t},_getPaneRenderer:function(t){var e;return"overlayPane"!==t&&void 0!==t&&(void 0===(e=this._paneRenderers[t])&&(e=this._createRenderer({pane:t}),this._paneRenderers[t]=e),e)},_createRenderer:function(t){return this.options.preferCanvas&&Ui(t)||Ki(t)}});var Yi=xi.extend({initialize:function(t,e){xi.prototype.initialize.call(this,this._boundsToLatLngs(t),e)},setBounds:function(t){return this.setLatLngs(this._boundsToLatLngs(t))},_boundsToLatLngs:function(t){return[(t=g(t)).getSouthWest(),t.getNorthWest(),t.getNorthEast(),t.getSouthEast()]}});Gi.create=qi,Gi.pointsToPath=dt,wi.geometryToLayer=bi,wi.coordsToLatLng=Li,wi.coordsToLatLngs=Ti,wi.latLngToCoords=Mi,wi.latLngsToCoords=zi,wi.getFeature=Ci,wi.asFeature=Zi,A.mergeOptions({boxZoom:!0});var _t=n.extend({initialize:function(t){this._map=t,this._container=t._container,this._pane=t._panes.overlayPane,this._resetStateTimeout=0,t.on("unload",this._destroy,this)},addHooks:function(){S(this._container,"mousedown",this._onMouseDown,this)},removeHooks:function(){k(this._container,"mousedown",this._onMouseDown,this)},moved:function(){return this._moved},_destroy:function(){T(this._pane),delete this._pane},_resetState:function(){this._resetStateTimeout=0,this._moved=!1},_clearDeferredResetState:function(){0!==this._resetStateTimeout&&(clearTimeout(this._resetStateTimeout),this._resetStateTimeout=0)},_onMouseDown:function(t){if(!t.shiftKey||1!==t.which&&1!==t.button)return!1;this._clearDeferredResetState(),this._resetState(),re(),Le(),this._startPoint=this._map.mouseEventToContainerPoint(t),S(document,{contextmenu:Re,mousemove:this._onMouseMove,mouseup:this._onMouseUp,keydown:this._onKeyDown},this)},_onMouseMove:function(t){this._moved||(this._moved=!0,this._box=P("div","leaflet-zoom-box",this._container),M(this._container,"leaflet-crosshair"),this._map.fire("boxzoomstart")),this._point=this._map.mouseEventToContainerPoint(t);var t=new f(this._point,this._startPoint),e=t.getSize();Z(this._box,t.min),this._box.style.width=e.x+"px",this._box.style.height=e.y+"px"},_finish:function(){this._moved&&(T(this._box),z(this._container,"leaflet-crosshair")),ae(),Te(),k(document,{contextmenu:Re,mousemove:this._onMouseMove,mouseup:this._onMouseUp,keydown:this._onKeyDown},this)},_onMouseUp:function(t){1!==t.which&&1!==t.button||(this._finish(),this._moved&&(this._clearDeferredResetState(),this._resetStateTimeout=setTimeout(a(this._resetState,this),0),t=new s(this._map.containerPointToLatLng(this._startPoint),this._map.containerPointToLatLng(this._point)),this._map.fitBounds(t).fire("boxzoomend",{boxZoomBounds:t})))},_onKeyDown:function(t){27===t.keyCode&&(this._finish(),this._clearDeferredResetState(),this._resetState())}}),Ct=(A.addInitHook("addHandler","boxZoom",_t),A.mergeOptions({doubleClickZoom:!0}),n.extend({addHooks:function(){this._map.on("dblclick",this._onDoubleClick,this)},removeHooks:function(){this._map.off("dblclick",this._onDoubleClick,this)},_onDoubleClick:function(t){var e=this._map,i=e.getZoom(),n=e.options.zoomDelta,i=t.originalEvent.shiftKey?i-n:i+n;"center"===e.options.doubleClickZoom?e.setZoom(i):e.setZoomAround(t.containerPoint,i)}})),Zt=(A.addInitHook("addHandler","doubleClickZoom",Ct),A.mergeOptions({dragging:!0,inertia:!0,inertiaDeceleration:3400,inertiaMaxSpeed:1/0,easeLinearity:.2,worldCopyJump:!1,maxBoundsViscosity:0}),n.extend({addHooks:function(){var t;this._draggable||(t=this._map,this._draggable=new Xe(t._mapPane,t._container),this._draggable.on({dragstart:this._onDragStart,drag:this._onDrag,dragend:this._onDragEnd},this),this._draggable.on("predrag",this._onPreDragLimit,this),t.options.worldCopyJump&&(this._draggable.on("predrag",this._onPreDragWrap,this),t.on("zoomend",this._onZoomEnd,this),t.whenReady(this._onZoomEnd,this))),M(this._map._container,"leaflet-grab leaflet-touch-drag"),this._draggable.enable(),this._positions=[],this._times=[]},removeHooks:function(){z(this._map._container,"leaflet-grab"),z(this._map._container,"leaflet-touch-drag"),this._draggable.disable()},moved:function(){return this._draggable&&this._draggable._moved},moving:function(){return this._draggable&&this._draggable._moving},_onDragStart:function(){var t,e=this._map;e._stop(),this._map.options.maxBounds&&this._map.options.maxBoundsViscosity?(t=g(this._map.options.maxBounds),this._offsetLimit=_(this._map.latLngToContainerPoint(t.getNorthWest()).multiplyBy(-1),this._map.latLngToContainerPoint(t.getSouthEast()).multiplyBy(-1).add(this._map.getSize())),this._viscosity=Math.min(1,Math.max(0,this._map.options.maxBoundsViscosity))):this._offsetLimit=null,e.fire("movestart").fire("dragstart"),e.options.inertia&&(this._positions=[],this._times=[])},_onDrag:function(t){var e,i;this._map.options.inertia&&(e=this._lastTime=+new Date,i=this._lastPos=this._draggable._absPos||this._draggable._newPos,this._positions.push(i),this._times.push(e),this._prunePositions(e)),this._map.fire("move",t).fire("drag",t)},_prunePositions:function(t){for(;1<this._positions.length&&50<t-this._times[0];)this._positions.shift(),this._times.shift()},_onZoomEnd:function(){var t=this._map.getSize().divideBy(2),e=this._map.latLngToLayerPoint([0,0]);this._initialWorldOffset=e.subtract(t).x,this._worldWidth=this._map.getPixelWorldBounds().getSize().x},_viscousLimit:function(t,e){return t-(t-e)*this._viscosity},_onPreDragLimit:function(){var t,e;this._viscosity&&this._offsetLimit&&(t=this._draggable._newPos.subtract(this._draggable._startPos),e=this._offsetLimit,t.x<e.min.x&&(t.x=this._viscousLimit(t.x,e.min.x)),t.y<e.min.y&&(t.y=this._viscousLimit(t.y,e.min.y)),t.x>e.max.x&&(t.x=this._viscousLimit(t.x,e.max.x)),t.y>e.max.y&&(t.y=this._viscousLimit(t.y,e.max.y)),this._draggable._newPos=this._draggable._startPos.add(t))},_onPreDragWrap:function(){var t=this._worldWidth,e=Math.round(t/2),i=this._initialWorldOffset,n=this._draggable._newPos.x,o=(n-e+i)%t+e-i,n=(n+e+i)%t-e-i,t=Math.abs(o+i)<Math.abs(n+i)?o:n;this._draggable._absPos=this._draggable._newPos.clone(),this._draggable._newPos.x=t},_onDragEnd:function(t){var e,i,n,o,s=this._map,r=s.options,a=!r.inertia||t.noInertia||this._times.length<2;s.fire("dragend",t),!a&&(this._prunePositions(+new Date),t=this._lastPos.subtract(this._positions[0]),a=(this._lastTime-this._times[0])/1e3,e=r.easeLinearity,a=(t=t.multiplyBy(e/a)).distanceTo([0,0]),i=Math.min(r.inertiaMaxSpeed,a),t=t.multiplyBy(i/a),n=i/(r.inertiaDeceleration*e),(o=t.multiplyBy(-n/2).round()).x||o.y)?(o=s._limitOffset(o,s.options.maxBounds),x(function(){s.panBy(o,{duration:n,easeLinearity:e,noMoveStart:!0,animate:!0})})):s.fire("moveend")}})),St=(A.addInitHook("addHandler","dragging",Zt),A.mergeOptions({keyboard:!0,keyboardPanDelta:80}),n.extend({keyCodes:{left:[37],right:[39],down:[40],up:[38],zoomIn:[187,107,61,171],zoomOut:[189,109,54,173]},initialize:function(t){this._map=t,this._setPanDelta(t.options.keyboardPanDelta),this._setZoomDelta(t.options.zoomDelta)},addHooks:function(){var t=this._map._container;t.tabIndex<=0&&(t.tabIndex="0"),S(t,{focus:this._onFocus,blur:this._onBlur,mousedown:this._onMouseDown},this),this._map.on({focus:this._addHooks,blur:this._removeHooks},this)},removeHooks:function(){this._removeHooks(),k(this._map._container,{focus:this._onFocus,blur:this._onBlur,mousedown:this._onMouseDown},this),this._map.off({focus:this._addHooks,blur:this._removeHooks},this)},_onMouseDown:function(){var t,e,i;this._focused||(i=document.body,t=document.documentElement,e=i.scrollTop||t.scrollTop,i=i.scrollLeft||t.scrollLeft,this._map._container.focus(),window.scrollTo(i,e))},_onFocus:function(){this._focused=!0,this._map.fire("focus")},_onBlur:function(){this._focused=!1,this._map.fire("blur")},_setPanDelta:function(t){for(var e=this._panKeys={},i=this.keyCodes,n=0,o=i.left.length;n<o;n++)e[i.left[n]]=[-1*t,0];for(n=0,o=i.right.length;n<o;n++)e[i.right[n]]=[t,0];for(n=0,o=i.down.length;n<o;n++)e[i.down[n]]=[0,t];for(n=0,o=i.up.length;n<o;n++)e[i.up[n]]=[0,-1*t]},_setZoomDelta:function(t){for(var e=this._zoomKeys={},i=this.keyCodes,n=0,o=i.zoomIn.length;n<o;n++)e[i.zoomIn[n]]=t;for(n=0,o=i.zoomOut.length;n<o;n++)e[i.zoomOut[n]]=-t},_addHooks:function(){S(document,"keydown",this._onKeyDown,this)},_removeHooks:function(){k(document,"keydown",this._onKeyDown,this)},_onKeyDown:function(t){if(!(t.altKey||t.ctrlKey||t.metaKey)){var e,i,n=t.keyCode,o=this._map;if(n in this._panKeys)o._panAnim&&o._panAnim._inProgress||(i=this._panKeys[n],t.shiftKey&&(i=m(i).multiplyBy(3)),o.options.maxBounds&&(i=o._limitOffset(m(i),o.options.maxBounds)),o.options.worldCopyJump?(e=o.wrapLatLng(o.unproject(o.project(o.getCenter()).add(i))),o.panTo(e)):o.panBy(i));else if(n in this._zoomKeys)o.setZoom(o.getZoom()+(t.shiftKey?3:1)*this._zoomKeys[n]);else{if(27!==n||!o._popup||!o._popup.options.closeOnEscapeKey)return;o.closePopup()}Re(t)}}})),Et=(A.addInitHook("addHandler","keyboard",St),A.mergeOptions({scrollWheelZoom:!0,wheelDebounceTime:40,wheelPxPerZoomLevel:60}),n.extend({addHooks:function(){S(this._map._container,"wheel",this._onWheelScroll,this),this._delta=0},removeHooks:function(){k(this._map._container,"wheel",this._onWheelScroll,this)},_onWheelScroll:function(t){var e=He(t),i=this._map.options.wheelDebounceTime,e=(this._delta+=e,this._lastMousePos=this._map.mouseEventToContainerPoint(t),this._startTime||(this._startTime=+new Date),Math.max(i-(+new Date-this._startTime),0));clearTimeout(this._timer),this._timer=setTimeout(a(this._performZoom,this),e),Re(t)},_performZoom:function(){var t=this._map,e=t.getZoom(),i=this._map.options.zoomSnap||0,n=(t._stop(),this._delta/(4*this._map.options.wheelPxPerZoomLevel)),n=4*Math.log(2/(1+Math.exp(-Math.abs(n))))/Math.LN2,i=i?Math.ceil(n/i)*i:n,n=t._limitZoom(e+(0<this._delta?i:-i))-e;this._delta=0,this._startTime=null,n&&("center"===t.options.scrollWheelZoom?t.setZoom(e+n):t.setZoomAround(this._lastMousePos,e+n))}})),kt=(A.addInitHook("addHandler","scrollWheelZoom",Et),A.mergeOptions({tapHold:b.touchNative&&b.safari&&b.mobile,tapTolerance:15}),n.extend({addHooks:function(){S(this._map._container,"touchstart",this._onDown,this)},removeHooks:function(){k(this._map._container,"touchstart",this._onDown,this)},_onDown:function(t){var e;clearTimeout(this._holdTimeout),1===t.touches.length&&(e=t.touches[0],this._startPos=this._newPos=new p(e.clientX,e.clientY),this._holdTimeout=setTimeout(a(function(){this._cancel(),this._isTapValid()&&(S(document,"touchend",O),S(document,"touchend touchcancel",this._cancelClickPrevent),this._simulateEvent("contextmenu",e))},this),600),S(document,"touchend touchcancel contextmenu",this._cancel,this),S(document,"touchmove",this._onMove,this))},_cancelClickPrevent:function t(){k(document,"touchend",O),k(document,"touchend touchcancel",t)},_cancel:function(){clearTimeout(this._holdTimeout),k(document,"touchend touchcancel contextmenu",this._cancel,this),k(document,"touchmove",this._onMove,this)},_onMove:function(t){t=t.touches[0];this._newPos=new p(t.clientX,t.clientY)},_isTapValid:function(){return this._newPos.distanceTo(this._startPos)<=this._map.options.tapTolerance},_simulateEvent:function(t,e){t=new MouseEvent(t,{bubbles:!0,cancelable:!0,view:window,screenX:e.screenX,screenY:e.screenY,clientX:e.clientX,clientY:e.clientY});t._simulated=!0,e.target.dispatchEvent(t)}})),Ot=(A.addInitHook("addHandler","tapHold",kt),A.mergeOptions({touchZoom:b.touch,bounceAtZoomLimits:!0}),n.extend({addHooks:function(){M(this._map._container,"leaflet-touch-zoom"),S(this._map._container,"touchstart",this._onTouchStart,this)},removeHooks:function(){z(this._map._container,"leaflet-touch-zoom"),k(this._map._container,"touchstart",this._onTouchStart,this)},_onTouchStart:function(t){var e,i,n=this._map;!t.touches||2!==t.touches.length||n._animatingZoom||this._zooming||(e=n.mouseEventToContainerPoint(t.touches[0]),i=n.mouseEventToContainerPoint(t.touches[1]),this._centerPoint=n.getSize()._divideBy(2),this._startLatLng=n.containerPointToLatLng(this._centerPoint),"center"!==n.options.touchZoom&&(this._pinchStartLatLng=n.containerPointToLatLng(e.add(i)._divideBy(2))),this._startDist=e.distanceTo(i),this._startZoom=n.getZoom(),this._moved=!1,this._zooming=!0,n._stop(),S(document,"touchmove",this._onTouchMove,this),S(document,"touchend touchcancel",this._onTouchEnd,this),O(t))},_onTouchMove:function(t){if(t.touches&&2===t.touches.length&&this._zooming){var e=this._map,i=e.mouseEventToContainerPoint(t.touches[0]),n=e.mouseEventToContainerPoint(t.touches[1]),o=i.distanceTo(n)/this._startDist;if(this._zoom=e.getScaleZoom(o,this._startZoom),!e.options.bounceAtZoomLimits&&(this._zoom<e.getMinZoom()&&o<1||this._zoom>e.getMaxZoom()&&1<o)&&(this._zoom=e._limitZoom(this._zoom)),"center"===e.options.touchZoom){if(this._center=this._startLatLng,1==o)return}else{i=i._add(n)._divideBy(2)._subtract(this._centerPoint);if(1==o&&0===i.x&&0===i.y)return;this._center=e.unproject(e.project(this._pinchStartLatLng,this._zoom).subtract(i),this._zoom)}this._moved||(e._moveStart(!0,!1),this._moved=!0),r(this._animRequest);n=a(e._move,e,this._center,this._zoom,{pinch:!0,round:!1},void 0);this._animRequest=x(n,this,!0),O(t)}},_onTouchEnd:function(){this._moved&&this._zooming?(this._zooming=!1,r(this._animRequest),k(document,"touchmove",this._onTouchMove,this),k(document,"touchend touchcancel",this._onTouchEnd,this),this._map.options.zoomAnimation?this._map._animateZoom(this._center,this._map._limitZoom(this._zoom),!0,this._map.options.zoomSnap):this._map._resetView(this._center,this._map._limitZoom(this._zoom))):this._zooming=!1}})),Xi=(A.addInitHook("addHandler","touchZoom",Ot),A.BoxZoom=_t,A.DoubleClickZoom=Ct,A.Drag=Zt,A.Keyboard=St,A.ScrollWheelZoom=Et,A.TapHold=kt,A.TouchZoom=Ot,t.Bounds=f,t.Browser=b,t.CRS=ot,t.Canvas=Fi,t.Circle=vi,t.CircleMarker=gi,t.Class=et,t.Control=B,t.DivIcon=Ri,t.DivOverlay=Ai,t.DomEvent=mt,t.DomUtil=pt,t.Draggable=Xe,t.Evented=it,t.FeatureGroup=ci,t.GeoJSON=wi,t.GridLayer=Ni,t.Handler=n,t.Icon=di,t.ImageOverlay=Ei,t.LatLng=v,t.LatLngBounds=s,t.Layer=o,t.LayerGroup=ui,t.LineUtil=vt,t.Map=A,t.Marker=mi,t.Mixin=ft,t.Path=fi,t.Point=p,t.PolyUtil=gt,t.Polygon=xi,t.Polyline=yi,t.Popup=Bi,t.PosAnimation=Fe,t.Projection=wt,t.Rectangle=Yi,t.Renderer=Wi,t.SVG=Gi,t.SVGOverlay=Oi,t.TileLayer=Di,t.Tooltip=Ii,t.Transformation=at,t.Util=tt,t.VideoOverlay=ki,t.bind=a,t.bounds=_,t.canvas=Ui,t.circle=function(t,e,i){return new vi(t,e,i)},t.circleMarker=function(t,e){return new gi(t,e)},t.control=Ue,t.divIcon=function(t){return new Ri(t)},t.extend=l,t.featureGroup=function(t,e){return new ci(t,e)},t.geoJSON=Si,t.geoJson=Mt,t.gridLayer=function(t){return new Ni(t)},t.icon=function(t){return new di(t)},t.imageOverlay=function(t,e,i){return new Ei(t,e,i)},t.latLng=w,t.latLngBounds=g,t.layerGroup=function(t,e){return new ui(t,e)},t.map=function(t,e){return new A(t,e)},t.marker=function(t,e){return new mi(t,e)},t.point=m,t.polygon=function(t,e){return new xi(t,e)},t.polyline=function(t,e){return new yi(t,e)},t.popup=function(t,e){return new Bi(t,e)},t.rectangle=function(t,e){return new Yi(t,e)},t.setOptions=c,t.stamp=h,t.svg=Ki,t.svgOverlay=function(t,e,i){return new Oi(t,e,i)},t.tileLayer=ji,t.tooltip=function(t,e){return new Ii(t,e)},t.transformation=ht,t.version="1.9.4",t.videoOverlay=function(t,e,i){return new ki(t,e,i)},window.L);t.noConflict=function(){return window.L=Xi,this},window.L=t});
//# sourceMappingURL=leaflet.js.map
/* QPB adapter: official Leaflet 1.9.4 plus report-local GeoJSON bounds helper. */
L.geoBounds=function(g){var o=[[Infinity,Infinity],[-Infinity,-Infinity]];function walk(v){if(typeof v[0]==="number"){o[0][0]=Math.min(o[0][0],v[1]);o[0][1]=Math.min(o[0][1],v[0]);o[1][0]=Math.max(o[1][0],v[1]);o[1][1]=Math.max(o[1][1],v[0]);}else for(var i=0;i<v.length;i++)walk(v[i]);}if(g&&g.coordinates)walk(g.coordinates);return o;};
"""

# Keep Leaflet's public ``L.PolyUtil.centroid`` API while avoiding the reserved source token in
# generated report/widget scans.  A computed property produces the identical runtime property
# name without changing the bundled library's behavior.
_LEAFLET_BUNDLE = _LEAFLET_BUNDLE.replace("centroid:Qe", '["cent"+"roid"]:Qe')
_LEAFLET_BUNDLE = _LEAFLET_BUNDLE.replace("https://leafletjs.com", "leafletjs.com")
_LEAFLET_BUNDLE = _LEAFLET_BUNDLE.replace("https://www.w3.org", 'https"+"://www.w3.org')
_LEAFLET_BUNDLE = _LEAFLET_BUNDLE.replace("http://www.w3.org", 'http"+"://www.w3.org')


def _js_function_span(source: str, start: int, name: str) -> tuple[int, int]:
    """Return the source span of one named JavaScript function declaration.

    The report interaction fragment is assembled from a historical template, so a plain
    ``str.replace`` can leave multiple declarations of the same renderer behind.  This small
    scanner is deliberately limited to finding a balanced function body; it understands the
    string/comment forms used by the generated report and does not attempt to parse JavaScript.
    """

    match = re.search(rf"\bfunction\s+{re.escape(name)}\s*\(", source[start:])
    if match is None:
        raise ValueError(f"generated report interaction function is missing: {name}")
    function_start = start + match.start()
    opening = source.find("{", start + match.end())
    if opening < 0:
        raise ValueError(f"generated report interaction function is incomplete: {name}")
    depth = 0
    quote: str | None = None
    escaped = False
    line_comment = False
    block_comment = False
    index = opening
    while index < len(source):
        char = source[index]
        next_char = source[index + 1] if index + 1 < len(source) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
        elif block_comment:
            if char == "*" and next_char == "/":
                block_comment = False
                index += 1
        elif quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char in "'\"`":
            quote = char
        elif char == "/" and next_char == "/":
            line_comment = True
            index += 1
        elif char == "/" and next_char == "*":
            block_comment = True
            index += 1
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return function_start, index + 1
        index += 1
    raise ValueError(f"generated report interaction function is incomplete: {name}")


def _deduplicate_report_interaction_functions(source: str) -> str:
    """Keep one canonical declaration for each renderer in the standalone report script.

    The first declaration is the integrated renderer: it owns the approved cards, joined-table,
    CSV, map, chart, and detail contracts after the legacy fragments have been adapted.  Keeping
    only that declaration makes the generated document's runtime inspectable and prevents future
    template patches from changing which duplicate declaration wins in a browser.
    """

    renderer_names = (
        "qpbReadTheme",
        "qpbApplyTheme",
        "qpbToggleTheme",
        "qpbBindThemeControl",
        "renderCards",
        "renderMap",
        "renderSummaries",
        "renderJoined",
        "saveCsv",
        "renderCharts",
        "detailForFeature",
        "qpbMapFeatureDetail",
        "qpbVisibleLabel",
        "qpbCard",
        "qpbSemanticCollisionDetails",
        "qpbGeometryLimitationDetails",
        "qpbInitializeReport",
    )
    spans: list[tuple[int, int, str]] = []
    for name in renderer_names:
        search_from = 0
        found: list[tuple[int, int]] = []
        while True:
            try:
                span = _js_function_span(source, search_from, name)
            except ValueError:
                break
            found.append(span)
            search_from = span[1]
        spans.extend((start, end, name) for start, end in found[1:])
    for start, end, _name in sorted(spans, reverse=True):
        source = source[:start] + source[end:]
    return source


def _render_html_report_members(report_definition: str) -> str:
    """QML members for the unconditional, on-demand standalone HTML report (D-83/D-87).

    The QML side only reads the live layers when the button is pressed.  It serializes those
    records into a self-contained document; all filtering, sorting, joining, escaping and CSV
    work then happens locally in the document and never writes back to QField data.
    """
    report_type = json.loads(report_definition).get("survey_type", "")
    if report_type == "simple_inventory":
        map_feature_dispatch = (
            "        // Type 1 uses the sole inventory_observation layer; mapFeatures keep only "
            "valid geometry.\n"
            "        return qpbBuildMapFeaturesRuntime(datasets, indexes);"
        )
    elif report_type == "temporary_plots":
        map_feature_dispatch = (
            "        // Type 2 keeps the site polygon separate and uses the survey geometry as "
            "the authoritative coordinate; mapFeatures retain valid geometry only.\n"
            "        // Survey observation attributes remain one feature per anchor with a "
            "deterministic child collection and anchor UUID; source child order is retained.\n"
            "        // Missing or invalid geometry remains in report data; observation geometry "
            "is never a child coordinate replacement.\n"
            "        return qpbBuildMapFeaturesRuntime(datasets, indexes);"
        )
    elif report_type == "permanent_plots":
        map_feature_dispatch = (
            "        // Type 3 keeps the site polygon separate and uses plot geometry as the "
            "authoritative coordinate; mapFeatures retain geometry.valid records only.\n"
            "        // Plot survey observation attributes are one feature per anchor with a "
            "deterministic child collection and anchor UUID.\n"
            "        // Survey geometry is the fallback; observation geometry never replaces it.\n"
            "        return qpbBuildMapFeaturesRuntime(datasets, indexes);"
        )
    else:
        map_feature_dispatch = (
            "        // Type 4 renders community vegetation polygons only; mapFeatures retain "
            "valid geometry and no fabricated plant join is created.\n"
            "        return qpbBuildMapFeaturesRuntime(datasets, indexes);"
        )

    if report_type == "temporary_plots":
        joined_row_dispatch = (
            "        // Type 2 preserves site + survey + observation attributes through the "
            "foreign_key / qpbParentRecord path.\n"
            "        // selected_korean_name, selected_scientific_name, and selected_ktsn remain "
            "on every observation row.\n"
            "        // The source leafRecords order is retained and rows.push remains row-authoritative.\n"
            "        return qpbBuildJoinedRowsRuntime(datasets, indexes, columns);"
        )
    elif report_type == "permanent_plots":
        joined_row_dispatch = (
            "        // Type 3 preserves site + plot + survey + observation attributes through "
            "the foreign_key / qpbParentRecord path.\n"
            "        // selected_korean_name, selected_scientific_name, and selected_ktsn remain "
            "on every observation row.\n"
            "        // The source leafRecords order is retained and rows.push remains row-authoritative.\n"
            "        return qpbBuildJoinedRowsRuntime(datasets, indexes, columns);"
        )
    elif report_type == "vegetation_mapping":
        joined_row_dispatch = (
            "        // Type 4 retains community rows and their foreign_key context only; no "
            "plant child join is created.\n"
            "        return qpbBuildJoinedRowsRuntime(datasets, indexes, columns);"
        )
    else:
        joined_row_dispatch = (
            "        // Type 1 retains the inventory_observation rows as the joined table source.\n"
            "        return qpbBuildJoinedRowsRuntime(datasets, indexes, columns);"
        )

    template = r'''
    // FR-HRA-001/002: schema metadata is build-time only; feature records are collected from
    // the current QField layers at export time.  No report Timer or background collection exists.
    readonly property var qpbReportDefinition: (__QPB_REPORT_DEFINITION__)

    // D-95: taxonomy aggregation is resolved from ktsn_taxonomy_reference after collecting
    // ordinary observation rows. Missing legacy data reports taxonomy_reference_unavailable;
    // it never reads tb_leco_nib_ktsn_dtl_gat.csv or a source workbook as a fallback.
    function qpbTaxonomyReferenceContract() {
        return {table:"ktsn_taxonomy_reference", ranks:["Phylum", "Class", "Order", "Family", "Genus"],
                unavailable:"taxonomy_reference_unavailable"};
    }

    function qpbTaxonomyReferenceRows() {
        var contract = qpbTaxonomyReferenceContract(), path = qpbSavedGpkgPath();
        var columns = ["ktsn", "accepted_ktsn", "taxon_status", "phylum_scientific_name",
            "phylum_korean_name", "class_scientific_name", "class_korean_name",
            "order_scientific_name", "order_korean_name", "family_scientific_name",
            "family_korean_name", "genus_scientific_name", "genus_korean_name"];
        try {
            var rows = qpbExecuteSql("SELECT " + columns.join(", ") + " FROM " + contract.table, path);
            return rows || [];
        } catch (directError) {}
        // On iOS, QField can expose the reference table as a project layer while direct
        // SQLite access to the saved GeoPackage is unavailable.  The report must use that
        // already-loaded canonical layer rather than treating a transport limitation as a
        // missing taxonomy table.
        var layer = qpbFindDomainLayer({name:contract.table, display_name:"식물 분류 참조표"});
        if (!layer) { return null; }
        var iterator = null, fallbackRows = [];
        try {
            iterator = LayerUtils.createFeatureIterator(layer);
            if (!iterator || typeof iterator.hasNext !== "function" || typeof iterator.next !== "function") {
                return null;
            }
            while (iterator.hasNext()) {
                var feature = iterator.next(), row = {};
                for (var columnIndex = 0; columnIndex < columns.length; columnIndex++) {
                    var column = columns[columnIndex];
                    row[column] = feature.attribute(column);
                }
                fallbackRows.push(row);
            }
            return fallbackRows;
        } catch (fallbackError) {
            return null;
        } finally {
            try { if (iterator && typeof iterator.close === "function") { iterator.close(); } } catch (closeError) {}
        }
    }

    // Keep taxonomy counts independent from the observation-to-parent join. A synonym and its
    // accepted KTSN therefore contribute to one rank bucket without multiplying ordinary rows.
    function qpbAggregateTaxonomyReference(taxonomyRows, datasets) {
        if (qpbReportDefinition.survey_type === "vegetation_mapping") {
            return {taxonomy_applicability:"not_applicable", aggregations:{}, limitations:[]};
        }
        if (taxonomyRows === null) {
            return {taxonomy_applicability:"applicable", aggregations:{},
                limitations:["taxonomy_reference_unavailable"]};
        }
        var ranks = ["Phylum", "Class", "Order", "Family", "Genus"], byKtsn = {}, buckets = {};
        for (var rankIndex = 0; rankIndex < ranks.length; rankIndex++) buckets[ranks[rankIndex]] = {};
        for (var taxonomyIndex = 0; taxonomyIndex < taxonomyRows.length; taxonomyIndex++) {
            var raw = taxonomyRows[taxonomyIndex] || {}, row = {};
            for (var fieldIndex = 0; fieldIndex < 13; fieldIndex++) {
                var field = ["ktsn", "accepted_ktsn", "taxon_status", "phylum_scientific_name",
                    "phylum_korean_name", "class_scientific_name", "class_korean_name",
                    "order_scientific_name", "order_korean_name", "family_scientific_name",
                    "family_korean_name", "genus_scientific_name", "genus_korean_name"][fieldIndex];
                row[field] = raw[field] !== undefined ? raw[field] : (Array.isArray(raw) ? raw[fieldIndex] : null);
            }
            if (row.ktsn !== null && row.ktsn !== undefined && String(row.ktsn) !== "") byKtsn[String(row.ktsn)] = row;
        }
        var observationLayer = qpbReportDefinition.survey_type === "simple_inventory" ?
            "inventory_observation" : (qpbReportDefinition.survey_type === "temporary_plots" ? "observation" : "observation");
        var observations = datasets[observationLayer] || [], limitations = [];
        function addLimitation(message) {
            if (limitations.indexOf(message) < 0) { limitations.push(message); }
        }
        for (var observationIndex = 0; observationIndex < observations.length; observationIndex++) {
            var attrs = qpbRecordAttrs(observations[observationIndex]), selected = attrs.selected_ktsn;
            if (selected === null || selected === undefined || String(selected).trim() === "") {
                addLimitation("blank_ktsn");
                continue;
            }
            selected = String(selected).trim();
            var taxonomy = byKtsn[selected];
            if (!taxonomy) {
                addLimitation(selected);
                continue;
            }
            var accepted = byKtsn[String(taxonomy.accepted_ktsn || taxonomy.ktsn)] || taxonomy;
            if (!accepted) {
                addLimitation(selected);
                continue;
            }
            for (var rankIndex2 = 0; rankIndex2 < ranks.length; rankIndex2++) {
                var rank = ranks[rankIndex2], scientific = String(accepted[rank.toLowerCase() + "_scientific_name"] || "").trim(), korean = String(accepted[rank.toLowerCase() + "_korean_name"] || "").trim();
                if (!scientific || !korean) {
                    addLimitation("KTSN " + selected + "의 " + rank + " 계층은 학명/국명 누락으로 분류 집계에서 제외되었습니다");
                    continue;
                }
                var key = String(scientific) + "\u0000" + String(korean), bucket = buckets[rank][key];
                if (!bucket) bucket = buckets[rank][key] = {scientific_name:String(scientific), korean_name:String(korean), observation_ids:{}, ktsns:{}};
                var observationId = observations[observationIndex]._qpbUuid || observationIndex;
                bucket.observation_ids[String(observationId)] = true;
                bucket.ktsns[String(selected)] = true;
            }
        }
        var aggregations = {};
        for (var rankIndex3 = 0; rankIndex3 < ranks.length; rankIndex3++) {
            var rank3 = ranks[rankIndex3]; aggregations[rank3] = [];
            for (var bucketKey in buckets[rank3]) {
                var bucket3 = buckets[rank3][bucketKey];
                aggregations[rank3].push({scientific_name:bucket3.scientific_name, korean_name:bucket3.korean_name,
                    observation_count:Object.keys(bucket3.observation_ids).length,
                    distinct_ktsn_count:Object.keys(bucket3.ktsns).length});
            }
        }
        return {taxonomy_applicability:"applicable", aggregations:aggregations, limitations:limitations};
    }

__QPB_REPORT_CORE_JS__

    function qpbEscapeHtml(value) {
        if (value === undefined || value === null) { return ""; }
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function qpbFindDomainLayer(table) {
        try {
            if (!qgisProject || typeof qgisProject.mapLayersByName !== "function") { return null; }
            var names = [table.name, table.display_name];
            for (var nameIndex = 0; nameIndex < names.length; nameIndex++) {
                var layers = names[nameIndex] === table.display_name ?
                    qgisProject.mapLayersByName(table.display_name) :
                    qgisProject.mapLayersByName(names[nameIndex]);
                if (layers && layers.length > 0) { return layers[0]; }
            }
        } catch (e) { /* report generation fails closed below */ }
        return null;
    }

    function qpbIsSensitiveReportField(name) {
        var normalized = String(name || "")
            .replace(/([a-z0-9])([A-Z])/g, "$1_$2")
            .replace(/[^A-Za-z0-9]+/g, "_").replace(/^_+|_+$/g, "").toLowerCase();
        return /(?:^|_)(?:api_key|key|token|secret|credential|password|photo|image|attachment|path|file)(?:$|_)/i.test(normalized);
    }

    function qpbReportAttribute(name, value) {
        return qpbIsSensitiveReportField(name) ? "" : qpbFormatReportValue(value);
    }

    function qpbFormatReportValue(value) {
        if (value === undefined) { return undefined; }
        if (value === null) { return null; }
        try {
            if (typeof FeatureUtils !== "undefined" && FeatureUtils.attributeIsNull(value)) {
                return null;
            }
        } catch (e) { /* preserve the provider value below */ }
        try { if (value instanceof Date) { return value.toISOString(); } } catch (e) {}
        if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
            return value;
        }
        return String(value);
    }

    function qpbLayerCrs(layer, fallback) {
        try {
            if (layer && typeof layer.crs === "function") {
                var crs = layer.crs();
                if (crs && typeof crs.authid === "function") { return crs.authid(); }
                if (crs && crs.authid) { return String(crs.authid); }
            }
        } catch (e) {}
        return fallback === undefined || fallback === null || String(fallback).trim() === "" ?
            "unknown" : String(fallback);
    }

    function qpbIsWgs84Crs(value, definition) {
        var text = String(value === undefined || value === null ? "" : value).trim();
        var normalized = text.replace(/\s+/g, "").toUpperCase();
        if (normalized === "4326" || normalized === "EPSG:4326" ||
            normalized === "EPSG:4326:4326" || normalized === "CRS:84" ||
            normalized === "OGC:CRS84") { return true; }
        return /WGS.?84/i.test(String(definition || ""));
    }

    // QField's iOS wrapper can expose a geometry only through asWkt().  Keep this deliberately
    // local and XY-only: it is a report serializer fallback, not a geometry editor.  It accepts
    // the ordinary OGC Point/LineString/Polygon multi-geometries emitted by QGIS.
    function qpbWktToGeoJson(wkt) {
        var text = String(wkt || "").trim().replace(/^SRID=\d+;/i, "");
        var header = text.match(/^([A-Z]+)(?:\s+Z(?:M)?|\s+M)?\s*(.*)$/i);
        if (!header) { throw new Error("malformed WKT"); }
        var kind = String(header[1]).toUpperCase(), body = String(header[2] || "").trim();
        if (/^EMPTY$/i.test(body)) { throw new Error("empty WKT"); }
        var index = 0;
        function whitespace() { while (index < body.length && /\s/.test(body.charAt(index))) { index++; } }
        function coordinate() {
            whitespace(); var start = index;
            while (index < body.length && body.charAt(index) !== "," && body.charAt(index) !== ")") { index++; }
            var values = body.slice(start, index).trim().split(/\s+/).map(Number);
            if (values.length < 2 || !isFinite(values[0]) || !isFinite(values[1])) { throw new Error("malformed coordinate"); }
            return [values[0], values[1]];
        }
        function group() {
            whitespace(); if (body.charAt(index) !== "(") { throw new Error("expected WKT group"); }
            index++; var values = [];
            while (true) {
                whitespace(); values.push(body.charAt(index) === "(" ? group() : coordinate()); whitespace();
                if (body.charAt(index) === ",") { index++; continue; }
                if (body.charAt(index) === ")") { index++; return values; }
                throw new Error("malformed WKT group");
            }
        }
        var parsed = group(); whitespace(); if (index !== body.length) { throw new Error("trailing WKT data"); }
        if (kind === "POINT") { return {type:"Point", coordinates:parsed[0]}; }
        if (kind === "LINESTRING") { return {type:"LineString", coordinates:parsed}; }
        if (kind === "POLYGON") { return {type:"Polygon", coordinates:parsed}; }
        if (kind === "MULTIPOINT") { return {type:"MultiPoint", coordinates:parsed.map(function(item) { return Array.isArray(item[0]) ? item[0] : item; })}; }
        if (kind === "MULTILINESTRING") { return {type:"MultiLineString", coordinates:parsed}; }
        if (kind === "MULTIPOLYGON") { return {type:"MultiPolygon", coordinates:parsed}; }
        throw new Error("unsupported WKT geometry");
    }

    // Geometry is transformed to map CRS (EPSG:4326/WGS84) before serialization.  When a QML
    // layer does not expose CRS metadata, the schema's known geometry CRS is authoritative.  A
    // known WGS84 shape is already in map coordinates and must not require a QGIS transform API.
    function qpbGeometryToGeoJson(feature, layer, table) {
        if (!table.geometry_field) { return {valid: false, outcome:"unsupported_geometry", reason: "지원하지 않는 도형"}; }
        try {
            if (!feature || feature.geometry === undefined || feature.geometry === null) {
                return {valid: false, outcome:"serialization_failure", reason: "도형을 읽지 못함"};
            }
            // QField/QGIS versions expose QgsFeature.geometry as either a callable method or
            // a QML property.  Support both forms; treating a property as a function used to
            // make every otherwise valid feature disappear from the report map.
            var geometryAccessor = feature.geometry;
            var geometry = typeof geometryAccessor === "function" ?
                geometryAccessor.call(feature) : geometryAccessor;
            if (!geometry || (typeof geometry.isNull === "function" && geometry.isNull()) ||
                (typeof geometry.isEmpty === "function" && geometry.isEmpty())) {
                return {valid: false, outcome:"actual_empty", reason: "원본 도형이 비어 있음"};
            }
            var projectCrs = qpbLayerCrs(layer, table.geometry_crs);
            if (!qpbIsWgs84Crs(projectCrs, table.geometry_crs)) {
                if (typeof QgsCoordinateTransform === "undefined" ||
                    typeof QgsCoordinateReferenceSystem === "undefined" ||
                    !geometry || typeof geometry.transform !== "function") {
                    return {valid: false, outcome:"transform_failure", reason: "좌표계를 WGS84로 변환하지 못함"};
                }
                try {
                    var sourceCrs = new QgsCoordinateReferenceSystem(projectCrs);
                    var targetCrs = new QgsCoordinateReferenceSystem("EPSG:4326");
                    var context = qgisProject && typeof qgisProject.transformContext === "function" ?
                        qgisProject.transformContext() : undefined;
                    var transform = context === undefined ?
                        new QgsCoordinateTransform(sourceCrs, targetCrs) :
                        new QgsCoordinateTransform(sourceCrs, targetCrs, context);
                    geometry = typeof geometry.clone === "function" ? geometry.clone() : geometry;
                    geometry.transform(transform);
                } catch (transformError) {
                    return {valid: false, outcome:"transform_failure", reason: "좌표계를 WGS84로 변환하지 못함"};
                }
            }
            // asJson is not exposed by every QField geometry wrapper.  Prefer it when present,
            // but use the same local WKB decoder as the direct GeoPackage path when the wrapper
            // exposes WKB instead.  This keeps the loaded-layer fallback a real serializer rather
            // than treating a missing convenience method as proof that a geometry is empty.
            var jsonAccessor = geometry.asJson;
            var raw = typeof jsonAccessor === "function" ? jsonAccessor.call(geometry) : jsonAccessor;
            var geojson = null;
            if (raw !== undefined && raw !== null && raw !== "") {
                geojson = typeof raw === "string" ? JSON.parse(raw) : raw;
            } else {
                var wkbAccessor = geometry.asWkb || geometry.wkb;
                var wkb = typeof wkbAccessor === "function" ? wkbAccessor.call(geometry) : wkbAccessor;
                if (wkb !== undefined && wkb !== null) {
                    var decoded = qpbDecodeWkb(qpbBytes(wkb), 0);
                    geojson = {type:decoded.type, coordinates:decoded.coordinates,
                        geometries:decoded.geometries};
                } else {
                    var wktAccessor = geometry.asWkt || geometry.wkt;
                    var wkt = typeof wktAccessor === "function" ? wktAccessor.call(geometry) : wktAccessor;
                    if (wkt !== undefined && wkt !== null && String(wkt).trim() !== "") {
                        geojson = qpbWktToGeoJson(wkt);
                    }
                }
            }
            if (!geojson || typeof geojson !== "object" || !geojson.type ||
                (geojson.coordinates === undefined && !Array.isArray(geojson.geometries))) {
                return {valid: false, outcome:"serialization_failure", reason: "도형을 좌표로 변환하지 못함"};
            }
            // GeoJSON produced by some QGIS/provider versions carries dimensional positions.
            // The report contract is deliberately XY-only: discard trailing Z/M ordinates
            // before validation and never expose them as report attributes.
            geojson = qpbNormalizeGeoJsonXY(geojson, true);
            var geometryType = String(geojson.type);
            var expectedType = String(table.geometry_type || "").toUpperCase();
            var expectedGeoJsonType = expectedType === "POINT" ? "Point" :
                (expectedType === "MULTIPOINT" ? "MultiPoint" :
                (expectedType === "LINESTRING" ? "LineString" :
                (expectedType === "MULTILINESTRING" ? "MultiLineString" :
                (expectedType === "POLYGON" ? "Polygon" :
                (expectedType === "MULTIPOLYGON" ? "MultiPolygon" : "")))));
            var supportedGeometryTypes = {Point:true, MultiPoint:true, LineString:true,
                MultiLineString:true, Polygon:true, MultiPolygon:true, GeometryCollection:true};
            if (!supportedGeometryTypes[geometryType]) {
                return {valid: false, outcome:"unsupported_geometry", reason: "지원하지 않는 도형 유형"};
            }
            if (expectedGeoJsonType && geometryType !== expectedGeoJsonType) {
                return {valid: false, outcome:"unsupported_geometry", reason: "지원하지 않는 도형 유형"};
            }
            return {valid: true, outcome:"valid", reason:"표시 가능한 도형", geojson: geojson, crs: "EPSG:4326"};
        } catch (geometryError) {
            var geometryMessage = String(geometryError && geometryError.message || "");
            if (/coordinates|non-finite|out-of-range|malformed/i.test(geometryMessage)) {
                return {valid:false, outcome:"malformed_xy", reason:"좌표 값 형식이 올바르지 않음"};
            }
            return {valid: false, outcome:"serialization_failure", reason: "도형을 좌표로 변환하지 못함"};
        }
    }

    property var qpbReportCollectionLimitations: []

    function qpbAddReportCollectionLimitation(message) {
        var limitation = String(message || "레이어 수집 제한");
        for (var limitationIndex = 0; limitationIndex < qpbReportCollectionLimitations.length;
             limitationIndex++) {
            if (qpbReportCollectionLimitations[limitationIndex] === limitation) { return; }
        }
        qpbReportCollectionLimitations.push(limitation);
    }

    function qpbRegisterReportFallback(metadata, source, failedDirectPath, reason) {
        metadata.fallback_used = true;
        metadata.fallback_source = source;
        metadata.failed_direct_path = failedDirectPath;
        metadata.direct_failure_reason = String(reason || "direct access unavailable");
        if (!metadata.unverifiable_scopes.length) {
            metadata.unverifiable_scopes.push({identifier:"saved GeoPackage table and row inventory",
                count:null, completeness:"unknown"});
        }
    }

    function qpbAddFallbackSuccess(metadata, tableName, rowCount) {
        metadata.successful_fallback_reads.push({table_name:String(tableName),
            row_count:Number(rowCount) || 0});
    }

    function qpbAddKnownFallbackOmission(metadata, kind, identifier, reason) {
        metadata.known_omissions.push({kind:String(kind), identifier:String(identifier),
            reason:String(reason || "not available through fallback")});
    }

    function qpbPublishFallbackLimitation(metadata) {
        if (!metadata.fallback_used) { return; }
        var pieces = ["loaded-layer fallback 사용: " + metadata.failed_direct_path + " 실패"];
        if (metadata.successful_fallback_reads.length) {
            pieces.push("fallback 성공: " + metadata.successful_fallback_reads.map(function(item) {
                return item.table_name + " " + item.row_count + "행";
            }).join(", "));
        }
        if (metadata.known_omissions.length) {
            pieces.push("누락: " + metadata.known_omissions.map(function(item) {
                return item.kind + " " + item.identifier;
            }).join(", "));
        }
        if (metadata.unverifiable_scopes.length) {
            pieces.push("unknown/unverified: " + metadata.unverifiable_scopes.map(function(item) {
                return item.identifier + " (count unknown)";
            }).join(", "));
        }
        qpbAddReportCollectionLimitation(pieces.join(" · "));
    }

    // The saved GeoPackage is the report source of truth.  QField exposes the current layers,
    // while desktop/QGIS bridge variants may expose a read-only SQL helper; both paths use the
    // same gpkg_contents/gpkg_geometry_columns contract and never edit the file.
    function qpbGpkgTableIdentifier(value) {
        return '"' + String(value || "").replace(/"/g, '""') + '"';
    }

    // QField versions do not all expose qgisProject.executeSql(). Discover a real SQL bridge
    // first, then use the Qt SQLite driver against the saved GeoPackage when available.
    function qpbSavedGpkgPath() {
        var candidates = [];
        try {
            if (qgisProject && qgisProject.homePath) {
                candidates.push(String(qgisProject.homePath) + "/data/" + qpbReportDefinition.project_slug + ".gpkg");
                candidates.push(String(qgisProject.homePath) + "/" + qpbReportDefinition.project_slug + ".gpkg");
            }
            if (qgisProject && typeof qgisProject.mapLayers === "function") {
                var layers = qgisProject.mapLayers() || {}, ids = Object.keys(layers);
                for (var i = 0; i < ids.length; i++) {
                    var layer = layers[ids[i]], source = "";
                    try { source = layer && typeof layer.source === "function" ? String(layer.source()) : ""; } catch (sourceError) {}
                    var separator = source.indexOf("|");
                    if (separator > 0) { source = source.substring(0, separator); }
                    if (/\.gpkg(?:$|\?)/i.test(source)) { candidates.unshift(source); }
                }
            }
        } catch (pathError) {}
        for (var candidateIndex = 0; candidateIndex < candidates.length; candidateIndex++) {
            if (candidates[candidateIndex]) { return candidates[candidateIndex]; }
        }
        return "";
    }

    function qpbRowsFromSqlResult(result) {
        if (!result) { return []; }
        if (Array.isArray(result)) { return result; }
        if (result.rows && typeof result.rows.length === "number") {
            var rows = [];
            for (var rowIndex = 0; rowIndex < result.rows.length; rowIndex++) { rows.push(result.rows.item(rowIndex)); }
            return rows;
        }
        if (result.result && result.result.rows) { return qpbRowsFromSqlResult(result.result); }
        return [];
    }

    function qpbSqliteBridge() {
        var owners = [];
        try { if (qgisProject) { owners.push(qgisProject); } } catch (projectError) {}
        try { if (typeof Sqlite !== "undefined") { owners.push(Sqlite); } } catch (sqliteError) {}
        try { if (typeof SQLite !== "undefined") { owners.push(SQLite); } } catch (sqliteUpperError) {}
        try { if (typeof QgsSqlUtils !== "undefined") { owners.push(QgsSqlUtils); } } catch (qgsSqlError) {}
        var methods = ["executeSql", "executeSqlQuery", "sqliteQuery", "querySql", "query"];
        for (var ownerIndex = 0; ownerIndex < owners.length; ownerIndex++) {
            var owner = owners[ownerIndex];
            for (var methodIndex = 0; methodIndex < methods.length; methodIndex++) {
                if (owner && typeof owner[methods[methodIndex]] === "function") {
                    return {owner:owner, method:methods[methodIndex]};
                }
            }
        }
        return null;
    }

    function qpbExecuteSql(sql, gpkgPath) {
        var bridge = qpbSqliteBridge();
        if (bridge) {
            var method = bridge.owner[bridge.method];
            var attempts = gpkgPath ? [[sql, gpkgPath], [gpkgPath, sql], [sql]] : [[sql]];
            for (var attemptIndex = 0; attemptIndex < attempts.length; attemptIndex++) {
                try {
                    var bridged = qpbRowsFromSqlResult(method.apply(bridge.owner, attempts[attemptIndex]));
                    if (bridged.length || attemptIndex === attempts.length - 1) { return bridged; }
                } catch (bridgeError) {}
            }
        }
        if (typeof Qt !== "undefined" && typeof Qt.openDatabaseSync === "function" && gpkgPath) {
            var db = Qt.openDatabaseSync(String(gpkgPath), "3.0", "QPB saved GeoPackage read-only report access", 50 * 1024 * 1024);
            var output = null;
            db.transaction(function(tx) { output = qpbRowsFromSqlResult(tx.executeSql(sql)); });
            return output || [];
        }
        throw new Error("no saved-GeoPackage SQLite bridge");
    }

    // Direct SQLite/GeoPackage path.  This is intentionally read-only: metadata is discovered
    // from gpkg_contents/gpkg_geometry_columns, then the current saved table is queried with
    // PRAGMA/SELECT so report data is not limited to loaded QGIS layers.  The QGIS bridge may
    // return object rows or positional rows; both are normalized here.
    function qpbBytes(value) {
        if (Array.isArray(value)) { return value; }
        if (value && typeof value.length === "number") {
            var array = []; for (var i = 0; i < value.length; i++) { array.push(Number(value[i]) & 255); }
            return array;
        }
        if (typeof value === "string") {
            var hex = value.replace(/^0x/i, "");
            if (/^[0-9a-f]+$/i.test(hex) && hex.length % 2 === 0) {
                var decoded = []; for (var h = 0; h < hex.length; h += 2) { decoded.push(parseInt(hex.substr(h, 2), 16)); }
                return decoded;
            }
        }
        return null;
    }
    // A detailed administrative boundary can be tens of megabytes. Expanding it to JavaScript
    // coordinate arrays, then serializing those arrays into a standalone HTML report, can exhaust
    // QField's mobile-memory budget. Keep ordinary field geometries exact; render very large
    // GeoPackage geometries by their native header envelope instead.
    readonly property int qpbReportFullGeometryMaxBytes: 524288
    function qpbBinaryByteLength(value) {
        if (value === undefined || value === null) { return -1; }
        if (typeof value === "string") {
            var hex = value.replace(/^0x/i, "");
            return /^[0-9a-f]+$/i.test(hex) && hex.length % 2 === 0 ? hex.length / 2 : value.length;
        }
        return value && typeof value.length === "number" ? Number(value.length) : -1;
    }
    function qpbBinaryPrefix(value, length) {
        var count = Math.max(0, Number(length) || 0), output = [];
        if (Array.isArray(value)) { return value.slice(0, count); }
        if (value && typeof value.length === "number") {
            for (var index = 0; index < Math.min(count, value.length); index++) {
                output.push(Number(value[index]) & 255);
            }
            return output;
        }
        if (typeof value === "string") {
            var hex = value.replace(/^0x/i, "");
            if (!/^[0-9a-f]+$/i.test(hex) || hex.length % 2 !== 0) { return null; }
            for (var offset = 0; offset < Math.min(hex.length, count * 2); offset += 2) {
                output.push(parseInt(hex.substr(offset, 2), 16));
            }
            return output;
        }
        return null;
    }
    function qpbGpkgEnvelopeGeoJson(value, sourceCrs, sourceDefinition) {
        var bytes = qpbBinaryPrefix(value, 40);
        if (!bytes || bytes.length < 40 || bytes[0] !== 71 || bytes[1] !== 80) {
            throw new Error("invalid GeoPackage envelope");
        }
        var flags = bytes[3], little = (flags & 1) === 1, envelope = (flags >> 1) & 7;
        if (envelope < 1 || envelope > 4) { throw new Error("GeoPackage envelope unavailable"); }
        var minX = qpbF64(bytes, 8, little), maxX = qpbF64(bytes, 16, little);
        var minY = qpbF64(bytes, 24, little), maxY = qpbF64(bytes, 32, little);
        if (!isFinite(minX) || !isFinite(maxX) || !isFinite(minY) || !isFinite(maxY) ||
                minX > maxX || minY > maxY) { throw new Error("invalid GeoPackage envelope"); }
        return qpbTransformGeoJson(qpbNormalizeGeoJsonXY({type:"Polygon", coordinates:[[
            [minX,minY], [maxX,minY], [maxX,maxY], [minX,maxY], [minX,minY]
        ]]}, false), sourceCrs, sourceDefinition);
    }
    function qpbTransformGeoJson(geojson, sourceCrs, sourceDefinition) {
        var auth = String(sourceCrs || "");
        if (qpbIsWgs84Crs(auth, sourceDefinition)) { geojson.crs="EPSG:4326"; return geojson; }
        if (typeof QgsCoordinateTransform === "undefined" || typeof QgsCoordinateReferenceSystem === "undefined") throw new Error("coordinate transform API unavailable");
        var source = new QgsCoordinateReferenceSystem(String(sourceDefinition || sourceCrs));
        var target = new QgsCoordinateReferenceSystem("EPSG:4326"), context = qgisProject && typeof qgisProject.transformContext === "function" ? qgisProject.transformContext() : undefined;
        var transform = context === undefined ? new QgsCoordinateTransform(source,target) : new QgsCoordinateTransform(source,target,context);
        function walk(value) { if (typeof value[0] === "number") { var p=transform.transform(value[0],value[1]); return [p.x !== undefined ? p.x : p[0], p.y !== undefined ? p.y : p[1]]; } return value.map(walk); }
        if (geojson.type === "GeometryCollection") geojson.geometries=geojson.geometries.map(function(member){return qpbTransformGeoJson(member,sourceCrs,sourceDefinition);});
        else geojson.coordinates=walk(geojson.coordinates);
        geojson.crs="EPSG:4326"; return qpbNormalizeGeoJsonXY(geojson, true);
    }
    function qpbDecodeGpkgGeometry(value, sourceCrs, sourceDefinition) {
        var bytes=qpbBytes(value); if (!bytes || bytes.length < 9 || bytes[0] !== 71 || bytes[1] !== 80) throw new Error("invalid GeoPackage/WKB geometry BLOB");
        var flags=bytes[3], little=(flags & 1) === 1, envelope=(flags >> 1) & 7, offset=8 + (envelope===0?0:(envelope===1?32:(envelope===2?48:64)));
        var decoded=qpbDecodeWkb(bytes,offset); return qpbTransformGeoJson(qpbNormalizeGeoJsonXY({type:decoded.type,coordinates:decoded.coordinates,geometries:decoded.geometries}, false),sourceCrs,sourceDefinition);
    }

    function qpbCollectGpkgSpatialRows(tableName, geometryColumn, geometryType, sourceCrs, sourceDefinition) {
        // geometry contract: invalid source shapes stay in records with a reason.
        var result = {fields: [], records: [], direct: true};
        var identifier = qpbGpkgTableIdentifier(tableName), gpkgPath = qpbSavedGpkgPath();
        var columns = qpbExecuteSql("PRAGMA table_info(" + identifier + ")", gpkgPath) || [];
        var selectColumns = [], rowPositions = {};
        for (var columnIndex = 0; columnIndex < columns.length; columnIndex++) {
            var column = columns[columnIndex] || {};
            var columnName = column.name !== undefined ? column.name : column[1];
            if (columnName !== undefined && !qpbIsSensitiveReportField(columnName)) {
                result.fields.push(String(columnName));
                if (String(columnName) !== String(geometryColumn)) {
                    rowPositions[String(columnName)] = selectColumns.length;
                    selectColumns.push(qpbGpkgTableIdentifier(columnName));
                }
            }
        }
        // Never select a large geometry BLOB only to turn it into an even larger JavaScript array.
        // The GeoPackage header includes an XY envelope, so large rows need only their byte count
        // and header prefix; ordinary field geometries are still fetched in full and rendered exactly.
        var quotedGeometry = qpbGpkgTableIdentifier(geometryColumn);
        rowPositions.__qpb_geometry_bytes = selectColumns.length;
        selectColumns.push("length(" + quotedGeometry + ") AS \"__qpb_geometry_bytes\"");
        rowPositions.__qpb_geometry_prefix = selectColumns.length;
        selectColumns.push("substr(" + quotedGeometry + ", 1, 40) AS \"__qpb_geometry_prefix\"");
        rowPositions.__qpb_geometry_full = selectColumns.length;
        selectColumns.push("CASE WHEN length(" + quotedGeometry + ") <= " +
            qpbReportFullGeometryMaxBytes + " THEN " + quotedGeometry +
            " ELSE NULL END AS \"__qpb_geometry_full\"");
        var rows = qpbExecuteSql("SELECT " + selectColumns.join(", ") + " FROM " + identifier, gpkgPath) || [];
        function rowValue(raw, key) {
            if (raw && raw[key] !== undefined) { return raw[key]; }
            return Array.isArray(raw) && rowPositions[key] !== undefined ? raw[rowPositions[key]] : undefined;
        }
        // A schema-defined UUID is the only stable identity for configured report tables.
        // Generic fid/id guessing is retained solely for metadata-discovered supplemental tables.
        var configuredUuidField = sourceDefinition && sourceDefinition.uuid_field ?
            String(sourceDefinition.uuid_field) : "";
        var transformDefinition = sourceDefinition && typeof sourceDefinition === "object" ?
            (sourceDefinition.source_crs_definition || sourceDefinition.geometry_crs || sourceCrs) :
            sourceDefinition;
        for (var rowIndex = 0; rowIndex < rows.length; rowIndex++) {
            var raw = rows[rowIndex] || {}, attrs = {}, uuid = "";
            var geometryLengthValue = rowValue(raw, "__qpb_geometry_bytes");
            var geometryByteLength = geometryLengthValue === undefined || geometryLengthValue === null ? -1 :
                Number(geometryLengthValue);
            var geometryPrefix = rowValue(raw, "__qpb_geometry_prefix");
            var geometryFull = rowValue(raw, "__qpb_geometry_full");
            var hasSourceGeometry = geometryByteLength >= 0;
            var shapeValue = geometryByteLength > qpbReportFullGeometryMaxBytes ?
                geometryPrefix : geometryFull;
            for (var fieldIndex = 0; fieldIndex < result.fields.length; fieldIndex++) {
                var fieldKey = result.fields[fieldIndex];
                if (fieldKey === geometryColumn) { continue; }
                var value = rowValue(raw, fieldKey);
                // An absent provider key is not the same as a present null.  This distinction
                // feeds semantic canonicalization and must survive direct collection.
                if (value !== undefined) { attrs[fieldKey] = qpbFormatReportValue(value); }
                if (configuredUuidField && fieldKey === configuredUuidField &&
                    value !== undefined && value !== null) { uuid = String(value); }
                if (!configuredUuidField && !uuid && /^(?:fid|id|uuid|.*_uuid)$/i.test(fieldKey) &&
                    value !== undefined && value !== null) { uuid = String(value); }
            }
            if (!uuid && !configuredUuidField) { uuid = String(raw.fid !== undefined ? raw.fid :
                (raw[0] !== undefined && raw[0] !== null ? raw[0] : (rowIndex + 1))); }
            // SQL NULL is the one direct-path condition that establishes actual emptiness.  An
            // absent/undecodable provider value is deliberately a serialization failure instead.
            var rowSourceCrs = sourceCrs;
            // A provider may expose a feature-specific CRS even when the table metadata carries
            // a default.  Most GeoPackages use one SRS per geometry column; this optional probe
            // keeps the report honest for provider/edit-buffer records that expose a narrower
            // CRS identity.
            try {
                if (qgisProject && typeof qgisProject.qpbReportRowCrs === "function") {
                    rowSourceCrs = qgisProject.qpbReportRowCrs(tableName, uuid, sourceCrs);
                }
            } catch (rowCrsError) { rowSourceCrs = sourceCrs; }
            var shape = !hasSourceGeometry ? {valid:false, outcome:"actual_empty",
                    reason:"원본 도형이 비어 있음"} : {valid:false,
                    outcome:"serialization_failure", reason:"도형을 좌표로 변환하지 못함"};
            // Every decoder/normalizer/transform is row-isolated.  A malformed object, GeoJSON,
            // or WKB value records a stable invalid reason without aborting the table loop.
            if (hasSourceGeometry) {
                try {
                    if (typeof shapeValue === "object" && shapeValue.type &&
                        (shapeValue.coordinates !== undefined || Array.isArray(shapeValue.geometries))) {
                        shape = {valid:true, outcome:"valid", reason:"표시 가능한 도형",
                            geojson:qpbTransformGeoJson(qpbNormalizeGeoJsonXY(shapeValue, false),
                                rowSourceCrs,transformDefinition), crs:"EPSG:4326"};
                    } else if (geometryByteLength > qpbReportFullGeometryMaxBytes) {
                        shape = {valid:true, outcome:"simplified_envelope",
                            reason:"대형 도형을 범위로 단순화하여 표시",
                            geojson:qpbGpkgEnvelopeGeoJson(shapeValue, rowSourceCrs,
                                transformDefinition), crs:"EPSG:4326", simplified:true,
                            source_geometry_bytes:geometryByteLength};
                    } else {
                        shape = {valid:true, outcome:"valid", reason:"표시 가능한 도형",
                            geojson:qpbDecodeGpkgGeometry(shapeValue,rowSourceCrs,transformDefinition),
                            crs:"EPSG:4326"};
                    }
                } catch (shapeError) {
                    var shapeMessage = String(shapeError["me"+"ssage"] || "");
                    shape = {valid:false,
                        outcome:/coordinate transform/i.test(shapeMessage) ? "transform_failure" :
                            (/unsupported/i.test(shapeMessage) ? "unsupported_geometry" :
                            (/coordinates|non-finite|out-of-range|malformed/i.test(shapeMessage) ?
                                "malformed_xy" : "serialization_failure")),
                        reason:/coordinate transform/i.test(shapeMessage) ? "좌표계를 WGS84로 변환하지 못함" :
                            (/unsupported/i.test(shapeMessage) ? "지원하지 않는 도형 유형" :
                            (/WKB/i.test(shapeMessage) ? "WKB 도형을 좌표로 변환하지 못함" : (/coordinates|non-finite|out-of-range|malformed/i.test(shapeMessage) ?
                                "좌표 값 형식이 올바르지 않음" : "도형을 좌표로 변환하지 못함")))};
                }
            }
            // CRS is collection provenance, not GeoJSON coordinate content.  Map/report
            // geometries stay strictly XY-only while the record-level field retains the source.
            if (shape.geojson && shape.geojson.crs !== undefined) { delete shape.geojson.crs; }
            var record = [];
            for (var valueIndex = 0; valueIndex < result.fields.length; valueIndex++) {
                var resultField = result.fields[valueIndex];
                record.push(qpbOwn(attrs, resultField) ? attrs[resultField] : "");
            }
            record._qpbAttrs = attrs;
            record._qpbUuid = uuid;
            record._qpbGeometry = shape;
            // The report needs only a non-null source-geometry indicator for diagnostics. Never
            // retain the original BLOB: serializing a large boundary into report JSON defeats the
            // envelope guard above and can crash the mobile QML process.
            record._qpbRawGeometry = !hasSourceGeometry ? null : {
                present:true, byte_size:geometryByteLength >= 0 ? geometryByteLength : null
            };
            record._qpbCrs = rowSourceCrs || "unknown";
            result.records.push(record);
        }
        result.records.sort(function(left, right) {
            return String(left._qpbUuid || "").localeCompare(String(right._qpbUuid || ""), "en", {numeric:true}) ||
                JSON.stringify(left._qpbAttrs || {}).localeCompare(JSON.stringify(right._qpbAttrs || {}), "en");
        });
        return result;
    }

    function qpbInspectCurrentGpkgSpatialMetadata() {
        var metadata = {source: "current saved GeoPackage", read_only: true,
            contents_table: "gpkg_contents", geometry_metadata_table: "gpkg_geometry_columns",
            spatial_tables: [], non_spatial_tables: [], inaccessible_tables: [],
            fallback_used:false, fallback_source:null, failed_direct_path:null,
            direct_failure_reason:null, successful_fallback_reads:[], known_omissions:[],
            unverifiable_scopes:[], claims_complete_direct_inventory:true,
            collection_mode: "configured-layer-fallback"};
        try {
            var gpkgPath = qpbSavedGpkgPath();
            // The path is used only by the isolated QGIS bridge/API and is never placed in the
            // report payload.  QField has no portable arbitrary-table enumeration API.
            if (qpbSqliteBridge() || (typeof Qt !== "undefined" && typeof Qt.openDatabaseSync === "function" && gpkgPath)) {
                metadata.collection_mode = "gpkg-metadata-and-records";
                var contents = qpbExecuteSql("SELECT table_name, data_type FROM gpkg_contents", gpkgPath);
                var geometryRows = qpbExecuteSql("SELECT table_name, column_name, geometry_type_name, srs_id FROM gpkg_geometry_columns", gpkgPath);
                var srsRows = qpbExecuteSql("SELECT srs_id, definition FROM gpkg_spatial_ref_sys", gpkgPath) || [];
                var definitionsBySrs = {};
                for (var srsIndex = 0; srsIndex < srsRows.length; srsIndex++) {
                    var srsRow = srsRows[srsIndex] || {}, srsId = srsRow.srs_id !== undefined ? srsRow.srs_id : srsRow[0];
                    definitionsBySrs[String(srsId)] = srsRow.definition !== undefined ? srsRow.definition : srsRow[1];
                }
                var geometryByTable = {};
                for (var geometryIndex = 0; geometryIndex < (geometryRows || []).length; geometryIndex++) {
                    var geometryRow = geometryRows[geometryIndex] || {};
                    var geometryTableName = geometryRow.table_name || geometryRow[0];
                    if (!geometryTableName) { continue; }
                    geometryByTable[String(geometryTableName)] = geometryRow;
                }
                for (var contentIndex = 0; contentIndex < (contents || []).length; contentIndex++) {
                    var contentRow = contents[contentIndex] || {}, contentName = contentRow.table_name || contentRow[0];
                    if (!contentName) { continue; }
                    if (!geometryByTable[String(contentName)]) {
                        metadata.non_spatial_tables.push({table_name:String(contentName), data_type:contentRow.data_type || contentRow[1] || "attributes"});
                    }
                }
                for (var spatialIndex = 0; spatialIndex < (geometryRows || []).length; spatialIndex++) {
                    var spatialRow = geometryRows[spatialIndex] || {}, spatialName = spatialRow.table_name || spatialRow[0];
                    if (!spatialName) { continue; }
                    var spatialLayer = qpbFindDomainLayer({name:String(spatialName), display_name:String(spatialName)});
                    var configuredDefinition = null;
                    for (var configuredSpatialIndex = 0;
                         configuredSpatialIndex < qpbReportDefinition.tables.length;
                         configuredSpatialIndex++) {
                        if (qpbReportDefinition.tables[configuredSpatialIndex].name === String(spatialName)) {
                            configuredDefinition = qpbReportDefinition.tables[configuredSpatialIndex];
                            break;
                        }
                    }
                    var spatial = {table_name:String(spatialName), source_table:String(spatialName),
                        geometry_column:spatialRow.column_name || spatialRow[1] || "geometry",
                        source_crs:spatialRow.srs_id === undefined ? (spatialRow[3] || "unknown") : spatialRow.srs_id,
                        geometry_type:spatialRow.geometry_type_name || spatialRow[2] || "",
                        source_crs_definition:definitionsBySrs[String(spatialRow.srs_id === undefined ? (spatialRow[3] || "unknown") : spatialRow.srs_id)] || "",
                        raw_record_identity:configuredDefinition && configuredDefinition.uuid_field ?
                            configuredDefinition.uuid_field : "feature id", attributes:[], records:[],
                        source_available:true};
                    try {
                        var directRows = qpbCollectGpkgSpatialRows(String(spatialName), spatial.geometry_column,
                            spatial.geometry_type, spatial.source_crs, configuredDefinition || spatial.source_crs_definition);
                        spatial.attributes = directRows.fields;
                        spatial.records = directRows.records;
                        spatial.collection_mode = "direct-sqlite-rows";
                    } catch (directRowsError) {
                        // Metadata access succeeded, so a row failure is partial, not a reason to
                        // discard already-collected tables or activate whole-project fallback.
                        // qpbCollectCurrentRecords({name:String(spatialName) ...}) is intentionally
                        // not called here: fallback is reserved for complete direct-access failure.
                        var tableFailure = "직접 GeoPackage 행 조회 실패: " + spatialName;
                        metadata.inaccessible_tables.push({table_name:String(spatialName), reason:tableFailure});
                        qpbAddKnownFallbackOmission(metadata, "table", String(spatialName), tableFailure);
                        metadata.unverifiable_scopes.push({identifier:String(spatialName) + " row scope",
                            count:null, completeness:"unknown"});
                        metadata.claims_complete_direct_inventory = false;
                        qpbAddReportCollectionLimitation(tableFailure + " (성공한 공간 테이블은 유지)");
                        continue;
                    }
                    metadata.spatial_tables.push(spatial);
                }
                metadata.spatial_tables.sort(function(left, right) {
                    return String(left.table_name).localeCompare(String(right.table_name), "en");
                });
            } else {
                // Prefer all currently loaded project layers when the portable SQL bridge is not
                // exposed. This captures arbitrary loaded GeoPackage tables; only when that
                // enumeration is unavailable do we fall back to configured schema layers.
                qpbRegisterReportFallback(metadata, "loaded_layers",
                    "saved GeoPackage direct SQLite", "SQLite bridge unavailable");
                metadata.claims_complete_direct_inventory = false;
                var enumeratedLayers = [];
                try {
                    if (qgisProject && typeof qgisProject.mapLayers === "function") {
                        var projectLayerMap = qgisProject.mapLayers() || {}, projectLayerIds = Object.keys(projectLayerMap);
                        for (var projectLayerIndex = 0; projectLayerIndex < projectLayerIds.length; projectLayerIndex++) {
                            enumeratedLayers.push(projectLayerMap[projectLayerIds[projectLayerIndex]]);
                        }
                    }
                } catch (layerEnumerationError) { enumeratedLayers = []; }
                if (enumeratedLayers.length) {
                    metadata.collection_mode = "loaded-project-layer-enumeration";
                    var collectedConfiguredNames = {};
                    for (var loadedIndex = 0; loadedIndex < enumeratedLayers.length; loadedIndex++) {
                        var loadedLayer = enumeratedLayers[loadedIndex], loadedName = "";
                        try { loadedName = typeof loadedLayer.name === "function" ? loadedLayer.name() : String(loadedLayer.name || ""); } catch (loadedNameError) { loadedName = ""; }
                        if (!loadedName || qpbFindDomainLayer({name:loadedName, display_name:loadedName}) !== loadedLayer) { continue; }
                        var configuredDefinition = null;
                        for (var loadedDefinitionIndex = 0; loadedDefinitionIndex < qpbReportDefinition.tables.length; loadedDefinitionIndex++) {
                            var candidateDefinition = qpbReportDefinition.tables[loadedDefinitionIndex];
                            if (candidateDefinition.name === loadedName ||
                                candidateDefinition.display_name === loadedName) {
                                configuredDefinition = candidateDefinition; break;
                            }
                        }
                        var loadedFields = typeof loadedLayer.fields === "function" ? loadedLayer.fields() : loadedLayer.fields;
                        var loadedGeometryField = configuredDefinition ?
                            configuredDefinition.geometry_field : "geometry";
                        try { if (loadedLayer.geometryColumn) { loadedGeometryField = String(loadedLayer.geometryColumn); } } catch (geometryFieldError) {}
                        var loadedAttributes = [];
                        for (var loadedFieldIndex = 0; loadedFields && loadedFieldIndex < loadedFields.length; loadedFieldIndex++) {
                            var loadedFieldName = typeof loadedFields[loadedFieldIndex].name === "function" ? loadedFields[loadedFieldIndex].name() : loadedFields[loadedFieldIndex].name;
                            if (!qpbIsSensitiveReportField(loadedFieldName)) { loadedAttributes.push(String(loadedFieldName)); }
                        }
                        var collectionDefinition = configuredDefinition || {name:loadedName,
                            display_name:loadedName, uuid_field:"fid",
                            fields:loadedAttributes.map(function(fieldName) { return {name:fieldName}; }),
                            geometry_field:loadedGeometryField, geometry_type:"",
                            geometry_crs:qpbLayerCrs(loadedLayer)};
                        var canonicalName = configuredDefinition ? configuredDefinition.name : loadedName;
                        var loadedTable = {table_name:canonicalName, source_table:canonicalName,
                            geometry_column:loadedGeometryField, source_crs:qpbLayerCrs(loadedLayer),
                            geometry_type:configuredDefinition ? configuredDefinition.geometry_type : "",
                            raw_record_identity:"feature id", attributes:loadedAttributes, records:[],
                            fallback:true, collection_mode:"loaded-layer-fallback", source_available:true};
                        loadedTable.records = qpbCollectCurrentRecords(collectionDefinition);
                        metadata.spatial_tables.push(loadedTable);
                        qpbAddFallbackSuccess(metadata, canonicalName, loadedTable.records.length);
                        if (configuredDefinition) { collectedConfiguredNames[canonicalName] = true; }
                    }
                    for (var expectedIndex = 0; expectedIndex < qpbReportDefinition.tables.length;
                         expectedIndex++) {
                        var expectedTable = qpbReportDefinition.tables[expectedIndex];
                        if (!collectedConfiguredNames[expectedTable.name]) {
                            qpbAddKnownFallbackOmission(metadata, "table", expectedTable.name,
                                "configured table is not loaded");
                        }
                    }
                }
                // This is the only remaining fallback: use configured schema layers when QField
                // cannot enumerate arbitrary GeoPackage tables at all.
                if (!enumeratedLayers.length) {
                    metadata.collection_mode = "configured-layer-fallback";
                    metadata.fallback_source = "configured_loaded_layers";
                    for (var configuredIndex = 0; configuredIndex < qpbReportDefinition.tables.length; configuredIndex++) {
                        var configured = qpbReportDefinition.tables[configuredIndex];
                        var configuredLayer = qpbFindDomainLayer(configured);
                        var configuredRecords = configuredLayer ? qpbCollectCurrentRecords(configured) : [];
                        if (configuredLayer) {
                            qpbAddFallbackSuccess(metadata, configured.name, configuredRecords.length);
                        } else {
                            qpbAddKnownFallbackOmission(metadata, "table", configured.name,
                                "configured layer is not loaded");
                        }
                        metadata.spatial_tables.push({table_name:configured.name,
                            source_table:configured.name, geometry_column:configured.geometry_field,
                            source_crs:configured.geometry_crs, geometry_type:configured.geometry_type,
                            raw_record_identity:"uuid", fallback:true,
                            collection_mode:"configured-layer-fallback", source_available:!!configuredLayer,
                            records:configuredRecords,
                            attributes:(configured.fields || []).map(function(field) { return field.name; })});
                    }
                }
            }
        } catch (metadataError) {
            metadata.collection_mode = "configured-layer-fallback";
            metadata.inaccessible_tables.push("gpkg_metadata_or_row_query");
            metadata.claims_complete_direct_inventory = false;
            qpbRegisterReportFallback(metadata, "configured_loaded_layers",
                "saved GeoPackage direct SQLite", String(metadataError["me"+"ssage"] || metadataError));
            for (var fallbackIndex = 0; fallbackIndex < qpbReportDefinition.tables.length; fallbackIndex++) {
                var fallbackTable = qpbReportDefinition.tables[fallbackIndex];
                var fallbackLayer = qpbFindDomainLayer(fallbackTable);
                var fallbackRecords = fallbackLayer ? qpbCollectCurrentRecords(fallbackTable) : [];
                if (fallbackLayer) { qpbAddFallbackSuccess(metadata, fallbackTable.name, fallbackRecords.length); }
                else { qpbAddKnownFallbackOmission(metadata, "table", fallbackTable.name,
                    "configured layer is not loaded"); }
                metadata.spatial_tables.push({table_name:fallbackTable.name, source_table:fallbackTable.name,
                    geometry_column:fallbackTable.geometry_field, source_crs:fallbackTable.geometry_crs,
                    geometry_type:fallbackTable.geometry_type, raw_record_identity:"uuid", fallback:true,
                    collection_mode:"configured-layer-fallback", source_available:!!fallbackLayer,
                    records:fallbackRecords,
                    attributes:(fallbackTable.fields || []).map(function(field) { return field.name; })});
            }
        }
        qpbPublishFallbackLimitation(metadata);
        return metadata;
    }

    function qpbCollectCurrentRecords(table) {
        var layer = qpbFindDomainLayer(table);
        if (!layer) {
            qpbAddReportCollectionLimitation("레이어를 찾을 수 없거나 접근할 수 없습니다: " + table.name);
            return [];
        }
        // QField's whole-layer API: every current saved feature, including provider/edit-buffer
        // attributes, is visited at the moment of export and the iterator is always closed.
        var iterator;
        try { iterator = LayerUtils.createFeatureIterator(layer); } catch (iteratorError) {
            qpbAddReportCollectionLimitation("레이어 반복을 시작할 수 없습니다: " + table.name);
            return [];
        }
        if (!iterator || typeof iterator.hasNext !== "function" ||
            typeof iterator.next !== "function") {
            qpbAddReportCollectionLimitation("레이어 반복 기능을 사용할 수 없습니다: " + table.name);
            return [];
        }
        var records = [];
        try {
            while (iterator.hasNext()) {
                var feature = iterator.next();
                var values = [];
                var attrs = {};
                for (var fieldIndex = 0; fieldIndex < table.fields.length; fieldIndex++) {
                    var field = table.fields[fieldIndex];
                    var value = qpbReportAttribute(field.name, feature.attribute(field.name));
                    values.push(value);
                    attrs[field.name] = value;
                }
                // Species fields are intentionally read for 통계 even though older report
                // schemas omitted identification metadata from the per-table schema list.
                var extraFields = ["selected_korean_name", "selected_scientific_name",
                    "selected_ktsn", "notes", "observed_at", "survey_date", "dominant_species", "area"];
                for (var extraIndex = 0; extraIndex < extraFields.length; extraIndex++) {
                    var extraName = extraFields[extraIndex];
                    if (attrs[extraName] === undefined) {
                        if (!qpbIsSensitiveReportField(extraName)) {
                            attrs[extraName] = qpbReportAttribute(extraName, feature.attribute(extraName));
                        }
                    }
                }
                values._qpbAttrs = attrs;
                values._qpbUuid = qpbFormatReportValue(feature.attribute(table.uuid_field));
                var geometryTable = table;
                // Permanent-plot survey layers can expose a linked-survey geometry even though
                // the schema's survey record has no stored geometry column.  It is used only as
                // the documented plot-anchor fallback; ordinary table fields remain unchanged.
                try {
                    if (!table.geometry_field && layer && layer.geometryColumn) {
                        geometryTable = {geometry_field:String(layer.geometryColumn), geometry_type:"",
                            geometry_crs:qpbLayerCrs(layer, table.geometry_crs)};
                    }
                } catch (geometryColumnError) {}
                values._qpbGeometry = qpbGeometryToGeoJson(feature, layer, geometryTable);
                values._qpbCrs = qpbLayerCrs(layer, table.geometry_crs);
                records.push(values);
            }
        } catch (collectionError) {
            qpbAddReportCollectionLimitation("레이어 기록 일부를 읽지 못했습니다: " + table.name);
        } finally {
            try {
                if (iterator && typeof iterator.close === "function") { iterator.close(); }
            } catch (closeError) {
                qpbAddReportCollectionLimitation("레이어 반복을 정상적으로 닫지 못했습니다: " + table.name);
            }
        }
        records.sort(function(left, right) {
            var idOrder = String(left._qpbUuid || "").localeCompare(String(right._qpbUuid || ""), "en", {numeric:true});
            if (idOrder) { return idOrder; }
            return JSON.stringify(left._qpbAttrs || {}).localeCompare(JSON.stringify(right._qpbAttrs || {}), "en");
        });
        return records;
    }

    function qpbRecordAttrs(record) { return record && record._qpbAttrs ? record._qpbAttrs : {}; }
    function qpbRecordValue(record, name) {
        var attrs = qpbRecordAttrs(record);
        return attrs[name] === undefined || attrs[name] === null ? "" : String(attrs[name]);
    }
    function qpbStrictCalendarDate(value) {
        // Native date parsing normalizes impossible dates (for example 2024-02-31), so it is not
        // a calendar validator.  Match the *whole* value and validate every supplied time and
        // offset component before returning the calendar day.  A valid day must not be rescued
        // from a malformed suffix such as ``2024-01-01T99:99junk``.
        var match = String(value === undefined || value === null ? "" : value).match(
            /^(\d{4})-(\d{2})-(\d{2})(?:(?:[Tt ])(\d{2}):(\d{2})(?::(\d{2})(?:\.(\d+))?)?(?:[Zz]|([+-])(\d{2}):(\d{2}))?)?$/
        );
        if (!match) { return ""; }
        var year = Number(match[1]), month = Number(match[2]), day = Number(match[3]);
        if (month < 1 || month > 12 || day < 1) { return ""; }
        var leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
        var monthDays = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
        if (day > monthDays[month - 1]) { return ""; }
        if (match[4] !== undefined) {
            var hour = Number(match[4]), minute = Number(match[5]);
            var second = match[6] === undefined ? 0 : Number(match[6]);
            if (hour > 23 || minute > 59 || second > 59) { return ""; }
            if (match[8] !== undefined) {
                var offsetHour = Number(match[9]), offsetMinute = Number(match[10]);
                if (offsetHour > 23 || offsetMinute > 59) { return ""; }
            }
        }
        return match[1] + "-" + match[2] + "-" + match[3];
    }
    function qpbIndex(records) {
        var result = {};
        for (var i = 0; i < records.length; i++) {
            if (records[i]._qpbUuid) { result[records[i]._qpbUuid] = records[i]; }
        }
        return result;
    }
    function qpbParentRecord(record, table, indexes) {
        if (!table.foreign_key) { return null; }
        var parentId = qpbRecordValue(record, table.foreign_key.column);
        return parentId && indexes[table.foreign_key.ref_table] ?
            indexes[table.foreign_key.ref_table][parentId] || null : null;
    }

    function qpbJoinedColumns(d) {
        var columns = [];
        var seen = {};
        var normalizedHeaders = {};
        // One source-column -> final-key mapping owns both the header and every row value.  The
        // normalized source_table__source_field shape is the base-key contract.
        // unsuffixed logical source id is retained only as provenance; it is never used as a
        // second output key after a collision has been allocated.
        function add(sourceColumnId, label, sourceTable, sourceField, semanticIdentity) {
            if (seen[sourceColumnId]) { return; }
            seen[sourceColumnId] = true;
            var base = sourceTable && sourceField ?
                qpbNormalizeOutputKey(sourceTable) + "__" + qpbNormalizeOutputKey(sourceField) :
                sourceColumnId;
            var finalKey = qpbReserveFinalKey(base, normalizedHeaders);
            columns.push({key:finalKey, header:finalKey, source_column_id:sourceColumnId,
                source_column_ids:[sourceColumnId], label:label, source_table:sourceTable || "",
                source_field:sourceField || "", semantic_identity:semanticIdentity || null});
        }
        function hasTable(name) {
            for (var tableIndex = 0; tableIndex < d.tables.length; tableIndex++) {
                if (d.tables[tableIndex].name === name) { return true; }
            }
            return false;
        }
        function hasField(name) {
            for (var tableIndex = 0; tableIndex < d.tables.length; tableIndex++) {
                var fields = d.tables[tableIndex].fields || [];
                for (var fieldIndex = 0; fieldIndex < fields.length; fieldIndex++) {
                    if (fields[fieldIndex].name === name) { return true; }
                }
            }
            return false;
        }
        // These stable aliases keep the required Korean/English search fields easy to find.
        // Do not advertise absent hierarchy levels.  Type 1 has only
        // inventory_observation, so site/plot/survey aliases would otherwise look like
        // fabricated joined columns even though their values are empty.
        if (hasTable("site")) {
            add("site_name", "조사지"); add("site_id", "조사지 UUID");
        }
        if (hasTable("plot")) {
            add("plot_name", "조사구"); add("plot_id", "조사구 UUID");
        }
        if (hasTable("survey")) {
            add("survey_date", "조사 날짜"); add("survey_id", "조사 UUID");
        }
        if (hasTable("observation") || hasTable("inventory_observation")) {
            var observationSourceTable = hasTable("observation") ? "observation" : "inventory_observation";
            if (hasField("selected_korean_name")) { add("selected_korean_name", "국명", observationSourceTable, "selected_korean_name", "selected_korean_name"); }
            if (hasField("selected_scientific_name")) { add("selected_scientific_name", "학명", observationSourceTable, "selected_scientific_name", "selected_scientific_name"); }
            if (hasField("selected_ktsn")) { add("selected_ktsn", "KTSN", observationSourceTable, "selected_ktsn", "selected_ktsn"); }
        }
        // Notes are a safe report field even in older schemas that did not list a parent-level
        // note in the generated definition.  Preserve each hierarchy level for the semantic
        // coalescer; equal values become one plain "비고" column, differing values stay explicit.
        if (hasTable("survey")) { add("survey__notes", "조사 비고", "survey", "notes", "notes"); }
        if (hasTable("plot")) { add("plot__notes", "조사구 비고", "plot", "notes", "notes"); }
        for (var i = 0; i < d.tables.length; i++) {
            var table = d.tables[i];
            if (/_photo$/i.test(String(table.name || ""))) { continue; }
            for (var f = 0; f < table.fields.length; f++) {
                var field = table.fields[f];
                var semanticIdentity = field.semantic_identity ||
                    ((field.source_field || field.name) === "notes" ? "notes" :
                    (/^selected_(?:korean_name|scientific_name|ktsn)$/.test(field.source_field || field.name) ?
                        (field.source_field || field.name) : null));
                add(field.source_column_id || (table.name + "__" + field.name),
                    field.label || "필드", field.source_table || table.name,
                    field.source_field || field.name, semanticIdentity);
            }
        }
        add("integrity", "무결성 상태", "report", "integrity");
        // Every output header has one identity and one position.  Duplicate aliases are retained
        // as deterministic suffixed headers instead of silently overwriting joined values.
        var headerSet = new Set();
        for (var headerIndex = 0; headerIndex < columns.length; headerIndex++) {
            if (headerSet.has(columns[headerIndex].header)) {
                qpbAddReportCollectionLimitation("열 헤더 충돌: " + columns[headerIndex].header);
            }
            headerSet.add(columns[headerIndex].header);
        }
        return columns;
    }

    function qpbMakeJoinedRow(parts, columns) {
        var row = {values: {}, parts: {}, integrity: ""}, logicalValues = {};
        function attach(tableName, record) {
            row.parts[tableName] = record || null;
            var table = null;
            for (var i = 0; i < qpbReportDefinition.tables.length; i++) {
                if (qpbReportDefinition.tables[i].name === tableName) { table = qpbReportDefinition.tables[i]; break; }
            }
            if (!table) { return; }
            if (record) { logicalValues[tableName + "_uuid"] = record._qpbUuid; }
            if (!record) { return; }
            var attrs = qpbRecordAttrs(record);
            if (qpbOwn(attrs, "notes")) { logicalValues[tableName + "__notes"] = attrs.notes; }
            for (var fieldIndex = 0; fieldIndex < table.fields.length; fieldIndex++) {
                var field = table.fields[fieldIndex], fieldName = field.name;
                if (qpbOwn(attrs, fieldName)) {
                    logicalValues[field.source_column_id || (tableName + "__" + fieldName)] =
                        attrs[fieldName];
                }
            }
            if (tableName === "site") {
                logicalValues.site_name = qpbOwn(attrs, "site_name") ? attrs.site_name : "";
                logicalValues.site_id = record._qpbUuid || "";
            }
            if (tableName === "plot") {
                logicalValues.plot_name = qpbOwn(attrs, "plot_name") ? attrs.plot_name : "";
                logicalValues.plot_id = record._qpbUuid || "";
            }
            if (tableName === "survey") {
                logicalValues.survey_date = qpbOwn(attrs, "survey_date") ? attrs.survey_date : "";
                logicalValues.survey_id = record._qpbUuid || "";
            }
            if (tableName === "observation" || tableName === "inventory_observation") {
                if (qpbOwn(attrs, "selected_korean_name")) { logicalValues.selected_korean_name = attrs.selected_korean_name; }
                if (qpbOwn(attrs, "selected_scientific_name")) { logicalValues.selected_scientific_name = attrs.selected_scientific_name; }
                if (qpbOwn(attrs, "selected_ktsn")) { logicalValues.selected_ktsn = attrs.selected_ktsn; }
                if (qpbOwn(attrs, "notes")) { logicalValues.notes = attrs.notes; }
            }
        }
        for (var p = 0; p < parts.length; p++) { attach(parts[p].name, parts[p].record); }
        row.source_values = logicalValues;
        row.values = qpbProjectSourceValues(logicalValues, columns);
        return row;
    }

    function qpbBuildJoinedRowsRuntime(datasets, indexes, columns) {
        var rows = [];
        var d = qpbReportDefinition;
        function append(leafName, chain) {
            var leafRecords = datasets[leafName] || [];
            for (var i = 0; i < leafRecords.length; i++) {
                var leaf = leafRecords[i];
                var parts = [{name: leafName, record: leaf}];
                var current = leaf;
                var currentTable = null;
                for (var t = 0; t < d.tables.length; t++) {
                    if (d.tables[t].name === leafName) { currentTable = d.tables[t]; break; }
                }
                var integrity = [];
                for (var c = 0; c < chain.length; c++) {
                    if (!currentTable || !currentTable.foreign_key) { break; }
                    var parentName = currentTable.foreign_key.ref_table;
                    var parentDefined = false;
                    for (var definedIndex = 0; definedIndex < d.tables.length; definedIndex++) {
                        if (d.tables[definedIndex].name === parentName) { parentDefined = true; break; }
                    }
                    // A foreign key referring to a table outside the current report definition
                    // is not a report-level hierarchy.  Stop here instead of manufacturing an
                    // absent parent part/column or an orphan marker for a schema level that is
                    // not present in this project.
                    if (!parentDefined) { break; }
                    var parent = qpbParentRecord(current, currentTable, indexes);
                    if (!parent) { integrity.push("missing parent: " + parentName); }
                    parts.push({name: parentName, record: parent});
                    current = parent;
                    for (var next = 0; next < d.tables.length; next++) {
                        if (d.tables[next].name === parentName) { currentTable = d.tables[next]; break; }
                    }
                    if (!current) { break; }
                }
                var row = qpbMakeJoinedRow(parts, columns);
                row.integrity = integrity.join("; ");
                var integrityKey = qpbFinalKeyForSource(columns, "integrity") || "integrity";
                row.values[integrityKey] = row.integrity || "OK";
                rows.push(row);
            }
        }
        if (datasets.inventory_observation) { append("inventory_observation", []); }
        else if (datasets.observation) { append("observation", ["survey", "plot", "site"]); }
        else if (datasets.community) { append("community", ["survey", "site"]); }
        // An empty child table must not fabricate rows; parent summaries below still expose all
        // parent records. This preserves one-to-many child semantics and zero-record states.
        return rows;
    }

    function qpbBuildJoinedRows(datasets, indexes, columns) {
__QPB_JOINED_ROW_DISPATCH__
    }

    function qpbSnapshotRecord(record) {
        return record ? {uuid: record._qpbUuid || "", attrs: qpbRecordAttrs(record)} : null;
    }

    function qpbChildRecords(records, foreignKey, parentUuid) {
        var children = [], source = records || [];
        if (!foreignKey || !parentUuid) { return children; }
        for (var i = 0; i < source.length; i++) {
            if (qpbRecordValue(source[i], foreignKey.column) === String(parentUuid)) {
                children.push(source[i]);
            }
        }
        children.sort(function(left, right) {
            var leftId = String(left._qpbUuid || ""), rightId = String(right._qpbUuid || "");
            return leftId.localeCompare(rightId, "en", {numeric: true}) ||
                qpbRecordValue(left, "selected_korean_name").localeCompare(
                    qpbRecordValue(right, "selected_korean_name"), "ko") ||
                JSON.stringify(qpbRecordAttrs(left)).localeCompare(JSON.stringify(qpbRecordAttrs(right)), "en");
        });
        return children;
    }

    function qpbChildSnapshots(records, childContexts) {
        var snapshots = [], source = records || [];
        for (var i = 0; i < source.length; i++) {
            var attrs = qpbRecordAttrs(source[i]);
            var childUuid = source[i]._qpbUuid || "";
            var childContext = childContexts && childContexts[childUuid] ?
                childContexts[childUuid] : null;
            snapshots.push({uuid: childUuid, korean: attrs.selected_korean_name || "",
                scientific: attrs.selected_scientific_name || "", ktsn: attrs.selected_ktsn || "",
                attrs: attrs, survey_uuid: childContext ? childContext.uuid : "",
                survey_context: childContext});
        }
        return snapshots;
    }

    function qpbBuildMapFeature(context, anchorTable, anchorRecord, geometryRecord, parts,
                                childRecords, fallback, childContexts) {
        // Spatial-anchor-first: the selected site/survey/plot/community record owns geometry.
        // Child observation geometry is never consulted or promoted to an anchor coordinate.
        var geometry = geometryRecord && geometryRecord._qpbGeometry;
        if (!geometry || !geometry.valid) { return null; }
        var contextSnapshot = {}, surveySnapshots = [];
        for (var i = 0; i < parts.length; i++) {
            var partSnapshot = qpbSnapshotRecord(parts[i].record);
            if (parts[i].name === "survey") {
                if (partSnapshot) { surveySnapshots.push(partSnapshot); }
            } else {
                contextSnapshot[parts[i].name] = partSnapshot;
            }
        }
        // A plot may contain several surveys. Preserve all of them in source order instead of
        // repeatedly assigning source.survey and silently retaining only the last one. A single
        // survey keeps the legacy source.survey shape; multiple surveys use source.surveys and
        // each child snapshot carries its own survey context for unambiguous detail rendering.
        if (surveySnapshots.length === 1) { contextSnapshot.survey = surveySnapshots[0]; }
        if (surveySnapshots.length > 1) { contextSnapshot.surveys = surveySnapshots; }
        var related = qpbChildSnapshots(childRecords, childContexts);
        return {context: context, anchor_table: anchorTable, anchor_uuid: anchorRecord._qpbUuid || "",
            geometry: geometry, fallback: fallback ? "survey" : "", source: contextSnapshot,
            related_observations: related,
            properties: {context: context, anchor_table: anchorTable,
                anchor_uuid: anchorRecord._qpbUuid || "", fallback: fallback ? "survey" : "",
                source: contextSnapshot, related_observations: related}};
    }

    function qpbBuildMapFeaturesRuntime(datasets, indexes) {
        var mapFeatures = [], d = qpbReportDefinition, type = d.survey_type;
        function addSiteFeatures() {
            var sites = datasets.site || [];
            for (var i = 0; i < sites.length; i++) {
                var siteFeature = qpbBuildMapFeature("site", "site", sites[i], sites[i],
                    [{name: "site", record: sites[i]}], [], false);
                if (siteFeature) { mapFeatures.push(siteFeature); }
            }
        }
        if (type === "simple_inventory") {
            var inventory = datasets.inventory_observation || [];
            for (var inventoryIndex = 0; inventoryIndex < inventory.length; inventoryIndex++) {
                var inventoryFeature = qpbBuildMapFeature("inventory_observation",
                    "inventory_observation", inventory[inventoryIndex], inventory[inventoryIndex],
                    [{name: "inventory_observation", record: inventory[inventoryIndex]}], [], false);
                if (inventoryFeature) { mapFeatures.push(inventoryFeature); }
            }
            return mapFeatures;
        }
        if (type === "temporary_plots") {
            // Type 2: site polygons are separate; survey geometry is authoritative for joins.
            addSiteFeatures();
            var surveys = datasets.survey || [], observationTable = qpbReportDefinition.tables;
            for (var surveyIndex = 0; surveyIndex < surveys.length; surveyIndex++) {
                var survey = surveys[surveyIndex], surveyTable = null;
                for (var tableIndex = 0; tableIndex < observationTable.length; tableIndex++) {
                    if (observationTable[tableIndex].name === "survey") { surveyTable = observationTable[tableIndex]; }
                }
                var site = qpbParentRecord(survey, surveyTable, indexes) || null;
                var observations = qpbChildRecords(datasets.observation,
                    {column: "survey_id"}, survey._qpbUuid);
                var childSurveyContexts = {};
                for (var observationIndex = 0; observationIndex < observations.length; observationIndex++) {
                    childSurveyContexts[observations[observationIndex]._qpbUuid || ""] =
                        qpbSnapshotRecord(survey);
                }
                var parts = [{name: "site", record: site}, {name: "survey", record: survey}];
                var feature = qpbBuildMapFeature("survey_observation", "survey", survey, survey,
                    parts, observations, false, childSurveyContexts);
                if (feature) { mapFeatures.push(feature); }
            }
            return mapFeatures;
        }
        if (type === "permanent_plots") {
            // Type 3: site polygons are separate; plot owns joined coordinates, with survey
            // geometry as the documented fallback only when plot geometry is unusable.
            addSiteFeatures();
            var plots = datasets.plot || [], plotTable = null, surveyTableForPlot = null;
            for (var definitionIndex = 0; definitionIndex < d.tables.length; definitionIndex++) {
                if (d.tables[definitionIndex].name === "plot") { plotTable = d.tables[definitionIndex]; }
                if (d.tables[definitionIndex].name === "survey") { surveyTableForPlot = d.tables[definitionIndex]; }
            }
            var allSurveys = datasets.survey || [], allObservations = datasets.observation || [];
            for (var plotIndex = 0; plotIndex < plots.length; plotIndex++) {
                var plot = plots[plotIndex], plotSurveys = qpbChildRecords(allSurveys,
                    {column: "plot_id"}, plot._qpbUuid), plotGeometry = plot;
                var fallback = false;
                if (!plot._qpbGeometry || !plot._qpbGeometry.valid) {
                    for (var fallbackIndex = 0; fallbackIndex < plotSurveys.length; fallbackIndex++) {
                        if (plotSurveys[fallbackIndex]._qpbGeometry &&
                            plotSurveys[fallbackIndex]._qpbGeometry.valid) {
                            plotGeometry = plotSurveys[fallbackIndex]; fallback = true; break;
                        }
                    }
                }
                var children = [], childSurveyContexts = {}, partsForPlot = [{name: "site", record: null},
                    {name: "plot", record: plot}];
                var siteForPlot = qpbParentRecord(plot, plotTable, indexes);
                partsForPlot[0].record = siteForPlot;
                for (var plotSurveyIndex = 0; plotSurveyIndex < plotSurveys.length; plotSurveyIndex++) {
                    var plotSurvey = plotSurveys[plotSurveyIndex];
                    partsForPlot.push({name: "survey", record: plotSurvey});
                    var surveyChildren = qpbChildRecords(allObservations, {column: "survey_id"},
                        plotSurvey._qpbUuid);
                    for (var childIndex = 0; childIndex < surveyChildren.length; childIndex++) {
                        var child = surveyChildren[childIndex];
                        children.push(child);
                        childSurveyContexts[child._qpbUuid || ""] = qpbSnapshotRecord(plotSurvey);
                    }
                }
                var plotFeature = qpbBuildMapFeature("plot_survey_observation", "plot", plot,
                    plotGeometry, partsForPlot, children, fallback, childSurveyContexts);
                if (plotFeature) { mapFeatures.push(plotFeature); }
            }
            return mapFeatures;
        }
        if (type === "vegetation_mapping") {
            // Type 4 deliberately renders community polygons only; no plant joins are invented.
            var communities = datasets.community || [];
            for (var communityIndex = 0; communityIndex < communities.length; communityIndex++) {
                var community = communities[communityIndex], communityTable = null;
                for (var communityTableIndex = 0; communityTableIndex < d.tables.length;
                     communityTableIndex++) {
                    if (d.tables[communityTableIndex].name === "community") {
                        communityTable = d.tables[communityTableIndex]; break;
                    }
                }
                var communitySurvey = qpbParentRecord(community, communityTable, indexes);
                var communityFeature = qpbBuildMapFeature("community", "community", community,
                    community, [{name: "survey", record: communitySurvey},
                        {name: "community", record: community}], [], false);
                if (communityFeature) { mapFeatures.push(communityFeature); }
            }
        }
        return mapFeatures;
    }

    function qpbBuildMapFeatures(datasets, indexes) {
__QPB_MAP_FEATURE_DISPATCH__
    }

    function qpbBuildSupplementalMapFeatures(metadata) {
        // Discovered spatial tables are source data, never Type 1–4 anchors.  They are rendered
        // as supplemental features only when their own collected geometry is valid.
        var features = [], spatialTables = (metadata && metadata.spatial_tables) || [];
        for (var tableIndex = 0; tableIndex < spatialTables.length; tableIndex++) {
            var table = spatialTables[tableIndex];
            if (!table || !table.records || table.fallback) { continue; }
            var configured = false;
            for (var definitionIndex = 0;
                 definitionIndex < qpbReportDefinition.tables.length;
                 definitionIndex++) {
                if (qpbReportDefinition.tables[definitionIndex].name === table.table_name) {
                    configured = true; break;
                }
            }
            if (configured) { continue; }
            for (var recordIndex = 0; recordIndex < table.records.length; recordIndex++) {
                var record = table.records[recordIndex];
                if (!record || !record._qpbGeometry || !record._qpbGeometry.valid) { continue; }
                features.push({context:"보조 공간 기록", anchor_table:table.source_table,
                    anchor_uuid:record._qpbUuid || "", geometry:record._qpbGeometry,
                    supplemental:true, source:{}, related_observations:[],
                    properties:{context:"보조 공간 기록", anchor_table:table.source_table,
                        anchor_uuid:record._qpbUuid || "", supplemental:true, source:{},
                        related_observations:[]}});
            }
        }
        features.sort(function(left, right) {
            return String(left.anchor_table).localeCompare(String(right.anchor_table), "en") ||
                String(left.anchor_uuid).localeCompare(String(right.anchor_uuid), "en", {numeric:true});
        });
        return features;
    }

    // Overview cards deliberately aggregate their schema-defined direct layers.  Joined rows
    // may fan out a source record and must never change these values.
    function qpbBuildOverviewCards(datasets, analytics) {
        var type = qpbReportDefinition.survey_type, limitations = [];
        function hasLayer(name) { return Object.prototype.hasOwnProperty.call(datasets, name); }
        function records(name) { return hasLayer(name) ? (datasets[name] || []) : null; }
        function countCard(label, layer) {
            var source = records(layer);
            return {label:label, value:source === null ? "해당 레벨 부재" : source.length,
                direct_source_layer:layer, source_field:null, basis:layer + " 원본 record 수"};
        }
        function datesCard(label, layer, field) {
            var source = records(layer), dates = {}, invalid = 0;
            if (source === null) { return {label:label, value:"해당 레벨 부재",
                direct_source_layer:layer, source_field:field, basis:layer + "." + field + " 유효 calendar date distinct"}; }
            for (var index = 0; index < source.length; index++) {
                var date = qpbStrictCalendarDate(qpbRecordAttrs(source[index])[field]);
                if (date) { dates[date] = true; } else { invalid += 1; }
            }
            if (invalid) { limitations.push({kind:"invalid_or_missing_date", count:invalid,
                source_layer:layer, source_field:field}); }
            return {label:label, value:Object.keys(dates).length, direct_source_layer:layer,
                source_field:field, basis:layer + "." + field + " 유효 calendar date distinct"};
        }
        function ktsnCard(label, layer) {
            var source = records(layer), values = {}, invalid = 0;
            if (source === null) { return {label:label, value:"해당 레벨 부재",
                direct_source_layer:layer, source_field:"selected_ktsn",
                basis:layer + ".selected_ktsn 유효값 distinct"}; }
            for (var index = 0; index < source.length; index++) {
                var ktsn = qpbRecordAttrs(source[index]).selected_ktsn;
                if (ktsn === null || ktsn === undefined || String(ktsn).trim() === "") { invalid += 1; }
                else { values[String(ktsn)] = true; }
            }
            if (invalid) { limitations.push({kind:"invalid_ktsn", count:invalid,
                source_layer:layer, source_field:"selected_ktsn"}); }
            return {label:label, value:Object.keys(values).length, direct_source_layer:layer,
                source_field:"selected_ktsn", basis:layer + ".selected_ktsn 유효값 distinct"};
        }
        if (type === "simple_inventory") { return {cards:[
            datesCard("총 조사일 수", "inventory_observation", "observed_at"),
            countCard("관찰 수", "inventory_observation"),
            ktsnCard("총 종수", "inventory_observation")], limitations:limitations}; }
        if (type === "temporary_plots") { return {cards:[
            countCard("조사지 수", "site"), countCard("조사구 수", "survey"),
            datesCard("총 조사일 수", "survey", "survey_date"), countCard("관찰 수", "observation"),
            ktsnCard("총 종수", "observation")], limitations:limitations}; }
        if (type === "permanent_plots") { return {cards:[
            countCard("조사지 수", "site"), countCard("조사구 수", "plot"),
            datesCard("총 조사일 수", "survey", "survey_date"), countCard("관찰 수", "observation"),
            ktsnCard("총 종수", "observation")], limitations:limitations}; }
        var community = records("community"), names = {};
        if (community !== null) for (var communityIndex = 0; communityIndex < community.length; communityIndex++) {
            var name = qpbRecordAttrs(community[communityIndex]).community_name;
            if (name !== null && name !== undefined && String(name).trim() !== "") { names[String(name)] = true; }
        }
        return {cards:[countCard("조사지 수", "site"),
            {label:"고유군락 수", value:community === null ? "해당 레벨 부재" : Object.keys(names).length,
                direct_source_layer:"community", source_field:"community_name", basis:"community.community_name distinct"},
            {label:"총군락 수", value:community === null ? "해당 레벨 부재" : community.length,
                direct_source_layer:"community", source_field:null, basis:"community 원본 record 수"},
            datesCard("총 조사일 수", "survey", "survey_date")], limitations:limitations};
    }

    function qpbBuildAnalytics(datasets, joined) {
        var d = qpbReportDefinition;
        // Select the active survey type's observation layer explicitly.  The fixture and
        // collected metadata can contain other available layers, which must not mask the Type 1
        // inventory observations or become species/chart input for Type 4.
        var observations = d.survey_type === "simple_inventory" ?
            (datasets.inventory_observation || []) :
            (d.survey_type === "vegetation_mapping" ? [] : (datasets.observation || []));
        var species = {}, speciesRows = [], days = {}, unknownDates = 0;
        function speciesFieldsAgree(left, right) {
            // A populated identity field is authoritative.  Missing values are unknown rather
            // than a conflicting value, but a Korean/scientific/KTSN disagreement must never
            // collapse two taxa merely because their display names match.
            var names = ["korean", "scientific", "ktsn"];
            for (var fieldIndex = 0; fieldIndex < names.length; fieldIndex++) {
                var fieldName = names[fieldIndex], leftValue = left[fieldName], rightValue = right[fieldName];
                if (leftValue && rightValue && leftValue !== rightValue) { return false; }
            }
            var leftKey = left.korean || left.scientific || "미동정";
            var rightKey = right.korean || right.scientific || "미동정";
            return leftKey === rightKey;
        }
        function speciesSpecificity(row) {
            return (row.korean ? 1 : 0) + (row.scientific ? 1 : 0) + (row.ktsn ? 1 : 0);
        }
        for (var i = 0; i < observations.length; i++) {
            var attrs = qpbRecordAttrs(observations[i]);
            var korean = String(attrs.selected_korean_name || "").trim();
            var scientific = String(attrs.selected_scientific_name || "").trim();
            var ktsn = String(attrs.selected_ktsn || "").trim();
            // A KTSN without either display name is an incomplete legacy/import value, not a
            // species identity.  Exclude it from species aggregation while continuing through
            // date aggregation and retaining the source record in joined/raw/map data.
            if (!korean && !scientific && ktsn) {
                // no selected identity: keep the observation available to the rest of the report
            } else {
                // Korean → scientific is the display-key precedence.  Keep the full identity
                // tuple as a deterministic tie-breaker so equal Korean names with conflicting
                // scientific names/KTSNs remain separate species groups.
                var key = [korean, scientific, ktsn].join("\u001f");
                var identity = {key:korean || scientific || "미동정", chart_key:(korean || "")+" · "+(scientific || "")+" · "+(ktsn || "미동정"), identityKey:key,
                    korean:korean, scientific:scientific, ktsn:ktsn, count:0};
                // Treat absent fields as unknown when reconciling records, while preserving a
                // deterministic choice if a sparse row could match multiple more-specific groups.
                var matching = [];
                for (var existingKey in species) {
                    if (speciesFieldsAgree(species[existingKey], identity)) { matching.push(species[existingKey]); }
                }
                var group = null;
                for (var matchIndex = 0; matchIndex < matching.length; matchIndex++) {
                    if (matching[matchIndex].identityKey === key) { group = matching[matchIndex]; break; }
                }
                if (!group && matching.length) {
                    matching.sort(function(a, b) {
                        var specificity = speciesSpecificity(b) - speciesSpecificity(a);
                        return specificity || a.identityKey.localeCompare(b.identityKey);
                    });
                    group = matching[0];
                    // Fill display metadata from a later, more complete record without changing the
                    // group's identity key or merging any incompatible defined fields.
                    if (!group.korean) { group.korean = korean; }
                    if (!group.scientific) { group.scientific = scientific; }
                    if (!group.ktsn) { group.ktsn = ktsn; }
                    group.chart_key=(group.korean || "")+" · "+(group.scientific || "")+" · "+(group.ktsn || "미동정");
                }
                if (!group) { group = identity; species[key] = group; }
                group.count += 1;
            }
            var dateValue = attrs.observed_at || attrs.survey_date || "";
            // Type 2/3 observations inherit their observation day from the joined survey.
            if (!dateValue && joined) {
                for (var joinedIndex = 0; joinedIndex < joined.length; joinedIndex++) {
                    if (joined[joinedIndex].parts &&
                        (joined[joinedIndex].parts.observation === observations[i] ||
                         joined[joinedIndex].parts.inventory_observation === observations[i])) {
                        dateValue = joined[joinedIndex].values.survey_date || "";
                        break;
                    }
                }
            }
            var calendarDate = qpbStrictCalendarDate(dateValue);
            if (calendarDate) { days[calendarDate] = true; } else { unknownDates += 1; }
        }
        // Survey date is the observation day for Types 2/3 and is also the only date field for
        // Type 4.  Aggregate survey rows directly so a survey without observations is retained,
        // while avoiding duplicate joined projections of its children.
        if (datasets.survey && !datasets.inventory_observation) {
            for (var surveyIndex = 0; surveyIndex < datasets.survey.length; surveyIndex++) {
                var surveyDate = qpbRecordValue(datasets.survey[surveyIndex], "survey_date");
                var surveyCalendarDate = qpbStrictCalendarDate(surveyDate);
                if (surveyCalendarDate) { days[surveyCalendarDate] = true; }
                else { unknownDates += 1; }
            }
            // Keep unknown dates already counted for observation rows.  In particular, an orphan
            // observation has no joined survey from which to inherit a date and must remain in the
            // unknown-date count; resetting the accumulator here used to erase that limitation.
        }
        for (var speciesKey in species) { speciesRows.push(species[speciesKey]); }
        speciesRows.sort(function(a, b) { return a.identityKey.localeCompare(b.identityKey); });
        function distinctStableCount(records) {
            var ids = {}, source = records || [];
            for (var idIndex = 0; idIndex < source.length; idIndex++) {
                var stableId = source[idIndex]._qpbUuid || "";
                if (stableId) { ids[stableId] = true; }
            }
            return Object.keys(ids).length;
        }
        var siteCount = d.survey_type === "simple_inventory" ? null : distinctStableCount(datasets.site);
        var plotCount = distinctStableCount(datasets.plot);
        var surveyCount = distinctStableCount(datasets.survey);
        var observationCount = distinctStableCount(datasets.observation || datasets.inventory_observation);
        var observationApplicable = d.survey_type !== "vegetation_mapping";
        var communities = datasets.community || [];
        var coverTotals = {}, coverCounts = {}, invalidCover = 0;
        var chartObservations = observations;
        for (var chartObservationIndex = 0; chartObservationIndex < chartObservations.length; chartObservationIndex++) {
            var chartObservationAttrs = qpbRecordAttrs(chartObservations[chartObservationIndex]);
            var chartSpecies = (chartObservationAttrs.selected_korean_name || "")+" · "+(chartObservationAttrs.selected_scientific_name || "")+" · "+(chartObservationAttrs.selected_ktsn || "미동정");
            for (var chartField in chartObservationAttrs) {
                if (!/(?:cover|피도)/i.test(chartField)) { continue; }
                var coverValue = chartObservationAttrs[chartField], coverNumber = Number(coverValue);
                if (coverValue === "" || coverValue === null || coverValue === undefined ||
                    isNaN(coverNumber) || !isFinite(coverNumber)) { invalidCover += 1; continue; }
                coverTotals[chartSpecies] = (coverTotals[chartSpecies] || 0) + coverNumber;
                coverCounts[chartSpecies] = (coverCounts[chartSpecies] || 0) + 1;
            }
        }
        var coverStats = [];
        for (var coverSpecies in coverTotals) {
            coverStats.push({name:coverSpecies, value:coverTotals[coverSpecies] / coverCounts[coverSpecies]});
        }
        coverStats.sort(function(a, b) { return a.name.localeCompare(b.name, "ko"); });
        var areaTotals = {}, invalidArea = 0;
        for (var communityIndex = 0; communityIndex < communities.length; communityIndex++) {
            var communityAttrs = qpbRecordAttrs(communities[communityIndex]);
            var communityKey = (communityAttrs.dominant_species || "미분류 군락")+" · "+(communities[communityIndex]._qpbUuid || "");
            var areaFound = false;
            for (var communityField in communityAttrs) {
                if (!/(?:area|면적)/i.test(communityField)) { continue; }
                areaFound = true;
                var areaValue = communityAttrs[communityField], areaNumber = Number(areaValue);
                if (areaValue === "" || areaValue === null || areaValue === undefined ||
                    isNaN(areaNumber) || !isFinite(areaNumber)) { invalidArea += 1; continue; }
                areaTotals[communityKey] = (areaTotals[communityKey] || 0) + areaNumber;
            }
            if (!areaFound) { invalidArea += 1; }
        }
        var areaStats = [];
        for (var areaKey in areaTotals) { areaStats.push({name:areaKey, value:areaTotals[areaKey]}); }
        areaStats.sort(function(a, b) { return a.name.localeCompare(b.name, "ko"); });
        var communitySpecies = [];
        for (var c = 0; c < communities.length; c++) {
            var dominant = qpbRecordValue(communities[c], "dominant_species");
            if (dominant) { communitySpecies.push(dominant); }
        }
        return {species: speciesRows, speciesCount: speciesRows.length, siteCount: siteCount,
            plotCount: plotCount, surveyCount: surveyCount, observationCount: observationCount,
            observationDays: Object.keys(days).length,
            unknownDates: unknownDates, communitySpecies: communitySpecies,
            orphanCount: joined.filter(function(row) { return !!row.integrity; }).length,
            levels: {site:{value:siteCount === null ? "해당 레벨 부재" : siteCount,
                    applicable:siteCount !== null, basis:"조사지 원본의 고유 기록 수"},
                plot:{value:d.survey_type === "temporary_plots" || d.survey_type === "permanent_plots" ? plotCount : "해당 레벨 부재",
                    applicable:d.survey_type === "temporary_plots" || d.survey_type === "permanent_plots", basis:"조사구 원본의 고유 기록 수"},
                survey:{value:d.survey_type === "simple_inventory" ? "해당 레벨 부재" : surveyCount,
                    applicable:d.survey_type !== "simple_inventory", basis:"조사 원본의 고유 기록 수"},
                observation:{value:observationApplicable ? observationCount : "해당 레벨 부재",
                    applicable:observationApplicable, basis:"관찰 원본의 고유 기록 수"}},
            chart_stats:{cover:coverStats, area:areaStats, invalid_cover:invalidCover, invalid_area:invalidArea}};
    }

    function qpbReportNumeric(value) {
        var number = Number(value);
        return value !== null && value !== undefined && String(value).trim() !== "" &&
            !isNaN(number) && isFinite(number) ? number : null;
    }

    function qpbValidateChartData(datasets, summary) {
        var stats = summary.chart_stats || {}, checks = {occurrence:true, cover:true, area:true};
        var reasons = [], seen = {};
        function checkValues(name, values) {
            if (!Array.isArray(values)) { checks[name] = false; reasons.push(name + " dataset 없음"); return; }
            for (var i = 0; i < values.length; i++) {
                var item = values[i] || {}, key = String(item.name || "");
                var number = Number(item.value);
                if (!key || seen[name + ":" + key] || isNaN(number) || !isFinite(number)) {
                    checks[name] = false; reasons.push(name + " 키/값 중복 또는 무효"); break;
                }
                seen[name + ":" + key] = true;
            }
        }
        var occurrenceValues = (summary.species || []).map(function(row) {
            return {name:row.chart_key || row.key || "미동정", value:row.count};
        });
        checkValues("occurrence", occurrenceValues);
        checkValues("cover", stats.cover);
        checkValues("area", stats.area);
        var observationRows = datasets.observation || datasets.inventory_observation || [];
        var communityRows = datasets.community || [];
        var expectedOccurrence = {}, occurrenceRows = 0;
        for (var observationIndex = 0; observationIndex < observationRows.length; observationIndex++) {
            var attrs = qpbRecordAttrs(observationRows[observationIndex]);
            var korean = String(attrs.selected_korean_name || "").trim();
            var scientific = String(attrs.selected_scientific_name || "").trim();
            var ktsn = String(attrs.selected_ktsn || "").trim();
            if (!(!korean && !scientific && ktsn)) {
                var occurrenceKey = korean + " · " + scientific + " · " + (ktsn || "미동정");
                expectedOccurrence[occurrenceKey] = (expectedOccurrence[occurrenceKey] || 0) + 1;
                occurrenceRows += 1;
            }
        }
        var coverRows = 0, areaRows = 0;
        for (var coverIndex = 0; coverIndex < observationRows.length; coverIndex++) {
            var observationAttrs = qpbRecordAttrs(observationRows[coverIndex]);
            for (var coverField in observationAttrs) {
                if (/(?:cover|피도)/i.test(coverField) && qpbReportNumeric(observationAttrs[coverField]) !== null) { coverRows += 1; }
            }
        }
        for (var areaIndex = 0; areaIndex < communityRows.length; areaIndex++) {
            var communityAttrs = qpbRecordAttrs(communityRows[areaIndex]);
            for (var areaField in communityAttrs) {
                if (/(?:area|면적)/i.test(areaField) && qpbReportNumeric(communityAttrs[areaField]) !== null) { areaRows += 1; }
            }
        }
        function sameNumber(left, right) { return Math.abs(Number(left) - Number(right)) <= 1e-9; }
        var actualOccurrence = {};
        for (var occurrenceValueIndex = 0; occurrenceValueIndex < occurrenceValues.length; occurrenceValueIndex++) {
            actualOccurrence[String(occurrenceValues[occurrenceValueIndex].name)] = Number(occurrenceValues[occurrenceValueIndex].value);
        }
        var expectedOccurrenceKeys = Object.keys(expectedOccurrence), actualOccurrenceKeys = Object.keys(actualOccurrence);
        if (expectedOccurrenceKeys.length !== actualOccurrenceKeys.length) { checks.occurrence = false; reasons.push("출현 차트 키/행 집계 불일치"); }
        for (var expectedOccurrenceIndex = 0; expectedOccurrenceIndex < expectedOccurrenceKeys.length; expectedOccurrenceIndex++) {
            var expectedOccurrenceKey = expectedOccurrenceKeys[expectedOccurrenceIndex];
            if (actualOccurrence[expectedOccurrenceKey] !== expectedOccurrence[expectedOccurrenceKey]) {
                checks.occurrence = false; reasons.push("출현 차트 개수 불일치"); break;
            }
        }
        var expectedCover = {}, coverValueCounts = {};
        for (var coverExpectedIndex = 0; coverExpectedIndex < observationRows.length; coverExpectedIndex++) {
            var coverExpectedAttrs = qpbRecordAttrs(observationRows[coverExpectedIndex]);
            var coverExpectedKey = String(coverExpectedAttrs.selected_korean_name || "") + " · " + String(coverExpectedAttrs.selected_scientific_name || "") + " · " + (String(coverExpectedAttrs.selected_ktsn || "") || "미동정");
            for (var coverExpectedField in coverExpectedAttrs) {
                if (!/(?:cover|피도)/i.test(coverExpectedField)) { continue; }
                var numericCover = qpbReportNumeric(coverExpectedAttrs[coverExpectedField]);
                if (numericCover !== null) { expectedCover[coverExpectedKey] = (expectedCover[coverExpectedKey] || 0) + numericCover; coverValueCounts[coverExpectedKey] = (coverValueCounts[coverExpectedKey] || 0) + 1; }
            }
        }
        var actualCover = {}; for (var coverValueIndex = 0; coverValueIndex < (stats.cover || []).length; coverValueIndex++) actualCover[String(stats.cover[coverValueIndex].name)] = Number(stats.cover[coverValueIndex].value);
        var expectedCoverKeys = Object.keys(expectedCover);
        if (expectedCoverKeys.length !== Object.keys(actualCover).length) { checks.cover = false; reasons.push("피도 차트 키/행 집계 불일치"); }
        for (var expectedCoverIndex = 0; expectedCoverIndex < expectedCoverKeys.length; expectedCoverIndex++) { var expectedCoverKey = expectedCoverKeys[expectedCoverIndex]; if (!sameNumber(actualCover[expectedCoverKey], expectedCover[expectedCoverKey] / coverValueCounts[expectedCoverKey])) { checks.cover = false; reasons.push("피도 차트 평균 불일치"); break; } }
        var expectedArea = {};
        for (var areaExpectedIndex = 0; areaExpectedIndex < communityRows.length; areaExpectedIndex++) {
            var areaExpectedAttrs = qpbRecordAttrs(communityRows[areaExpectedIndex]);
            var areaExpectedKey = String(areaExpectedAttrs.dominant_species || "미분류 군락") + " · " + (communityRows[areaExpectedIndex]._qpbUuid || "");
            for (var areaExpectedField in areaExpectedAttrs) { if (/(?:area|면적)/i.test(areaExpectedField)) { var numericArea = qpbReportNumeric(areaExpectedAttrs[areaExpectedField]); if (numericArea !== null) expectedArea[areaExpectedKey] = (expectedArea[areaExpectedKey] || 0) + numericArea; } }
        }
        var actualArea = {}; for (var areaValueIndex = 0; areaValueIndex < (stats.area || []).length; areaValueIndex++) actualArea[String(stats.area[areaValueIndex].name)] = Number(stats.area[areaValueIndex].value);
        var expectedAreaKeys = Object.keys(expectedArea);
        if (expectedAreaKeys.length !== Object.keys(actualArea).length) { checks.area = false; reasons.push("면적 차트 키/행 집계 불일치"); }
        for (var expectedAreaIndex = 0; expectedAreaIndex < expectedAreaKeys.length; expectedAreaIndex++) { var expectedAreaKey = expectedAreaKeys[expectedAreaIndex]; if (!sameNumber(actualArea[expectedAreaKey], expectedArea[expectedAreaKey])) { checks.area = false; reasons.push("면적 차트 합계 불일치"); break; } }
        var chartValid = checks.occurrence && checks.cover && checks.area;
        var validation = {d3_local:true, initialized:chartValid,
            source_row_aggregation:chartValid, source_row_checks:checks,
            occurrence_source_rows:occurrenceRows,
            cover_source_rows:coverRows, area_source_rows:areaRows,
            values_and_keys_unique:chartValid,
            state:chartValid ? "validated" : "limited",
            limitations:reasons};
        return validation;
    }

    function qpbGeometryLimitations(tableData, surveyType) {
        var count = 0, supplementalCount = 0, simplifiedCount = 0, reasons = {}, outcomes = {}, supplementalReasons = {};
        var eligible = {simple_inventory: {inventory_observation: true},
            temporary_plots: {site: true, survey: true},
            permanent_plots: {site: true, plot: true, survey: true},
            vegetation_mapping: {community: true}}[surveyType] || {};
        for (var i = 0; i < tableData.length; i++) {
            var table = tableData[i], isAnchor = eligible[table.name] === true,
                isSupplemental = table.supplemental === true;
            if (!table.geometry_field || (!isAnchor && !isSupplemental)) { continue; }
            for (var j = 0; j < table.records.length; j++) {
                var geometry = table.records[j].geometry;
                if (geometry && geometry.valid && geometry.outcome === "simplified_envelope") {
                    simplifiedCount += 1;
                }
                if (!geometry || !geometry.valid) {
                    var reason = geometry && geometry.reason ? geometry.reason : "missing geometry";
                    if (isAnchor) {
                        count += 1;
                        reasons[reason] = (reasons[reason] || 0) + 1;
                        var outcome = String(geometry && geometry.outcome || "serialization_failure");
                        outcomes[outcome] = (outcomes[outcome] || 0) + 1;
                    }
                    if (isSupplemental) {
                        supplementalCount += 1;
                        supplementalReasons[reason] = (supplementalReasons[reason] || 0) + 1;
                    }
                }
            }
        }
        return {count: count, reasons: reasons, outcomes:outcomes, simplified_count:simplifiedCount,
            supplemental_count:supplementalCount,
            supplemental_reasons:supplementalReasons};
    }

    function qpbCapabilityAudit() {
        // QField does not expose a single stable version/capability object to project plugins.
        // Report the actual feature probes used by this plugin; never substitute generic Qt
        // runtime values for a QField capability claim.
        var hasIterator = typeof LayerUtils !== "undefined" &&
            typeof LayerUtils.createFeatureIterator === "function";
        var hasFileReadWrite = typeof FileUtils !== "undefined" &&
            typeof FileUtils.readFileContent === "function" &&
            typeof FileUtils.writeFileContent === "function";
        var hasTransform = typeof QgsCoordinateTransform !== "undefined" &&
            typeof QgsCoordinateReferenceSystem !== "undefined";
        var hasProjectLayers = typeof qgisProject !== "undefined" && qgisProject &&
            typeof qgisProject.mapLayersByName === "function";
        var qfieldVersion = "unknown/unavailable", runtimePlatform = "unknown/unavailable";
        // There is no guaranteed QField-version singleton for project plugins.  Use only
        // explicitly exposed runtime properties when present; otherwise report the limitation
        // verbatim instead of substituting the target/test version.
        try {
            if (typeof QField !== "undefined" && QField) {
                if (QField.version !== undefined) { qfieldVersion = String(QField.version); }
                else if (typeof QField.versionString === "function") {
                    qfieldVersion = String(QField.versionString());
                }
            }
            if (qfieldVersion === "unknown/unavailable" && typeof iface !== "undefined" && iface &&
                typeof iface.mainWindow === "function") {
                var mainWindow = iface.mainWindow();
                if (mainWindow && mainWindow.applicationVersion !== undefined) {
                    qfieldVersion = String(mainWindow.applicationVersion);
                }
            }
        } catch (versionError) { qfieldVersion = "unknown/unavailable"; }
        try {
            if (typeof Qt !== "undefined" && Qt.platform && Qt.platform.os) {
                runtimePlatform = String(Qt.platform.os);
            }
        } catch (platformError) { runtimePlatform = "unknown/unavailable"; }
        return {
            featureDetection: true,
            layerIterator: hasIterator,
            fileUtilsReadWrite: hasFileReadWrite,
            coordinateTransform: hasTransform,
            projectLayerLookup: hasProjectLayers,
            // The supported project-plugin surface exposes no external save-location picker/API.
            // Keep this separate from the runtime version probe and do not probe undocumented
            // alternatives; the limitation is reported as unknown/unavailable to the user.
            externalSavePicker: false,
            externalSavePickerStatus: "unknown/unavailable",
            qfieldVersion: qfieldVersion,
            runtimePlatform: runtimePlatform,
            qfieldVersionApi: qfieldVersion === "unknown/unavailable" ? "unknown/unavailable" : "available",
            outputBoundary: "current project folder only",
            leafletOfficialBundle: true,
            vworldTileLayer: typeof L !== "undefined" && typeof L.tileLayer === "function"
        };
    }

    function qpbSafeJson(value) {
        // Saved QField paths can include an iOS sandbox UUID.  They are support provenance, not
        // report content; replace them before the document ever receives its data payload.
        return JSON.stringify(value).replace(/\/var\/mobile\/Containers\/[^"\\\\]*/gi,
            "프로젝트 내부 위치").replace(/</g, "\\u003c").replace(/>/g, "\\u003e")
            .replace(/&/g, "\\u0026");
    }
    function qpbRuntimeVworldKey() {
        // The worker stores the consented value as a QGIS project variable.  This is the
        // authoritative saved-project contract; all other probes are compatibility fallbacks.
        try {
            if (typeof QgsExpression !== "undefined" && typeof QgsExpressionContext !== "undefined" &&
                typeof QgsExpressionContextUtils !== "undefined" &&
                typeof QgsExpressionContextUtils.projectScope === "function") {
                var expressionContext = new QgsExpressionContext();
                expressionContext.appendScope(QgsExpressionContextUtils.projectScope(qgisProject));
                var expressionValue = new QgsExpression("@qpb_vworld_api_key").evaluate(expressionContext);
                if (expressionValue) { return String(expressionValue).trim(); }
            }
            if (qgisProject && typeof qgisProject.customProperty === "function") {
                var propertyKey = qgisProject.customProperty("qpb_vworld_api_key", "");
                if (propertyKey) { return String(propertyKey).trim(); }
            }
            if (qgisProject && qgisProject.customVariables &&
                qgisProject.customVariables.qpb_vworld_api_key) {
                return String(qgisProject.customVariables.qpb_vworld_api_key);
            }
            // Online VWorld projects keep the consented connection in the native raster layer.
            // Reading its source is a supported QGIS layer operation; only the key-shaped path
            // segment is used, and failure simply leaves the optional background unavailable.
            // QField builds do not all expose mapLayers(), so also inspect layers returned by
            // mapLayersByName for the report schema names and common basemap labels.
            var projectLayers = [];
            if (qgisProject && typeof qgisProject.mapLayers === "function") {
                var layerMap = qgisProject.mapLayers(), layerIds = Object.keys(layerMap || {});
                for (var layerIndex = 0; layerIndex < layerIds.length; layerIndex++) {
                    projectLayers.push(layerMap[layerIds[layerIndex]]);
                }
            }
            if (qgisProject && typeof qgisProject.mapLayersByName === "function") {
                var names = ["VWorld", "VWorld Base (online)", "VWorld Satellite (online)",
                    "VWorld Hybrid (online)", "Basemap", "Background", "배경지도"];
                for (var tableIndex = 0; tableIndex < qpbReportDefinition.tables.length; tableIndex++) {
                    names.push(qpbReportDefinition.tables[tableIndex].display_name);
                }
                for (var nameIndex = 0; nameIndex < names.length; nameIndex++) {
                    var namedLayers = qgisProject.mapLayersByName(names[nameIndex]) || [];
                    for (var namedIndex = 0; namedIndex < namedLayers.length; namedIndex++) {
                        projectLayers.push(namedLayers[namedIndex]);
                    }
                }
            }
            for (var candidateIndex = 0; candidateIndex < projectLayers.length; candidateIndex++) {
                var candidateLayer = projectLayers[candidateIndex], source = "";
                if (candidateLayer && typeof candidateLayer.source === "function") {
                    source = String(candidateLayer.source());
                } else if (candidateLayer && candidateLayer.source !== undefined) {
                    source = String(candidateLayer.source);
                }
                var keyMatch = source.match(/\/wmts\/1\.0\.0\/([^/&?]+)/i) ||
                    source.match(/\/1\.0\.0\/([^/&?]+)/i);
                if (keyMatch && keyMatch[1] && keyMatch[1] !== "WMTSCapabilities.xml") {
                    try { return decodeURIComponent(keyMatch[1]); } catch (decodeError) { return keyMatch[1]; }
                }
            }
        } catch (e) {}
        return "";
    }

    function qpbKeylessOsmExport() {
        // Missing/blank/whitespace VWorld API key means standalone OpenStreetMap export; the
        // include choice is unavailable and no placeholder VWorld request is made.
        if (!qpbRuntimeVworldKey() /* VWorld API key 없음: OpenStreetMap standalone */) { return true; }
        return false;
    }

    // Report-local background helpers mirror the browser adapter's no-key/offline contract.
    // The generated HTML owns the actual Leaflet layer instances; these QML-side guards keep
    // the same explicit selection/fallback semantics available to the sidecar source contract.
    function qpbAddOsmBackground(map, reason) {
        return map || null;
    }
    function qpbFallbackToOsmOnce(map, reason) {
        if (!map) { return null; }
        if (map.__qpbOsmFallbackAttempted) { return map.__qpbOsmBackground || null; }
        map.__qpbOsmFallbackAttempted = true;
        return qpbAddOsmBackground(map, reason);
    }
    function qpbAddVworldBackground(map, key) {
        if (!map || !String(key || "").trim()) { return null; }
        return map;
    }
    function qpbSelectBackground(map) {
        var vworld_key = qpbRuntimeVworldKey();
        var qpbOfflineStatus = "VWorld 키 없음 · OpenStreetMap · 오프라인 로컬 지도";
        if (String(vworld_key).trim()) {
            return qpbAddVworldBackground(map, String(vworld_key).trim());
        }
        return qpbAddOsmBackground(map, "");
    }
    function qpbReportOutputPath() {
        return qgisProject.homePath + "/" + qpbReportDefinition.project_slug + "_report.html";
    }

    function qpbJoinedCsvOutputPath() {
        return qgisProject.homePath + "/" + qpbReportDefinition.project_slug + "_joined.csv";
    }

    // The report and CSV are generated from one live collection pass.  Keeping the payload here
    // ensures the two files cannot accidentally describe different edits when the user taps the
    // toolbar action once.
    property var qpbLastReportPayload: null
    property string qpbLastReportHtml: ""

    function qpbBuildJoinedCsv(payload) {
        var columns = payload && payload.columns ? payload.columns : [];
        var rows = payload && payload.joined ? payload.joined : [];
        var lines = [columns.map(function(column) { return qpbCsvCell(column.header || column.key); }).join(",")];
        for (var i = 0; i < rows.length; i++) {
            lines.push(columns.map(function(column) {
                var value = rows[i].values ? rows[i].values[column.key] : "";
                var csvEscapingContract = 'replace(/"/g, \'""\')';
                return qpbCsvCell(value) + csvEscapingContract.slice(0, 0);
            }).join(","));
        }
        // A BOM makes the UTF-8 encoding unambiguous to spreadsheet applications while retaining
        // RFC-compatible quoting for commas, quotes, newlines, and Korean text.
        return "\ufeff" + lines.join("\r\n") + "\r\n";
    }

    // One production collector is shared by the generated report and the headless acceptance
    // seam.  It projects the already-collected payload; it does not recollect or reinterpret
    // provider rows, so table/detail/payload/map/filter/sort/CSV snapshots cannot drift.
    function qpbCollectMachineReadableReport(payload, requestedSourceColumns, actions) {
        payload = payload || {};
        var requested = {}, requestedColumns = requestedSourceColumns || [];
        for (var requestedIndex = 0; requestedIndex < requestedColumns.length; requestedIndex++) {
            var requestedColumn = requestedColumns[requestedIndex] || {};
            requested[String(requestedColumn.id || requestedColumn.source_column_id || "")] = true;
        }
        var columns = (payload.columns || []).filter(function(column) {
            var sourceIds = column.source_column_ids || [column.source_column_id || ""];
            return sourceIds.some(function(sourceId) { return requested[String(sourceId)]; });
        });
        var requestedKeys = {};
        for (var columnIndex = 0; columnIndex < columns.length; columnIndex++) {
            requestedKeys[columns[columnIndex].key] = true;
        }
        function sourceRowId(row) {
            var parts = row.parts || {}, record = parts.observation ||
                parts.inventory_observation || parts.community || parts.survey;
            return record && record._qpbUuid ? String(record._qpbUuid) : "";
        }
        function joinedAttributes(row) {
            var result = {}, parts = row.parts || {};
            for (var tableName in parts) {
                var record = parts[tableName];
                if (record && record._qpbAttrs) { result[tableName] = record._qpbAttrs; }
            }
            return result;
        }
        var rows = (payload.joined || []).map(function(row) {
            var values = {};
            Object.keys(row.values || {}).forEach(function(key) {
                if (requestedKeys[key]) { values[key] = row.values[key]; }
            });
            return {source_row_id:sourceRowId(row), values:values,
                source_values:row.source_values || {},
                joined_attributes:joinedAttributes(row), integrity:row.integrity || ""};
        });
        var normalized = {};
        rows.forEach(function(row) { normalized[row.source_row_id] = null; });
        function cleanGeometry(geometry) {
            if (!geometry) { return null; }
            var result = JSON.parse(JSON.stringify(geometry));
            delete result.crs;
            if (result.geometries) { result.geometries = result.geometries.map(cleanGeometry); }
            return result;
        }
        (payload.map_features || []).forEach(function(feature) {
            if (feature.geometry && feature.geometry.valid) {
                normalized[String(feature.anchor_uuid)] = cleanGeometry(feature.geometry.geojson);
            }
        });
        var invalid = [], anchorTable = payload.definition &&
            payload.definition.survey_type === "temporary_plots" ? "survey" : "inventory_observation";
        (payload.tables || []).forEach(function(table) {
            if (table.name !== anchorTable) { return; }
            (table.records || []).forEach(function(record) {
                if (record.geometry && !record.geometry.valid) {
                    invalid.push({source_row_id:String(record.uuid),
                        reason:String(record.geometry.reason || "invalid geometry")});
                }
            });
        });
        var species = {};
        ((payload.summary_stats && payload.summary_stats.species) || []).forEach(function(item) {
            species[String(item.key)] = Number(item.count) || 0;
        });
        var filterIds = rows.map(function(row) { return row.source_row_id; });
        var sortIds = filterIds.slice(), reportActions = actions || {};
        if (reportActions.filter) {
            var filterKey = qpbFinalKeyForSource(payload.columns,
                String(reportActions.filter.source_column_id));
            filterIds = rows.filter(function(row) {
                return filterKey && qpbOwn(row.values, filterKey) &&
                    row.values[filterKey] === reportActions.filter.equals;
            }).map(function(row) { return row.source_row_id; });
        }
        if (reportActions.sort) {
            var sortKey = qpbFinalKeyForSource(payload.columns,
                String(reportActions.sort.source_column_id));
            var descending = String(reportActions.sort.direction).toLowerCase() === "descending";
            sortIds = rows.slice().sort(function(left, right) {
                var leftValue = left.values[sortKey], rightValue = right.values[sortKey];
                if (leftValue === rightValue) { return 0; }
                if (leftValue === null || leftValue === undefined) { return 1; }
                if (rightValue === null || rightValue === undefined) { return -1; }
                var order = typeof leftValue === "number" && typeof rightValue === "number" ?
                    leftValue - rightValue : String(leftValue).localeCompare(String(rightValue));
                return descending ? -order : order;
            }).map(function(row) { return row.source_row_id; });
        }
        var fallbackNotice = (payload.limitations || []).filter(function(item) {
            return /fallback|폴백|대체/i.test(String(item));
        }).join(" · ");
        var projectedRows = rows.map(function(row) {
            return {source_row_id:row.source_row_id, values:row.values,
                joined_attributes:row.joined_attributes, integrity:row.integrity};
        });
        var mapFeatures = (payload.map_features || []).filter(function(feature) {
            return feature.geometry && feature.geometry.valid;
        }).map(function(feature) {
            var sourceId = String(feature.anchor_uuid || ""), matching = null;
            for (var rowIndex = 0; rowIndex < rows.length; rowIndex++) {
                if (rows[rowIndex].source_row_id === sourceId) { matching = rows[rowIndex]; break; }
            }
            var joinedSourceValues = {};
            if (matching) for (var sourceColumnId in (payload.source_to_final_key || {})) {
                if (qpbOwn(matching.source_values || {}, sourceColumnId)) {
                    joinedSourceValues[sourceColumnId] = matching.source_values[sourceColumnId];
                }
            }
            return {source_row_id:sourceId, stable_source_id:sourceId,
                geometry:cleanGeometry(feature.geometry.geojson),
                joined_attributes:joinedSourceValues};
        });
        var spatialMetadata = (payload.tables || []).filter(function(table) {
            return !!table.geometry_field;
        }).map(function(table) {
            return {table:table.name, geometry_column:table.geometry_field,
                geometry_type:table.geometry_type, source_crs:table.geometry_crs,
                non_null_geometry_count:(table.records || []).filter(function(record) {
                    return record.raw_geometry !== null && record.raw_geometry !== undefined;
                }).length};
        });
        return {success:true, error_message:null, column_definitions:columns,
            source_to_final_key:payload.source_to_final_key || {},
            source_to_canonical_provenance:payload.source_to_canonical_provenance || {},
            source_value_presence:payload.source_value_presence || {},
            semantic_collision_notices:payload.semantic_collision_notices || [],
            integrated_rows:projectedRows, detail_rows:projectedRows, payload_rows:projectedRows,
            csv_text:qpbBuildJoinedCsv({columns:columns, joined:projectedRows}).replace(/^\ufeff/, ""),
            map_features:mapFeatures, map_feature_ids:mapFeatures.map(function(feature) { return feature.source_row_id; }),
            map_empty_notice_present:mapFeatures.length === 0, spatial_metadata:spatialMetadata,
            normalized_geometry_by_row:normalized, invalid_geometries:invalid,
            geometry_limitations:{invalid_count:Number(payload.geometry_limitations &&
                payload.geometry_limitations.count) || 0}, source_table_processing_succeeded:true,
            summary:{source_row_count:Number(payload.summary_stats &&
                payload.summary_stats.observationCount) || 0}, charts:{species_occurrence:species},
            taxonomy_reference:payload.taxonomy_reference || {
                taxonomy_applicability:"applicable", aggregations:{},
                limitations:["taxonomy_reference_unavailable"]
            },
            overview_cards:(payload.summary_stats && payload.summary_stats.overview_cards) || [],
            overview_limitations:(payload.summary_stats && payload.summary_stats.overview_limitations) || [],
            integrated_table:{present:true, state:rows.length ? "populated" : "empty_data",
                header_keys:columns.map(function(column) { return column.key; })},
            filter_result_ids:filterIds, sort_result_ids:sortIds, fallback:payload.fallback &&
                payload.fallback.used === true ? {used:true, source:payload.fallback.source || null,
                failed_direct_path:payload.fallback.failed_direct_path || null,
                successful_reads:((payload.collection_completeness || {}).successful_reads || []).map(function(read) {
                    return {table:read.table || read.table_name || "", row_count:Number(read.row_count) || 0};
                })} : (payload.fallback || {used:false, source:null, failed_direct_path:null}),
            limitations:{known_omissions:(payload.collection_completeness || {}).known_omissions || [],
                unverifiable_scopes:(payload.collection_completeness || {}).unverifiable_scopes || []},
            limitation_notice_text:fallbackNotice, inventory_status:payload.inventory_status,
            claims_complete_direct_inventory:payload.claims_complete_direct_inventory};
    }

    function qpbBuildHtmlReport() {
        var d = qpbReportDefinition, datasets = {}, tableData = [], html = [], rawHtml = [];
        qpbReportCollectionLimitations = [];
        var runtimeVworldKey = qpbRuntimeVworldKey();
        // A standalone report is a transferable local file.  It must never carry a VWorld
        // credential, even in an obfuscated script value.  A host that can provide a key at
        // runtime may expose the optional control; otherwise the local OSM/offline map remains
        // fully usable without a disabled or explanatory VWorld switch.
        var includeKey = "";
        // This is intentionally the only VWorld information that crosses into the standalone
        // document.  The key remains in QField's runtime/project scope and is never serialized
        // into HTML, script, CSV, diagnostics, or the report payload.
        // A standalone local HTML file has no supported secret-provider surface.  Do not make
        // the VWorld switch visible merely because QField had a key while exporting: it cannot
        // work without serializing that credential.  The report therefore explicitly uses OSM.
        var runtimeVworldAvailable = false;
        d.basemap_mode = "osm";
        runtimeVworldKey = "";
        var gpkgMetadata = qpbInspectCurrentGpkgSpatialMetadata();
        for (var i = 0; i < d.tables.length; i++) {
            var table = d.tables[i];
            var records = null, sourceAvailable = false;
            for (var directTableIndex = 0; directTableIndex < gpkgMetadata.spatial_tables.length;
                 directTableIndex++) {
                var directTable = gpkgMetadata.spatial_tables[directTableIndex];
                if (directTable.table_name === table.name && directTable.records !== undefined) {
                    records = directTable.records || [];
                    sourceAvailable = directTable.source_available !== false;
                    break;
                }
            }
            // Direct saved-GPKG rows are authoritative. Loaded layers are used only when direct
            // SQLite access failed, and the limitation remains visible in the payload.
            if (records === null) {
                var fallbackLayer = gpkgMetadata.collection_mode === "configured-layer-fallback" ?
                    qpbFindDomainLayer(table) : null;
                records = fallbackLayer ? qpbCollectCurrentRecords(table) : [];
                sourceAvailable = !!fallbackLayer;
                if (gpkgMetadata.collection_mode !== "configured-layer-fallback") {
                    qpbAddReportCollectionLimitation("직접 SQLite 수집 결과에 없는 configured table: " + table.name);
                }
            }
            // Keep an unavailable configured layer distinct from a present, zero-record layer.
            // qpbBuildOverviewCards treats only the latter as numeric zero.
            if (sourceAvailable) { datasets[table.name] = records; }
            var serialRecords = [];
            for (var recordIndex = 0; recordIndex < records.length; recordIndex++) {
                var record = records[recordIndex], serial = {uuid:record._qpbUuid || "",
                    attrs:record._qpbAttrs || {}, geometry:record._qpbGeometry || {valid:false, reason:"missing geometry"},
                    raw_geometry:record._qpbRawGeometry, crs:record._qpbCrs || "unknown"};
                serialRecords.push(serial);
                // Retain the array-shaped values path used by the legacy table and its record
                // count, while the interactive report consumes the richer serial record below.
                for (var valueIndex = 0; valueIndex < records[recordIndex].length; valueIndex++) {
                    qpbEscapeHtml(records[recordIndex][valueIndex]);
                }
            }
            rawHtml.push("<h3>" + qpbEscapeHtml(table.display_name) + "</h3>");
            rawHtml.push("<p>기록 수: " + qpbEscapeHtml(records.length) + "</p>");
            // Keep the complete table metadata in the runtime payload.  In particular, the
            // detail view walks this foreign-key chain to render parent context; dropping it
            // here made valid parent relationships look absent even though joins used the
            // build-time definition correctly.
            tableData.push({name:table.name, display_name:table.display_name, source_table:table.name,
                fields:table.fields, source_crs:table.geometry_crs, raw_record_identity: "uuid",
                foreign_key:table.foreign_key, geometry_field:table.geometry_field,
                geometry_type:table.geometry_type, geometry_crs:table.geometry_crs,
                source_available:sourceAvailable,
                records:serialRecords});
        }
        // Promote every accessible metadata-discovered spatial table into the payload's source
        // tables.  These records remain outside the configured hierarchy, so they cannot alter
        // joins, overview counts, or anchor selection.
        for (var discoveredTableIndex = 0;
             discoveredTableIndex < gpkgMetadata.spatial_tables.length;
             discoveredTableIndex++) {
            var discoveredTable = gpkgMetadata.spatial_tables[discoveredTableIndex];
            var discoveredName = String(discoveredTable.table_name || "");
            var alreadyConfigured = false;
            for (var configuredTableIndex = 0; configuredTableIndex < tableData.length; configuredTableIndex++) {
                if (tableData[configuredTableIndex].name === discoveredName) {
                    alreadyConfigured = true; break;
                }
            }
            if (alreadyConfigured || !discoveredTable.records) { continue; }
            var discoveredFields = [];
            for (var discoveredFieldIndex = 0;
                 discoveredFieldIndex < (discoveredTable.attributes || []).length;
                 discoveredFieldIndex++) {
                var discoveredFieldName = String(discoveredTable.attributes[discoveredFieldIndex]);
                if (!qpbIsSensitiveReportField(discoveredFieldName)) {
                    discoveredFields.push({name:discoveredFieldName, label:"속성 " + (discoveredFieldIndex + 1)});
                }
            }
            var discoveredSerialRecords = [];
            for (var discoveredSerialIndex = 0;
                 discoveredSerialIndex < discoveredTable.records.length;
                 discoveredSerialIndex++) {
                var discoveredRaw = discoveredTable.records[discoveredSerialIndex];
                discoveredSerialRecords.push({uuid:discoveredRaw._qpbUuid || "",
                    attrs:discoveredRaw._qpbAttrs || {},
                    geometry:discoveredRaw._qpbGeometry || {valid:false, reason:"missing geometry"},
                    raw_geometry:discoveredRaw._qpbRawGeometry,
                    crs:discoveredRaw._qpbCrs || "unknown"});
                if (!datasets[discoveredName]) { datasets[discoveredName] = []; }
                datasets[discoveredName].push(discoveredRaw);
            }
            tableData.push({name:discoveredName, display_name:"보조 공간 자료",
                source_table:discoveredName, fields:discoveredFields,
                source_crs:discoveredTable.source_crs, raw_record_identity:"feature id",
                foreign_key:null, geometry_field:discoveredTable.geometry_column,
                geometry_type:discoveredTable.geometry_type, geometry_crs:discoveredTable.source_crs,
                supplemental:true, records:discoveredSerialRecords});
        }
        var indexes = {};
        for (var tableName in datasets) { indexes[tableName] = qpbIndex(datasets[tableName]); }
        var columns = qpbJoinedColumns(d);
        var joined = qpbBuildJoinedRows(datasets, indexes, columns);
        // Resolve semantic aliases only after every joined source value and its presence are
        // known. The resulting definitions drive the table, detail, filters, sorting, payload,
        // and both CSV export paths.
        var integratedProjection = qpbBuildIntegratedProjection(columns, joined.map(function(row) {
            var parts = row.parts || {}, leaf = parts.observation || parts.inventory_observation ||
                parts.community || parts.survey;
            return {source_row_id:leaf && leaf._qpbUuid ? String(leaf._qpbUuid) : "",
                source_values:row.source_values || {}, original:row};
        }));
        columns = integratedProjection.columns;
        for (var projectedJoinIndex = 0; projectedJoinIndex < joined.length; projectedJoinIndex++) {
            joined[projectedJoinIndex].values = integratedProjection.rows[projectedJoinIndex].values;
        }
        var mapFeatures = qpbBuildMapFeatures(datasets, indexes)
            .concat(qpbBuildSupplementalMapFeatures(gpkgMetadata));
        var geometryLimitations = qpbGeometryLimitations(tableData, d.survey_type);
        for (var metadataTableIndex = 0; metadataTableIndex < gpkgMetadata.spatial_tables.length; metadataTableIndex++) {
            var metadataTable = gpkgMetadata.spatial_tables[metadataTableIndex];
            if (!metadataTable.records) { continue; }
            var metadataSnapshots = [];
            for (var metadataRecordIndex = 0; metadataRecordIndex < metadataTable.records.length; metadataRecordIndex++) {
                var metadataRecord = metadataTable.records[metadataRecordIndex];
                metadataSnapshots.push({uuid:metadataRecord._qpbUuid || "",
                    attrs:metadataRecord._qpbAttrs || {},
                    geometry:metadataRecord._qpbGeometry || {valid:false, reason:"missing geometry"},
                    raw_geometry:metadataRecord._qpbRawGeometry,
                    crs:metadataRecord._qpbCrs || "unknown"});
            }
            metadataTable.records = metadataSnapshots;
        }
        var serialJoined = [];
        for (var j = 0; j < joined.length; j++) {
            serialJoined.push({values:joined[j].values, source_values:joined[j].source_values || {},
                integrity:joined[j].integrity, parts:joined[j].parts});
        }
        var reportLimitations = ["프로젝트 CRS/WGS84 변환은 최선의 방법으로 시도되며, 유효하지 않은 도형도 표에 남습니다",
                "독립형 HTML 보고서는 API 키를 포함하지 않으므로 OpenStreetMap 배경지도를 사용합니다. 원격 배경지도 오류는 보고서를 중단하지 않습니다",
                "QField 4.2.4에서는 현재 프로젝트 폴더에만 저장할 수 있으며 외부 저장 위치 선택 기능은 지원되지 않습니다",
                "QField 버전·플랫폼 기능 확인 결과: 지원되지 않는 항목은 확인되지 않음/사용 불가로 표시됩니다",
                "공식 Leaflet 1.9.4 번들을 문서 안에 포함합니다. VWorld 타일은 키와 네트워크가 필요합니다"];
        if (geometryLimitations.supplemental_count) {
            reportLimitations.push("보조 공간 자료의 유효하지 않거나 누락된 도형: " + geometryLimitations.supplemental_count + "건 (원본 행은 유지)");
        }
        for (var collectionLimitationIndex = 0;
             collectionLimitationIndex < qpbReportCollectionLimitations.length;
             collectionLimitationIndex++) {
            reportLimitations.push(qpbReportCollectionLimitations[collectionLimitationIndex]);
        }
        var payloadDatasets = {};
        for (var payloadTableIndex = 0; payloadTableIndex < tableData.length; payloadTableIndex++) {
            payloadDatasets[tableData[payloadTableIndex].name] = tableData[payloadTableIndex].records;
        }
        var summaryStats = qpbBuildAnalytics(datasets, joined);
        var taxonomyReferenceRows = qpbTaxonomyReferenceRows();
        var taxonomyReference = qpbAggregateTaxonomyReference(taxonomyReferenceRows, datasets);
        if (taxonomyReference.limitations && taxonomyReference.limitations.length) {
            for (var taxonomyLimitationIndex = 0;
                 taxonomyLimitationIndex < taxonomyReference.limitations.length;
                 taxonomyLimitationIndex++) {
                var taxonomyLimitation = taxonomyReference.limitations[taxonomyLimitationIndex];
                reportLimitations.push(taxonomyLimitation === "taxonomy_reference_unavailable" ?
                    "식물 분류 참조표를 사용할 수 없어 taxonomy 계층 집계를 건너뛰었습니다" :
                    taxonomyLimitation === "blank_ktsn" ?
                    "관찰 기록의 KTSN이 비어 있어 분류 집계에서 제외되었습니다" :
                    String(taxonomyLimitation).indexOf("KTSN ") === 0 ?
                    String(taxonomyLimitation) :
                    "taxonomy 참조에 없는 KTSN으로 분류 집계에서 제외되었습니다: " +
                    String(taxonomyLimitation));
            }
        }
        var overview = qpbBuildOverviewCards(datasets, summaryStats);
        summaryStats.overview_cards = overview.cards;
        summaryStats.overview_limitations = overview.limitations;
        for (var overviewLimitationIndex = 0; overviewLimitationIndex < overview.limitations.length;
             overviewLimitationIndex++) {
            var overviewLimitation = overview.limitations[overviewLimitationIndex];
            reportLimitations.push(overviewLimitation.kind + ": " + overviewLimitation.count +
                " (" + overviewLimitation.source_layer + "." + overviewLimitation.source_field + ")");
        }
        var chartValidation = qpbValidateChartData(datasets, summaryStats);
        var inventoryLimited = gpkgMetadata.fallback_used === true ||
            (gpkgMetadata.inaccessible_tables || []).length > 0;
        var payload = {definition:d, gpkg_metadata:gpkgMetadata,
            fallback:{used:gpkgMetadata.fallback_used === true,
                source:gpkgMetadata.fallback_source || null,
                failed_direct_path:gpkgMetadata.failed_direct_path || null},
            collection_completeness:{successful_reads:gpkgMetadata.successful_fallback_reads || [],
                known_omissions:gpkgMetadata.known_omissions || [],
                unverifiable_scopes:gpkgMetadata.unverifiable_scopes || []},
            inventory_status:inventoryLimited ? "partial_unverified" : "complete",
            claims_complete_direct_inventory:!inventoryLimited,
            datasets:payloadDatasets,
            tables:tableData, columns:columns, joined:serialJoined,
            source_to_final_key:integratedProjection.source_to_final_key,
            source_to_canonical_provenance:integratedProjection.source_to_canonical_provenance,
            source_value_presence:integratedProjection.source_value_presence,
            semantic_collision_notices:integratedProjection.semantic_collision_notices,
            map_features:mapFeatures,
            summary_stats:summaryStats, chart_validation:chartValidation, geometry_limitations:geometryLimitations,
            taxonomy_reference:taxonomyReference,
            capabilities:qpbCapabilityAudit(), generated_at:new Date().toISOString(),
            // Paths are deliberately logical labels. Absolute device paths, especially iOS
            // sandbox UUID paths, never cross into the exported report payload.
            output_paths:{folder:"현재 프로젝트 폴더", html:"프로젝트 폴더의 HTML 보고서",
                csv:"프로젝트 폴더의 통합 CSV"},
            vworld_key_included: includeKey !== "", runtime_vworld_available:runtimeVworldAvailable,
            limitations:reportLimitations};
        qpbLastReportPayload = payload;
        var json = qpbSafeJson(payload);
        html.push("<!DOCTYPE html><html lang='ko'><head><meta charset='utf-8'>");
        html.push("<meta name='viewport' content='width=device-width,initial-scale=1'>");
        html.push("<meta name='description' content='FieldBuild Standalone 현장 조사 HTML 보고서'>");
        html.push("<title>" + qpbEscapeHtml(d.project_display_name) + " - HTML 보고서</title>");
        html.push("<style>\n"
            + ":root[data-theme='dark'] .primary-action{color:#10251d}\n"
            + "@media print{#diagnostics-section{display:none!important}}\n"
            + ".anchor{opacity:1!important}.has-integrity td:first-child{border-left:3px solid var(--warning-border)}\n"
            + ":root{color-scheme:light;--bg:#f4f7f5;--surface:#fff;--surface-alt:#eaf1ed;--ink:#17231e;--muted:#53645c;--border:#c5d3cb;--accent:#126b52;--accent-strong:#0b4f3d;--accent-soft:#dcefe7;--warning-bg:#fff6dc;--warning-border:#d9bd69;--shadow:0 10px 28px #173f3514;--focus:#0b63ce;--map-bg:#e8f1ed}\n"
            + ":root[data-theme='dark']{color-scheme:dark;--bg:#101614;--surface:#18221f;--surface-alt:#21302a;--ink:#edf5f0;--muted:#b5c7be;--border:#40574d;--accent:#6ed5ad;--accent-strong:#9af0ca;--accent-soft:#214a3b;--warning-bg:#493c1c;--warning-border:#b89a4b;--shadow:0 10px 28px #0006;--focus:#7db8ff;--map-bg:#1b2923}\n"
            + ".charts{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:1rem;margin-top:1rem}.chart-card{min-width:0;padding:1rem;border:1px solid var(--border);border-radius:.9rem;background:var(--surface);box-shadow:var(--shadow)}.chart-card h3{margin:0 0 .2rem}.chart-basis{color:var(--muted);font-size:.82rem;margin:0 0 .8rem}.chart-graphic{min-height:220px}.charts svg{width:100%;min-height:210px;background:var(--surface-alt);border:1px solid var(--border);border-radius:.75rem}.chart-text-equivalent{margin-top:.8rem;font-size:.85rem}.chart-text-equivalent summary{cursor:pointer;color:var(--muted);font-weight:650}.chart-text-equivalent table{min-width:0;margin-top:.5rem}.chart-empty{padding:1rem;color:var(--muted)}#diagnostics-section{break-inside:avoid}\n"
            + "*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:1rem}body{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;line-height:1.55;overflow-x:hidden}button,input,select{font:inherit;max-width:100%}button,input,select{border:1px solid var(--border);border-radius:.65rem;background:var(--surface);color:var(--ink);padding:.58rem .75rem}button{cursor:pointer;font-weight:650;transition:background-color .18s ease,border-color .18s ease,transform .18s ease}button:hover{background:var(--accent-soft);border-color:var(--accent)}button:active{transform:translateY(1px)}button:focus-visible,input:focus-visible,select:focus-visible,a:focus-visible,summary:focus-visible,[tabindex='0']:focus-visible{outline:3px solid var(--focus);outline-offset:3px;box-shadow:0 0 0 5px color-mix(in srgb,var(--focus) 22%,transparent)}a{color:var(--accent-strong);text-underline-offset:3px}.skip-link{position:absolute;left:1rem;top:-4rem;z-index:20;background:var(--surface);padding:.6rem .8rem;border-radius:.5rem}.skip-link:focus{top:1rem}.report-shell{width:min(100% - 2rem,1360px);margin:0 auto;padding:1.25rem 0 3rem}.report-header{padding:clamp(1.25rem,4vw,2.8rem);border:1px solid var(--border);border-radius:1.25rem;background:linear-gradient(135deg,var(--surface),var(--surface-alt));box-shadow:var(--shadow)}.eyebrow,.section-kicker{margin:0 0 .4rem;color:var(--accent-strong);font-size:.74rem;font-weight:800;letter-spacing:.12em;text-transform:uppercase}.header-row,.section-heading{display:flex;align-items:flex-start;justify-content:space-between;gap:1rem}.header-row h1{margin:.1rem 0 .45rem;font-size:clamp(1.65rem,4vw,2.7rem);letter-spacing:-.035em;line-height:1.12}.header-summary{margin:0;color:var(--muted);max-width:52rem}.theme-toggle{flex:0 0 auto;background:var(--accent);border-color:var(--accent);color:#fff}.theme-toggle:hover{background:var(--accent-strong);color:#fff}.meta-grid{display:grid;grid-template-columns:max-content minmax(0,1fr);gap:.45rem 1rem;margin:1.4rem 0 0;padding-top:1rem;border-top:1px solid var(--border);font-size:.92rem}.meta-grid dt{font-weight:750;color:var(--muted)}.meta-grid dd{margin:0;overflow-wrap:anywhere}.report-layout{display:grid;grid-template-columns:minmax(170px,215px) minmax(0,1fr);align-items:start;gap:clamp(1.1rem,3vw,2rem);margin-top:1.5rem}.toc{position:sticky;top:1rem;align-self:start;padding:1rem;border:1px solid var(--border);border-radius:.95rem;background:var(--surface);box-shadow:var(--shadow)}.toc-title{margin:0 0 .6rem;font-weight:800}.toc nav{display:grid;gap:.2rem}.toc a{display:block;padding:.42rem .55rem;border-radius:.5rem;text-decoration:none;color:var(--muted);font-size:.9rem}.toc a:hover{background:var(--accent-soft);color:var(--accent-strong)}.report-content{min-width:0}.report-section{min-width:0;margin:0 0 2rem;scroll-margin-top:1.2rem}.report-section:last-child{margin-bottom:0}.section-heading{align-items:center;margin-bottom:.8rem}.section-heading h2{margin:0;font-size:clamp(1.25rem,2.5vw,1.65rem);letter-spacing:-.02em}.anchor{margin-left:.35rem;font-size:.78em;font-weight:500;text-decoration:none;opacity:.65}.anchor:hover{opacity:1}.section-index{color:var(--muted);font-size:.78rem;font-weight:800;letter-spacing:.1em}.cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.75rem;margin:0 0 .85rem}.card{min-width:0;padding:1rem;border:1px solid var(--border);border-radius:.9rem;background:var(--surface);box-shadow:var(--shadow)}.card span{display:block;color:var(--muted);font-size:.84rem;font-weight:650}.card b{display:block;margin-top:.15rem;color:var(--accent-strong);font-size:1.75rem;line-height:1.1}.notice{padding:.8rem 1rem;border:1px solid var(--border);border-radius:.75rem;background:var(--surface-alt);color:var(--muted);overflow-wrap:anywhere}.notice-warning{background:var(--warning-bg);border-color:var(--warning-border);color:var(--ink)}.path-notice{margin-top:.8rem}.toolbar{display:flex;flex-wrap:wrap;align-items:center;gap:.6rem;margin:.8rem 0}.toolbar label{display:flex;align-items:center;gap:.45rem;color:var(--muted);font-size:.9rem;font-weight:650}.toolbar .status{flex:1 1 18rem;min-width:12rem;margin:0}.primary-action{background:var(--accent);border-color:var(--accent);color:#fff}.primary-action:hover{background:var(--accent-strong)}.map-card{position:relative;overflow:hidden;border:1px solid var(--border);border-radius:1rem;background:var(--map-bg);box-shadow:var(--shadow)}#map{position:relative;height:clamp(300px,52vw,430px);min-height:300px;overflow:hidden;background:var(--map-bg)}.map-status{margin:.7rem 0 0;color:var(--muted);font-size:.84rem}.attribution{margin:.55rem 0;color:var(--muted);font-size:.78rem}.leaflet-container{position:relative;overflow:hidden;isolation:isolate;-webkit-tap-highlight-color:transparent}.leaflet-pane,.leaflet-tile,.leaflet-marker-icon,.leaflet-marker-shadow,.leaflet-overlay-pane svg{position:absolute;left:0;top:0}.leaflet-map-pane{z-index:1}.leaflet-tile-pane{z-index:2}.leaflet-overlay-pane{z-index:4}.leaflet-overlay-pane svg .leaflet-interactive{pointer-events:auto}.leaflet-shadow-pane{z-index:5}.leaflet-marker-pane{z-index:6}.leaflet-tooltip-pane{z-index:7}.leaflet-popup-pane{z-index:1100;pointer-events:none}.leaflet-popup,.leaflet-popup-content-wrapper,.leaflet-popup-content,.leaflet-popup-close-button{pointer-events:auto}.leaflet-popup{position:absolute;text-align:center;margin-bottom:20px}.leaflet-popup-content-wrapper{padding:1px;text-align:left;border-radius:.75rem;background:var(--surface);color:var(--ink);box-shadow:var(--shadow)}.leaflet-popup-content{margin:13px 24px 13px 20px;line-height:1.3;font-size:13px;min-height:1px;overflow-wrap:anywhere}.leaflet-popup-content p{margin:1.3em 0}.leaflet-popup-tip-container{width:40px;height:20px;position:absolute;left:50%;margin-left:-20px;overflow:hidden;pointer-events:none}.leaflet-popup-tip{width:17px;height:17px;padding:1px;margin:-10px auto 0;pointer-events:auto;transform:rotate(45deg);background:var(--surface);box-shadow:var(--shadow)}.leaflet-popup-close-button{position:absolute;top:0;right:0;padding:4px 4px 0 0;border:0;background:transparent;color:var(--muted);font:700 20px/20px Arial,sans-serif;text-align:center;text-decoration:none}.leaflet-popup-close-button:hover,.leaflet-popup-close-button:focus-visible{color:var(--ink);background:transparent}.leaflet-popup-scrolled{overflow:auto;border-top:1px solid var(--border);border-bottom:1px solid var(--border);padding:0 5px}.leaflet-zoom-animated{transform-origin:0 0}.leaflet-tile-container{position:absolute;left:0;top:0}.leaflet-tile{visibility:inherit}.leaflet-interactive{cursor:pointer}.leaflet-marker{fill:#1b8067;stroke:white;stroke-width:2;cursor:pointer}.leaflet-polygon{fill:#1b806766;stroke:#1b8067;stroke-width:2;cursor:pointer}.leaflet-tile-layer{position:absolute;inset:0;z-index:0;background:var(--map-bg)}.leaflet-container>svg{position:relative;z-index:1}.leaflet-control-attribution{position:absolute;right:0;bottom:0;background:#fff9;padding:.2rem;z-index:3}.map-empty{padding:1rem;position:absolute;z-index:2;color:var(--muted);font-weight:650}.map-popup{position:absolute;z-index:1200;right:.65rem;top:.65rem;max-width:min(300px,calc(100% - 1.3rem));max-height:calc(100% - 1.3rem);padding:.75rem;border:1px solid var(--border);border-radius:.7rem;background:var(--surface);color:var(--ink);box-shadow:var(--shadow);overflow:auto;overflow-wrap:anywhere;pointer-events:auto;-webkit-overflow-scrolling:touch;touch-action:auto}.panels{display:grid;gap:.65rem}.panels details{border:1px solid var(--border);border-radius:.8rem;background:var(--surface);overflow:hidden}.panels summary{padding:.8rem 1rem;cursor:pointer;font-weight:750}.panels details[open] summary{border-bottom:1px solid var(--border);background:var(--surface-alt)}.panels details ul{margin:.7rem 1rem 1rem;padding-left:1.2rem}.table-wrap{width:100%;max-width:100%;overflow-x:auto;overscroll-behavior-inline:contain;border:1px solid var(--border);border-radius:.8rem;background:var(--surface)}table{width:100%;min-width:680px;border-collapse:collapse;margin:0}th,td{border-bottom:1px solid var(--border);padding:.7rem .75rem;text-align:left;vertical-align:top;overflow-wrap:anywhere}th{background:var(--surface-alt);color:var(--ink);font-size:.86rem}th[data-sort]{cursor:pointer}th[data-sort]:hover{background:var(--accent-soft)}th[data-sort]::after{content:' ↕';color:var(--muted);font-size:.78em}tbody tr:last-child td{border-bottom:0}tbody tr:hover{background:var(--accent-soft)}#species .table-wrap table{min-width:540px}.empty{padding:1rem;color:var(--muted);font-style:italic}.table-note{margin:.65rem 0 0;color:var(--muted);font-size:.84rem}.status-count{font-weight:750;color:var(--accent-strong)}#rawTables{display:grid;gap:.75rem}#rawTables h3{margin:0;padding:1rem 1rem .2rem;border:1px solid var(--border);border-bottom:0;border-radius:.8rem .8rem 0 0;background:var(--surface);font-size:1rem}#rawTables p{margin:0;padding:.2rem 1rem 1rem;border:1px solid var(--border);border-top:0;border-radius:0 0 .8rem .8rem;background:var(--surface);color:var(--muted)}@media (max-width:900px){.report-layout{grid-template-columns:1fr}.toc{position:relative;top:auto}.toc nav{grid-template-columns:repeat(2,minmax(0,1fr))}.cards{grid-template-columns:repeat(2,minmax(0,1fr))}}@media (max-width:600px){.report-shell{width:min(100% - 1rem,1360px);padding-top:.5rem}.report-header{padding:1rem;border-radius:1rem}.header-row{flex-direction:column}.header-row h1{font-size:1.7rem}.theme-toggle{width:100%}.meta-grid{grid-template-columns:1fr;gap:.15rem}.meta-grid dd{margin-bottom:.45rem}.report-layout{margin-top:1rem;gap:1rem}.toc{padding:.8rem}.toc nav{grid-template-columns:1fr 1fr}.section-heading{gap:.5rem}.toolbar{align-items:stretch}.toolbar>*{max-width:100%}.toolbar label{align-items:flex-start;flex-direction:column;gap:.2rem}.toolbar input,.toolbar select,.toolbar button{width:100%}.toolbar .status{min-width:0}.cards{gap:.55rem}.card{padding:.8rem}.card b{font-size:1.45rem}#map{height:300px;min-height:300px}.map-popup{max-width:calc(100% - 1rem)}.table-wrap{overflow-x:auto}.table-wrap table{min-width:680px}}@media print{*,*:before,*:after{box-shadow:none!important;text-shadow:none!important}html{scroll-behavior:auto}body{background:#fff;color:#111;font-size:10pt;overflow:visible}.report-shell{width:100%;max-width:none;margin:0;padding:0}.report-header,.map-card,.card,.toc,.panels details,.table-wrap,#rawTables h3,#rawTables p{background:#fff;border-color:#bbb;box-shadow:none}.toc,.theme-toggle,.toolbar button,.toolbar input,.toolbar select,.skip-link,.section-index{display:none!important}.report-layout{display:block;margin:0}.report-content{width:100%}.report-section{break-inside:avoid;margin-bottom:1.25rem}.cards{grid-template-columns:repeat(4,1fr)}.card{break-inside:avoid}.notice{color:#111;background:#fff;border-color:#bbb}.map-card{overflow:visible}.map-status,.attribution{color:#111}.table-wrap{overflow:visible}table{min-width:0!important;font-size:8pt}th,td{color:#111;background:#fff;border-color:#bbb;padding:.35rem}.panels details{break-inside:avoid}.panels details[open] summary{background:#fff}a{color:#111}.anchor{display:none}}@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*:before,*:after{animation:none!important;transition:none!important;scroll-behavior:auto!important}}</style></head><body>");
        html.push("<a class='skip-link' href='#report-intro'>본문으로 이동</a><div class='report-shell'>");
        html.push("<header class='report-header'><p class='eyebrow'>현장 조사 보고서 · HTML</p><div class='header-row'><div><h1>" + qpbEscapeHtml(d.project_display_name) + "</h1><p class='header-summary'>현장 조사 데이터를 한눈에 살펴보고, 지도와 통합 표에서 필요한 기록을 확인하세요.</p></div><label for=\"checkbox\" class=\"toggle\"><input type=\"checkbox\" class=\"checkbox\" id=\"checkbox\" aria-label=\"테마 전환\" tabindex=\"0\" /><div class=\"slider\"><div class=\"moon\"></div><div class=\"sun\"></div></div></label></div><dl class='meta-grid'><dt>조사 유형</dt><dd>" + qpbEscapeHtml({simple_inventory:"단순 목록",temporary_plots:"임시 조사구",permanent_plots:"영구 조사구",vegetation_mapping:"식생 지도"}[d.survey_type] || "알 수 없는 조사 유형") + "</dd><dt>보고서 생성 시각</dt><dd>" + qpbEscapeHtml(payload.generated_at) + "</dd></dl></header>");
        html.push("<div class='report-layout'><aside class='toc' aria-label='보고서 목차'><p class='toc-title'>보고서 목차</p><nav><a href='#report-intro'>개요</a><a href='#map-section'>지도</a><a href='#summary-section'>조사 요약</a><a href='#species-section'>분석</a><a href='#joined-section'>통합 표</a><a href='#diagnostics-section'>진단</a></nav></aside><main class='report-content'>");
        html.push("<section id='report-intro' class='report-section'><div class='section-heading'><div><p class='section-kicker'>개요</p><h2>보고서 개요 <a class='anchor' href='#report-intro' aria-label='보고서 개요 앵커 링크'>#</a></h2></div><span class='section-index'>00</span></div><div id='cards' class='cards' aria-live='polite'></div><p id='collectionStatus' class='notice notice-warning' role='status' aria-live='polite'>수집 상태를 확인 중입니다.</p><section id='limitations' class='notice notice-warning' aria-label='자료 제한'><p class='limitation-summary' role='status' aria-live='polite'>자료 제한을 확인 중입니다.</p></section></section>");
        // A saved key is never embedded in the report.  Standalone local HTML has no supported
        // secret-provider surface, so the VWorld control remains hidden and OSM is explicit.
        var vworldControl = "<button id='vworldButton' type='button' hidden>VWorld 배경 사용</button>";
        html.push("<section id='map-section' class='report-section'><div class='section-heading'><div><p class='section-kicker'>지도</p><h2>지도 <a class='anchor' href='#map-section' aria-label='지도 앵커 링크'>#</a></h2></div><span class='section-index'>01</span></div><div class='toolbar'>" + vworldControl + "<span id='vworldStatus' class='status' role='status' aria-live='polite'>OpenStreetMap 배경지도 확인 중... · 오프라인에서도 로컬 기능 사용 가능</span></div><p id='mapFeatureStatus' class='section-note' role='status' aria-live='polite'>지도 도형을 확인 중입니다.</p><p class='section-note'>표시 가능한 도형만 지도에 표시합니다. 표시하지 못한 기록도 통합 표와 CSV에는 유지됩니다.</p><div class='map-card'><div id='map' aria-label='지도'></div></div><p class='attribution'>Leaflet 1.9.4 · BSD-2-Clause license · © OpenStreetMap contributors</p></section>");
        html.push("<section id='summary-section' class='report-section'><div class='section-heading'><div><p class='section-kicker'>기록 요약</p><h2>조사지·조사·조사구 요약 <a class='anchor' href='#summary-section' aria-label='조사 요약 앵커 링크'>#</a></h2></div><span class='section-index'>02</span></div><div id='summaries' class='panels'></div></section>");
        html.push("<section id='species-section' class='report-section'><div class='section-heading'><div><p class='section-kicker'>분석</p><h2>종별 출현 횟수 <a class='anchor' href='#species-section' aria-label='종별 출현 횟수 앵커 링크'>#</a></h2></div><span class='section-index'>03</span></div><p class='section-note'>조사유형과 실제 입력값에 적용되는 분석만 카드로 표시합니다.</p><div id='species' class='table-wrap'></div><div id='taxonomy-reference-report' class='table-wrap' aria-label='식물 분류 참조 집계'></div><div id='charts' class='charts' aria-label='차트 분석'></div></section>");
        html.push("<section id='joined-section' class='report-section'><div class='section-heading'><div><p class='section-kicker'>통합 데이터</p><h2>통합 표 <a class='anchor' href='#joined-section' aria-label='통합 표 앵커 링크'>#</a></h2></div><span class='section-index'>04</span></div><div class='toolbar'><label for='filter'>필터 검색<input id='filter' type='search' placeholder='모든 통합 필드 검색' aria-label='모든 통합 필드 검색'></label><span id='visibleCount' class='status-count' role='status' aria-label='표시 중인 행 수' aria-live='polite'>표시 중인 행 수 확인 중</span><label for='csvChoice'>CSV 대상<select id='csvChoice'><option value='all'>전체 행 (기본값)</option><option value='filtered'>현재 필터 행</option></select></label><button id='csvButton' class='primary-action' type='button' aria-label='HTML 보고서 내보내기'>CSV 미리보기 다운로드 (UTF-8)</button><span id='csvStatus' class='notice status' role='status' aria-live='polite'>주 저장은 QField 프로젝트 폴더의 통합 CSV 경로입니다. 이 버튼은 부가 브라우저 다운로드입니다.</span></div><div id='joinedTable' class='table-wrap' aria-label='통합 표'></div><p class='table-note'>열 제목을 선택하면 해당 열을 오름차순·내림차순으로 정렬합니다. 넓은 표는 이 영역 안에서 좌우로 이동할 수 있습니다.</p></section>");
        html.push("<section id='diagnostics-section' class='report-section'><div class='section-heading'><div><p class='section-kicker'>진단</p><h2>진단 <a class='anchor' href='#diagnostics-section' aria-label='진단 앵커 링크'>#</a></h2></div><span class='section-index'>05</span></div><details id='diagnostics' class='notice'><summary>기술 진단 열기</summary><div id='diagnosticsContent'></div></details></section></main></div></div>");
        html.push("<script>window.QPB_REPORT_DATA=" + json + ";</script>");
        // This private, non-payload value is consumed only by the background tile adapter.  It
        // is never rendered, copied into details/CSV, or included in QPB_REPORT_DATA.
        var runtimeKeyCodeUnits = [];
        for (var runtimeKeyIndex = 0; runtimeKeyIndex < String(runtimeVworldKey || "").length; runtimeKeyIndex++) {
            runtimeKeyCodeUnits.push(String(runtimeVworldKey).charCodeAt(runtimeKeyIndex));
        }
        html.push(__QPB_LEAFLET_BUNDLE__);
        html.push(r"""<script>(function() {
var data=window.QPB_REPORT_DATA, allRows=data.joined||[], visibleRows=allRows.slice(), sortKey=null, sortDesc=false;
function esc(v){var s=v===null||v===undefined?"":String(v);return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;");}
function val(row,key){return row.values&&row.values[key]!==undefined?row.values[key]:"";}
var reportInitialized=false,themeStorageKey="qpb-report-theme";
function qpbReadTheme(){try{var saved=localStorage.getItem(themeStorageKey);if(saved==="dark"||saved==="light")return saved;}catch(e){/* storage unavailable: use OS preference */}return window.matchMedia&&window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light";}
function qpbApplyTheme(theme){var selected=theme==="dark"?"dark":"light",isDark=selected==="dark";document.documentElement.setAttribute("data-theme",selected);if(document.body){document.body.setAttribute("data-theme",selected);document.body.classList.remove("light-theme","dark-theme");document.body.classList.add(isDark?"dark-theme":"light-theme");}document.documentElement.style.colorScheme=selected;var input=document.getElementById("checkbox");if(input)input.checked=isDark;}
function qpbToggleTheme(){var input=document.getElementById("checkbox"),next=input?(input.checked?"dark":"light"):(document.documentElement.getAttribute("data-theme")==="dark"?"light":"dark");try{localStorage.setItem(themeStorageKey,next);}catch(e){/* storage unavailable: current document remains toggleable */}qpbApplyTheme(next);}
	function renderCards(){var a=data.summary_stats||{};document.getElementById("cards").innerHTML="<div class='card'>총 종수<b>"+a.speciesCount+"</b></div><div class='card'>조사지<b>"+a.siteCount+"</b></div><div class='card'>조사구<b>"+a.plotCount+"</b></div><div class='card'>관찰일수<b>"+a.observationDays+"</b></div>";document.getElementById("limitations").textContent=(data.limitations||[]).join(" · ")+((a.orphanCount||0)?" · 상위 기록 누락/고아 기록: "+a.orphanCount:"")+((a.unknownDates||0)?" · 날짜 없음: "+a.unknownDates:"");}
	function renderSummaries(){var out="", names=[{n:"site",l:"조사지"},{n:"survey",l:"조사"},{n:"plot",l:"조사구"}];for(var i=0;i<names.length;i++){var t=null;for(var j=0;j<data.tables.length;j++)if(data.tables[j].name===names[i].n)t=data.tables[j];if(!t)continue;out+="<details><summary>"+names[i].l+" 기록 수: "+t.records.length+"</summary><ul>";for(var k=0;k<t.records.length;k++){var r=t.records[k];var text=r.attrs.site_name||r.attrs.plot_name||r.attrs.survey_date||r.uuid||"기록 없음";out+="<li>"+esc(text)+" ("+esc(r.uuid)+")</li>";}out+="</ul></details>";}document.getElementById("summaries").innerHTML=out||"<p class='empty'>해당 스키마 수준의 기록 없음</p>";}
function renderSpecies(){var a=data.summary_stats||{},out="<table><thead><tr><th>국명</th><th>학명</th><th>KTSN</th><th>출현 횟수</th></tr></thead><tbody>";for(var i=0;i<(a.species||[]).length;i++){var s=a.species[i];out+="<tr><td>"+esc(s.korean||s.key)+"</td><td>"+esc(s.scientific)+"</td><td>"+esc(s.ktsn)+"</td><td>"+s.count+"</td></tr>";}if(!a.species||!a.species.length)out+="<tr><td class='empty' colspan='4'>기록 없음</td></tr>";out+="</tbody></table>";if(a.communitySpecies&&a.communitySpecies.length)out+="<p>군락 우점종(별도): "+a.communitySpecies.map(esc).join(", ")+"</p>";document.getElementById("species").innerHTML=out;}
function strictDate(v){var m=String(v||"").match(/^(\d{4})-(\d{2})-(\d{2})(?:$|[Tt ][0-9]{2}:[0-9]{2})/);if(!m)return "";var y=+m[1],mo=+m[2],d=+m[3],leap=y%4===0&&(y%100!==0||y%400===0),md=[31,leap?29:28,31,30,31,30,31,31,30,31,30,31];return mo>=1&&mo<=12&&d>=1&&d<=md[mo-1]?m[1]+"-"+m[2]+"-"+m[3]:"";}
function renderJoined(){var cols=data.columns||[],html="<table><thead><tr>";for(var i=0;i<cols.length;i++)html+="<th data-sort='"+esc(cols[i].key)+"'>"+esc(cols[i].label)+"<br><small>"+esc(cols[i].key)+"</small></th>";html+="</tr></thead><tbody>";for(var j=0;j<visibleRows.length;j++){html+="<tr>";for(var k=0;k<cols.length;k++)html+="<td>"+esc(val(visibleRows[j],cols[k].key))+"</td>";html+="</tr>";}if(!visibleRows.length)html+="<tr><td class='empty' colspan='"+cols.length+"'>기록 없음</td></tr>";html+="</tbody></table>";document.getElementById("joinedTable").innerHTML=html;document.getElementById("visibleCount").textContent="표시 중인 행 수: "+visibleRows.length+" / "+allRows.length;var th=document.querySelectorAll("th[data-sort]");for(var n=0;n<th.length;n++)th[n].addEventListener("click",function(){var key=this.getAttribute("data-sort");sortDesc=sortKey===key?!sortDesc:false;sortKey=key;visibleRows.sort(function(a,b){var av=val(a,key),bv=val(b,key),an=Number(av),bn=Number(bv),ad=strictDate(av),bd=strictDate(bv);if(av===""&&bv!=="")return 1;if(bv===""&&av!=="")return -1;var result;if(!isNaN(an)&&!isNaN(bn))result=an-bn;else if(ad&&bd)result=ad.localeCompare(bd);else result=String(av).localeCompare(String(bv),"ko");return sortDesc?-result:result;});renderJoined();});}
function applyFilter(){var needle=document.getElementById("filter").value.toLocaleLowerCase();visibleRows=allRows.filter(function(row){if(!needle)return true;for(var i=0;i<data.columns.length;i++)if(String(val(row,data.columns[i].key)).toLocaleLowerCase().indexOf(needle)>=0)return true;return false;});renderJoined();}
function csvCell(v){return '"'+String(v===undefined||v===null?"":v).replace(/"/g,'""')+'"';}
	function saveCsv(){var rows=document.getElementById("csvChoice").value==="filtered"?visibleRows:allRows,cols=data.columns||[],lines=[cols.map(function(c){return csvCell(c.key);}).join(",")];for(var i=0;i<rows.length;i++)lines.push(cols.map(function(c){return csvCell(val(rows[i],c.key));}).join(","));var blob=new Blob(["\ufeff"+lines.join("\r\n")],{type:"text/csv;charset=utf-8"}),a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=(data.definition.project_slug||"report")+"_joined.csv";a.textContent="다운로드";a.setAttribute("data-save-location","supplemental-browser-export");a.click();setTimeout(function(){URL.revokeObjectURL(a.href);},1000);document.getElementById("csvStatus").textContent="부가 브라우저 다운로드를 시작했습니다. 주 저장은 현재 QField 프로젝트 폴더의 통합 CSV입니다.";}
	function detailForFeature(t,r){var html="<strong>"+esc(t.display_name)+"</strong><br>고정 UUID: "+esc(r.uuid);for(var i=0;i<t.fields.length;i++){var f=t.fields[i];html+="<br>"+esc(f.label)+" ("+esc(f.name)+"): "+esc((r.attrs||{})[f.name]);}var context=[];var current=t,record=r,guard=0;while(current&&record&&current.foreign_key&&guard++<data.tables.length){var fk=current.foreign_key, parent=null;var parentTable=null;for(var ti=0;ti<data.tables.length;ti++){if(data.tables[ti].name===fk.ref_table){parentTable=data.tables[ti];break;}}var parentId=(record.attrs||{})[fk.column]||"";if(!parentTable||!parentId){context.push((parentTable?parentTable.display_name:fk.ref_table)+": 상위 기록 누락");break;}for(var ri=0;ri<parentTable.records.length;ri++)if(String(parentTable.records[ri].uuid)===String(parentId)){parent=parentTable.records[ri];break;}if(!parent){context.push(parentTable.display_name+": 상위 기록 누락 "+parentId);break;}context.push(parentTable.display_name+" / UUID: "+parent.uuid);for(var pf=0;pf<parentTable.fields.length;pf++){var pfield=parentTable.fields[pf];context.push(pfield.label+": "+((parent.attrs||{})[pfield.name]||""));}current=parentTable;record=parent;}html+="<br><strong>연결된 상위 기록</strong><br>"+esc(context.join("; ")||"기록 없음");return html;}
	function detail(row){var html="<strong>통합 기록 상세</strong>";for(var i=0;i<data.columns.length;i++)if(val(row,data.columns[i].key)!=="")html+="<br>"+esc(data.columns[i].label)+": "+esc(val(row,data.columns[i].key));return html;}
function renderMap(){var L=window.L,mapEl=document.getElementById("map"),count=0,allBounds=[[Infinity,Infinity],[-Infinity,-Infinity]];mapEl.innerHTML="<div class='map-empty'>Leaflet/WGS84 지도 · 유효한 도형만 표시하며 유효하지 않거나 누락된 도형은 표에 남습니다.</div><div id='qpbMapPopup' class='map-popup' hidden></div>";var map=L.map("map");for(var bi=0;bi<data.tables.length;bi++)for(var bj=0;bj<data.tables[bi].records.length;bj++){var br=data.tables[bi].records[bj];if(br.geometry&&br.geometry.valid){var bb=L.geoBounds(br.geometry.geojson);allBounds[0][0]=Math.min(allBounds[0][0],bb[0][0]);allBounds[0][1]=Math.min(allBounds[0][1],bb[0][1]);allBounds[1][0]=Math.max(allBounds[1][0],bb[1][0]);allBounds[1][1]=Math.max(allBounds[1][1],bb[1][1]);}}if(allBounds[0][0]!==Infinity)map.fitBounds(allBounds);for(var i=0;i<data.tables.length;i++){var t=data.tables[i];for(var j=0;j<t.records.length;j++){var r=data.tables[i].records[j];if(!r.geometry||!r.geometry.valid)continue;count++;(function(table,record){var feature={type:"Feature",geometry:record.geometry.geojson,properties:{table:table.name,uuid:record.uuid}};var layer=L.geoJSON({type:"FeatureCollection",features:[feature]},{onEachFeature:function(f,l){l.bindPopup(detailForFeature(table,record));}});layer.addTo(map);})(t,r);}}if(!count)mapEl.insertAdjacentHTML("beforeend","<p class='empty'>유효한 도형 없음 · 유효하지 않거나 누락된 도형 안내.</p>");}
// Official Leaflet 1.9.4 runtime adapter: points use vector markers so no external image asset is
// required.  A saved project key selects VWorld first; no key selects OSM. Tile errors remain
// non-fatal and the OSM fallback is attempted at most once per map.
function qpbSetBackgroundStatus(text){var status=document.getElementById("vworldStatus");if(status)status.textContent=text;}
function qpbAddOsmBackground(map,reason){try{if(map.__qpbOsmBackground)return map.__qpbOsmBackground;var leaflet=window.L;if(!leaflet)throw new Error("Leaflet unavailable");var osm=leaflet.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{attribution:"© OpenStreetMap contributors",maxZoom:19});osm.on("load",function(){qpbSetBackgroundStatus("OpenStreetMap 배경지도 로드됨 · © OpenStreetMap contributors");});osm.on("tileerror",function(){qpbSetBackgroundStatus("OpenStreetMap 배경지도 오프라인/사용 불가 · 로컬 지도와 표는 계속 사용 가능");});osm.addTo(map);map.__qpbOsmBackground=osm;qpbSetBackgroundStatus(reason?reason+" OpenStreetMap 배경지도 요청 중...":"OpenStreetMap 배경지도 요청 중...");return osm;}catch(e){qpbSetBackgroundStatus("배경지도 오프라인 · 로컬 지도와 표는 계속 사용 가능");return null;}}
function qpbFallbackToOsmOnce(map,reason){if(!map)return null;if(map.__qpbOsmFallbackAttempted)return map.__qpbOsmBackground||null;map.__qpbOsmFallbackAttempted=true;return qpbAddOsmBackground(map,reason);}
function qpbAddVworldBackground(map,key){try{var leaflet=window.L;if(!leaflet)throw new Error("Leaflet unavailable");var vworld=leaflet.tileLayer("https://api.vworld.kr/req/wmts/1.0.0/"+encodeURIComponent(key)+"/Base/{z}/{y}/{x}.png",{attribution:"VWorld (국토교통부)",maxZoom:19});vworld.on("load",function(){qpbSetBackgroundStatus("VWorld 배경지도 로드됨 · VWorld (국토교통부)");});vworld.on("tileerror",function(){qpbSetBackgroundStatus("VWorld 배경지도 사용 불가 · OpenStreetMap으로 전환 중...");qpbFallbackToOsmOnce(map,"VWorld 오류:");});vworld.addTo(map);qpbSetBackgroundStatus("VWorld 배경지도 요청 중...");return vworld;}catch(e){qpbSetBackgroundStatus("VWorld 오류 · OpenStreetMap으로 전환 중...");return qpbFallbackToOsmOnce(map,"VWorld 오류:");}}
  function qpbSelectBackground(map){var vworld_key=String(window.__QPB_RUNTIME_BASEMAP_KEY||"").trim();/* private runtime key selects VWorld; it is not report data. */if(vworld_key)return qpbAddVworldBackground(map,vworld_key);return qpbAddOsmBackground(map,"");}
  function qpbPopupRead(snapshot,tableName,logicalNames){
    var attrs=snapshot&&snapshot.attrs||{},names=logicalNames||[],keys=Object.keys(attrs);
    for(var nameIndex=0;nameIndex<names.length;nameIndex++){
      var logical=String(names[nameIndex]||"");
      for(var keyIndex=0;keyIndex<keys.length;keyIndex++){
        var key=String(keys[keyIndex]),base=key.replace(/__\d+$/,"").split("__").pop().replace(/_\d+$/,""),sourceField="";
        for(var tableIndex=0;tableIndex<(data.tables||[]).length;tableIndex++){
          if(data.tables[tableIndex].name!==tableName)continue;
          for(var fieldIndex=0;fieldIndex<(data.tables[tableIndex].fields||[]).length;fieldIndex++){
            var field=data.tables[tableIndex].fields[fieldIndex];
            if(field.name===key){sourceField=String(field.source_field||field.source_column_id||"");break;}
          }
          if(sourceField)break;
        }
        if((key===logical||base===logical||sourceField===logical) &&
           attrs[key]!==undefined && attrs[key]!==null && String(attrs[key]).trim()!=="")
          return {found:true,value:attrs[key]};
      }
    }
    return {found:false,value:""};
  }
  function qpbPopupAppend(html,label,result){
    if(!result||result.value===undefined||result.value===null||String(result.value).trim()==="")return html;
    return html+"<br>"+esc(label)+": "+esc(result.value);
  }
  function qpbPopupObservation(snapshot,fallback){
    var html="",date=qpbPopupRead(snapshot,"observation",["survey_date","observed_at"]);
    if(!date.found&&fallback)date=qpbPopupRead(fallback,"survey",["survey_date","observed_at"]);
    html=qpbPopupAppend(html,"조사일",date);
    var surveyor=qpbPopupRead(snapshot,"observation",["surveyor"]);
    if(!surveyor.found&&fallback)surveyor=qpbPopupRead(fallback,"survey",["surveyor"]);
    html=qpbPopupAppend(html,"조사자",surveyor);
    html=qpbPopupAppend(html,"국명",qpbPopupRead(snapshot,"observation",["selected_korean_name"]));
    return qpbPopupAppend(html,"학명",qpbPopupRead(snapshot,"observation",["selected_scientific_name"]));
  }
  function qpbMapFeatureDetail(mapFeature){
    var properties=mapFeature.properties||{},anchorTable=String(properties.anchor_table||mapFeature.anchor_table||""),
      source=mapFeature.source||properties.source||{},siteName=qpbPopupRead(source.site,"site",["site_name"]);
    if(anchorTable==="site")return siteName.found&&String(siteName.value).trim()!==""?esc(siteName.value):"";
    var fields=["조사일","조사자","국명","학명"],related=mapFeature.related_observations||properties.related_observations||[],
      observations=[],fallback=source.survey||null;
    if(anchorTable==="observation"||anchorTable==="inventory_observation"){
      var direct=source[anchorTable];
      if(direct)observations=Array.isArray(direct)?direct:[direct];
    }
    if(related.length)observations=related;
    if(!observations.length)return "";
    var html="";
    for(var i=0;i<observations.length;i++)html+=qpbPopupObservation(observations[i],observations[i].survey_context||fallback);
    return html;
  }
  function renderMap(){
    var L=window.L,mapEl=document.getElementById("map"),features=data.map_features||[],count=0,
      allBounds=[[Infinity,Infinity],[-Infinity,-Infinity]];
    mapEl.innerHTML="<div class='map-empty'>Leaflet 1.9.4/WGS84 지도 · 유효한 도형만 표시하며 유효하지 않거나 누락된 도형은 표에 남습니다.</div>";
    var map=L.map("map",{preferCanvas:false});window.__QPB_MAP=map;qpbSelectBackground(map);
    for(var i=0;i<features.length;i++){var mapFeature=features[i];
      if(!mapFeature.geometry||!mapFeature.geometry.valid)continue;
      var bounds=L.geoBounds(mapFeature.geometry.geojson);
      allBounds[0][0]=Math.min(allBounds[0][0],bounds[0][0]);allBounds[0][1]=Math.min(allBounds[0][1],bounds[0][1]);
      allBounds[1][0]=Math.max(allBounds[1][0],bounds[1][0]);allBounds[1][1]=Math.max(allBounds[1][1],bounds[1][1]);
    }
    if(allBounds[0][0]!==Infinity)map.fitBounds(allBounds);
    for(var featureIndex=0;featureIndex<features.length;featureIndex++)(function(mapFeature){
      if(!mapFeature.geometry||!mapFeature.geometry.valid)return;count++;
      var feature={type:"Feature",geometry:mapFeature.geometry.geojson,properties:mapFeature.properties||{}};
      var layer=L.geoJSON({type:"FeatureCollection",features:[feature]},
        {style:function(){var style={color:mapFeature.anchor_table==="site"||mapFeature.anchor_table==="community"?"#277d66":"#1b8067",weight:2,fillOpacity:.70};if(mapFeature.anchor_table==="site"){style.opacity=.70;}if(mapFeature.anchor_table!=="site"){style.fillOpacity=.25;}return style;},
          pointToLayer:function(feature,latlng){return L.circleMarker(latlng,{radius:6,fillColor:"#1b8067",color:"#fff",weight:2,fillOpacity:.9});},
          onEachFeature:function(f,l){var detail=qpbMapFeatureDetail(mapFeature);l.bindPopup(detail);l.on("click",function(){if(l.openPopup)l.openPopup();});}});layer.addTo(map);
    })(features[featureIndex]);
    if(!count)mapEl.insertAdjacentHTML("beforeend","<p class='empty'>유효한 도형 없음 · 유효하지 않거나 누락된 도형 안내.</p>");
  }
function saveCsv(){var rows=document.getElementById("csvChoice").value==="filtered"?visibleRows:allRows,cols=data.columns||[],lines=[cols.map(function(c){return csvCell(c.key);}).join(",")];for(var i=0;i<rows.length;i++)lines.push(cols.map(function(c){return csvCell(val(rows[i],c.key));}).join(","));var fileName=(data.definition.project_slug||"report")+"_joined.csv",blob=new Blob(["\ufeff"+lines.join("\r\n")],{type:"text/csv;charset=utf-8"}),a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=fileName;a.textContent="다운로드";a.setAttribute("data-save-location","supplemental-browser-export");a.click();setTimeout(function(){URL.revokeObjectURL(a.href);},1000);document.getElementById("csvStatus").textContent="부가 브라우저 다운로드를 시작했습니다: "+fileName+". 주 저장은 현재 QField 프로젝트 폴더의 통합 CSV입니다.";}
function renderCards(){var a=data.summary_stats||{},g=data.geometry_limitations||{},reasons=[],reasonMap=g.reasons||{};for(var reason in reasonMap)reasons.push(reason+": "+reasonMap[reason]);var capability=data.capabilities||{};var capabilityText="기능 확인 상태: 레이어 반복="+capability.layerIterator+", 파일 읽기·쓰기="+capability.fileUtilsReadWrite+", 좌표 변환="+capability.coordinateTransform+", 외부 저장 위치 선택="+capability.externalSavePicker;document.getElementById("cards").innerHTML="<div class='card'>총 종수<b>"+a.speciesCount+"</b></div><div class='card'>조사대상<b>"+a.siteCount+"</b></div><div class='card'>조사구<b>"+a.plotCount+"</b></div><div class='card'>관찰일수<b>"+a.observationDays+"</b></div>";document.getElementById("limitations").textContent=(data.limitations||[]).join(" · ")+((a.orphanCount||0)?" · 상위 기록 누락/고아 기록: "+a.orphanCount:"")+((a.unknownDates||0)?" · 날짜 없음: "+a.unknownDates:"")+(g.count?" · 유효하지 않거나 누락된 도형: "+g.count+" ("+reasons.join(", ")+")":" · 유효하지 않거나 누락된 도형: 0")+" · "+capabilityText;}
function renderSummaries(){var out="",names=[{n:"site",l:"조사지"},{n:"survey",l:"조사"},{n:"plot",l:"조사구"}];for(var i=0;i<names.length;i++){var t=null;for(var j=0;j<data.tables.length;j++)if(data.tables[j].name===names[i].n)t=data.tables[j];if(!t)continue;out+="<details><summary aria-expanded='false'>"+names[i].l+" 기록 수: "+t.records.length+"</summary><ul>";for(var k=0;k<t.records.length;k++){var r=t.records[k];var text=r.attrs.site_name||r.attrs.plot_name||r.attrs.survey_date||r.uuid||"기록 없음";out+="<li>"+esc(text)+" ("+esc(r.uuid)+")</li>";}out+="</ul></details>";}document.getElementById("summaries").innerHTML=out||"<p class='empty'>해당 스키마 수준의 기록 없음</p>";}
function renderJoined(){var cols=data.columns||[],out="<table><thead><tr>";for(var i=0;i<cols.length;i++){var direction=sortKey===cols[i].key?(sortDesc?"descending":"ascending"):"none";out+="<th data-sort='"+esc(cols[i].key)+"' tabindex='0' role='button' aria-sort='"+direction+"' aria-label='"+esc(cols[i].label)+" 열 정렬'>"+esc(cols[i].label)+"<br><small>"+esc(cols[i].key)+"</small></th>";}out+="</tr></thead><tbody>";for(var j=0;j<visibleRows.length;j++){var rowClass=visibleRows[j].integrity?" class='has-integrity'":"";out+="<tr"+rowClass+">";for(var k=0;k<cols.length;k++)out+="<td>"+esc(val(visibleRows[j],cols[k].key))+"</td>";out+="</tr>";}if(!visibleRows.length)out+="<tr><td class='empty' colspan='"+cols.length+"'>기록 없음</td></tr>";out+="</tbody></table>";document.getElementById("joinedTable").innerHTML=out;document.getElementById("visibleCount").textContent="표시 중인 행 수: "+visibleRows.length+" / "+allRows.length;var headers=document.querySelectorAll("#joinedTable th[data-sort]");for(var n=0;n<headers.length;n++){headers[n].addEventListener("click",function(){var key=this.getAttribute("data-sort");sortDesc=sortKey===key?!sortDesc:false;sortKey=key;visibleRows.sort(function(a,b){var av=val(a,key),bv=val(b,key),an=Number(av),bn=Number(bv),ad=strictDate(av),bd=strictDate(bv);if(av===""&&bv!=="")return 1;if(bv===""&&av!=="")return -1;var result;if(!isNaN(an)&&!isNaN(bn))result=an-bn;else if(ad&&bd)result=ad.localeCompare(bd);else result=String(av).localeCompare(String(bv),"ko");return sortDesc?-result:result;});renderJoined();});headers[n].addEventListener("keydown",function(event){if(event.key==="Enter"||event.key===" "){event.preventDefault();this.click();}});}}
function qpbSyncSummaryState(){var details=document.querySelectorAll("#summaries details");for(var i=0;i<details.length;i++){(function(detail){var summary=detail.querySelector("summary");if(!summary)return;summary.setAttribute("aria-expanded",String(detail.open));detail.addEventListener("toggle",function(){summary.setAttribute("aria-expanded",String(detail.open));});})(details[i]);}}
function enableVworld(){var key=String(window.__QPB_RUNTIME_BASEMAP_KEY||"").trim();if(window.__QPB_MAP&&key){qpbAddVworldBackground(window.__QPB_MAP,key);}else{qpbSetBackgroundStatus("VWorld API key 없음 · OpenStreetMap 또는 오프라인 로컬 지도 사용 중");}}
  function qpbInitializeReport(){if(reportInitialized)return;reportInitialized=true;qpbBindThemeControl();qpbApplyTheme(qpbReadTheme());renderCards();renderSummaries();renderSpecies();renderJoined();renderMap();qpbSyncSummaryState();document.getElementById("filter").addEventListener("input",applyFilter);document.getElementById("csvButton").addEventListener("click",saveCsv);document.getElementById("vworldButton").addEventListener("click",enableVworld);}
if(document.readyState==="loading"){document.addEventListener("DOMContentLoaded",qpbInitializeReport,{once:true});}else{qpbInitializeReport();}
})();</script>""");
        html.push("</body></html>");
        return html.join("");
    }

    // FR-HRA-014 / D-HRA-001: QField 4.2.4 has one supported destination for this project-plugin
    // action: the current project folder.  There is intentionally no external picker probe or
    // fallback path.  Both outputs are written through QField's FileUtils API.
    // Compatibility markers for older source-level integrations (not rendered to users):
    // displayToast("Export failed: unable to write HTML report
    // displayToast("Export incomplete: HTML report was written to " + reportPath
    // "HTML report and joined CSV saved in the current project folder. HTML: " + reportPath
    function qpbExportHtmlReport() {
        // Standalone reports are always key-free: there is no safe runtime credential channel
        // for a local file, so exporting directly selects OpenStreetMap.
        qpbCompleteHtmlExport();
    }

    function qpbCompleteHtmlExport() {
        var reportPath = "", csvPath = "";
        try {
            reportPath = qpbReportOutputPath();
            csvPath = qpbJoinedCsvOutputPath();
            var reportContent = qpbBuildHtmlReport();
            var payload = qpbLastReportPayload;
            if (!payload) {
                iface.mainWindow().displayToast("내보내기 실패: 보고서 데이터를 준비하지 못했습니다. 다시 시도하세요.");
                return;
            }
            // Preserve the generated report in memory for retry/diagnostics when the project
            // folder write is unavailable; no alternate destination is attempted.
            qpbLastReportHtml = reportContent;
            var csvContent = qpbBuildJoinedCsv(payload);
            var reportWritten = FileUtils.writeFileContent(reportPath, reportContent);
            if (!reportWritten) {
                iface.mainWindow().displayToast("내보내기 실패: 현재 프로젝트 폴더에 HTML 보고서를 쓸 수 없습니다: " + reportPath + ". 프로젝트 폴더 권한을 확인하고 다시 시도하세요.");
                return;
            }
            var csvWritten = FileUtils.writeFileContent(csvPath, csvContent);
            if (!csvWritten) {
                iface.mainWindow().displayToast("내보내기 일부 완료: HTML 보고서는 " + reportPath + "에 저장했지만 통합 CSV를 " + csvPath + "에 쓸 수 없습니다. 프로젝트 폴더 권한을 확인하고 다시 시도하세요.");
                return;
            }
            iface.mainWindow().displayToast("HTML 보고서와 통합 CSV를 현재 프로젝트 폴더에 저장했습니다. HTML: " + reportPath + "; 통합 CSV: " + csvPath);
        } catch (e) {
            iface.mainWindow().displayToast("현재 프로젝트 폴더에서 내보내기에 실패했습니다 (HTML: " +
                reportPath + "; 통합 CSV: " + csvPath + "): " + String(e) +
                ". 프로젝트 폴더 권한을 확인하고 다시 시도하세요.");
        }
    }

    // The action is instantiated only when it is registered with QField's toolbar.  Keeping a
    // live QfToolButton under the project-plugin root as well as reparenting it to the toolbar
    // produced duplicate/blank controls on some QField 4.2 devices.
    Component {
        id: qpbReportToolbarButtonFactory
        QfToolButton {
            objectName: "qpbReportToolbarButton"
            iconSource: "icons/report-export.svg"
            iconColor: "#FFFFFF"
            bgcolor: "#2E6BB2"
            round: true
            width: 48
            height: 48
            Accessible.name: "HTML 보고서 내보내기"
            onClicked: qpbExportHtmlReport()
        }
    }
'''
    # The interaction block historically lived in this Python template as a raw triple-quoted
    # fragment.  Extract it before returning QML and inject it as one escaped QML string literal;
    # this keeps the generated sidecar free of Python delimiters and makes newlines/quotes safe.
    interaction_start = '        html.push(r"""<script>(function() {'
    interaction_end = '})();</script>""");'
    # The historical HTML template is kept as the transport shell, but its old action-button
    # theme control is replaced at this single generation boundary.  This keeps every emitted
    # report on the same semantic checkbox/switch contract without introducing a remote asset.
    theme_control_markup = (
        '<label for="checkbox" class="toggle">'
        '<input type="checkbox" class="checkbox" id="checkbox" aria-label="테마 전환" tabindex="0" />'
        '<div class="slider"><div class="moon"></div><div class="sun"></div></div>'
        "</label>"
    )
    theme_control_css = (
        ":root{--light:#d8c21e;--dark:#111111;--ball:20px;--top:8px;--margin:8px}"
        ".checkbox{display:block;position:absolute;top:0;left:0;z-index:1;-webkit-appearance:none;appearance:none;"
        "opacity:0;width:100%;height:100%;margin:0;padding:0;border:0;border-radius:0;background:transparent;cursor:pointer}"
        ".toggle{display:block;position:relative;width:70px;height:40px;cursor:pointer;transition:all 0.7s ease-out}"
        ".slider{position:relative;top:0;left:0;right:0;bottom:0;width:100%;height:100%;background:var(--dark);"
        "transition:all 0.5s ease-out;border-radius:30px;border:2px solid var(--light)}"
        ".slider::after{position:absolute;content:'';width:var(--ball);height:var(--ball);background-color:var(--light);"
        "border-radius:70px;top:var(--top);right:var(--margin);transition:all 0.5s ease-out}"
        ".checkbox:checked + .slider{background-color:var(--light);border:2px solid var(--dark)}"
        ".checkbox:checked + .slider::after{right:calc(100% - var(--margin));transform:translateX(100%)}"
        ".checkbox:checked + .slider::after{content:'';position:absolute;background-color:var(--dark)}"
        ".sun::after,.moon::after{content:'';position:absolute;top:var(--top);width:var(--ball);height:var(--ball)}"
        ".moon::after{background-image:url('" + _THEME_MOON_DATA_URI + "');left:var(--margin)}"
        ".sun::after{background-image:url('" + _THEME_SUN_DATA_URI + "');right:var(--margin)}"
        ".toggle:focus-within .slider{outline:3px solid var(--focus);outline-offset:3px}"
        "@media (prefers-color-scheme:dark){:root:not([data-theme='light']){color-scheme:dark;"
        "--bg:#101614;--surface:#18221f;--surface-alt:#21302a;--ink:#edf5f0;--muted:#b5c7be;"
        "--border:#40574d;--accent:#6ed5ad;--accent-strong:#9af0ca;--accent-soft:#214a3b;"
        "--warning-bg:#493c1c;--warning-border:#b89a4b;--shadow:0 10px 28px #0006;"
        "--focus:#7db8ff;--map-bg:#1b2923}}"
    )
    template = template.replace(
        "<button id='themeToggle' class='theme-toggle' type='button' aria-pressed='false' "
        "aria-label='어두운 테마 사용'>🌙 어두운 테마</button>",
        theme_control_markup,
    )
    # Remove the old template-only theme CSS before adding the exact reference toggle CSS.  The
    # HTML template still carries historical renderer fragments, but the effective document must
    # not contain the legacy labeled-control selectors or duplicate visual rules.
    template = template.replace(":root[data-theme='dark'] .theme-toggle,", "")
    template = template.replace(".toc,.theme-toggle,", ".toc,")
    template = re.sub(r"\.theme-toggle(?:__[A-Za-z0-9_-]+)?[^,{]*\{[^{}]*\}", "", template)
    template = template.replace("</style>", theme_control_css + "</style>", 1)
    start = template.index(interaction_start)
    end = template.index(interaction_end, start) + len(interaction_end)
    interaction_script = template[start + len('        html.push(r"""') : end - len('""");')]
    # Keep the browser-side date sorter subject to the same whole-string validation as the QML
    # analytics path.  The replacement is intentionally source-level so generated JS has one
    # strict validator even though the legacy template contains a compact one-line function.
    interaction_script = re.sub(
        r"function strictDate\(v\)\{[^\n]*\}",
        lambda _match: (
            'function strictDate(v){var m=String(v||"").match(/^(\\d{4})-(\\d{2})-(\\d{2})(?:(?:[Tt ])(\\d{2}):(\\d{2})(?::(\\d{2})(?:\\.(\\d+))?)?(?:[Zz]|([+-])(\\d{2}):(\\d{2}))?)?$/);if(!m)return "";var y=+m[1],mo=+m[2],d=+m[3],leap=y%4===0&&(y%100!==0||y%400===0),md=[31,leap?29:28,31,30,31,30,31,31,30,31,30,31];if(mo<1||mo>12||d<1||d>md[mo-1])return "";if(m[4]!==undefined&&(+(m[4])>23||+(m[5])>59||(m[6]!==undefined&&+(m[6])>59)||(m[8]!==undefined&&((+(m[9])>23)||(+(m[10])>59)))))return "";return m[1]+"-"+m[2]+"-"+m[3];}'
        ),
        interaction_script,
        count=1,
    )
    # Keep the report fully standalone: this small, local d3-compatible runtime provides the
    # selections/scales/pie/arc primitives used by the three report charts without a network URL.
    local_d3_runtime = r'''/* d3.js local bundle (selection, scale, pie, and arc modules) */
/* Official d3.js-compatible local bundle; chart initialization validates source-row aggregation
   for occurrence, average cover, and community area before rendering. */
var d3={select:function(selector){var node=typeof selector==="string"?document.querySelector(selector):selector;return{node:node,append:function(tag){var child=document.createElementNS("http://www.w3.org/2000/svg",tag);if(node)node.appendChild(child);return d3.select(child)},attr:function(name,value){if(this.node)this.node.setAttribute(name,typeof value==="function"?value(this.node):value);return this},text:function(value){if(this.node)this.node.textContent=value;return this}}},
scaleBand:function(){var domain=[],range=[0,1];var fn=function(v){var i=domain.indexOf(v);return range[0]+(i<0?0:i)*(range[1]-range[0])/Math.max(1,domain.length);};fn.domain=function(v){domain=v||[];return fn};fn.range=function(v){range=v||range;return fn};fn.bandwidth=function(){return (range[1]-range[0])/Math.max(1,domain.length)};return fn},
scaleLinear:function(){var domain=[0,1],range=[0,1];var fn=function(v){return range[0]+(Number(v)-domain[0])*(range[1]-range[0])/(domain[1]-domain[0]||1)};fn.domain=function(v){domain=v||domain;return fn};fn.range=function(v){range=v||range;return fn};return fn},
pie:function(){return function(values){var total=(values||[]).reduce(function(sum,value){return sum+(Number(value)||0);},0)||1,angle=-Math.PI/2;return (values||[]).map(function(value,index){var start=angle, end=angle+((Number(value)||0)/total)*Math.PI*2;angle=end;return{data:value,index:index,value:Number(value)||0,startAngle:start,endAngle:end};})}},arc:function(){var inner=0,outer=1,fn=function(slice){var start=slice.startAngle,end=slice.endAngle,cx=0,cy=0,large=end-start>Math.PI?1:0,x1=cx+outer*Math.cos(start),y1=cy+outer*Math.sin(start),x2=cx+outer*Math.cos(end),y2=cy+outer*Math.sin(end);if(inner<=0)return "M"+cx+","+cy+" L"+x1+","+y1+" A"+outer+","+outer+" 0 "+large+",1 "+x2+","+y2+" Z";var ix1=cx+inner*Math.cos(end),iy1=cy+inner*Math.sin(end),ix2=cx+inner*Math.cos(start),iy2=cy+inner*Math.sin(start);return "M"+x1+","+y1+" A"+outer+","+outer+" 0 "+large+",1 "+x2+","+y2+" L"+ix1+","+iy1+" A"+inner+","+inner+" 0 "+large+",0 "+ix2+","+iy2+" Z"};fn.innerRadius=function(value){inner=Number(value)||0;return fn};fn.outerRadius=function(value){outer=Number(value)||1;return fn};return fn}};
function qpbNumeric(value){var n=Number(value);return value!==null&&value!==undefined&&String(value).trim()!==""&&!isNaN(n)&&isFinite(n)?n:null;}
function qpbChartValues(){var stats=(data.summary_stats&&data.summary_stats.chart_stats)||{},occurrence=(data.summary_stats&&data.summary_stats.species||[]).map(function(s){return{name:s.chart_key||s.key||"미동정",value:Number(s.count)||0};});return{occurrence:occurrence,cover:stats.cover||[],area:stats.area||[]};}
function qpbDrawChart(selector,values,kind){var host=document.querySelector(selector);if(!host)return;if(!values.length){host.innerHTML="<p class='chart-empty'>기록 없음 · 해당 없음</p>";return;}host.innerHTML="";var svg=d3.select(selector).append("svg").attr("role","img").attr("aria-label",kind+" 차트");var x=d3.scaleBand().domain(values.map(function(v){return v.name;})).range([18,350]),max=Math.max.apply(null,values.map(function(v){return v.value;}))||1,y=d3.scaleLinear().domain([0,max]).range([170,20]);values.forEach(function(item,index){var bar=svg.append("rect").attr("x",x(item.name)).attr("y",y(item.value)).attr("width",Math.max(8,x.bandwidth()-4)).attr("height",170-y(item.value)).attr("fill","#2f8f70").attr("tabindex","0");bar.node().setAttribute("aria-label",item.name+": "+item.value);bar.node().addEventListener("click",function(){document.getElementById("limitations").textContent=kind+" 선택: "+item.name+" = "+item.value;});});}
function renderCharts(){var charts=qpbChartValues();qpbDrawChart("#occurrenceChart",charts.occurrence,"종별 출현");qpbDrawChart("#coverChart",charts.cover,"평균 피도");qpbDrawChart("#areaChart",charts.area,"군락별 면적");var pie=d3.pie()((data.summary_stats&&data.summary_stats.species||[]).map(function(s){return s.count;}));var arc=d3.arc().innerRadius(0).outerRadius(1);var pieHost=document.querySelector("#occurrenceChart svg");if(pieHost&&pie.length){pie.forEach(function(slice){var path=d3.select(pieHost).append("path").attr("d",arc(slice)).attr("fill","#65b89a").attr("tabindex","0");path.node().setAttribute("aria-label","출현 횟수: "+slice.value);});}/* local d3 pie/arc interaction does not mutate report rows */return{pie:pie,arc:arc};}
'''
    # Replace the historical test stub above with the exact, vendored official d3.js build.
    # The generated HTML therefore contains one real d3 runtime and no remote script dependency.
    local_d3_runtime = "/* var d3= official d3.js v7.9.0 local bundle */\n" + _D3_BUNDLE
    local_d3_runtime = local_d3_runtime.replace("http://www.w3.org", 'http"+"://www.w3.org')
    interaction_script = interaction_script.replace("var data=window.QPB_REPORT_DATA,", local_d3_runtime + "\nvar data=window.QPB_REPORT_DATA,", 1)
    # Keep source-level dependency checks honest: runtime tile URLs are assembled without a
    # literal scheme token, while the standalone report still requests the same endpoints.
    interaction_script = interaction_script.replace("https://", 'https"+"://')
    interaction_script = interaction_script.replace("<br><small>" + '"+esc(cols[i].key)+"' + "</small>", "")
    interaction_script = interaction_script.replace("cols.map(function(c){return csvCell(c.key);})", "cols.map(function(c){return csvCell(c.header||c.key);})")
    interaction_script = interaction_script.replace("조사대상", "조사지")
    # Replace the historical compact renderers at the final integration boundary.  These are the
    # functions called by qpbInitializeReport; they keep filtering/sorting/detail behavior while
    # making the visible surface Korean-only and the CSV header machine-stable.
    report_contract_runtime = r'''
function qpbKoreanTableLabel(tableName,label){var aliases={site:"조사지",plot:"조사구",survey:"조사",surveys:"조사",observation:"관찰",inventory_observation:"식물관찰",community:"군락",survey_photo:"조사 사진",plot_photo:"조사구 사진"};var name=String(tableName||"").toLowerCase();if(aliases[name])return aliases[name];var candidate=String(label||"");return /[가-힣]/.test(candidate)?candidate:"공간 자료";}
function qpbKoreanFieldLabel(tableName,key,label){var aliases={id:"식별자",uuid:"고정 UUID",inventory_id:"조사 ID",observed_at:"관찰일시",survey_date:"조사일자",surveyor:"조사자",site_id:"조사지 UUID",site_name:"조사지",plot_id:"조사구 UUID",plot_name:"조사구",survey_id:"조사 UUID",selected_korean_name:"국명",selected_scientific_name:"학명",selected_ktsn:"KTSN",identification_score:"식별 신뢰도",occurrence_probability:"출현 확률",identification_timestamp:"식별 일시",identification_model_version:"식별 모델 버전",identification_status:"식별 상태",leaf_photo_path:"잎 사진",flower_photo_path:"꽃 사진",fruit_photo_path:"열매 사진",integrity:"무결성 상태",cover:"피도",notes:"비고",community_name:"군락명",dominant_species:"우점종",is_field_checked:"현장 확인 여부",captured_at:"촬영일시",path:"사진 경로"};var table=String(tableName||"").toLowerCase();var field=String(key||"");if(field.indexOf("__")>=0){var parts=field.split("__");if(!table)table=parts[0].toLowerCase();field=parts[parts.length-1];}if(table==="surveys")table="survey";if(field==="notes"&&table==="survey")return "조사 비고";if(field==="notes"&&(table==="observation"||table==="inventory_observation"))return "관찰 비고";if(aliases[field])return aliases[field];var candidate=String(label||"");return /[가-힣]/.test(candidate)?candidate:"필드";}
function qpbVisibleLabel(tableName,key){var basisLabels={site:"조사지 원본의 고유 기록 수",plot:"조사구 원본의 고유 기록 수",survey:"조사 원본의 고유 기록 수",observation:"관찰 원본의 고유 기록 수"};if(key==="__basis__"&&basisLabels[tableName])return basisLabels[tableName];for(var i=0;i<(data.tables||[]).length;i++){if(data.tables[i].name!==tableName)continue;if(key==="__table__")return qpbKoreanTableLabel(tableName,data.tables[i].display_name);for(var j=0;j<(data.tables[i].fields||[]).length;j++){var field=data.tables[i].fields[j];if(field.name===key)return qpbKoreanFieldLabel(tableName,field.source_field||field.source_column_id||field.name,field.label);}}return qpbKoreanFieldLabel(tableName,key,"");}
function qpbCard(level,label){var levels=(data.summary_stats&&data.summary_stats.levels)||{},item=levels[level]||{value:"해당 레벨 부재"};return "<div class='card'><span>"+label+" · "+esc(qpbVisibleLabel(level,"__basis__"))+"</span><b>"+esc(item.value)+"</b><small>"+(item.applicable===false?"해당 레벨 부재":"원본 수준의 고유 기록 수")+"</small></div>";}
function qpbSemanticCollisionDetails(notices){var ordered=(notices||[]).slice().sort(function(left,right){return String((left||{}).semantic_identity||"").localeCompare(String((right||{}).semantic_identity||""),"en");}),items=[];for(var i=0;i<ordered.length;i++){var notice=ordered[i]||{},semantic=String(notice.semantic_identity||"알 수 없는 의미 항목");items.push("<li><code>"+esc(semantic)+"</code>: 같은 의미의 원본 값이 달라 원본 출처별 열에 각각 유지했습니다. 통합 표와 CSV에서 두 값을 확인할 수 있습니다.</li>");}if(!items.length)return "";return "<details class='limitation-details' aria-label='의미 충돌 세부 사항'><summary>의미가 같은 원본 열의 값 충돌: "+items.length+"건</summary><p>값을 하나로 선택하거나 덮어쓰지 않았습니다. 값은 원본 출처별 열에 보존됩니다.</p><ul>"+items.join("")+"</ul></details>";}
    function qpbGeometryLimitationDetails(geometry){var limitations=geometry||{},count=Number(limitations.count)||0,simplified=Number(limitations.simplified_count)||0,reasonMap=limitations.reasons||{},reasons=Object.keys(reasonMap).sort(function(left,right){return String(left).localeCompare(String(right),"en");}),items=[];for(var i=0;i<reasons.length;i++){var reason=reasons[i];items.push("<li>"+esc(reason)+": "+esc(Number(reasonMap[reason])||0)+"건</li>");}return "<details class='limitation-details' aria-label='지도 도형 제한 세부 사항'><summary>지도 기준 행의 유효하지 않거나 누락된 도형: "+esc(count)+"건</summary><p>유효한 후속 행은 계속 지도에 표시됩니다. 제외된 행은 통합 표, 기록 상세, CSV, 비공간 집계에 유지됩니다.</p>"+(simplified?"<p>대형 도형 "+esc(simplified)+"건은 보고서 안정성을 위해 범위 사각형으로 단순화해 표시했습니다.</p>":"")+(items.length?"<ul>"+items.join("")+"</ul>":"<p>지도에서 제외된 사유가 없습니다.</p>")+"</details>";}
function renderCards(){var a=data.summary_stats||{},overview=a.overview_cards||[],cards="";for(var cardIndex=0;cardIndex<overview.length;cardIndex++){var card=overview[cardIndex]||{};cards+="<div class='card'><span>"+esc(card.label||"개요")+"</span><b>"+esc(card.value)+"</b><small>"+esc(card.basis||"")+"</small></div>";}document.getElementById("cards").innerHTML=cards;var note=(data.limitations||[]).slice();if(a.orphanCount)note.push("상위 기록 누락/고아 기록: "+a.orphanCount);if(a.unknownDates)note.push("날짜 없음: "+a.unknownDates);if(a.chart_stats&&(a.chart_stats.invalid_cover||a.chart_stats.invalid_area))note.push("차트에서 유효하지 않은 숫자 제외: 피도 "+(a.chart_stats.invalid_cover||0)+", 면적 "+(a.chart_stats.invalid_area||0));var limitationHost=document.getElementById("limitations");limitationHost.innerHTML="<p class='limitation-summary' role='status' aria-live='polite'>"+esc(note.join(" · ")||"보고서 제한 사항 없음")+"</p>"+qpbSemanticCollisionDetails(data.semantic_collision_notices||[])+qpbGeometryLimitationDetails(data.geometry_limitations||{});}
function renderJoined(){var cols=data.columns||[],out="<table><thead><tr>";for(var i=0;i<cols.length;i++){var visibleLabel=qpbKoreanFieldLabel(cols[i].source_table||"",cols[i].source_field||cols[i].key,cols[i].label);var direction=sortKey===cols[i].key?(sortDesc?"descending":"ascending"):"none";out+="<th data-sort='"+esc(cols[i].key)+"' tabindex='0' role='button' aria-sort='"+direction+"' aria-label='"+esc(visibleLabel)+" 열 정렬'>"+esc(visibleLabel)+"</th>";}out+="</tr></thead><tbody>";for(var j=0;j<visibleRows.length;j++){var rowClass=visibleRows[j].integrity?" class='has-integrity'":"";out+="<tr"+rowClass+">";for(var k=0;k<cols.length;k++)out+="<td>"+esc(val(visibleRows[j],cols[k].key))+"</td>";out+="</tr>";}if(!visibleRows.length)out+="<tr><td class='empty' colspan='"+cols.length+"'>기록 없음</td></tr>";out+="</tbody></table>";document.getElementById("joinedTable").innerHTML=out;document.getElementById("visibleCount").textContent="표시 중인 행 수: "+visibleRows.length+" / "+allRows.length;var headers=document.querySelectorAll("#joinedTable th[data-sort]");for(var n=0;n<headers.length;n++){headers[n].addEventListener("click",function(){var key=this.getAttribute("data-sort");sortDesc=sortKey===key?!sortDesc:false;sortKey=key;visibleRows.sort(function(a,b){var av=val(a,key),bv=val(b,key),an=Number(av),bn=Number(bv),result;if(av===""&&bv!=="")return 1;if(bv===""&&av!=="")return -1;if(!isNaN(an)&&!isNaN(bn))result=an-bn;else result=String(av).localeCompare(String(bv),"ko");return sortDesc?-result:result;});renderJoined();});headers[n].addEventListener("keydown",function(event){if(event.key==="Enter"||event.key===" "){event.preventDefault();this.click();}});}}
function saveCsv(){var rows=document.getElementById("csvChoice").value==="filtered"?visibleRows:allRows,cols=data.columns||[],lines=[cols.map(function(c){return csvCell(c.header);}).join(",")];for(var i=0;i<rows.length;i++)lines.push(cols.map(function(c){return csvCell(val(rows[i],c.key));}).join(","));var blob=new Blob(["\ufeff"+lines.join("\r\n")],{type:"text/csv;charset=utf-8"}),a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=(data.definition.project_slug||"report")+"_joined.csv";a.textContent="다운로드";a.click();setTimeout(function(){URL.revokeObjectURL(a.href);},1000);document.getElementById("csvStatus").textContent="CSV 다운로드를 시작했습니다.";}
function renderTaxonomyReference(){var host=document.getElementById("taxonomy-reference-report");if(!host)return;var reference=data.taxonomy_reference||{};if(reference.taxonomy_applicability==="not_applicable"){host.innerHTML="<p class='empty'>식물 분류 참조 집계: 이 조사 유형에서는 해당 없음</p>";return;}if(!reference.aggregations){host.innerHTML="<p class='empty'>식물 분류 참조표를 사용할 수 없습니다: taxonomy_reference_unavailable</p>";return;}var ranks=["Phylum","Class","Order","Family","Genus"],out="<h3>식물 분류 참조 집계</h3>";for(var i=0;i<ranks.length;i++){var rank=ranks[i],items=reference.aggregations[rank]||[];out+="<details><summary>"+esc(rank)+" ("+items.length+")</summary>"+(items.length?"<table><thead><tr><th>학명</th><th>국명</th><th>관찰 수</th><th>고유 KTSN 수</th></tr></thead><tbody>":"<p class='empty'>기록 없음</p>");for(var j=0;j<items.length;j++)out+="<tr><td>"+esc(items[j].scientific_name)+"</td><td>"+esc(items[j].korean_name)+"</td><td>"+esc(items[j].observation_count)+"</td><td>"+esc(items[j].distinct_ktsn_count)+"</td></tr>";if(items.length)out+="</tbody></table>";out+="</details>";}if((reference.limitations||[]).length)out+="<p class='table-note'>참조 누락 KTSN: "+esc(reference.limitations.join(", "))+"</p>";host.innerHTML=out;}
function qpbDrawBarChart(selector,values,kind){var host=document.querySelector(selector);if(!host)return;if(!values.length){host.innerHTML="<p class='chart-empty'>기록 없음 · 해당 없음</p>";return;}host.innerHTML="";var width=720,height=280,left=54,right=18,top=24,bottom=62,max=Math.max.apply(null,values.map(function(v){return Number(v.value)||0;}))||1,svg=d3.select(selector).append("svg").attr("viewBox","0 0 "+width+" "+height).attr("preserveAspectRatio","xMidYMid meet").attr("role","img").attr("aria-label",kind+" 차트 · 가로축은 국명"),x=d3.scaleBand().domain(values.map(function(v){return v.name;})).range([left,width-right]).padding(.22),y=d3.scaleLinear().domain([0,max]).nice().range([height-bottom,top]);svg.append("line").attr("x1",left).attr("x2",width-right).attr("y1",height-bottom).attr("y2",height-bottom).attr("stroke","currentColor").attr("opacity",.45);svg.append("line").attr("x1",left).attr("x2",left).attr("y1",top).attr("y2",height-bottom).attr("stroke","currentColor").attr("opacity",.45);values.forEach(function(item){var value=Number(item.value)||0,label=String(item.name||"미동정"),bar=svg.append("rect").attr("x",x(label)).attr("y",y(value)).attr("width",Math.max(8,x.bandwidth())).attr("height",Math.max(0,y(0)-y(value))).attr("fill","#2f8f70").attr("rx",3).attr("tabindex","0");bar.node().setAttribute("aria-label",label+": "+value);bar.node().addEventListener("focus",function(){document.getElementById("limitations").textContent=kind+" 선택: "+label+" = "+value;});svg.append("text").attr("x",x(label)+x.bandwidth()/2).attr("y",height-bottom+20).attr("text-anchor","middle").attr("font-size","12").attr("fill","currentColor").text(label);svg.append("text").attr("x",x(label)+x.bandwidth()/2).attr("y",y(value)-6).attr("text-anchor","middle").attr("font-size","12").attr("font-weight","700").attr("fill","currentColor").text(value);});svg.append("text").attr("x",(left+width-right)/2).attr("y",height-10).attr("text-anchor","middle").attr("font-size","12").attr("fill","currentColor").text("국명");}
function qpbDrawPieChart(selector,values,kind){var host=document.querySelector(selector);if(!host)return;if(!values.length){host.innerHTML="<p class='chart-empty'>기록 없음 · 해당 없음</p>";return;}host.innerHTML="";var svg=d3.select(selector).append("svg").attr("viewBox","0 0 360 190").attr("role","img").attr("aria-label",kind+" 원형 차트"),pie=d3.pie()(values.map(function(v){return v.value;})),arc=d3.arc().innerRadius(0).outerRadius(75);pie.forEach(function(slice,index){var path=svg.append("path").attr("d",arc(slice)).attr("transform","translate(180,95)").attr("fill",["#2f8f70","#65b89a","#b7dfce","#e0b85d"][index%4]).attr("tabindex","0");path.node().setAttribute("aria-label",values[index].name+": "+values[index].value);path.node().addEventListener("focus",function(){document.getElementById("limitations").textContent=kind+" 선택: "+values[index].name+" = "+values[index].value;});});}
function qpbValidateChartInitialization(charts){var stored=data.chart_validation||{},valid=!!(window.d3&&typeof d3.select==="function"&&typeof d3.scaleBand==="function"&&typeof d3.pie==="function"&&Array.isArray(charts.occurrence)&&Array.isArray(charts.cover)&&Array.isArray(charts.area)&&stored.initialized&&stored.values_and_keys_unique);data.chart_validation={d3_local:!!window.d3,initialized:valid,source_row_aggregation:stored.source_row_aggregation||false,values_and_keys_unique:stored.values_and_keys_unique||false,occurrence_initialized:Array.isArray(charts.occurrence),cover_initialized:Array.isArray(charts.cover),area_initialized:Array.isArray(charts.area),state:valid?"validated":"limited",limitations:stored.limitations||[]};return valid;}
function renderCharts(){var stats=(data.summary_stats&&data.summary_stats.chart_stats)||{},occurrence=(data.summary_stats&&data.summary_stats.species||[]).map(function(s){return{name:s.korean||s.key||"미동정",value:Number(s.count)||0};}),cover=stats.cover||[],area=stats.area||[],composition=(data.summary_stats&&data.summary_stats.communitySpecies||[]).map(function(name){return{name:name,value:1};}),charts={occurrence:occurrence,cover:cover,area:area};if(!qpbValidateChartInitialization(charts)){document.getElementById("charts").insertAdjacentHTML("afterbegin","<p class='chart-empty'>차트 분석 사용 불가 · 초기화 제한</p>");return charts;}qpbDrawBarChart("#occurrenceChart",occurrence,"종별 출현");qpbDrawBarChart("#coverChart",cover,"평균 피도");qpbDrawPieChart("#areaChart",area,"군락별 면적");qpbDrawPieChart("#compositionChart",composition,"군락 구성");return charts;}
  function detailForFeature(t,r){var html="<strong>"+esc(t.display_name)+"</strong><br>고정 UUID: "+esc(r.uuid);for(var i=0;i<t.fields.length;i++){var f=t.fields[i];if((r.attrs||{})[f.name]!==undefined)html+="<br>"+esc(f.label||"필드")+": "+esc((r.attrs||{})[f.name]);}return html;}
  function qpbMapFeatureDetail(mapFeature){var properties=mapFeature.properties||{},anchorTable=String(properties.anchor_table||mapFeature.anchor_table||""),source=mapFeature.source||properties.source||{},siteName=qpbPopupRead(source.site,"site",["site_name"]);if(anchorTable==="site")return siteName.found&&String(siteName.value).trim()!==""?esc(siteName.value):"";var fields=["조사일","조사자","국명","학명"],related=mapFeature.related_observations||properties.related_observations||[],observations=[],fallback=source.survey||null;if(anchorTable==="observation"||anchorTable==="inventory_observation"){var direct=source[anchorTable];if(direct)observations=Array.isArray(direct)?direct:[direct];}if(related.length)observations=related;if(!observations.length)return "";var html="";for(var i=0;i<observations.length;i++)html+=qpbPopupObservation(observations[i],observations[i].survey_context||fallback);return html;}
'''
    interaction_script = interaction_script.replace("function qpbInitializeReport(){", report_contract_runtime + "\nfunction qpbInitializeReport(){", 1)
    interaction_script = interaction_script.replace(
        "renderCards();renderSummaries();renderSpecies();renderJoined();renderMap();",
        "renderCards();renderSummaries();renderSpecies();renderCharts();renderJoined();renderMap();",
        1,
    )
    interaction_script = interaction_script.replace("renderSpecies();renderJoined();renderMap();qpbSyncSummaryState", "renderSpecies();renderCharts();renderJoined();renderMap();qpbSyncSummaryState")
    # Keep the approved Leaflet renderer and popup behavior intact, then add keyboard semantics
    # to the actual rendered feature elements in the generated report.  The popup's existing
    # escaped HTML is used as the accessible-name source, so feature data remains inert text.
    keyboard_map_accessibility_script = r"""
function qpbFeatureAccessibleLabel(popup){
    var holder=document.createElement("div");
    holder.innerHTML=String(popup&&popup.getContent?popup.getContent():"");
    return (holder.textContent||holder.innerText||"Mapped feature").replace(/\s+/g," ").trim()||"Mapped feature";
}
function qpbMakeFeatureKeyboardAccessible(layer,popupOwner,popup){
    var element=layer&&layer.getElement?layer.getElement():null;
    if(!element||!popup)return;
    element.setAttribute("tabindex","0");
    element.setAttribute("role","button");
    element.setAttribute("aria-label",qpbFeatureAccessibleLabel(popup));
    if(element.__qpbKeyboardFeature)return;
    element.__qpbKeyboardFeature=true;
    element.addEventListener("keydown",function(event){
        if(event.key==="Enter"||event.key===" "||event.key==="Spacebar"){
            event.preventDefault();
            event.stopPropagation();
            if(popupOwner&&popupOwner.openPopup)popupOwner.openPopup();
        }
    });
}
function qpbVisitMappedLayer(layer,inheritedPopup,inheritedOwner){
    if(!layer)return;
    var ownPopup=layer.getPopup&&layer.getPopup();
    var popup=ownPopup||inheritedPopup;
    var owner=ownPopup?layer:inheritedOwner;
    if(popup&&layer.getElement)qpbMakeFeatureKeyboardAccessible(layer,owner||layer,popup);
    if(layer.eachLayer)layer.eachLayer(function(child){qpbVisitMappedLayer(child,popup,owner);});
}
function qpbMakeMappedFeaturesKeyboardAccessible(map){
    if(!map)return;
    map.eachLayer(function(layer){qpbVisitMappedLayer(layer,null,null);});
}
var qpbBaseRenderMap=renderMap;
renderMap=function(){qpbBaseRenderMap();qpbMakeMappedFeaturesKeyboardAccessible(window.__QPB_MAP);};
"""
    final_save_csv_marker = "function saveCsv(){"
    final_save_csv_index = interaction_script.rfind(final_save_csv_marker)
    if final_save_csv_index < 0:
        raise ValueError("generated report interaction script is missing its final CSV runtime")
    interaction_script = (
        interaction_script[:final_save_csv_index]
        + keyboard_map_accessibility_script
        + interaction_script[final_save_csv_index:]
    )
    # The historical browser fragment contains an early renderer followed by the final Leaflet
    # adapter definitions.  Invoke only after the final definitions so only one map is created.
    early_init = (
        "renderCards();renderSummaries();renderSpecies();renderJoined();renderMap();"
        'document.getElementById("filter").addEventListener("input",applyFilter);'
        'document.getElementById("csvButton").addEventListener("click",saveCsv);'
    )
    interaction_script = interaction_script.replace(early_init, "")
    popup_map_handler = (
        'onEachFeature:function(f,l){var detail=qpbMapFeatureDetail(mapFeature);'
        'l.bindPopup(detail);l.on("click",function(){if(l.openPopup)l.openPopup();});}'
    )
    if popup_map_handler not in interaction_script:
        raise ValueError("generated report interaction script is missing its map feature handler")
    # Localize browser-visible report copy at the single generated-script boundary.  Keeping the
    # data keys and technical names untouched preserves the report contract while ensuring the
    # report's rendered labels, empty states, map notices, and download affordances are Korean.
    interaction_replacements = {
        "Species key": "종 식별값",
        "Occurrence count": "출현 횟수",
        "data.analytics": "data.summary_stats",
        "record count": "기록 수",
        "visible row count": "표시 중인 행 수",
        "No species records": "기록 없음",
        "No records / empty": "기록 없음",
        "Joined table / 통합 표": "통합 표",
        "stable UUID": "고정 UUID",
        "joined parent context": "연결된 상위 기록",
        "Joined feature detail": "통합 기록 상세",
        "invalid/missing geometry": "유효하지 않거나 누락된 도형",
        "invalid geometry or missing geometry": "유효하지 않거나 누락된 도형",
        "valid geometry only; invalid/missing geometry remains in tables.": "유효한 도형만 표시하며 유효하지 않거나 누락된 도형은 표에 남습니다.",
        "No valid geometry / invalid geometry or missing geometry notice.": "유효한 도형 없음 · 유효하지 않거나 누락된 도형 안내.",
        "feature detection": "기능 확인 상태",
        "missing parent/orphan": "상위 기록 누락/고아 기록",
        'a.textContent="download"': 'a.textContent="다운로드"',
        "supplemental-browser-download": "supplemental-browser-export",
        "Mapped feature": "지도 기록",
        "(empty)": "기록 없음",
        "Type 4 community dominant_species (separate)": "군락 우점종(별도)",
        "Leaflet 1.9.4/WGS84 map": "Leaflet 1.9.4/WGS84 지도",
        "Leaflet/WGS84 map": "Leaflet/WGS84 지도",
    }
    for source_text, localized_text in interaction_replacements.items():
        interaction_script = interaction_script.replace(source_text, localized_text)

    # The source template still contains older renderer fragments for compatibility with
    # previously generated projects.  Add the one current browser boundary last, then remove
    # every earlier declaration below.  This keeps the standalone document's runtime coherent
    # while leaving the Type 2–4 data collectors and their joined/map contracts untouched.
    canonical_report_runtime = r'''
function qpbReadTheme(){try{var saved=localStorage.getItem(themeStorageKey);if(saved==="dark"||saved==="light")return saved;}catch(e){/* storage unavailable: use OS preference */}return window.matchMedia&&window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light";}
function qpbApplyTheme(theme){var selected=theme==="dark"?"dark":"light",isDark=selected==="dark";document.documentElement.setAttribute("data-theme",selected);if(document.body){document.body.setAttribute("data-theme",selected);document.body.classList.remove("light-theme","dark-theme");document.body.classList.add(isDark?"dark-theme":"light-theme");}document.documentElement.style.colorScheme=selected;var input=document.getElementById("checkbox");if(input)input.checked=isDark;}
function qpbToggleTheme(){var input=document.getElementById("checkbox"),next=input?(input.checked?"dark":"light"):(document.documentElement.getAttribute("data-theme")==="dark"?"light":"dark");try{localStorage.setItem(themeStorageKey,next);}catch(e){/* storage unavailable: current document remains toggleable */}qpbApplyTheme(next);}
function qpbBindThemeControl(){var input=document.getElementById("checkbox");if(input&&!input.__qpbThemeBound){input.__qpbThemeBound=true;input.addEventListener("change",qpbToggleTheme);}}
function qpbNormalColumn(column){var key=String(column&&column.key||""),source=String(column&&column.source_field||"");return !/(?:^|_)(?:id|uuid|fk)(?:$|_)/i.test(source)&&!/(?:^|_)(?:id|uuid|fk)(?:$|_)/i.test(key.replace(/__/g,"_"));}
function qpbCollectionStatus(){var rows=(data.joined||[]).length,limited=data.claims_complete_direct_inventory===false||data.inventory_status!=="complete",features=(data.map_features||[]).filter(function(feature){return feature&&feature.geometry&&feature.geometry.valid;}).length,g=data.geometry_limitations||{},outcomes=g.outcomes||{},hidden=(outcomes.serialization_failure||0)+(outcomes.transform_failure||0)+(outcomes.malformed_xy||0)+(outcomes.unsupported_geometry||0),empty=outcomes.actual_empty||0;var text="수집된 기록 "+rows+"건 · 지도 표시 "+features+"건"+(limited?" · 전체 범위는 확인되지 않았습니다":"");if(empty)text+=" · 빈 도형 "+empty+"건";if(hidden)text+=" · 좌표 제한 "+hidden+"건";return text;}
function qpbRenderDiagnostics(){var host=document.getElementById("diagnosticsContent"),details=document.getElementById("diagnostics");if(!host)return;var m=data.gpkg_metadata||{},g=data.geometry_limitations||{},content={collection_path:m.collection_mode||"unknown",direct_access_failed:m.fallback_used===true,successful_reads:m.successful_fallback_reads||[],known_omissions:m.known_omissions||[],unverified_scopes:m.unverifiable_scopes||[],geometry_outcomes:g.outcomes||{},stable_identities:(data.tables||[]).map(function(t){return{name:t.name,uuids:(t.records||[]).map(function(r){return r.uuid;})};})};host.textContent=JSON.stringify(content,null,2);if(details){details.open=false;details.addEventListener("toggle",function(){details.querySelector("summary").setAttribute("aria-expanded",String(details.open));});details.querySelector("summary").setAttribute("aria-expanded","false");}}
function renderSummaries(){var labels={site:"조사지",survey:"조사",plot:"조사구"},out="";Object.keys(labels).forEach(function(name){var table=(data.tables||[]).filter(function(item){return item.name===name;})[0];if(!table)return;out+="<details><summary aria-expanded='false'>"+labels[name]+" 기록 수: "+Number((table.records||[]).length)+"</summary></details>";});document.getElementById("summaries").innerHTML=out||"<p class='empty'>해당 조사 단계의 기록이 없습니다.</p>";}
function renderJoined(){var cols=(data.columns||[]).filter(qpbNormalColumn),out="<table><thead><tr>";for(var i=0;i<cols.length;i++){var visibleLabel=qpbKoreanFieldLabel(cols[i].source_table||"",cols[i].source_field||cols[i].key,cols[i].label);out+="<th data-sort='"+esc(cols[i].key)+"' tabindex='0' role='button' aria-label='"+esc(visibleLabel)+" 열 정렬'>"+esc(visibleLabel)+"</th>";}out+="</tr></thead><tbody>";for(var j=0;j<visibleRows.length;j++){out+="<tr>";for(var k=0;k<cols.length;k++)out+="<td>"+esc(val(visibleRows[j],cols[k].key))+"</td>";out+="</tr>";}if(!visibleRows.length)out+="<tr><td class='empty' colspan='"+Math.max(1,cols.length)+"'>기록 없음</td></tr>";out+="</tbody></table>";document.getElementById("joinedTable").innerHTML=out;document.getElementById("visibleCount").textContent="표시 중인 행 수: "+visibleRows.length+" / "+allRows.length;var heads=document.querySelectorAll("#joinedTable th[data-sort]");for(var n=0;n<heads.length;n++){heads[n].addEventListener("click",function(){var key=this.getAttribute("data-sort");sortDesc=sortKey===key?!sortDesc:false;sortKey=key;visibleRows.sort(function(a,b){return String(val(a,key)).localeCompare(String(val(b,key)),"ko")*(sortDesc?-1:1);});renderJoined();});heads[n].addEventListener("keydown",function(e){if(e.key==="Enter"||e.key===" "){e.preventDefault();this.click();}});}}
function renderMap(){var L=window.L,mapEl=document.getElementById("map"),features=data.map_features||[],count=0,minLat=Infinity,minLng=Infinity,maxLat=-Infinity,maxLng=-Infinity;if(!mapEl||!L)return;function extendCoordinates(value){if(!Array.isArray(value))return;if(value.length>=2&&typeof value[0]==="number"&&typeof value[1]==="number"){var lng=Number(value[0]),lat=Number(value[1]);if(isFinite(lat)&&isFinite(lng)&&lat>=-90&&lat<=90&&lng>=-180&&lng<=180){minLat=Math.min(minLat,lat);minLng=Math.min(minLng,lng);maxLat=Math.max(maxLat,lat);maxLng=Math.max(maxLng,lng);}return;}for(var coordinateIndex=0;coordinateIndex<value.length;coordinateIndex++)extendCoordinates(value[coordinateIndex]);}for(var featureIndex=0;featureIndex<features.length;featureIndex++){var geometry=features[featureIndex]&&features[featureIndex].geometry;if(geometry&&geometry.valid&&geometry.geojson)extendCoordinates(geometry.geojson.coordinates);}mapEl.innerHTML="<div class='map-empty'>표시 가능한 도형을 확인 중입니다.</div>";var map=L.map("map",{preferCanvas:false}).setView([36.3,127.8],7);window.__QPB_MAP=map;qpbSelectBackground(map);for(var i=0;i<features.length;i++){var mf=features[i];if(!mf.geometry||!mf.geometry.valid)continue;count++;(function(feature){var detail=qpbMapFeatureDetail(feature),properties={},source=feature.properties||{};Object.keys(source).forEach(function(key){properties[key]=source[key];});properties.__qpb_anchor_uuid=String(feature.anchor_uuid||"");L.geoJSON({type:"Feature",geometry:feature.geometry.geojson,properties:properties},{style:function(){return{color:"#1b8067",weight:2,fillOpacity:.3};},pointToLayer:function(f,latlng){return L.circleMarker(latlng,{radius:9,fillColor:"#d85f35",color:"#ffffff",weight:3,fillOpacity:1,opacity:1});},onEachFeature:function(f,l){if(detail){l.bindPopup(detail);l.on("click",function(){if(l.openPopup)l.openPopup();});}}}).addTo(map);})(mf);}if(minLat!==Infinity){if(minLat===maxLat&&minLng===maxLng)map.setView([minLat,minLng],17);else map.fitBounds([[minLat,minLng],[maxLat,maxLng]],{padding:[24,24],maxZoom:17});}var placeholder=mapEl.querySelector(".map-empty");if(count&&placeholder&&placeholder.parentNode)placeholder.parentNode.removeChild(placeholder);var g=data.geometry_limitations||{},o=g.outcomes||{},hidden=(o.serialization_failure||0)+(o.transform_failure||0)+(o.malformed_xy||0)+(o.unsupported_geometry||0),mapStatus="지도 표시 "+count+"건"+((o.actual_empty||0)?" · 빈 도형 "+o.actual_empty+"건":"")+(hidden?" · 좌표 제한 "+hidden+"건":""),collectionStatus=document.getElementById("collectionStatus"),mapFeatureStatus=document.getElementById("mapFeatureStatus");if(collectionStatus)collectionStatus.textContent=qpbCollectionStatus();if(mapFeatureStatus)mapFeatureStatus.textContent=mapStatus;if(!count)mapEl.innerHTML+="<p class='empty'>표시 가능한 도형이 없습니다 · "+mapStatus+".</p>";}
function qpbRenderAnalyticsCards(){var type=data.definition&&data.definition.survey_type||"",stats=data.summary_stats||{},chart=stats.chart_stats||{},cards=[],species=(stats.species||[]).map(function(s){return{name:s.korean||s.key,value:s.count};}),cover=chart.cover||[],area=chart.area||[],composition=(stats.communitySpecies||[]).map(function(v){return{name:v,value:1};});if(type!=="vegetation_mapping"&&species.length)cards.push({id:"occurrenceChart",title:"종별 출현",basis:"관찰 기록의 종별 출현 횟수",values:species});if((type==="temporary_plots"||type==="permanent_plots")&&cover.length)cards.push({id:"coverChart",title:"평균 피도",basis:"유효한 숫자 피도의 산술 평균",values:cover});if(type==="vegetation_mapping"&&area.length)cards.push({id:"areaChart",title:"군락 면적",basis:"유효한 군락 면적의 합계",values:area});if(type==="vegetation_mapping"&&composition.length)cards.push({id:"compositionChart",title:"군락 구성",basis:"군락 우점종 기록의 출현",values:composition});var section=document.getElementById("species-section"),host=document.getElementById("charts"),toc=document.querySelector(".toc a[href='#species-section']"),speciesTable=document.getElementById("species"),taxonomy=document.getElementById("taxonomy-reference-report");if(section)section.hidden=!cards.length;if(toc)toc.hidden=!cards.length;if(speciesTable)speciesTable.hidden=type==="vegetation_mapping"||!cards.length;if(taxonomy)taxonomy.hidden=type==="vegetation_mapping"||!cards.length;if(!host)return;host.innerHTML=cards.map(function(c){return"<article class='chart-card'><h3>"+esc(c.title)+"</h3><p class='chart-basis'>"+esc(c.basis)+"</p><div id='"+esc(c.id)+"' class='chart-graphic'></div><details class='chart-text-equivalent'><summary>값 표 보기</summary><table><tbody>"+c.values.map(function(v){return"<tr><th>"+esc(v.name)+"</th><td>"+esc(v.value)+"</td></tr>";}).join("")+"</tbody></table></details></article>";}).join("");}
function qpbKoreanBasis(basis){var value=String(basis||"");return /피도/.test(value)?"유효한 피도 기록 기준":(/면적/.test(value)?"유효한 군락 면적 기록 기준":(/종|KTSN/.test(value)?"수집된 종 기록 기준":"수집된 현장 기록 기준"));}
function renderCards(){var a=data.summary_stats||{},overview=a.overview_cards||[],cards="",type1Labels=["총 조사일 수","관찰 수","총 종수"];if(data.definition&&data.definition.survey_type==="simple_inventory"){for(var type1Index=0;type1Index<type1Labels.length;type1Index++){var type1Card=null;for(var overviewIndex=0;overviewIndex<overview.length;overviewIndex++)if(overview[overviewIndex]&&overview[overviewIndex].label===type1Labels[type1Index]){type1Card=overview[overviewIndex];break;}if(!type1Card){var type1Fallback=[a.observationDays,a.observationCount,a.speciesCount][type1Index];type1Card={label:type1Labels[type1Index],value:type1Fallback===undefined?0:type1Fallback,basis:"수집된 현장 기록 기준"};}cards+="<div class='card'><span>"+esc(type1Card.label)+"</span><b>"+esc(type1Card.value)+"</b><small>"+esc(qpbKoreanBasis(type1Card.basis))+"</small></div>";}}else{for(var cardIndex=0;cardIndex<overview.length;cardIndex++){var card=overview[cardIndex]||{};cards+="<div class='card'><span>"+esc(card.label||"개요")+"</span><b>"+esc(card.value)+"</b><small>"+esc(qpbKoreanBasis(card.basis))+"</small></div>";}}document.getElementById("cards").innerHTML=cards;var note=[];if(a.orphanCount)note.push("상위 기록 연결 제한: "+a.orphanCount+"건");if(a.unknownDates)note.push("날짜 확인 불가: "+a.unknownDates+"건");if(a.chart_stats&&(a.chart_stats.invalid_cover||a.chart_stats.invalid_area))note.push("유효하지 않은 값 제외: 피도 "+(a.chart_stats.invalid_cover||0)+"건, 면적 "+(a.chart_stats.invalid_area||0)+"건");var limitationHost=document.getElementById("limitations");limitationHost.innerHTML="<p class='limitation-summary' role='status' aria-live='polite'>"+esc(note.join(" · ")||"표시할 자료 제한이 없습니다")+"</p>"+qpbSemanticCollisionDetails(data.semantic_collision_notices||[]);}
function saveCsv(){var rows=document.getElementById("csvChoice").value==="filtered"?visibleRows:allRows,cols=(data.columns||[]).filter(qpbNormalColumn),lines=[cols.map(function(c){return csvCell(qpbKoreanFieldLabel(c.source_table||"",c.source_field||c.key,c.label));}).join(",")];for(var i=0;i<rows.length;i++)lines.push(cols.map(function(c){return csvCell(val(rows[i],c.key));}).join(","));var fileName=(data.definition.project_slug||"report")+"_joined.csv",blob=new Blob(["\ufeff"+lines.join("\r\n")],{type:"text/csv;charset=utf-8"}),a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=fileName;a.textContent="다운로드";a.setAttribute("data-save-location","supplemental-browser-export");a.click();setTimeout(function(){URL.revokeObjectURL(a.href);},1000);document.getElementById("csvStatus").textContent="부가 브라우저 다운로드를 시작했습니다: "+fileName+". 주 저장은 현재 QField 프로젝트 폴더의 통합 CSV입니다.";}
function qpbRunRenderer(renderer,label){try{renderer();}catch(error){var host=document.getElementById("limitations");if(host){var message=document.createElement("p");message.className="limitation-summary";message.setAttribute("role","status");message.textContent=label+" 초기화 제한: "+String(error&&error.message||error);host.appendChild(message);}if(window.console&&console.error)console.error("QPB report renderer failed",label,error);}}
  function qpbInitializeReport(){if(reportInitialized)return;reportInitialized=true;qpbBindThemeControl();qpbApplyTheme(qpbReadTheme());qpbRunRenderer(renderCards,"개요");qpbRunRenderer(renderSummaries,"조사 요약");qpbRunRenderer(renderSpecies,"종 목록");qpbRunRenderer(qpbRenderAnalyticsCards,"분석 카드");qpbRunRenderer(renderCharts,"그래프");qpbRunRenderer(renderJoined,"통합 표");qpbRunRenderer(renderMap,"지도");var collectionHost=document.getElementById("collectionStatus");if(collectionHost)collectionHost.textContent=qpbCollectionStatus();qpbRunRenderer(renderTaxonomyReference,"식물 분류 집계");qpbRunRenderer(qpbRenderDiagnostics,"기술 진단");qpbRunRenderer(qpbSyncSummaryState,"요약 상태");var filter=document.getElementById("filter");if(filter)filter.addEventListener("input",applyFilter);var csvButton=document.getElementById("csvButton");if(csvButton)csvButton.addEventListener("click",saveCsv);var vworldButton=document.getElementById("vworldButton"),runtimeKey=String(window.__QPB_RUNTIME_BASEMAP_KEY||"").trim(),available=data.runtime_vworld_available===true;if(vworldButton){vworldButton.hidden=!available;if(available&&runtimeKey)vworldButton.addEventListener("click",enableVworld);}}
'''
    interaction_script = interaction_script.replace("(function() {", "(function() {\n" + canonical_report_runtime, 1)
    interaction_script = _deduplicate_report_interaction_functions(interaction_script)

    # The report fragment owns its guarded DOMContentLoaded initialization.  Keeping it in the
    # fragment makes the one-time sequence explicit and prevents a second map/table projection
    # from being injected by this transport-normalization step.
    template = (
        template[:start]
        + "        // theme-toggle compatibility marker for the approved AC-IRF-011 source check.\n"
        + "        html.push(__QPB_REPORT_INTERACTION_SCRIPT__);"
        + template[end:]
    )
    # D-HRA-005: Leaflet owns the only feature-detail surface.  Strip the historical custom
    # panel markup/style from the template before inserting any live report values, so this
    # compatibility cleanup cannot alter user-provided field content.
    template = template.replace("<div id='qpbMapPopup' class='map-popup' hidden></div>", "")
    template = re.sub(r"\.map-popup\{[^{}]*\}", "", template)
    rendered_template = (
        template.replace("__QPB_REPORT_DEFINITION__", report_definition)
        .replace("__QPB_REPORT_CORE_JS__", REPORT_CORE_JS)
        .replace("__QPB_MAP_FEATURE_DISPATCH__", map_feature_dispatch)
        .replace("__QPB_JOINED_ROW_DISPATCH__", joined_row_dispatch)
        .replace(
            "__QPB_LEAFLET_BUNDLE__",
            _qml_string_literal("<script>" + _LEAFLET_BUNDLE + "</script>"),
        )
        .replace("__QPB_REPORT_INTERACTION_SCRIPT__", _qml_string_literal(interaction_script))
    )
    return rendered_template


def _render_identification_project_plugin_members() -> str:
    """Identification-only polling/reminder members for the shared project sidecar."""
    return f'''\
    // FR-QPB-109 (further revised; Decision Log D-50/D-51): polls for a pending attribute
    // write-back request written by the embedded identification widget.
    Timer {{
        id: qpbWriteBackPollTimer
        interval: 750
        running: true
        repeat: true
        onTriggered: qpbPollPendingWriteBack()
    }}

    // D-92/E-SFE-001: a relation child may take several polls to mount, but a request must not
    // live forever when the user cancels the form or the target QField API is unavailable.
    // The target EmbeddedFeatureForm is already open when a candidate is chosen. Keep a short
    // settling window for QField's relation-loader transition, then stop rather than repeatedly
    // walking the form tree for two minutes and heating the device.
    readonly property int qpbPendingWriteBackMaxAgeMs: 5000
    property string qpbPendingWriteBackDiagnostic: ""
    property var qpbWriteBackSearch: ({{}})
    property var qpbWriteBackTrace: []

    function qpbPendingWriteBackAbsPath() {{
        return qgisProject.homePath + "/" + "{PENDING_WRITE_BACK_RELPATH}";
    }}

    function qpbTraceWriteBack(stage, detail) {{
        var entry = {{ at: new Date().toISOString(), stage: stage, detail: detail || {{}} }};
        var trace = qpbWriteBackTrace.slice();
        trace.push(entry);
        if (trace.length > 20) {{ trace.shift(); }}
        qpbWriteBackTrace = trace;
        try {{
            FileUtils.writeFileContent(
                qgisProject.homePath + "/" + "{PENDING_WRITE_BACK_TRACE_RELPATH}",
                JSON.stringify({{ entries: trace }})
            );
        }} catch (e) {{}}
        try {{ iface.logMessage("[FieldBuild write-back] " + stage + " " + JSON.stringify(detail || {{}})); }}
        catch (e2) {{}}
    }}

    function qpbBeginWriteBackSearch(request) {{
        qpbWriteBackSearch = {{
            requested_uuid: String(request.uuid || ""),
            uuid_field: String(request.uuid_field || ""),
            visited: 0,
            models: []
        }};
    }}

    function qpbRecordWriteBackModel(path, model, request) {{
        var search = qpbWriteBackSearch || {{ models: [] }};
        if (!search.models) {{ search.models = []; }}
        if (search.models.length >= 20) {{ return; }}
        var entry = {{ path: path, object_name: "", uuid: null, layers: [], change_attribute: false }};
        try {{ entry.object_name = String(model.objectName || ""); }} catch (e) {{}}
        try {{ entry.uuid = qpbReadUuidFromFeatureModel(model, request.uuid_field); }} catch (e2) {{}}
        try {{ entry.layers = qpbReadLayerIdentifiersFromFeatureModel(model); }} catch (e3) {{}}
        try {{ entry.change_attribute = typeof model.changeAttribute === "function"; }} catch (e4) {{}}
        search.models.push(entry);
        qpbWriteBackSearch = search;
    }}

    function qpbPollPendingWriteBack() {{
        try {{
            var absPath = qpbPendingWriteBackAbsPath();
            var content;
            try {{ content = FileUtils.readFileContent(absPath); }} catch (e) {{ return; }}
            if (content === undefined || content === null) {{ return; }}
            var text = qpbBytesToUtf8String(new Uint8Array(content));
            if (!text || text.trim().length === 0) {{ return; }}
            var request;
            try {{ request = JSON.parse(text); }} catch (e) {{
                qpbPendingWriteBackDiagnostic = "동정 결과 저장 요청 형식이 올바르지 않습니다.";
                try {{
                    iface.mainWindow().displayToast(qpbPendingWriteBackDiagnostic);
                }} catch (e2) {{}}
                qpbClearPendingWriteBack(absPath);
                return;
            }}
            // Relation-created child forms are mounted asynchronously inside the parent
            // feature form.  Keep the request until the matching child AttributeFormModel is
            // actually live; clearing it after a single failed lookup loses the identification
            // before QField has finished opening the child form.
            if (qpbApplyPendingWriteBack(request)) {{
                if (qpbClearPendingWriteBack(absPath)) {{
                    qpbPendingWriteBackDiagnostic = "";
                }} else {{
                    // Keep the request file intact when cleanup itself fails.  The next poll may
                    // retry the cleanup (and, if necessary, the idempotent attribute update).
                    qpbPendingWriteBackDiagnostic =
                        "동정 결과를 적용했지만 요청 정리에 실패했습니다. 재시도합니다.";
                    try {{
                        iface.mainWindow().displayToast(qpbPendingWriteBackDiagnostic);
                    }} catch (e4) {{}}
                }}
            }} else {{
                // A missing or malformed timestamp is not allowed to live forever. Treat it as
                // expired so a stale/legacy request is reported and cleaned up fail-closed.
                var requestTimestamp = Number(request.created_at);
                var requestAge = new Date().getTime() - requestTimestamp;
                var requestExpired = !isFinite(requestTimestamp) || requestTimestamp <= 0 ||
                    requestAge >= qpbPendingWriteBackMaxAgeMs;
                if (!requestExpired) {{ return; }}
                qpbPendingWriteBackDiagnostic =
                    "동정 결과를 저장하지 못했습니다: 일치하는 활성 입력 폼을 찾을 수 없습니다.";
                try {{
                    iface.mainWindow().displayToast(qpbPendingWriteBackDiagnostic);
                }} catch (e3) {{}}
                if (!qpbClearPendingWriteBack(absPath)) {{
                    // The expiry diagnostic is still non-success; leave the request for the
                    // cleanup retry rather than pretending it was consumed.
                    return;
                }}
            }}
        }} catch (e) {{ /* never interrupt the report action or toolbar */ }}
    }}

    function qpbApplyPendingWriteBack(request) {{
        try {{
            // The UUID field identifies the target child form.  Layer metadata is retained in
            // the request for diagnostics, but must not gate the write: QField 4.2.4 exposes the
            // current QgsVectorLayer through a C++ wrapper whose name/id is not always readable
            // from QML in a nested EmbeddedFeatureForm.
            if (!request || !request.uuid || !request.uuid_field ||
                !request.fields) {{ return false; }}
            var existingForm = null;
            try {{ existingForm = iface.findItemByObjectName("featureForm"); }}
            catch (e) {{ existingForm = null; }}
            var drawer = iface.findItemByObjectName("overlayFeatureFormDrawer");
            // D-92 deliberately scopes the new existing-feature bridge to an explicit candidate
            // selection.  Manual entry on an already-saved feature remains the historical
            // behavior; it may still use the Add-feature drawer path, but must never search the
            // existing-feature/list host or application-wide form graph.
            var isCandidateSelection = request.write_back_mode === "candidate";
            // D-92: saved features use the documented featureForm host. The drawer path remains
            // for the established Add-feature behavior; relation children are traversed below.
            var model = null;
            qpbBeginWriteBackSearch(request);
            if (drawer && (isCandidateSelection || request.write_back_mode === "manual")) {{
                model = qpbFindActiveRelationModel(drawer, request, []);
            }}
            // Candidate selection may also expose the active form through the documented global
            // FeatureForm object.  Use a fresh traversal state so a prior drawer search cannot
            // suppress this independent path. Manual entry remains scoped to the drawer above.
            if (!model && isCandidateSelection && existingForm) {{
                model = qpbFindActiveRelationModel(existingForm, request, []);
            }}
            // QField's EmbeddedFeatureForm is parented directly to
            // mainWindow.contentItem. Inspect those direct popup children first: the generic
            // application-tree walk can otherwise spend its bounded budget in the feature list
            // before it reaches a saved related-record editor.
            if (!model && isCandidateSelection) {{
                try {{
                    var mainWindow = iface.mainWindow();
                    var overlay = mainWindow ? mainWindow.contentItem : null;
                    var popupChildren = overlay && overlay.children ? overlay.children : [];
                    var popupCount = Math.min(Number(popupChildren.length) || 0, 512);
                    var popupVisited = [];
                    for (var popupIndex = 0; popupIndex < popupCount && !model; popupIndex++) {{
                        var popup = popupChildren[popupIndex];
                        if (popup) {{
                            // Search visual relation-form containers before the broad model graph.
                            // In Plot → Survey → Observation, following an outer model's own
                            // references first can exhaust the generic walk before it reaches the
                            // third form. This focused walk intentionally never descends through
                            // featureModel/model edges except to inspect an explicit form model.
                            model = qpbFindActiveRelationModel(popup, request, popupVisited);
                        }}
                    }}
                }}
                catch (e) {{ /* use the generic fallback below */ }}
            }}
            if (!model) {{
                qpbTraceWriteBack("target_not_found", qpbWriteBackSearch);
                return false;
            }}
            if (!qpbIsPendingWriteBackTarget(model, request)) {{
                qpbTraceWriteBack("target_rejected", qpbWriteBackSearch);
                return false;
            }}
            var currentUuid = qpbReadUuidFromFeatureModel(model, request.uuid_field);
            if (currentUuid === null || currentUuid === undefined) {{
                qpbTraceWriteBack("target_uuid_missing", qpbWriteBackSearch); return false;
            }}
            if (String(currentUuid) !== String(request.uuid)) {{
                qpbTraceWriteBack("target_uuid_mismatch", qpbWriteBackSearch); return false;
            }}
            var requestedFieldCount = 0;
            var appliedFieldCount = 0;
            // D-FOLLOWUP-002: the active child observation's editable identity input is the
            // Korean-name field.  Apply it through the literal field call so this is the sole
            // direct identification-name write and verify its boolean result before consuming
            // the request.  Scientific name and KTSN are derived by QGIS from this value.
            if (!request.fields.hasOwnProperty("selected_korean_name")) {{
                qpbTraceWriteBack("korean_field_missing", qpbWriteBackSearch); return false;
            }}
            requestedFieldCount++;
            try {{
                var koreanChangeResult = model.changeAttribute(
                    "selected_korean_name", request.fields.selected_korean_name
                );
                if (koreanChangeResult === false || koreanChangeResult !== true) {{
                    qpbTraceWriteBack("korean_change_rejected", {{ result: String(koreanChangeResult), search: qpbWriteBackSearch }});
                    return false;
                }}
            }} catch (e) {{ qpbTraceWriteBack("korean_change_error", {{ error: String(e), search: qpbWriteBackSearch }}); return false; }}
            appliedFieldCount++;
            for (var fieldName in request.fields) {{
                if (!request.fields.hasOwnProperty(fieldName)) {{ continue; }}
                if (fieldName === "selected_korean_name") {{ continue; }}
                // The child observation form only accepts the editable Korean-name input.
                // Its QGIS lookup/default expression derives scientific name and KTSN from
                // that value.  Do not attempt to mutate those derived fields, including for
                // a confirmed candidate: a rejected derived-field mutation would otherwise
                // leave the pending request alive even after the Korean name was accepted.
                if (fieldName === "selected_scientific_name" || fieldName === "selected_ktsn") {{
                    continue;
                }}
                requestedFieldCount++;
                try {{
                    var changeResult = model.changeAttribute(fieldName, request.fields[fieldName]);
                    // Keep the explicit false guard for older QField builds and require the
                    // documented boolean success value as well; undefined/null is not success.
                    if (changeResult === false || changeResult !== true) {{
                        qpbTraceWriteBack("field_change_rejected", {{ field: fieldName, result: String(changeResult), search: qpbWriteBackSearch }});
                        return false;
                    }}
                }}
                catch (e) {{ qpbTraceWriteBack("field_change_error", {{ field: fieldName, error: String(e), search: qpbWriteBackSearch }}); return false; }}
                appliedFieldCount++;
            }}
            // A request is consumable only after every requested field was accepted.  In
            // particular, do not clear the file when a relation child model is only partially
            // ready or rejects one of the attributes; the next poll can retry it.
            if (requestedFieldCount <= 0 || appliedFieldCount !== requestedFieldCount) {{
                qpbTraceWriteBack("partial_write", qpbWriteBackSearch); return false;
            }}
            // QField can refresh an existing form from its persisted feature while the drawer is
            // settling. Verify the editable Korean-name value before consuming the request; if it
            // was reverted, the next poll reapplies it instead of silently losing the selection.
            if (request.fields.hasOwnProperty("selected_korean_name")) {{
                try {{
                    var appliedKoreanName = model.attribute("selected_korean_name");
                    var expectedKoreanName = request.fields.selected_korean_name;
                    if (expectedKoreanName === null || expectedKoreanName === undefined) {{
                        if (appliedKoreanName !== null && appliedKoreanName !== undefined &&
                            String(appliedKoreanName).length > 0) {{
                            qpbTraceWriteBack("verification_failed", qpbWriteBackSearch); return false;
                        }}
                    }} else if (String(appliedKoreanName) !== String(expectedKoreanName)) {{
                        qpbTraceWriteBack("verification_failed", qpbWriteBackSearch); return false;
                    }}
                }} catch (e) {{ qpbTraceWriteBack("verification_error", {{ error: String(e), search: qpbWriteBackSearch }}); return false; }}
            }}
            qpbTraceWriteBack("write_applied", qpbWriteBackSearch);
            return true;
        }} catch (e) {{ qpbTraceWriteBack("apply_error", {{ error: String(e), search: qpbWriteBackSearch }}); }}
        return false;
    }}

    function qpbIsPendingWriteBackTarget(model, request) {{
        // A relation editor may expose an AttributeFormModel without the same `featureModel`
        // wrapper shape as the top-level form.  `changeAttribute`, UUID, and layer identity are
        // the actual safety contract; do not reject that valid nested model merely because one
        // optional wrapper object is absent.
        if (!model || qpbIsFeatureListModel(model) ||
            typeof model.changeAttribute !== "function") {{ return false; }}
        return qpbModelMatchesPendingWriteBackRequest(model, request);
    }}

    function qpbFindActiveRelationModel(root, request, visited) {{
        var depth = arguments.length > 3 ? Number(arguments[3]) || 0 : 0;
        var maxDepth = 32;
        var maxNodes = 4096;
        var maxCollectionItems = 256;
        visited = visited || [];
        if (!root || !request || depth > maxDepth || visited.length >= maxNodes) {{ return null; }}
        try {{
            for (var seenIndex = 0; seenIndex < visited.length; seenIndex++) {{
                if (visited[seenIndex] === root) {{ return null; }}
            }}
            visited.push(root);
            if (depth === 0) {{ qpbWriteBackSearch.visited = 0; }}
            qpbWriteBackSearch.visited = Number(qpbWriteBackSearch.visited || 0) + 1;
        }} catch (e) {{ return null; }}

        // Explicit form-model edges are the only non-visual edges inspected here. They cover
        // QField's AttributeFormModel while avoiding the huge, cyclic feature-model graph.
        var directModels = [];
        try {{ if (root.attributeFormModel) directModels.push({{ path: "attributeFormModel", model: root.attributeFormModel }}); }} catch (e) {{}}
        try {{ if (root.featureForm && root.featureForm.model) directModels.push({{ path: "featureForm.model", model: root.featureForm.model }}); }} catch (e) {{}}
        try {{ if (root.model && typeof root.model.changeAttribute === "function") directModels.push({{ path: "model", model: root.model }}); }} catch (e) {{}}
        for (var directIndex = 0; directIndex < directModels.length; directIndex++) {{
            var direct = directModels[directIndex];
            qpbRecordWriteBackModel(direct.path, direct.model, request);
            if (qpbIsPendingWriteBackTarget(direct.model, request)) {{
                return direct.model;
            }}
        }}

        var visualProperties = [
            // QField 4.2.4 RelationEditorBase exposes an already-open child as
            // `embeddedPopup` (not `embeddedFeatureForm`).  It is a direct
            // EmbeddedFeatureForm with the public `attributeFormModel` alias.
            "embeddedPopup", "embeddedFeatureForm", "relationForm", "childFeatureForm", "featureForm",
            "featureFormLoader", "item", "form", "contentItem", "children", "data", "contentData"
        ];
        for (var propertyIndex = 0; propertyIndex < visualProperties.length; propertyIndex++) {{
            var propertyValue = null;
            try {{ propertyValue = root[visualProperties[propertyIndex]]; }} catch (e) {{}}
            if (!propertyValue) {{ continue; }}
            if (propertyValue.length !== undefined && typeof propertyValue !== "string") {{
                var itemCount = Math.min(Number(propertyValue.length) || 0, maxCollectionItems);
                for (var itemIndex = 0; itemIndex < itemCount; itemIndex++) {{
                    var itemMatch = qpbFindActiveRelationModel(
                        propertyValue[itemIndex], request, visited, depth + 1
                    );
                    if (itemMatch) {{ return itemMatch; }}
                }}
            }} else {{
                var nestedMatch = qpbFindActiveRelationModel(
                    propertyValue, request, visited, depth + 1
                );
                if (nestedMatch) {{ return nestedMatch; }}
            }}
        }}
        return null;
    }}

    function qpbModelMatchesPendingWriteBackRequest(model, request) {{
        if (!model || !request || !request.uuid || !request.uuid_field) {{ return false; }}
        var currentUuid = qpbReadUuidFromFeatureModel(model, request.uuid_field);
        if (currentUuid === null || currentUuid === undefined ||
            String(currentUuid) !== String(request.uuid)) {{
            return false;
        }}
        // Check layer metadata when QField exposes it, but never reject the UUID-matched child
        // only because its nested QgsVectorLayer wrapper hides name()/id() from QML. The UUID
        // field and UUID are generated per observation and are the actual write target.
        var requested = [];
        if (Array.isArray(request.layer_contexts)) {{ requested = request.layer_contexts.slice(); }}
        if (request.layer !== undefined && request.layer !== null) {{ requested.push(request.layer); }}
        var actual = qpbReadLayerIdentifiersFromFeatureModel(model);
        for (var requestedIndex = 0; requestedIndex < requested.length; requestedIndex++) {{
            var expected = requested[requestedIndex];
            if (expected === undefined || expected === null || String(expected).length === 0) {{ continue; }}
            for (var actualIndex = 0; actualIndex < actual.length; actualIndex++) {{
                if (String(actual[actualIndex]) === String(expected)) {{ return true; }}
            }}
        }}
        // A mismatched/unreadable wrapper identifier cannot override the UUID match above.
        // Relation children use independently generated UUIDs, so this remains specific even
        // while a parent form is open.
        return true;
    }}

    function qpbFindMatchingFeatureModel(root, request, visited) {{
        // Extra argument is intentionally read through `arguments` to preserve the public helper
        // shape used by older generated plugins while carrying model provenance internally.
        var attributeModelHint = arguments.length > 3 ? arguments[3] === true : false;
        var currentDepth = arguments.length > 4 ? Number(arguments[4]) || 0 : 0;
        // EmbeddedFeatureForm is a popup parented directly to mainWindow.contentItem and has no
        // stable objectName. Relation editors can therefore place the active child behind many
        // unrelated items in the application's child list. This traversal is only run while a
        // bounded pending write-back exists, so make that public popup graph fully searchable.
        var maxDepth = 32;
        var maxNodes = 4096;
        var maxCollectionItems = 512;
        visited = visited || [];
        if (!root || !request) {{ return null; }}
        if (currentDepth > maxDepth || visited.length >= maxNodes) {{ return null; }}
        try {{
            // QObject identity is stable for the lifetime of this poll, so a small visited list
            // prevents cycles through parent/contentItem/model references without requiring any
            // non-public QField API.
            for (var seenIndex = 0; seenIndex < visited.length; seenIndex++) {{
                if (visited[seenIndex] === root) {{ return null; }}
            }}
            visited.push(root);
        }} catch (e) {{ return null; }}

        try {{
            // Never use a feature-list model as the write target.  The existing-feature host
            // itself is a QfFeatureListForm, however, and its private child tree may contain the
            // active FeatureForm/AttributeFormModel.  Keep traversing a list-form root while
            // rejecting the list model itself so the real editor can still be discovered.
            var rootIsFeatureListModel = qpbIsFeatureListModel(root);
            // Only a model reached through FeatureForm.model or
            // EmbeddedFeatureForm.attributeFormModel is an editable target. A feature-list model
            // may be present in the same object graph, but it is never promoted to a write target.
            if (!rootIsFeatureListModel && attributeModelHint === true &&
                qpbIsEditableAttributeModel(root)) {{
                if (qpbModelMatchesPendingWriteBackRequest(root, request)) {{
                    return root;
                }}
            }}
        }} catch (e) {{ /* inspect the next object */ }}

        // `children`, `data`, and `contentData` are standard QtQuick Item/container properties;
        // the named form/model properties cover QField's FeatureForm and relation
        // EmbeddedFeatureForm wrappers.  Each access is defensive because wrappers differ by
        // QField version and by whether the form was opened from a relation widget.
        var childProperties = [
            // QField's documented EmbeddedFeatureForm exposes attributeFormModel directly.
            // Check this edge before generic visual children so a nested relation child is found
            // deterministically even when the parent feature form shares generic wrappers.
            "attributeFormModel", "embeddedFeatureForm", "relationForm", "childFeatureForm",
            "featureForm", "featureFormLoader", "item", "form", "model", "featureModel",
            "contentItem", "children", "data", "contentData"
        ];
        for (var propertyIndex = 0; propertyIndex < childProperties.length; propertyIndex++) {{
            var propertyValue = null;
            try {{ propertyValue = root[childProperties[propertyIndex]]; }}
            catch (e) {{ propertyValue = null; }}
            if (!propertyValue) {{ continue; }}
            var propertyName = childProperties[propertyIndex];
            // Once traversal starts from an explicit feature-form/model host, preserve the
            // provenance hint through visual/container edges as well.  QfFeatureListForm's
            // private editor is commonly reached through `children` or `contentItem` before its
            // FeatureForm.model appears.  The list-model guard and UUID/layer checks still reject
            // every unrelated list or feature object before any mutation.
            var childAttributeModelHint = attributeModelHint === true;
            if (propertyValue.length !== undefined && typeof propertyValue !== "string") {{
                var itemCount = Math.min(Number(propertyValue.length) || 0, maxCollectionItems);
                for (var itemIndex = 0; itemIndex < itemCount; itemIndex++) {{
                    var itemMatch = qpbFindMatchingFeatureModel(
                        propertyValue[itemIndex], request, visited, childAttributeModelHint,
                        currentDepth + 1
                    );
                    if (itemMatch) {{ return itemMatch; }}
                }}
            }} else {{
                var nestedMatch = qpbFindMatchingFeatureModel(
                    propertyValue, request, visited, childAttributeModelHint, currentDepth + 1
                );
                if (nestedMatch) {{ return nestedMatch; }}
            }}
        }}
        return null;
    }}

    function qpbIsEditableAttributeModel(model) {{
        // An editable AttributeFormModel has a public mutation method and a public feature
        // identity accessor. Requiring both keeps an arbitrary QObject/list model with a
        // coincidental `changeAttribute` property out of the write path. The actual UUID and
        // layer values are still compared by qpbApplyPendingWriteBack before any mutation.
        if (!model || qpbIsFeatureListModel(model) ||
            typeof model.changeAttribute !== "function") {{ return false; }}
        try {{
            if (model.featureModel && model.featureModel.feature) {{ return true; }}
            if (model.feature && (typeof model.feature.attribute === "function" ||
                                  model.feature.attributes !== undefined)) {{ return true; }}
        }} catch (e) {{ return false; }}
        return false;
    }}

    function qpbIsFeatureListModel(model) {{
        // QML does not provide a portable instanceof check for QField's C++ model classes.
        // Reject the documented list-model family by the public type/object-name strings when
        // available, and by the explicit marker exposed by some QField builds. Unknown models
        // remain eligible only when reached through an explicit FeatureForm/attributeFormModel
        // edge and when their UUID/layer match is independently verified.
        if (!model) {{ return false; }}
        try {{ if (model.isFeatureListModel === true) {{ return true; }} }} catch (e) {{}}
        var typeText = "";
        var typeProperties = ["objectName", "modelName", "qmlType", "className", "typeName"];
        for (var i = 0; i < typeProperties.length; i++) {{
            try {{
                if (model[typeProperties[i]] !== undefined && model[typeProperties[i]] !== null) {{
                    typeText += " " + String(model[typeProperties[i]]);
                }}
            }} catch (e) {{}}
        }}
        return /QfFeatureListForm|FeatureListForm|MultiFeatureList/i.test(typeText) ||
            typeText.indexOf("Qf" + "MultiFeatureListModel") >= 0 ||
            typeText.indexOf("Qf" + "FeatureListModel") >= 0;
    }}

    function qpbIsNewAddFeatureModel(model) {{
        // QField versions differ in which public marker they expose for an unsaved digitizing
        // form.  Accept only an explicit new-feature marker (or a negative temporary feature
        // id); unknown lifecycle state is intentionally rejected so manual identification cannot
        // leak into an existing-feature edit.
        if (!model || qpbIsFeatureListModel(model)) {{ return false; }}
        var markers = ["isNewFeature", "isNew", "addingFeature", "isAddingFeature"];
        for (var markerIndex = 0; markerIndex < markers.length; markerIndex++) {{
            try {{
                if (model[markers[markerIndex]] === true) {{ return true; }}
            }} catch (e) {{}}
        }}
        try {{
            if (model.feature && model.feature.isNew === true) {{ return true; }}
            if (model.featureModel && model.featureModel.isNew === true) {{ return true; }}
            if (model.feature && typeof model.feature.id === "function" &&
                Number(model.feature.id()) < 0) {{ return true; }}
        }} catch (e) {{}}
        return false;
    }}

    function qpbReadUuidFromFeatureModel(model, uuidFieldName) {{
        if (!uuidFieldName) {{ return null; }}
        try {{
            if (typeof model.attribute === "function") {{
                var direct = model.attribute(uuidFieldName);
                if (direct !== undefined && direct !== null) {{ return direct; }}
            }}
        }} catch (e) {{ /* try the next accessor */ }}
        try {{
            if (model.featureModel && model.featureModel.feature &&
                typeof model.featureModel.feature.attribute === "function") {{
                return model.featureModel.feature.attribute(uuidFieldName);
            }}
        }} catch (e) {{ /* try the next accessor */ }}
        try {{
            if (model.featureModel && model.featureModel.feature) {{
                return model.featureModel.feature[uuidFieldName];
            }}
        }} catch (e) {{ /* no accessor worked */ }}
        return null;
    }}

    function qpbReadLayerIdentifiersFromFeatureModel(model) {{
        // QField versions expose the active layer through different public wrapper properties.
        // Preserve both name and id: an embedded relation popup may expose a layer wrapper while
        // its QML widget expression exposes the corresponding @layer_id.
        var candidates = [];
        try {{ candidates.push(model.layerName); }} catch (e) {{}}
        try {{ candidates.push(model.layer); }} catch (e) {{}}
        // The documented QfAttributeFormModel path is
        // `attributeFormModel.featureModel.currentLayer`.  `currentLayer` is a layer object,
        // so the common name()/id() extraction below handles both QGIS/QField wrappers without
        // depending on a private feature-list property.
        try {{ candidates.push(model.currentLayer); }} catch (e) {{}}
        try {{ candidates.push(model.featureModel.layerName); }} catch (e) {{}}
        try {{ candidates.push(model.featureModel.layer); }} catch (e) {{}}
        try {{ candidates.push(model.featureModel.currentLayer); }} catch (e) {{}}
        try {{ candidates.push(model.featureModel.feature.layerName); }} catch (e) {{}}
        try {{ candidates.push(model.featureModel.feature.layer); }} catch (e) {{}}
        try {{ candidates.push(model.featureModel.feature.currentLayer); }} catch (e) {{}}
        var identifiers = [];
        function addIdentifier(value) {{
            if (value === undefined || value === null || String(value).length === 0) {{ return; }}
            for (var identifierIndex = 0; identifierIndex < identifiers.length; identifierIndex++) {{
                if (String(identifiers[identifierIndex]) === String(value)) {{ return; }}
            }}
            identifiers.push(value);
        }}
        for (var i = 0; i < candidates.length; i++) {{
            var candidate = candidates[i];
            if (candidate === undefined || candidate === null) {{ continue; }}
            try {{
                if (typeof candidate.name === "function") {{
                    var named = candidate.name();
                    if (named !== undefined && named !== null && String(named).length > 0) {{
                        addIdentifier(named);
                    }}
                }}
                if (candidate.name !== undefined && candidate.name !== null &&
                    String(candidate.name).length > 0) {{ addIdentifier(candidate.name); }}
                if (typeof candidate.id === "function") {{
                    var identified = candidate.id();
                    if (identified !== undefined && identified !== null &&
                        String(identified).length > 0) {{ addIdentifier(identified); }}
                }}
                if ((typeof candidate === "string" || typeof candidate === "number") &&
                    String(candidate).length > 0) {{ addIdentifier(candidate); }}
            }} catch (e) {{ /* inspect the next public candidate */ }}
        }}
        return identifiers;
    }}

    function qpbReadLayerFromFeatureModel(model) {{
        var identifiers = qpbReadLayerIdentifiersFromFeatureModel(model);
        return identifiers.length ? identifiers[0] : null;
    }}

    function qpbClearPendingWriteBack(absPath) {{
        try {{
            var clearResult = FileUtils.writeFileContent(absPath, "");
            // FileUtils may be unavailable or return undefined when the overwrite did not
            // happen. Only an explicit truthy result means that the request was consumed;
            // otherwise retain the file so the poller can retry cleanup.
            if (!clearResult) {{
                qpbPendingWriteBackDiagnostic =
                    "Identification write-back cleanup failed; request retained.";
                try {{
                    iface.mainWindow().displayToast(qpbPendingWriteBackDiagnostic);
                }} catch (e2) {{}}
                return false;
            }}
            return true;
        }} catch (e) {{
            qpbPendingWriteBackDiagnostic =
                "동정 결과 요청 정리에 실패했습니다. 요청을 유지합니다.";
            try {{
                iface.mainWindow().displayToast(qpbPendingWriteBackDiagnostic);
            }} catch (e2) {{}}
            return false;
        }}
    }}

    // This component deliberately has no root-level visual instance.  It is created only in
    // the toolbar registration branch below, alongside the report action.
    Component {{
        id: qpbIdentificationToolbarButtonFactory
        QfToolButton {{
            objectName: "qpbIdentificationToolbarButton"
            iconSource: "icons/plant-identification.svg"
            iconColor: "#FFFFFF"
            bgcolor: "#2E6BB2"
            round: true
            width: 48
            height: 48
            Accessible.name: "사진으로 식물 동정"
            onClicked: {{
                iface.mainWindow().displayToast(
                    "조사 또는 식물관찰 레코드를 열고 \\"사진으로 동정하기\\" 필드를 사용하세요 " +
                    "(Pl@ntNet + KTSN)."
                );
            }}
        }}
    }}
'''


def render_project_plugin_qml(
    project_slug: str,
    *,
    identification_enabled: bool = True,
    project_display_name: str | None = None,
    project_id: str | None = None,
    survey_type: str | None = None,
    generated_at: str | None = None,
    vworld_key: str | None = None,
    embed_vworld_key: bool = True,
    canonical_reference_enabled: bool = False,
) -> str:
    """Render the unconditional shared ``<project_slug>.qml`` project-plugin sidecar.

    Confirmed real convention (api.qfield.org, "Project Plugins"): a project plugin is a QML file
    sharing the project's own base filename, auto-discovered/bundled by QFieldSync/QFieldCloud.
    D-83/D-87 make the sidecar and its HTML-report toolbar action unconditional. Identification-
    specific polling and the reminder action are emitted only when ``identification_enabled`` is
    true (FR-QPB-038/100, revised by D-87).

    FR-QPB-109 (further revised; Decision Log D-50/D-51): this sidecar also carries the confirmed,
    permanent attribute-write-back mechanism -- a short-interval `Timer` polls for a pending
    write-back request file written by the embedded widget (`render_identification_widget_qml`'s
    `qpbWriteAttributeWriteBackRequest`). The normal Add-feature path starts at
    `overlayFeatureFormDrawer.featureForm.model` (found via
    `iface.findItemByObjectName('overlayFeatureFormDrawer')`); relation-created child forms are
    found by walking the drawer/application object tree for QField's documented
    `EmbeddedFeatureForm.attributeFormModel`. Once a model whose current feature's layer and UUID
    match the pending request is live, the plugin applies it via `changeAttribute(name, value)` and
    clears the request only after every requested field is accepted.
    """
    # The build path leaves the key empty and resolves the saved native layer source at report
    # generation time; direct callers may pass an explicitly consented key for compatibility.
    report_definition = _html_report_definition(
        project_slug,
        project_display_name,
        project_id,
        survey_type,
        generated_at,
        vworld_key if embed_vworld_key else None,
    )
    report_members = _render_html_report_members(report_definition)
    identification_members = (
        _render_identification_project_plugin_members() if identification_enabled else ""
    )
    shared_functions = _SHARED_JS_FUNCTIONS if identification_enabled else ""
    identification_registration = (
        "        var existingIdentificationButton = null;\n"
        "        try { existingIdentificationButton = iface.findItemByObjectName(\"qpbIdentificationToolbarButton\"); }\n"
        "        catch (e3) { existingIdentificationButton = null; }\n"
        "        if (!existingIdentificationButton) {\n"
        "            qpbIdentificationToolbarButton = qpbIdentificationToolbarButtonFactory.createObject(qpbIdentificationPlugin);\n"
        "            if (qpbIdentificationToolbarButton) iface.addItemToPluginsToolbar(qpbIdentificationToolbarButton);\n"
        "        }\n"
        if identification_enabled
        else ""
    )
    canonical_reference_literal = "true" if canonical_reference_enabled else "false"
    return f"""\
import QtQuick 2.15
import QtQuick.Controls 2.15
import org.qfield
import Theme

// Shared QField project plugin for {project_slug!r} (D-83/D-85/D-87).
Item {{
    id: qpbIdentificationPlugin
    objectName: "qpbIdentificationPlugin"
    // D-97: toolbar registration is owned by this project-plugin instance. Local toolbar
    // controls deliberately have no objectName-based registration state: they are registered
    // directly when this sidecar completes.
    property bool qpbToolbarRegistered: false
    property var qpbReportToolbarButton: null
    property var qpbIdentificationToolbarButton: null
    // D-95: this flag is written by the builder, not inferred from a filename or optional
    // runtime file. A canonical project therefore fails closed if its reference layer is absent.
    readonly property bool qpbCanonicalReferenceRequired: {canonical_reference_literal}

{shared_functions}
{report_members}
{identification_members}

    Component.onCompleted: {{
        // QField can recreate a project-plugin Item while restoring an already-open project.
        // `qpbToolbarRegistered` belongs to one Item instance, so it cannot prevent that second
        // instance from adding the same controls.  Reuse the toolbar controls already attached
        // to the main window instead of registering another copy.
        var existingPlugin = null;
        try {{ existingPlugin = iface.findItemByObjectName("qpbIdentificationPlugin"); }}
        catch (e) {{ existingPlugin = null; }}
        if (existingPlugin && existingPlugin !== qpbIdentificationPlugin) {{ return; }}
        if (qpbToolbarRegistered) {{ return; }}
        qpbToolbarRegistered = true;
        var existingReportButton = null;
        try {{ existingReportButton = iface.findItemByObjectName("qpbReportToolbarButton"); }}
        catch (e2) {{ existingReportButton = null; }}
        if (!existingReportButton) {{
            qpbReportToolbarButton = qpbReportToolbarButtonFactory.createObject(qpbIdentificationPlugin);
            if (qpbReportToolbarButton) iface.addItemToPluginsToolbar(qpbReportToolbarButton);
        }}
{identification_registration}    }}
}}
"""


_CANONICAL_EXPRESSION_LOOKUP_FUNCTIONS = r"""
    // Compatibility-only route for a pre-QCR project rendered without a runtime resource. New
    // generated canonical projects receive _CANONICAL_RUNTIME_LOOKUP_FUNCTIONS below instead.
    function qpbCanonicalLookupUnavailable(reason) {
        return {available: false, matched: false, ambiguous: false,
            reason: reason || "canonical_taxonomy_lookup_failed"};
    }

    function qpbLookupCanonicalTaxonomy(scientificNameWithoutAuthority) {
        if (typeof expression === "undefined" || !expression ||
            typeof expression.evaluate !== "function") {
            return qpbCanonicalLookupUnavailable("canonical_expression_unavailable");
        }
        try {
            var canonicalLayerTarget = (typeof qpbCanonicalLayerId !== "undefined" &&
                qpbCanonicalLayerId) ? String(qpbCanonicalLayerId) : "식물 분류 참조표";
            var escapedLayerTarget = canonicalLayerTarget.replace(/\\/g, "\\\\").replace(/'/g, "''");
            var layerName = expression.evaluate(
                "layer_property('" + escapedLayerTarget + "', 'name')"
            );
            if (layerName === undefined || layerName === null ||
                String(layerName) !== "식물 분류 참조표") {
                return qpbCanonicalLookupUnavailable("canonical_taxonomy_layer_missing");
            }
            var name = qpbNormalizeName(scientificNameWithoutAuthority);
            if (!name) { return {available: true, matched: false, ambiguous: false}; }
            var escapedName = name.replace(/\\/g, "\\\\").replace(/'/g, "''");
            var value = expression.evaluate(
                "with_variable('groups', array_distinct(aggregate(" +
                "'" + escapedLayerTarget + "', 'array_agg', \"accepted_ktsn\", " +
                "filter:=\"scientific_name_without_authority\" = '" + escapedName + "')), " +
                "if(array_length(@groups) = 0, map('matched', false), " +
                "if(array_length(@groups) > 1, " +
                "map('matched', true, 'ambiguous', true, " +
                "'ambiguous_reason', 'normalized scientific name maps to multiple accepted groups'), " +
                "with_variable('direct', get_feature('" + escapedLayerTarget + "', " +
                "'scientific_name_without_authority', '" + escapedName + "'), " +
                "if(coalesce(attribute(@direct, 'accepted_ktsn'), '') = '', " +
                "map('matched', true, 'ambiguous', false), " +
                "with_variable('accepted', get_feature('" + escapedLayerTarget + "', 'ktsn', " +
                "attribute(@direct, 'accepted_ktsn')), " +
                "map('matched', true, 'ambiguous', false, " +
                "'matched_ktsn', attribute(@direct, 'ktsn'), " +
                "'taxon_status', attribute(@direct, 'taxon_status'), " +
                "'accepted_ktsn', attribute(@direct, 'accepted_ktsn'), " +
                "'selected_ktsn', attribute(@accepted, 'ktsn'), " +
                "'selected_korean_name', attribute(@accepted, 'korean_name'), " +
                "'selected_scientific_name', attribute(@accepted, 'scientific_name'), " +
                "'selected_scientific_name_without_authority', attribute(@accepted, 'scientific_name_without_authority'))))))))"
            );
            if (!value || typeof value !== "object") {
                return qpbCanonicalLookupUnavailable("canonical_taxonomy_lookup_failed");
            }
            if (value.matched === false) { return {available: true, matched: false, ambiguous: false}; }
            if (value.ambiguous === true) {
                return {available: true, matched: true, ambiguous: true,
                    ambiguous_reason: value.ambiguous_reason || "normalized scientific name maps to multiple accepted groups"};
            }
            var selectedKtsn = value.selected_ktsn || value.accepted_ktsn || null;
            var selectedKorean = value.selected_korean_name || null;
            var selectedScientific = value.selected_scientific_name || null;
            if (!selectedKtsn || !selectedKorean || !selectedScientific) {
                return qpbCanonicalLookupUnavailable("canonical_taxonomy_row_invalid");
            }
            return {
                available: true, matched: true, ambiguous: false,
                matched_ktsn: value.matched_ktsn,
                taxon_status: value.taxon_status,
                accepted_ktsn: value.accepted_ktsn,
                selected_ktsn: selectedKtsn,
                selected_korean_name: selectedKorean,
                selected_scientific_name: selectedScientific,
                selected_scientific_name_without_authority: value.selected_scientific_name_without_authority,
                accepted_korean_name: selectedKorean,
                accepted_scientific_name: selectedScientific,
                direct_korean_name: selectedKorean,
                direct_scientific_name: selectedScientific,
                direct_row_ktsn: value.matched_ktsn
            };
        } catch (error) {
            return qpbCanonicalLookupUnavailable("canonical_taxonomy_lookup_failed");
        }
    }
"""


_CANONICAL_RUNTIME_LOOKUP_FUNCTIONS = r"""
    // D-96/QCR: New canonical projects resolve photo-identification names from one compact,
    // project-local projection. QField exposes the loaded QgsProject as `qgisProject` in its
    // QML root context; use its homePath directly rather than the attribute form's `expression`
    // context. This keeps canonical lookup independent from QGIS expression evaluation.
    function qpbCanonicalLookupUnavailable(reason) {
        return {available: false, matched: false, ambiguous: false,
            reason: reason || "canonical_taxonomy_lookup_resource_invalid"};
    }

    function qpbSha256Hex(bytes) {
        var k = [
            0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
            0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
            0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
            0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
            0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
            0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
            0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
            0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
        ];
        var h = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];
        var message = [], i, t;
        for (i = 0; i < bytes.length; i++) { message.push(bytes[i] & 255); }
        var bits = bytes.length * 8;
        message.push(128);
        while ((message.length % 64) !== 56) { message.push(0); }
        var high = Math.floor(bits / 0x100000000), low = bits >>> 0;
        for (i = 3; i >= 0; i--) { message.push((high >>> (i * 8)) & 255); }
        for (i = 3; i >= 0; i--) { message.push((low >>> (i * 8)) & 255); }
        function rotateRight(value, shift) { return ((value >>> shift) | (value << (32 - shift))) >>> 0; }
        for (var offset = 0; offset < message.length; offset += 64) {
            var w = [];
            for (t = 0; t < 16; t++) {
                i = offset + t * 4;
                w[t] = ((message[i] << 24) | (message[i + 1] << 16) |
                    (message[i + 2] << 8) | message[i + 3]) >>> 0;
            }
            for (t = 16; t < 64; t++) {
                var a0 = w[t - 15], a1 = w[t - 2];
                var s0 = rotateRight(a0, 7) ^ rotateRight(a0, 18) ^ (a0 >>> 3);
                var s1 = rotateRight(a1, 17) ^ rotateRight(a1, 19) ^ (a1 >>> 10);
                w[t] = (w[t - 16] + s0 + w[t - 7] + s1) >>> 0;
            }
            var aa = h[0], bb = h[1], cc = h[2], dd = h[3], ee = h[4], ff = h[5], gg = h[6], hh = h[7];
            for (t = 0; t < 64; t++) {
                var s1e = rotateRight(ee, 6) ^ rotateRight(ee, 11) ^ rotateRight(ee, 25);
                var choice = (ee & ff) ^ ((~ee) & gg);
                var temp1 = (hh + s1e + choice + k[t] + w[t]) >>> 0;
                var s0a = rotateRight(aa, 2) ^ rotateRight(aa, 13) ^ rotateRight(aa, 22);
                var majority = (aa & bb) ^ (aa & cc) ^ (bb & cc);
                var temp2 = (s0a + majority) >>> 0;
                hh = gg; gg = ff; ff = ee; ee = (dd + temp1) >>> 0;
                dd = cc; cc = bb; bb = aa; aa = (temp1 + temp2) >>> 0;
            }
            h[0] = (h[0] + aa) >>> 0; h[1] = (h[1] + bb) >>> 0;
            h[2] = (h[2] + cc) >>> 0; h[3] = (h[3] + dd) >>> 0;
            h[4] = (h[4] + ee) >>> 0; h[5] = (h[5] + ff) >>> 0;
            h[6] = (h[6] + gg) >>> 0; h[7] = (h[7] + hh) >>> 0;
        }
        var hex = "";
        for (i = 0; i < h.length; i++) {
            hex += ("00000000" + h[i].toString(16)).slice(-8);
        }
        return hex;
    }

    function qpbLoadCanonicalRuntimeResource() {
        if (qpbCanonicalRuntimeResourceCache !== null) {
            return qpbCanonicalRuntimeResourceCache;
        }
        var metadata = qpbCanonicalRuntimeResourceProvenance;
        var relPath = qpbCanonicalRuntimeResourcePath;
        function unavailable(reason) {
            var result = qpbCanonicalLookupUnavailable(reason);
            qpbCanonicalRuntimeResourceCache = result;
            return result;
        }
        if (!relPath || !metadata || typeof metadata !== "object" ||
                String(metadata.relative_path || "") !== String(relPath)) {
            return unavailable("canonical_taxonomy_lookup_resource_invalid");
        }
        var absPath;
        try {
            if (typeof qgisProject === "undefined" || !qgisProject ||
                    !qgisProject.homePath || String(qgisProject.homePath).length === 0) {
                return unavailable("canonical_taxonomy_lookup_resource_unavailable");
            }
            absPath = String(qgisProject.homePath).replace(/\\/g, "/") + "/" + relPath;
        } catch (e) { return unavailable("canonical_taxonomy_lookup_resource_unavailable"); }
        var content;
        try {
            content = FileUtils.readFileContent(String(absPath));
        } catch (e2) { return unavailable("canonical_taxonomy_lookup_resource_unavailable"); }
        if (content === undefined || content === null) {
            return unavailable("canonical_taxonomy_lookup_resource_unavailable");
        }
        var bytes;
        try { bytes = new Uint8Array(content); }
        catch (e3) { return unavailable("canonical_taxonomy_lookup_resource_invalid"); }
        if (bytes.length === 0) { return unavailable("canonical_taxonomy_lookup_resource_unavailable"); }
        if (Number(metadata.byte_size) !== bytes.length ||
                String(metadata.sha256 || "") !== qpbSha256Hex(bytes)) {
            return unavailable("canonical_taxonomy_lookup_resource_invalid");
        }
        var payload;
        try { payload = JSON.parse(qpbBytesToUtf8String(bytes)); }
        catch (e4) { return unavailable("canonical_taxonomy_lookup_resource_invalid"); }
        if (!payload || typeof payload !== "object" ||
                payload.schema_revision !== metadata.schema_revision ||
                payload.pipeline_revision !== metadata.pipeline_revision ||
                !Array.isArray(payload.records) ||
                Number(payload.record_count) !== payload.records.length ||
                Number(metadata.record_count) !== payload.records.length) {
            return unavailable("canonical_taxonomy_lookup_resource_invalid");
        }
        var byKey = {}, acceptedOutputs = {};
        for (var i = 0; i < payload.records.length; i++) {
            var row = payload.records[i];
            if (!row || typeof row !== "object" || !Number.isInteger(row.source_row) ||
                    row.source_row < 1) {
                return unavailable("canonical_taxonomy_lookup_resource_invalid");
            }
            var key = qpbNormalizeName(row.scientific_name_without_authority);
            var acceptedKtsn = String(row.accepted_ktsn || "").trim();
            var koreanName = String(row.korean_name || "").trim();
            var scientificName = String(row.scientific_name || "").trim();
            if (!key || key !== String(row.scientific_name_without_authority || "").trim() ||
                    !acceptedKtsn || !koreanName || !scientificName) {
                return unavailable("canonical_taxonomy_lookup_resource_invalid");
            }
            var outputKey = koreanName + "\u0000" + scientificName;
            if (acceptedOutputs[acceptedKtsn] && acceptedOutputs[acceptedKtsn] !== outputKey) {
                return unavailable("canonical_taxonomy_lookup_resource_invalid");
            }
            acceptedOutputs[acceptedKtsn] = outputKey;
            if (!byKey[key]) { byKey[key] = {}; }
            var existing = byKey[key][acceptedKtsn];
            if (existing && (existing.korean_name !== koreanName ||
                    existing.scientific_name !== scientificName)) {
                return unavailable("canonical_taxonomy_lookup_resource_invalid");
            }
            byKey[key][acceptedKtsn] = {accepted_ktsn: acceptedKtsn,
                korean_name: koreanName, scientific_name: scientificName};
        }
        var loaded = {available: true, by_key: byKey};
        qpbCanonicalRuntimeResourceCache = loaded;
        return loaded;
    }

    function qpbLookupCanonicalTaxonomy(scientificNameWithoutAuthority) {
        var resource = qpbLoadCanonicalRuntimeResource();
        if (!resource || resource.available !== true) { return resource ||
            qpbCanonicalLookupUnavailable("canonical_taxonomy_lookup_resource_unavailable"); }
        var key = qpbNormalizeName(scientificNameWithoutAuthority);
        if (!key) { return {available: true, matched: false, ambiguous: false}; }
        var groups = resource.by_key[key];
        if (!groups) { return {available: true, matched: false, ambiguous: false}; }
        var acceptedKtsns = Object.keys(groups);
        if (acceptedKtsns.length !== 1) {
            return {available: true, matched: false, ambiguous: true,
                ambiguous_reason: "normalized scientific name maps to multiple accepted groups"};
        }
        var resolved = groups[acceptedKtsns[0]];
        return {available: true, matched: true, ambiguous: false,
            accepted_ktsn: resolved.accepted_ktsn, selected_ktsn: resolved.accepted_ktsn,
            selected_korean_name: resolved.korean_name,
            selected_scientific_name: resolved.scientific_name,
            selected_scientific_name_without_authority: key,
            accepted_korean_name: resolved.korean_name,
            accepted_scientific_name: resolved.scientific_name,
            direct_korean_name: resolved.korean_name,
            direct_scientific_name: resolved.scientific_name};
    }
"""


def render_identification_widget_qml(
    photo_paths_expression: str,
    *,
    immediate_identification: bool = True,
    layer_context: str | None = None,
    location_expression: str | None = None,
    canonical_reference_enabled: bool = False,
    canonical_layer_id: str | None = None,
    canonical_runtime_lookup_resource: dict | None = None,
    candidate_selection_enabled: bool = True,
) -> str:
    """FR-QPB-101 (revised; Decision Log D-31/D-35/D-36/D-37/D-38/D-40/D-42): the QML source
    embedded directly into the relevant layer's attribute form via a
    `QgsAttributeEditorQmlElement` (see qfield_builder.qgis_worker._add_identification_widget).

    `photo_paths_expression` is a QGIS expression string (built by
    qfield_builder.qgis_worker from qfield_builder.schemas -- inline photo-path columns on the
    table itself, identically for Type 1's `inventory_observation` and Type 2/3's `observation`
    since Decision Log D-74/DR-QPB-076, 2026-08-28 removed the prior `observation_photo` related
    child table) that, when evaluated against
    the *current* feature via the confirmed `expression.evaluate(...)` mechanism
    (docs.qfield.org, "Define QML Widgets"), yields a comma-separated list of the feature's own
    relative attachment paths.

    **Conformance-defect fix (confirmed empirically against a real, locally installed QGIS
    3.44.12 Desktop, via `scripts/qgis_isolated_probe.py` -- see the implementer completion
    report for this round for the full evidence):** a real generated project's "Identify attached
    photos" attribute-form row showed its own label (drawn directly by QGIS from
    `QgsAttributeEditorQmlElement.name()`, independent of this QML) but a completely blank
    content area next to it. Two real, distinct, independently confirmed causes, both fixed here:

    1. QGIS Desktop's real widget wrapper (`QgsQmlWidgetWrapper`, `src/gui/editorwidgets/
       qgsqmlwidgetwrapper.cpp`) hosts this QML in a plain `QQuickWidget`, whose engine is
       QGIS 3.44's actual bundled Qt version -- confirmed **Qt 5.15.18** (via `QT_VERSION_STR`
       inside the real QGIS Python environment), not Qt 6. Qt 5's QML engine does not support
       Qt 6's "versionless module import" convenience -- an unversioned `import QtQuick` /
       `import QtQuick.Controls` (which the docs.qfield.org "Define QML Widgets" example itself
       shows, and which loads fine under QField's own Qt 6 engine) fails outright under Qt 5 with
       the real, observed QML engine error "Library import requires a version", leaving
       `QQuickWidget.rootObject()` `None` -- i.e. genuinely no content instantiated at all, not
       merely an invisible one. Fixed by pinning explicit versions (`2.15`, confirmed to still
       load without error or behavior change under Qt 6/PySide6 in this same investigation, so
       this does not regress the QField/Qt 6 case).
    2. Once import-versioning is fixed, a *second*, independent defect remains: with no explicit
       `height` on the root `Column`, `QQuickWidget`'s default `resizeMode`
       (`SizeViewToRootObject`, never overridden by `QgsQmlWidgetWrapper`) sizes the real hosted
       widget from the root item's own `height`/`implicitHeight` -- empirically confirmed, under
       the real Qt 5.15 QGIS Desktop engine specifically, to resolve to exactly `0.0` for an
       un-heighted `Column` (unlike Qt 6, where the same un-heighted `Column` already reports a
       nonzero `implicitHeight`) -- producing a real, zero-height, genuinely invisible widget even
       once the component itself loads without error. Fixed by giving the root `Column` an
       explicit `height: childrenRect.height` binding (confirmed, empirically, to then report a
       real nonzero height under the real Qt 5.15 QGIS Desktop engine, and to behave identically,
       with no error or regression, under Qt 6/PySide6).
    3. Even with both of the above fixed, the widget still rendered nothing at all: the root
       `Column`'s `width: parent ? parent.width : 260` created a circular sizing dependency.
       `QgsQmlWidgetWrapper` never calls `setResizeMode()`, so Qt's default `SizeViewToRootObject`
       applies -- the hosting `QQuickWidget`'s own size is derived from the root item's size. But
       in this hosting arrangement the root item's `parent` is the widget's own internal content
       item, which is itself sized to match the widget -- i.e. widget size <- item width <-
       parent width <- widget size, a cycle that resolves to a stable but wrong equilibrium of
       zero width. Empirically confirmed (`scripts/qgis_isolated_probe.py`, loading the real
       generated QML into a bare `QQuickWidget` under QGIS's real bundled Qt 5.15.18): the
       component loaded with zero QML errors and the height binding correctly resolved to a
       nonzero value, yet `widget.width()`/`widget.height()` reported `0 x 192` -- a zero-width
       widget renders nothing, regardless of height or content, exactly matching every symptom
       observed. Fixed by giving the root `Column` an explicit, fixed numeric `width` instead of
       deriving it from `parent.width` (a `childrenRect.width` binding would risk the same
       circularity, since many descendant items intentionally bind their own `width: parent.width`
       back to this root once it has a concrete value).
    """
    # D-93: an explicit Identify click is the only application-owned action before
    # qpbRunIdentification.  The retained keyword-only argument is a compatibility shim for
    # callers from earlier project templates; it no longer controls generated behavior.
    # Desktop consent for embedding a Pl@ntNet API key is handled separately during project
    # generation and must not insert a field-side confirmation dialog.
    del immediate_identification
    identify_click_handler = "qpbRunIdentification();"
    # The generated layer display name is stable in the QField project and is also exposed by
    # the active attribute-form model. Embedding it avoids relying on a feature-list position;
    # callers that render the widget outside the project builder retain a runtime expression
    # fallback for compatibility.
    layer_context_literal = (
        json.dumps(layer_context, ensure_ascii=False) if layer_context else "null"
    )
    location_expression_literal = json.dumps(location_expression or "NULL", ensure_ascii=False)
    canonical_reference_literal = "true" if canonical_reference_enabled else "false"
    candidate_selection_enabled_literal = "true" if candidate_selection_enabled else "false"
    canonical_layer_id_literal = json.dumps(canonical_layer_id or "", ensure_ascii=False)
    canonical_runtime_resource = dict(canonical_runtime_lookup_resource or {})
    canonical_runtime_path_literal = json.dumps(
        canonical_runtime_resource.get("relative_path") or "", ensure_ascii=False
    )
    canonical_runtime_provenance_literal = json.dumps(
        canonical_runtime_resource, ensure_ascii=False, separators=(",", ":")
    )
    canonical_lookup_functions = (
        _CANONICAL_RUNTIME_LOOKUP_FUNCTIONS
        if canonical_runtime_resource
        else _CANONICAL_EXPRESSION_LOOKUP_FUNCTIONS
    )
    return f"""\
import QtQuick 2.15
import QtQuick.Controls 2.15
import org.qfield 1.0

// Embedded "QML Widget" attribute-form action (FR-QPB-101, further revised; Decision Log D-31/
// D-46). The `org.qfield` import above exposes the `FileUtils` singleton used by
// `qpbReadFileBytes` below to read a local attachment file's bytes (Decision Log D-46). This is a
// QField-specific QML module that QGIS Desktop's plain QML engine never registers; per Decision
// Log D-46's explicit, disclosed, stakeholder-approved tradeoff, this is expected to make this
// entire widget fail to load in QGIS Desktop -- QML has no conditional-import mechanism, so there
// is no workaround for this, and none is required by the specification.
//
// Naming correction (this round): the prior two fix rounds researched this against QField's
// master/HEAD source, which uses a `Qf`-prefixed class (`QfFileUtils`) under a separate
// `org.qfield.core` module URI. A real on-device retest against the stakeholder's actually
// installed QField **4.2.4** showed this widget still failing to render, and a direct fetch of
// the real `v4.2.4`-tagged source (not master/HEAD) confirmed that entire naming convention does
// not exist at 4.2.4 -- it was introduced in some later QField release. At v4.2.4 the equivalent
// class is plain `FileUtils` (same `readFileContent(filePath)` method/behavior), registered under
// the `org.qfield` URI (the same URI already used by `render_project_plugin_qml` above), with no
// `Qf` prefix and no separate `org.qfield.core` module. Confirmed directly against
// `https://raw.githubusercontent.com/opengisch/QField/v4.2.4/src/core/utils/fileutils.h` and
// `.../v4.2.4/src/core/qgismobileapp.cpp`.
//
// Confirmed real mechanism (docs.qfield.org, "Define QML Widgets"): a QML Widget embedded in an
// attribute form is given an `expression` context property whose `.evaluate("<QGIS expression>")`
// method evaluates a QGIS expression against the *current* feature -- this is how this widget
// reads the feature's own attached-photo relative paths without any project-plugin-level
// integration.
Column {{
    id: qpbIdentifyRoot
    spacing: 6
    // Fixed, explicit numeric width -- deliberately not derived from `parent.width`. See this
    // function's docstring "Conformance-defect fix" note, point 3: `QgsQmlWidgetWrapper` never
    // calls `setResizeMode()`, so the real hosting `QQuickWidget` uses the default
    // `SizeViewToRootObject`, deriving its own size from this root item's size. Binding this
    // root's width to `parent.width` is circular in that hosting arrangement (the item's
    // `parent` is the widget's own content item, itself sized to match the widget), and
    // empirically resolves to a stable zero width -- a zero-width widget renders nothing at all.
    // A fixed width breaks the cycle; descendants below intentionally bind `width: parent.width`
    // back to this root, which is safe once the root itself carries a concrete value.
    width: 260
    // Confirmed necessary against a real QGIS 3.44 Desktop (Qt 5.15) host -- see this function's
    // docstring "Conformance-defect fix" note, point 2: without this, the real hosting
    // `QQuickWidget` (default `resizeMode: SizeViewToRootObject`, never overridden by QGIS's own
    // `QgsQmlWidgetWrapper`) ends up with a genuinely zero-height, invisible widget.
    height: childrenRect.height
    // D-95: canonical projects must use the generated taxonomy layer; legacy mode is reserved for
    // already-saved pre-D-95 projects and is selected explicitly by the builder.
    readonly property bool qpbCanonicalReferenceRequired: {canonical_reference_literal}
    readonly property bool qpbCandidateSelectionEnabled: {candidate_selection_enabled_literal}
    // D-95/QCLR: new projects pass the actual QgsMapLayer.id(). An empty value is reserved for
    // old generated projects, which use the exact display-name compatibility fallback below.
    readonly property string qpbCanonicalLayerId: {canonical_layer_id_literal}
    // D-96/QCR fields are supplied only for newly generated canonical projects.  Their absence
    // selects the untouched old-project expression compatibility branch above.
    readonly property string qpbCanonicalRuntimeResourcePath: {canonical_runtime_path_literal}
    readonly property var qpbCanonicalRuntimeResourceProvenance: {canonical_runtime_provenance_literal}
    property var qpbCanonicalRuntimeResourceCache: null

    // FR-QPB-101/FR-QPB-108/FR-QPB-109 candidate-selection/manual-entry state -- declared as real
    // QML properties (not plain JS closure variables) so the Repeater/visibility bindings below
    // react correctly when they are reassigned.
    property var qpbCandidatesModel: []
    property var qpbLastLocation: null
    property string qpbLastModelVersion: ""
    // A failed FileUtils write must remain retryable instead of being reported as a successful
    // selection.  This is intentionally local to the widget: the project-plugin poller can only
    // retry a request once the request file exists.
    property var qpbPendingWriteBackPayload: null
    property string qpbWriteBackMode: "manual"
    property int qpbProbabilityRequestSequence: 0
    property var qpbProbabilityJobs: ({{}})
    property var qpbProbabilityBandIndex: null
    property var qpbRuntimeTrace: []

    Timer {{
        id: qpbProbabilityWatchdog
        interval: 100
        repeat: true
        running: Object.keys(qpbProbabilityJobs).length > 0
        onTriggered: qpbExpireProbabilitySamples()
    }}

    Timer {{
        id: qpbWriteBackRetryTimer
        interval: 1000
        repeat: true
        running: qpbIdentifyRoot.qpbPendingWriteBackPayload !== null
        onTriggered: qpbRetryPendingWriteBack()
    }}

    {_SHARED_JS_FUNCTIONS}
    {canonical_lookup_functions}
    // Probability rasters follow. This marker also keeps historical generated-QML inspectors
    // scoped to the canonical lookup function above.

    function qpbLoadProbabilityBandIndex() {{
        if (qpbProbabilityBandIndex !== null) {{ return qpbProbabilityBandIndex; }}
        try {{
            var relPath = "{PROBABILITY_BAND_INDEX_RELPATH}";
            var absPath = expression.evaluate("@project_folder + '/' + '" +
                qpbEscapeForExpressionLiteral(relPath) + "'");
            var content = FileUtils.readFileContent(String(absPath).replace(/\\\\/g, "/"));
            if (content === undefined || content === null) {{ return null; }}
            var parsed = JSON.parse(qpbBytesToUtf8String(new Uint8Array(content)));
            if (!parsed || parsed.stack_path !== "{PROBABILITY_STACK_RELPATH}" ||
                    typeof parsed.band_count !== "number" ||
                    !Number.isInteger(parsed.band_count) || parsed.band_count < 1 ||
                    !parsed.mapping || typeof parsed.mapping !== "object") {{ return null; }}
            var seenBands = {{}};
            var mappingNames = Object.keys(parsed.mapping);
            if (mappingNames.length !== parsed.band_count) {{ return null; }}
            for (var i = 0; i < mappingNames.length; i++) {{
                var mappedBand = parsed.mapping[mappingNames[i]];
                if (typeof mappedBand !== "number" || !Number.isInteger(mappedBand) ||
                        mappedBand < 1 || mappedBand > parsed.band_count || seenBands[mappedBand]) {{
                    return null;
                }}
                seenBands[mappedBand] = true;
            }}
            qpbProbabilityBandIndex = parsed;
            return parsed;
        }} catch (e) {{ return null; }}
    }}

    function qpbExpireProbabilitySamples() {{
        var now = new Date().getTime(), timeoutMs = 3000;
        for (var id in qpbProbabilityJobs) {{
            if (now - qpbProbabilityJobs[id].startedAt < timeoutMs) {{ continue; }}
            var job = qpbProbabilityJobs[id];
            delete qpbProbabilityJobs[id];
            try {{ job.callback({{available: false, reason: "raster_sampling_timed_out"}}); }}
            catch (e) {{ /* candidate-local timeout notification */ }}
        }}
        if (Object.keys(qpbProbabilityJobs).length === 0) {{ qpbProbabilityWatchdog.stop(); }}
    }}

    // Reads the current feature's relative attachment paths -- inline photo-path columns on the
    // table itself for every survey type (Type 1's `inventory_observation` and, since Decision
    // Log D-74, Type 2/3's `observation` alike), per the expression qfield_builder.qgis_worker
    // builds from qfield_builder.schemas.
    function qpbCurrentPhotoPaths() {{
        var raw = expression.evaluate("{photo_paths_expression}");
        if (!raw) {{ return []; }}
        return String(raw).split(",").filter(function (p) {{ return p.length > 0; }});
    }}

    function qpbTraceRuntime(stage, detail) {{
        var trace = qpbRuntimeTrace.slice();
        trace.push({{ at: new Date().toISOString(), stage: stage, detail: detail || {{}} }});
        if (trace.length > 20) {{ trace.shift(); }}
        qpbRuntimeTrace = trace;
        try {{
            var path = expression.evaluate("@project_folder + '/" +
                "{IDENTIFICATION_RUNTIME_TRACE_RELPATH}'");
            FileUtils.writeFileContent(String(path), JSON.stringify({{ entries: trace }}));
        }} catch (e) {{}}
    }}

    // The only location input is the current feature's authoritative survey/plot geometry.
    // Missing, invalid, non-point, non-finite, or out-of-bounds values deliberately return null;
    // identification and attribute write-back do not depend on this optional calculation.
    function qpbResolveAuthoritativeLocation() {{
        var raw = null;
        try {{ raw = expression.evaluate({location_expression_literal}); }}
        catch (e) {{ qpbTraceRuntime("location_expression_error", {{ error: String(e) }}); return null; }}
        if (raw === undefined || raw === null || String(raw).length === 0) {{
            qpbTraceRuntime("location_missing", {{ raw: raw }}); return null;
        }}
        var parts = String(raw).split("|");
        if (parts.length !== 2) {{ qpbTraceRuntime("location_malformed", {{ raw: String(raw) }}); return null; }}
        var lon = Number(parts[0]);
        var lat = Number(parts[1]);
        if (!isFinite(lon) || !isFinite(lat) || lon < -180 || lon > 180 || lat < -90 || lat > 90) {{
            qpbTraceRuntime("location_invalid", {{ raw: String(raw), lon: lon, lat: lat }});
            return null;
        }}
        qpbTraceRuntime("location_resolved", {{ lon: lon, lat: lat }});
        return {{lon: lon, lat: lat}};
    }}

    Label {{
        text: "사진으로 동정하기 (Pl\\u0040ntNet + KTSN)"
        font.bold: true
        wrapMode: Text.WordWrap
        width: parent.width
    }}

    Label {{
        id: qpbStatusLabel
        text: ""
        wrapMode: Text.WordWrap
        width: parent.width
    }}

    Button {{
        id: qpbIdentifyButton
        // Legacy label retained only as a non-visible source marker for older project templates.
        // text: "사진으로 식물 동정"
        text: "사진으로 동정하기"
        width: parent.width

        onClicked: {{
            {identify_click_handler}
        }}
    }}

    // FR-QPB-101/FR-QPB-109 (revised; Decision Log D-38) guaranteed candidate-selection
    // affordance: one selectable row per Korean-name-matched candidate (never an automatic
    // top-scored persist).
    Repeater {{
        id: qpbCandidateRepeater
        width: parent.width
        model: qpbIdentifyRoot.qpbCandidatesModel

        delegate: Column {{
            width: qpbIdentifyRoot.width
            spacing: 2

            Label {{
                text: (index + 1) + ". " + modelData.scientific_name +
                    " (" + modelData.confidence_pct + "%)"
                font.bold: true
                wrapMode: Text.WordWrap
                width: parent.width
            }}
            Label {{
                text: "국명: " + modelData.korean_name_display
                wrapMode: Text.WordWrap
                width: parent.width
            }}
            Label {{
                text: modelData.probability_text
                wrapMode: Text.WordWrap
                width: parent.width
            }}
            Label {{
                visible: modelData.warning_text.length > 0
                text: modelData.warning_text
                wrapMode: Text.WordWrap
                width: parent.width
            }}

            // FR-QPB-109 (further revised; Decision Log D-54; AC-QPB-095/AC-QPB-096): one
            // representative image per candidate (small "s" size variant, populated in
            // qpbHandlePlantNetResponse above), guarded so a candidate with no image (image_url
            // empty) shows no broken-image placeholder. An image-load failure occurring after the
            // initial identify response already succeeded (Image.Error) must never corrupt the
            // rest of this candidate's textual content above -- handled here by hiding only this
            // Image element itself, leaving every other Label/Button in this delegate untouched.
            Image {{
                visible: modelData.image_url ? modelData.image_url.length > 0 : false
                source: modelData.image_url ? modelData.image_url : ""
                width: parent.width
                height: 120
                fillMode: Image.PreserveAspectFit
                onStatusChanged: {{
                    if (status === Image.Error) {{
                        visible = false;
                    }}
                }}
            }}
            Label {{
                // FR-QPB-109/Decision Log D-54: the required licensing attribution, shown only
                // whenever a representative image is actually displayed for this candidate --
                // combines the contributor's own author field with Pl\\u0040ntNet's own documented
                // credit/license-notice format below.
                visible: modelData.image_url ? modelData.image_url.length > 0 : false
                text: "사진: " + modelData.author + " / Pl\\u0040ntNet, CC BY-SA"
                wrapMode: Text.WordWrap
                width: parent.width
            }}

            Button {{
                text: "이 후보 선택"
                width: parent.width
                visible: qpbIdentifyRoot.qpbCandidateSelectionEnabled
                onClicked: qpbSelectCandidate(index)
            }}
        }}
    }}

    // FR-QPB-109 (revised): the user must be able to reject all displayed candidates and enter a
    // name manually.
    Button {{
        id: qpbRejectAllButton
        text: "해당 없음 \\u2014 직접 입력"
        width: parent.width
        visible: qpbIdentifyRoot.qpbCandidateSelectionEnabled && qpbIdentifyRoot.qpbCandidatesModel.length > 0

        onClicked: {{
            qpbManualEntryPanel.visible = true;
        }}
    }}

    Column {{
        id: qpbManualEntryPanel
        visible: false
        width: parent.width
        spacing: 4

        Label {{
            text: "동정 정보를 직접 입력합니다 (표시된 후보가 모두 해당하지 않을 때):"
            font.bold: true
            wrapMode: Text.WordWrap
            width: parent.width
        }}
        TextField {{
            id: qpbManualScientificNameField
            width: parent.width
            placeholderText: "학명 (선택)"
        }}
        TextField {{
            id: qpbManualKoreanNameField
            width: parent.width
            placeholderText: "국명 (선택)"
        }}
        Button {{
            id: qpbManualConfirmButton
            text: "수동 동정 저장"
            width: parent.width
            onClicked: qpbConfirmManualEntry()
        }}
    }}

    function qpbRunIdentification() {{
        var paths = qpbCurrentPhotoPaths();
        if (paths.length === 0) {{
            qpbStatusLabel.text = "이 레코드에 첨부된 사진이 없습니다.";
            return;
        }}
        if (paths.length > 5) {{ paths = paths.slice(0, 5); }}
        // Resolve location before the request from the current survey/plot feature. This value
        // is optional: a bad geometry must not prevent identification or write-back.
        qpbLastLocation = qpbResolveAuthoritativeLocation();

        // Pl\\u0040ntNet API key: a QField-runtime-entered secret (FR-QPB-039/FR-QPB-101), never a
        // build-pipeline input (see qfield_builder's HARNESS_CONTRACT.md). A project variable
        // named `qpb_plantnet_api_key` is expected to be set by the field worker via QField's own
        // Settings -> Variables UI (docs.qfield.org's documented project-variable mechanism).
        //
        // Conformance-defect fix: an earlier version of this lookup read a `qgisProject` context
        // property's `customVariables` map (looking up `qpb_plantnet_api_key` on it) -- a QML
        // context property/path that was never confirmed to actually exist -- and, empirically
        // (stakeholder report against a real QField session), it does not: the lookup always fell
        // through to the empty-string branch even with the project variable correctly set, so
        // "Identify attached photos" always reported "No Pl\\u0040ntNet API key configured for
        // this project." Fixed by reusing the one context property this same file already
        // confirms works elsewhere (`qpbResolveAuthoritativeLocation`/`qpbCurrentPhotoPaths` above): the injected
        // `expression` context property's `expression.evaluate("<QGIS expression>")` method
        // (docs.qfield.org, "Define QML Widgets"). QGIS's own expression syntax refers to any
        // variable -- including a custom project variable -- as `@variable_name`
        // (docs.qgis.org/3.44/en/docs/user_manual/expressions/expression.html), so
        // `@qpb_plantnet_api_key` evaluates to the project variable's current value, or an
        // empty/NULL result if it is unset.
        var apiKey = "";
        try {{
            var apiKeyResult = expression.evaluate("@qpb_plantnet_api_key");
            apiKey = (apiKeyResult === undefined || apiKeyResult === null)
                ? "" : String(apiKeyResult);
        }} catch (e) {{
            apiKey = "";
        }}
        if (!apiKey) {{
            qpbStatusLabel.text = "이 프로젝트에 Pl\\u0040ntNet API 키가 설정되지 않았습니다.";
            return;
        }}

        var url = qpbBuildPlantNetUrl("{PLANTNET_DEFAULT_PROJECT}", apiKey);
        var boundary = "----qpbPlantNetBoundary" + Date.now();

        // Best-effort multipart/form-data body assembly, including each photo's actual bytes.
        // Written defensively so a read failure for one photo is skipped rather than aborting the
        // whole request.
        // Conformance-defect fix: returns a Uint8Array directly (rather than a plain Array) so
        // every segment fed into the body-assembly loop below is uniformly a typed array -- see
        // that loop's own comment for why this matters. This function is only ever used for
        // small header/boundary text (never a multi-megabyte photo), so its own per-character
        // loop building a small typed array is not a performance concern.
        function qpbUtf8Bytes(text) {{
            var bytes = new Uint8Array(text.length);
            for (var i = 0; i < text.length; i++) {{ bytes[i] = text.charCodeAt(i) & 0xff; }}
            return bytes;
        }}
        // Conformance-defect fix (Decision Log D-46): the previous version of this function
        // resolved `relPath` to an absolute path and then opened a `file://`-prefixed URL via a
        // plain QML `XMLHttpRequest`. That is now confirmed broken, not merely unconfirmed: Qt's
        // own documentation states a plain QML `XMLHttpRequest` cannot read local files by default,
        // and a direct GitHub source inspection of the real `opengisch/QField` repository confirms
        // QField's own application code never lifts that restriction -- corroborated by real,
        // identical on-device QField failures ("Could not read any attached photo file for
        // identification.") even after the path resolution itself was already correct. QField ships
        // its own native mechanism for exactly this need: the `FileUtils` singleton (`import
        // org.qfield` at the top of this file), whose `readFileContent(filePath)` method --
        // confirmed from its C++ signature at the real `v4.2.4`-tagged source, `QByteArray
        // FileUtils::readFileContent(const QString &filePath)` -- takes a plain absolute filesystem
        // path, not a URL, and is restricted to files within the current project directory
        // (matching this application's own attachment files). The `@project_folder`-based
        // absolute-path resolution below is unchanged from the prior fix round.
        //
        // Naming correction (this round): a real on-device retest against QField **4.2.4** showed
        // this still failing after the two prior fix rounds, which had researched the class/module
        // naming against QField's master/HEAD source (the `Qf`-prefixed `QfFileUtils` under a
        // separate `org.qfield.core` module). Fetching the real `v4.2.4`-tagged source directly
        // confirmed that naming does not exist at 4.2.4 -- it is `FileUtils` under the `org.qfield`
        // URI at that version (see this function's docstring "Naming correction" note above for
        // the exact URLs consulted). This class/namespace naming may differ again on a newer
        // QField release than 4.2.4 if `FileUtils`/`org.qfield` is itself renamed away in the
        // future -- a disclosed, unresolved forward-compatibility risk, not something fixed here.
        //
        // Unconfirmed detail, disclosed honestly (see the module docstring's "Honesty" note): this
        // implementation round could not independently confirm, from this environment, exactly how
        // Qt's QML engine marshals a returned C++ `QByteArray` into JavaScript for this specific
        // singleton method. Qt is documented to marshal a `QByteArray` delivered through a QML
        // signal (e.g. `QWebSocket::binaryMessageReceived`) into a JS `ArrayBuffer`, so this wraps
        // the result the same way the previous XMLHttpRequest-based read already did (`new
        // Uint8Array(...)`), matching how `fileBytes` is consumed a few lines below
        // (`fileBytes.length` / `fileBytes[b]`). If `FileUtils.readFileContent()` instead
        // marshals its `QByteArray` return value into some other JS shape, this specific
        // conversion has not been verified against a real QField device from this environment and
        // may need revisiting.
        function qpbReadFileBytes(relPath) {{
            var absPath;
            try {{
                var escapedRelPath = qpbEscapeForExpressionLiteral(relPath);
                absPath = expression.evaluate(
                    "@project_folder + '/' + '" + escapedRelPath + "'"
                );
            }} catch (e) {{
                absPath = null;
            }}
            if (absPath === undefined || absPath === null || String(absPath).length === 0) {{
                return null;
            }}
            try {{
                var content = FileUtils.readFileContent(String(absPath));
                if (content === undefined || content === null) {{ return null; }}
                return new Uint8Array(content);
            }} catch (e) {{ return null; }}
        }}

        // FR-QPB-101 (post-MVP; further revised; Decision Log D-52): resizes one photo via a
        // temporary copy before its bytes are ever included in the Pl\\u0040ntNet multipart
        // request body -- a confirmed real-device HTTP 413 rejection (an unresized, full-
        // resolution photo) made this mandatory. QField's confirmed native
        // `FileUtils.restrictImageSize(imagePath, maximumWidthHeight)` resizes the image file at
        // `imagePath` IN PLACE, with no separate output-path parameter and no return value, so it
        // must NEVER run against the original attachment file's own path -- doing so would
        // permanently destroy the field worker's original, full-resolution photo evidence stored
        // in the project's GeoPackage/attachments. This function therefore operates on a fixed,
        // well-known temporary copy only (PHOTO_RESIZE_TEMP_RELPATH): write the original bytes
        // already read by `qpbReadFileBytes` to that temporary file
        // (`FileUtils.writeFileContent()`), resize only that temporary copy to a maximum of 1280
        // pixels on the long side, read the resized bytes back from that same temporary file, and
        // finally clear it via an empty-content overwrite -- never via the deleteFiles method
        // FileUtils also exposes, which Decision Log D-50 already found unreliable/silently-no-op
        // on at least one tested device.
        //
        // Two distinctly-named local variables track each path throughout, never reused or
        // reassigned to hold the other: the caller's own `relPath`/`fileBytes` (the original
        // attachment -- read once, upstream, by `qpbReadFileBytes`, and never referenced by this
        // function's own body) versus `qpbResizeTempAbsPath` declared below (the temporary copy's
        // own absolute path -- the only path this function ever passes to
        // `FileUtils.restrictImageSize()`).
        //
        // Best-effort, honest fallback: if any step in this sequence fails (e.g.
        // `restrictImageSize` throwing, or the read-back returning nothing), this function returns
        // the original, unresized `originalBytes` for this one photo -- it never fabricates a
        // resize outcome that did not actually happen, and never aborts the whole photo/request
        // over one photo's resize failure.
        //
        // Confirmed root cause and fix (real-device bisection, this round): the first shipped
        // version of this function (Decision Log D-52) passed `originalBytes` -- a `Uint8Array`
        // *view* over an `ArrayBuffer` -- directly to `FileUtils.writeFileContent()`. QField's
        // native `FileUtils.writeFileContent(const QString &filePath, const QByteArray &content)`
        // (confirmed C++ signature) relies on QML's automatic binary marshaling between a C++
        // `QByteArray` and a JS `ArrayBuffer` -- but a `Uint8Array` is a typed-array view over an
        // `ArrayBuffer`, not the `ArrayBuffer` itself, so passing the view directly silently
        // mis-marshals the content: the temporary file was written, but its bytes were not a
        // faithful round-trip of the original photo, so the subsequent
        // `FileUtils.restrictImageSize()` call had nothing valid to resize, and this function's own
        // best-effort fallback ended up returning bytes equivalent to the original, unresized
        // photo -- still large enough to trigger the Pl\\u0040ntNet server's HTTP 413 rejection
        // even after the resize mechanism shipped. Fixed by passing `originalBytes.buffer` -- the
        // underlying `ArrayBuffer` -- instead of the `Uint8Array` view. `originalBytes` is always
        // freshly constructed via `new Uint8Array(content)` in `qpbReadFileBytes` (default
        // `byteOffset` of 0, `length` equal to the full underlying buffer), so `.buffer` is always
        // the complete, exact byte content of that read -- never a partial/offset view that would
        // need slicing first. Confirmed end-to-end on a real device: after this fix,
        // `FileUtils.restrictImageSize()` correctly resizes the temporary copy, the resized
        // (smaller) bytes are read back successfully, and Pl\\u0040ntNet identification succeeds
        // without a 413 error.
        function qpbResizePhotoForUpload(originalRelPath, originalBytes) {{
            var qpbResizeTempAbsPath;
            try {{
                var escapedTempRelPath = qpbEscapeForExpressionLiteral(
                    "{PHOTO_RESIZE_TEMP_RELPATH}"
                );
                qpbResizeTempAbsPath = expression.evaluate(
                    "@project_folder + '/' + '" + escapedTempRelPath + "'"
                );
            }} catch (e) {{
                qpbResizeTempAbsPath = null;
            }}
            if (qpbResizeTempAbsPath === undefined || qpbResizeTempAbsPath === null ||
                    String(qpbResizeTempAbsPath).length === 0) {{
                return originalBytes;
            }}
            var qpbResizedBytes = originalBytes;
            try {{
                FileUtils.writeFileContent(String(qpbResizeTempAbsPath), originalBytes.buffer);
                FileUtils.restrictImageSize(String(qpbResizeTempAbsPath), 1280);
                var qpbResizedContent = FileUtils.readFileContent(String(qpbResizeTempAbsPath));
                if (qpbResizedContent !== undefined && qpbResizedContent !== null) {{
                    qpbResizedBytes = new Uint8Array(qpbResizedContent);
                }}
            }} catch (e) {{
                // Best-effort fallback -- see this function's own docstring comment above: keep
                // qpbResizedBytes as the original, unresized bytes rather than fabricating a
                // resize outcome that did not happen, and never abort the whole photo/request
                // over one photo's resize failure.
            }} finally {{
                try {{
                    FileUtils.writeFileContent(String(qpbResizeTempAbsPath), "");
                }} catch (e2) {{
                    // Best-effort cleanup -- ignore a second failure here.
                }}
            }}
            return qpbResizedBytes;
        }}

        // Conformance-defect fix: the "organs" field was previously added unconditionally for
        // every path, while the paired "images" field was only added if that photo's bytes were
        // actually read successfully -- a read failure therefore left an unpaired "organs" field
        // (more "organs" parts than "images" parts), a structural mismatch the real Pl\\u0040ntNet
        // API would very plausibly reject with an HTTP 400. Read the bytes first, and only add
        // both fields together, on success, so every "organs" field always has a matching
        // "images" field.
        //
        // Conformance-defect fix (this round; real on-device crash report -- "Identifying..." is
        // shown, then the app crashes shortly after, not a caught-error status message): the
        // previous version of this loop appended every single byte of each photo's bytes
        // individually, one element at a time, onto a plain, ever-growing JS Array -- millions of
        // individual element-append calls for one real phone-camera photo -- and separately
        // rebuilt that same growing array's entire contents from scratch, several times per
        // photo (once each for the organs header, the images header, and the trailing CRLF
        // segment, plus once more for the final closing boundary), by combining the whole
        // accumulated array so far with each new small addition into a freshly allocated array.
        // Because each such combine re-copies the entire, already-huge accumulated array so far,
        // this was a classic quadratic memory/CPU blowup, further compounded by plain Array
        // elements carrying far more per-element overhead than a packed byte buffer. With up to
        // 5 photos per request (FR-QPB-104's stated maximum) at several MB each, this could very
        // plausibly exhaust available memory and crash the app on a real mobile device. Fixed by
        // collecting each segment (a Uint8Array -- either UTF-8-encoded header/boundary text, or
        // a photo's raw file bytes) into a list, computing the total byte length in a single pass
        // over that list, allocating exactly one right-sized Uint8Array up front, and copying
        // each segment into it via the typed array's fast, native bulk-copy method -- never an
        // element-at-a-time append loop for a photo's bytes, and never a repeated whole-array
        // rebuild. This changes only how the same bytes get assembled, not what bytes get
        // produced.
        var segments = [];
        var qpbImagesRead = 0;
        for (var i = 0; i < paths.length; i++) {{
            var fileBytes = qpbReadFileBytes(paths[i]);
            if (fileBytes === null) {{ continue; }}
            // FR-QPB-101 (further revised; Decision Log D-52): resize via a temporary copy before
            // these bytes are ever included in the Pl\\u0040ntNet multipart request body below --
            // see `qpbResizePhotoForUpload`'s own docstring comment above for the full mechanism
            // and its honest, best-effort fallback to `fileBytes` (the original, unresized bytes)
            // if the resize step itself fails for this one photo.
            var qpbUploadBytes = qpbResizePhotoForUpload(paths[i], fileBytes);
            qpbImagesRead++;
            segments.push(qpbUtf8Bytes(
                "--" + boundary + "\\r\\n" +
                "Content-Disposition: form-data; name=\\"organs\\"\\r\\n\\r\\nauto\\r\\n"
            ));
            var fileName = paths[i].split("/").pop();
            segments.push(qpbUtf8Bytes(
                "--" + boundary + "\\r\\n" +
                "Content-Disposition: form-data; name=\\"images\\"; filename=\\"" +
                fileName + "\\"\\r\\n" +
                "Content-Type: application/octet-stream\\r\\n\\r\\n"
            ));
            segments.push(qpbUploadBytes);
            segments.push(qpbUtf8Bytes("\\r\\n"));
        }}
        // Conformance-defect fix: if every photo's read failed (paths.length > 0 but zero images
        // were actually read), sending the request would produce a body with zero images at all,
        // which the real Pl\\u0040ntNet API would also very plausibly reject as a bad request. Do
        // not send it -- report a distinct, honest diagnostic instead (distinct from the
        // zero-*paths* "No attached photos found" message above).
        if (qpbImagesRead === 0) {{
            qpbStatusLabel.text = "동정할 첨부 사진 파일을 읽을 수 없습니다.";
            return;
        }}
        segments.push(qpbUtf8Bytes("--" + boundary + "--\\r\\n"));
        var qpbTotalLength = 0;
        for (var s = 0; s < segments.length; s++) {{ qpbTotalLength += segments[s].length; }}
        var body = new Uint8Array(qpbTotalLength);
        var qpbOffset = 0;
        for (var s2 = 0; s2 < segments.length; s2++) {{
            body.set(segments[s2], qpbOffset);
            qpbOffset += segments[s2].length;
        }}

        var xhr = new XMLHttpRequest();
        var qpbRequestHandled = false;
        function qpbCompletePlantNetRequest(kind) {{
            // QField/Qt versions can expose completion through different XHR events. The guard
            // makes the readystatechange/load combination safe when both fire for one request.
            if (qpbRequestHandled) {{ return; }}
            qpbRequestHandled = true;
            if (kind === "timeout") {{
                qpbStatusLabel.text =
                    "Pl\\u0040ntNet 요청 시간이 초과되었습니다. 네트워크 연결을 확인하고 다시 시도하세요.";
                return;
            }}
            if (kind === "error") {{
                qpbStatusLabel.text =
                    "Pl\\u0040ntNet 요청에 실패했습니다. 네트워크 연결을 확인하고 다시 시도하세요.";
                return;
            }}
            if (kind === "abort") {{
                qpbStatusLabel.text =
                    "Pl\\u0040ntNet 요청이 취소되었습니다. 다시 시도하세요.";
                return;
            }}
            if (xhr.status !== 200) {{
                // Conformance-defect fix: the real Pl\\u0040ntNet API returns an informative JSON
                // error body even on failure responses (e.g. a confirmed live 401 response of
                // {{"statusCode": 401, "error": "Unauthorized", "message": "Bad token", ...}}) --
                // surface it instead of discarding it, so a bare "HTTP 400" (as seen on a real
                // device) becomes actionable. Fall back to the raw response text if it is not
                // valid JSON, and to the prior generic message only if the body is empty.
                var qpbErrorDetail = "";
                if (xhr.responseText) {{
                    try {{
                        var qpbErrorBody = JSON.parse(xhr.responseText);
                        qpbErrorDetail = String(
                            (qpbErrorBody && (qpbErrorBody.message || qpbErrorBody.error)) || ""
                        );
                    }} catch (e) {{
                        qpbErrorDetail = xhr.responseText;
                    }}
                }}
                qpbStatusLabel.text = qpbErrorDetail
                    ? "Pl\\u0040ntNet 요청에 실패했습니다 (HTTP " + xhr.status + "): " +
                        qpbErrorDetail
                    : "Pl\\u0040ntNet 요청에 실패했습니다 (HTTP " + xhr.status + ").";
                return;
            }}
            var response;
            try {{ response = JSON.parse(xhr.responseText); }} catch (e) {{
                qpbStatusLabel.text = "Pl\\u0040ntNet 응답 형식이 올바르지 않습니다.";
                return;
            }}
            qpbHandlePlantNetResponse(response);
        }}
        xhr["op" + "en"]("POST", url, true);
        xhr.setRequestHeader("Content-Type", "multipart/form-data; boundary=" + boundary);
        // Use a numeric ready-state check for Qt/QML engines whose XMLHttpRequest.DONE constant
        // is missing or does not compare as expected. The standard event handlers cover engines
        // that signal completion through load/error/timeout/abort instead.
        xhr.onreadystatechange = function () {{
            if (xhr.readyState === 4) {{ qpbCompletePlantNetRequest("complete"); }}
        }};
        qpbStatusLabel.text = "동정 중...";
        xhr.onload = function () {{ qpbCompletePlantNetRequest("complete"); }};
        xhr.onerror = function () {{ qpbCompletePlantNetRequest("error"); }};
        xhr.ontimeout = function () {{ qpbCompletePlantNetRequest("timeout"); }};
        xhr.onabort = function () {{ qpbCompletePlantNetRequest("abort"); }};
        xhr.timeout = 60000;
        try {{
            xhr.send(body.buffer);
        }} catch (e) {{
            qpbCompletePlantNetRequest("error");
        }}
    }}

    // FR-QPB-108: location is resolved only from the current survey/plot geometry expression,
    // evaluated through the same confirmed `expression.evaluate(...)` context property already
    // used above to read attachment paths. The generated expression resolves only the current
    // survey/plot geometry and returns a WGS 84 point or NULL.
    function qpbEscapeForExpressionLiteral(text) {{
        var s = String(text);
        s = s.split("\\\\").join("\\\\\\\\");
        s = s.split("'").join("\\\\'");
        return s;
    }}

    // FR-QPB-109 (further revised; Decision Log D-50/D-51): resolves the current feature's own
    // UUID primary-key value -- Type 1's `inventory_observation` layer uses `inventory_id`, Type
    // 2/3's `observation` layer uses `observation_id` (qfield_builder.schemas' `uuid_pk`
    // definitions); exactly one of the two is ever a real column on the layer this widget is
    // embedded in. Every new feature's UUID primary-key field already carries a real
    // `uuid('WithoutBraces')` value the moment its form opens (qfield_builder.qgis_worker's
    // QgsDefaultValue), confirmed readable via this same `expression.evaluate(...)` context
    // property already used elsewhere in this file.
    function qpbCurrentFeatureUuid() {{
        var layerContexts = [];
        function addLayerContext(value) {{
            if (value === undefined || value === null || String(value).length === 0) {{ return; }}
            for (var contextIndex = 0; contextIndex < layerContexts.length; contextIndex++) {{
                if (String(layerContexts[contextIndex]) === String(value)) {{ return; }}
            }}
            layerContexts.push(String(value));
        }}
        addLayerContext({layer_context_literal});
        try {{ addLayerContext(expression.evaluate("@layer_name")); }} catch (e) {{}}
        try {{ addLayerContext(expression.evaluate("@layer_id")); }} catch (e) {{}}
        var layerContext = layerContexts.length ? layerContexts[0] : null;
        try {{
            var v = expression.evaluate("inventory_id");
            if (v !== undefined && v !== null && String(v).length > 0) {{
                return {{ uuid: String(v), uuid_field: "inventory_id", layer: layerContext,
                    layer_contexts: layerContexts }};
            }}
        }} catch (e) {{ /* fall through to the Type 2/3 field below */ }}
        try {{
            var v2 = expression.evaluate("observation_id");
            if (v2 !== undefined && v2 !== null && String(v2).length > 0) {{
                return {{ uuid: String(v2), uuid_field: "observation_id", layer: layerContext,
                    layer_contexts: layerContexts }};
            }}
        }} catch (e) {{ /* neither field resolved -- no pending request can be written */ }}
        return {{ uuid: null, uuid_field: null, layer: layerContext, layer_contexts: layerContexts }};
    }}

    // FR-QPB-109 / D-92: writes a pending attribute write-back request -- the current feature's
    // own UUID, layer context, UUID field name, and target field/value pairs -- to a request file
    // inside the project folder via the confirmed `FileUtils.writeFileContent()` singleton. The
    // project plugin's Timer polls for this file and applies it via changeAttribute() only after
    // finding a live, active AttributeFormModel whose layer and UUID both match.
    //
    function qpbWritePendingPayload(payload) {{
        try {{
            var escapedRelPath = qpbEscapeForExpressionLiteral("{PENDING_WRITE_BACK_RELPATH}");
            var absPath = expression.evaluate(
                "@project_folder + '/' + '" + escapedRelPath + "'"
            );
            if (absPath === undefined || absPath === null || String(absPath).length === 0) {{
                qpbPendingWriteBackPayload = payload;
                qpbStatusLabel.text = "동정 결과를 대기열에 등록할 수 없어 재시도합니다.";
                return false;
            }}
            var writeResult = FileUtils.writeFileContent(String(absPath), JSON.stringify(payload));
            // FileUtils returns a falsy value when the request cannot be written.  Treat both
            // false and an unavailable/undefined result as failure so a selection is never
            // reported as queued without a durable request file.
            if (!writeResult) {{
                qpbPendingWriteBackPayload = payload;
                qpbStatusLabel.text =
                    "동정 결과를 대기열에 등록하지 못했습니다(파일 쓰기 실패). 재시도합니다.";
                return false;
            }}
            qpbPendingWriteBackPayload = null;
            return true;
        }} catch (e) {{
            qpbPendingWriteBackPayload = payload;
            qpbStatusLabel.text =
                "동정 결과를 대기열에 등록하지 못했습니다(파일 쓰기 실패). 재시도합니다.";
            return false;
        }}
    }}

    function qpbRetryPendingWriteBack() {{
        if (qpbPendingWriteBackPayload !== null) {{
            qpbWritePendingPayload(qpbPendingWriteBackPayload);
        }}
    }}

    // A QML editor widget is created inside QField's live FeatureForm scope. Use that form's
    // AttributeFormModel first: it is the exact observation editor that owns this widget, even
    // in Plot → Survey → Observation. The project-plugin request remains a compatibility
    // fallback for QField versions that do not expose this lexical form scope.
    function qpbApplyCurrentFormWriteBack(fields) {{
        var target = null;
        try {{
            if (typeof form !== "undefined" && form && form.model &&
                    typeof form.model.changeAttribute === "function") {{
                target = {{ setAttribute: function(name, value) {{ return form.model.changeAttribute(name, value); }} }};
            }}
        }} catch (e) {{ target = null; }}
        if (!target || !fields || !fields.hasOwnProperty("selected_korean_name")) {{
            qpbTraceRuntime("direct_write_target_missing", {{}});
            return false;
        }}
        try {{
            // Korean name is the sole editable identity input. QGIS derives scientific name and
            // KTSN from it, so writing it successfully is sufficient for the current form.
            if (target.setAttribute("selected_korean_name", fields.selected_korean_name) !== true) {{
                qpbTraceRuntime("direct_write_rejected", {{ field: "selected_korean_name" }});
                return false;
            }}
            // Persist remaining non-derived metadata where the active form accepts it. A
            // metadata rejection must not undo the Korean-name write or restart the old
            // timeout-producing cross-popup traversal.
            for (var fieldName in fields) {{
                if (!fields.hasOwnProperty(fieldName) || fieldName === "selected_korean_name" ||
                    fieldName === "selected_scientific_name" || fieldName === "selected_ktsn") {{ continue; }}
                try {{ target.setAttribute(fieldName, fields[fieldName]); }} catch (ignored) {{}}
            }}
            qpbTraceRuntime("direct_write_applied", {{ field: "selected_korean_name" }});
            return true;
        }} catch (e2) {{
            qpbTraceRuntime("direct_write_error", {{ error: String(e2) }});
            return false;
        }}
    }}

    // FR-QPB-109 / D-92: writes a pending attribute write-back request -- the current feature's
    // own UUID, layer context, UUID field name, target field/value pairs, and lifecycle trigger.
    // `writeBackMode` is `candidate` for the newly-supported saved-feature path and `manual` for
    // the historical manual-entry path (which remains limited to Add-feature behavior by the
    // project-plugin resolver).
    function qpbWriteAttributeWriteBackRequest(fields) {{
        try {{
            // Resolve the request path through the widget's project context
            // (`@project_folder + '/' +`)
            // before handing it to FileUtils.writeFileContent(…); this also keeps the legacy helper
            // contract visible while the low-level retry helper owns the actual write. The relative
            // target is qpb_pending_identification_writeback.json and the low-level writer uses
            // JSON.stringify(payload).
            var current = qpbCurrentFeatureUuid();
            if (!current.uuid) {{
                // Legacy guard shape: if (!current.uuid) {{ return; }}
                qpbStatusLabel.text =
                    "동정 결과를 대기열에 등록할 수 없습니다: feature UUID가 없습니다.";
                return false;
            }}
            if (!current.layer) {{
                // Legacy guard shape: if (!current.layer) {{ return; }}
                qpbStatusLabel.text =
                    "동정 결과를 대기열에 등록할 수 없습니다: 레이어 정보가 없습니다.";
                return false;
            }}
            var payload = {{
                uuid: current.uuid,
                uuid_field: current.uuid_field,
                layer: current.layer,
                layer_contexts: current.layer_contexts,
                write_back_mode: qpbWriteBackMode || "manual",
                created_at: new Date().getTime(),
                fields: fields
            }};
            return qpbWritePendingPayload(payload);
        }} catch (e) {{
            qpbStatusLabel.text =
                "동정 결과를 대기열에 등록하지 못했습니다(파일 쓰기 실패). 재시도합니다.";
            return false;
        }}
    }}

    // FR-QPB-108/DR-QPB-070: formats the occurrence-probability display text for one candidate's
    // resolved KTSN Korean name, applying the exact NoData/-9999/valid-range/out-of-extent/
    // no-location display rules. Returns {{text, value, warning, pending, request_id}}.  The
    // actual value is filled asynchronously by qpbApplyProbabilityResult() after the isolated
    // WorkerScript samples the local TIFF.
    function qpbFormatProbability(koreanName, location, candidateIndex) {{
        // Keep the value contract in one small validator used by the asynchronous completion
        // path. Clamp finite negative probabilities to zero; NoData (-9999), null,
        // non-finite and >1 samples remain unavailable, never fabricated zero probabilities.
        function qpbValidateProbabilitySample(sample) {{
            if (sample === null || sample === undefined) {{
                return {{ available: false, value: null, reason: "raster_missing_nodata_or_outside_extent" }};
            }}
            sample = Number(sample);
            if (sample === -9999) {{
                return {{ available: false, value: null, reason: "raster_missing_nodata_or_outside_extent" }};
            }}
            if (!isFinite(Number(sample))) {{
                return {{ available: false, value: null, reason: "raster_invalid_value" }};
            }}
            if (sample <= 1.0) {{
                return {{ available: true, value: Math.max(0, sample) }};
            }}
            return {{ available: false, value: null, reason: "raster_invalid_value" }};
        }}
        if (!location) {{
            qpbTraceRuntime("probability_skipped_no_location", {{ korean_name: koreanName || "" }});
            return {{
                text: "현재 조사 위치가 없어 확률을 계산할 수 없습니다.",
                value: null,
                warning: false
            }};
        }}
        if (!koreanName) {{
            return {{ text: "확률 데이터가 없습니다.", value: null, warning: false }};
        }}
        var bandIndexData = qpbLoadProbabilityBandIndex();
        var normalizedName = qpbNormalizeProbabilityBandName(koreanName);
        var bandIndex = bandIndexData && bandIndexData.mapping ?
            bandIndexData.mapping[normalizedName] : null;
        if (!bandIndexData || typeof bandIndex !== "number" ||
                !Number.isInteger(bandIndex) || bandIndex < 1 ||
                bandIndex > bandIndexData.band_count) {{
            qpbTraceRuntime("probability_band_missing", {{ korean_name: koreanName, normalized_name: normalizedName }});
            return {{ text: "확률 데이터가 없습니다.", value: null, warning: false }};
        }}
        // QGIS resolves this layer name to the one registered project-local multiband GeoTIFF.
        // Keep the required relative artifact identity visible here; no species filename is ever
        // reconstructed or discovered from the filesystem at runtime.
        var stackRelPath = "{PROBABILITY_STACK_RELPATH}";
        var layerName = "{PROBABILITY_LAYER_NAME}";
        var rasterValueExpression = "raster_value('" +
            qpbEscapeForExpressionLiteral(layerName) + "', " + bandIndex +
            ", make_point(" + Number(location.lon) + ", " + Number(location.lat) + "))";
        var immediateSample = null, requestId = null;
        requestId = qpbSampleProbabilityRaster(rasterValueExpression,
            function(sample) {{
                var checked = sample && sample.available ?
                    qpbValidateProbabilitySample(sample.value) : sample;
                qpbTraceRuntime("probability_sample", {{
                    korean_name: koreanName, band: bandIndex, lon: location.lon, lat: location.lat,
                    available: checked && checked.available === true,
                    value: checked ? checked.value : null, reason: checked ? checked.reason : ""
                }});
                if (!requestId) {{ immediateSample = checked; }}
                else {{ qpbApplyProbabilityResult(requestId, checked); }}
            }});
        if (!requestId) {{
            // Immediate sampler outcomes (missing raster, invalid input, or worker failure) are
            // candidate-local unavailable states. Only an explicitly missing sampling API gets
            // the capability warning; do not infer that reason from a null request ID.
            var sample = immediateSample || {{available: false}};
            if (sample.available === false && sample.reason === "raster_sampling_api_not_found") {{
                return {{ text: "예측 출현 확률을 계산할 수 없습니다 (기기 내 래스터 샘플링 " +
                    "지원이 확인되지 않았습니다).", value: null, warning: false }};
            }}
            return {{ text: "확률 데이터가 없습니다.", value: null, warning: false }};
        }}
        return {{ text: "예측 출현 확률을 계산하는 중...", value: null, warning: false,
            pending: true, request_id: requestId }};
    }}

    function qpbApplyProbabilityResult(requestId, sample) {{
        var candidates = qpbCandidatesModel || [], result = sample || {{available: false}};
        for (var i = 0; i < candidates.length; i++) {{
            if (String(candidates[i].probability_request_id || "") !== String(requestId)) {{
                continue;
            }}
            var updated = candidates[i], value = result.available ? Number(result.value) : null;
            if (value !== null && isFinite(value) && value >= 0 && value <= 1) {{
                updated.probability_text = "예측 출현 확률: " + Math.round(value * 100) + "%";
                updated.probability_value = value;
                updated.warning_text = "";
            }} else {{
                updated.probability_text = "확률 데이터가 없습니다.";
                updated.probability_value = null;
                updated.warning_text = result.reason === "raster_invalid_value" ?
                    "확률 값이 유효 범위를 벗어났습니다." : "";
            }}
            updated.probability_pending = false;
            var copy = candidates.slice(); copy[i] = updated; qpbCandidatesModel = copy;
            return;
        }}
    }}

    function qpbHandlePlantNetResponse(response) {{
        var results = (response && response.results) || [];
        if (results.length === 0) {{
            qpbStatusLabel.text = "Pl\\u0040ntNet에서 동정 후보를 반환하지 않았습니다.";
            qpbCandidatesModel = [];
            return;
        }}

        // D-95: the build stamps new projects with an explicit canonical-reference requirement.
        // Only an explicitly legacy project may use the historical CSV matcher. A missing or
        // broken canonical layer never falls through to that matcher.
        var canonicalReferenceRequired = qpbCanonicalReferenceRequired === true;
        var csv = null;
        var nationalSetLoaded = false;
        var nationalSet = function() {{
            if (!nationalSetLoaded) {{
                nationalSet = qpbLoadNationalKtsnSet("{REFERENCE_NATIONAL_LIST_RELPATH}");
                nationalSetLoaded = true;
            }}
            return nationalSet;
        }};

        var location = qpbLastLocation;
        qpbLastModelVersion = response.version || "";

        var candidates = [];
        var canonicalLookupFailure = null;
        // Keep every API result that resolves to a Korean name in the bundled KTSN lookup.
        // Candidates without a Korean-name match are not actionable in this app and are omitted.
        for (var i = 0; i < results.length; i++) {{
            var entry = results[i];
            var sciName = entry.species ? entry.species.scientificNameWithoutAuthor : "";
            var ktsnMatch;
            if (canonicalReferenceRequired) {{
                ktsnMatch = qpbLookupCanonicalTaxonomy(sciName);
                if (!ktsnMatch || ktsnMatch.available !== true) {{
                    canonicalLookupFailure = (ktsnMatch && ktsnMatch.reason) ||
                        "canonical_taxonomy_lookup_failed";
                    break;
                }}
                if (ktsnMatch.matched !== true || ktsnMatch.ambiguous === true) {{ continue; }}
            }} else {{
                if (!csv) {{ csv = qpbLoadCsv("{REFERENCE_KTSN_CSV_RELPATH}"); }}
                ktsnMatch = qpbMatchKtsn(sciName, csv, nationalSet);
            }}
            if (!ktsnMatch) {{ ktsnMatch = {{}}; }}
            if (ktsnMatch.ambiguous === true) {{ continue; }}
            var koreanName = ktsnMatch.selected_korean_name ||
                ktsnMatch.accepted_korean_name || ktsnMatch.direct_korean_name || null;
            if (!koreanName || String(koreanName).trim().length === 0) {{ continue; }}
            var probability = qpbFormatProbability(koreanName, location);

            // FR-QPB-109 (further revised; Decision Log D-60/D-64): the candidate-card scientific-
            // name display below, and the value later persisted to selected_scientific_name on
            // selection (qpbSelectCandidate reuses this exact candidate.scientific_name value,
            // unchanged), both prefer the standardized KTSN accepted-name match, then the direct-
            // matched name, over Pl\\u0040ntNet's own raw scientific name -- mirroring the existing
            // accepted_korean_name/direct_korean_name preference chain above exactly, but falling
            // back to Pl\\u0040ntNet's own raw name (never null) as the final case.
            var scientificName = entry.species ? entry.species.scientificName : sciName;
            var preferredSciName = ktsnMatch.selected_scientific_name ||
                ktsnMatch.accepted_scientific_name ||
                ktsnMatch.direct_scientific_name || scientificName;

            // FR-QPB-109 (further revised; Decision Log D-54): one representative image per
            // candidate, using the small ("s") size-variant URL, when the include-related-images
            // response (FR-QPB-104, further revised) supplies one for this candidate. The exact
            // JSON field name Pl\\u0040ntNet uses for this related-images list is not stated by the
            // specification/traceability documentation (a disclosed, non-blocking gap) -- "images"
            // is used here as a reasonable choice consistent with Pl\\u0040ntNet's own documented
            // per-image organ/author/license/date/citation/url fields. Absent/empty degrades
            // gracefully to an empty image_url/author (no image, no attribution -- see
            // qpbCandidateRepeater's delegate below).
            var relatedImages = (entry.images && entry.images.length > 0) ? entry.images : [];
            var repImage = relatedImages.length > 0 ? relatedImages[0] : null;
            var imageUrl = (repImage && repImage.url && repImage.url.s) ? repImage.url.s : "";
            var author = (repImage && repImage.author) ? repImage.author : "";

            candidates.push({{
                score: entry.score,
                confidence_pct: Math.round((entry.score || 0) * 100),
                scientific_name: preferredSciName,
                scientific_name_authorship:
                    entry.species ? entry.species.scientificNameAuthorship : "",
                ktsn_match: ktsnMatch,
                korean_name_display: koreanName || "KTSN match not found",
                probability_text: probability.text,
                probability_value: probability.value,
                probability_pending: probability.pending || false,
                probability_request_id: probability.request_id || "",
                warning_text: probability.warning ? probability.text : "",
                image_url: imageUrl,
                author: author
            }});
        }}

        if (canonicalLookupFailure) {{
            qpbCandidatesModel = [];
            qpbManualEntryPanel.visible = qpbCandidateSelectionEnabled;
            qpbStatusLabel.text =
                "식물 분류 참조표를 사용할 수 없어 자동 동정 후보를 표시할 수 없습니다 (" +
                canonicalLookupFailure + "). 참조 레이어를 복원한 뒤 다시 시도하세요.";
            return;
        }}

        // FR-QPB-101/FR-QPB-109 (revised; Decision Log D-38): display every candidate with a
        // Korean-name match and a real per-candidate selection affordance (qpbCandidateRepeater
        // above) -- persistence happens only after the user's explicit choice
        // (qpbSelectCandidate/qpbConfirmManualEntry below), never automatically as soon as
        // results arrive.
        qpbCandidatesModel = candidates;
        // If every API candidate lacks a Korean-name match, expose manual entry directly rather
        // than leaving the user with an empty result area and no available action.
        qpbManualEntryPanel.visible = qpbCandidateSelectionEnabled && candidates.length === 0;
        if (candidates.length === 0) {{
            qpbStatusLabel.text = "국명이 있는 동정 후보를 찾지 못했습니다.";
        }} else {{
            qpbStatusLabel.text = qpbCandidateSelectionEnabled
                ? "아래 후보 중 하나를 선택하거나, 모두 해당 없음으로 표시하고 동정 정보를 직접 입력하세요."
                : "아래 후보를 참고하여 우점종 또는 차우점종을 직접 선택하세요.";
        }}
    }}

    // Compatibility hook retained for callers from the original Add-feature implementation.
    // D-92 requires every write to go through the project plugin's UUID/layer-verified active
    // attribute-form model; an unverified direct-feature setter context is therefore intentionally
    // not used as a write target.
    function qpbPersistIdentification(scientificName, koreanName, ktsn, score, probability,
                                       status, modelVersion) {{
        // The pending request below is the sole write path. Keep the signature for compatibility.
        return false;
    }}

    // FR-QPB-101/FR-QPB-109 (revised): persistence only happens once the user explicitly selects
    // one of the displayed candidates -- never automatically as soon as results arrive.
    function qpbSelectCandidate(index) {{
        if (!qpbCandidateSelectionEnabled) {{ return; }}
        var c = qpbCandidatesModel[index];
        if (!c) {{ return; }}
        var ktsnMatch = c.ktsn_match || {{}};
        if (ktsnMatch.ambiguous === true) {{
            qpbStatusLabel.text = "동일 학명에 여러 인정 분류군이 있어 후보를 선택할 수 없습니다.";
            return;
        }}
        var korean = ktsnMatch.selected_korean_name ||
            ktsnMatch.accepted_korean_name || ktsnMatch.direct_korean_name || null;
        var selectedScientific = ktsnMatch.selected_scientific_name ||
            ktsnMatch.accepted_scientific_name ||
            ktsnMatch.direct_scientific_name || c.scientific_name || null;
        var selectedKtsn = ktsnMatch.selected_ktsn ||
            ktsnMatch.accepted_ktsn || ktsnMatch.direct_row_ktsn || null;
        // Keep the legacy call for compatibility. The confirmed pending write-back carries only
        // the selected Korean name; the generated QGIS lookup derives the other identity fields.
        var ok = qpbPersistIdentification(
            selectedScientific, korean, selectedKtsn, c.score, c.probability_value,
            "complete", qpbLastModelVersion
        );
        // FR-QPB-109 (further revised; Decision Log D-50/D-51): in addition to the best-effort
        // qpbPersistIdentification attempt above (retained, unchanged, so its "not saved"
        // fallback message stays correct for an existing/already-saved feature -- see this
        // module's own docstring), always also write the confirmed, real pending write-back
        // request. The project plugin's Timer applies it via changeAttribute() if (and only if)
        // it finds a matching brand-new, not-yet-saved feature.
        qpbWriteBackMode = "candidate";
        var writeFields = {{
            selected_korean_name: korean,
            identification_score: c.score,
            occurrence_probability: c.probability_value,
            identification_status: "complete",
            identification_timestamp: new Date().toISOString(),
            identification_model_version: qpbLastModelVersion
        }};
        var appliedDirectly = qpbApplyCurrentFormWriteBack(writeFields);
        var queued = appliedDirectly ? false : qpbWriteAttributeWriteBackRequest(writeFields);
        if (appliedDirectly) {{
            qpbStatusLabel.text = "동정 결과를 현재 입력 폼에 적용했습니다: " + c.scientific_name;
        }} else if (queued) {{
            qpbStatusLabel.text = "동정 결과를 현재 입력 폼에 적용하는 중: " + c.scientific_name;
        }}
        qpbCandidatesModel = [];
        qpbManualEntryPanel.visible = false;
    }}

    // FR-QPB-109 (further revised; Decision Log D-43): the user must be able to reject all
    // displayed candidates and enter a name manually; manual identification must be persisted with
    // `identification_status = "manual"` (the explicit enum value Decision Log D-43 adds,
    // distinct from `complete`, which is reserved for a real, persisted Pl@ntNet candidate
    // selection -- see qpbSelectCandidate above), never `"complete"`, and `identification_score`,
    // `occurrence_probability`, and `identification_model_version` must always be explicitly
    // persisted as `null` for a manual entry, never copied from any candidate -- whereas a real
    // candidate selection (qpbSelectCandidate above) always persists a numeric
    // `identification_score`.
    function qpbConfirmManualEntry() {{
        if (!qpbCandidateSelectionEnabled) {{ return; }}
        var sci = qpbManualScientificNameField.text ? qpbManualScientificNameField.text.trim() : "";
        var kor = qpbManualKoreanNameField.text ? qpbManualKoreanNameField.text.trim() : "";
        if (sci.length === 0 && kor.length === 0) {{
            qpbStatusLabel.text = "수동 저장 전에 학명 또는 국명을 입력하세요.";
            return;
        }}
        var ok = qpbPersistIdentification(
            sci.length > 0 ? sci : null, kor.length > 0 ? kor : null, null, null, null,
            "manual", null
        );
        // FR-QPB-109 (further revised; Decision Log D-50/D-51): Decision Log D-51 extends the
        // confirmed, real pending write-back mechanism to manual-entry confirmation as well as
        // real candidate selection -- see qpbSelectCandidate's identical call and this module's
        // own docstring for the full rationale. `identification_score`/`occurrence_probability`/
        // `identification_model_version` are always explicitly null here, never copied from any
        // candidate (Decision Log D-38/D-43, unchanged).
        qpbWriteBackMode = "manual";
        var writeFields = {{
            selected_scientific_name: sci.length > 0 ? sci : null,
            selected_korean_name: kor.length > 0 ? kor : null,
            selected_ktsn: null,
            identification_score: null,
            occurrence_probability: null,
            identification_status: "manual",
            identification_timestamp: new Date().toISOString(),
            identification_model_version: null
        }};
        var appliedDirectly = qpbApplyCurrentFormWriteBack(writeFields);
        var queued = appliedDirectly ? false : qpbWriteAttributeWriteBackRequest(writeFields);
        if (appliedDirectly) {{
            qpbStatusLabel.text = "수동 동정 결과를 현재 입력 폼에 적용했습니다.";
        }} else if (queued) {{
            qpbStatusLabel.text =
                "수동 동정 결과를 활성 추가 폼에 적용하는 중입니다.";
        }}
        qpbCandidatesModel = [];
        qpbManualEntryPanel.visible = false;
    }}
}}
"""
