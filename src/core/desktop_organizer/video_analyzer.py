"""
视频分析模块
负责视频关键帧提取和CLIP分析
"""

import cv2
import numpy as np
import tempfile
from pathlib import Path
import logging
import requests
from typing import Dict, List, Optional
from . import config

class VideoAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # 确保OpenCV正确加载
        try:
            cv2.__version__
        except Exception as e:
            self.logger.error(f"OpenCV加载失败: {str(e)}")
            raise ImportError("OpenCV加载失败，请检查依赖安装")

    def analyze_video(self, video_path: str) -> Optional[Dict]:
        """分析视频关键帧"""
        try:
            frames = self._extract_keyframes(video_path)
            if not frames:
                return None

            result = {
                "关键帧标签": {
                    "开始": [],
                    "中间": [],
                    "结束": []
                }
            }

            # 分析每个关键帧
            for position, frame in frames.items():
                tags = self._analyze_frame_with_clip(frame)
                if tags:
                    result["关键帧标签"][position] = tags

            return result

        except Exception as e:
            self.logger.error(f"视频分析出错 {video_path}: {str(e)}")
            return None

    def _extract_keyframes(self, video_path: str) -> Optional[Dict[str, str]]:
        """提取视频关键帧
        返回: Dict[位置, 临时文件路径]
        """
        try:
            if not Path(video_path).exists():
                raise FileNotFoundError(f"视频文件不存在: {video_path}")

            cap = cv2.VideoCapture(str(video_path))  # 确保路径是字符串
            if not cap.isOpened():
                raise Exception("无法打开视频文件")

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            if total_frames == 0 or fps == 0:
                raise Exception("无法获取视频信息")

            # 提取开始、中间和结束的帧
            # 跳过前几帧，避免黑屏
            frames = {}
            positions = {
                "开始": min(fps, total_frames // 10),  # 第一秒或前10%
                "中间": total_frames // 2,
                "结束": max(total_frames - fps, total_frames * 9 // 10)  # 最后一秒或后10%
            }

            for position, frame_num in positions.items():
                if not cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num):
                    self.logger.warning(f"设置帧位置失败: {position} - {frame_num}")
                    continue

                ret, frame = cap.read()
                if ret and frame is not None:
                    # 保存帧到临时文件
                    temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
                    # 确保图像数据正确
                    if frame.size == 0:
                        continue
                    # 转换为RGB格式
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    success = cv2.imwrite(temp_file.name, frame_rgb)
                    if success:
                        frames[position] = temp_file.name
                    else:
                        self.logger.warning(f"保存帧失败: {position}")

            cap.release()
            return frames if frames else None

        except Exception as e:
            self.logger.error(f"提取关键帧出错: {str(e)}")
            return None
        finally:
            if 'cap' in locals():
                cap.release()

    def _analyze_frame_with_clip(self, frame_path: str) -> Optional[List[str]]:
        """使用CLIP服务分析帧"""
        try:
            if not Path(frame_path).exists():
                raise FileNotFoundError(f"帧图像文件不存在: {frame_path}")

            with open(frame_path, 'rb') as f:
                files = {'image': f}
                response = requests.post(
                    f"{config.CLIP_SERVICE['url']}{config.CLIP_SERVICE['endpoints']['predict']}", 
                    files=files,
                    timeout=10  # 添加超时设置
                )
                if response.status_code == 200:
                    result = response.json()
                    return [item["tag"] for item in result]

        except requests.exceptions.RequestException as e:
            self.logger.error(f"CLIP服务请求失败: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"CLIP分析帧出错 {frame_path}: {str(e)}")
            return None
        finally:
            # 清理临时文件
            try:
                Path(frame_path).unlink(missing_ok=True)
            except Exception as e:
                self.logger.warning(f"清理临时文件失败 {frame_path}: {str(e)}") 