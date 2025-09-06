from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from PySide6.QtCore import Qt, QRect, QPoint
from novic.core.title_bar import TitleBar
from novic.core.menu_framework import MenuRegistry

class FramelessWindow(QMainWindow):
    """Reusable frameless window with integrated custom TitleBar and MenuRegistry.

    Subclasses typically add their central content below the title bar.
    Provides helper to (re)attach menus after modifying registry.
    """
    def __init__(self, *, title: str = "", size=(900, 600), resizable: bool = True, show_menu: bool = True):
        super().__init__()
        if title:
            self.setWindowTitle(title)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.resize(*size)
        self._resizable = resizable
        self._show_menu = show_menu
        self._resize_margin = 6  # px grab area
        self._resizing = False
        self._resize_edge = None  # type: ignore

        # Layout scaffold
        self._central_container = QWidget(self)
        self._vbox = QVBoxLayout(self._central_container)
        self._vbox.setContentsMargins(0, 0, 0, 0)
        self._vbox.setSpacing(0)

        # Title bar
        self.title_bar = TitleBar(self)
        self.title_bar.setMouseTracking(True)
        self._vbox.addWidget(self.title_bar)
        if not self._show_menu:
            # ensure any attempt to rebuild menus yields nothing
            self.menu_registry = MenuRegistry()  # empty
        else:
            self.menu_registry = MenuRegistry()

        self.setCentralWidget(self._central_container)
        # enable passive mouse move events for hover edge detection
        self.setMouseTracking(True)
        self._central_container.setMouseTracking(True)

    # --- menu helpers ---
    def rebuild_menus(self):
        if not self._show_menu:
            # remove existing if present
            if getattr(self.title_bar, 'menu_bar', None):
                try:
                    self.title_bar.layout().removeWidget(self.title_bar.menu_bar)
                    self.title_bar.menu_bar.deleteLater()
                    self.title_bar.menu_bar = None
                except Exception:
                    pass
            return
        if hasattr(self.title_bar, 'attach_menus'):
            self.title_bar.attach_menus(self.menu_registry)

    # --- content helpers ---
    def add_content_widget(self, widget):
        self._vbox.addWidget(widget)
        return widget

    # --- configuration API ---
    def set_resizable(self, flag: bool):
        if self._resizable == flag:
            return
        self._resizable = flag
        # propagate to title bar button state
        if hasattr(self, 'title_bar') and hasattr(self.title_bar, 'set_resizable'):
            try:
                self.title_bar.set_resizable(flag)
            except Exception:
                pass

    def set_menu_visible(self, flag: bool):
        if self._show_menu == flag:
            return
        self._show_menu = flag
        self.rebuild_menus()

    # --- mouse events for manual resize ---
    def mousePressEvent(self, event):  # type: ignore
        if self._resizable and event.button() == Qt.LeftButton:
            edge = self._detect_edge(event.pos())
            if edge:
                self._resizing = True
                self._resize_edge = edge
                self._drag_origin_geom = self.geometry()
                self._drag_origin_pos = event.globalPosition().toPoint()
                # set appropriate resize cursor immediately
                self._apply_resize_cursor(edge)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):  # type: ignore
        if self._resizable and not self._resizing:
            edge = self._detect_edge(event.pos())
            if edge:
                cursors = {
                    'left': Qt.SizeHorCursor,
                    'right': Qt.SizeHorCursor,
                    'top': Qt.SizeVerCursor,
                    'bottom': Qt.SizeVerCursor,
                    'top-left': Qt.SizeFDiagCursor,
                    'bottom-right': Qt.SizeFDiagCursor,
                    'top-right': Qt.SizeBDiagCursor,
                    'bottom-left': Qt.SizeBDiagCursor,
                }
                self.setCursor(cursors.get(edge, Qt.ArrowCursor))
            else:
                self.setCursor(Qt.ArrowCursor)
        if self._resizing:
            # keep resize cursor while dragging
            if self._resize_edge:
                self._apply_resize_cursor(self._resize_edge)
            self._perform_resize(event.globalPosition().toPoint())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):  # type: ignore
        if self._resizing and event.button() == Qt.LeftButton:
            self._resizing = False
            self._resize_edge = None
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    # helper to map edge to cursor and apply
    def _apply_resize_cursor(self, edge: str):
        mapping = {
            'left': Qt.SizeHorCursor,
            'right': Qt.SizeHorCursor,
            'top': Qt.SizeVerCursor,
            'bottom': Qt.SizeVerCursor,
            'top-left': Qt.SizeFDiagCursor,
            'bottom-right': Qt.SizeFDiagCursor,
            'top-right': Qt.SizeBDiagCursor,
            'bottom-left': Qt.SizeBDiagCursor,
        }
        self.setCursor(mapping.get(edge, Qt.ArrowCursor))

    # --- internal resize helpers ---
    def _detect_edge(self, pos: QPoint):
        m = self._resize_margin
        r = self.rect()
        left = pos.x() <= m
        right = pos.x() >= r.width() - m
        top = pos.y() <= m
        bottom = pos.y() >= r.height() - m
        if top and left:
            return 'top-left'
        if top and right:
            return 'top-right'
        if bottom and left:
            return 'bottom-left'
        if bottom and right:
            return 'bottom-right'
        if left:
            return 'left'
        if right:
            return 'right'
        if top:
            return 'top'
        if bottom:
            return 'bottom'
        return None

    def _perform_resize(self, global_pos):
        if not self._resize_edge:
            return
        geom: QRect = self._drag_origin_geom
        delta = global_pos - self._drag_origin_pos
        min_w = 300
        min_h = 200
        x = geom.x()
        y = geom.y()
        w = geom.width()
        h = geom.height()
        if 'right' in self._resize_edge:
            w = max(min_w, geom.width() + delta.x())
        if 'bottom' in self._resize_edge:
            h = max(min_h, geom.height() + delta.y())
        if 'left' in self._resize_edge:
            new_w = max(min_w, geom.width() - delta.x())
            x = geom.right() - new_w + 1
            w = new_w
        if 'top' in self._resize_edge:
            new_h = max(min_h, geom.height() - delta.y())
            y = geom.bottom() - new_h + 1
            h = new_h
        self.setGeometry(QRect(x, y, w, h))

__all__ = ["FramelessWindow"]
