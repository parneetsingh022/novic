
from PySide6.QtWidgets import QLabel, QMainWindow
from PySide6.QtCore import Qt


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Novic - Hello Example")

        # Central widget
        label = QLabel("Hello, PySide6!", self)
        label.setAlignment(Qt.AlignCenter)

        # Set QLabel as the central widget of the main window
        self.setCentralWidget(label)
