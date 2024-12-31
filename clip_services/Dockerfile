FROM nvidia/cuda:12.1.0-base-ubuntu22.04

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 使用阿里云Ubuntu镜像源
RUN sed -i 's/archive.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list \
    && sed -i 's/security.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list

# 安装Python和依赖
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# 创建工作目录和缓存目录
WORKDIR /app
RUN mkdir -p /root/.cache/huggingface

# 首先复制并安装依赖，这样源代码改变时不会重新安装依赖
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip install --no-cache-dir -r requirements.txt

# 最后才复制应用代码，这样修改代码不会影响前面的缓存层
COPY . .

# 暴露端口
EXPOSE 5000

# 启动服务
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "5000"] 