import sys
import pkg_resources
import platform
import logging
import aiohttp
import asyncio
from pathlib import Path
from typing import Dict, List, Tuple
from .config.settings import Settings

logger = logging.getLogger(__name__)

class EnvironmentChecker:
    """环境检查工具"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.required_packages = {
            'PyQt6': '6.0.0',
            'python-pptx': '0.6.0',
            'Pillow': '9.5.0',
            'aiohttp': '3.8.0',
            'tqdm': '4.65.0',
            'pywin32': '300'
        }
    
    def check_python_version(self) -> bool:
        """检查Python版本是否满足要求"""
        required_version = (3, 8)
        current_version = sys.version_info[:2]
        
        if current_version < required_version:
            logger.error(
                f"Python版本不满足要求: 需要 {required_version[0]}.{required_version[1]} 或更高版本, "
                f"当前版本 {current_version[0]}.{current_version[1]}"
            )
            return False
        return True
    
    def check_required_packages(self) -> Tuple[bool, List[str]]:
        """检查必要包的安装情况"""
        missing_packages = []
        outdated_packages = []
        
        for package, min_version in self.required_packages.items():
            try:
                installed_version = pkg_resources.get_distribution(package).version
                if pkg_resources.parse_version(installed_version) < pkg_resources.parse_version(min_version):
                    outdated_packages.append(f"{package} (需要 {min_version}, 当前 {installed_version})")
            except pkg_resources.DistributionNotFound:
                missing_packages.append(package)
        
        if missing_packages or outdated_packages:
            if missing_packages:
                logger.error(f"缺少必要的包: {', '.join(missing_packages)}")
            if outdated_packages:
                logger.warning(f"包版本过低: {', '.join(outdated_packages)}")
            return False, missing_packages + outdated_packages
        return True, []
    
    def check_system_requirements(self) -> bool:
        """检查系统环境要求"""
        try:
            # 检查操作系统
            os_name = platform.system()
            if os_name == 'Windows':
                win_version = platform.win32_ver()[0]
                if int(win_version.split('.')[0]) < 10:
                    logger.error(f"Windows版本过低: 需要Windows 10或更高版本")
                    return False
            
            # 检查存储空间
            app_dir = Path(self.settings.APP_DATA_DIR).resolve()
            if app_dir.exists():
                free_space = self._get_free_space(app_dir)
                if free_space < 1024 * 1024 * 1024:  # 1GB
                    logger.warning(f"存储空间不足: 剩余 {free_space / (1024*1024):.2f} MB")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"检查系统要求时出错: {str(e)}")
            return False
    
    async def check_ai_service_availability(self) -> bool:
        """检查AI服务是否可用"""
        try:
            clip_config = self.settings.AI_SERVICE_CONFIG['clip']
            url = f"http://{clip_config['host']}:{clip_config['port']}/health"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('status') == 'healthy':
                            return True
                    logger.error(f"AI服务响应异常: {response.status}")
                    return False
                    
        except aiohttp.ClientError as e:
            logger.error(f"无法连接到AI服务: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"检查AI服务时出错: {str(e)}")
            return False
    
    def _get_free_space(self, path: Path) -> int:
        """获取指定路径的可用存储空间（字节）"""
        if platform.system() == 'Windows':
            import ctypes
            free_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                ctypes.c_wchar_p(str(path)), 
                None, None, 
                ctypes.pointer(free_bytes)
            )
            return free_bytes.value
        else:
            import os
            st = os.statvfs(path)
            return st.f_bavail * st.f_frsize 