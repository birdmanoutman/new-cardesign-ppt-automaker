from fastapi import FastAPI, File, UploadFile
from model import ClipModel
import logging
from typing import List, Dict

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="CLIP Image Tagging Service",
    description="基于CLIP模型的图片标签预测服务",
    version="1.0.0"
)

# 初始化模型
model = ClipModel()

@app.post("/predict", response_model=List[Dict[str, float]])
async def predict_tags(image: UploadFile = File(...)):
    """预测图片标签
    
    Args:
        image: 上传的图片文件
        
    Returns:
        List[Dict[str, float]]: 标签及其置信度列表
    """
    try:
        return await model.predict(image)
    except Exception as e:
        logger.error(f"预测失败: {str(e)}")
        raise

@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy"} 