from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QTableWidget, QHeaderView, QTabWidget
)
from .tabs.file_tab import FileTab
from .tabs.ppt_tab import PPTTab
from .tabs.image_db_tab import ImageDBTab
from ..core import file_manager, ppt_processor

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("汽车设计效率工具")
        self.setMinimumSize(1000, 700)
        
        # 初始化核心组件
        self.file_manager = file_manager.FileManager()
        self.ppt_processor = ppt_processor.PPTProcessor()
        
        # 创建中心部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 创建主布局
        layout = QVBoxLayout(self.central_widget)
        
        # 创建标签页
        self.tabs = QTabWidget()
        
        # 添加各个标签页
        self.file_tab = FileTab(self.file_manager)
        self.ppt_tab = PPTTab(self.ppt_processor)
        self.image_tab = ImageDBTab(self.ppt_processor)
        
        self.tabs.addTab(self.file_tab, "文件名标准化")
        self.tabs.addTab(self.ppt_tab, "PPT快捷操作")
        self.tabs.addTab(self.image_tab, "PPT图片数据库")
        
        layout.addWidget(self.tabs)