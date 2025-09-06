from PySide6.QtWidgets import QApplication
from .ui.MainWindow import MainWindow

class NovicApplication:
    def __init__(self, argv):
        self.app = QApplication(argv)
        self.window = MainWindow()
        self.window.resize(800,600)


    def run(self):
        self.window.show()
        return self.app.exec()
