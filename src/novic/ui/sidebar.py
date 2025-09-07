from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import Qt, QSize, QDir, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QToolButton, QStackedWidget, QLabel,
    QFileSystemModel, QTreeView, QFileIconProvider, QSizePolicy, QFrame,
    QPushButton, QFileDialog
)


class ActivitySidebar(QWidget):
    """Activity bar + explorer/settings panels.

    Starts with an empty explorer showing a button to open a folder. Only after
    a folder is chosen is the tree view displayed.
    """

    panelShown = Signal()
    panelHidden = Signal()
    currentPanelChanged = Signal(int)
    folderOpened = Signal(str)
    fileActivated = Signal(str)  # emitted with absolute file path when a file is clicked

    ICON_BAR_WIDTH = 56

    def __init__(self, parent=None):
        super().__init__(parent)
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # --- Activity icon bar -------------------------------------------------
        self._nav_bar = QWidget(self)
        self._nav_bar.setFixedWidth(self.ICON_BAR_WIDTH)
        self._nav_bar.setStyleSheet("background:#1d1f21;")
        nav_layout = QVBoxLayout(self._nav_bar)
        nav_layout.setContentsMargins(0, 6, 0, 6)
        nav_layout.setSpacing(4)

        def _make_tool(icon_name: str, tooltip: str):
            btn = QToolButton(self._nav_bar)
            btn.setToolButtonStyle(Qt.ToolButtonIconOnly)
            btn.setFixedSize(self.ICON_BAR_WIDTH, 44)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setAutoRaise(True)
            btn.setStyleSheet("QToolButton { background:transparent; border:0; }")
            icon_path_svg = Path(__file__).resolve().parent.parent / "resources" / "icons" / "side_icon" / f"{icon_name}.svg"
            icon_path_png = icon_path_svg.with_suffix('.png')
            if icon_path_svg.exists():
                btn.setIcon(QIcon(str(icon_path_svg)))
            elif icon_path_png.exists():
                btn.setIcon(QIcon(str(icon_path_png)))
            else:
                btn.setText(icon_name[:2].upper())
            btn.setIconSize(QSize(28, 28))
            btn.setToolTip(tooltip)
            btn.setCheckable(True)
            return btn

        self._explorer_btn = _make_tool("explorer", "Explorer")
        self._settings_btn = _make_tool("settings", "Settings")
        self._explorer_btn.setChecked(True)

        self._nav_bar.setStyleSheet(
            self._nav_bar.styleSheet() +
            "QToolButton { background:transparent; border:0; padding:0; margin:0; color:#cfd2d6; }"
            "QToolButton:hover { background:#2a2c2f; }"
            "QToolButton:checked { background:#303336; }"
            "QToolButton:focus { outline: none; }"
            "QToolButton:!hover:!checked { background:transparent; }"
            "QToolButton::menu-indicator { image: none; width:0; height:0; }"
        )

        buttons_container = QWidget(self._nav_bar)
        bc_layout = QVBoxLayout(buttons_container)
        bc_layout.setContentsMargins(0, 0, 0, 0)
        bc_layout.setSpacing(4)
        bc_layout.addWidget(self._explorer_btn)
        bc_layout.addWidget(self._settings_btn)
        bc_layout.addStretch()
        nav_layout.addWidget(buttons_container)
        nav_layout.addStretch()

        # Selection indicator
        self._indicator = QFrame(buttons_container)
        self._indicator.setFixedWidth(4)
        self._indicator.setStyleSheet("background:#2680ff; border:none; border-radius:2px;")
        self._indicator.hide()

        # --- Panels ------------------------------------------------------------
        self._stack = QStackedWidget(self)
        self._stack.setStyleSheet("background:#242629;")

        # Explorer page
        explorer_page = QWidget()
        exp_layout = QVBoxLayout(explorer_page)
        exp_layout.setContentsMargins(0, 0, 0, 0)
        exp_layout.setSpacing(0)
        header = QWidget(explorer_page)
        header.setFixedHeight(24)
        header.setStyleSheet("background:#242629; border:none;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(8, 0, 4, 0)
        hl.setSpacing(0)
        title_lbl = QLabel("Explorer", header)
        title_lbl.setStyleSheet("color:#cfd2d6; font-weight:bold; font-size:11px;")
        hl.addWidget(title_lbl)
        hl.addStretch()
        exp_layout.addWidget(header)

        # Filesystem model (lazy root)
        self._fs_model = QFileSystemModel(self)
        try:
            from .file_icons import FileIconProvider, file_icon_registry  # type: ignore
            from .file_icon_config import apply_file_icon_config  # type: ignore
            apply_file_icon_config()
            self._fs_model.setIconProvider(FileIconProvider(file_icon_registry))
        except Exception:
            class _EmptyIconProvider(QFileIconProvider):
                def icon(self, *_):
                    return QIcon()
            self._fs_model.setIconProvider(_EmptyIconProvider())
        self._fs_model.setFilter(QDir.AllDirs | QDir.NoDotAndDotDot | QDir.Files)

        # Placeholder before a folder is opened
        self._placeholder = QWidget(explorer_page)
        ph_layout = QVBoxLayout(self._placeholder)
        ph_layout.setContentsMargins(20, 30, 20, 20)
        ph_layout.setSpacing(14)
        msg = QLabel("No folder opened", self._placeholder)
        msg.setStyleSheet("color:#cfd2d6; font-size:13px; font-weight:bold;")
        sub = QLabel("Click the button below to choose a folder to explore.", self._placeholder)
        sub.setStyleSheet("color:#9ca2a8; font-size:11px;")
        sub.setWordWrap(True)
        open_btn = QPushButton("Open Folder...", self._placeholder)
        open_btn.setCursor(Qt.PointingHandCursor)
        open_btn.setStyleSheet(
            "QPushButton { background:#2f3235; border:1px solid #3a3d41; color:#e3e5e8; padding:6px 14px; border-radius:4px; }"
            "QPushButton:hover { background:#3a3d41; }"
            "QPushButton:pressed { background:#45484c; }"
        )
        ph_layout.addWidget(msg)
        ph_layout.addWidget(sub)
        ph_layout.addSpacing(4)
        ph_layout.addWidget(open_btn, 0, Qt.AlignLeft)
        ph_layout.addStretch()
        exp_layout.addWidget(self._placeholder)

        # Tree view (hidden initially)
        self._tree = QTreeView(explorer_page)
        self._tree.hide()
        self._tree.setModel(self._fs_model)
        self._tree.setHeaderHidden(True)
        self._tree.setIndentation(14)
        self._tree.setAnimated(True)
        self._tree.setIconSize(QSize(14, 14))
        resources_dir = Path(__file__).resolve().parent.parent / "resources" / "icons"
        chevron_right = (resources_dir / "chevron_right.svg").as_posix()
        chevron_down = (resources_dir / "chevron_down.svg").as_posix()
        self._tree.setStyleSheet(
            "QTreeView { background:#242629; color:#e3e5e8; border:none; outline:0; padding-left:5px; }"
            "QTreeView::viewport { margin-left:5px; }"
            "QTreeView::item { padding-left:2px; }"
            "QTreeView::item:selected { background:#3a3d41; }"
            "QTreeView::branch { background: transparent; margin-left:0px; }"
            f"QTreeView::branch:has-children:!has-siblings:closed,QTreeView::branch:closed:has-children {{ image: url({chevron_right}); }}"
            f"QTreeView::branch:open:has-children:!has-siblings,QTreeView::branch:open:has-children {{ image: url({chevron_down}); }}"
        )
        self._tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        exp_layout.addWidget(self._tree)

        def _toggle(idx):
            if self._fs_model.isDir(idx):
                if self._tree.isExpanded(idx):
                    self._tree.collapse(idx)
                else:
                    self._tree.expand(idx)
            else:
                # open file
                path = self._fs_model.filePath(idx)
                if path:
                    self.fileActivated.emit(path)
        self._tree.clicked.connect(_toggle)
        open_btn.clicked.connect(self.open_folder)
        self._folder_loaded = False

        # Settings page (placeholder)
        settings_page = QWidget()
        sl = QVBoxLayout(settings_page)
        sl.setContentsMargins(8, 8, 8, 8)
        sl.setSpacing(4)
        ph = QLabel("Settings panel (placeholder)", settings_page)
        ph.setStyleSheet("color:#cfd2d6; font-size:12px;")
        sl.addWidget(ph)
        sl.addStretch()

        self._stack.addWidget(explorer_page)   # index 0
        self._stack.addWidget(settings_page)   # index 1

        root_layout.addWidget(self._nav_bar, 0)
        root_layout.addWidget(self._stack, 1)

        # Initial state
        self._panel_visible = True
        self._active_btn = self._explorer_btn
        self._move_indicator(self._explorer_btn)

        self._explorer_btn.clicked.connect(lambda: self._activate(self._explorer_btn, 0))
        self._settings_btn.clicked.connect(lambda: self._activate(self._settings_btn, 1))

    # --- internal helpers ----------------------------------------------------
    def _move_indicator(self, btn):
        self._indicator.setFixedHeight(btn.height())
        self._indicator.move(0, btn.y())
        if not self._indicator.isVisible():
            self._indicator.show()

    def _activate(self, btn, idx: int):
        if btn is self._active_btn and self._panel_visible:
            # hide panel
            self._stack.hide()
            self._panel_visible = False
            btn.setChecked(False)
            self._active_btn = None
            self._indicator.hide()
            self.panelHidden.emit()
            return
        if not self._panel_visible:
            self._stack.show()
            self._panel_visible = True
            self.panelShown.emit()
        if self._active_btn and self._active_btn is not btn:
            self._active_btn.setChecked(False)
        btn.setChecked(True)
        self._active_btn = btn
        self._stack.setCurrentIndex(idx)
        if self._panel_visible:
            self._move_indicator(btn)
        self.currentPanelChanged.emit(idx)

    # --- public API ----------------------------------------------------------
    def is_panel_visible(self) -> bool:
        return self._panel_visible

    def nav_bar_width(self) -> int:
        return self._nav_bar.width()

    def stack(self) -> QStackedWidget:
        return self._stack

    def ensure_panel_visible(self):
        if not self._panel_visible:
            self._activate(self._explorer_btn if self._active_btn is None else self._active_btn,
                           self._stack.currentIndex())

    # --- folder handling -----------------------------------------------------
    def open_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Open Folder", QDir.homePath())
        if not path:
            return
        idx = self._fs_model.setRootPath(path)
        self._tree.setRootIndex(idx)
        for c in range(1, self._fs_model.columnCount()):  # hide extra columns
            self._tree.setColumnHidden(c, True)
        self._placeholder.hide()
        self._tree.show()
        self._folder_loaded = True
        self.folderOpened.emit(path)


__all__ = ["ActivitySidebar"]
