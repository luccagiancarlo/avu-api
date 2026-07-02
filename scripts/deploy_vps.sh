#!/usr/bin/env bash
# scripts/deploy_vps.sh — deploy do gateway (avu-api) na VPS.
#
# Pré-requisito: os 3 irmãos (bff-bb, api-auth, api-auth-ldap) já estão
# em /home/glucca/ na VPS com seus próprios .env + secrets, deployados
# previamente pelos scripts de cada um.
#
# Uso:
#   ./scripts/deploy_vps.sh                # sync + build + up
#   ./scripts/deploy_vps.sh --restart-only # só restart (sem rsync)

set -euo pipefail

HOST="${HOST:-npd-avu}"
REMOTE_DIR="${REMOTE_DIR:-/home/glucca/avu-api}"
LOCAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

RESTART_ONLY=0
FIRST_TIME=0
for arg in "$@"; do
  case "$arg" in
    --restart-only) RESTART_ONLY=1 ;;
    --first-time)   FIRST_TIME=1 ;;
  esac
done

ssh_run() { ssh "$HOST" "$@"; }

echo "→ host: $HOST | remoto: $REMOTE_DIR"

if [[ "$RESTART_ONLY" -eq 1 ]]; then
  echo "→ restart-only: pulando rsync"
else
  echo "→ criando diretório remoto"
  ssh_run "mkdir -p $REMOTE_DIR"

  echo "→ rsync do código"
  rsync -avz --delete \
    --exclude='.git' \
    --exclude='.env' \
    --exclude='.DS_Store' \
    "$LOCAL_DIR/" "$HOST:$REMOTE_DIR/"

  if [[ "$FIRST_TIME" -eq 1 ]]; then
    if [[ -f "$LOCAL_DIR/.env" ]]; then
      echo "→ first-time: copiando .env"
      scp "$LOCAL_DIR/.env" "$HOST:$REMOTE_DIR/.env"
      ssh_run "chmod 600 $REMOTE_DIR/.env"
    fi
  fi
fi

echo "→ verificando pastas irmãs na VPS"
for sibling in bff-bb api-auth api-auth-ldap; do
  if ! ssh_run "test -d /home/glucca/$sibling"; then
    echo "❌ /home/glucca/$sibling ausente na VPS. Deploy cada projeto primeiro."
    exit 1
  fi
done

echo "→ derrubando containers antigos individuais (se estiverem rodando)"
# Cada projeto tinha seu próprio compose isolado. Como o gateway agora
# orquestra todos, precisamos parar as instâncias avulsas para evitar
# conflito de nomes e portas.
for sibling in bff-bb api-auth api-auth-ldap; do
  ssh_run "cd /home/glucca/$sibling && docker compose down 2>/dev/null || true"
done

echo "→ build + up do compose guarda-chuva"
ssh_run "cd $REMOTE_DIR && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build"

echo "→ status"
ssh_run "cd $REMOTE_DIR && docker compose ps"

echo
echo "✅ deploy concluído. Testes:"
echo "   ssh $HOST 'curl -fsS http://localhost:8081/avu/rest/health'"
echo "   ssh $HOST 'cd $REMOTE_DIR && docker compose logs -f gateway'"
