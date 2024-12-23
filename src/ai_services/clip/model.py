from typing import List, Dict
import torch
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import logging

class ClipModel:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(self.device)
        self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        self.logger = logging.getLogger(__name__)
        
        # 默认标签类别
        self.categories = {
            'object': ['car', 'person', 'building', 'animal', 'plant'],
            'scene': ['interior', 'exterior', 'street', 'nature', 'urban'],
            'style': ['modern', 'classic', 'sporty', 'luxury', 'minimalist'],
            'color': ['red', 'blue', 'green', 'yellow', 'white']
        }
        
    async def predict(self, image_file) -> List[Dict[str, float]]:
        """预测图片标签

        Args:
            image_file: 上传的图片文件

        Returns:
            List[Dict[str, float]]: 标签及其置信度列表
        """
        try:
            # 读取图片
            image = Image.open(image_file.file).convert('RGB')
            
            results = []
            # 对每个类别进行预测
            for category, tags in self.categories.items():
                # 构建提示文本
                prompts = [f"This image contains {tag}" for tag in tags]
                
                # 处理图片和文本
                inputs = self.processor(
                    images=image,
                    text=prompts,
                    return_tensors="pt",
                    padding=True
                ).to(self.device)
                
                # 获取预测结果
                outputs = self.model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = torch.nn.functional.softmax(logits_per_image, dim=1)
                
                # 添加预测结果
                for tag, prob in zip(tags, probs[0].tolist()):
                    if prob > 0.5:  # 只返回置信度大于0.5的标签
                        results.append({
                            'category': category,
                            'tag': tag,
                            'confidence': prob
                        })
            
            # 按置信度排序
            results.sort(key=lambda x: x['confidence'], reverse=True)
            return results
            
        except Exception as e:
            self.logger.error(f"预测失败: {str(e)}")
            raise 