#!/usr/bin/env bash
# run.sh — atalhos do compose guarda-chuva (gateway + 3 APIs).
#
# Uso:
#   ./run.sh up        # sobe os 4 serviços
#   ./run.sh down      # derruba
#   ./run.sh logs      # tail dos logs (gateway + APIs)
#   ./run.sh ps        # status
#   ./run.sh rebuild   # rebuild --no-cache
#   ./run.sh test      # curl /avu/rest/health + /docs de cada API interna
#
# Requer que ../bff-bb, ../api-auth e ../api-auth-ldap estejam no filesystem
# (o compose faz build referenciando essas pastas).

set -euo pipefail
cd "$(dirname "$0")"

# Detecta docker compose v2 ou docker-compose v1.
if docker compose version >/dev/null 2>&1; then
  COMPOSE="docker compose"
else
  COMPOSE="docker-compose"
fi

PORT="${GATEWAY_PORT:-8080}"

case "${1:-help}" in
  up)
    # Confere que os irmãos existem.
    for sibling in ../bff-bb ../api-auth ../api-auth-ldap; do
      if [[ ! -d "$sibling" ]]; then
        echo "❌ pasta irmã ausente: $sibling"
        echo "   Este compose precisa dos 3 repos clonados lado a lado."
        exit 1
      fi
      if [[ ! -f "$sibling/.env" ]]; then
        echo "⚠️  $sibling/.env não existe — provavelmente vai subir com defaults."
      fi
    done
    $COMPOSE up -d --build
    echo "✅ gateway em http://localhost:$PORT"
    echo "   health: curl http://localhost:$PORT/avu/rest/health"
    ;;

  down)
    $COMPOSE down
    ;;

  logs)
    $COMPOSE logs -f "${@:2}"
    ;;

  ps)
    $COMPOSE ps
    ;;

  rebuild)
    $COMPOSE down
    $COMPOSE build --no-cache
    $COMPOSE up -d
    $COMPOSE logs -f
    ;;

  test)
    echo "=== gateway health ==="
    curl -fsS "http://localhost:$PORT/avu/rest/health" && echo
    echo
    echo "=== rota inexistente (esperado 404) ==="
    curl -sS -o /dev/null -w "HTTP=%{http_code}\n" "http://localhost:$PORT/avu/rest/rota_inexistente"
    ;;

  help|*)
    sed -n '2,17p' "$0"
    ;;
esac
