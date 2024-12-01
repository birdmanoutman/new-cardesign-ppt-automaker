from PyQt6.QtWidgets import QWidget, QVBoxLayout

class BaseTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.init_ui()
    
    def init_ui(self):
        """初始化UI，子类需要实现这个方法"""
        raise NotImplementedError 