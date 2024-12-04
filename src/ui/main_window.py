from PyQt6.QtWidgets import QMainWindow, QTabWidget, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt
from .tabs import FileTab, PPTTab, ImageDBTab
from ..core import file_manager, ppt_processor

class MainWindow(QMainWindow):
    """主窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("汽车设计效率工具")
        self.resize(1200, 800)
        
        # 创建中心部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 创建主布局
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        
        # 初始化核心组件
        self.file_manager = file_manager.FileManager()
        self.ppt_processor = ppt_processor.PPTProcessor()
        
        # 初始化UI
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        # 创建标签页
        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)
        
        # 添加各个标签页
        self.file_tab = FileTab(self.file_manager)
        self.ppt_tab = PPTTab(self.ppt_processor)
        self.image_tab = ImageDBTab(self.ppt_processor)
        
        self.tab_widget.addTab(self.file_tab, "文件名标准化")
        self.tab_widget.addTab(self.ppt_tab, "PPT快捷操作")
        self.tab_widget.addTab(self.image_tab, "PPT图片数据库")
        
        # 设置窗口样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background: white;
                margin: 0px;
            }
            QTabWidget::tab-bar {
                left: 5px;
            }
            QTabBar::tab {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #f6f7fa, stop: 1 #dadbde);
                border: 1px solid #C4C4C3;
                border-bottom-color: #C2C7CB;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                min-width: 8ex;
                padding: 8px;
            }
            QTabBar::tab:selected {
                background: white;
                border-color: #9B9B9B;
                border-bottom-color: white;
            }
            QTabBar::tab:!selected {
                margin-top: 2px;
            }
            QWidget {
                font-size: 12px;
            }
        """)

    def closeEvent(self, event):
        """窗口关闭事件"""
        # 清理资源
        if hasattr(self, 'file_tab'):
            self.file_tab.close()
        if hasattr(self, 'ppt_tab'):
            self.ppt_tab.close()
        if hasattr(self, 'image_tab'):
            self.image_tab.close()
        event.accept()