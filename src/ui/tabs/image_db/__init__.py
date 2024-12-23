"""图片数据库模块

此模块提供了图片数据库的UI和处理功能。
支持V1（原始版本）和V2（新版本）两种模式。
"""

from .tab import ImageDBTab
from .ui import ImageDBUI
from .handlers import ImageDBHandlers
from .handlers_v2 import ImageDBHandlersV2
from .image_item import ImageItem

__all__ = [
    'ImageDBTab',
    'ImageDBUI',
    'ImageDBHandlers',
    'ImageDBHandlersV2',
    'ImageItem'
]

# 版本信息
__version__ = '2.0.0'
__author__ = 'Your Name'
__description__ = '图片数据库模块 - 支持AI服务的新版本' 