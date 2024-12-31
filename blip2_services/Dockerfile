FROM nvidia/cuda:12.1.0-base-ubuntu22.04

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 使用阿里云Ubuntu镜像源
RUN sed -i 's/archive.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list \
    && sed -i 's/security.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list

# 设置工作目录
WORKDIR /app

# 安装基本依赖
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    git \
    && rm -rf /var/lib/apt/lists/*

# 创建缓存目录
RUN mkdir -p /root/.cache/huggingface

# 升级pip并安装依赖
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip install --no-cache-dir -r requirements.txt

# 复制服务代码
COPY . .

# 暴露端口
EXPOSE 5001

# 启动服务
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5001"] 