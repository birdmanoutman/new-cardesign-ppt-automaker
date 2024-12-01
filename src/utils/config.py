import json
from pathlib import Path

class Config:
    def __init__(self):
        self.config_path = Path("config.json")
        self.default_config = {
            "file_rules": {},
            "ppt_templates": {},
            "recent_files": []
        }
        self.current_config = self.load_config()
    
    def load_config(self):
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self.default_config.copy()
    
    def save_config(self):
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.current_config, f, ensure_ascii=False, indent=4) 