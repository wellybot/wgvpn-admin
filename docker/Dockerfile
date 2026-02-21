FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    wireguard \
    wireguard-tools \
    python3 \
    python3-pip \
    python3-venv \
    nodejs \
    npm \
    curl \
    iproute2 \
    iputils-ping \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# 設定工作目錄
WORKDIR /app

# 複製專案
COPY . /app/

# 安裝 Python 依賴
RUN cd /app/backend && python3 -m venv venv && \
    ./venv/bin/pip install -r requirements.txt

# 初始化資料庫
RUN cd /app/backend && sqlite3 wgvpn.db < ../schema.sql

# 建立測試 WireGuard 設定
RUN mkdir -p /etc/wireguard && \
    wg genkey | tee /etc/wireguard/privatekey | wg pubkey > /etc/wireguard/publickey && \
    chmod 600 /etc/wireguard/privatekey

EXPOSE 8000 5173

CMD ["/bin/bash"]
