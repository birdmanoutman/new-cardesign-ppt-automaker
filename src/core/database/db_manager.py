from pathlib import Path
import sqlite3
from datetime import datetime
import logging
from typing import List, Dict, Optional, Union, Tuple
from contextlib import contextmanager

class DatabaseManager:
    """数据库管理器 - 负责所有数据库操作"""
    
    def __init__(self, app_data_dir: Path):
        self.db_path = app_data_dir / "image_gallery.db"
        self.db_conn = None
        self.cursor = None
        self.table_name = "images"
        self.logger = logging.getLogger(__name__)
        
        # 确保目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库
        self.init_database()
    
    def init_database(self):
        """初始化数据库连接和表结构"""
        try:
            # 连接数据库(如果不存在会自动创建)
            self.db_conn = sqlite3.connect(str(self.db_path))
            self.db_conn.row_factory = sqlite3.Row  # 启用字典行工厂
            self.cursor = self.db_conn.cursor()
            
            # 创建表结构(如果不存在)
            self._init_tables()
            
            self.logger.info(f"数据库连接成功: {self.db_path}")
            
        except Exception as e:
            self.logger.error(f"初始化数据库时出错: {str(e)}")
            raise
    
    @contextmanager
    def transaction(self):
        """事务上下文管理器"""
        try:
            self.execute("BEGIN TRANSACTION")
            yield
            self.commit()
        except Exception as e:
            self.logger.error(f"事务执行失败: {str(e)}")
            self.rollback()
            raise
    
    def _init_tables(self):
        """初始化数据库表"""
        try:
            # 删除并重建settings表
            self.execute("DROP TABLE IF EXISTS settings")
            self.execute("""
                CREATE TABLE settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT
                )
            """)
            
            # 创建PPT源文件表
            self.execute("""
                CREATE TABLE IF NOT EXISTS ppt_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE,
                    added_date TEXT
                )
            """)
            
            # 创建标签分类表
            self.execute("""
                CREATE TABLE IF NOT EXISTS tag_categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    type TEXT UNIQUE,
                    prompt_template TEXT,
                    confidence_threshold REAL,
                    priority INTEGER DEFAULT 0,
                    created_at TEXT
                )
            """)
            
            # 创建标签表
            self.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category_id INTEGER,
                    parent_id INTEGER,
                    prompt_words TEXT,
                    confidence_threshold REAL,
                    level INTEGER DEFAULT 1,
                    created_at TEXT,
                    FOREIGN KEY (category_id) REFERENCES tag_categories (id),
                    FOREIGN KEY (parent_id) REFERENCES tags (id)
                )
            """)
            
            # 创建图片标签关联表
            self.execute("""
                CREATE TABLE IF NOT EXISTS image_tags (
                    img_hash TEXT,
                    tag_id INTEGER,
                    confidence REAL,
                    created_at TEXT,
                    PRIMARY KEY (img_hash, tag_id),
                    FOREIGN KEY (tag_id) REFERENCES tags (id)
                )
            """)
            
            # 创建图片PPT映射表
            self.execute("""
                CREATE TABLE IF NOT EXISTS image_ppt_mapping (
                    img_hash TEXT,
                    pptx_path TEXT,
                    slide_index INTEGER,
                    shape_index INTEGER,
                    created_at TEXT,
                    PRIMARY KEY (img_hash, pptx_path, slide_index, shape_index)
                )
            """)
            
            self.commit()
            
        except Exception as e:
            self.logger.error(f"初始化数据库表失败: {str(e)}")
            raise
    
    def execute(self, sql: str, params: Optional[Union[tuple, dict]] = None) -> sqlite3.Cursor:
        """执行SQL语句"""
        try:
            if params:
                return self.cursor.execute(sql, params)
            return self.cursor.execute(sql)
        except Exception as e:
            self.logger.error(f"执行SQL失败: {sql}\n错误: {str(e)}")
            raise
    
    def executemany(self, sql: str, params_list: List[Union[tuple, dict]]) -> sqlite3.Cursor:
        """批量执行SQL语句"""
        try:
            return self.cursor.executemany(sql, params_list)
        except Exception as e:
            self.logger.error(f"批量执行SQL失败: {sql}\n错误: {str(e)}")
            raise
    
    def fetchone(self) -> Optional[sqlite3.Row]:
        """获取一条记录"""
        return self.cursor.fetchone()
    
    def fetchall(self) -> List[sqlite3.Row]:
        """获取所有记录"""
        return self.cursor.fetchall()
    
    def commit(self):
        """提交事务"""
        self.db_conn.commit()
    
    def rollback(self):
        """回滚事务"""
        self.db_conn.rollback()
    
    def close(self):
        """关闭数据库连接"""
        if self.cursor:
            self.cursor.close()
        if self.db_conn:
            self.db_conn.close()
    
    def get_image_by_hash(self, img_hash: str) -> Optional[Dict]:
        """根据哈希值获取图片信息"""
        try:
            result = self.execute(
                f"SELECT * FROM {self.table_name} WHERE img_hash = ?",
                (img_hash,)
            ).fetchone()
            return dict(result) if result else None
        except Exception as e:
            self.logger.error(f"获取图片信息失败: {str(e)}")
            return None
    
    def get_image_tags(self, img_hash: str) -> List[Dict]:
        """获取图片的所有标签"""
        try:
            sql = """
                SELECT t.*, tc.name as category_name, it.confidence
                FROM image_tags it
                JOIN tags t ON it.tag_id = t.id
                LEFT JOIN tag_categories tc ON t.category_id = tc.id
                WHERE it.img_hash = ?
                ORDER BY it.confidence DESC
            """
            results = self.execute(sql, (img_hash,)).fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            self.logger.error(f"获取图片标签失败: {str(e)}")
            return []
    
    def add_image_tag(self, img_hash: str, tag_id: int, confidence: float, source: str = 'auto'):
        """添加图片标签"""
        try:
            with self.transaction():
                self.execute(
                    """
                    INSERT OR REPLACE INTO image_tags
                    (img_hash, tag_id, confidence, created_at, source)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (img_hash, tag_id, confidence, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), source)
                )
        except Exception as e:
            self.logger.error(f"添加图片标签失败: {str(e)}")
            raise
    
    def remove_image_tag(self, img_hash: str, tag_id: int):
        """移除图片标签"""
        try:
            with self.transaction():
                self.execute(
                    "DELETE FROM image_tags WHERE img_hash = ? AND tag_id = ?",
                    (img_hash, tag_id)
                )
        except Exception as e:
            self.logger.error(f"移除图片标签失败: {str(e)}")
            raise 