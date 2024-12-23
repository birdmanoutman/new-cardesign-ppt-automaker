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
from typing import Dict, Optional, List, Union

from ...dialogs.tag_manager_dialog import TagManagerDialog
from .image_item import ImageItem
from ....core.services.image_service import ImageService
from ....core.services.tag_service import TagService
from .handlers_v2 import ImageDBHandlersV2

class ImageDBHandlers:
    """图片数据库处理器（兼容层）"""
    
    def __init__(self, tab, ui, ppt_processor=None, image_service: Optional[ImageService] = None,
                 tag_service: Optional[TagService] = None):
        self.logger = logging.getLogger(__name__)
        
        # V2 服务支持
        self._image_service = image_service
        self._tag_service = tag_service
        
        # V1 支持
        self._tab = tab
        self._ui = ui
        self._ppt_processor = ppt_processor
        
        # 创建适当的处理器实例
        if image_service is not None:
            # V2 模式
            self._handler = ImageDBHandlersV2(tab, ui, image_service, tag_service)
            self.logger.info("使用 V2 处理器")
        else:
            # V1 模式 - 保留原有代码
            self._handler = self  # 使用自身作为处理器
            self.tab = tab
            self.ui = ui
            self.ppt_processor = ppt_processor
            self.tag_manager = ppt_processor.get_image_processor().tag_manager if ppt_processor else None
            self.current_page = 0
            self.page_size = 1000
            self.is_loading = False
            self.has_more = True
            self.all_images = []
            self.loaded_images = set()
            self.cleanup_handlers = []
            self._connect_signals()
            self.logger.info("使用 V1 处理器")
    
    def __getattr__(self, name):
        """处理未找到的属性访问"""
        # 如果是 V2 模式，尝试从 V2 处理器获取
        if hasattr(self, '_handler') and self._handler is not self:
            return getattr(self._handler, name)
        raise AttributeError(f"'{self.__class__.__name__}' 对象没有属性 '{name}'")
    
    # 以下是原有的所有方法实现...
    # [保留原有的所有方法实现，完全不变]
    
    def _connect_signals(self):
        """连接信号到处理函数"""
        if self._handler is not self:
            return  # V2 模式下不需要这个
            
        components = self.ui.get_components()
        
        # 搜索和过滤
        components['image_search'].textChanged.connect(self._filter_images)
        components['tag_filter'].currentTextChanged.connect(self._filter_images)
        components['match_all_tags'].stateChanged.connect(self._filter_images)
        
        # 图片网格
        components['image_grid'].customContextMenuRequested.connect(self._show_image_context_menu)
        components['image_grid'].verticalScrollBar().valueChanged.connect(self._check_scroll_position)
    
    # ... [这里是原有代码的其余部分，保持不变] ...