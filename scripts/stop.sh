#!/usr/bin/env bash
# dev.sh ilə başladılan NexusIQ proseslərini dayandırır (yalnız öz PID-lərimizi).
set -uo pipefail

LOG_DIR="$HOME/Library/Logs/nexusiq"
BACKEND_PORT="${BACKEND_PORT:-8001}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

stop_one() {
  local name="$1" pidfile="$LOG_DIR/$1.pid"
  if [ -f "$pidfile" ]; then
    local pid; pid="$(cat "$pidfile" 2>/dev/null || true)"
    if [ -n "${pid:-}" ] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null && echo "==> $name dayandırıldı (pid $pid)"
    else
      echo "==> $name işləmir"
    fi
    rm -f "$pidfile"
  else
    echo "==> $name üçün pid faylı yox (dev.sh ilə başlamayıb?)"
  fi
}

# Portda qalan yetimləri süpür (yalnız öz stack-imiz: uvicorn/next/node) —
# pidfile PID-i wrapper olubsa və ya servis əl ilə başladılıbsa.
sweep_port() {  # $1=ad $2=port
  local opid
  for opid in $(lsof -ti tcp:"$2" 2>/dev/null || true); do
    if ps -p "$opid" -o command= 2>/dev/null | grep -Eq 'uvicorn|next|node'; then
      kill "$opid" 2>/dev/null
      for _ in 1 2 3; do kill -0 "$opid" 2>/dev/null || break; sleep 1; done
      kill -0 "$opid" 2>/dev/null && kill -9 "$opid" 2>/dev/null
      echo "==> $1: portda qalan proses dayandırıldı (pid $opid)"
    fi
  done
}

stop_one watchdog   # ƏVVƏL watchdog — yoxsa dayandırdıqlarımızı dirildər
stop_one backend
stop_one frontend
sweep_port backend "$BACKEND_PORT"
sweep_port frontend "$FRONTEND_PORT"
echo "Bitdi. (Postgres toxunulmadı.)"
