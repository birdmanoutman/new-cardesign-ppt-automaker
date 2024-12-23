from pathlib import Path
from typing import List, Dict, Optional
from PIL import Image
import hashlib
from datetime import datetime
import logging
from tqdm import tqdm
from ...utils.config.settings import Settings

class PPTExtractor:
    """PPT提取器 - 负责从PPT中提取图片到图库"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
        self.total_processed_ppts = 0
        
    def extract_images_from_folder(self, folder_path: str, output_folder: str, 
                                 progress_callback=None) -> Dict[str, List[Dict]]:
        """从PPT文件夹中提取图片到图库
        
        Args:
            folder_path: PPT文件夹路径
            output_folder: 图片输出文件夹
            progress_callback: 进度回调函数
            
        Returns:
            Dict[str, List[Dict]]: 包含成功和失败信息的字典
                {
                    'success': [图片信息列表],
                    'failed': [失败信息列表]
                }
        """
        results = {'success': [], 'failed': []}
        try:
            folder_path = Path(folder_path)
            if not folder_path.exists():
                raise FileNotFoundError(f"文件夹不存在: {folder_path}")
            
            # 获取所有PPT文件
            ppt_files = []
            for ext in ['.ppt', '.pptx']:
                ppt_files.extend(folder_path.glob(f"**/*{ext}"))
            
            if not ppt_files:
                self.logger.warning(f"未在 {folder_path} 找到PPT文件")
                return results
            
            # 创建PPTProcessor实例
            from .ppt_processor import PPTProcessor
            ppt_processor = PPTProcessor()
            
            # 使用tqdm创建进度条
            for ppt_path in tqdm(ppt_files, desc="处理PPT文件"):
                try:
                    # 更新进度
                    if progress_callback:
                        current_idx = ppt_files.index(ppt_path) + 1
                        progress_callback(current_idx, len(ppt_files), f"正在处理: {ppt_path.name}")
                    
                    # 打开PPT文件
                    ppt_processor.open_presentation(str(ppt_path))
                    
                    # 提取图片
                    images = ppt_processor.extract_all_images(output_folder)
                    if not images:
                        continue
                        
                    # 处理每个提取的图片
                    for img_info in images:
                        try:
                            processed_info = self._process_single_image(img_info, ppt_path)
                            if processed_info:
                                results['success'].append(processed_info)
                        except Exception as img_e:
                            self.logger.error(f"处理图片 {img_info['path']} 时出错: {str(img_e)}")
                            results['failed'].append({
                                'path': img_info['path'],
                                'error': str(img_e),
                                'ppt': str(ppt_path)
                            })
                    
                    self.total_processed_ppts += 1
                    
                except Exception as e:
                    self.logger.error(f"处理文件 {ppt_path} 时出错: {str(e)}")
                    results['failed'].append({
                        'path': str(ppt_path),
                        'error': str(e)
                    })
            
            return results
            
        except Exception as e:
            self.logger.error(f"处理文件夹 {folder_path} 时出错: {str(e)}")
            return results
    
    def _process_single_image(self, img_info: Dict, ppt_path: Path) -> Optional[Dict]:
        """处理单个图片
        
        Args:
            img_info: 图片信息字典
            ppt_path: PPT文件路径
            
        Returns:
            Optional[Dict]: 处理成功返回图片信息，失败返回None
        """
        try:
            # 获取图片信息
            img_path = img_info['path']
            slide_idx = img_info['slide']
            shape_idx = img_info['shape']
            
            # 打开图片获取详细信息
            with Image.open(img_path) as img:
                width, height = img.size
                img_format = img.format
                
            # 计算图片哈希
            with open(img_path, 'rb') as f:
                img_hash = hashlib.md5(f.read()).hexdigest()
            
            # 添加到数据库
            self._add_image_to_db(
                img_hash, img_path, img_format, width, height,
                ppt_path, slide_idx, shape_idx
            )
            
            # 返回完整信息
            return {
                **img_info,
                'hash': img_hash,
                'width': width,
                'height': height,
                'format': img_format,
                'source_ppt': str(ppt_path)
            }
            
        except Exception as e:
            self.logger.error(f"处理图片失败: {str(e)}")
            return None
    
    def _add_image_to_db(self, img_hash: str, img_path: str, img_format: str,
                        width: int, height: int, ppt_path: Path, 
                        slide_idx: int, shape_idx: str):
        """将图片信息添加到数据库"""
        try:
            # 开始事务
            self.db.execute("BEGIN TRANSACTION")
            
            # 添加图片记录
            self.db.execute(
                f"""
                INSERT OR IGNORE INTO {self.db.table_name}
                (img_hash, img_path, img_name, extract_date, img_type, format, width, height)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    img_hash,
                    str(img_path),
                    Path(img_path).name,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'normal',
                    img_format,
                    width,
                    height
                )
            )
            
            # 添加PPT映射关系
            self.db.execute(
                """
                INSERT OR IGNORE INTO image_ppt_mapping
                (img_hash, pptx_path, slide_index, shape_index, extract_date)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    img_hash,
                    str(ppt_path),
                    slide_idx,
                    str(shape_idx),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
            )
            
            # 添加PPT源
            self.db.execute(
                """
                INSERT OR REPLACE INTO ppt_sources 
                (path, added_date) VALUES (?, ?)
                """,
                (
                    str(ppt_path),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
            )
            
            # 提交事务
            self.db.commit()
            
        except Exception as e:
            self.logger.error(f"添加图片到数据库失败: {str(e)}")
            self.db.rollback()
            raise
    
    def get_ppt_sources(self) -> List[str]:
        """获取所有PPT源文件夹"""
        try:
            self.db.execute("SELECT path FROM ppt_sources ORDER BY added_date DESC")
            return [row[0] for row in self.db.fetchall()]
        except Exception as e:
            self.logger.error(f"获取PPT源失败: {str(e)}")
            return []
    
    def get_total_ppts(self) -> int:
        """获取已处理的PPT总数"""
        try:
            self.db.execute("SELECT COUNT(DISTINCT pptx_path) FROM image_ppt_mapping")
            return self.db.fetchone()[0]
        except Exception as e:
            self.logger.error(f"获取PPT总数失败: {str(e)}")
            return 0