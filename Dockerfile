# 第一阶段：构建环境
FROM python:3.10-slim as builder

WORKDIR /app
COPY requirements.txt .

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev && \
    pip install --user -r requirements.txt

# 第二阶段：运行环境
FROM python:3.10-slim

WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .

# 确保脚本可执行
RUN chmod +x web_ui/app.py

# 设置环境变量
ENV PATH=/root/.local/bin:$PATH
ENV FLASK_APP=web_ui/app.py
ENV FLASK_ENV=production

# 安装Playwright浏览器
RUN apt-get update && \
    apt-get install -y --no-install-recommends wget && \
    python -m playwright install && \
    python -m playwright install-deps && \
    apt-get remove -y wget && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8866/ || exit 1

EXPOSE 8866
CMD ["gunicorn", "--bind", "0.0.0.0:8866", "--workers", "4", "web_ui.app:app"]
