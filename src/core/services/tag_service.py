import aiohttp
import logging
from typing import List, Dict
from pathlib import Path
from ..interfaces.ai_service import IAIService
from ...utils.config.settings import Settings

class TagService:
    """标签服务 - 负责与AI服务通信"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.ai_config = settings.AI_SERVICE_CONFIG['clip']
        self.logger = logging.getLogger(__name__)
    
    async def get_image_tags(self, image_path: str) -> List[Dict[str, float]]:
        """获取图片标签
        
        Args:
            image_path: 图片路径
            
        Returns:
            List[Dict[str, float]]: 标签及其置信度列表
        """
        try:
            # 构建API URL
            url = f"http://{self.ai_config['host']}:{self.ai_config['port']}/predict"
            
            # 准备文件
            files = {'image': open(image_path, 'rb')}
            
            # 发送请求
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=files, timeout=self.ai_config['timeout']) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        error_msg = await resp.text()
                        raise Exception(f"AI服务请求失败: {error_msg}")
                        
        except Exception as e:
            self.logger.error(f"获取图片标签失败: {str(e)}")
            raise 