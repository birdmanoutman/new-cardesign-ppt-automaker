import os
import sys
import platform
from pathlib import Path
from PyInstaller.__main__ import run

def build():
    # 获取项目根目录
    root_dir = Path(__file__).parent.absolute()
    
    # 基本配置
    opts = [
        str(root_dir / 'main.py'),  # 主脚本
        '--name=PPT快捷处理工具',   # 应用名称
        '--noconsole',            # 不显示控制台
        '--windowed',             # 使用窗口模式
        '--clean',                # 清理临时文件
        '--noconfirm',            # 不确认覆盖
        '--onefile',              # 打包成单个文件
        
        # 添加必要的隐式导入
        '--hidden-import', 'win32com.client',
        '--hidden-import', 'PIL',
        '--hidden-import', 'pptx',
        '--hidden-import', 'sqlite3',
    ]
    
    # 添加数据文件
    if platform.system() == "Windows":
        opts.extend([
            '--add-data', f'{root_dir / "src"};src',  # Windows 使用分号
            '--add-binary', f'{sys.prefix}/Lib/site-packages/PyQt6/Qt6/bin/*;PyQt6/Qt6/bin',
        ])
    else:
        opts.extend([
            '--add-data', f'{root_dir / "src"}:src',  # Unix 使用冒号
        ])
    
    # 添加图标（如果有的话）
    icon_path = root_dir / 'resources' / 'icon.ico'
    if icon_path.exists():
        opts.extend(['--icon', str(icon_path)])
    
    print("Starting build with options:", opts)
    run(opts)

if __name__ == '__main__':
    try:
        build()
        print("Build completed successfully!")
    except Exception as e:
        print(f"Build failed: {str(e)}")
        sys.exit(1) 