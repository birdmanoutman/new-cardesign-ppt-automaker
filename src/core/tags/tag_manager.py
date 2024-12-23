from typing import List, Dict
from datetime import datetime

class TagManager:
    def __init__(self, db_manager):
        self.db = db_manager
        
    def add_tag(self, name: str, category_id: int = None, parent_id: int = None, 
                prompt_words: str = None, confidence_threshold: float = None):
        """添加标签"""
        try:
            # 计算标签层级
            level = 1
            if parent_id:
                self.db.execute(
                    "SELECT level FROM tags WHERE id = ?", (parent_id,)
                )
                parent_level = self.db.fetchone()
                if parent_level:
                    level = parent_level[0] + 1
            
            self.db.execute(
                """
                INSERT INTO tags 
                (name, category_id, parent_id, prompt_words, 
                 confidence_threshold, level, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (name, category_id, parent_id, prompt_words,
                 confidence_threshold, level,
                 datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )
            self.db.commit()
            return self.db.cursor.lastrowid
        except Exception as e:
            print(f"添加标签失败: {str(e)}")
            self.db.rollback()
            raise

    def get_tag_tree(self, category_id: int = None) -> List[Dict]:
        """获取标签树结构"""
        try:
            query = """
                WITH RECURSIVE tag_tree AS (
                    SELECT 
                        t.id, t.name, t.category_id, t.parent_id, 
                        t.prompt_words, t.confidence_threshold,
                        t.level, t.created_at,
                        CAST(t.name AS TEXT) as path
                    FROM tags t
                    WHERE t.parent_id IS NULL
                    
                    UNION ALL
                    
                    SELECT 
                        t.id, t.name, t.category_id, t.parent_id,
                        t.prompt_words, t.confidence_threshold,
                        t.level, t.created_at,
                        tt.path || '/' || t.name
                    FROM tags t
                    JOIN tag_tree tt ON t.parent_id = tt.id
                )
                SELECT 
                    tt.*,
                    tc.name as category_name,
                    tc.type as category_type,
                    (SELECT COUNT(*) FROM image_tags WHERE tag_id = tt.id) as usage_count
                FROM tag_tree tt
                LEFT JOIN tag_categories tc ON tt.category_id = tc.id
            """
            
            if category_id:
                query += " WHERE tt.category_id = ?"
                self.db.execute(query, (category_id,))
            else:
                self.db.execute(query)
            
            rows = self.db.cursor.fetchall()
            
            # 构建树形结构
            tag_dict = {}
            tree = []
            
            for row in rows:
                tag = {
                    'id': row[0],
                    'name': row[1],
                    'category_id': row[2],
                    'parent_id': row[3],
                    'prompt_words': row[4],
                    'confidence_threshold': row[5],
                    'level': row[6],
                    'created_at': row[7],
                    'path': row[8],
                    'category_name': row[9],
                    'category_type': row[10],
                    'usage_count': row[11],
                    'children': []
                }
                
                tag_dict[tag['id']] = tag
                
                if tag['parent_id'] is None:
                    tree.append(tag)
                else:
                    parent = tag_dict.get(tag['parent_id'])
                    if parent:
                        parent['children'].append(tag)
            
            return tree
            
        except Exception as e:
            print(f"获取标签树失败: {str(e)}")
            return []

    def init_default_categories(self, categories: Dict):
        """初始化默认分类和标签"""
        try:
            for category_type, category_data in categories.items():
                # 添加分类
                self.db.execute(
                    """
                    INSERT OR IGNORE INTO tag_categories 
                    (name, type, prompt_template, confidence_threshold, priority, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        category_data['name'],
                        category_type,
                        ';'.join(category_data['prompts']),
                        category_data['confidence_threshold'],
                        category_data['priority'],
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    )
                )
                
                # 获取分类ID
                self.db.execute(
                    "SELECT id FROM tag_categories WHERE type = ?",
                    (category_type,)
                )
                category_id = self.db.cursor.fetchone()[0]
                
                # 添加标签
                for tag_name in category_data['tags']:
                    self.db.execute(
                        """
                        INSERT OR IGNORE INTO tags 
                        (name, category_id, created_at)
                        VALUES (?, ?, ?)
                        """,
                        (
                            tag_name,
                            category_id,
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        )
                    )
            
            self.db.commit()
            print("默认分类和标签初始化完成")
            
        except Exception as e:
            print(f"初始化默认分类失败: {str(e)}")
            self.db.rollback()

    def update_tag(self, tag_id: int, **kwargs):
        """更新标签"""
        try:
            update_fields = []
            params = []
            for key, value in kwargs.items():
                if value is not None:
                    update_fields.append(f"{key} = ?")
                    params.append(value)
            
            if update_fields:
                params.append(tag_id)
                query = f"""
                    UPDATE tags 
                    SET {', '.join(update_fields)}
                    WHERE id = ?
                """
                self.db.execute(query, params)
                self.db.commit()
                
        except Exception as e:
            print(f"更新标签失败: {str(e)}")
            self.db.rollback()

    def delete_tag(self, tag_id: int):
        """删除标签"""
        try:
            self.db.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
            self.db.commit()
        except Exception as e:
            print(f"删除标签失败: {str(e)}")
            self.db.rollback()

    def get_tag_categories(self) -> List[Dict]:
        """获取所有标签分类"""
        try:
            self.db.execute(
                """
                SELECT id, name, type, prompt_template, 
                       confidence_threshold, priority
                FROM tag_categories
                ORDER BY priority
                """
            )
            return [{
                'id': row[0],
                'name': row[1],
                'type': row[2],
                'prompt_template': row[3],
                'confidence_threshold': row[4],
                'priority': row[5]
            } for row in self.db.cursor.fetchall()]
        except Exception as e:
            print(f"获取标签分类失败: {str(e)}")
            return []

    def get_image_tags(self, img_hash: str) -> List[Dict]:
        """获取图片的标签"""
        try:
            self.db.execute(
                """
                SELECT 
                    t.id, t.name, t.category_id, t.parent_id,
                    t.prompt_words, t.confidence_threshold,
                    t.level, t.created_at,
                    tc.name as category_name,
                    tc.type as category_type,
                    it.confidence as tag_confidence
                FROM image_tags it
                JOIN tags t ON it.tag_id = t.id
                LEFT JOIN tag_categories tc ON t.category_id = tc.id
                WHERE it.img_hash = ?
                ORDER BY tc.priority, t.level, t.name
                """,
                (img_hash,)
            )
            
            return [{
                'id': row[0],
                'name': row[1],
                'category_id': row[2],
                'parent_id': row[3],
                'prompt_words': row[4],
                'confidence_threshold': row[5],
                'level': row[6],
                'created_at': row[7],
                'category_name': row[8],
                'category_type': row[9],
                'confidence': row[10]
            } for row in self.db.cursor.fetchall()]
            
        except Exception as e:
            print(f"获取图片标签失败: {str(e)}")
            return []

    def add_image_tag(self, img_hash: str, tag_id: int, confidence: float = None):
        """为图片添加标签"""
        try:
            self.db.execute(
                """
                INSERT OR REPLACE INTO image_tags 
                (img_hash, tag_id, confidence, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    img_hash, 
                    tag_id, 
                    confidence,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
            )
            self.db.commit()
        except Exception as e:
            print(f"添加图片标签失败: {str(e)}")
            self.db.rollback()

    def remove_image_tag(self, img_hash: str, tag_id: int):
        """移除图片的标签"""
        try:
            self.db.execute(
                "DELETE FROM image_tags WHERE img_hash = ? AND tag_id = ?",
                (img_hash, tag_id)
            )
            self.db.commit()
        except Exception as e:
            print(f"移除图片标签失败: {str(e)}")
            self.db.rollback()