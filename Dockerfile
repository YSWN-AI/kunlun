# 昆仑创作引擎 — Dockerfile (多阶段构建)
# 基于 python:3.11-slim，安装依赖后通过 uvicorn 启动 FastAPI
# 国内用户：使用 docker.m.daocloud.io 镜像站加速

# ==================== 构建阶段 ====================
FROM docker.m.daocloud.io/library/python:3.11-slim AS builder

# 仅安装编译所需工具（torch/sentence-transformers 编译加速）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt .
# 预编译依赖到 wheels（使用清华镜像源加速）
RUN pip install --no-cache-dir --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# ==================== 运行阶段 ====================
FROM docker.m.daocloud.io/library/python:3.11-slim

LABEL org.opencontainers.image.title="kunlun-creation-engine"
LABEL org.opencontainers.image.description="昆仑创作引擎 - AI 驱动的小说创作系统"
LABEL org.opencontainers.image.version="v0.2.0"

# 仅安装运行时系统依赖（无需 build-essential）
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户
RUN groupadd -r kunlun && useradd -r -g kunlun -d /app -m kunlun

WORKDIR /app

# 复制预编译的 wheels 并安装（使用清华镜像源加速）
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl -i https://pypi.tuna.tsinghua.edu.cn/simple && rm -rf /wheels

# 复制应用代码
COPY . .

# 创建数据目录并设置权限
RUN mkdir -p data/published data/learn data/snapshots data/logs data/export && \
    chown -R kunlun:kunlun /app

# 切换到非 root 用户
USER kunlun

# 暴露端口
EXPOSE 8000

# 健康检查（与 docker-compose 保持一致）
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["uvicorn", "kunlun.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
