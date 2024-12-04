from PyQt6.QtWidgets import QWidget, QDialog, QTableWidgetItem, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer
from ..base_tab import BaseTab
from .ui import ImageDBUI
from .handlers import ImageDBHandlers

class ImageDBTab(BaseTab):
    """图片数据库标签页"""
    def __init__(self, ppt_processor, parent=None):
        self.ppt_processor = ppt_processor
        # 初始化UI组件
        self.ui = ImageDBUI()
        super().__init__(parent)
        
        # 初始化事件处理器
        self.handlers = ImageDBHandlers(self, self.ui, ppt_processor)
        
        # 连接信号
        self._connect_signals()
        
        # 初始化完成后加载数据
        QTimer.singleShot(100, self.handlers.load_database_state)

    def init_ui(self):
        """实现基类的init_ui方法"""
        # 设置UI组件
        self.ui.setup_ui(self)

    def _connect_signals(self):
        """连接信号到处理函数"""
        components = self.ui.get_components()
        
        # 源管理按钮
        components['add_source_btn'].clicked.connect(self.handlers._add_ppt_source)
        components['remove_source_btn'].clicked.connect(self.handlers._remove_ppt_source)
        components['scan_source_btn'].clicked.connect(self.handlers._scan_ppt_source)
        
        # 图片库设置
        components['image_lib_browse_btn'].clicked.connect(self.handlers._browse_image_lib)
        components['extract_btn'].clicked.connect(self.handlers._extract_and_index)
        components['rebuild_db_btn'].clicked.connect(self.handlers._rebuild_database)
        
        # 标签管理
        components['tag_manage_btn'].clicked.connect(self.handlers._show_tag_manager)
        components['batch_tag_btn'].clicked.connect(self.handlers._batch_process_tags)

    def closeEvent(self, event):
        """窗口关闭事件"""
        try:
            # 清理资源
            if hasattr(self, 'handlers'):
                self.handlers.cleanup()  # 使用新的cleanup方法
        except Exception as e:
            print(f"关闭窗口时出错: {str(e)}")
        super().closeEvent(event)