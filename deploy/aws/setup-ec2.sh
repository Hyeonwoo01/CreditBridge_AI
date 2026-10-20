#!/usr/bin/env bash
# EC2(Ubuntu 24.04) 처음 한 번: Docker 설치, 스왑 2GB(메모리 1GB인 t3.micro 보완), 저장소 받기.
#   실행: curl -fsSL https://raw.githubusercontent.com/Hyeonwoo01/CreditBridge_AI/main/deploy/aws/setup-ec2.sh | bash
# 끝나면 다시 로그인한 뒤(docker 그룹 적용) docs/deploy-aws.md 5단계부터 이어서 한다.
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/Hyeonwoo01/CreditBridge_AI.git}"
APP_DIR="${APP_DIR:-$HOME/CreditBridge_AI}"

# 1) Docker Engine + compose 플러그인 (Docker 공식 설치 스크립트)
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sudo sh
fi
sudo usermod -aG docker "$USER"
sudo systemctl enable --now docker

# 2) 스왑 2GB: 이미지 빌드와 AI 분석 중 메모리가 모자라 멈추지 않게 (EBS 용량 2GB 사용)
if ! sudo swapon --show | grep -q /swapfile; then
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

# 3) 저장소
if [ ! -d "$APP_DIR/.git" ]; then
  git clone "$REPO_URL" "$APP_DIR"
fi
if [ ! -f "$APP_DIR/.env" ]; then
  cp "$APP_DIR/deploy/aws/env.example" "$APP_DIR/.env"
  chmod 600 "$APP_DIR/.env"
fi

echo
echo "준비 완료. 로그아웃 후 다시 접속한 뒤:"
echo "  cd $APP_DIR && nano .env      # 값 채우기 (docs/deploy-aws.md 5단계)"
echo "  docker compose -f docker-compose.prod.yml up -d --build"
