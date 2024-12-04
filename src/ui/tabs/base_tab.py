from PyQt6.QtWidgets import QWidget, QVBoxLayout

class BaseTab(QWidget):
    """标签页基类"""
    def __init__(self, parent=None):
        super().__init__(parent)
        # 创建主布局
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(10)
        # 初始化UI
        self.init_ui()

    def init_ui(self):
        """初始化UI，子类需要实现此方法"""
        raise NotImplementedError("子类必须实现init_ui方法")