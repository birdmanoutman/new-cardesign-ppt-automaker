from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from model import ClipModel
import logging
from typing import List, Union, Optional
from pydantic import BaseModel
import json

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 定义响应模型
class PredictionResult(BaseModel):
    category: str
    tag: str
    confidence: float

class SimilarityRequest(BaseModel):
    text: Union[str, List[str]]

class SimilarityResult(BaseModel):
    similarity: Union[float, List[float]]
    text: Union[str, List[str]]

app = FastAPI(
    title="CLIP Image Service",
    description="基于CLIP模型的图片分析服务",
    version="1.0.0"
)

# 初始化模型
model = ClipModel()

def parse_text_input(text_input: str) -> Union[str, List[str]]:
    """解析文本输入,支持多种格式"""
    try:
        # 尝试解析为JSON
        data = json.loads(text_input)
        
        # 如果是字典,尝试获取text字段
        if isinstance(data, dict):
            return data.get("text", text_input)
            
        # 如果是列表或字��串,直接返回
        return data
    except json.JSONDecodeError:
        # 如果不是JSON,直接返回原始文本
        return text_input

@app.post("/predict", response_model=List[PredictionResult])
async def predict_tags(image: UploadFile = File(...)):
    """预测图片标签

    Args:
        image: 上传的图片文件

    Returns:
        List[PredictionResult]: 标签及其置信度列表
    """
    if not image.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="只支持图片文件")

    try:
        return await model.predict(image)
    except Exception as e:
        logger.error(f"预测失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/similarity", response_model=SimilarityResult)
async def compute_similarity(text: SimilarityRequest, image: UploadFile = File(...)):
    """计算图片与文本的相似度（原有API，保持兼容性）

    Args:
        text: 文本提示词或提示词列表
        image: 上传的图片文件

    Returns:
        SimilarityResult: 相似度分数
    """
    if not image.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="只支持图片文件")

    try:
        similarity = await model.compute_similarity(image, text.text)
        return SimilarityResult(
            similarity=similarity,
            text=text.text
        )
    except Exception as e:
        logger.error(f"相似度计算失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/similarity_flexible", response_model=SimilarityResult)
async def compute_similarity_flexible(
    image: UploadFile = File(...),
    text: str = Form(...),
):
    """计算图片与文本的相似度（新API，支持更灵活的输入格式）
    
    支持多种文本输入格式:
    1. 直接文本字符串
    2. JSON对象: {"text": "文本"}
    3. JSON数组: ["文本1", "文本2"]
    """
    if not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="只支持图片文件")

    try:
        # 解析文本输入
        parsed_text = parse_text_input(text)
        logger.info(f"解析后的文本: {parsed_text}")
        
        # 计算相似度
        similarity = await model.compute_similarity(image, parsed_text)
        
        return SimilarityResult(
            similarity=similarity,
            text=parsed_text
        )
    except Exception as e:
        logger.error(f"相似度计算失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "model": "clip-vit-large-patch14"} 