# 安装说明

## 系统要求
- Python 3.8+
- Windows 10 或更高版本
- 至少 1GB 可用存储空间

## 主程序安装

1. 创建并激活虚拟环境：
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

2. 安装主程序依赖：
```bash
pip install -r requirements.txt
```

3. （可选）安装开发依赖：
```bash
pip install -r dev-requirements.txt
```

## AI服务安装

### 方式一：使用 Docker（推荐）

1. 安装 Docker

2. 构建镜像：
```bash
cd src/ai_services/clip
docker build -t cardesign-clip .
```

3. 运行容器：
```bash
docker run -d -p 5000:5000 --name clip-service cardesign-clip
```

### 方式二：本地安装

1. 创建独立的虚拟环境：
```bash
python -m venv clip-venv
source clip-venv/bin/activate  # Linux/Mac
clip-venv\Scripts\activate     # Windows
```

2. 安装AI服务依赖：
```bash
cd src/ai_services/clip
pip install -r requirements.txt
```

3. 运行服务：
```bash
uvicorn api:app --host 0.0.0.0 --port 5000
```

## 验证安装

运行环境检查：
```bash
python -m utils.environment_check
```

## 常见问题

1. 如果安装 `pywin32` 失败，尝试：
```bash
pip install --only-binary :all: pywin32
```

2. 如果 AI 服务无法连接，检查：
- Docker 服务是否正在运行
- 端口 5000 是否被占用
- 防火墙设置 