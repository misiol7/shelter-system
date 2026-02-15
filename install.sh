#!/bin/bash
set -e

echo "======================================"
echo "   SCHRONISKO PRO MAX INSTALLER"
echo "======================================"

APP_DIR="/opt/shelter-system"
REPO_URL="https://github.com/misiol7/shelter-system.git"

# ===== UPDATE SYSTEM =====
apt update -y
apt upgrade -y

# ===== TOOLS =====
apt install -y curl git ca-certificates gnupg lsb-release

# ===== INSTALL DOCKER =====
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

systemctl enable docker
systemctl start docker

# ===== CLEAN OLD INSTALL =====
if [ -d "$APP_DIR" ]; then
    echo "Removing old installation..."
    rm -rf "$APP_DIR"
fi

# ===== CLONE PROJECT =====
git clone "$REPO_URL" "$APP_DIR"
cd "$APP_DIR"

# ===== BUILD + RUN =====
docker compose down || true
docker compose up -d --build

# ===== AUTO START =====
cat <<EOF >/etc/systemd/system/shelter.service
[Unit]
Description=Schronisko PRO MAX
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
echo " INSTALACJA ZAKOŃCZONA"
echo "======================================"
echo "Otwórz:"
echo "http://$IP"
echo ""
