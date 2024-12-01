class NameProcessor:
    @staticmethod
    def to_camel_case(text: str) -> str:
        """将文本转换为驼峰命名格式"""
        if not re.search(r'[a-zA-Z]', text):
            return text
            
        words = re.split(r'[_\s-]+', text)
        result = []
        
        for i, word in enumerate(words):
            if not word:
                continue
            if i == 0:
                result.append(word.lower())
            else:
                result.append(word.capitalize())
        
        return ''.join(result)
    
    @staticmethod
    def normalize_spaces(text: str) -> str:
        """标准化空格和分隔符"""
        text = re.sub(r'\s+', '_', text)
        text = re.sub(r'_{2,}', '_', text)
        return text.strip('_') 