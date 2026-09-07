"""Keep standard QtGui collection, excluding unused PDF and virtual-keyboard plugins."""

from pathlib import Path

from PyInstaller.utils.hooks.qt import add_qt6_dependencies

hiddenimports, binaries, datas = add_qt6_dependencies(__file__)
# Filter before binary dependency analysis: qpdf pulls QtPdf, while the virtual keyboard
# pulls QtQuick/Qml. Keep native input methods, image formats, SVG and platform plugins.
binaries = [
    entry for entry in binaries
    if Path(entry[0]).stem.lower().removeprefix("lib") not in {"qpdf", "qtvirtualkeyboardplugin"}
]
