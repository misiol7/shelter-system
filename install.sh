#!/bin/bash
set -e
APP_DIR=/opt/shelter-system
REPO_URL=https://github.com/misiol7/shelter-system.git

apt update -y
apt install -y curl git ca-certificates gnupg lsb-release

if ! command -v docker >/dev/null 2>&1; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list
  apt update -y
  apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

rm -rf $APP_DIR
git clone $REPO_URL $APP_DIR
cd $APP_DIR
docker compose up -d --build
echo "Done."
