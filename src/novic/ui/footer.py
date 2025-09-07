from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel

class StatusFooter(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(18)
        self.setStyleSheet("background:#2b2d30; border-top:1px solid #3a3d41;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8,0,8,0)
        layout.setSpacing(12)
        self.label = QLabel("Ready", self)
        self.label.setStyleSheet("color:#8d949a; font-size:10px;")
        layout.addWidget(self.label)
        layout.addStretch()

    def set_status(self, text: str):
        self.label.setText(text)

__all__ = ["StatusFooter"]
