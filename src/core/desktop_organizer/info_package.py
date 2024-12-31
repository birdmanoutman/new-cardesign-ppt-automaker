"""
信息包模块
用于存储和处理文件信息
"""

from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
from . import config

class InfoPackage:
    def __init__(self):
        self.files: Dict[str, List[Dict]] = {
            "图片": [],
            "视频": [],
            "文档": [],
            "演示": [],
            "压缩": [],
            "临时文件夹": [],
            "其他": []
        }
        self.projects: Dict[str, List[Dict]] = {
            "sprint项目": [],
            "slowburn项目": []
        }
        self.timestamp = datetime.now()

    def add_file(self, category: str, file_info: Dict):
        """添加文件信息"""
        if category in self.files:
            self.files[category].append(file_info)
        else:
            self.files["其他"].append(file_info)

    def add_project(self, category: str, project_info: Dict):
        """添加项目信息"""
        if category in self.projects:
            self.projects[category].append(project_info)

    def get_files(self, category: Optional[str] = None) -> Dict:
        """获取文件信息"""
        if category:
            return self.files.get(category, [])
        return self.files

    def get_projects(self, category: Optional[str] = None) -> Dict:
        """获取项目信息"""
        if category:
            return self.projects.get(category, [])
        return self.projects

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "files": self.files,
            "projects": self.projects,
            "timestamp": self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'InfoPackage':
        """从字典创建实例"""
        instance = cls()
        instance.files = data.get("files", {})
        instance.projects = data.get("projects", {})
        instance.timestamp = datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat()))
        return instance
