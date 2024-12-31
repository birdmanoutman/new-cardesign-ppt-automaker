"""
文件扫描器
负责扫描桌面文件和项目结构，并进行初步分析
"""

import os
from pathlib import Path
import logging
from datetime import datetime
import requests
from typing import Dict, List, Set, Optional
from . import config
from .video_analyzer import VideoAnalyzer
from .info_package import InfoPackage
import json

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileScanner:
    """文件扫描器"""
    
    def __init__(self):
        """初始化扫描器"""
        self.logger = logger
        self.desktop_path = Path(config.DESKTOP_PATH)
        self.sprint_projects_path = Path(config.SPRINT_PROJECTS_PATH)
        self.slowburn_projects_path = Path(config.SLOWBURN_PROJECTS_PATH)
        self.video_analyzer = VideoAnalyzer()
        self.info_package = InfoPackage()

    def scan_desktop(self) -> Dict:
        """扫描桌面文件"""
        self.logger.info("开始扫描桌面文件")
        
        try:
            for item in self.desktop_path.iterdir():
                # 跳过排除的文件和文件夹
                if self._should_exclude(item):
                    continue

                if item.is_file():
                    file_info = self._get_file_info(item)
                    if file_info:
                        category = self._get_file_category(item)
                        # 对于图片和视频文件，立即进行CLIP分析
                        if category == "图片":
                            clip_result = self._analyze_with_clip(file_info["路径"])
                            if clip_result:
                                file_info["CLIP分析"] = clip_result
                        elif category == "视频":
                            clip_result = self._analyze_video_with_clip(file_info["路径"])
                            if clip_result:
                                file_info["CLIP分析"] = clip_result
                        self.info_package.add_file(category, file_info)
                
                elif item.is_dir():
                    if self._is_temp_folder(item):
                        folder_info = self._get_folder_info(item)
                        self.info_package.add_file("临时文件夹", folder_info)

            return self.info_package.get_files()

        except Exception as e:
            self.logger.error(f"扫描桌面文件时出错: {str(e)}")
            raise

    def scan_projects(self) -> Dict:
        """扫描项目结构"""
        self.logger.info("开始扫描项目结构")
        
        try:
            # 扫描sprint项目
            if self.sprint_projects_path.exists():
                for project in self.sprint_projects_path.iterdir():
                    if project.is_dir() and not self._should_exclude(project):
                        project_info = self._get_project_info(project)
                        self.info_package.add_project("sprint项目", project_info)

            # 扫描slowburn项目
            if self.slowburn_projects_path.exists():
                for project in self.slowburn_projects_path.iterdir():
                    if project.is_dir() and not self._should_exclude(project):
                        project_info = self._get_project_info(project, detailed=False)
                        self.info_package.add_project("slowburn项目", project_info)

            return self.info_package.get_projects()

        except Exception as e:
            self.logger.error(f"扫描项目结构时出错: {str(e)}")
            raise

    def _should_exclude(self, path: Path) -> bool:
        """判断是否应该排除该路径"""
        if path.is_file():
            return path.name in config.EXCLUDE_FILES
        return path.name in config.EXCLUDE_FOLDERS

    def _get_file_info(self, file_path: Path) -> Optional[Dict]:
        """获取文件信息"""
        try:
            return {
                "文件名": file_path.name,
                "类型": file_path.suffix.lower(),
                "修改时间": datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "大小": file_path.stat().st_size,
                "路径": str(file_path)
            }
        except Exception as e:
            self.logger.error(f"获取文件信息时出错 {file_path}: {str(e)}")
            return None

    def _get_folder_info(self, folder_path: Path) -> Dict:
        """获取文件夹信息"""
        files = []
        try:
            for item in folder_path.iterdir():
                if item.is_file() and not self._should_exclude(item):
                    files.append(item.name)
            
            return {
                "文件夹名": folder_path.name,
                "文件列表": files,
                "最近修改": datetime.fromtimestamp(folder_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "路径": str(folder_path)  # 添加路径信息
            }
        except Exception as e:
            self.logger.error(f"获取文件夹信息时出错 {folder_path}: {str(e)}")
            return {
                "文件夹名": folder_path.name,
                "文件列表": [],
                "最近修改": datetime.fromtimestamp(folder_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "路径": str(folder_path)  # 添加路径信息
            }

    def _get_project_info(self, project_path: Path, detailed: bool = True) -> Dict:
        """获取项目信息"""
        try:
            info = {
                "项目名": project_path.name,
                "路径": str(project_path),
                "最近修改": datetime.fromtimestamp(project_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            }
            
            if detailed:
                subfolders = []
                for item in project_path.iterdir():
                    if item.is_dir() and not self._should_exclude(item):
                        subfolders.append(item.name)
                info["子文件夹"] = subfolders

            return info
        except Exception as e:
            self.logger.error(f"获取项目信息时出错 {project_path}: {str(e)}")
            return {
                "项目名": project_path.name,
                "路径": str(project_path),
                "最近修改": datetime.fromtimestamp(project_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            }

    def _get_file_category(self, file_path: Path) -> str:
        """获取文件类型"""
        suffix = file_path.suffix.lower()
        for category, extensions in config.FILE_TYPES.items():
            if suffix in extensions:
                return category
        return "其他"

    def _is_temp_folder(self, folder_path: Path) -> bool:
        """判断是否为临时文件夹"""
        name = folder_path.name.lower()
        return (
            name.startswith("新建文件夹") or
            name.startswith("untitled") or
            name.startswith("20") or  # 以日期开头
            "临时" in name or
            "temp" in name
        )

    def _analyze_with_clip(self, file_path: str) -> Optional[Dict]:
        """使用CLIP服务分析图片"""
        try:
            if not Path(file_path).exists():
                return None
                
            with open(file_path, 'rb') as f:
                files = {
                    'image': ('image.jpg', f, 'image/jpeg')
                }
                response = requests.post(
                    f"{config.CLIP_SERVICE['url']}{config.CLIP_SERVICE['endpoints']['predict']}", 
                    files=files
                )
                response.raise_for_status()
                return {"标签": [tag["tag"] for tag in response.json()]}
        except Exception as e:
            self.logger.error(f"CLIP分析失败: {str(e)}")
            return None

    def _analyze_video_with_clip(self, video_path: str) -> Optional[Dict]:
        """使用CLIP服务分析视频的关键帧"""
        return self.video_analyzer.analyze_video(video_path)

    def save_info_package(self, output_path: str) -> Path:
        """保存信息包到文件
        
        Args:
            output_path: 输出文件路径，如果是目录，将自动生成文件名
            
        Returns:
            保存的文件路径
        """
        output_path = Path(output_path)
        
        # 如果是目录，生成文件名
        if output_path.is_dir():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = output_path / f"scan_result_{timestamp}.json"
        
        # 确保父目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存信息包
        with open(output_path, "w", encoding="utf-8-sig") as f:
            json.dump(self.info_package.to_dict(), f, ensure_ascii=False, indent=2)
            
        return output_path
