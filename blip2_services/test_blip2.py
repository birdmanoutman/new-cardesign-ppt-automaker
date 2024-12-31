import requests
import os

def test_describe():
    """测试图片描述功能"""
    # 准备图片文件
    image_path = "../clip_services/test.png"
    if not os.path.exists(image_path):
        print(f"错误: 找不到测试图片 {image_path}")
        return
    
    # 发送请求
    with open(image_path, "rb") as f:
        files = {"image": ("test.png", f, "image/png")}
        response = requests.post("http://localhost:5001/describe", files=files)
    
    # 打印结果
    print("\n=== 图片描述测试 ===")
    if response.status_code == 200:
        print("成功!")
        print(f"描述: {response.json()['description']}")
    else:
        print(f"失败! 状态码: {response.status_code}")
        print(f"错误信息: {response.text}")

def test_qa():
    """测试视觉问答功能"""
    # 准备图片文件
    image_path = "../clip_services/test.png"
    if not os.path.exists(image_path):
        print(f"错误: 找不到测试图片 {image_path}")
        return
    
    # 测试问题
    question = "这张图片的主要颜色是什么？"
    
    # 发送请求
    with open(image_path, "rb") as f:
        files = {"image": ("test.png", f, "image/png")}
        data = {"question": question}
        response = requests.post("http://localhost:5001/qa", files=files, data=data)
    
    # 打印结果
    print("\n=== 视觉问答测试 ===")
    if response.status_code == 200:
        print("成功!")
        print(f"问题: {response.json()['question']}")
        print(f"回答: {response.json()['answer']}")
    else:
        print(f"失败! 状态码: {response.status_code}")
        print(f"错误信息: {response.text}")

def test_health():
    """测试健康检查接口"""
    response = requests.get("http://localhost:5001/health")
    
    print("\n=== 健康检查测试 ===")
    if response.status_code == 200:
        print("成功!")
        print(f"状态: {response.json()}")
    else:
        print(f"失败! 状态码: {response.status_code}")
        print(f"错误信息: {response.text}")

if __name__ == "__main__":
    print("开始测试BLIP2服务...")
    test_health()
    test_describe()
    test_qa()
    print("\n测试完成!") 