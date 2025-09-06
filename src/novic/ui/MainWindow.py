# ui/main_window.py
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTextEdit
from PySide6.QtCore import Qt
from novic.core.title_bar import TitleBar
from novic.core.menu_framework import MenuRegistry, MenuDefinition, MenuAction

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Novic")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.resize(900, 600)  # give it a starting size

        # central container + vertical layout
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # custom title bar (make sure TitleBar sets a fixed height)
        self.title_bar = TitleBar(self)
        layout.addWidget(self.title_bar)

        # Menus integrated directly into title bar
        self.menu_registry = MenuRegistry()
        self._register_default_menus()
        self.title_bar.attach_menus(self.menu_registry)

        # content below menus (placeholder editor)
        self.editor = QTextEdit(self)
        self.editor.setPlaceholderText("Hello, Novic!")
        layout.addWidget(self.editor)

        # IMPORTANT: attach central widget to the window
        self.setCentralWidget(central)

    # --- menu setup ---
    def _register_default_menus(self):
        self.menu_registry.add_menu(MenuDefinition(
            "File",
            actions=[
                MenuAction("New", callback=self._file_new, shortcut="Ctrl+N"),
                MenuAction("Open...", callback=self._file_open, shortcut="Ctrl+O"),
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

    def _file_save(self):
        # TODO: implement save logic
        pass

    def _file_save_as(self):
        # TODO: implement save-as logic
        pass

    def _about_dialog(self):
        # TODO: implement about dialog (QMessageBox)
        pass
