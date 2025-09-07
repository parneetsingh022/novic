# ui/main_window.py
from PySide6.QtWidgets import (QTextEdit, QListWidget, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
                               QTreeView, QFileSystemModel, QSizePolicy, QSplitter, QFileIconProvider,
                               QDialog, QPushButton, QScrollArea, QFrame, QStackedWidget, QToolButton)
from pathlib import Path
from PySide6.QtGui import QIcon
from PySide6.QtCore import QDir, QSize, Qt, QObject, QEvent
from novic.core.menu_framework import MenuDefinition, MenuAction
from .sidebar import ActivitySidebar
from .footer import StatusFooter
from .tabbed_editor import TabbedEditor
from novic.ui.frameless import FramelessWindow

class MainWindow(FramelessWindow):
    def __init__(self):
        # Non-resizable and hide menu bar per request (menu still built for About action trigger)
        super().__init__(title="Novic", size=(900, 600), resizable=False, show_menu=True)
        self._register_default_menus()
        self._build_body()
        # restore previous session after UI widgets built
        self._restore_session()

    # --- menu definitions -------------------------------------------------
    def _register_default_menus(self):
        """Populate the menu registry and rebuild the menu bar."""
        file_menu = MenuDefinition(title="File", actions=[
            MenuAction("Save", self._file_save, shortcut="Ctrl+S"),
            MenuAction("Save As...", self._file_save_as, shortcut="Ctrl+Shift+S"),
            MenuAction.separator(),
            MenuAction("Close Folder", self._file_close_folder),
        ])
        edit_menu = MenuDefinition(title="Edit", actions=[
            MenuAction("Undo", self._edit_undo, shortcut="Ctrl+Z"),
            MenuAction("Redo", self._edit_redo, shortcut="Ctrl+Y"),
            MenuAction.separator(),
            MenuAction("Cut", self._edit_cut, shortcut="Ctrl+X"),
            MenuAction("Copy", self._edit_copy, shortcut="Ctrl+C"),
            MenuAction("Paste", self._edit_paste, shortcut="Ctrl+V"),
            MenuAction.separator(),
            MenuAction("Select All", self._edit_select_all, shortcut="Ctrl+A"),
        ])
        help_menu = MenuDefinition(title="Help", actions=[
            MenuAction("About Novic", self._about_dialog),
            MenuAction.separator(),
            MenuAction("View Logs", self._help_view_logs),
            MenuAction("Open Documentation", self._help_open_docs),
            MenuAction("Check for Updates", self._help_check_updates),
            MenuAction("Report Issue", self._help_report_issue),
            MenuAction.separator(),
            MenuAction("Keyboard Shortcuts", self._help_shortcuts, shortcut="Ctrl+K"),
        ])
        self.menu_registry.clear()
        self.menu_registry.add_menu(file_menu).add_menu(edit_menu).add_menu(help_menu)
        self.rebuild_menus()

    def _build_body(self):
        body = QWidget(self)
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0,0,0,0)
        body_layout.setSpacing(0)
        splitter = QSplitter(Qt.Horizontal, body)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(2)

        # Sidebar component
        self.sidebar = ActivitySidebar(splitter)
        splitter.addWidget(self.sidebar)
        # Tabbed editor component
        self.editors = TabbedEditor(splitter)
        splitter.addWidget(self.editors)
        splitter.setStretchFactor(0,0)
        splitter.setStretchFactor(1,1)
        splitter.setSizes([260, max(300, self.width()-260)])

        # Wire file activation from sidebar
        self.sidebar.fileActivated.connect(self._open_file_from_sidebar)

        # Hook sidebar show/hide to adjust splitter handle
        self._orig_handle_width = splitter.handleWidth()
        def _on_hide():
            sizes = splitter.sizes()
            if len(sizes) == 2:
                w = self.sidebar.nav_bar_width()
                splitter.setSizes([w, sizes[1]])
            splitter.setHandleWidth(0)
        def _on_show():
            splitter.setHandleWidth(self._orig_handle_width)
        self.sidebar.panelHidden.connect(_on_hide)
        self.sidebar.panelShown.connect(_on_show)

        splitter.setStyleSheet(
            "QSplitter::handle { background:#303234; }"
            "QSplitter::handle:horizontal:hover { background:#3a3d41; }"
        )
        body_layout.addWidget(splitter,1)

        # Footer component
        self.footer = StatusFooter(body)
        body_layout.addWidget(self.footer,0)
        self.add_content_widget(body)
        # ensure close event triggers session save
        self.installEventFilter(self)


    def _file_save(self):
        # TODO: implement save logic
        pass

    def _file_save_as(self):
        # TODO: implement save-as logic
        pass

    def _file_close_folder(self):
        if hasattr(self, 'sidebar'):
            try:
                self.sidebar.close_folder()
            except Exception:
                pass

    # --- help handlers ----------------------------------------------------
    def _help_view_logs(self):
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Logs", "Log viewer not implemented yet.")

    def _help_open_docs(self):
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl("https://example.com/novic/docs"))

    def _help_check_updates(self):
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Updates", "You're on the latest version (stub).")

    def _help_report_issue(self):
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl("https://example.com/novic/issues"))

    def _help_shortcuts(self):
        from PySide6.QtWidgets import QMessageBox
        shortcuts = (
            "Ctrl+S  Save\n"
            "Ctrl+Shift+S  Save As\n"
            "Ctrl+Z  Undo\n"
            "Ctrl+Y  Redo\n"
            "Ctrl+X  Cut\n"
            "Ctrl+C  Copy\n"
            "Ctrl+V  Paste\n"
            "Ctrl+A  Select All\n"
        )
        QMessageBox.information(self, "Keyboard Shortcuts", shortcuts)

    # --- file opening ------------------------------------------------------
    def _open_file_from_sidebar(self, path: str):
        if hasattr(self, 'editors'):
            self.editors.open_file(path)

    # --- edit actions (safe even if editor not yet built) -----------------
    def _editor(self):
        # return active QTextEdit within tabbed editor
        if hasattr(self, 'editors') and self.editors is not None:
            return self.editors.current_editor()
        return None

    def _edit_undo(self):
        e = self._editor();  e and e.undo()

    def _edit_redo(self):
        e = self._editor();  e and e.redo()

    def _edit_cut(self):
        e = self._editor();  e and e.cut()

    def _edit_copy(self):
        e = self._editor();  e and e.copy()

    def _edit_paste(self):
        e = self._editor();  e and e.paste()

    def _edit_select_all(self):
        e = self._editor();  e and e.selectAll()

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

    # --- session persistence -------------------------------------------
    def _session_file(self) -> Path:
        from pathlib import Path as _P
        return _P.home() / ".novic_session.json"

    def _gather_session(self) -> dict:
        data: dict[str, object] = {}
        try:
            data["explorer"] = self.sidebar.save_state()
        except Exception:
            data["explorer"] = {}
        try:
            data["tabs"] = self.editors.save_state()
        except Exception:
            data["tabs"] = {}
        return data

    def _restore_session(self):
        sf = self._session_file()
        if not sf.exists():
            return
        import json
        try:
            payload = json.loads(sf.read_text(encoding="utf-8"))
        except Exception:
            return
        if isinstance(payload, dict):
            try:
                self.sidebar.restore_state(payload.get("explorer", {}))
            except Exception:
                pass
            try:
                self.editors.restore_state(payload.get("tabs", {}))
            except Exception:
                pass

    def _save_session(self):
        sf = self._session_file()
        import json
        try:
            sf.write_text(json.dumps(self._gather_session(), indent=2), encoding="utf-8")
        except Exception:
            pass

    def eventFilter(self, obj: QObject, ev: QEvent):  # type: ignore[override]
        from PySide6.QtCore import QEvent as _QE
        if ev.type() == _QE.Close:
            self._save_session()
        return super().eventFilter(obj, ev)

    def closeEvent(self, event):  # type: ignore[override]
        # Fallback: ensure session saved even if eventFilter missed
        try:
            self._save_session()
        except Exception:
            pass
        super().closeEvent(event)
