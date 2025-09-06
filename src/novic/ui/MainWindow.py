# ui/main_window.py
from PySide6.QtWidgets import QTextEdit, QListWidget, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QTreeView, QFileSystemModel, QSizePolicy, QSplitter, QFileIconProvider
from pathlib import Path
from PySide6.QtGui import QIcon
from PySide6.QtCore import QDir, QSize, Qt, QObject, QEvent
from novic.core.menu_framework import MenuDefinition, MenuAction
from novic.ui.frameless import FramelessWindow

class MainWindow(FramelessWindow):
    def __init__(self):
        super().__init__(title="Novic", size=(900, 600))
        # populate menus
        self._register_default_menus()
        self.rebuild_menus()
        # build main body: left sidebar + editor + footer
        self._build_body()



    # --- menu setup ---
    def _register_default_menus(self):
        self.menu_registry.add_menu(MenuDefinition(
            "File",
            actions=[
                MenuAction("New", callback=self._file_new, shortcut="Ctrl+N"),
                MenuAction("Open...", callback=self._file_open, shortcut="Ctrl+O"),
                # Demonstrate a submenu with placeholder recent files
                MenuAction.submenu("Open Recent", [
                    MenuAction("(No recent files)", enabled=False),
                    MenuAction.separator(),
                    MenuAction("Clear Recent List", callback=self._clear_recent, enabled=False),
                ]),
                MenuAction.separator(),
                MenuAction("Save", callback=self._file_save, shortcut="Ctrl+S"),
                MenuAction("Save As...", callback=self._file_save_as),
            ]
        ))
        self.menu_registry.add_menu(MenuDefinition(
            "Edit",
            actions=[
                MenuAction("Undo", callback=lambda: self.editor.undo(), shortcut="Ctrl+Z"),
                MenuAction("Redo", callback=lambda: self.editor.redo(), shortcut="Ctrl+Y"),
                MenuAction("Copy", callback=lambda: self.editor.copy(), shortcut="Ctrl+C"),
                MenuAction("Cut", callback=lambda: self.editor.cut(), shortcut="Ctrl+X"),
                MenuAction("Paste", callback=lambda: self.editor.paste(), shortcut="Ctrl+V"),
            ]
        ))
        self.menu_registry.add_menu(MenuDefinition(
            "Help",
            actions=[
                MenuAction("About Novic", callback=self._about_dialog),
            ]
        ))

    # --- file ops (stubs to expand later) ---
    def _file_new(self):
        self.editor.clear()

    def _file_open(self):
        # TODO: implement file dialog
        pass

    # --- layout construction ---
    def _build_body(self):
        # Root body widget
        body = QWidget(self)
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Splitter (sidebar | editor)
        splitter = QSplitter(Qt.Horizontal, body)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(2)  # thin divider

        # Sidebar -------------------------------------------------
        sidebar = QWidget(splitter)
        sidebar_layout = QVBoxLayout(sidebar)
        # Full bleed header & tree; no bottom margin so it touches footer area
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        sidebar.setMinimumWidth(160)

        # Header (Explorer)
        header = QWidget(sidebar)
        header.setFixedHeight(24)
        header.setStyleSheet("background:#242629; border: none;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 0, 4, 0)
        header_layout.setSpacing(0)
        header_label = QLabel("Explorer", header)
        header_label.setStyleSheet("color:#cfd2d6; font-weight:bold; font-size:11px;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        sidebar_layout.addWidget(header)

        # File system tree
        self.fs_model = QFileSystemModel(self)
        # Custom file icon system (extensions / filenames) while keeping folders iconless.
        try:
            from .file_icons import FileIconProvider, file_icon_registry
            # Example (commented): register icons here or from a higher-level bootstrap
            file_icon_registry.register_extension("py", "./novic/resources/icons/files/python_file.png")
            file_icon_registry.set_default_file("./novic/resources/icons/files/regular_file.png")
            self.fs_model.setIconProvider(FileIconProvider(file_icon_registry))
        except Exception:
            # Fallback: no icons (safe degrade)
            class _EmptyIconProvider(QFileIconProvider):
                def icon(self, *_):
                    return QIcon()
            self.fs_model.setIconProvider(_EmptyIconProvider())
        self.fs_model.setRootPath(QDir.currentPath())
        self.fs_model.setFilter(QDir.AllDirs | QDir.NoDotAndDotDot | QDir.Files)
        tree = QTreeView(sidebar)
        tree.setModel(self.fs_model)
        tree.setRootIndex(self.fs_model.index(QDir.currentPath()))
        tree.setHeaderHidden(True)
        for col in range(1, self.fs_model.columnCount()):
            tree.setColumnHidden(col, True)
        tree.setAlternatingRowColors(False)
        tree.setIndentation(14)
        tree.setExpandsOnDoubleClick(True)
        tree.setAnimated(True)
        # Show custom file icons (keep small). Zero size previously hid them entirely.
        tree.setIconSize(QSize(14, 14))
        # Resolve absolute paths for branch chevron icons to avoid working-dir issues
        resources_dir = Path(__file__).resolve().parent.parent / "resources" / "icons"
        chevron_right = (resources_dir / "chevron_right.svg").as_posix()
        chevron_down = (resources_dir / "chevron_down.svg").as_posix()
        tree.setStyleSheet(
            # 5px horizontal margin requested for branch icons & text
            "QTreeView { background:#242629; color:#e3e5e8; border:none; outline:0; padding-left:5px; }"
            "QTreeView::viewport { margin-left:5px; }"
            "QTreeView::item { padding-left:2px; }"      # space between branch/chevron & icon/text
            "QTreeView::item:selected { background:#3a3d41; }"
            "QTreeView::branch { background: transparent; margin-left:0px; }"
            f"QTreeView::branch:has-children:!has-siblings:closed,QTreeView::branch:closed:has-children {{ image: url({chevron_right}); }}"
            f"QTreeView::branch:open:has-children:!has-siblings,QTreeView::branch:open:has-children {{ image: url({chevron_down}); }}"
        )
        tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tree = tree
        # Hover pointer cursor over items
        tree.setMouseTracking(True)
        class _CursorFilter(QObject):
            def eventFilter(self, obj, event):
                if event.type() == QEvent.MouseMove:
                    idx = tree.indexAt(event.pos())
                    if idx.isValid():
                        tree.viewport().setCursor(Qt.PointingHandCursor)
                    else:
                        tree.viewport().unsetCursor()
                return False
        _cf = _CursorFilter(tree)
        tree.viewport().installEventFilter(_cf)
        self._tree_cursor_filter = _cf  # keep reference
        # Single-click toggle expand/collapse when clicking directory text
        def _toggle(index):
            if self.fs_model.isDir(index):
                if tree.isExpanded(index):
                    tree.collapse(index)
                else:
                    tree.expand(index)
        tree.clicked.connect(_toggle)
        sidebar_layout.addWidget(tree)
        splitter.addWidget(sidebar)

        # Editor --------------------------------------------------
        editor = QTextEdit(splitter)
        editor.setPlaceholderText("Start typing...")
        editor.setStyleSheet("QTextEdit { background:#1f2123; color:#e3e5e8; border:none; padding:6px; }")
        self.editor = editor
        splitter.addWidget(editor)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        # Initial sizes (avoid startup gap)
        sidebar_initial = 220
        editor_initial = max(300, self.width() - sidebar_initial)
        splitter.setSizes([sidebar_initial, editor_initial])

        # Handle styling: thin light divider, brighter on hover
        splitter.setStyleSheet(
            "QSplitter::handle { background:#303234; }"
            "QSplitter::handle:horizontal:hover { background:#3a3d41; }"
        )
        body_layout.addWidget(splitter, 1)

        # Footer --------------------------------------------------
        footer = QWidget(body)
        footer.setFixedHeight(18)
        footer.setStyleSheet("background:#2b2d30; border-top:1px solid #3a3d41;")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(8, 0, 8, 0)
        footer_layout.setSpacing(12)
        status_label = QLabel("Ready", footer)
        status_label.setStyleSheet("color:#8d949a; font-size:10px;")
        footer_layout.addWidget(status_label)
        footer_layout.addStretch()
        self.status_label = status_label
        body_layout.addWidget(footer, 0)

        # Attach body to window
        self.add_content_widget(body)

    def _file_save(self):
        # TODO: implement save logic
        pass

    def _file_save_as(self):
        # TODO: implement save-as logic
        pass

    def _about_dialog(self):
        # TODO: implement about dialog (QMessageBox)
        pass

    def _clear_recent(self):
        # TODO: implement clearing recent files list
        pass
