# 第一阶段：构建环境
FROM python:3.10-slim as builder

WORKDIR /app
COPY requirements.txt .

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc python3-dev wget curl && \
    pip install --user --no-cache-dir -r requirements.txt

# 第二阶段：运行环境
FROM python:3.10-slim

WORKDIR /app

# 复制 Python 依赖
COPY --from=builder /root/.local /root/.local

# 复制源码
COPY . .

# 环境变量
ENV PATH=/root/.local/bin:$PATH
ENV FLASK_ENV=production
ENV FLASK_DEBUG=false

# 安装 Playwright 浏览器（无头 Chromium）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        wget gnupg ca-certificates && \
    python -m playwright install chromium && \
    python -m playwright install-deps chromium && \
    apt-get remove -y wget gnupg && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8866/ || exit 1

EXPOSE 8866

# 使用 gunicorn 启动（注意：entrypoint 是 create_app 函数）
CMD ["gunicorn", "--bind", "0.0.0.0:8866", "--workers", "4", "--threads", "2", "apps.app_factory:create_app"]
