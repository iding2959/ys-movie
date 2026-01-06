# ============================================
# 构建阶段：安装依赖和编译
# ============================================
FROM python:3.11-slim AS builder

# 从官方 uv 镜像复制 uv 二进制文件
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 安装构建时依赖（编译工具）
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY pyproject.toml uv.lock ./

# 使用 uv 安装依赖到虚拟环境（使用缓存挂载加速构建）
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# ============================================
# 运行阶段：只包含运行时需要的文件
# ============================================
FROM python:3.11-slim AS runtime

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# 只安装运行时依赖（curl 用于健康检查）
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 从构建阶段复制虚拟环境（只复制必要的文件）
COPY --from=builder /app/.venv /app/.venv

# 复制项目文件
COPY . .

# 创建必要的目录
RUN mkdir -p uploads outputs workflows static

# 清理不必要的文件以减小镜像大小
RUN find /app -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true \
    && find /app -type f -name "*.pyc" -delete \
    && find /app -type f -name "*.pyo" -delete \
    && find /app/.venv -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true \
    && find /app/.venv -type f -name "*.pyc" -delete \
    && find /app/.venv -type f -name "*.pyo" -delete \
    && find /app/.venv -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true \
    && find /app/.venv -type d -name "test" -exec rm -rf {} + 2>/dev/null || true \
    && find /app/.venv -type d -name "docs" -exec rm -rf {} + 2>/dev/null || true \
    && find /app/.venv -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

# 暴露端口
EXPOSE 12321

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:12321/api/health || exit 1

# 启动命令（直接使用 Python，因为虚拟环境已在 PATH 中）
CMD ["python", "start.py", "--host", "0.0.0.0", "--port", "12321", "--no-reload"]

