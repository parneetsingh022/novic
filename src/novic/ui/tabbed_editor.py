from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QIcon, QMouseEvent
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTabBar,
    QStackedWidget,
    QToolButton,
)
from .code_editor import CodeEditor


class _HoverCloseTabBar(QTabBar):
    """Custom tab bar showing:
    - Close button always on the selected tab
    - Close button on any other tab while hovered
    - Pointer cursor over tabs & close button
    - Stable tab widths (placeholder button for all tabs)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self._hover_index: int = -1
        self._active_close_indices: set[int] = set()

    # ---- placeholder mgmt -------------------------------------------------
    def _ensure_placeholder(self, index: int):
        if 0 <= index < self.count():
            existing = self.tabButton(index, QTabBar.RightSide)
            if existing is None:
                spacer = QToolButton(self)
                spacer.setEnabled(False)
                spacer.setAutoRaise(True)
                spacer.setFixedSize(14, 14)
                spacer.setStyleSheet("QToolButton { background: transparent; border:none; margin:0; padding:0; }")
                self.setTabButton(index, QTabBar.RightSide, spacer)

    def _replace_with_placeholder(self, index: int):
        if 0 <= index < self.count():
            spacer = QToolButton(self)
            spacer.setEnabled(False)
            spacer.setAutoRaise(True)
            spacer.setFixedSize(14, 14)
            spacer.setStyleSheet("QToolButton { background: transparent; border:none; margin:0; padding:0; }")
            self.setTabButton(index, QTabBar.RightSide, spacer)

    def _ensure_all_placeholders(self):
        for i in range(self.count()):
            self._ensure_placeholder(i)

    def tabInserted(self, index: int):  # type: ignore[override]
        super().tabInserted(index)
        self._ensure_placeholder(index)
        self._update_close_buttons()

    # ---- events -----------------------------------------------------------
    def mouseMoveEvent(self, event: QMouseEvent):  # type: ignore[override]
        idx = self.tabAt(event.position().toPoint() if hasattr(event, "position") else event.pos())
        if idx != self._hover_index:
            self._hover_index = idx
            self._update_close_buttons()
        # cursor
        if idx >= 0:
            if self.cursor().shape() != Qt.PointingHandCursor:
                self.setCursor(Qt.PointingHandCursor)
        else:
            if self.cursor().shape() != Qt.ArrowCursor:
                self.setCursor(Qt.ArrowCursor)
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):  # type: ignore[override]
        self._hover_index = -1
        self._update_close_buttons()
        if self.cursor().shape() != Qt.ArrowCursor:
            self.setCursor(Qt.ArrowCursor)
        super().leaveEvent(event)

    # ---- core logic -------------------------------------------------------
    def _update_close_buttons(self):
        self._ensure_all_placeholders()
        desired: set[int] = set()
        current = self.currentIndex()
        if 0 <= current < self.count():
            desired.add(current)
        if 0 <= self._hover_index < self.count():
            desired.add(self._hover_index)

        # Add where needed
        for idx in desired:
            btn = self.tabButton(idx, QTabBar.RightSide)
            if isinstance(btn, QToolButton) and btn.isEnabled():
                continue
            close_btn = QToolButton(self)
            close_btn.setAutoRaise(True)
            close_btn.setCursor(Qt.PointingHandCursor)
            close_btn.setFixedSize(14, 14)
            svg_path = Path(__file__).resolve().parent.parent / 'resources' / 'icons' / 'close.svg'
            icon = QIcon(str(svg_path)) if svg_path.exists() else QIcon()
            if not icon.isNull():
                close_btn.setIcon(icon)
                close_btn.setIconSize(QSize(12, 12))
            else:
                close_btn.setText('×')
            close_btn.setAccessibleName('Close')
            # NOTE: we don't capture the index in a lambda because after tab reordering
            # the stored index would become stale (especially when moving a tab left),
            # making the tab impossible to close. Instead we resolve the sender's
            # current index dynamically in _handle_close_clicked.
            close_btn.clicked.connect(self._handle_close_clicked)
            close_btn.setStyleSheet(
                "QToolButton { background: transparent; border:none; padding:0; margin:0; color:#cfd2d6; }"
                "QToolButton:hover { background:#45484d; color:#ffffff; border-radius:3px; }"
            )
            self.setTabButton(idx, QTabBar.RightSide, close_btn)
            self._active_close_indices.add(idx)

        # Remove where no longer desired
        for idx in list(self._active_close_indices):
            if idx not in desired:
                btn = self.tabButton(idx, QTabBar.RightSide)
                if isinstance(btn, QToolButton) and btn.isEnabled():
                    self._replace_with_placeholder(idx)
                self._active_close_indices.discard(idx)

    def _handle_close_clicked(self):
        btn = self.sender()
        if not isinstance(btn, QToolButton):
            return
        # Find which tab currently owns this button
        for i in range(self.count()):
            if self.tabButton(i, QTabBar.RightSide) is btn:
                self.tabCloseRequested.emit(i)
                return


class TabbedEditor(QWidget):
    """Tabbed text editor container managing multiple CodeEditor instances."""
    currentEditorChanged = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tab_bar = _HoverCloseTabBar(self)
        self._tab_bar.setMovable(True)
        self._tab_bar.setTabsClosable(False)
        self._tab_bar.setDocumentMode(True)
        self._tab_bar.setElideMode(Qt.ElideRight)
        self._tab_bar.setExpanding(False)
        self._tab_bar.tabCloseRequested.connect(self._close_index)
        self._tab_bar.currentChanged.connect(self._on_tab_changed)
        self._tab_bar.tabMoved.connect(self._on_tab_moved)

        self._stack = QStackedWidget(self)
        layout.addWidget(self._tab_bar)
        layout.addWidget(self._stack, 1)

        self._path_to_index: dict[str, int] = {}
        try:
            from .file_icons import file_icon_registry  # type: ignore
            from .file_icon_config import apply_file_icon_config  # type: ignore
            apply_file_icon_config()
            self._file_icon_registry = file_icon_registry
        except Exception:
            self._file_icon_registry = None
        self._editors: list[CodeEditor] = []

        self._apply_style()
        self._tab_bar._update_close_buttons()

    # ---- session persistence -----------------------------------------
    def save_state(self) -> dict:
        tabs: list[str] = []
        for i in range(self._tab_bar.count()):
            p = self._tab_bar.tabToolTip(i)
            if p:
                tabs.append(p)
        cur = self._tab_bar.currentIndex()
        return {"tabs": tabs, "current": cur if 0 <= cur < len(tabs) else None}

    def restore_state(self, state: dict):
        if not isinstance(state, dict):
            return
        tabs = state.get("tabs", [])
        if not isinstance(tabs, list):
            return
        current = state.get("current")
        for p in tabs:
            if isinstance(p, str) and Path(p).exists():
                try:
                    self.open_file(p)
                except Exception:
                    continue
        if isinstance(current, int) and 0 <= current < self._tab_bar.count():
            self._tab_bar.setCurrentIndex(current)
            self._set_current_editor_by_tab()
        self._tab_bar._update_close_buttons()

    # ---- styling -------------------------------------------------------
    def _apply_style(self):
        self._tab_bar.setStyleSheet(
            "QTabBar { background:#1f2123; }"
            "QTabBar::tab { background:#2a2c2f; color:#cfd2d6;"
            " padding:5px 10px 3px 10px; margin-right:0;"
            " border:1px solid #3a3d41; border-bottom:0;"
            " min-height:24px; min-width:70px; position:relative; }"
            "QTabBar::tab:selected { background:#34373a; color:#ffffff; border-top:2px solid #2f80ed; padding-top:3px; }"
            "QTabBar::tab:hover { background:#323539; }"
            "QTabBar::tab + QTabBar::tab { border-left:1px solid #2d3033; }"
        )
        self._stack.setStyleSheet("")

    # ---- public API ----------------------------------------------------
    def open_file(self, path: str):
        norm = str(Path(path).resolve())
        if norm in self._path_to_index:
            self._tab_bar.setCurrentIndex(self._path_to_index[norm])
            return
        try:
            text = Path(norm).read_text(encoding="utf-8", errors="replace")
        except Exception as e:  # pragma: no cover
            text = f"<Unable to open file>\n{e}"
        editor = CodeEditor(self._stack)
        editor.setPlainText(text)
        # auto-detect syntax from extension
        try:
            ext = Path(norm).suffix
            if ext:
                apply_ext = getattr(editor, 'applySyntaxForExtension', None)
                if callable(apply_ext):
                    apply_ext(ext)
        except Exception:
            pass
        self._stack.addWidget(editor)
        self._editors.append(editor)
        icon = self._icon_for_file(norm)
        tab_index = self._tab_bar.addTab(icon, Path(norm).name)
        self._path_to_index[norm] = tab_index
        self._tab_bar.setTabToolTip(tab_index, norm)
        self._tab_bar.setCurrentIndex(tab_index)
        self._stack.setCurrentWidget(editor)
        self._tab_bar._update_close_buttons()
        self.currentEditorChanged.emit(editor)

    def current_editor(self) -> CodeEditor | None:
        w = self._stack.currentWidget()
        return w if isinstance(w, CodeEditor) else None

    def current_path(self) -> str | None:
        idx = self._tab_bar.currentIndex()
        if idx < 0:
            return None
        return self._tab_bar.tabToolTip(idx) or None

    # ---- internal slots ------------------------------------------------
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
        self._tab_bar._update_close_buttons()

    def _on_tab_changed(self, index: int):
        if index < 0:
            return
        self._set_current_editor_by_tab()
        self._tab_bar._update_close_buttons()
        cur = self.current_editor()
        if cur is not None:
            self.currentEditorChanged.emit(cur)

    def _on_tab_moved(self, from_index: int, to_index: int):
        if from_index == to_index:
            return
        if 0 <= from_index < len(self._editors):
            editor = self._editors.pop(from_index)
            if to_index < 0:
                to_index = 0
            if to_index > len(self._editors):
                to_index = len(self._editors)
            self._editors.insert(to_index, editor)
        self._rebuild_mapping()
        self._set_current_editor_by_tab()
        self._tab_bar._update_close_buttons()

    # ---- mapping -------------------------------------------------------
    def _rebuild_mapping(self):
        self._path_to_index.clear()
        for i in range(self._tab_bar.count()):
            p = self._tab_bar.tabToolTip(i)
            if p:
                self._path_to_index[p] = i

    def _set_current_editor_by_tab(self):
        idx = self._tab_bar.currentIndex()
        if 0 <= idx < len(self._editors):
            self._stack.setCurrentWidget(self._editors[idx])

    # ---- helpers -------------------------------------------------------
    def _icon_for_file(self, path: str) -> QIcon:
        if self._file_icon_registry is not None:
            try:
                return self._file_icon_registry.icon_for(Path(path))  # type: ignore[attr-defined]
            except Exception:
                return QIcon()
        return QIcon()


__all__ = ["TabbedEditor"]

