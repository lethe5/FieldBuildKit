# Canonical release source

`tables/Rpt_2026-08-29_List.xlsx` is the D-95 bundled candidate used by the release packaging
path. `canonical_source_manifest.json` pins its filename, byte size, and SHA-256 identity.

The release script reads this workbook only to derive validated application assets and to expose
the read-only candidate in the packaged application. It never copies the workbook into a
generated QField project. Probability rasters are supplied separately with
`QPB_REFERENCE_RASTER_DIR` because they are large runtime/reference data, not repository source.

If the approved workbook is replaced, update the workbook and manifest together after the source
has been explicitly approved. A release build fails closed when either the workbook or its pinned
identity is missing or mismatched.
