from pathlib import Path
import os
from datetime import datetime

class Settings:
    """统一的配置管理"""
    def __init__(self):
        self.APP_DATA_DIR = Path(os.getenv('APP_DATA_DIR', '~/.cardesigntools'))
        self.IMAGE_CACHE_DIR = self.APP_DATA_DIR / 'cache' / 'images'
        self.MAX_IMAGE_SIZE = 1920
        self.THUMBNAIL_SIZE = (200, 200) 
        
        self.DATE_CONFIG = {
            'min_year': 1949,
            'max_year': datetime.now().year,
        }
        
        self.FILE_CONFIG = {
            'cache_size': 1000,
            'ignored_files': [
                r'^\.',
                r'^desktop\.ini$',
                r'^thumbs\.db$',
                r'^~\$',
            ]
        }
        
        # AI服务配置
        self.AI_SERVICE_CONFIG = {
            'clip': {
                'host': os.getenv('CLIP_SERVICE_HOST', 'localhost'),
                'port': int(os.getenv('CLIP_SERVICE_PORT', '5000')),
                'timeout': int(os.getenv('CLIP_SERVICE_TIMEOUT', '30')),
                'batch_size': int(os.getenv('CLIP_SERVICE_BATCH_SIZE', '32'))
            }
        }