#!/usr/bin/env bash
# NexusIQ sağlamlıq yoxlaması — backend, DB, frontend, watchdog.
set -uo pipefail

BACKEND_PORT="${BACKEND_PORT:-8001}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
LOG_DIR="$HOME/Library/Logs/nexusiq"
GREEN="\033[32m"; RED="\033[31m"; DIM="\033[2m"; NC="\033[0m"
ok()  { printf "${GREEN}● %s${NC}\n" "$1"; }
bad() { printf "${RED}● %s${NC}\n" "$1"; }

echo "── NexusIQ status ──"

health="$(curl -s -m5 "http://localhost:$BACKEND_PORT/api/v1/health" 2>/dev/null)"
case "$health" in
  *'"status":"ok"'*) ok "backend  :$BACKEND_PORT  $health" ;;
  *)                 bad "backend  :$BACKEND_PORT  (cavab yox)" ;;
esac

db="$(curl -s -m5 "http://localhost:$BACKEND_PORT/api/v1/health/db" 2>/dev/null)"
case "$db" in
  *'"database":"connected"'*) ok "database (Postgres 5433)  $db" ;;
  *)                          bad "database  $db" ;;
esac

code="$(curl -s -m5 -o /dev/null -w '%{http_code}' "http://localhost:$FRONTEND_PORT" 2>/dev/null)"
[ "$code" = "200" ] && ok "frontend :$FRONTEND_PORT  ($code)" || bad "frontend :$FRONTEND_PORT  (HTTP $code)"

wd_pid="$(cat "$LOG_DIR/watchdog.pid" 2>/dev/null || true)"
if [ -n "${wd_pid:-}" ] && kill -0 "$wd_pid" 2>/dev/null; then
  ok "watchdog  aktiv (pid $wd_pid)"
else
  bad "watchdog  işləmir — scripts/dev.sh ilə başlat"
fi

printf "${DIM}Loglar: ~/Library/Logs/nexusiq/{backend,frontend,watchdog}.log${NC}\n"
