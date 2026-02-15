#!/bin/bash
set -e

APP_DIR="/opt/shelter-system"
REPO_URL="https://github.com/TWOJ_LOGIN/shelter-system.git"

echo "======================================"
echo " SCHRONISKO AUTO-FIX PRO INSTALLER"
echo "======================================"

# ===== SYSTEM =====
apt update -y
apt upgrade -y
apt install -y curl git ca-certificates gnupg lsb-release

# ===== DOCKER =====
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
  apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

systemctl enable docker
systemctl start docker

# ===== CLEAN OLD =====
rm -rf "$APP_DIR"

# ===== CLONE =====
git clone "$REPO_URL" "$APP_DIR"
cd "$APP_DIR"

# ===== AUTO-FIX DOCKERFILE =====
echo "Checking backend Dockerfile..."

cat > backend/Dockerfile <<'EOF'
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn","main:app","--host","0.0.0.0","--port","8000"]
EOF

# ===== BUILD (RETRY) =====
echo "Building containers..."
if ! docker compose build --no-cache; then
    echo "First build failed -> retry..."
    sleep 5
    docker compose build --no-cache
fi

# ===== START =====
docker compose up -d

# ===== WAIT HEALTH =====
echo "Waiting backend..."
sleep 10

if docker compose ps | grep backend | grep -q "Up"; then
    echo "Backend OK"
else
    echo "Backend failed -> showing logs"
    docker compose logs backend --tail=50
fi

# ===== AUTOSTART SERVICE =====
cat <<EOF >/etc/systemd/system/shelter.service
[Unit]
Description=Schronisko PRO
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable shelter.service

IP=$(hostname -I | awk '{print $1}')

echo ""
echo "======================================"
echo " INSTALL COMPLETE (AUTO-FIX PRO)"
echo "======================================"
echo "Open:"
echo "http://$IP"
echo ""
