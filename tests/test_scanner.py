"""
测试文件扫描器
"""

import pytest
from pathlib import Path
import tempfile
import shutil
import os
import cv2
import numpy as np
import requests
from unittest.mock import patch, MagicMock
from src.core.desktop_organizer.scanner import FileScanner
from src.core.desktop_organizer import config

@pytest.fixture(scope="function")
def mock_clip_response():
    """模拟CLIP服务响应"""
    return [{"tag": "测试标签", "confidence": 0.9}]

@pytest.fixture(scope="function")
def test_env(test_data_dir, mock_clip_response):
    """创建测试环境"""
    # 创建目录结构
    desktop_path = Path(test_data_dir) / "Desktop"
    sprint_projects_path = Path(test_data_dir) / "sprintProjects"
    slowburn_projects_path = Path(test_data_dir) / "slowburnProjects"

    # 清理并重新创建目录
    for path in [desktop_path, sprint_projects_path, slowburn_projects_path]:
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)

    # 创建测试文件
    def create_test_files():
        # 在桌面创建各种类型的文件
        create_test_image(desktop_path / "test.jpg")
        create_test_image(desktop_path / "test.png")
        
        # 创建测试视频文件
        video_path = desktop_path / "test.mp4"
        create_test_video(str(video_path))
        
        (desktop_path / "test.docx").touch()
        (desktop_path / "test.pptx").touch()
        
        # 创建临时文件夹
        temp_folder = desktop_path / "新建文件夹"
        temp_folder.mkdir(exist_ok=True)
        (temp_folder / "temp.txt").touch()

        # 创建项目文件夹
        project1 = sprint_projects_path / "项目1"
        project1.mkdir(exist_ok=True)
        (project1 / "doc").mkdir(exist_ok=True)
        (project1 / "doc" / "设计文档.docx").touch()

        project2 = slowburn_projects_path / "项目2"
        project2.mkdir(exist_ok=True)
        (project2 / "资料").mkdir(exist_ok=True)

    create_test_files()

    # 修改配置
    original_desktop_path = config.DESKTOP_PATH
    original_sprint_projects_path = config.SPRINT_PROJECTS_PATH
    original_slowburn_projects_path = config.SLOWBURN_PROJECTS_PATH

    config.DESKTOP_PATH = str(desktop_path)
    config.SPRINT_PROJECTS_PATH = str(sprint_projects_path)
    config.SLOWBURN_PROJECTS_PATH = str(slowburn_projects_path)

    yield desktop_path, sprint_projects_path, slowburn_projects_path

    # 恢复原始配置
    config.DESKTOP_PATH = original_desktop_path
    config.SPRINT_PROJECTS_PATH = original_sprint_projects_path
    config.SLOWBURN_PROJECTS_PATH = original_slowburn_projects_path

    # 清理测试目录
    for path in [desktop_path, sprint_projects_path, slowburn_projects_path]:
        if path.exists():
            shutil.rmtree(path)

def create_test_image(path: Path):
    """创建测试图片文件"""
    # 创建一个简单的测试图片
    height, width = 480, 640
    image = np.zeros((height, width, 3), dtype=np.uint8)
    # 添加一些简单的图形
    cv2.rectangle(image, (100, 100), (540, 380), (255, 255, 255), -1)
    cv2.circle(image, (320, 240), 100, (0, 0, 255), -1)
    # 转换为RGB格式（OpenCV默认是BGR）
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    # 保存图片
    if str(path).lower().endswith('.jpg'):
        cv2.imwrite(str(path), image, [cv2.IMWRITE_JPEG_QUALITY, 95])
    else:
        cv2.imwrite(str(path), image)

def create_test_video(path: str, duration: int = 3):
    """创建测试视频文件"""
    # 创建一个简单的测试视频
    height, width = 480, 640
    fps = 30
    
    # 创建视频写入器
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(path, fourcc, fps, (width, height))
    
    try:
        # 生成一些帧
        for i in range(duration * fps):
            # 创建一个渐变色帧
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            frame[:, :, 0] = i % 255  # 蓝色通道
            frame[:, :, 1] = (i * 2) % 255  # 绿色通道
            frame[:, :, 2] = (i * 3) % 255  # 红色通道
            
            # 添加一些简单的图形
            cv2.rectangle(frame, (100, 100), (540, 380), (255, 255, 255), 2)
            cv2.circle(frame, (320, 240), 100, (0, 0, 255), 2)
            
            out.write(frame)
    finally:
        out.release()

@pytest.fixture
def scanner(test_env):
    """创建扫描器实例"""
    return FileScanner()

def test_scan_desktop(scanner, mock_clip_response):
    """测试桌面扫描功能"""
    # 模拟文件存在检查
    with patch('pathlib.Path.exists', return_value=True):
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_clip_response
            mock_post.return_value = mock_response
            
            # 模拟视频分析结果
            with patch('src.core.desktop_organizer.video_analyzer.VideoAnalyzer.analyze_video') as mock_analyze:
                mock_analyze.return_value = {
                    "关键帧标签": {
                        "开始": ["测试标签"],
                        "中间": ["测试标签"],
                        "结束": ["测试标签"]
                    }
                }
                
                result = scanner.scan_desktop()
                
                # 验证文件分类
                assert len(result["图片"]) == 2  # .jpg和.png
                assert len(result["视频"]) == 1  # .mp4
                assert len(result["文档"]) == 1  # .docx
                assert len(result["演示"]) == 1  # .pptx
                assert len(result["临时文件夹"]) == 1  # "新建文件夹"

                # 验证临时文件夹内容
                temp_folder = result["临时文件夹"][0]
                assert temp_folder["文件夹名"] == "新建文件夹"
                assert len(temp_folder["文件列表"]) == 1  # temp.txt

                # 验证CLIP分析结果
                for file_info in result["图片"]:
                    assert "CLIP分析" in file_info
                    assert "标签" in file_info["CLIP分析"]
                    assert isinstance(file_info["CLIP分析"]["标签"], list)
                    assert len(file_info["CLIP分析"]["标签"]) > 0

                for file_info in result["视频"]:
                    assert "CLIP分析" in file_info
                    assert "关键帧标签" in file_info["CLIP分析"]
                    assert all(key in file_info["CLIP分析"]["关键帧标签"] for key in ["开始", "中间", "结束"])

def test_scan_projects(scanner):
    """测试项目扫描功能"""
    result = scanner.scan_projects()
    
    # 验证项目数量
    assert len(result["sprint项目"]) == 1
    assert len(result["slowburn项目"]) == 1

    # 验证sprint项目信息
    sprint_project = result["sprint项目"][0]
    assert sprint_project["项目名"] == "项目1"
    assert len(sprint_project["子文件夹"]) == 1  # doc文件夹

    # 验证slowburn项目信息
    slowburn_project = result["slowburn项目"][0]
    assert slowburn_project["项目名"] == "项目2"
    assert "子文件夹" not in slowburn_project  # detailed=False

def test_file_category(scanner, test_env):
    """测试文件分类功能"""
    desktop_path = test_env[0]
    test_file = desktop_path / "test.jpg"
    category = scanner._get_file_category(test_file)
    assert category == "图片"

def test_temp_folder_detection(scanner, test_env):
    """测试临时文件夹检测"""
    desktop_path = test_env[0]
    
    # 测试各种临时文件夹名称
    temp_folders = [
        "新建文件夹",
        "untitled folder",
        "20240315_临时",
        "temp_files",
        "临时文档"
    ]
    
    for folder_name in temp_folders:
        folder_path = desktop_path / folder_name
        folder_path.mkdir(exist_ok=True)
        assert scanner._is_temp_folder(folder_path)

    # 测试正常文件夹
    normal_folder = desktop_path / "正常文件夹"
    normal_folder.mkdir(exist_ok=True)
    assert not scanner._is_temp_folder(normal_folder)

def test_error_handling(scanner, test_env):
    """测试错误处理"""
    desktop_path = test_env[0]
    
    # 测试不存在的文件
    non_existent_file = desktop_path / "not_exists.jpg"
    file_info = scanner._get_file_info(non_existent_file)
    assert file_info is None

    # 测试访问受限的文件夹
    restricted_folder = desktop_path / "restricted"
    restricted_folder.mkdir(exist_ok=True)
    try:
        os.chmod(str(restricted_folder), 0o000)  # 移除所有权限
        folder_info = scanner._get_folder_info(restricted_folder)
        assert folder_info["文件列表"] == []  # 应该返回空列表而不是失败
    finally:
        os.chmod(str(restricted_folder), 0o777)  # 恢复权限 

def test_clip_analysis(scanner, mock_clip_response):
    """测试CLIP分析功能"""
    desktop_path = Path(config.DESKTOP_PATH)

    # 测试图片分析
    test_image = desktop_path / "test_clip.jpg"
    create_test_image(test_image)
    
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_clip_response
        mock_post.return_value = mock_response
        
        # 正常图片测试
        with patch('pathlib.Path.exists', return_value=True):
            image_result = scanner._analyze_with_clip(str(test_image))
            assert image_result is not None
            assert "标签" in image_result
            assert isinstance(image_result["标签"], list)
            assert len(image_result["标签"]) > 0
        
        # 测试视频分析
        test_video = desktop_path / "test_clip.mp4"
        create_test_video(str(test_video))
        
        with patch('src.core.desktop_organizer.video_analyzer.VideoAnalyzer.analyze_video') as mock_analyze:
            mock_analyze.return_value = {
                "关键帧标签": {
                    "开始": ["测试标签"],
                    "中间": ["测试标签"],
                    "结束": ["测试标签"]
                }
            }
            video_result = scanner._analyze_video_with_clip(str(test_video))
            assert video_result is not None
            assert "关键帧标签" in video_result
            assert all(key in video_result["关键帧标签"] for key in ["开始", "中间", "结束"])

        # 测试错误处理
        # 1. 不存在的文件
        with patch('pathlib.Path.exists', return_value=False):
            non_existent = desktop_path / "non_existent.jpg"
            result = scanner._analyze_with_clip(str(non_existent))
            assert result is None

        # 2. 损坏的图片文件
        with patch('pathlib.Path.exists', return_value=True):
            corrupt_image = desktop_path / "corrupt.jpg"
            corrupt_image.write_bytes(b"Not an image")
            mock_post.side_effect = requests.exceptions.RequestException()
            result = scanner._analyze_with_clip(str(corrupt_image))
            assert result is None

        # 3. 损坏的视频文件
        corrupt_video = desktop_path / "corrupt.mp4"
        corrupt_video.write_bytes(b"Not a video")
        with patch('src.core.desktop_organizer.video_analyzer.VideoAnalyzer.analyze_video') as mock_analyze:
            mock_analyze.return_value = None
            result = scanner._analyze_video_with_clip(str(corrupt_video))
            assert result is None 