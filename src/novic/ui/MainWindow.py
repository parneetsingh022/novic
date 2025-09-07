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
        # Window now resizable; user can drag edges/corners (frameless custom logic)
        super().__init__(title="Novic", size=(900, 600), resizable=True, show_menu=True)
        self._last_normal_size = self.size()
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

        # Main horizontal splitter (sidebar | editors) kept as attribute for persistence
        splitter = QSplitter(Qt.Horizontal, body)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(2)
        self.splitter = splitter  # store for later session persistence (sizes)

        # Sidebar component
        self.sidebar = ActivitySidebar(splitter)
        splitter.addWidget(self.sidebar)
        # Tabbed editor component
        self.editors = TabbedEditor(splitter)
        splitter.addWidget(self.editors)
        splitter.setStretchFactor(0,0)
        splitter.setStretchFactor(1,1)
        # Initial default sizes (will be overridden by session restore if present)
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
        # Window size (width & height) + maximized state
        try:
            sz = self.size()
            win_state: dict[str, object] = {}
            if self.isMaximized():
                win_state["maximized"] = True
                # store current size for reference plus last known normal size
                win_state["width"] = int(sz.width())
                win_state["height"] = int(sz.height())
                try:
                    normal_sz = getattr(self, "_last_normal_size", None)
                    if normal_sz is not None:
                        win_state["normal_width"] = int(normal_sz.width())
                        win_state["normal_height"] = int(normal_sz.height())
                    else:
                        ng = self.normalGeometry()
                        win_state["normal_width"] = int(ng.width())
                        win_state["normal_height"] = int(ng.height())
                except Exception:
                    pass
            else:
                win_state["maximized"] = False
                win_state["width"] = int(sz.width())
                win_state["height"] = int(sz.height())
            data["window"] = win_state
        except Exception:
            pass
        # Raw geometry blob (fallback) encoded base64
        try:
            from PySide6.QtCore import QByteArray
            geo = self.saveGeometry()
            if isinstance(geo, QByteArray):
                data["geometry"] = bytes(geo.toBase64()).decode("ascii")
        except Exception:
            pass
        # Splitter sizes (sidebar width, editor width)
        try:
            if hasattr(self, 'splitter'):
                data["splitter"] = list(self.splitter.sizes())  # type: ignore[attr-defined]
        except Exception:
            pass
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
            # Restore window size first (so child layouts adapt before restoring child state)
            try:
                win = payload.get("window", {})
                if isinstance(win, dict):
                    maximized = bool(win.get("maximized", False))
                    target_w = int(win.get("normal_width", win.get("width", 0)) or 0)
                    target_h = int(win.get("normal_height", win.get("height", 0)) or 0)
                    target_x = win.get("normal_x", win.get("x", None))
                    target_y = win.get("normal_y", win.get("y", None))
                    self._requested_restore = {  # type: ignore[attr-defined]
                        "maximized": maximized,
                        "width": target_w,
                        "height": target_h,
                        "x": target_x,
                        "y": target_y,
                    }
                    applied_geo = False
                    try:
                        geo_enc = payload.get("geometry")
                        if isinstance(geo_enc, str) and geo_enc:
                            from PySide6.QtCore import QByteArray
                            ba = QByteArray.fromBase64(geo_enc.encode("ascii"))
                            if ba and self.restoreGeometry(ba):
                                applied_geo = True
                                print(f"[SessionDebug] restore: applied geometry blob (maximized={maximized})")
                    except Exception:
                        applied_geo = False
                    if not applied_geo:
                        if target_w > 200 and target_h > 150:
                            self.resize(target_w, target_h)
                        if isinstance(target_x, int) and isinstance(target_y, int):
                            try:
                                self.move(int(target_x), int(target_y))
                            except Exception:
                                pass
                        print(f"[SessionDebug] restore: manual size={target_w}x{target_h} pos={target_x},{target_y} maximized={maximized}")
                    try:
                        if not maximized:
                            self._last_normal_size = self.size()
                        else:
                            from PySide6.QtCore import QSize
                            w_ref = target_w if target_w > 0 else self.width()
                            h_ref = target_h if target_h > 0 else self.height()
                            self._last_normal_size = QSize(w_ref, h_ref)
                    except Exception:
                        pass
                    if maximized:
                        from PySide6.QtCore import QTimer
                        QTimer.singleShot(0, lambda: (print("[SessionDebug] restore: showMaximized"), self.showMaximized()))
            except Exception:
                pass
            try:
                self.sidebar.restore_state(payload.get("explorer", {}))
            except Exception:
                pass
            try:
                self.editors.restore_state(payload.get("tabs", {}))
            except Exception:
                pass
            # Restore splitter sizes after sidebar + tabs so counts are known
            try:
                sp = payload.get("splitter")
                if isinstance(sp, list) and len(sp) == 2 and all(isinstance(v, int) and v > 0 for v in sp):
                    if hasattr(self, 'splitter'):
                        self.splitter.setSizes(sp)  # type: ignore[attr-defined]
            except Exception:
                pass

    def _save_session(self):
        sf = self._session_file()
        import json
        try:
            payload = self._gather_session()
            # Debug print of window sizing info before writing
            try:
                sz = self.size()
                ln = getattr(self, "_last_normal_size", None)
                ln_txt = f"{ln.width()}x{ln.height()}" if ln is not None else "?"
                print(f"[SessionDebug] closing size={sz.width()}x{sz.height()} maximized={self.isMaximized()} last_normal={ln_txt}")
            except Exception:
                pass
            sf.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            self._session_saved = True  # type: ignore[attr-defined]
        except Exception:
            pass

    def eventFilter(self, obj: QObject, ev: QEvent):  # type: ignore[override]
        from PySide6.QtCore import QEvent as _QE
        if ev.type() == _QE.Close:
            if not getattr(self, "_session_saved", False):
                self._save_session()
        return super().eventFilter(obj, ev)

    def closeEvent(self, event):  # type: ignore[override]
        # Fallback: ensure session saved even if eventFilter missed
        try:
            if not getattr(self, "_session_saved", False):
                self._save_session()
        except Exception:
            pass
        super().closeEvent(event)

    def resizeEvent(self, event):  # type: ignore[override]
        # Track last non-maximized size so we can restore accurately
        try:
            if not self.isMaximized() and not self.isMinimized():
                self._last_normal_size = event.size()
        except Exception:
            pass
        return super().resizeEvent(event)

    def showEvent(self, event):  # type: ignore[override]
        super().showEvent(event)
        # Enforce restored size after first show if layout compressed us
        try:
            if getattr(self, "_requested_restore", None) and not getattr(self, "_post_show_restored", False):
                req = self._requested_restore  # type: ignore
                if not req.get("maximized"):
                    w = req.get("width")
                    h = req.get("height")
                    x = req.get("x")
                    y = req.get("y")
                    from PySide6.QtCore import QTimer
                    def _apply_final():
                        changed = False
                        if isinstance(w, int) and isinstance(h, int) and w > 0 and h > 0:
                            if self.width() != w or self.height() != h:
                                self.resize(w, h)
                                changed = True
                        if isinstance(x, int) and isinstance(y, int):
                            if self.x() != x or self.y() != y:
                                self.move(x, y)
                                changed = True
                        print(f"[SessionDebug] post-show enforce target={w}x{h} actual={self.width()}x{self.height()} changed={changed}")
                    QTimer.singleShot(0, _apply_final)
                self._post_show_restored = True  # type: ignore[attr-defined]
        except Exception:
            pass
