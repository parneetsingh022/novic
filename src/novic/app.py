from PySide6.QtWidgets import QApplication
from .ui.MainWindow import MainWindow


class NovicApplication:
    def __init__(self, argv):
        self.app = QApplication(argv)
        self.window = MainWindow()  # internal restore logic handles geometry

    def run(self):
        # Show after construction (restore_session already ran inside MainWindow)
        self.window.show()
        return self.app.exec()
