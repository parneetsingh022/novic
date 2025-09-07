# ui/main_window.py
from PySide6.QtWidgets import (QTextEdit, QListWidget, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
                               QTreeView, QFileSystemModel, QSizePolicy, QSplitter, QFileIconProvider,
                               QDialog, QPushButton, QScrollArea, QFrame, QStackedWidget, QToolButton)
from pathlib import Path
from PySide6.QtGui import QIcon
from PySide6.QtCore import QDir, QSize, Qt, QObject, QEvent
from novic.core.menu_framework import MenuDefinition, MenuAction
from novic.ui.frameless import FramelessWindow

class MainWindow(FramelessWindow):
    def __init__(self):
        # Non-resizable and hide menu bar per request (menu still built for About action trigger)
        super().__init__(title="Novic", size=(900, 600), resizable=False, show_menu=True)
        # populate menus
        self._register_default_menus()
        self.rebuild_menus()
        # build main body: left sidebar + editor + footer
        self._build_body()
        # Disable resize visuals entirely
        self.set_resizable(False)



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

        # Left composite (icon bar + stack) ------------------------------------
        left_container = QWidget(splitter)
        left_hbox = QHBoxLayout(left_container)
        left_hbox.setContentsMargins(0, 0, 0, 0)
        left_hbox.setSpacing(0)

        # Icon bar (activity bar)
        nav_bar = QWidget(left_container)
        nav_bar.setFixedWidth(56)
        nav_bar.setStyleSheet("background:#1d1f21;")
        nav_layout = QVBoxLayout(nav_bar)
        nav_layout.setContentsMargins(0, 6, 0, 6)
        nav_layout.setSpacing(4)

        def _make_tool(icon_name: str, tooltip: str):
            btn = QToolButton(nav_bar)
            btn.setToolButtonStyle(Qt.ToolButtonIconOnly)
            btn.setFixedSize(56, 44)
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
            btn.setAutoExclusive(True)
            return btn

        explorer_btn = _make_tool("explorer", "Explorer")
        settings_btn = _make_tool("settings", "Settings")
        explorer_btn.setChecked(True)

        nav_bar.setStyleSheet(
            nav_bar.styleSheet() +
            "QToolButton { background:transparent; border:0; padding:0; margin:0; color:#cfd2d6; }"
            "QToolButton:hover { background:#2a2c2f; }"
            "QToolButton:checked { background:#303336; }"
            "QToolButton:focus { outline: none; }"
            "QToolButton:!hover:!checked { background:transparent; }"
            "QToolButton::menu-indicator { image: none; width:0; height:0; }"
        )

        nav_layout.addStretch()  # we will overlay buttons with an indicator container next
        # Create a container holding buttons and indicator overlay
        from PySide6.QtWidgets import QFrame
        buttons_container = QWidget(nav_bar)
        buttons_container.setFixedWidth(56)
        bc_layout = QVBoxLayout(buttons_container)
        bc_layout.setContentsMargins(0,0,0,0)
        bc_layout.setSpacing(4)
        bc_layout.addWidget(explorer_btn)
        bc_layout.addWidget(settings_btn)
        bc_layout.addStretch()
        nav_layout.insertWidget(0, buttons_container)

        # Indicator
        self._side_indicator = QFrame(buttons_container)
        self._side_indicator.setFixedWidth(4)
        self._side_indicator.setStyleSheet("background:#2680ff; border:none; border-radius:2px;")
        self._side_indicator.hide()

        def _move_indicator(btn, checked):
            if not checked:
                return
            self._side_indicator.setFixedHeight(btn.height())
            y = btn.y()
            self._side_indicator.move(0, y)
            if not self._side_indicator.isVisible():
                self._side_indicator.show()

        explorer_btn.toggled.connect(lambda c: _move_indicator(explorer_btn, c))
        settings_btn.toggled.connect(lambda c: _move_indicator(settings_btn, c))
        _move_indicator(explorer_btn, True)

        # Stacked sidebar views
        stack = QStackedWidget(left_container)
        stack.setStyleSheet("background:#242629;")

        # Explorer page (migrated from previous sidebar)
        explorer_page = QWidget()
        sidebar_layout = QVBoxLayout(explorer_page)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        explorer_page.setMinimumWidth(160)

        header = QWidget(explorer_page)
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

        self.fs_model = QFileSystemModel(self)
        try:
            from .file_icons import FileIconProvider, file_icon_registry
            from .file_icon_config import apply_file_icon_config
            apply_file_icon_config()
            self.fs_model.setIconProvider(FileIconProvider(file_icon_registry))
        except Exception:
            class _EmptyIconProvider(QFileIconProvider):
                def icon(self, *_):
                    return QIcon()
            self.fs_model.setIconProvider(_EmptyIconProvider())
        self.fs_model.setRootPath(QDir.currentPath())
        self.fs_model.setFilter(QDir.AllDirs | QDir.NoDotAndDotDot | QDir.Files)
        tree = QTreeView(explorer_page)
        tree.setModel(self.fs_model)
        tree.setRootIndex(self.fs_model.index(QDir.currentPath()))
        tree.setHeaderHidden(True)
        for col in range(1, self.fs_model.columnCount()):
            tree.setColumnHidden(col, True)
        tree.setAlternatingRowColors(False)
        tree.setIndentation(14)
        tree.setExpandsOnDoubleClick(True)
        tree.setAnimated(True)
        tree.setIconSize(QSize(14, 14))
        resources_dir = Path(__file__).resolve().parent.parent / "resources" / "icons"
        chevron_right = (resources_dir / "chevron_right.svg").as_posix()
        chevron_down = (resources_dir / "chevron_down.svg").as_posix()
        tree.setStyleSheet(
            "QTreeView { background:#242629; color:#e3e5e8; border:none; outline:0; padding-left:5px; }"
            "QTreeView::viewport { margin-left:5px; }"
            "QTreeView::item { padding-left:2px; }"
            "QTreeView::item:selected { background:#3a3d41; }"
            "QTreeView::branch { background: transparent; margin-left:0px; }"
            f"QTreeView::branch:has-children:!has-siblings:closed,QTreeView::branch:closed:has-children {{ image: url({chevron_right}); }}"
            f"QTreeView::branch:open:has-children:!has-siblings,QTreeView::branch:open:has-children {{ image: url({chevron_down}); }}"
        )
        tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tree = tree
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
        self._tree_cursor_filter = _cf
        def _toggle(index):
            if self.fs_model.isDir(index):
                if tree.isExpanded(index):
                    tree.collapse(index)
                else:
                    tree.expand(index)
        tree.clicked.connect(_toggle)
        sidebar_layout.addWidget(tree)

        # Settings placeholder page
        settings_page = QWidget()
        settings_layout = QVBoxLayout(settings_page)
        settings_layout.setContentsMargins(8, 8, 8, 8)
        settings_layout.setSpacing(4)
        ph = QLabel("Settings panel (placeholder)", settings_page)
        ph.setStyleSheet("color:#cfd2d6; font-size:12px;")
        settings_layout.addWidget(ph)
        settings_layout.addStretch()

        stack.addWidget(explorer_page)   # index 0
        stack.addWidget(settings_page)   # index 1
        self.sidebar_stack = stack

        left_hbox.addWidget(nav_bar, 0)
        left_hbox.addWidget(stack, 1)
        splitter.addWidget(left_container)

        def _activate(idx):
            stack.setCurrentIndex(idx)
        explorer_btn.clicked.connect(lambda: _activate(0))
        settings_btn.clicked.connect(lambda: _activate(1))

        # Editor --------------------------------------------------
        editor = QTextEdit(splitter)
        editor.setPlaceholderText("Start typing...")
        editor.setStyleSheet("QTextEdit { background:#1f2123; color:#e3e5e8; border:none; padding:6px; }")
        self.editor = editor
        splitter.addWidget(editor)
        splitter.setStretchFactor(0, 0)  # left composite
        splitter.setStretchFactor(1, 1)  # editor

        # Initial sizes (avoid startup gap)
        sidebar_initial = 260  # icon bar + sidebar
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
                from novic import __version__ as app_version
                import platform, textwrap
                from PySide6.QtCore import qVersion

                py_ver = platform.python_version()
                os_info = platform.platform()
                qt_ver = qVersion()
                icon_path = Path(__file__).resolve().parent.parent / "resources" / "icons" / "novic_logo.png"
                icon_path_str = icon_path.as_posix()
                html = f"""
                        <div style='color:#e3e5e8; font-family:Segoe UI, sans-serif; padding:6px 10px 10px 10px;'>
                            <div style='display:flex; align-items:center; gap:10px; margin:0 0 6px 0;'>
                                <img src='{icon_path_str}' width='80' height='80' style='border-radius:6px; padding:4px; border:1px solid #3a3d41;' />
                                <div>
                                    <h2 style='margin:0; font-size:18px; line-height:18px;'>Novic <span style="opacity:.65;font-weight:400;font-size:13px;">v{app_version}</span></h2>
                                    <div style='margin:4px 0 0 0; line-height:140%; font-size:12px; color:#b7bcc1;'>A minimal experimental PySide6 editor scaffold.</div>
                                </div>
                            </div>
                            <h4 style='margin:4px 0 4px 0; font-size:13px; color:#cfd2d6;'>Runtime</h4>
                            <table style='font-size:11px; border-collapse:collapse;'>
                                <tr><td style='padding:2px 6px; opacity:.65;'>Python</td><td style='padding:2px 6px;'>{py_ver}</td></tr>
                                <tr><td style='padding:2px 6px; opacity:.65;'>Qt</td><td style='padding:2px 6px;'>{qt_ver}</td></tr>
                                <tr><td style='padding:2px 6px; opacity:.65;'>Platform</td><td style='padding:2px 6px;'>{os_info}</td></tr>
                            </table>
                            <div style='margin-top:12px; font-size:11px; color:#8d949a;'>© 2025 Novic Project • Apache-2.0 License</div>
                        </div>
                        """
                dlg = QDialog(self)
                dlg.setWindowTitle("About Novic")
                if icon_path.exists():
                        dlg.setWindowIcon(QIcon(str(icon_path)))
                dlg.setModal(True)
                dlg.setAttribute(Qt.WA_TranslucentBackground, True)
                dlg.setFixedWidth(520)
                outer = QVBoxLayout(dlg)
                outer.setContentsMargins(0,0,0,0)
                outer.setSpacing(0)
                card = QFrame(dlg)
                card.setObjectName("aboutCard")
                card.setStyleSheet(
                        "#aboutCard { background:#242629; border:1px solid #3a3d41;}"
                        "QPushButton { background:#3a3d41; color:#e3e5e8; border:none; padding:6px 14px; border-radius:4px; font-size:12px; }"
                        "QPushButton:hover { background:#4a4d51; }"
                        "QPushButton:pressed { background:#5a5d61; }"
                )
                card_layout = QVBoxLayout(card)
                card_layout.setContentsMargins(18,16,18,14)
                card_layout.setSpacing(10)
                scroll = QScrollArea(card)
                scroll.setWidgetResizable(True)
                scroll.setFrameShape(QFrame.NoFrame)
                scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                scroll.setStyleSheet("QScrollArea { border:none; } QScrollBar:vertical { background:#2b2d30; width:8px; margin:2px; } QScrollBar::handle { background:#44484c; border-radius:3px; } QScrollBar::handle:hover { background:#565a5e; }")
                content = QWidget()
                c_layout = QVBoxLayout(content)
                c_layout.setContentsMargins(6,4,6,6)
                c_layout.setSpacing(0)
                lbl = QLabel(content)
                lbl.setTextFormat(Qt.RichText)
                lbl.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
                lbl.setOpenExternalLinks(True)
                lbl.setWordWrap(True)
                lbl.setText(html)
                c_layout.addWidget(lbl)
                c_layout.addStretch()
                scroll.setWidget(content)
                card_layout.addWidget(scroll, 1)
                btn_row = QHBoxLayout()
                btn_row.addStretch()
                copy_btn = QPushButton("Copy Info", card)
                close_btn = QPushButton("Close", card)
                btn_row.addWidget(copy_btn)
                btn_row.addWidget(close_btn)
                card_layout.addLayout(btn_row)
                def _copy():
                        plain = textwrap.dedent(f"""Novic {app_version}\nPython: {py_ver}\nQt: {qt_ver}\nPlatform: {os_info}""").strip()
                        from PySide6.QtWidgets import QApplication
                        QApplication.clipboard().setText(plain)
                copy_btn.clicked.connect(_copy)
                close_btn.clicked.connect(dlg.close)
                outer.addWidget(card)
                dlg.exec()

    def _clear_recent(self):
        # TODO: implement clearing recent files list
        pass
