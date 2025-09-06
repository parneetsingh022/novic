from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from PySide6.QtWidgets import QMenuBar, QMenu
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt

ActionCallback = Callable[[], None]

@dataclass
class MenuAction:
    """Represents either a normal action, a separator, or a nested submenu.

    Use ``MenuAction.submenu(title, actions)`` to create a submenu.
    Use ``MenuAction.separator()`` to insert a separator line.
    """
    text: str
    callback: Optional[ActionCallback] = None
    shortcut: str | None = None
    checkable: bool = False
    checked: bool = False
    enabled: bool = True
    submenu_def: 'MenuDefinition | None' = None  # renamed to avoid clash with factory
    _separator: bool = False  # internal flag

    def build(self, parent) -> QAction | QMenu | None:
        if self._separator:
            return None  # handled by container
        if self.submenu_def:
            menu = QMenu(self.text, parent)
            self.submenu_def.build_into(menu)
            return menu
        act = QAction(self.text, parent)
        if self.shortcut:
            act.setShortcut(self.shortcut)
        if self.callback:
            act.triggered.connect(self.callback)  # type: ignore[arg-type]
        act.setEnabled(self.enabled)
        if self.checkable:
            act.setCheckable(True)
            act.setChecked(self.checked)
        return act

    # --- helpers ---
    @classmethod
    def separator(cls):
        return cls(text="--", _separator=True, enabled=False)

    @classmethod
    def submenu(cls, title: str, actions: List['MenuAction']):  # factory returning a submenu action
        return cls(text=title, submenu_def=MenuDefinition(title, actions))

@dataclass
class MenuDefinition:
    title: str
    actions: List[MenuAction] = field(default_factory=list)

    def build_into(self, menubar_or_menu: QMenuBar | QMenu):
        for item in self.actions:
            if item._separator:
                menubar_or_menu.addSeparator()
                continue
            built = item.build(menubar_or_menu)
            if built is None:
                continue
            if isinstance(built, QMenu):
                menubar_or_menu.addMenu(built)
            else:
                menubar_or_menu.addAction(built)

class TransparentMenuBar(QMenuBar):
    """MenuBar that forwards drags on empty space to parent title bar."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_pos = None

    def mousePressEvent(self, event):
        act = self.actionAt(event.pos())
        if act is None and event.button() == Qt.LeftButton and hasattr(self.parent(), "_start_external_drag"):
            self._drag_pos = event.globalPosition().toPoint()
            self.parent()._start_external_drag(self._drag_pos)  # type: ignore[attr-defined]
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.LeftButton and hasattr(self.parent(), "_continue_external_drag"):
            self.parent()._continue_external_drag(event.globalPosition().toPoint())  # type: ignore[attr-defined]
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

class MenuRegistry:
    """Registry to dynamically (re)build a QMenuBar from definitions."""
    def __init__(self):
        self._menus: list[MenuDefinition] = []

    def add_menu(self, menu: MenuDefinition):
        self._menus.append(menu)
        return self

    def clear(self):
        self._menus.clear()

    def build(self, parent) -> QMenuBar:
        bar = TransparentMenuBar(parent)
        bar.setNativeMenuBar(False)
        for m in self._menus:
            menu = bar.addMenu(m.title)
            m.build_into(menu)
        return bar

__all__ = [
    "MenuAction", "MenuDefinition", "MenuRegistry"
]
