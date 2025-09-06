# ui/main_window.py
from PySide6.QtWidgets import QTextEdit
from novic.core.menu_framework import MenuDefinition, MenuAction
from novic.ui.frameless import FramelessWindow

class MainWindow(FramelessWindow):
    def __init__(self):
        super().__init__(title="Novic", size=(900, 600))
        self.set_resizable(False)
        # populate menus
        self._register_default_menus()
        self.rebuild_menus()
        # editor content
        self.editor = self.add_content_widget(QTextEdit(self))
        self.editor.setPlaceholderText("Hello, Novic!")

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
