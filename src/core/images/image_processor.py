from PIL import Image, ImageDraw, ImageFont
import hashlib
from pathlib import Path
import os
from typing import Dict, List, Optional, Tuple
import json
import logging
from datetime import datetime
from ..tags.tag_manager import TagManager
from ...utils.config.settings import Settings

class ImageProcessor:
    """图片处理器 - 负责图片处理、缩略图生成等功能"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.tag_manager = TagManager(db_manager)
        self.cursor = db_manager.cursor  # 添加cursor属性
    
    def search_images_by_tags(self, tags: Tuple[str, ...], match_all: bool = False) -> List[Dict]:
        """根据标签搜索图片"""
        try:
            # 构建SQL查询
            if match_all:
                # 必须匹配所有标签
                sql = f"""
                    SELECT i.img_hash as hash, i.img_path as path, i.img_name as name, 
                           i.extract_date, i.img_type, i.format, i.width, i.height,
                           i.file_size,
                           COUNT(DISTINCT m.pptx_path) as ref_count,
                           GROUP_CONCAT(DISTINCT t2.name) as tags
                    FROM {self.db.table_name} i
                    JOIN image_tags it ON i.img_hash = it.img_hash
                    JOIN tags t ON it.tag_id = t.id
                    LEFT JOIN image_ppt_mapping m ON i.img_hash = m.img_hash
                    LEFT JOIN image_tags it2 ON i.img_hash = it2.img_hash
                    LEFT JOIN tags t2 ON it2.tag_id = t2.id
                    WHERE t.name IN ({','.join(['?' for _ in tags])})
                    GROUP BY i.img_hash
                    HAVING COUNT(DISTINCT t.name) = ?
                    ORDER BY i.extract_date DESC
                """
                params = list(tags) + [len(tags)]
            else:
                # 匹配任意标签
                sql = f"""
                    SELECT i.img_hash as hash, i.img_path as path, i.img_name as name, 
                           i.extract_date, i.img_type, i.format, i.width, i.height,
                           i.file_size,
                           COUNT(DISTINCT m.pptx_path) as ref_count,
                           GROUP_CONCAT(DISTINCT t2.name) as tags
                    FROM {self.db.table_name} i
                    JOIN image_tags it ON i.img_hash = it.img_hash
                    JOIN tags t ON it.tag_id = t.id
                    LEFT JOIN image_ppt_mapping m ON i.img_hash = m.img_hash
                    LEFT JOIN image_tags it2 ON i.img_hash = it2.img_hash
                    LEFT JOIN tags t2 ON it2.tag_id = t2.id
                    WHERE t.name IN ({','.join(['?' for _ in tags])})
                    GROUP BY i.img_hash
                    ORDER BY i.extract_date DESC
                """
                params = list(tags)
            
            results = self.db.execute(sql, params).fetchall()
            
            # 转换结果为字典列表
            images = []
            for row in results:
                img_dict = dict(row)
                # 处理标签
                if img_dict.get('tags'):
                    img_dict['tags'] = img_dict['tags'].split(',')
                else:
                    img_dict['tags'] = []
                images.append(img_dict)
            
            return images
            
        except Exception as e:
            logging.error(f"搜索图片失败: {str(e)}")
            return []
    
    def get_ppt_sources(self) -> List[str]:
        """获取所有PPT源文件路径"""
        try:
            results = self.db.execute(
                "SELECT DISTINCT path FROM ppt_sources ORDER BY added_date DESC"
            ).fetchall()
            return [row[0] for row in results]
        except Exception as e:
            logging.error(f"获取PPT源文件失败: {str(e)}")
            return []
    
    def get_setting(self, key: str) -> Optional[str]:
        """获取设置值"""
        try:
            result = self.db.execute(
                "SELECT value FROM settings WHERE key = ?",
                (key,)
            ).fetchone()
            return result[0] if result else None
        except Exception as e:
            logging.error(f"获取设置失败: {str(e)}")
            return None
    
    def set_setting(self, key: str, value: str):
        """设置值"""
        try:
            with self.db.transaction():
                self.db.execute(
                    "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
                    (key, value, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                )
        except Exception as e:
            logging.error(f"保存设置失败: {str(e)}")
            raise
    
    def get_image_stats(self) -> Dict:
        """获取图片库统计信息"""
        try:
            # 获取总图片数
            total = self.db.execute(
                f"SELECT COUNT(*) FROM {self.db.table_name}"
            ).fetchone()[0]
            
            # 获取PPT数量
            ppt_count = self.db.execute(
                "SELECT COUNT(DISTINCT pptx_path) FROM image_ppt_mapping"
            ).fetchone()[0]
            
            return {
                'total': total,
                'ppt_count': ppt_count
            }
        except Exception as e:
            logging.error(f"获取统计信息失败: {str(e)}")
            return {'total': 0, 'ppt_count': 0}
    
    def get_all_images(self) -> List[Dict]:
        """获取所有图片信息"""
        try:
            results = self.db.execute(f"""
                SELECT i.img_hash as hash, i.img_path as path, i.img_name as name, 
                       i.extract_date, i.img_type, i.format, i.width, i.height,
                       i.file_size,
                       COUNT(DISTINCT m.pptx_path) as ref_count,
                       GROUP_CONCAT(DISTINCT t.name) as tags
                FROM {self.db.table_name} i
                LEFT JOIN image_ppt_mapping m ON i.img_hash = m.img_hash
                LEFT JOIN image_tags it ON i.img_hash = it.img_hash
                LEFT JOIN tags t ON it.tag_id = t.id
                GROUP BY i.img_hash
                ORDER BY i.extract_date DESC
            """).fetchall()
            
            # 转换结果为字典列表
            images = []
            for row in results:
                img_dict = dict(row)
                # 处理标签
                if img_dict.get('tags'):
                    img_dict['tags'] = img_dict['tags'].split(',')
                else:
                    img_dict['tags'] = []
                images.append(img_dict)
            
            return images
            
        except Exception as e:
            logging.error(f"获取图片列表失败: {str(e)}")
            return []
    
    def process_image(self, img_path: str) -> Dict:
        """处理单个图片，返回图片信息"""
        try:
            # 打开图片获取基本信息
            with Image.open(img_path) as img:
                width, height = img.size
                img_format = img.format
            
            # 计算图片哈希
            with open(img_path, 'rb') as f:
                img_hash = hashlib.md5(f.read()).hexdigest()
            
            # 构建图片信息
            img_info = {
                'hash': img_hash,
                'path': str(img_path),
                'name': Path(img_path).name,
                'format': img_format,
                'width': width,
                'height': height,
                'size': os.path.getsize(img_path)
            }
            
            return img_info
            
        except Exception as e:
            logging.error(f"处理图片失败: {str(e)}")
            raise
    
    def create_thumbnail(self, img_path: str, size=(200, 200)) -> str:
        """创建缩略图"""
        try:
            # 检查文件扩展名
            ext = Path(img_path).suffix.lower()
            if ext in ['.wmf', '.emf']:
                # 对于元文件格式，返回一个默认图标
                default_icon = str(Path(__file__).parent / 'assets' / 'metafile_icon.png')
                if not Path(default_icon).exists():
                    # 如果默认图标不存在，创建一个简单的图标
                    icon = Image.new('RGB', (200, 200), (200, 200, 200))
                    draw = ImageDraw.Draw(icon)
                    draw.text((50, 90), "WMF/EMF\nFile", fill=(100, 100, 100))
                    
                    # 确保assets目录存在
                    assets_dir = Path(__file__).parent / 'assets'
                    assets_dir.mkdir(parents=True, exist_ok=True)
                    
                    # 保存默认图标
                    icon.save(default_icon, "PNG", icc_profile=None)
                
                return default_icon
            
            # 生成缓存路径
            cache_dir = Path(self._get_cache_dir()) / "thumbnails"
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            # 计算缩略图文件名
            thumb_name = hashlib.md5(str(img_path).encode()).hexdigest() + ".png"
            thumb_path = cache_dir / thumb_name
            
            # 如果缩略图已存在，直接返回
            if thumb_path.exists():
                return str(thumb_path)
            
            # 创建缩略图
            with Image.open(img_path) as img:
                # 保持RGBA格式
                if img.mode == 'RGBA':
                    thumb = img.copy()
                else:
                    thumb = img.convert('RGBA')
                
                # 计算缩略图尺寸
                thumb.thumbnail(size, Image.Resampling.LANCZOS)
                
                # 保存缩略图，移除ICC配置文件以避免警告
                thumb.save(thumb_path, "PNG", optimize=True, icc_profile=None)
            
            return str(thumb_path)
            
        except Exception as e:
            logging.error(f"创建缩略图失败: {str(e)}")
            # 返回一个错误占位图
            error_icon = str(Path(__file__).parent / 'assets' / 'error_icon.png')
            if not Path(error_icon).exists():
                # 创建错误占位图
                icon = Image.new('RGB', (200, 200), (255, 200, 200))
                draw = ImageDraw.Draw(icon)
                draw.text((50, 90), "Error\nLoading", fill=(200, 0, 0))
                
                # 确保assets目录存在
                assets_dir = Path(__file__).parent / 'assets'
                assets_dir.mkdir(parents=True, exist_ok=True)
                
                # 保存错误图标
                icon.save(error_icon, "PNG", icc_profile=None)
            
            return error_icon
    
    def batch_create_thumbnails(self, img_paths: List[str], ref_counts: List[int] = None) -> List[str]:
        """批量创建缩略图"""
        try:
            thumb_paths = []
            for i, img_path in enumerate(img_paths):
                try:
                    # 创建基本缩略图
                    thumb_path = self.create_thumbnail(img_path)
                    
                    # 如果有引用计数大于1，添加角标
                    if ref_counts and i < len(ref_counts) and ref_counts[i] > 1:
                        thumb_path = self._add_ref_count_watermark(
                            thumb_path, ref_counts[i]
                        )
                    
                    thumb_paths.append(thumb_path)
                except Exception as e:
                    logging.error(f"处理图片 {img_path} 失败: {str(e)}")
                    # 返回错误占位图
                    error_icon = str(Path(__file__).parent / 'assets' / 'error_icon.png')
                    thumb_paths.append(error_icon)
            
            return thumb_paths
            
        except Exception as e:
            logging.error(f"批量创建缩略图失败: {str(e)}")
            # 返回错误占位图列表
            error_icon = str(Path(__file__).parent / 'assets' / 'error_icon.png')
            return [error_icon] * len(img_paths)
    
    def _add_ref_count_watermark(self, img_path: str, ref_count: int) -> str:
        """添加引用计数水印"""
        try:
            # 生成水印图片路径
            cache_dir = Path(self._get_cache_dir()) / "watermarks"
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            watermark_name = (
                hashlib.md5(f"{img_path}_{ref_count}".encode()).hexdigest() + 
                ".png"  # 使用PNG以支持透明度
            )
            watermark_path = cache_dir / watermark_name
            
            # 如果水印图片已存在，直接返回
            if watermark_path.exists():
                return str(watermark_path)
            
            # 打开原图
            with Image.open(img_path) as img:
                # 保持RGBA格式以支持透明度
                if img.mode == 'RGBA':
                    thumb = img.copy()
                else:
                    thumb = img.convert('RGBA')
                
                # 创建一个新的透明图层用于绘制角标
                badge = Image.new('RGBA', thumb.size, (0, 0, 0, 0))
                draw = ImageDraw.Draw(badge)
                
                # 绘制圆形背景
                badge_size = min(thumb.size) // 8  # 根据图片大小调整角标大小
                x = thumb.size[0] - badge_size - 5
                y = 5
                draw.ellipse(
                    [x, y, x + badge_size, y + badge_size],
                    fill=(255, 0, 0, 200)  # 半透明红色
                )
                
                # 设置字体
                font_size = badge_size * 2 // 3  # 角标大小的2/3
                try:
                    font = ImageFont.truetype("arial.ttf", font_size)
                except:
                    font = ImageFont.load_default()
                
                # 绘制文字
                text = str(ref_count)
                text_bbox = draw.textbbox((0, 0), text, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                
                text_x = x + (badge_size - text_width) // 2
                text_y = y + (badge_size - text_height) // 2
                draw.text(
                    (text_x, text_y), 
                    text, 
                    font=font, 
                    fill=(255, 255, 255)  # 白色文字
                )
                
                # 合并图层
                thumb = Image.alpha_composite(thumb, badge)
                
                # 保存结果
                thumb.save(watermark_path, "PNG", optimize=True)
            
            return str(watermark_path)
            
        except Exception as e:
            logging.error(f"添加水印失败: {str(e)}")
            return img_path
    
    def _get_cache_dir(self) -> str:
        """获取缓存目录"""
        try:
            cache_dir = self.get_setting('cache_dir')
            if not cache_dir:
                if os.name == 'nt':  # Windows
                    cache_dir = str(Path(os.getenv('LOCALAPPDATA')) / 'CarDesignTools' / 'cache')
                else:  # Linux/Mac
                    cache_dir = str(Path.home() / '.cache' / 'cardesigntools')
                
                # 创建目录
                Path(cache_dir).mkdir(parents=True, exist_ok=True)
                
                # 保存设置
                self.set_setting('cache_dir', cache_dir)
            return cache_dir
        except Exception as e:
            # 如果设置保存失败，直接返回默认路径
            if os.name == 'nt':  # Windows
                cache_dir = str(Path(os.getenv('LOCALAPPDATA')) / 'CarDesignTools' / 'cache')
            else:  # Linux/Mac
                cache_dir = str(Path.home() / '.cache' / 'cardesigntools')
            
            # 创建目录
            Path(cache_dir).mkdir(parents=True, exist_ok=True)
            return cache_dir
    
    def save_setting(self, key: str, value: str):
        """保存设置（兼容旧代码）"""
        try:
            self.set_setting(key, value)
        except Exception as e:
            logging.error(f"保存设置失败: {str(e)}")
            raise