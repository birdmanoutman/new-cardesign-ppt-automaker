import requests
import json
import mimetypes
import os

def test_describe():
    """测试图片描述功能"""
    url = 'http://localhost:5001/describe'
    image_path = os.path.abspath('test.png')
    
    if not os.path.exists(image_path):
        print(f"错误: 文件不存在: {image_path}")
        return
        
    file_size = os.path.getsize(image_path)
    print(f"文件大小: {file_size} bytes")
    
    content_type = mimetypes.guess_type(image_path)[0] or 'application/octet-stream'
    print(f"Content-Type: {content_type}")
    
    try:
        with open(image_path, 'rb') as f:
            files = {
                'image': (os.path.basename(image_path), f, content_type)
            }
            print(f"正在发送描述请求...")
            response = requests.post(url, files=files)
            
        print("状态码:", response.status_code)
        print("响应头:", response.headers)
        
        if response.status_code == 500:
            print("错误详情:", response.text)
        else:
            response.raise_for_status()
            result = response.json()
            print("\n生成的描述:")
            print("-" * 50)
            print(result['description'])
            print("-" * 50)
    except Exception as e:
        print("错误:", str(e))
        if hasattr(e, 'response'):
            print("响应内容:", e.response.text)

if __name__ == '__main__':
    print("=== 测试图片描述功能 ===")
    test_describe() 