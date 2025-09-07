from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import Qt, QFileInfo, QSize
from PySide6.QtGui import QIcon, QMouseEvent
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTabBar,
    QStackedWidget,
    QTextEdit,
    QToolButton,
    QStyle,
)


class _HoverCloseTabBar(QTabBar):
    """A QTabBar that only shows a close button when hovering a tab.

    We dynamically install/remove a QToolButton as the RightSide tab button
    for the hovered tab. This avoids always-visible close buttons and any
    red/colored background; the button uses the standard window close icon.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self._hover_index: int = -1
        self._last_active_index: int = -1

    # Ensure placeholder button exists for a tab index
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

    # Called by Qt when a tab is inserted; we add placeholder immediately to avoid size jump
    def tabInserted(self, index: int):  # type: ignore[override]
        super().tabInserted(index)
        self._ensure_placeholder(index)

    # --- Qt events -------------------------------------------------
    def mouseMoveEvent(self, event: QMouseEvent):  # type: ignore[override]
        idx = self.tabAt(event.position().toPoint() if hasattr(event, "position") else event.pos())
        if idx != self._hover_index:
            self._hover_index = idx
            self._update_close_button()
        # Change cursor to pointing hand when over a tab (any tab index >=0)
        if idx >= 0:
            if self.cursor().shape() != Qt.PointingHandCursor:
                self.setCursor(Qt.PointingHandCursor)
        else:
            if self.cursor().shape() != Qt.ArrowCursor:
                self.setCursor(Qt.ArrowCursor)
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):  # type: ignore[override]
        # On leave, revert active close button to placeholder so it disappears
        if self._hover_index != -1:
            self._replace_with_placeholder(self._hover_index)
        self._hover_index = -1
        # Restore default cursor
        if self.cursor().shape() != Qt.ArrowCursor:
            self.setCursor(Qt.ArrowCursor)
        super().leaveEvent(event)

    # --- helpers ---------------------------------------------------
    def _update_close_button(self):
        # Always ensure placeholders so tab widths never change
        self._ensure_all_placeholders()

        # Promote hovered tab's placeholder to active close button
        if 0 <= self._hover_index < self.count():
            current_btn = self.tabButton(self._hover_index, QTabBar.RightSide)
            if isinstance(current_btn, QToolButton) and not current_btn.isEnabled():
                close_btn = QToolButton(self)
                close_btn.setAutoRaise(True)
                close_btn.setCursor(Qt.ArrowCursor)
                close_btn.setFixedSize(14, 14)
                svg_path = Path(__file__).resolve().parent.parent / 'resources' / 'icons' / 'close.svg'
                icon = QIcon(str(svg_path)) if svg_path.exists() else QIcon()
                if not icon.isNull():
                    close_btn.setIcon(icon)
                    close_btn.setIconSize(QSize(12, 12))
                else:
                    close_btn.setText('×')
                close_btn.setAccessibleName('Close')
                close_btn.clicked.connect(self._emit_close_current)
                close_btn.setStyleSheet(
                    "QToolButton { background: transparent; border:none; padding:0; margin:0; color:#cfd2d6; }"
                    "QToolButton:hover { background:#45484d; color:#ffffff; border-radius:3px; }"
                )
                self.setTabButton(self._hover_index, QTabBar.RightSide, close_btn)

        # Revert previously active (if different) back to placeholder if it became a close button
        if 0 <= self._last_active_index < self.count() and self._last_active_index != self._hover_index:
            prev_btn = self.tabButton(self._last_active_index, QTabBar.RightSide)
            if isinstance(prev_btn, QToolButton) and prev_btn.isEnabled():
                self._replace_with_placeholder(self._last_active_index)

        self._last_active_index = self._hover_index

    def _emit_close_current(self):
        if 0 <= self._hover_index < self.count():
            self.tabCloseRequested.emit(self._hover_index)


class TabbedEditor(QWidget):
    """Simple tabbed text editor container.

    - One QTextEdit per tab.
    - Avoids duplicate tabs for same absolute path.
    - Supports reordering with matching editor content.
    - Close button appears only on hover (per request).
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tab_bar = _HoverCloseTabBar(self)
        self._tab_bar.setMovable(True)
        self._tab_bar.setTabsClosable(False)  # managed manually by hover buttons
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
        # Lazy import custom file icon machinery (shared with sidebar)
        try:
            from .file_icons import file_icon_registry  # type: ignore
            from .file_icon_config import apply_file_icon_config  # type: ignore
            apply_file_icon_config()
            self._file_icon_registry = file_icon_registry
        except Exception:
            self._file_icon_registry = None
        self._editors: list[QTextEdit] = []

        self._apply_style()

    # --- styling ---------------------------------------------------
    def _apply_style(self):
        self._tab_bar.setStyleSheet(
            "QTabBar { background:#1f2123; }"
            "QTabBar::tab { background:#2a2c2f; color:#cfd2d6; padding:3px 8px 1px 8px; margin-right:2px;"
            " border:1px solid #3a3d41; border-bottom:0; border-top-left-radius:3px;"
            " border-top-right-radius:3px; min-height:20px; min-width:70px; position:relative; }"
            "QTabBar::tab:selected { background:#34373a; color:#ffffff; border-top:2px solid #2f80ed; padding-top:1px; }"
            "QTabBar::tab:hover { background:#323539; }"
        )
        self._stack.setStyleSheet(
            "QTextEdit { background:#1f2123; color:#e3e5e8; border:none; padding:6px; }"
        )

    # --- public API ------------------------------------------------
    def open_file(self, path: str):
        norm = str(Path(path).resolve())
        if norm in self._path_to_index:
            self._tab_bar.setCurrentIndex(self._path_to_index[norm])
            return
        try:
            text = Path(norm).read_text(encoding="utf-8", errors="replace")
        except Exception as e:  # pragma: no cover - display fallback
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
        idx = self._tab_bar.currentIndex()
        if idx < 0:
            return None
        return self._tab_bar.tabToolTip(idx) or None

    # --- internal slots --------------------------------------------
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
            # QTabBar already finalized the visual order; insert at to_index.
            if to_index < 0:
                to_index = 0
            if to_index > len(self._editors):
                to_index = len(self._editors)
            self._editors.insert(to_index, editor)
        self._rebuild_mapping()
        self._set_current_editor_by_tab()

    # --- mapping maintenance ---------------------------------------
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

    # --- helpers ----------------------------------------------------
    def _icon_for_file(self, path: str) -> QIcon:
        if self._file_icon_registry is not None:
            try:
                return self._file_icon_registry.icon_for(Path(path))  # type: ignore[attr-defined]
            except Exception:
                return QIcon()
        return QIcon()


__all__ = ["TabbedEditor"]
