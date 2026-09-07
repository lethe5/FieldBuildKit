"""PyInstaller entry-point bootstrap for ``qfield_builder.ui.app:main``.

This tiny script exists only because PyInstaller's ``Analysis`` treats whatever script path it is
given as a standalone top-level ``__main__`` module with no package context -- running
``qfield_builder/ui/app.py`` directly as that script therefore breaks its own
``from .wizard import ProjectBuilderWizard`` relative import at startup (confirmed empirically: a
built ``.app`` using that script directly crashes immediately with ``ImportError: attempted
relative import with no known parent package``). Importing ``qfield_builder.ui.app`` as a real,
already-installed package from a separate bootstrap script (an *absolute* import, performed by a
script that is itself not part of the ``qfield_builder`` package) avoids that problem entirely,
without needing any change to ``qfield_builder/ui/app.py`` itself.

This is not macOS-specific -- the same relative-import breakage would occur identically on
Windows/Linux PyInstaller builds, which is why this bootstrap lives in the shared, cross-platform
``packaging/qfield_builder.spec`` rather than in the macOS-only ``packaging/build_macos_app.sh``.

``multiprocessing.freeze_support()`` (below) is equally not macOS-specific, and equally required
here: :mod:`qfield_builder.worker_process` spawns the real GIS worker via
``multiprocessing.get_context("spawn").Process(...)`` (Section 5.3/FR-QPB-010's separate-OS-process
requirement), and CPython's own ``multiprocessing.spawn.get_command_line()`` checks
``getattr(sys, "frozen", False)`` -- not ``sys.platform`` -- to decide whether to re-launch
``sys.executable`` with a ``--multiprocessing-fork`` marker (the frozen-app path) instead of a
bare ``python -c <code>`` (confirmed by reading the installed CPython 3.12 ``multiprocessing``
source directly: ``popen_spawn_posix.Popen._launch`` on POSIX -- macOS included -- calls
``spawn.get_command_line()``, whose frozen branch fires whenever PyInstaller has set
``sys.frozen = True``, regardless of OS). Since this application's own frozen executable *is*
``sys.executable`` in a PyInstaller build, an unintercepted respawn falls straight through this
same ``entry_point.py`` script again, re-running ``main()`` and opening a whole second GUI window
-- exactly the defect a real packaged build exhibited. Per Python's own documented guidance
("Programming guidelines" -> "Frozen executables" in the ``multiprocessing`` docs),
``multiprocessing.freeze_support()`` must be the first statement inside
``if __name__ == "__main__":`` to intercept this before anything else runs.

A second, independent respawn source exists too: POSIX ``multiprocessing`` also transparently
launches its own "resource tracker" helper process (for cleaning up leaked POSIX semaphores) the
first time a ``Queue``/``Lock`` is used, via ``multiprocessing.resource_tracker.ensure_running()``
-- and *that* code path (confirmed by reading CPython's ``resource_tracker.py``) always re-invokes
``spawn.get_executable()`` with a bare ``-c <code>`` command line, with no ``sys.frozen`` check of
its own at all, so plain ``multiprocessing.freeze_support()`` alone would not catch it. This is
exactly the second extra window the stakeholder observed (one from the worker respawn, one from
the resource tracker). PyInstaller ships its own runtime hook for this
(``PyInstaller/hooks/rthooks/pyi_rth_multiprocessing.py``, registered in ``rthooks.dat`` against
the ``multiprocessing`` package and confirmed present in this project's own installed PyInstaller),
which runs automatically, before this script's own code, in *every* frozen build that imports
``multiprocessing`` (as :mod:`qfield_builder.worker_process` does) -- it monkey-patches
``multiprocessing.freeze_support``/``multiprocessing.spawn.freeze_support`` with a superset that
*also* recognizes the resource-tracker's (and forkserver's) own ``-c <code>`` command line and
``exec()``s it directly, in addition to the normal ``--multiprocessing-fork`` case. So the single,
standard, unconditional ``multiprocessing.freeze_support()`` call below transparently covers both
respawn paths in the actual packaged build -- no extra code is needed here to special-case the
resource tracker, and no explicit ``multiprocessing.set_start_method(...)`` call is needed either:
:mod:`qfield_builder.worker_process` already pins its own start method explicitly per call via
``multiprocessing.get_context("spawn")`` rather than relying on the process-wide default, so there
is no ambiguous default-start-method state here for ``set_start_method`` to fix.

Calling ``multiprocessing.freeze_support()`` on a normal (non-respawned, non-frozen) run is an
inert no-op (confirmed by reading CPython's own implementation: it only acts when
``sys.argv`` indicates this process *is* one of the intercepted respawns), so this call is always
unconditionally safe to make here, on every platform, every run.
"""
from __future__ import annotations

import multiprocessing
import sys

from qfield_builder.ui.app import main

if __name__ == "__main__":
    # Must be the very first statement in this block, before anything else -- see the module
    # docstring above for exactly why (both the worker-process respawn and the resource-tracker
    # helper respawn depend on this running before `main()` ever constructs a QApplication).
    multiprocessing.freeze_support()

    sys.exit(main())
