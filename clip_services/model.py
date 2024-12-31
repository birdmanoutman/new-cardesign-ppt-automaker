import torch
from transformers import CLIPProcessor, CLIPModel
import logging
from typing import List, Dict, Union
import io
from PIL import Image
import os

# 设置环境变量，使用国内镜像
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HF_HOME'] = '/root/.cache/huggingface'  # 设置缓存目录

logger = logging.getLogger(__name__)

class ClipModel:
    def __init__(self):
        logger.info("正在初始化CLIP模型...")
        # 使用CLIP ViT-Large/14模型
        self.model_name = "openai/clip-vit-large-patch14"
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"使用设备: {self.device}")
        
        # 从镜像站下载模型
        self.model = CLIPModel.from_pretrained(
            self.model_name,
            cache_dir="/root/.cache/huggingface",
            local_files_only=False,
            resume_download=True
        ).to(self.device)
        
        self.processor = CLIPProcessor.from_pretrained(
            self.model_name,
            cache_dir="/root/.cache/huggingface",
            local_files_only=False,
            resume_download=True
        )
        
        # 预定义的标签类别
        self.categories = {
            "color": ["red", "blue", "green", "yellow", "orange", "purple", "black", "white", "gray", "brown"],
            "emotion": ["happy", "sad", "angry", "peaceful", "energetic", "calm", "dynamic", "elegant"],
            "object": ["car", "building", "person", "tree", "road", "sky", "water", "mountain"],
            "scene": ["city", "nature", "interior", "exterior", "day", "night", "modern", "traditional"]
        }
        logger.info("CLIP模型初始化完成")
        
    async def predict(self, image_file) -> List[Dict[str, str]]:
        """预测图片的标签
        
        Args:
            image_file: 上传的图片文件
            
        Returns:
            List[Dict[str, str]]: 预测结果列表，每个结果包含类别、标签和置信度
        """
        try:
            # 读取图片
            image_data = await image_file.read()
            image = Image.open(io.BytesIO(image_data))
            
            results = []
            # 对每个类别进行预测
            for category, tags in self.categories.items():
                # 准备文本输入
                texts = [f"a photo of {tag}" for tag in tags]
                
                # 处理图片和文本
                inputs = self.processor(
                    images=image,
                    text=texts,
                    return_tensors="pt",
                    padding=True
                )
                
                # 将输入移到正确的设备上
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                
                # 获取预测结果
                outputs = self.model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = torch.nn.functional.softmax(logits_per_image, dim=1)[0]
                
                # 获取最高置信度的标签
                max_prob, max_idx = torch.max(probs, dim=0)
                best_tag = tags[max_idx]
                
                # 添加到结果列表
                results.append({
                    "category": category,
                    "tag": best_tag,
                    "confidence": float(max_prob)
                })
            
            return results
            
        except Exception as e:
            logger.error(f"预测过程中出错: {str(e)}")
            raise
            
    async def compute_similarity(self, image_file, text: Union[str, List[str]]) -> Union[float, List[float]]:
        """计算图片与文本的相似度
        
        Args:
            image_file: 上传的图片文件
            text: 文本提示词或提示词列表
            
        Returns:
            Union[float, List[float]]: 相似度分数或分数列表
        """
        try:
            # 读取图片
            image_data = await image_file.read()
            image = Image.open(io.BytesIO(image_data))
            
            # 如果输入是单个字符串，转换为列表
            if isinstance(text, str):
                texts = [text]
            else:
                texts = text
            
            # 处理图片和文本
            inputs = self.processor(
                images=image,
                text=texts,
                return_tensors="pt",
                padding=True
            )
            
            # 将输入移到正确的设备上
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # 获取预测结果
            outputs = self.model(**inputs)
            logits_per_image = outputs.logits_per_image
            
            # 计算相似度分数
            similarities = torch.nn.functional.softmax(logits_per_image, dim=1)[0]
            
            # 如果输入是单个字符串  返回单个分数
            if isinstance(text, str):
                return float(similarities[0])
            
            # 否则返回分数列表
            return [float(s) for s in similarities]
            
        except Exception as e:
            logger.error(f"计算相似度时出错: {str(e)}")
            raise 