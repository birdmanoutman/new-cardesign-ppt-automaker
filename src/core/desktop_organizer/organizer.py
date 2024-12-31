"""
文件整理器
负责根据扫描结果执行文件整理操作
"""

import shutil
from pathlib import Path
import logging
from typing import Dict, List, Optional
from datetime import datetime
from . import config
from .info_package import InfoPackage

class Organizer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.desktop_path = Path(config.DESKTOP_PATH)
        self.sprint_projects_path = Path(config.SPRINT_PROJECTS_PATH)
        self.slowburn_projects_path = Path(config.SLOWBURN_PROJECTS_PATH)

    def organize(self, info_package: InfoPackage) -> Dict:
        """执行文件整理"""
        self.logger.info("开始整理文件")
        result = {
            "成功": [],
            "失败": [],
            "跳过": []
        }

        try:
            # 整理文件
            for category, files in info_package.get_files().items():
                for file_info in files:
                    try:
                        if category == "临时文件夹":
                            self._organize_temp_folder(file_info, result)
                        else:
                            self._organize_file(category, file_info, result)
                    except Exception as e:
                        self.logger.error(f"整理文件失败 {file_info.get('路径', '未知')}: {str(e)}")
                        result["失败"].append({
                            "路径": file_info.get("路径", "未知"),
                            "错误": str(e)
                        })

            return result

        except Exception as e:
            self.logger.error(f"整理过程出错: {str(e)}")
            raise

    def _organize_file(self, category: str, file_info: Dict, result: Dict):
        """整理单个文件"""
        source_path = Path(file_info["路径"])
        if not source_path.exists():
            result["失败"].append({
                "路径": str(source_path),
                "错误": "文件不存在"
            })
            return

        # 根据文件类型和CLIP分析结果决定目标位置
        target_path = self._determine_target_path(category, file_info)
        if not target_path:
            result["跳过"].append({
                "路径": str(source_path),
                "原因": "无法确定目标位置"
            })
            return

        # 确保目标目录存在
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # 如果目标文件已存在，添加时间戳
        if target_path.exists():
            stem = target_path.stem
            suffix = target_path.suffix
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target_path = target_path.with_name(f"{stem}_{timestamp}{suffix}")

        try:
            # 移动文件
            shutil.move(str(source_path), str(target_path))
            result["成功"].append({
                "源路径": str(source_path),
                "目标路径": str(target_path)
            })
        except Exception as e:
            result["失败"].append({
                "路径": str(source_path),
                "错误": str(e)
            })

    def _organize_temp_folder(self, folder_info: Dict, result: Dict):
        """整理临时文件夹"""
        folder_path = Path(folder_info["路径"])
        if not folder_path.exists():
            result["失败"].append({
                "路径": str(folder_path),
                "错误": "文件夹不存在"
            })
            return

        # 根据文件夹内容决定目标位置
        target_path = self._determine_folder_target(folder_info)
        if not target_path:
            result["跳过"].append({
                "路径": str(folder_path),
                "原因": "无法确定目标位置"
            })
            return

        # 确保目标目录存在
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # 如果目标文件夹已存在，添加时间戳
        if target_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target_path = target_path.with_name(f"{target_path.name}_{timestamp}")

        try:
            # 移动文件夹
            shutil.move(str(folder_path), str(target_path))
            result["成功"].append({
                "源路径": str(folder_path),
                "目标路径": str(target_path)
            })
        except Exception as e:
            result["失败"].append({
                "路径": str(folder_path),
                "错误": str(e)
            })

    def _determine_target_path(self, category: str, file_info: Dict) -> Optional[Path]:
        """确定文件的目标路径"""
        # TODO: 实现基于CLIP分析和文件特征的智能路径决策
        # 当前使用简单的类型分类
        if category == "图片文件":
            return self.sprint_projects_path / "图片资源" / file_info["文件名"]
        elif category == "视频文件":
            return self.sprint_projects_path / "视频资源" / file_info["文件名"]
        elif category == "文档文件":
            return self.sprint_projects_path / "文档资源" / file_info["文件名"]
        elif category == "演示文件":
            return self.sprint_projects_path / "演示资源" / file_info["文件名"]
        return None

    def _determine_folder_target(self, folder_info: Dict) -> Optional[Path]:
        """确定文件夹的目标路径"""
        # TODO: 实现基于文件夹内容和特征的智能路径决策
        # 当前简单返回临时文件夹路径
        return self.slowburn_projects_path / folder_info["文件夹名"]
