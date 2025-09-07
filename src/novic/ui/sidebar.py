from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import Qt, QSize, QDir, Signal, QMimeData, QUrl, QTimer
from PySide6.QtGui import QIcon, QDrag, QPainter, QColor, QPixmap, QFont, QPen, QFontMetrics, QAction
from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem
from PySide6.QtWidgets import QMenu, QInputDialog, QMessageBox
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QToolButton, QStackedWidget, QLabel,
    QFileSystemModel, QTreeView, QFileIconProvider, QSizePolicy, QFrame,
    QPushButton, QFileDialog, QAbstractItemView
)
import shutil
import os


class _FileTreeView(QTreeView):
    """Custom tree view to support drag & drop of filesystem items.

    Features:
    - Internal move (within opened root) via drag & drop.
    - External drop (files/folders from OS) copies into target directory.
    - External drag (to OS) provides file URLs.
    """
    def __init__(self, parent_sidebar: 'ActivitySidebar', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sidebar = parent_sidebar
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self._hover_index = None  # type: ignore
        self.setContextMenuPolicy(Qt.DefaultContextMenu)
        self.setEditTriggers(
            QAbstractItemView.EditKeyPressed |
            QAbstractItemView.SelectedClicked
        )

        class _HoverDelegate(QStyledItemDelegate):
            def __init__(self, view: '_FileTreeView'):
                super().__init__(view)
                self._view = view
                self._color = QColor('#2f4254')  # subtle highlight

            def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):  # type: ignore
                if self._view._hover_index is not None and index == self._view._hover_index:
                    painter.save()
                    painter.fillRect(option.rect, self._color)
                    painter.restore()
                super().paint(painter, option, index)

        self.setItemDelegate(_HoverDelegate(self))

    # --- context menu -------------------------------------------------------
    def contextMenuEvent(self, event):  # type: ignore
        root_path = self._sidebar._current_root_path
        if not root_path:
            return
        pos = event.pos()
        idx = self.indexAt(pos)
        model: QFileSystemModel = self.model()  # type: ignore[assignment]
        clicked_path = None
        is_dir = False
        if idx.isValid():
            clicked_path = model.filePath(idx)
            is_dir = model.isDir(idx)
            # ensure selection reflects right-clicked item if not already multi-select including it
            if idx not in self.selectedIndexes():
                self.selectionModel().select(idx, self.selectionModel().Clear | self.selectionModel().Select | self.selectionModel().Rows)
        selected_paths = []
        for sidx in self.selectedIndexes():
            if sidx.column() != 0:
                continue
            try:
                p = model.filePath(sidx)
            except Exception:
                p = None
            if p:
                selected_paths.append(p)
        # Custom menu subclass to enforce cursor + potential future tweaks
        class _ContextMenu(QMenu):  # local lightweight subclass
            def showEvent(self, e):  # type: ignore
                super().showEvent(e)
                self.setCursor(Qt.PointingHandCursor)
        menu = _ContextMenu(self)
        menu.setCursor(Qt.PointingHandCursor)
        menu.setStyleSheet(
            "QMenu {"
            " background:#2b2e31;"
            " border:1px solid #3d4145;"
            " border-radius:8px;"
            " padding:6px 4px;"
            " font-size:12px;"
            " color:#d6d9dd;"
            "}"
            "QMenu::separator {"
            " height:1px;"
            " background:#404448;"
            " margin:6px 10px;"
            "}"
            "QMenu::item {"
            " padding:6px 16px;"
            " border-radius:5px;"
            "}"
            "QMenu::item:selected {"
            " background:#3a4046;"
            " color:#ffffff;"
            "}"
            "QMenu::item:disabled {"
            " color:#6f7479;"
            "}"
        )

        def _refresh():
            try:
                current = model.rootPath()
                model.setRootPath("")
                model.setRootPath(current)
            except Exception:
                pass

        # Helpers
        def _target_directory():
            # Directory where new file/folder or paste should land
            if clicked_path and is_dir:
                return clicked_path
            if clicked_path and not is_dir:
                return os.path.dirname(clicked_path)
            return root_path

        # New Folder
        if is_dir or not clicked_path:  # allow when right-clicking folder or empty area
            act_new_folder = QAction("New Folder", menu)
            def _new_folder():
                base_dir = _target_directory()
                base_name = "New Folder"
                candidate = base_name
                i = 1
                while os.path.exists(os.path.join(base_dir, candidate)):
                    candidate = f"{base_name} {i}"
                    i += 1
                path = os.path.join(base_dir, candidate)
                try:
                    os.makedirs(path)
                except Exception:
                    return
                # ensure parent expanded then edit the new folder name inline
                parent_idx = model.index(base_dir)
                if parent_idx.isValid():
                    self.expand(parent_idx)
                def _try_edit(attempt=0):
                    idx_new = model.index(path)
                    if idx_new.isValid():
                        self.setCurrentIndex(idx_new)
                        self.edit(idx_new)
                    elif attempt < 10:
                        QTimer.singleShot(50, lambda: _try_edit(attempt+1))
                QTimer.singleShot(0, _try_edit)
            act_new_folder.triggered.connect(_new_folder)
            menu.addAction(act_new_folder)

        # New File
        if is_dir or not clicked_path:
            act_new_file = QAction("New File", menu)
            def _new_file():
                base_dir = _target_directory()
                base_name = "New File"
                candidate = base_name
                i = 1
                while os.path.exists(os.path.join(base_dir, candidate)):
                    candidate = f"{base_name} {i}"
                    i += 1
                path = os.path.join(base_dir, candidate)
                try:
                    with open(path, 'w', encoding='utf-8'):
                        pass
                except Exception:
                    return
                parent_idx = model.index(base_dir)
                if parent_idx.isValid():
                    self.expand(parent_idx)
                def _try_edit(attempt=0):
                    idx_new = model.index(path)
                    if idx_new.isValid():
                        self.setCurrentIndex(idx_new)
                        self.edit(idx_new)
                    elif attempt < 10:
                        QTimer.singleShot(50, lambda: _try_edit(attempt+1))
                QTimer.singleShot(0, _try_edit)
            act_new_file.triggered.connect(_new_file)
            menu.addAction(act_new_file)

        if menu.actions():
            menu.addSeparator()

        # Rename
        if len(selected_paths) == 1:
            act_rename = QAction("Rename", menu)
            def _rename():
                target_idx = None
                for sidx in self.selectedIndexes():
                    if sidx.column() == 0:
                        target_idx = sidx
                        break
                if not target_idx:
                    return
                def _attempt(attempt=0):
                    self.setCurrentIndex(target_idx)
                    started = self.edit(target_idx)
                    if (not started) and attempt < 8:
                        QTimer.singleShot(40, lambda: _attempt(attempt+1))
                QTimer.singleShot(0, _attempt)
            act_rename.triggered.connect(_rename)
            menu.addAction(act_rename)

        # Delete
        if selected_paths:
            act_delete = QAction("Delete", menu)
            def _delete():
                if QMessageBox.question(self, "Delete", f"Delete {len(selected_paths)} item(s)?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                    return
                for p in selected_paths:
                    try:
                        if os.path.isdir(p):
                            shutil.rmtree(p)
                        else:
                            os.remove(p)
                    except Exception:
                        pass
                _refresh()
            act_delete.triggered.connect(_delete)
            menu.addAction(act_delete)

        # Cut / Copy
        if selected_paths:
            act_cut = QAction("Cut", menu)
            act_copy = QAction("Copy", menu)
            def _cut():
                self._sidebar._clipboard_paths = selected_paths[:]  # type: ignore[attr-defined]
                self._sidebar._clipboard_mode = 'cut'  # type: ignore[attr-defined]
            def _copy():
                self._sidebar._clipboard_paths = selected_paths[:]  # type: ignore[attr-defined]
                self._sidebar._clipboard_mode = 'copy'  # type: ignore[attr-defined]
            act_cut.triggered.connect(_cut)
            act_copy.triggered.connect(_copy)
            menu.addAction(act_cut)
            menu.addAction(act_copy)

        # Paste
        if getattr(self._sidebar, '_clipboard_paths', None):
            act_paste = QAction("Paste", menu)
            def _paste():
                dest_dir = _target_directory()
                paths = getattr(self._sidebar, '_clipboard_paths', [])
                mode = getattr(self._sidebar, '_clipboard_mode', None)
                any_changed = False
                for src in paths:
                    if not os.path.exists(src):
                        continue
                    base = os.path.basename(src)
                    dest = os.path.join(dest_dir, base)
                    # auto-rename if exists for copy, skip for cut
                    if os.path.exists(dest):
                        if mode == 'cut':
                            continue
                        i = 1
                        name, ext = os.path.splitext(base)
                        while True:
                            candidate = f"{name}_{i}{ext}"
                            cpath = os.path.join(dest_dir, candidate)
                            if not os.path.exists(cpath):
                                dest = cpath
                                break
                            i += 1
                    try:
                        if mode == 'cut':
                            shutil.move(src, dest)
                            any_changed = True
                        elif mode == 'copy':
                            if os.path.isdir(src):
                                shutil.copytree(src, dest)
                            else:
                                shutil.copy2(src, dest)
                            any_changed = True
                    except Exception:
                        pass
                if mode == 'cut':
                    # Clear clipboard after move
                    self._sidebar._clipboard_paths = []  # type: ignore[attr-defined]
                    self._sidebar._clipboard_mode = None  # type: ignore[attr-defined]
                if any_changed:
                    _refresh()
            act_paste.triggered.connect(_paste)
            menu.addAction(act_paste)

        # Copy Path
        if selected_paths:
            act_copy_path = QAction("Copy Path", menu)
            def _copy_path():
                try:
                    from PySide6.QtGui import QGuiApplication
                    clip = QGuiApplication.clipboard()
                    clip.setText('\n'.join(selected_paths))
                except Exception:
                    pass
            act_copy_path.triggered.connect(_copy_path)
            menu.addAction(act_copy_path)

        # Open in Explorer
        if len(selected_paths) == 1:
            act_open_explorer = QAction("Open in Explorer", menu)
            def _open_explorer():
                target = selected_paths[0]
                try:
                    if os.path.isdir(target):
                        os.startfile(target)  # type: ignore[attr-defined]
                    else:
                        os.startfile(os.path.dirname(target))  # type: ignore[attr-defined]
                except Exception:
                    pass
            act_open_explorer.triggered.connect(_open_explorer)
            menu.addAction(act_open_explorer)

        if not menu.actions():
            return
        menu.exec(self.viewport().mapToGlobal(pos))

    # Provide URLs for dragging out to OS / other apps
    def startDrag(self, supportedActions):  # type: ignore
        idxs = self.selectedIndexes()
        if not idxs:
            return super().startDrag(supportedActions)
        paths = []
        primary_indexes = []  # only column 0 indexes used for icon composition
        model = self.model()
        for idx in idxs:
            if idx.column() != 0:
                continue
            try:
                p = model.filePath(idx)  # type: ignore[attr-defined]
            except Exception:
                p = None
            if p:
                paths.append(p)
                primary_indexes.append(idx)
        if not paths:
            return super().startDrag(supportedActions)
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(p) for p in paths])
        drag = QDrag(self)
        drag.setMimeData(mime)

        # --- Build a drag pixmap so user sees a visual representation ---------
        try:
            padding_x = 10
            padding_y = 6
            radius = 8
            font = QFont()
            font.setPointSize(9)
            fm = QFontMetrics(font)
            if len(primary_indexes) == 1:
                label = Path(paths[0]).name
            else:
                count = len(primary_indexes)
                first_name = Path(paths[0]).name
                label = f"{first_name} (+{count-1} more)" if count > 1 else first_name
            text_w = fm.horizontalAdvance(label)
            text_h = fm.height()
            pix = QPixmap(text_w + padding_x * 2, text_h + padding_y * 2)
            pix.fill(Qt.transparent)
            painter = QPainter(pix)
            painter.setRenderHint(QPainter.Antialiasing, True)
            # Semi-transparent blue background
            bg = QColor(38, 128, 255, 150)
            painter.setPen(Qt.NoPen)
            painter.setBrush(bg)
            painter.drawRoundedRect(0, 0, pix.width(), pix.height(), radius, radius)
            painter.setFont(font)
            painter.setPen(QColor('#ffffff'))
            painter.drawText(padding_x, padding_y + fm.ascent(), fm.elidedText(label, Qt.ElideMiddle, text_w))
            painter.end()
            drag.setPixmap(pix)
            drag.setHotSpot(pix.rect().topLeft())
        except Exception:
            pass
        drag.exec(Qt.MoveAction | Qt.CopyAction, Qt.MoveAction)

    # Accept external drags
    def dragEnterEvent(self, event):  # type: ignore
        if event.mimeData().hasUrls() or event.source() is self:
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):  # type: ignore
        if event.mimeData().hasUrls() or event.source() is self:
            pos = event.position().toPoint()
            idx = self.indexAt(pos)
            model = None
            try:
                model = self.model()
            except Exception:
                pass
            target_idx = None
            if idx.isValid() and model is not None:
                try:
                    if model.isDir(idx):  # type: ignore[attr-defined]
                        target_idx = idx
                    else:
                        # use parent folder for files
                        p = idx.parent()
                        if p.isValid():
                            target_idx = p
                except Exception:
                    pass
            # Only update/repaint if changed
            if target_idx != getattr(self, '_hover_index', None):
                self._hover_index = target_idx  # type: ignore
                self.viewport().update()
            event.acceptProposedAction()
        else:
            # clear hover if leaving acceptable region
            if self._hover_index is not None:
                self._hover_index = None
                self.viewport().update()
            super().dragMoveEvent(event)

    def dragLeaveEvent(self, event):  # type: ignore
        if self._hover_index is not None:
            self._hover_index = None
            self.viewport().update()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):  # type: ignore
        model: QFileSystemModel = self.model()  # type: ignore[assignment]
        sidebar = self._sidebar
        root = sidebar._current_root_path
        if not root:
            return
        target_dir = None
        idx = self.indexAt(event.position().toPoint())
        if idx.isValid():
            p = model.filePath(idx)
            if model.isDir(idx):
                target_dir = p
            else:
                target_dir = os.path.dirname(p)
        if not target_dir:
            target_dir = root
        target_dir = os.path.abspath(target_dir)
        changed = False
        if event.mimeData().hasUrls():
            root_abs = os.path.abspath(root)
            for url in event.mimeData().urls():
                src = url.toLocalFile()
                if not src:
                    continue
                src_abs = os.path.abspath(src)
                # Internal if common root path equals project root
                try:
                    internal = os.path.commonpath([src_abs, root_abs]) == root_abs
                except Exception:
                    internal = False
                base_name = os.path.basename(src_abs)
                dest = os.path.join(target_dir, base_name)
                # Prevent dropping into itself or descendant
                try:
                    if os.path.isdir(src_abs) and os.path.commonpath([src_abs, target_dir]) == src_abs:
                        continue
                except Exception:
                    pass
                if internal:
                    if os.path.normcase(src_abs) == os.path.normcase(dest) or os.path.exists(dest):
                        continue
                    # Attempt atomic rename first
                    try:
                        os.rename(src_abs, dest)
                        changed = True
                    except Exception:
                        try:
                            shutil.move(src_abs, dest)
                            changed = True
                        except Exception:
                            pass
                else:
                    if os.path.exists(dest):
                        continue
                    try:
                        if os.path.isdir(src_abs):
                            shutil.copytree(src_abs, dest)
                        else:
                            shutil.copy2(src_abs, dest)
                        changed = True
                    except Exception:
                        pass
            # Internal drag should be Move action
            event.setDropAction(Qt.MoveAction)
        if changed:
            try:
                current = model.rootPath()
                model.setRootPath("")
                model.setRootPath(current)
            except Exception:
                pass
        # clear hover highlight after drop
        if self._hover_index is not None:
            self._hover_index = None
            self.viewport().update()
        event.accept()



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
        # Root layout
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
            self._fs_model.setReadOnly(False)
        except Exception:
            pass
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
        self._tree = _FileTreeView(self, explorer_page)
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
            "QTreeView { background:#242629; color:#e3e5e8; border:none; outline:0; padding:0; font-size:13px; }"
            "QTreeView::viewport { margin:0; }"
            "QTreeView::item { padding:1px 4px; border:0; }"
            "QTreeView::item:hover { background:#33373b; }"
            "QTreeView::item:selected { background:#3a3f45; }"
            "QTreeView::branch { background: transparent; margin-left:0px; }"
            f"QTreeView::branch:has-children:!has-siblings:closed,QTreeView::branch:closed:has-children {{ image: url({chevron_right}); }}"
            f"QTreeView::branch:open:has-children:!has-siblings,QTreeView::branch:open:has-children {{ image: url({chevron_down}); }}"
        )
        # Increase tree view font size
        try:
            _f = self._tree.font()
            ps = _f.pointSize()
            if ps > 0:
                _f.setPointSize(ps + 2)
            else:
                _f.setPointSize(13)
            self._tree.setFont(_f)
        except Exception:
            pass
        self._tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._tree.setCursor(Qt.PointingHandCursor)
        self._tree.setCursor(Qt.PointingHandCursor)
        exp_layout.addWidget(self._tree)

        def _toggle(idx):
            if self._fs_model.isDir(idx):
                if self._tree.isExpanded(idx):
                    self._tree.collapse(idx)
                else:
                    self._tree.expand(idx)
            else:
                path = self._fs_model.filePath(idx)
                if path:
                    self.fileActivated.emit(path)
        self._tree.clicked.connect(_toggle)
        open_btn.clicked.connect(self.open_folder)
        self._folder_loaded = False
        self._current_root_path = None  # type: ignore[assignment]

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
        # clipboard (cut/copy) store
        self._clipboard_paths = []  # type: ignore[assignment]
        self._clipboard_mode = None  # type: ignore[assignment]

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
        self._load_folder_path(path)

    def close_folder(self):
        """Close the currently open folder and reset the explorer UI."""
        if not self._folder_loaded:
            return
        # Hide tree, show placeholder
        self._tree.hide()
        self._placeholder.show()
        self._folder_loaded = False
        self._current_root_path = None
        # Clear root index (optional visual reset)
        try:
            empty_idx = self._fs_model.setRootPath("")  # might be invalid, safe fallback
            self._tree.setRootIndex(empty_idx)
        except Exception:
            pass

    # --- state save/restore ----------------------------------------------
    def _load_folder_path(self, path: str):
        """Internal helper to load a folder without prompting."""
        if not path:
            return
        idx = self._fs_model.setRootPath(path)
        self._tree.setRootIndex(idx)
        for c in range(1, self._fs_model.columnCount()):  # hide extra columns
            self._tree.setColumnHidden(c, True)
        self._placeholder.hide()
        self._tree.show()
        self._folder_loaded = True
        self._current_root_path = path
        self.folderOpened.emit(path)

    def save_state(self) -> dict:
        """Return a serialisable snapshot of the explorer state.

        Structure:
        {
            'folder': str | None,      # absolute folder path or None
            'expanded': [rel paths],   # paths relative to root for expanded dirs
        }
        """
        state: dict[str, object] = {"folder": None, "expanded": []}
        if not self._folder_loaded or not self._current_root_path:
            return state
        root_path = Path(self._current_root_path)
        expanded: list[str] = []

        def _recurse(parent_index):
            rows = self._fs_model.rowCount(parent_index)
            for r in range(rows):
                idx = self._fs_model.index(r, 0, parent_index)
                if not idx.isValid():
                    continue
                p = Path(self._fs_model.filePath(idx))
                if self._fs_model.isDir(idx):
                    if self._tree.isExpanded(idx):
                        try:
                            rel = p.relative_to(root_path)
                            expanded.append(rel.as_posix())
                        except Exception:
                            pass
                        _recurse(idx)
        root_index = self._tree.rootIndex()
        _recurse(root_index)
        state["folder"] = str(root_path)
        state["expanded"] = expanded
        return state

    def restore_state(self, state: dict):
        """Restore explorer from a saved snapshot."""
        try:
            folder = state.get("folder") if isinstance(state, dict) else None
        except Exception:
            folder = None
        if not folder or not Path(folder).exists():
            return
        self._load_folder_path(folder)
        expanded = state.get("expanded", []) if isinstance(state, dict) else []
        if not isinstance(expanded, list):
            return
        root_path = Path(folder)
        for rel in expanded:
            try:
                full = (root_path / rel).resolve()
            except Exception:
                continue
            if not full.exists():
                continue
            idx = self._fs_model.index(str(full))
            if idx.isValid():
                self._tree.expand(idx)


__all__ = ["ActivitySidebar"]
