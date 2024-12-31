from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from transformers import Blip2Processor, Blip2ForConditionalGeneration
import torch
from PIL import Image
import io
import logging
from typing import List, Union
from pydantic import BaseModel
import os
from huggingface_hub import snapshot_download
import time
import requests
from pathlib import Path
import json

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 设置环境变量，使用多个国内镜像源
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HF_MIRROR'] = 'https://mirrors.tuna.tsinghua.edu.cn/hugging-face-models'
os.environ['TRANSFORMERS_CACHE'] = '/root/.cache/huggingface'
os.environ['HF_HOME'] = '/root/.cache/huggingface'
os.environ['HF_HUB_CACHE'] = '/root/.cache/huggingface/hub'
os.environ['HF_HUB_ENABLE_HF_TRANSFER'] = '1'
os.environ['HF_HUB_DOWNLOAD_TIMEOUT'] = '600'

# 定义响应模型
class ImageDescription(BaseModel):
    description: str

class VisualQA(BaseModel):
    question: str
    answer: str

app = FastAPI(
    title="BLIP-2 Image Service",
    description="基于BLIP-2模型的图片描述和视觉问答服务",
    version="1.0.0"
)

# 初始化模型
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
processor = None
model = None

def download_file(url, local_path):
    """下载单个文件"""
    response = requests.get(url, verify=False, stream=True)
    response.raise_for_status()
    
    local_path = Path(local_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(local_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

def download_model():
    """下载模型文件，支持断点续传"""
    model_name = "Salesforce/blip2-opt-2.7b"
    cache_dir = "/root/.cache/huggingface/models"
    base_path = Path(cache_dir) / model_name
    
    # 检查本地缓存是否存在模型文件
    model_files = [
        "config.json",
        "model.safetensors.index.json",
        "tokenizer_config.json",
        "vocab.json",
        "merges.txt",
        "model-00001-of-00002.safetensors",
        "model-00002-of-00002.safetensors"
    ]
    
    # 检查必要的模型文件是否都存在
    files_exist = all(
        (base_path / file).exists()
        for file in model_files
    )
    
    if files_exist:
        logger.info("模型文件已存在于本地缓存中，跳过下载")
        return
        
    logger.info(f"开始下载模型 {model_name}")
    
    # 设置环境变量，允许不安全的HTTPS请求
    os.environ['CURL_CA_BUNDLE'] = ''
    os.environ['REQUESTS_CA_BUNDLE'] = ''
    os.environ['SSL_CERT_FILE'] = ''
    os.environ['HF_HUB_DISABLE_SSL_VERIFICATION'] = '1'
    
    # 禁用SSL警告
    requests.packages.urllib3.disable_warnings()
    
    # 尝试不同的镜像源
    mirrors = [
        "https://hf-mirror.com",
        "https://mirrors.tuna.tsinghua.edu.cn/hugging-face-models",
        "https://huggingface.co"
    ]
    
    for mirror in mirrors:
        logger.info(f"尝试从镜像源下载: {mirror}")
        try:
            # 下载模型配置文件
            config_url = f"{mirror}/Salesforce/blip2-opt-2.7b/resolve/main/config.json"
            download_file(config_url, base_path / "config.json")
            
            # 下载分词器配置文件
            tokenizer_url = f"{mirror}/Salesforce/blip2-opt-2.7b/resolve/main/tokenizer_config.json"
            download_file(tokenizer_url, base_path / "tokenizer_config.json")
            
            # 下载词汇表
            vocab_url = f"{mirror}/Salesforce/blip2-opt-2.7b/resolve/main/vocab.json"
            download_file(vocab_url, base_path / "vocab.json")
            
            # 下载合并文件
            merges_url = f"{mirror}/Salesforce/blip2-opt-2.7b/resolve/main/merges.txt"
            download_file(merges_url, base_path / "merges.txt")
            
            # 下载模型文件
            model_url_1 = f"{mirror}/Salesforce/blip2-opt-2.7b/resolve/main/model-00001-of-00002.safetensors"
            download_file(model_url_1, base_path / "model-00001-of-00002.safetensors")
            
            model_url_2 = f"{mirror}/Salesforce/blip2-opt-2.7b/resolve/main/model-00002-of-00002.safetensors"
            download_file(model_url_2, base_path / "model-00002-of-00002.safetensors")
            
            # 下载模型索引文件
            model_index_url = f"{mirror}/Salesforce/blip2-opt-2.7b/resolve/main/model.safetensors.index.json"
            download_file(model_index_url, base_path / "model.safetensors.index.json")
            
            logger.info(f"从 {mirror} 成功下载模型")
            return
            
        except Exception as e:
            logger.error(f"从 {mirror} 下载失败: {str(e)}")
            continue
    
    raise Exception("所有镜像源都下载失败")

def load_model():
    global processor, model
    try:
        cache_dir = "/root/.cache/huggingface/models"
        model_name = "Salesforce/blip2-opt-2.7b"
        
        # 首先确保模型文件已下载
        download_model()
        
        # 加载模型
        logger.info("开始加载模型...")
        processor = Blip2Processor.from_pretrained(
            model_name,
            cache_dir=cache_dir,
            local_files_only=True  # 只使用本地文件
        )
        model = Blip2ForConditionalGeneration.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            cache_dir=cache_dir,
            device_map="auto",
            local_files_only=True  # 只使用本地文件
        )
        model.to(device)
        logger.info("BLIP-2模型加载成功")
    except Exception as e:
        logger.error(f"模型加载失败: {str(e)}")
        raise

@app.on_event("startup")
async def startup_event():
    """服务启动时加载模型"""
    load_model()

@app.post("/describe", response_model=ImageDescription)
async def describe_image(image: UploadFile = File(...)):
    """生成图片描述

    Args:
        image: 上传的图片文件

    Returns:
        ImageDescription: 生成的图片描述
    """
    logger.info(f"接收到图片上传请求: {image.filename}, content_type: {image.content_type}")
    
    if not image or not image.content_type:
        raise HTTPException(status_code=400, detail="未提供图片文件或content-type")
        
    if not image.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="只支持图片文件")

    try:
        # 读取图片
        image_data = await image.read()
        logger.info(f"成功读取图片数据，大小: {len(image_data)} bytes")
        
        # 转换为PIL图片
        try:
            pil_image = Image.open(io.BytesIO(image_data)).convert('RGB')
            logger.info(f"成功转换为PIL图片，尺寸: {pil_image.size}")
        except Exception as e:
            logger.error(f"图片转换失败: {str(e)}")
            raise HTTPException(status_code=400, detail=f"图片格式错误: {str(e)}")
        
        # 处理图片
        try:
            inputs = processor(
                images=pil_image,
                return_tensors="pt"
            ).to(device)
            logger.info("成功处理图片输入")
        except Exception as e:
            logger.error(f"图片处理失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"图片处理失败: {str(e)}")
        
        # 生成描述
        try:
            generation_config = {
                "max_new_tokens": 50,     # 适中的生成长度
                "min_length": 10,         # 确保描述有一定长度
                "num_beams": 3,           # 使用beam search
                "temperature": 0.6,       # 降低随机性，提高准确性
                "top_p": 0.85,           # 适当的nucleus sampling
                "repetition_penalty": 1.2, # 避免重复
                "length_penalty": 1.0     # 平衡长度
            }
            
            generated_ids = model.generate(**inputs, **generation_config)
            generated_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()
            
            logger.info(f"成功生成描述: {generated_text}")
            return ImageDescription(description=generated_text)
        except Exception as e:
            logger.error(f"描述生成失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"描述生成失败: {str(e)}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理过程中发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/qa", response_model=VisualQA)
async def visual_qa(
    image: UploadFile = File(...),
    question: str = Form(...)
):
    """视觉问答

    Args:
        image: 上传的图片文件
        question: 关于图片的问题

    Returns:
        VisualQA: 问题和回答
    """
    logger.info(f"接收到视觉问答请求: {image.filename}, 问题: {question}")
    
    if not image.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="只支持图片文件")

    try:
        # 读取图片
        image_data = await image.read()
        pil_image = Image.open(io.BytesIO(image_data)).convert('RGB')
        logger.info(f"成功转换为PIL图片，尺寸: {pil_image.size}")
        
        # 构建提示词
        examples = """
        Q: What brand is this car?
        A: This is a Toyota car.
        
        Q: What color is this car?
        A: The car appears to be silver/metallic in color.
        
        Q: What type of car is this?
        A: This is an electric vehicle (EV).
        """
        
        prompt = f"{examples}\n\nQ: {question}\nA:"
        
        # 处理图片和问题
        inputs = processor(
            images=pil_image,
            text=prompt,
            return_tensors="pt"
        ).to(device)
        
        # 设置生成参数
        generation_config = {
            "max_new_tokens": 50,
            "min_length": 5,
            "num_beams": 3,
            "temperature": 0.8,
            "top_p": 0.95,
            "repetition_penalty": 1.2,
            "length_penalty": 1.0,
            "do_sample": True,
            "early_stopping": True
        }
        
        # 生成答案
        generated_ids = model.generate(**inputs, **generation_config)
        generated_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()
        
        # 提取实际答案
        try:
            answer = generated_text.split("\nA:")[-1].strip()
            if not answer:
                answer = generated_text
        except:
            answer = generated_text
            
        # 检查答案质量
        if not answer or answer == question or "?" in answer or answer.startswith("Q:"):
            # 如果答案无效，使用更简单的提示词重试
            prompt = f"Answer this question about the image: {question}\nAnswer:"
            
            inputs = processor(
                images=pil_image,
                text=prompt,
                return_tensors="pt"
            ).to(device)
            
            generated_ids = model.generate(**inputs, **generation_config)
            generated_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()
            
            try:
                answer = generated_text.split("Answer:")[-1].strip()
                if not answer:
                    answer = generated_text
            except:
                answer = generated_text
            
            if not answer or answer == question or "?" in answer:
                answer = "抱歉，我无法准确回答这个问题。请尝试用不同的方式提问。"
        
        logger.info(f"生成的答案: {answer}")
        
        return VisualQA(
            question=question,
            answer=answer
        )
        
    except Exception as e:
        logger.error(f"视觉问答失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "model": "blip2-opt-2.7b",
        "model_loaded": processor is not None and model is not None
    } 