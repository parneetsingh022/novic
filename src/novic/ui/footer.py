from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, QSize


class StatusFooter(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(18)
        self.setStyleSheet("background:#2b2d30; border-top:1px solid #3a3d41;")
        # Ensure footer stretches full width
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # Allow stylesheet background to paint entire widget
        self.setAttribute(Qt.WA_StyledBackground, True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(12)
        self.label = QLabel("Ready", self)
        self.label.setStyleSheet("color:#8d949a; font-size:10px;")
        layout.addWidget(self.label)
        layout.addStretch()

    def set_status(self, text: str):
        self.label.setText(text)

    def sizeHint(self):  # type: ignore[override]
        # Suggest expansive width while keeping fixed height
        pw = self.parent().width() if self.parent() else 600
        return QSize(pw, 18)

    def minimumSizeHint(self):  # type: ignore[override]
        return QSize(0, 18)


__all__ = ["StatusFooter"]
