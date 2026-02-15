#!/bin/bash
set -e

APP_DIR="/opt/shelter-system"
REPO_URL="https://github.com/TWOJ_LOGIN/shelter-enterprise-final.git"

echo "=== SCHRONISKO ENTERPRISE INSTALLER ==="

# ---------------------------
# SYSTEM UPDATE
# ---------------------------
apt update -y
apt install -y curl git ca-certificates gnupg lsb-release

# ---------------------------
# DOCKER INSTALL
# ---------------------------
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."

    install -m 0755 -d /etc/apt/keyrings

    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
      | gpg --dearmor -o /etc/apt/keyrings/docker.gpg

    echo \
    "deb [arch=$(dpkg --print-architecture) \
    signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu \
    $(lsb_release -cs) stable" \
    > /etc/apt/sources.list.d/docker.list

    apt update -y

    apt install -y docker-ce docker-ce-cli containerd.io \
        docker-buildx-plugin docker-compose-plugin
fi

# ---------------------------
# INSTALL APP
# ---------------------------
rm -rf $APP_DIR

git clone $REPO_URL $APP_DIR

cd $APP_DIR

docker compose up -d --build

IP=$(hostname -I | awk '{print $1}')

echo ""
echo "======================================"
echo "✅ SCHRONISKO ENTERPRISE READY"
echo "🌐 OPEN: http://$IP"
echo "======================================"
