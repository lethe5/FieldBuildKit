#!/usr/bin/env python3
"""Orchestrator-side safety net: fingerprints the REAL, persistent QGIS profile location(s) on
this machine, so the orchestrator can prove — independent of whether any application code's own
isolation logic is correct — that a subagent round did not touch them.

This is deliberately NOT part of the application (`qfield_builder`) or its test suite: it is a
process-safety tool for the human/orchestrator driving subagents in this repository, following an
incident in which an ad hoc diagnostic command deleted a real QGIS profile directory outside any
of this codebase's own machinery.

Usage
-----
    python3 scripts/qgis_profile_guard.py snapshot /path/to/snapshot.json
    ... run a subagent round ...
    python3 scripts/qgis_profile_guard.py check /path/to/snapshot.json

Fingerprint scope and honest limitations
-----------------------------------------
Every directory, file, and symlink under each real profile root is recorded: directories by
their existence alone; files by size, mtime, AND a SHA-256 content hash (so a content change that
happens to preserve size and mtime is still detected — a plain size/mtime check would miss that);
symlinks by their raw, unfollowed target string (a symlink is never followed/recursed into, so a
change to whatever it points at, outside the profile root, is not itself detected by this tool —
only that the symlink entry itself was added, removed, or repointed). This is close to, but not
identical to, a true byte-for-byte forensic comparison: it does not capture file permissions,
ownership, extended attributes, or changes to a symlink's *target's* own content. `check` exits 0
and prints "UNCHANGED" only if every recorded entry (including the profile root directory itself)
is identical to the snapshot, or exits 1 and prints exactly what changed (added/removed/modified
paths) otherwise. If a profile root did not exist at snapshot time and still does not exist at
check time, that also counts as UNCHANGED — this tool does not require a real profile to exist,
only that this workflow never creates, modifies, or deletes one.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
from pathlib import Path


def real_qgis_profile_roots() -> list[Path]:
    home = Path.home()
    system = platform.system()
    if system == "Darwin":
        return [home / "Library" / "Application Support" / "QGIS"]
    if system == "Windows":
        roots = []
        for var in ("APPDATA", "LOCALAPPDATA"):
            value = os.environ.get(var)
            if value:
                roots.append(Path(value) / "QGIS")
        return roots
    return [home / ".local" / "share" / "QGIS", home / ".qgis3", home / ".qgis2"]


def _hash_file(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def _entry_fingerprint(path: Path) -> dict:
    """One entry's fingerprint: symlinks are checked (and recorded by raw target) *before*
    `is_dir()`/`is_file()`, since those two follow symlinks and would otherwise misclassify a
    symlink as whatever it currently points at."""
    try:
        if path.is_symlink():
            try:
                target = os.readlink(path)
            except OSError:
                target = None
            return {"type": "symlink", "target": target}
        if path.is_dir():
            return {"type": "dir"}
        if path.is_file():
            st = path.stat()
            return {
                "type": "file",
                "size": st.st_size,
                "mtime": st.st_mtime,
                "sha256": _hash_file(path),
            }
        return {"type": "other"}
    except OSError:
        return {"type": "error"}


def fingerprint(root: Path) -> dict:
    if not root.exists() and not root.is_symlink():
        return {"exists": False}
    # Keyed by string path, including the root directory's own entry (so e.g. the root itself
    # being replaced by a symlink is also detected, not just changes to its contents).
    entries = {str(root): _entry_fingerprint(root)}
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirpath_path = Path(dirpath)
        for name in dirnames:
            p = dirpath_path / name
            entries[str(p)] = _entry_fingerprint(p)
        for name in filenames:
            p = dirpath_path / name
            entries[str(p)] = _entry_fingerprint(p)
    return {"exists": True, "entries": entries}


def do_snapshot(out_path: str) -> int:
    snapshot = {str(root): fingerprint(root) for root in real_qgis_profile_roots()}
    Path(out_path).write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    for root_str, fp in snapshot.items():
        n = len(fp.get("entries", {})) if fp.get("exists") else 0
        print(f"snapshot: {root_str} exists={fp.get('exists')} entries={n}")
    return 0


def do_check(snapshot_path: str) -> int:
    before = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
    after = {str(root): fingerprint(root) for root in real_qgis_profile_roots()}

    changed = False
    for root_str in set(before) | set(after):
        b = before.get(root_str, {"exists": False})
        a = after.get(root_str, {"exists": False})
        if b.get("exists") != a.get("exists"):
            changed = True
            print(f"CHANGED (existence): {root_str}: before exists={b.get('exists')} "
                  f"after exists={a.get('exists')}")
            continue
        if not a.get("exists"):
            continue
        b_entries = b.get("entries", {})
        a_entries = a.get("entries", {})
        added = set(a_entries) - set(b_entries)
        removed = set(b_entries) - set(a_entries)
        modified = {
            p for p in set(a_entries) & set(b_entries)
            if a_entries[p] != b_entries[p]
        }
        if added or removed or modified:
            changed = True
            print(f"CHANGED: {root_str}")
            for p in sorted(added):
                print(f"  + added:    {p} ({a_entries[p].get('type')})")
            for p in sorted(removed):
                print(f"  - removed:  {p} ({b_entries[p].get('type')})")
            for p in sorted(modified):
                print(f"  * modified: {p}: before={b_entries[p]} after={a_entries[p]}")

    if changed:
        print("RESULT: CHANGED — the real QGIS profile was touched. Investigate before proceeding.")
        return 1
    print("RESULT: UNCHANGED — the real QGIS profile was not touched.")
    return 0


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[1] not in ("snapshot", "check"):
        print(__doc__)
        return 2
    command, path = sys.argv[1], sys.argv[2]
    if command == "snapshot":
        return do_snapshot(path)
    return do_check(path)


if __name__ == "__main__":
    raise SystemExit(main())
