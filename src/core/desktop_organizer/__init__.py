"""
桌面文件整理器
用于自动整理桌面文件，结合CLIP视觉分析和LLM服务
"""

from .scanner import FileScanner
from .info_package import InfoPackage
from .organizer import Organizer

__version__ = "0.1.0"
