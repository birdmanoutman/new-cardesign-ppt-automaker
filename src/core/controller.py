from pathlib import Path
from .services.image_service import ImageService
from .services.tag_service import TagService
from .storage.db_manager import DatabaseManager
from .processors.image_processor import ImageProcessor
from .tags.tag_manager import TagManager
from .ppt.ppt_extractor import PPTExtractor
from .ppt.ppt_processor import PPTProcessor
from typing import List, Dict
from ..utils.config.settings import Settings

class Controller:
    """应用程序主控制器 - 协调各个模块的工作"""
    
    def __init__(self, app_data_dir: Path):
        # 初始化配置
        self.settings = Settings()
        
        # 初始化存储层
        self.db_manager = DatabaseManager(app_data_dir)
        
        # 初始化处理器
        self.image_processor = ImageProcessor(self.db_manager)
        
        # 初始化服务层
        self.image_service = ImageService(
            processor=self.image_processor,
            storage=self.db_manager
        )
        self.tag_service = TagService(self.settings)
        
        # 初始化其他模块
        self.tag_manager = TagManager(self.db_manager)
        self.ppt_extractor = PPTExtractor(self.db_manager)
        self.ppt_processor = PPTProcessor()
        
        # 初始化默认数据
        self._init_default_data()
    
    def _init_default_data(self):
        """初始化默认数据(仅首次运行时)"""
        try:
            # 检查是否已有分类数据
            self.db_manager.execute("SELECT COUNT(*) FROM tag_categories")
            count = self.db_manager.fetchone()[0]
            
            # 只在没有分类数据时初始化
            if count == 0:
                # 默认标签分类
                default_categories = {
                    'object': {
                        'name': '对象',
                        'prompts': [
                            'This image contains {}',
                            'A photograph showing {}',
                            'The main subject is {}',
                            'We can see {} in this image'
                        ],
                        'confidence_threshold': 0.5,
                        'priority': 1,
                        'tags': ['car', 'person', 'building', 'animal', 'plant']
                    },
                    'scene': {
                        'name': '场景',
                        'prompts': [
                            'This is a scene of {}',
                            'The environment appears to be {}',
                            'The location looks like {}',
                            'This picture was taken in {}'
                        ],
                        'confidence_threshold': 0.5,
                        'priority': 2,
                        'tags': ['interior', 'exterior', 'street', 'nature', 'urban']
                    },
                    'style': {
                        'name': '风格',
                        'prompts': [
                            'The style is {}',
                            'This has a {} appearance',
                            'The design aesthetic is {}',
                            'It features a {} style'
                        ],
                        'confidence_threshold': 0.5,
                        'priority': 3,
                        'tags': ['modern', 'classic', 'sporty', 'luxury', 'minimalist']
                    },
                    'color': {
                        'name': '颜色',
                        'prompts': [
                            'The main color is {}',
                            'The dominant color appears to be {}',
                            'This image primarily features {} tones',
                            'The color scheme is mainly {}'
                        ],
                        'confidence_threshold': 0.5,
                        'priority': 4,
                        'tags': ['red', 'blue', 'green', 'yellow', 'white']
                    }
                }
                
                self.tag_manager.init_default_categories(default_categories)
                print("初始化默认分类数据完成")
                
        except Exception as e:
            print(f"初始化默认数据时出错: {str(e)}")
    
    def get_ppt_sources(self) -> List[str]:
        """获取所有PPT源文件夹"""
        return self.ppt_extractor.get_ppt_sources()
    
    def get_image_stats(self) -> Dict:
        """获取图片库统计信息"""
        return {
            'total': self.image_processor.get_total_images(),
            'ppt_count': self.ppt_extractor.get_total_ppts()
        }
    
    def extract_images_from_ppt(self, source_path: str, output_folder: str, 
                              progress_callback=None) -> Dict:
        """从PPT提取图片的统一入口"""
        return self.ppt_extractor.extract_images_from_folder(
            source_path, output_folder, progress_callback
        )
        