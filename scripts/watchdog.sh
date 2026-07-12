#!/usr/bin/env bash
# NexusIQ watchdog — hər 15 saniyədə backend (:8001) və frontend (:3000)
# sağlamlığını yoxlayır, cavab verməyəni yenidən başladır (30 iyun hadisəsi:
# backend səssiz öldü, 12 gün heç kim bilmədi — bir də olmasın).
# dev.sh tərəfindən başladılır; stop.sh ƏVVƏLCƏ bunu dayandırır.
set -uo pipefail   # DİQQƏT: -e YOX — keçici xəta döngəni öldürməməlidir

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$HOME/Library/Logs/nexusiq"; mkdir -p "$LOG_DIR"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
BACKEND_PORT="${BACKEND_PORT:-8001}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
PG_BIN="/opt/homebrew/opt/postgresql@14/bin"   # keg-only — tam yol lazımdır
INTERVAL=15        # yoxlama intervalı (san) — 30s daxilində dirilmə üçün
CONFIRM_DELAY=3    # keçici xətanı süzmək üçün təkrar yoxlama gecikməsi
BACKOFF_MAX=600    # restart-fırtınasına qarşı maksimum gözləmə (san)

log() { printf '%s %s\n' "$(date '+%F %T')" "$*" >> "$LOG_DIR/watchdog.log"; }

# ---- Tək nüsxə kilidi (dev.sh iki dəfə işləsə də dublikat olmasın) ----
PIDFILE="$LOG_DIR/watchdog.pid"
old="$(cat "$PIDFILE" 2>/dev/null || true)"
if [ -n "$old" ] && kill -0 "$old" 2>/dev/null \
   && ps -p "$old" -o command= | grep -q watchdog.sh; then
  exit 0   # artıq işləyir (PID təkrar istifadəsinə qarşı ps yoxlaması)
fi
echo $$ > "$PIDFILE"
# Yalnız ÖZ pidfile-ımızı sil — gec ölən köhnə nüsxə yenisininkini silməsin
cleanup() { [ "$(cat "$PIDFILE" 2>/dev/null)" = "$$" ] && rm -f "$PIDFILE"; }
trap 'cleanup; exit 0' TERM INT
trap 'cleanup' EXIT

backend_up()  { curl -fsS -m5 "http://localhost:$BACKEND_PORT/api/v1/health" >/dev/null 2>&1; }
frontend_up() { [ "$(curl -s -m5 -o /dev/null -w '%{http_code}' "http://localhost:$FRONTEND_PORT" 2>/dev/null)" = "200" ]; }

# QEYD: start əmrləri dev.sh ilə SİNXRON saxlanmalıdır (eyni bayraqlar, eyni log).
# exec vacibdir: pidfile-a bash wrapper deyil, servisin ÖZ PID-i düşsün —
# yoxsa stop/kill wrapper-i vurur, real proses yetim qalıb portu saxlayır.
# Frontend npm-siz (.bin/next) — npm ara-proses olub eyni yetim problemini yaradır.
start_backend() {
  ( cd "$ROOT/backend" && export BACKEND_PORT && exec nohup .venv/bin/python -m uvicorn \
      app.main:app --host 127.0.0.1 --port "$BACKEND_PORT" --log-level warning \
      >> "$LOG_DIR/backend.log" 2>&1 ) &
  echo $! > "$LOG_DIR/backend.pid"
}
start_frontend() {
  ( cd "$ROOT/frontend" && exec nohup ./node_modules/.bin/next start \
      --port "$FRONTEND_PORT" >> "$LOG_DIR/frontend.log" 2>&1 ) &
  echo $! > "$LOG_DIR/frontend.pid"
}

kill_service() {  # $1=ad $2=port — pidfile prosesini nəzakətlə, sonra zorla dayandır
  local pid opid
  pid="$(cat "$LOG_DIR/$1.pid" 2>/dev/null || true)"
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null
    for _ in 1 2 3 4 5; do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
    kill -0 "$pid" 2>/dev/null && { pkill -9 -P "$pid" 2>/dev/null; kill -9 "$pid" 2>/dev/null; }
  fi
  # Port hələ məşğuldursa və sahibi bizim stack-dəndirsə (uvicorn/next/node) — təmizlə
  for opid in $(lsof -ti tcp:"$2" 2>/dev/null || true); do
    if ps -p "$opid" -o command= | grep -Eq 'uvicorn|next|node'; then
      kill -9 "$opid" 2>/dev/null
      log "$1: portda qalan yetim proses öldürüldü (pid $opid)"
    fi
  done
  rm -f "$LOG_DIR/$1.pid"
}

# Hər servis üçün vəziyyət (bash 3.2 — assosiativ massiv yoxdur):
BACKEND_STREAK=0; BACKEND_LAST=0
FRONTEND_STREAK=0; FRONTEND_LAST=0

check() {  # $1=ad $2=up_fn $3=start_fn $4=port $5=STREAK_var $6=LAST_var
  local now streak last backoff exp
  now="$(date +%s)"; streak="${!5}"; last="${!6}"
  if "$2"; then
    # 5 dəq sağlam qalıbsa backoff yaddaşı sıfırlanır
    [ "$streak" -gt 0 ] && [ $((now - last)) -gt 300 ] && printf -v "$5" 0
    return 0
  fi
  sleep "$CONFIRM_DELAY"
  "$2" && return 0                         # keçici xəta idi — heç nə etmə
  if [ "$streak" -gt 0 ]; then             # restart-fırtınasına qarşı backoff
    exp="$streak"; [ "$exp" -gt 4 ] && exp=4   # 60→120→240→480→600 (daşma olmasın)
    backoff=$(( 60 * (2 ** (exp - 1)) ))
    [ "$backoff" -gt "$BACKOFF_MAX" ] && backoff="$BACKOFF_MAX"
    [ $((now - last)) -lt "$backoff" ] && return 0   # backoff bitməyib — gözlə
  fi
  log "$1 cavab vermir — restart edilir (streak=$((streak + 1)))"
  kill_service "$1" "$4"
  "$3"
  printf -v "$5" '%s' $((streak + 1))
  printf -v "$6" '%s' "$now"
}

log "watchdog başladı (pid $$, interval ${INTERVAL}s)"
while true; do
  check backend  backend_up  start_backend  "$BACKEND_PORT"  BACKEND_STREAK  BACKEND_LAST
  check frontend frontend_up start_frontend "$FRONTEND_PORT" FRONTEND_STREAK FRONTEND_LAST
  # Postgres: brew/launchd idarə edir — yalnız idempotent start cəhdi + log
  "$PG_BIN/pg_isready" -q -h localhost -p 5433 2>/dev/null || \
    { log "Postgres (5433) cavab vermir — brew services start cəhdi"; \
      brew services start postgresql@14 >/dev/null 2>&1; }
  # sleep arxa fonda + wait — TERM trap-ı sleep bitməsini gözləmədən dərhal işləsin
  sleep "$INTERVAL" & wait $! || true
done
