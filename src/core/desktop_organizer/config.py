"""
桌面文件整理器的配置文件
"""

import os
from pathlib import Path

# 获取项目根目录
PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

# 系统路径配置
DESKTOP_PATH = r"C:\Users\dell\Desktop"
SPRINT_PROJECTS_PATH = r"C:\Users\dell\Desktop\share\Syncdisk\sprintProjects"
SLOWBURN_PROJECTS_PATH = r"C:\Users\dell\Desktop\share\Syncdisk\SLowBurn"

# 输出路径配置
OUTPUT_PATH = PROJECT_ROOT / "scan_results"

# 排除的系统文件夹
EXCLUDE_FOLDERS = {
    "IMG",
    "TXT",
    "VIDEO",
    "MAYDAY",
    ".git",
    "__pycache__",
    "node_modules"
}

# 排除的文件类型
EXCLUDE_FILES = {
    ".lnk",  # 快捷方式
    "desktop.ini",
    ".DS_Store",
    "Thumbs.db"
}

# 文件类型映射
FILE_TYPES = {
    "图片": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"},
    "视频": {".mp4", ".mov", ".avi", ".mkv", ".wmv"},
    "文档": {".doc", ".docx", ".pdf", ".txt", ".md"},
    "演示": {".ppt", ".pptx"},
    "压缩": {".zip", ".rar", ".7z"}
}

# CLIP服务配置
CLIP_SERVICE = {
    "url": "http://localhost:5000",
    "endpoints": {
        "predict": "/predict",
        "similarity": "/similarity"
    }
}

# LLM服务配置
LLM_SERVICE = {
    "url": "http://localhost:2342",
    "model": "ollama"
}

# 日志配置
LOG_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
}
