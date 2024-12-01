import io
import logging
import os
import sqlite3
from pathlib import Path
from PIL import Image
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
import hashlib
from datetime import datetime
import win32com.client

class ImageProcessor:
    def __init__(self):
        self.db_path = None
        self.db_conn = None
        self.cursor = None
        self.table_name = "image_ppt_mapping"
        
        # 设置数据库路径（在应用程序数据目录）
        app_data_dir = Path(self._get_app_data_dir())
        self.db_path = app_data_dir / "image_gallery.db"
        
        # 确保目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库
        self.init_database()
    
    def _get_app_data_dir(self) -> Path:
        """获取应用程序数据目录"""
        if os.name == 'nt':  # Windows
            app_data = os.getenv('APPDATA')
            return Path(app_data) / 'CarDesignTools'
        else:  # Linux/Mac
            home = os.path.expanduser('~')
            return Path(home) / '.cardesigntools'
    
    def init_database(self):
        """初始化数据库"""
        try:
            # 连接数据库
            self.db_conn = sqlite3.connect(str(self.db_path))
            self.cursor = self.db_conn.cursor()
            
            # 创建表
            self._create_table()
            
            print(f"数据库初始化成功: {self.db_path}")
            
        except Exception as e:
            print(f"初始化数据库时出错: {str(e)}")
            raise
    
    def _create_table(self):
        """创建数据库表"""
        table_sql = f'''
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                id INTEGER PRIMARY KEY,
                img_hash TEXT UNIQUE,
                img_path TEXT,
                pptx_path TEXT,
                extract_date TEXT,
                is_duplicate INTEGER,
                img_type TEXT,
                width INTEGER,
                height INTEGER
            )
        '''
        self.cursor.execute(table_sql)
        self.db_conn.commit()
    
    def _calculate_image_hash(self, image_data: bytes) -> str:
        """计算图片哈希值"""
        return hashlib.md5(image_data).hexdigest()
    
    def _is_size_similar(self, img: Image.Image, presentation: Presentation) -> bool:
        """检查图片尺寸是否接近PPT幻灯片尺寸"""
        # 获取PPT幻灯片尺寸（英寸转像素，假设96 DPI）
        ppt_width = int(presentation.slide_width * 96 / 914400)  # EMU到英寸到像素
        ppt_height = int(presentation.slide_height * 96 / 914400)
        
        # 获取图片尺寸
        img_width, img_height = img.size
        
        # 计算比例
        width_ratio = img_width / ppt_width
        height_ratio = img_height / ppt_height
        
        # 如果图片尺寸接近或大于PPT尺寸，认为是景图
        return width_ratio >= 0.8 and height_ratio >= 0.8
    
    def _is_duplicate(self, img_hash: str) -> bool:
        """检查图片是否重复"""
        self.cursor.execute(
            f"SELECT EXISTS(SELECT 1 FROM {self.table_name} WHERE img_hash=? LIMIT 1)",
            (img_hash,)
        )
        return bool(self.cursor.fetchone()[0])
    
    def _save_image(self, img: Image.Image, img_path: str):
        """保存图片"""
        # 确保保存路径存在
        os.makedirs(os.path.dirname(img_path), exist_ok=True)
        
        # 转换图片格式并保存
        if img.mode in ['RGBA', 'P']:
            img = img.convert('RGB')
        img.save(img_path)
    
    def _determine_image_type(self, img: Image.Image, content_type: str, presentation: Presentation) -> str:
        """
        确定图片类型
        返回: 'background' | 'icon' | 'normal'
        """
        # 如果是WMF格式，标记为icon
        if content_type == 'image/x-wmf':
            return 'icon'
        
        # 获取PPT幻灯片尺寸（英寸转像素，假设96 DPI）
        ppt_width = int(presentation.slide_width * 96 / 914400)  # EMU到英寸到像素
        ppt_height = int(presentation.slide_height * 96 / 914400)
        
        # 获取图片尺寸
        img_width, img_height = img.size
        
        # 计算比例
        width_ratio = img_width / ppt_width
        height_ratio = img_height / ppt_height
        
        # 如果图片尺寸接近或大于PPT尺寸，认为是背景图片
        if width_ratio >= 0.8 and height_ratio >= 0.8:
            return 'background'
        
        return 'normal'
    
    def extract_background_images(self, ppt_path: str, output_folder: str) -> list:
        """
        从PPT中提取所有图片并建立索引
        返回: 提取的图片信息列表
        """
        try:
            ppt_path = Path(ppt_path)
            output_folder = Path(output_folder)
            output_folder.mkdir(parents=True, exist_ok=True)
            extracted_images = []
            
            # 打开PPT文件
            presentation = Presentation(ppt_path)
            
            # 遍历所有幻灯片
            for slide_idx, slide in enumerate(presentation.slides, 1):
                # 1. 提取形状中的图片
                for shape_idx, shape in enumerate(slide.shapes, 1):
                    try:
                        if hasattr(shape, 'image'):
                            # 获取图片数据和格式
                            img_data = shape.image.blob
                            content_type = shape.image.content_type
                            
                            # 打开图片并确定类型
                            img = Image.open(io.BytesIO(img_data))
                            img_type = self._determine_image_type(img, content_type, presentation)
                            
                            # 计算图片哈希值
                            img_hash = self._calculate_image_hash(img_data)
                            
                            # 确定文件扩展名
                            ext = self._get_image_extension(content_type, img_data)
                            
                            # 生成图片文件名
                            img_name = f"{ppt_path.stem}_slide{slide_idx}_shape{shape_idx}{ext}"
                            img_path = str(output_folder / img_name)
                            
                            # 检查是否重复
                            is_duplicate = self._is_duplicate(img_hash)
                            
                            if not is_duplicate:
                                # 保存原始图片数据
                                with open(img_path, 'wb') as f:
                                    f.write(img_data)
                                
                                # 记录图片信息
                                image_info = {
                                    'path': img_path,
                                    'hash': img_hash,
                                    'ppt_path': str(ppt_path),
                                    'slide': slide_idx,
                                    'shape': shape_idx,
                                    'format': ext[1:].upper(),
                                    'type': img_type,
                                    'width': img.size[0],
                                    'height': img.size[1],
                                    'extract_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                }
                                
                                extracted_images.append(image_info)
                                
                                # 记录到数据库
                                self.cursor.execute(
                                    f"INSERT OR REPLACE INTO {self.table_name} "
                                    f"(img_hash, img_path, pptx_path, extract_date, is_duplicate, img_type, width, height) "
                                    f"VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                    (img_hash, img_path, str(ppt_path), 
                                     image_info['extract_date'], 0, img_type,
                                     img.size[0], img.size[1])
                                )
                                self.db_conn.commit()
                                
                    except Exception as e:
                        print(f"处理图片时出错: {str(e)}")
                        continue
                
                # 2. 提取背景图片
                try:
                    if hasattr(slide, 'background') and hasattr(slide.background, 'image'):
                        img_data = slide.background.image.blob
                        content_type = slide.background.image.content_type
                        
                        img = Image.open(io.BytesIO(img_data))
                        img_hash = self._calculate_image_hash(img_data)
                        ext = self._get_image_extension(content_type, img_data)
                        
                        img_name = f"{ppt_path.stem}_slide{slide_idx}_background{ext}"
                        img_path = str(output_folder / img_name)
                        
                        is_duplicate = self._is_duplicate(img_hash)
                        
                        if not is_duplicate:
                            with open(img_path, 'wb') as f:
                                f.write(img_data)
                            
                            image_info = {
                                'path': img_path,
                                'hash': img_hash,
                                'ppt_path': str(ppt_path),
                                'slide': slide_idx,
                                'shape': 'background',
                                'format': ext[1:].upper(),
                                'type': 'background',  # 背景图片一定是background类型
                                'width': img.size[0],
                                'height': img.size[1],
                                'extract_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            }
                            
                            extracted_images.append(image_info)
                            
                            self.cursor.execute(
                                f"INSERT OR REPLACE INTO {self.table_name} "
                                f"(img_hash, img_path, pptx_path, extract_date, is_duplicate, img_type, width, height) "
                                f"VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                (img_hash, img_path, str(ppt_path), 
                                 image_info['extract_date'], 0, 'background',
                                 img.size[0], img.size[1])
                            )
                            self.db_conn.commit()
                            
                except Exception as e:
                    print(f"处理背景图片时出错: {str(e)}")
            
            return extracted_images
            
        except Exception as e:
            print(f"提取图片时出错: {str(e)}")
            raise

    def _get_image_extension(self, content_type: str, img_data: bytes) -> str:
        """根据内容类型和文件头确定图片扩展名"""
        try:
            # 尝试使用PIL打开图片来确定格式
            img = Image.open(io.BytesIO(img_data))
            if img.format:
                if img.format == 'MPO':
                    return '.jpg'  # MPO格式作为JPEG处理
                return f".{img.format.lower()}"
            
        except Exception:
            # 如果PIL无法打开，尝试从MIME类型和文件头判断
            ext_map = {
                'image/png': '.png',
                'image/jpeg': '.jpg',
                'image/gif': '.gif',
                'image/bmp': '.bmp',
                'image/tiff': '.tiff',
                'image/x-emf': '.emf',
                'image/x-wmf': '.wmf',
                'image/webp': '.webp',
                'image/x-icon': '.ico',
                'image/svg+xml': '.svg',
                'image/mpo': '.jpg',
            }
            
            if content_type in ext_map:
                return ext_map[content_type]
            
            # 从文件头判断
            if img_data.startswith(b'\x89PNG'):
                return '.png'
            elif img_data.startswith(b'\xFF\xD8'):
                return '.jpg'
            elif img_data.startswith(b'GIF8'):
                return '.gif'
            elif img_data.startswith(b'BM'):
                return '.bmp'
            elif img_data.startswith(b'II*\x00') or img_data.startswith(b'MM\x00*'):
                return '.tiff'
        
        # 如果无法确定格式，默认保存为JPEG
        return '.jpg'

    def get_all_images(self) -> list:
        """获取数据库中的所有图片信息"""
        if not self.cursor:
            raise ValueError("数据库未初始化")
        
        try:
            self.cursor.execute(
                f"SELECT img_hash, img_path, pptx_path, extract_date FROM {self.table_name} "
                f"WHERE is_duplicate = 0 ORDER BY extract_date DESC"
            )
            results = self.cursor.fetchall()
            
            images = []
            for row in results:
                img_hash, img_path, pptx_path, extract_date = row
                if Path(img_path).exists():  # 只返回仍然存在的图片
                    images.append({
                        'hash': img_hash,
                        'path': img_path,
                        'ppt_path': pptx_path,
                        'extract_date': extract_date,
                        'name': Path(img_path).name,
                        'ppt_name': Path(pptx_path).name
                    })
            return images
        except Exception as e:
            print(f"获取图片列表时出错: {str(e)}")
            return []

    def search_images(self, keyword: str = "", img_type: str = None) -> list:
        """
        搜索图片
        keyword: 搜索关键词
        img_type: 图片类型过滤（'background'|'icon'|'normal'|None）
        """
        if not self.cursor:
            raise ValueError("数据库未初始化")
        
        try:
            query = f"""
                SELECT img_hash, img_path, pptx_path, extract_date, img_type, width, height 
                FROM {self.table_name} 
                WHERE is_duplicate = 0
            """
            params = []
            
            # 添加关键词搜索条件
            if keyword:
                query += " AND (img_path LIKE ? OR pptx_path LIKE ?)"
                params.extend([f"%{keyword}%", f"%{keyword}%"])
            
            # 添加类型过滤条件
            if img_type:
                query += " AND img_type = ?"
                params.append(img_type)
            
            # 按提取时间降序排序
            query += " ORDER BY extract_date DESC"
            
            self.cursor.execute(query, params)
            results = self.cursor.fetchall()
            
            images = []
            for row in results:
                img_hash, img_path, pptx_path, extract_date, img_type, width, height = row
                if Path(img_path).exists():  # 只返回仍然存在的图片
                    images.append({
                        'hash': img_hash,
                        'path': img_path,
                        'ppt_path': pptx_path,
                        'extract_date': extract_date,
                        'type': img_type,
                        'width': width,
                        'height': height,
                        'name': Path(img_path).name,
                        'ppt_name': Path(pptx_path).name
                    })
            return images
        except Exception as e:
            print(f"搜索图片时出错: {str(e)}")
            return []

    def get_image_info(self, img_hash: str) -> dict:
        """获取指定图片的详细信息"""
        if not self.cursor:
            raise ValueError("数据库未初始化")
        
        try:
            self.cursor.execute(
                f"SELECT img_path, pptx_path, extract_date FROM {self.table_name} "
                f"WHERE img_hash = ?",
                (img_hash,)
            )
            result = self.cursor.fetchone()
            
            if result:
                img_path, pptx_path, extract_date = result
                return {
                    'hash': img_hash,
                    'path': img_path,
                    'ppt_path': pptx_path,
                    'extract_date': extract_date,
                    'name': Path(img_path).name,
                    'ppt_name': Path(pptx_path).name
                }
            return None
        except Exception as e:
            print(f"获取图片信息时出错: {str(e)}")
            return None

    def get_image_stats(self) -> dict:
        """获取图片库统计信息"""
        if not self.cursor:
            raise ValueError("数据库未初始化")
        
        try:
            stats = {
                'total': 0,
                'background': 0,
                'icon': 0,
                'normal': 0,
                'ppt_count': 0
            }
            
            # 获取总图片数和各类型图片数量
            self.cursor.execute(f"""
                SELECT img_type, COUNT(*) 
                FROM {self.table_name} 
                WHERE is_duplicate = 0 
                GROUP BY img_type
            """)
            for img_type, count in self.cursor.fetchall():
                stats[img_type] = count
                stats['total'] += count
            
            # 获取PPT文件数量
            self.cursor.execute(f"""
                SELECT COUNT(DISTINCT pptx_path) 
                FROM {self.table_name} 
                WHERE is_duplicate = 0
            """)
            stats['ppt_count'] = self.cursor.fetchone()[0]
            
            return stats
        except Exception as e:
            print(f"获取统计信息时出错: {str(e)}")
            return {}