#!/usr/bin/env bash
# scripts/deploy_vps.sh — deploy do gateway (avu-api) na VPS.
#
# Pré-requisito: os 7 irmãos ativos (bff-bb, bff-bb-fadec, api-vestibular-uem,
# api-auth-ldap, api-webhook-uem, api-webhook-fadec, api-id-uem) já estão em
# /home/glucca/ na VPS com seus próprios .env + secrets, deployados previamente
# pelos scripts de cada um.
# api-auth foi desativado em 2026-07 — não é mais checado nem parado aqui.
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

SIBLINGS=(bff-bb bff-bb-fadec api-vestibular-uem api-auth-ldap api-webhook-uem api-webhook-fadec api-id-uem api-fiscais-uem)

echo "→ verificando pastas irmãs na VPS"
for sibling in "${SIBLINGS[@]}"; do
  if ! ssh_run "test -d /home/glucca/$sibling"; then
    echo "❌ /home/glucca/$sibling ausente na VPS. Deploy cada projeto primeiro."
    exit 1
  fi
done

echo "→ derrubando containers antigos individuais (se estiverem rodando)"
# Cada projeto tinha seu próprio compose isolado. Como o gateway agora
# orquestra todos, precisamos parar as instâncias avulsas para evitar
# conflito de nomes e portas.
for sibling in "${SIBLINGS[@]}"; do
  ssh_run "cd /home/glucca/$sibling && docker compose down 2>/dev/null || true"
done

# api-auth desativado em 2026-07 — se ficou algum container/imagem antiga,
# derruba explicitamente (não é fatal se não existir).
ssh_run "docker ps -q -f name=api-auth | xargs -r docker rm -f 2>/dev/null || true"

echo "→ build + up do compose guarda-chuva"
ssh_run "cd $REMOTE_DIR && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build"

echo "→ status"
ssh_run "cd $REMOTE_DIR && docker compose ps"

echo
echo "✅ deploy concluído. Testes:"
echo "   ssh $HOST 'curl -fsS http://localhost:8081/avu/rest/health'"
echo "   ssh $HOST 'cd $REMOTE_DIR && docker compose logs -f gateway'"
