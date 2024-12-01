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
        self.table_name = "images"
        
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
        # 图片主表
        table_sql = f'''
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                img_hash TEXT PRIMARY KEY,  # 使用哈希作为主键
                img_path TEXT,
                img_name TEXT,
                extract_date TEXT,
                img_type TEXT,
                format TEXT,
                width INTEGER,
                height INTEGER,
                file_size INTEGER
            )
        '''
        self.cursor.execute(table_sql)
        
        # 图片-PPT映射关系表
        mapping_sql = '''
            CREATE TABLE IF NOT EXISTS image_ppt_mapping (
                img_hash TEXT,
                pptx_path TEXT,
                pptx_name TEXT,
                slide_index INTEGER,
                shape_index TEXT,
                extract_date TEXT,
                PRIMARY KEY (img_hash, pptx_path, slide_index, shape_index),
                FOREIGN KEY (img_hash) REFERENCES images(img_hash)
            )
        '''
        self.cursor.execute(mapping_sql)
        
        # 添加设置表
        settings_sql = '''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        '''
        self.cursor.execute(settings_sql)
        
        # 添加PPT源表
        sources_sql = '''
            CREATE TABLE IF NOT EXISTS ppt_sources (
                path TEXT PRIMARY KEY,
                added_date TEXT
            )
        '''
        self.cursor.execute(sources_sql)
        
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
        
        # 计比例
        width_ratio = img_width / ppt_width
        height_ratio = img_height / ppt_height
        
        # 如果图片尺寸接近或大于PPT尺寸，认为是景图
        return width_ratio >= 0.8 and height_ratio >= 0.8
    
    def _is_duplicate(self, img_hash: str, check_file_exists: bool = True) -> bool:
        """
        检查图片是否重复
        check_file_exists: 是否检查文件是否存在
        """
        self.cursor.execute(
            f"SELECT img_path FROM {self.table_name} WHERE img_hash=? LIMIT 1",
            (img_hash,)
        )
        result = self.cursor.fetchone()
        
        if not result:
            return False
        
        if check_file_exists:
            # 检查文件是否实际存在
            img_path = result[0]
            if not os.path.exists(img_path):
                # 如果文件不存在，删除数据库记录
                self.cursor.execute(
                    f"DELETE FROM {self.table_name} WHERE img_hash=?",
                    (img_hash,)
                )
                self.db_conn.commit()
                return False
        
        return True
    
    def _save_image(self, img: Image.Image, img_path: str):
        """保存图片"""
        # 确保保存路径存在
        os.makedirs(os.path.dirname(img_path), exist_ok=True)
        
        # 转换图片格式并保存
        if img.mode in ['RGBA', 'P']:
            img = img.convert('RGB')
        img.save(img_path)
    
    def _determine_image_type(self, content_type: str, img_data: bytes) -> str:
        """
        确定图片类型
        返回: 'background' | 'icon' | 'normal'
        """
        try:
            # 如果是WMF/EMF格式，标记为icon
            if content_type in ['image/x-wmf', 'image/x-emf']:
                return 'icon'
            
            # 打开图片获取尺寸
            img = Image.open(io.BytesIO(img_data))
            width, height = img.size
            
            # 如果尺寸太小，可能是图标
            if width < 100 or height < 100:
                return 'icon'
            
            # 如果是大尺寸图片，可能是背景
            if width >= 800 and height >= 600:
                return 'background'
            
            return 'normal'
        except:
            return 'normal'  # 如果无法判断，默认为普通图片
    
    def extract_background_images(self, ppt_path: str, output_folder: str) -> list:
        """从PPT中提取所有图片并建立索引"""
        try:
            # 开始事务
            self.db_conn.execute("BEGIN TRANSACTION")
            
            ppt_path = Path(ppt_path)
            output_folder = Path(output_folder)
            output_folder.mkdir(parents=True, exist_ok=True)
            
            # 使用列表收集所有要插入的数据
            insert_data = []
            
            # 打开PPT文件
            presentation = Presentation(ppt_path)
            
            # 遍历幻灯片和形状
            for slide_idx, slide in enumerate(presentation.slides, 1):
                for shape_idx, shape in enumerate(slide.shapes, 1):
                    try:
                        if not hasattr(shape, 'image'):
                            continue
                        
                        img_data = shape.image.blob
                        img_hash = self._calculate_image_hash(img_data)
                        
                        # 检查是否重复
                        if self._is_duplicate(img_hash):
                            continue
                        
                        # 处理和保存图片
                        img_info = self._process_and_save_image(
                            img_data, 
                            shape.image.content_type,
                            ppt_path,
                            output_folder,
                            slide_idx,
                            shape_idx
                        )
                        
                        if img_info:
                            insert_data.append(img_info)
                            
                    except Exception as e:
                        print(f"处理图片时出错 (slide {slide_idx}, shape {shape_idx}): {str(e)}")
                        continue
            
            # 批量插入数据库
            if insert_data:
                self._batch_insert_images(insert_data)
                
            # 提交事务
            self.db_conn.commit()
            return insert_data
            
        except Exception as e:
            # 发生错误时回滚
            self.db_conn.rollback()
            print(f"提取图片时出错: {str(e)}")
            raise

    def _process_and_save_image(self, img_data, content_type, ppt_path, output_folder, 
                              slide_idx, shape_idx) -> dict:
        """处理并保存单个图片"""
        try:
            img_hash = self._calculate_image_hash(img_data)
            
            # 检查是否已存在相同哈希的图片
            self.cursor.execute(
                f"SELECT img_path FROM {self.table_name} WHERE img_hash = ?",
                (img_hash,)
            )
            existing = self.cursor.fetchone()
            
            if existing:
                # 如果图片已存在，只添加PPT映射关系
                self._add_ppt_mapping(img_hash, ppt_path, ppt_path.name, slide_idx, shape_idx)
                return None
            
            # 处理新图片
            ext = self._get_image_extension(content_type, img_data)
            img_name = f"{img_hash[:8]}{ext}"  # 使用哈希值作为文件名
            img_path = output_folder / img_name
            
            # 保存图片
            try:
                img = Image.open(io.BytesIO(img_data))
                if img.format == 'MPO' or img.mode in ['RGBA', 'P']:
                    img = img.convert('RGB')
                img.save(img_path, quality=95, optimize=True)
                width, height = img.size
            except:
                img_path.parent.mkdir(parents=True, exist_ok=True)
                with open(img_path, 'wb') as f:
                    f.write(img_data)
                width = height = 0
            
            # 插入图片信息
            self.cursor.execute(
                f"""
                INSERT INTO {self.table_name} 
                (img_hash, img_path, img_name, extract_date, img_type, format, 
                width, height, file_size)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (img_hash, str(img_path), img_name, 
                 datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                 self._determine_image_type(content_type, img_data),
                 ext[1:].upper(), width, height, len(img_data))
            )
            
            # 添加PPT映射关系
            self._add_ppt_mapping(img_hash, ppt_path, ppt_path.name, slide_idx, shape_idx)
            
            return {
                'hash': img_hash,
                'path': str(img_path),
                'name': img_name
            }
            
        except Exception as e:
            print(f"处理图片失败: {str(e)}")
            return None

    def _add_ppt_mapping(self, img_hash: str, ppt_path: Path, ppt_name: str, 
                        slide_idx: int, shape_idx: str):
        """添加图片-PPT映射关系"""
        self.cursor.execute(
            """
            INSERT OR REPLACE INTO image_ppt_mapping 
            (img_hash, pptx_path, pptx_name, slide_index, shape_index, extract_date)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (img_hash, str(ppt_path), ppt_name, slide_idx, str(shape_idx),
             datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )
        self.db_conn.commit()

    def _batch_insert_images(self, image_info_list: list):
        """批量插入图片信息"""
        if not image_info_list:
            return
        
        insert_sql = f"""
            INSERT OR REPLACE INTO {self.table_name} (
                img_hash, img_path, img_name, pptx_path, pptx_name,
                slide_index, shape_index, img_type, format,
                width, height, file_size, extract_date, is_duplicate
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """
        
        # 准备批量插入的数据
        values = [(
            info['img_hash'], info['img_path'], info['img_name'],
            info['pptx_path'], info['pptx_name'], info['slide_index'],
            info['shape_index'], info['img_type'], info['format'],
            info['width'], info['height'], info['file_size'],
            info['extract_date']
        ) for info in image_info_list]
        
        # 执行批量插入
        self.cursor.executemany(insert_sql, values)
        self.db_conn.commit()

    def _get_image_extension(self, content_type: str, img_data: bytes) -> str:
        """根据内容类型和文件头确定图片扩展名"""
        try:
            # 尝试使用PIL打开图片来确定格式
            img = Image.open(io.BytesIO(img_data))
            if img.format:
                # 特殊处理 MPO 格式
                if img.format == 'MPO':
                    return '.jpg'  # MPO 实际上是多帧的 JPEG
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
                'image/mpo': '.jpg',  # 添加 MPO 映射
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
        """获取指定图片的详信息"""
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

    def save_setting(self, key: str, value: str):
        """保存设置"""
        self.cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )
        self.db_conn.commit()

    def get_setting(self, key: str, default: str = None) -> str:
        """获取设置"""
        self.cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        result = self.cursor.fetchone()
        return result[0] if result else default

    def add_ppt_source(self, path: str):
        """添加PPT源文件夹"""
        self.cursor.execute(
            "INSERT OR REPLACE INTO ppt_sources (path, added_date) VALUES (?, ?)",
            (path, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )
        self.db_conn.commit()

    def get_ppt_sources(self) -> list:
        """获取所有PPT源文件夹"""
        self.cursor.execute("SELECT path FROM ppt_sources")
        return [row[0] for row in self.cursor.fetchall()]

    def get_image_ppt_mappings(self, img_hash: str) -> list:
        """获取图片被使用的所有PPT信息"""
        self.cursor.execute(
            """
            SELECT m.pptx_path, m.slide_index, m.shape_index, m.extract_date
            FROM image_ppt_mapping m
            WHERE m.img_hash = ?
            ORDER BY m.extract_date DESC
            """,
            (img_hash,)
        )
        
        mappings = []
        for row in self.cursor.fetchall():
            ppt_path, slide_idx, shape_idx, extract_date = row
            if os.path.exists(ppt_path):  # 只返回存在的PPT
                mappings.append({
                    'ppt_path': ppt_path,
                    'ppt_name': Path(ppt_path).name,
                    'slide': slide_idx,
                    'shape': shape_idx,
                    'extract_date': extract_date
                })
        return mappings