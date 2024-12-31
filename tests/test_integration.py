"""
集成测试
测试与实际服务的交互
"""

import pytest
import json
from pathlib import Path
import requests
from datetime import datetime
from src.core.desktop_organizer.scanner import FileScanner
from src.core.desktop_organizer import config

def test_real_desktop_scan():
    """测试真实桌面扫描和CLIP服务集成"""
    # 检查CLIP服务是否可用
    try:
        response = requests.get(f"{config.CLIP_SERVICE['url']}/health")
        response.raise_for_status()
    except Exception as e:
        pytest.skip(f"CLIP服务不可用: {str(e)}")

    # 创建扫描器
    scanner = FileScanner()
    
    # 扫描桌面
    result = scanner.scan_desktop()
    
    # 验证扫描结果
    assert isinstance(result, dict)
    print("\n扫描结果统计:")
    for category, files in result.items():
        print(f"{category}: {len(files)} 个文件")
        if category in ["图片", "视频"]:
            for file_info in files:
                print(f"\n文件: {file_info['文件名']}")
                if "CLIP分析" in file_info:
                    if category == "图片":
                        print("CLIP标签:", file_info["CLIP分析"]["标签"])
                    else:  # 视频
                        print("视频关键帧CLIP分析:", file_info["CLIP分析"]["关键帧标签"])

    # 扫描项目
    projects = scanner.scan_projects()
    print("\n项目扫描结果:")
    for category, project_list in projects.items():
        print(f"\n{category}:")
        for project in project_list:
            print(f"- {project['项目名']}")
            if "子文件夹" in project:
                print("  子文件夹:", project["子文件夹"])

    # 保存结果到项目根目录的scan_results文件夹
    output_file = scanner.save_info_package(config.OUTPUT_PATH)
    print(f"\n扫描结果已保存到: {output_file}")
    
    # 验证输出文件
    assert output_file.exists()
    with open(output_file, "r", encoding="utf-8-sig") as f:
        saved_data = json.load(f)
        assert "files" in saved_data
        assert "projects" in saved_data
        assert "timestamp" in saved_data 