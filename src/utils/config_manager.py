class ConfigManager:
    def __init__(self):
        self.load_config()
    
    def load_config(self):
        """加载配置"""
        self.date_config = {
            'min_year': 1949,
            'max_year': datetime.now().year,
        }
        
        self.file_config = {
            'cache_size': 1000,
            'ignored_files': [
                r'^\.',
                r'^desktop\.ini$',
                r'^thumbs\.db$',
                r'^~\$',
            ]
        } 