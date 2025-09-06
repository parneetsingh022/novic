# ui/main_window.py
from PySide6.QtWidgets import QTextEdit, QListWidget, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QTreeView, QFileSystemModel, QSizePolicy, QSplitter
from PySide6.QtCore import QDir, QSize, Qt
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
        body = QWidget(self)
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal, body)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(4)

        # Sidebar -------------------------------------------------
        sidebar = QWidget(splitter)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(6, 4, 0, 4)
        sidebar_layout.setSpacing(4)
        sidebar.setMinimumWidth(160)

        label = QLabel("Explorer", sidebar)
        label.setStyleSheet("color:#cfd2d6; font-weight:bold; font-size:11px; margin-left:2px;")
        sidebar_layout.addWidget(label)

        self.fs_model = QFileSystemModel(self)
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
        tree.setIconSize(QSize(16, 16))
        tree.setStyleSheet(
            "QTreeView { background:#242629; color:#e3e5e8; border:none; outline:0; }"
            "QTreeView::item:selected { background:#3a3d41; }"
            "QTreeView::branch { background: transparent; }"
        )
        tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tree = tree
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

        # Initial sizes (prevents startup gap) --------------------
        sidebar_initial = 220
        editor_initial = max(300, self.width() - sidebar_initial)
        splitter.setSizes([sidebar_initial, editor_initial])

        # Handle styling (invisible unless hover) -----------------
        splitter.setStyleSheet(
            "QSplitter::handle { background: transparent; }"
            "QSplitter::handle:horizontal:hover { background: rgba(255,255,255,0.06); }"
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
