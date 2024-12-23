from ..interfaces.storage import IStorageProvider
from ..exceptions.base import StorageError
from pathlib import Path
import sqlite3
from datetime import datetime
import logging
from typing import Dict, Optional

class DatabaseManager(IStorageProvider):
    def __init__(self, app_data_dir: Path):
        self.db_path = app_data_dir / "image_gallery.db"
        self.db_conn = None
        self.cursor = None
        self.logger = logging.getLogger(__name__)
        
        # 确保目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()

    def save_image(self, image_data: Dict) -> str:
        try:
            # 从原有的 add_image_to_db 方法迁移代码
            self.execute(
                """INSERT INTO images 
                   (img_hash, img_path, img_name, extract_date, img_type, format, width, height)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    image_data['hash'],
                    str(image_data['path']),
                    image_data['name'],
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'normal',
                    image_data['format'],
                    image_data['width'],
                    image_data['height']
                )
            )
            self.commit()
            return image_data['hash']
        except Exception as e:
            raise StorageError(f"保存图片失败: {str(e)}")

    def get_image(self, image_id: str) -> Dict:
        try:
            result = self.execute(
                "SELECT * FROM images WHERE img_hash = ?",
                (image_id,)
            ).fetchone()
            if not result:
                raise StorageError(f"找不到图片: {image_id}")
            return dict(result)
        except Exception as e:
            raise StorageError(f"获取图片失败: {str(e)}")

    # 需要添加完整的数据库初始化和其他必要方法
    def init_database(self):
        """初始化数据库连接和表结构"""
        try:
            self.db_conn = sqlite3.connect(str(self.db_path))
            self.db_conn.row_factory = sqlite3.Row
            self.cursor = self.db_conn.cursor()
            self._init_tables()
        except Exception as e:
            raise StorageError(f"初始化数据库失败: {str(e)}")

    def _init_tables(self):
        """初始化数据库表"""
        try:
            # 创建图片表
            self.execute("""
                CREATE TABLE IF NOT EXISTS images (
                    img_hash TEXT PRIMARY KEY,
                    img_path TEXT,
                    img_name TEXT,
                    extract_date TEXT,
                    img_type TEXT,
                    format TEXT,
                    width INTEGER,
                    height INTEGER
                )
            """)
            # 添加其他必要的表...
            self.commit()
        except Exception as e:
            raise StorageError(f"创建数据库表失败: {str(e)}")

    def execute(self, sql: str, params: Optional[tuple] = None):
        """执行SQL语句"""
        try:
            if params:
                return self.cursor.execute(sql, params)
            return self.cursor.execute(sql)
        except Exception as e:
            raise StorageError(f"执行SQL失败: {str(e)}")

    def commit(self):
        """提交事务"""
        self.db_conn.commit()

    def close(self):
        """关闭数据库连接"""
        if self.cursor:
            self.cursor.close()
        if self.db_conn:
            self.db_conn.close()

    # 保留其他必要的数据库方法...