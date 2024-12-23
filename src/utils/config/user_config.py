import json
from pathlib import Path

class UserConfig:
    """用户配置管理 - 处理用户偏好设置"""
    
    def __init__(self, config_file="user_preferences.json"):
        self.config_path = Path(config_file)
        self.default_config = {
            "file_rules": {},
            "ppt_templates": {},
            "recent_files": []
        }
        self.current_config = self.load_config()
    
    def load_config(self):
        """加载用户配置"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self.default_config.copy()
    
    def save_config(self):
        """保存用户配置"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.current_config, f, ensure_ascii=False, indent=4) 