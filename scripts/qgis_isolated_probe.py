#!/usr/bin/env python3
"""The ONE sanctioned entry point for running ad hoc PyQGIS diagnostic code against a real,
locally installed QGIS Desktop installation.

Why this exists
----------------
During this project's development, an ad hoc diagnostic command run directly against a real QGIS
installation — outside any of this codebase's own isolation machinery — deleted a real user's
actual, persistent QGIS profile directory (settings, plugins, styles). This script exists so that
nobody (human or agent) ever again needs to hand-construct a ``QgsApplication`` or invoke a QGIS
application binary directly for a one-off check. It always routes through
``qfield_builder.qgis_bridge.run_ad_hoc_script``, which in turn always calls
``ensure_qgis_application()`` first — the same function every piece of this application's own
PyQGIS-calling code uses, which fails closed (raises ``QgisProfileIsolationError``) if QGIS's
resolved settings directory is not the *specific*, fresh, invocation-owned directory this
invocation itself created — not merely "somewhere under the system temp root".

This is a hard policy for this project: any manual/diagnostic PyQGIS work by a human, or by the
`implementer`/`test-designer` roles, MUST go through this script — never run
``python3 -c "import qgis..."`` directly, never invoke a QGIS/QGIS-LTR application binary
directly, and never construct ``QgsApplication`` yourself outside ``qfield_builder.qgis_bridge``.
The `reviewer` role is a separate case: it must never run this script (or any other executing
command) at all, since it is strictly read-only/non-executing — see `.claude/agents/reviewer.md`.
Any QGIS-related verification a reviewer needs is captured by the orchestrator beforehand and
handed to it as evidence, not reproduced by the reviewer itself.

Scope: what this script isolates, and what it does NOT
--------------------------------------------------------
This script (via ``ensure_qgis_application``'s fail-closed check) isolates exactly one thing:
*where a real QGIS installation resolves its own profile/settings directory to*. It is **not** a
general-purpose OS filesystem sandbox for the diagnostic code you pass it. If your diagnostic
script itself reads, writes, or deletes some unrelated path outside the repository — e.g. it
calls ``os.remove("/some/other/path")`` directly, with nothing to do with QGIS's own profile —
this script does nothing to stop that; QGIS-profile isolation and general filesystem safety are
two different concerns. The rule that diagnostic code must never touch anything outside this
repository (except its own self-created temp directories) still applies in full, independently of
this script, and is not satisfied merely by running your diagnostic through it.

Usage
-----
    python3 scripts/qgis_isolated_probe.py --code path/to/script.py
    python3 scripts/qgis_isolated_probe.py -c "from qgis.core import Qgis; print(Qgis.QGIS_VERSION)"

Either form prints the resolved, isolated QGIS settings directory it actually used (so the
isolation guarantee is auditable from the output, not just asserted), then the diagnostic
script's own stdout/stderr, then exits non-zero on any failure (including a caught
``QgisProfileIsolationError``, an ordinary exception from the diagnostic code, or "no QGIS
installation could be found on this machine at all").
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from qfield_builder import qgis_bridge  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--code", metavar="PATH", help="Path to a Python script to run inside PyQGIS."
    )
    group.add_argument(
        "-c", "--exec", metavar="CODE", help="A short inline Python snippet to run inside PyQGIS."
    )
    parser.add_argument("--timeout", type=float, default=qgis_bridge.DEFAULT_JOB_TIMEOUT_SECONDS)
    args = parser.parse_args()

    if args.code:
        script_path = args.code
        cleanup_dir = None
    else:
        cleanup_dir = tempfile.mkdtemp(prefix="qpb-inline-probe-")
        script_path = str(Path(cleanup_dir) / "inline.py")
        Path(script_path).write_text(args.exec, encoding="utf-8")

    target = qgis_bridge.get_bridge_target()
    if target is None:
        print(
            "No working QGIS/PyQGIS installation could be found on this machine at all — "
            "there is nothing to run this diagnostic against.",
            file=sys.stderr,
        )
        return 2

    print(f"Using QGIS bridge target: kind={target.kind} install_path={target.install_path} "
          f"qgis_version={target.qgis_version}", file=sys.stderr)

    result = qgis_bridge.run_ad_hoc_script(script_path, timeout=args.timeout)
    if cleanup_dir is not None:
        import shutil
        shutil.rmtree(cleanup_dir, ignore_errors=True)

    if result is None:
        print("No working QGIS bridge available.", file=sys.stderr)
        return 2

    print(
        f"Resolved (isolated) QGIS settings directory: {result.get('settings_dir')}",
        file=sys.stderr,
    )
    if result.get("stdout"):
        sys.stdout.write(result["stdout"])
    if result.get("stderr"):
        sys.stderr.write(result["stderr"])

    if not result.get("ok"):
        print(f"FAILED: {result.get('error')}", file=sys.stderr)
        if result.get("traceback"):
            print(result["traceback"], file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
