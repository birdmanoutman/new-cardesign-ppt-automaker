from PyQt6.QtWidgets import (
    QMessageBox, QFileDialog, QProgressDialog, QMenu,
    QTableWidgetItem, QDialog, QApplication
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage
from pathlib import Path
import os
import io
from PIL import Image
import win32clipboard
import win32con
import logging
from typing import Dict, Optional, List, Callable

from ...dialogs.tag_manager_dialog import TagManagerDialog
from .image_item import ImageItem
from ....core.services.image_service import ImageService
from ....core.services.tag_service import TagService

class ImageDBHandlersV2:
    """图片数据库处理器 V2 版本"""
    
    def __init__(self, tab, ui, image_service: ImageService, tag_service: Optional[TagService] = None):
        # 保留原有的初始化
        self.tab = tab
        self.ui = ui
        self.current_page = 0
        self.page_size = 1000
        self.is_loading = False
        self.has_more = True
        self.all_images = []
        self.loaded_images = set()
        self.cleanup_handlers = []
        
        # 新服务
        self.image_service = image_service
        self.tag_service = tag_service
        self.logger = logging.getLogger(__name__)
        
        # 连接信号
        self._connect_signals()
    
    def _connect_signals(self):
        """连接信号到处理函数"""
        components = self.ui.get_components()
        
        # 保留原有的信号连接
        components['image_search'].textChanged.connect(self._filter_images)
        components['tag_filter'].currentTextChanged.connect(self._filter_images)
        components['match_all_tags'].stateChanged.connect(self._filter_images)
        components['image_grid'].customContextMenuRequested.connect(self._show_image_context_menu)
        components['image_grid'].verticalScrollBar().valueChanged.connect(self._check_scroll_position)
        
        # 新的信号连接
        if hasattr(self.ui, 'image_uploaded'):
            self.ui.image_uploaded.connect(self._on_image_uploaded)
        if hasattr(self.ui, 'search_requested'):
            self.ui.search_requested.connect(self._on_search_requested)
        if hasattr(self.ui, 'tagging_requested'):
            self.ui.tagging_requested.connect(self._on_tagging_requested)
    
    # 保留原有的方法
    def load_database_state(self):
        """加载数据库状态"""
        try:
            components = self.ui.get_components()
            
            # 使用新的服务加载数据
            stats = self.image_service.get_stats()
            components['db_status_label'].setText(
                f"数据库状态: {stats['total_images']} 张图片，"
                f"来自 {stats['total_ppts']} 个PPT"
            )
            
        except Exception as e:
            self.logger.error(f"加载数据库状态时出错: {str(e)}")
    
    # ... [保留其他原有方法，但使用新的服务实现] ...
    
    # 新增的异步方法
    async def process_image_tags(self, image_path: str) -> List[Dict]:
        """处理图片标签（异步）"""
        try:
            if self.tag_service is None:
                raise ValueError("标签服务未初始化")
            return await self.tag_service.get_image_tags(image_path)
        except Exception as e:
            self.logger.error(f"处理图片标签失败: {str(e)}")
            raise
    
    # 实现向后兼容的方法
    def handle_image_upload(self, image_path: str) -> str:
        """处理图片上传（兼容旧接口）"""
        try:
            return self.image_service.handle_new_image(image_path)
        except Exception as e:
            self.logger.error(f"上传图片失败: {str(e)}")
            QMessageBox.critical(None, "错误", f"上传图片��败: {str(e)}")
            raise
    
    def handle_image_search(self, criteria: Dict) -> List[Dict]:
        """处理图片搜索（兼容旧接口）"""
        try:
            return self.image_service.search_images(criteria)
        except Exception as e:
            self.logger.error(f"搜索图片失败: {str(e)}")
            QMessageBox.critical(None, "错误", f"搜索图片失败: {str(e)}")
            raise
    
    def cleanup(self):
        """清理资源"""
        try:
            # 停止加载
            self.is_loading = False
            
            # 清理图片缓存
            components = self.ui.get_components()
            if components.get('image_grid'):
                components['image_grid'].clear()
            self.loaded_images.clear()
            
            # 执行注册的清理处理器
            for handler in self.cleanup_handlers:
                try:
                    handler()
                except Exception as e:
                    self.logger.error(f"执行清理处理器时出错: {str(e)}")
            
            # 隐藏进度条
            if components.get('image_progress_bar'):
                components['image_progress_bar'].setVisible(False)
            
        except Exception as e:
            self.logger.error(f"清理资源时出错: {str(e)}")
    
    def add_cleanup_handler(self, handler: Callable[[], None]):
        """添加清理处理器"""
        self.cleanup_handlers.append(handler) 