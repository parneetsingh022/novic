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

        # Placeholder for menu bar (injected later)
        self.menu_bar = None  # type: QMenuBar | None

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

        self._apply_styles()

    # --- handlers ---
    def on_minimize(self):
        self.window().showMinimized()

    def on_maximize_restore(self):
        if self.window().isMaximized():
            self.window().showNormal()
            self.btn_max.setIcon(QIcon(str(self._icon_path("maximize.svg"))))
            self.btn_max.setToolTip("Maximize")
        else:
            self.window().showMaximized()
            self.btn_max.setIcon(QIcon(str(self._icon_path("restore.svg"))))
            self.btn_max.setToolTip("Restore")

    def on_close(self):
        self.window().close()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            diff = event.globalPosition().toPoint() - self._drag_pos
            self.window().move(self.window().pos() + diff)
            self._drag_pos = event.globalPosition().toPoint()

    # --- public API ---
    def attach_menus(self, registry):
        """Build and attach a menubar into the title bar (after title)."""
        if self.menu_bar:
            self.layout().removeWidget(self.menu_bar)
            self.menu_bar.deleteLater()
            self.menu_bar = None

        bar = registry.build(self)
        bar.setFixedHeight(24)
        bar.setStyleSheet("QMenuBar { background: transparent; }")
        # Insert right after logo (index 1 since only logo precedes)
        self.layout().insertWidget(1, bar)
        self.menu_bar = bar
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

    def _apply_styles(self):
        # use object names for fine-grained styling if needed later
        self.setStyleSheet(
            """
            /* Neutral grey dark theme */
            #TitleBar { background-color: #2b2d30; color: #e3e5e8; }
            QLabel#logo { background: transparent; }
            QMenuBar { background: transparent; padding: 0 8px; }
            QMenuBar::item { background: transparent; padding: 4px 6px; margin: 0 2px; border-radius:4px; }
            QMenuBar::item:selected { background: #3a3d41; }
            QMenuBar::item:pressed { background: #464a4f; }
            QMenu { 
                background: #2f3337; 
                color: #e3e5e8; 
                border: 1px solid #41464b; 
                border-radius: 6px; 
                padding: 6px 0; 
            }
            QMenu::separator { height:1px; background: #3e444a; margin:4px 8px; }
            QMenu::item { padding:6px 14px; border-radius:4px; }
            QMenu::item:selected { background:#3d444a; }
            QMenu::item:pressed { background:#464d53; }
            QPushButton { border: none; background: transparent; }
            QPushButton:hover { background: #3a3d41; }
            QPushButton:pressed { background: #464a4f; }
            QPushButton[role='close']:hover { background: #e74c3c; }
            QPushButton[role='close']:pressed { background: #c0392b; }
            """
        )
        self.btn_close.setProperty("role", "close")
        # re-polish to apply dynamic property styling
        self.btn_close.style().unpolish(self.btn_close)
        self.btn_close.style().polish(self.btn_close)

