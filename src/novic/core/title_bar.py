from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QHBoxLayout, QMenuBar
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap

try:
    # Optional import so title bar does not depend hard on menu framework
    from .menu_framework import MenuRegistry
except Exception:  # pragma: no cover - fallback if not present
    MenuRegistry = None  # type: ignore

class TitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)  # height of title bar
        self.setObjectName("TitleBar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 0)

        # Logo (text removed as requested)
        self.logo = QLabel(self)
        self.logo.setObjectName("logo")
        self.logo.setFixedSize(24, 24)
        self._set_logo_pixmap()
        layout.addWidget(self.logo)
        # right margin after logo for visual breathing room
        layout.addSpacing(8)

        # Placeholder for menu bar (injected later)
        self.menu_bar = None  # type: ignore

        layout.addStretch()

        icon_size = QSize(14, 14)

        def make_btn(svg_name, tooltip):
            btn = QPushButton(self)
            btn.setIcon(QIcon(str(self._icon_path(svg_name))))
            btn.setIconSize(icon_size)
            btn.setFixedSize(32, 24)
            btn.setToolTip(tooltip)
            btn.setFlat(True)
            btn.setCursor(Qt.PointingHandCursor)
            return btn

        self.btn_min = make_btn("minimize.svg", "Minimize")
        self.btn_min.clicked.connect(self.on_minimize)
        layout.addWidget(self.btn_min)

        self.btn_max = make_btn("maximize.svg", "Maximize")
        self.btn_max.clicked.connect(self.on_maximize_restore)
        layout.addWidget(self.btn_max)

        self.btn_close = make_btn("close.svg", "Close")
        self.btn_close.clicked.connect(self.on_close)
        layout.addWidget(self.btn_close)
        # track resizable (default True) and apply styling
        self._resizable = True
        self._apply_styles()

    # --- handlers ---
    def on_minimize(self):
        self.window().showMinimized()
    
    def on_maximize_restore(self):
        if not self._resizable:
            return  # ignore when non-resizable
        win = self.window()
        if win.isMaximized():
            win.showNormal()
            self.btn_max.setIcon(QIcon(str(self._icon_path("maximize.svg"))))
            self.btn_max.setToolTip("Maximize")
        else:
            win.showMaximized()
            self.btn_max.setIcon(QIcon(str(self._icon_path("restore.svg"))))
            self.btn_max.setToolTip("Restore")

    def on_close(self):
        self.window().close()
    # drag API used by TransparentMenuBar
    def _start_external_drag(self, global_pos):
        self._drag_pos = global_pos

    def _continue_external_drag(self, global_pos):
        diff = global_pos - self._drag_pos
        self.window().move(self.window().pos() + diff)
        self._drag_pos = global_pos

    # --- helpers ---
    def _icon_path(self, name: str):
        # relative to this file -> ../resources/icons
        import pathlib
        return (pathlib.Path(__file__).parent.parent / "resources" / "icons" / name).resolve()

    def _logo_path(self):
        return self._icon_path("novic_logo.png")

    def _set_logo_pixmap(self):
        path = self._logo_path()
        if not path.exists():
            # generate a simple placeholder pixmap with an "N"
            pm = QPixmap(24, 24)
            pm.fill(Qt.transparent)
            from PySide6.QtGui import QPainter, QColor, QFont
            p = QPainter(pm)
            p.setRenderHint(p.Antialiasing)
            # Transparent background, only draw letter
            p.setPen(QColor("#ecf0f1"))
            f = QFont()
            f.setBold(True)
            f.setPointSize(11)
            p.setFont(f)
            p.drawText(pm.rect(), Qt.AlignCenter, "N")
            p.end()
            self.logo.setPixmap(pm)
            return
        pm = QPixmap(str(path))
        if not pm.isNull():
            self.logo.setPixmap(pm.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        # styling handled centrally in _apply_styles

    def _apply_styles(self):
        arrow_path = self._icon_path("submenu_arrow.svg").as_posix()
        self.setStyleSheet(
            f"""
            /* Neutral grey dark theme */
            #TitleBar {{ background-color: #2b2d30; color: #e3e5e8; }}
            QLabel#logo {{ background: transparent; }}
            QMenuBar {{ background: transparent; padding: 0 8px; }}
            QMenuBar::item {{ background: transparent; padding: 4px 6px; margin: 0 2px; border-radius:4px; }}
            QMenuBar::item:selected {{ background: #3a3d41; }}
            QMenuBar::item:pressed {{ background: #464a4f; }}
            QMenuBar::item:disabled {{ color: #6d7277; background: transparent; }}
            QMenu {{ background: #2f3337; color: #e3e5e8; border: 1px solid #41464b; border-radius: 6px; padding: 0; }}
            QMenu::separator {{ height:1px; background: #3e444a; margin:4px 8px; }}
            QMenu::item {{ padding:6px 14px; margin:0; border-radius:4px; }}
            QMenu::item:selected {{ background:#3d444a; }}
            QMenu::item:pressed {{ background:#464d53; }}
            QMenu::item:disabled {{ color:#5d6369; background:transparent; }}
            QMenu::right-arrow {{ image: url('{arrow_path}'); width: 12px; height: 12px; }}
            QPushButton {{ border: none; background: transparent; }}
            QPushButton:hover {{ background: #3a3d41; }}
            QPushButton:pressed {{ background: #464a4f; }}
            QPushButton[role='close']:hover {{ background: #e74c3c; }}
            QPushButton[role='close']:pressed {{ background: #c0392b; }}
            """
        )
        self.btn_close.setProperty("role", "close")
        self.btn_close.style().unpolish(self.btn_close)
        self.btn_close.style().polish(self.btn_close)
    # (styling applied in _apply_styles)

    # --- public API ---
    def attach_menus(self, registry):
        """Build and attach a menubar into the title bar right after the logo.

        Accepts a MenuRegistry (or compatible object with build(parent)->QMenuBar).
        Rebuilds cleanly if already present.
        """
        if self.menu_bar:
            try:
                self.layout().removeWidget(self.menu_bar)
                self.menu_bar.deleteLater()
            except Exception:
                pass
            self.menu_bar = None
        if registry is None:
            return
        bar = registry.build(self)
        bar.setFixedHeight(24)
        bar.setStyleSheet("QMenuBar { background: transparent; }")
        # insert after logo + spacing (logo index 0, spacing index 1)
        self.layout().insertWidget(2, bar)
        self.menu_bar = bar

    def set_resizable(self, flag: bool):
        """Enable/disable maximize ability (UI only; window logic handled externally)."""
        self._resizable = flag
        # show/hide maximize button instead of disabled icon
        self.btn_max.setVisible(flag)
        self.btn_max.setEnabled(flag)
        if not flag and self.window().isMaximized():
            # restore if currently maximized to avoid stuck state
            try:
                self.window().showNormal()
                self.btn_max.setIcon(QIcon(str(self._icon_path("maximize.svg"))))
                self.btn_max.setToolTip("Maximize")
            except Exception:
                pass
        if flag:
            # ensure correct icon state when re-enabled
            if self.window().isMaximized():
                self.btn_max.setIcon(QIcon(str(self._icon_path("restore.svg"))))
                self.btn_max.setToolTip("Restore")
            else:
                self.btn_max.setIcon(QIcon(str(self._icon_path("maximize.svg"))))
                self.btn_max.setToolTip("Maximize")
        else:
            # keep last icon but hide button (already hidden); no tooltip change needed
            pass

    def mouseDoubleClickEvent(self, event):  # type: ignore
        # Standard title bar double-click to maximize/restore (only if resizable)
        if event.button() == Qt.LeftButton and self._resizable:
            self.on_maximize_restore()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


