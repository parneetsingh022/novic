from PySide6.QtWidgets import QTextEdit

class CodeEditor(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Start typing...")
        self.setStyleSheet("QTextEdit { background:#1f2123; color:#e3e5e8; border:none; padding:6px; }")

__all__ = ["CodeEditor"]
