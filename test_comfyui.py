import requests
import json

def test_object_info():
    """测试获取节点信息"""
    print("\n=== 测试获取节点信息 ===")
    try:
        response = requests.get('http://127.0.0.1:8188/object_info')
        if response.status_code == 200:
            print("成功获取节点信息!")
            # 只打印部分关键信息避免输出过多
            data = response.json()
            print(f"可用节点数量: {len(data)}")
            print("\n部分节点类型:")
            count = 0
            for node_type in data.keys():
                print(f"- {node_type}")
                count += 1
                if count >= 5:  # 只显示前5个节点类型
                    break
        else:
            print(f"请求失败! 状态码: {response.status_code}")
    except Exception as e:
        print(f"错误: {str(e)}")

def test_queue():
    """测试获取队列信息"""
    print("\n=== 测试获取队列信息 ===")
    try:
        response = requests.get('http://127.0.0.1:8188/queue')
        if response.status_code == 200:
            print("成功获取队列信息!")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        else:
            print(f"请求失败! 状态码: {response.status_code}")
    except Exception as e:
        print(f"错误: {str(e)}")

def test_history():
    """测试获取历史记录"""
    print("\n=== 测试获取历史记录 ===")
    try:
        response = requests.get('http://127.0.0.1:8188/history')
        if response.status_code == 200:
            print("成功获取历史记录!")
            history = response.json()
            print(f"历史记录数量: {len(history)}")
            if history:
                print("\n最近的一条历史记录:")
                print(json.dumps(list(history.values())[0], indent=2, ensure_ascii=False))
        else:
            print(f"请求失败! 状态码: {response.status_code}")
    except Exception as e:
        print(f"错误: {str(e)}")

if __name__ == "__main__":
    print("开始测试 ComfyUI API...")
    test_object_info()
    test_queue()
    test_history()
    print("\n测试完成!") 