from __future__ import annotations
from pathlib import Path
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabBar, QStackedWidget, QTextEdit, QFileIconProvider
from PySide6.QtCore import Qt, QFileInfo
from PySide6.QtGui import QIcon

class TabbedEditor(QWidget):
    """Simple tabbed text editor container.

    - Reuses a QTextEdit per tab.
    - Avoids duplicate tabs for same path; focuses existing tab instead.
    - Provides open_file(path) API.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tab_bar = QTabBar(self)
        self._tab_bar.setMovable(True)
        self._tab_bar.setTabsClosable(True)
        self._tab_bar.setDocumentMode(True)
        self._tab_bar.setElideMode(Qt.ElideRight)
        self._tab_bar.setExpanding(False)  # compact tabs
        self._tab_bar.tabCloseRequested.connect(self._close_index)
        self._tab_bar.currentChanged.connect(self._on_tab_changed)
        self._tab_bar.tabMoved.connect(self._on_tab_moved)

        self._stack = QStackedWidget(self)
        layout.addWidget(self._tab_bar)
        layout.addWidget(self._stack, 1)

        self._path_to_index = {}  # type: dict[str, int]
        self._icon_provider = QFileIconProvider()
        self._editors = []  # list aligned to tab order

        self._apply_style()

    def _apply_style(self):
        self._tab_bar.setStyleSheet(
            "QTabBar { background:#1f2123; }"
            "QTabBar::tab { background:#2a2c2f; color:#cfd2d6; padding:2px 8px; margin-right:2px; border:1px solid #3a3d41; border-bottom:0; border-top-left-radius:3px; border-top-right-radius:3px; min-height:20px; min-width:70px; }"
            "QTabBar::tab:selected { background:#34373a; color:#ffffff; }"
            "QTabBar::tab:hover { background:#323539; }"
            "QTabBar::close-button { subcontrol-position: right; width:14px; height:14px; margin-left:6px; }"
            "QTabBar::close-button:hover { background:#45484c; border-radius:2px; }"
        )
        self._stack.setStyleSheet("QTextEdit { background:#1f2123; color:#e3e5e8; border:none; padding:6px; }")

    # --- public API ---
    def open_file(self, path: str):
        norm = str(Path(path).resolve())
        if norm in self._path_to_index:
            self._tab_bar.setCurrentIndex(self._path_to_index[norm])
            return
        try:
            text = Path(norm).read_text(encoding='utf-8', errors='replace')
        except Exception as e:
            text = f"<Unable to open file>\n{e}"
        editor = QTextEdit(self._stack)
        editor.setPlainText(text)
        editor.document().setModified(False)
        self._stack.addWidget(editor)
        self._editors.append(editor)
        icon = self._icon_for_file(norm)
        tab_index = self._tab_bar.addTab(icon, Path(norm).name)
        self._path_to_index[norm] = tab_index
        self._tab_bar.setTabToolTip(tab_index, norm)
        self._tab_bar.setCurrentIndex(tab_index)
        self._stack.setCurrentWidget(editor)

    def current_editor(self) -> QTextEdit | None:
        w = self._stack.currentWidget()
        return w if isinstance(w, QTextEdit) else None

    def current_path(self) -> str | None:
        """Return absolute path of the currently active tab (if any)."""
        idx = self._tab_bar.currentIndex()
        if idx < 0:
            return None
        return self._tab_bar.tabToolTip(idx) or None

    # --- internal slots ---
    def _close_index(self, index: int):
        if 0 <= index < len(self._editors):
            w = self._editors.pop(index)
            if w is not None:
                self._stack.removeWidget(w)
                w.deleteLater()
        self._tab_bar.removeTab(index)
        self._rebuild_mapping()
        if self._tab_bar.count() == 0:
            return
        self._set_current_editor_by_tab()

    def _on_tab_changed(self, index: int):
        if index < 0:
            return
        self._set_current_editor_by_tab()

    def _on_tab_moved(self, from_index: int, to_index: int):
        if from_index == to_index:
            return
        if 0 <= from_index < len(self._editors):
            editor = self._editors.pop(from_index)
            # adjust target index if after removal index shifts
            if from_index < to_index:
                to_index -= 1
            self._editors.insert(to_index, editor)
        self._rebuild_mapping()
        self._set_current_editor_by_tab()

    # --- mapping maintenance ----------------------------------------------
    def _rebuild_mapping(self):
        self._path_to_index.clear()
        for i in range(self._tab_bar.count()):
            p = self._tab_bar.tabToolTip(i)
            if p:
                self._path_to_index[p] = i
        # no need to reorder stack widgets; selection handled explicitly

    def _set_current_editor_by_tab(self):
        idx = self._tab_bar.currentIndex()
        if 0 <= idx < len(self._editors):
            self._stack.setCurrentWidget(self._editors[idx])

    # --- helpers -----------------------------------------------------------
    def _icon_for_file(self, path: str) -> QIcon:
        try:
            fi = QFileInfo(path)
            icon = self._icon_provider.icon(fi)
            if not icon.isNull():
                return icon
        except Exception:
            pass
        return QIcon()

__all__ = ["TabbedEditor"]