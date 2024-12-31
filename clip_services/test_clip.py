import requests
import json
import sys
import traceback
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_clip_service():
    try:
        # 健康检查
        logger.info("开始健康检查...")
        health_response = requests.get('http://localhost:5000/health')
        logger.info(f"健康检查响应: {health_response.json()}")
        
        # 准备测试图片
        image_path = 'test.png'
        logger.info(f"使用测试图片: {image_path}")
        
        # 发送预测请求
        try:
            with open(image_path, 'rb') as f:
                logger.info("正在发送预测请求...")
                files = {'image': ('test.png', f, 'image/png')}
                response = requests.post('http://localhost:5000/predict', files=files)
        except FileNotFoundError:
            logger.error(f"找不到测试图片: {image_path}")
            return
        except Exception as e:
            logger.error(f"读取图片时出错: {str(e)}")
            return
        
        # 打印结果
        if response.status_code == 200:
            results = response.json()
            logger.info("\n预测结果:")
            for result in results:
                logger.info(f"类别: {result['category']}, 标签: {result['tag']}, 置信度: {result['confidence']:.2f}")
        else:
            logger.error(f"请求失败: {response.status_code} - {response.text}")
            
    except requests.exceptions.ConnectionError:
        logger.error("无法连接到服务器，请确保服务正在运行")
    except Exception as e:
        logger.error(f"测试过程中出现错误: {str(e)}")
        logger.error(traceback.format_exc())

if __name__ == '__main__':
    test_clip_service() 