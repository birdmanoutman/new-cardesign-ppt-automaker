from ..interfaces.processor import IImageProcessor
from ..exceptions.base import ProcessorError
from ..interfaces.storage import IStorageProvider
from PIL import Image
import hashlib
from pathlib import Path
from typing import Dict

class ImageProcessor(IImageProcessor):
    def __init__(self, storage_provider: IStorageProvider):
        self.storage = storage_provider

    def process_image(self, image_path: str) -> Dict:
        try:
            # 从原有的 process_image 方法迁移代码
            with Image.open(image_path) as img:
                width, height = img.size
                img_format = img.format
            
            with open(image_path, 'rb') as f:
                img_hash = hashlib.md5(f.read()).hexdigest()
            
            return {
                'hash': img_hash,
                'path': str(image_path),
                'name': Path(image_path).name,
                'format': img_format,
                'width': width,
                'height': height
            }
        except Exception as e:
            raise ProcessorError(f"处理图片失败: {str(e)}")

    def create_thumbnail(self, image_path: str) -> str:
        try:
            cache_dir = Path("cache/thumbnails")
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            thumb_name = hashlib.md5(str(image_path).encode()).hexdigest() + ".png"
            thumb_path = cache_dir / thumb_name
            
            if thumb_path.exists():
                return str(thumb_path)
            
            with Image.open(image_path) as img:
                thumb = img.copy()
                thumb.thumbnail((200, 200))
                thumb.save(thumb_path, "PNG")
            
            return str(thumb_path)
        except Exception as e:
            raise ProcessorError(f"创建缩略图失败: {str(e)}")

    def get_image_info(self, img_hash: str) -> Dict:
        """获取图片信息"""
        try:
            return self.storage.get_image(img_hash)
        except Exception as e:
            raise ProcessorError(f"获取图片信息失败: {str(e)}") 