#!/bin/bash
set -e

REPO_DIR=$(pwd)

echo "🐾 Shelter System Production Install"

apt update -y
apt install -y ca-certificates curl gnupg lsb-release git

if ! command -v docker >/dev/null 2>&1; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg

  echo    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg]    https://download.docker.com/linux/ubuntu    $(. /etc/os-release && echo "$VERSION_CODENAME") stable"    | tee /etc/apt/sources.list.d/docker.list > /dev/null

  apt update -y
  apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable docker
  systemctl start docker
fi

docker compose up -d --build
sleep 10
docker compose exec backend python init_data.py || true

IP=$(hostname -I | awk '{print $1}')
echo "✅ READY: http://$IP"
echo "admin/admin123"
