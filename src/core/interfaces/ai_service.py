from abc import ABC, abstractmethod
from typing import List, Dict

class IAIService(ABC):
    """AI服务接口定义"""
    
    @abstractmethod
    async def predict_tags(self, image_path: str) -> List[Dict[str, float]]:
        """预测图片标签
        
        Args:
            image_path: 图片路径
            
        Returns:
            List[Dict[str, float]]: 标签及其置信度列表
        """
        pass 