import sys
import os
from pathlib import Path

def check_python():
    """检查Python环境"""
    print("\n=== Python环境 ===")
    print(f"Python版本: {sys.version}")
    print(f"Python路径: {sys.executable}")
    print(f"系统平台: {sys.platform}")

def check_dependencies():
    """检查项目依赖"""
    print("\n=== 核心依赖 ===")
    
    # 检查PyQt6
    try:
        from PyQt6.QtCore import QT_VERSION_STR
        print(f"PyQt6版本: {QT_VERSION_STR}")
    except ImportError as e:
        print(f"PyQt6未安装: {e}")
    
    # 检查python-pptx
    try:
        import pptx
        print(f"python-pptx版本: {pptx.__version__}")
    except ImportError as e:
        print(f"python-pptx未安装: {e}")
    
    # 检查Pillow
    try:
        from PIL import __version__ as pil_version
        print(f"Pillow版本: {pil_version}")
    except ImportError as e:
        print(f"Pillow未安装: {e}")
    
    # 检查pywin32
    try:
        import win32com
        print("pywin32已安装")
    except ImportError as e:
        print(f"pywin32未安装: {e}")

def check_ml_environment():
    """检查机器学习环境"""
    print("\n=== 机器学习环境 ===")
    
    # 检查PyTorch
    try:
        import torch
        print(f"PyTorch版本: {torch.__version__}")
        print(f"CUDA可用: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"CUDA版本: {torch.version.cuda}")
            print(f"当前GPU: {torch.cuda.get_device_name(0)}")
    except ImportError as e:
        print(f"PyTorch未安装: {e}")
    
    # 检查Transformers
    try:
        import transformers
        print(f"Transformers版本: {transformers.__version__}")
    except ImportError as e:
        print(f"Transformers未安装: {e}")

def check_project_structure():
    """检查项目结构"""
    print("\n=== 项目结构 ===")
    project_root = Path(__file__).parent.parent.parent
    
    required_dirs = [
        'src/core',
        'src/core/database',
        'src/core/images',
        'src/core/ml',
        'src/core/ppt',
        'src/core/tags',
        'src/ui',
        'src/ui/tabs',
        'src/ui/tabs/image_db',
        'src/ui/dialogs',
        'src/utils'
    ]
    
    required_files = [
        # 核心模块文件
        'src/core/__init__.py',
        'src/core/controller.py',
        'src/core/file_manager.py',
        'src/core/database/db_manager.py',
        'src/core/images/image_processor.py',
        'src/core/ml/clip_manager.py',
        'src/core/ppt/ppt_processor.py',
        'src/core/ppt/ppt_extractor.py',
        'src/core/tags/tag_manager.py',
        # UI模块文件
        'src/ui/main_window.py',
        'src/ui/tabs/base_tab.py',
        'src/ui/tabs/image_db/tab.py',
        'src/ui/tabs/image_db/ui.py',
        'src/ui/tabs/image_db/loader.py',
        'src/ui/tabs/image_db/handlers.py',
        'src/ui/tabs/image_db/image_item.py',
        'src/ui/dialogs/tag_manager_dialog.py',
        # 其他配置文件
        'requirements.txt',
        'version.txt'
    ]
    
    print("检查目录结构:")
    for dir_path in required_dirs:
        path = project_root / dir_path
        print(f"  {dir_path}: {'✓' if path.exists() else '✗'}")
    
    print("\n检查关键文件:")
    for file_path in required_files:
        path = project_root / file_path
        print(f"  {file_path}: {'✓' if path.exists() else '✗'}")

def check_data_directories():
    """检查数据目录"""
    print("\n=== 数据目录 ===")
    if sys.platform == 'win32':
        app_data = os.getenv('APPDATA')
        data_dir = Path(app_data) / 'CarDesignTools'
    else:
        home = os.path.expanduser('~')
        data_dir = Path(home) / '.cardesigntools'
    
    print(f"应用数据目录: {data_dir}")
    print(f"目录存在: {'✓' if data_dir.exists() else '✗'}")
    
    if data_dir.exists():
        db_file = data_dir / "image_gallery.db"
        thumb_dir = data_dir / "thumbnails"
        print(f"数据库文件: {'✓' if db_file.exists() else '✗'}")
        print(f"缩略图目录: {'✓' if thumb_dir.exists() else '✗'}")

def main():
    """运行所有检查"""
    print("=== 开始环境检查 ===")
    check_python()
    check_dependencies()
    check_ml_environment()
    check_project_structure()
    check_data_directories()
    print("\n=== 环境检查完成 ===")

if __name__ == '__main__':
    main() 