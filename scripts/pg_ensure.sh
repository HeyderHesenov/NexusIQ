#!/usr/bin/env bash
# NexusIQ Postgres təminatı — pg@14-ün DAİM 5433-də qalxmasını qarantiləyir (idempotent).
# Səbəb: maşında EnterpriseDB PostgreSQL 18 5432-ni tutur. `brew upgrade postgresql@14`
# postgresql.conf-u yeniləyib port sətrini default (şərhli 5432)-yə qaytara bilir → pg@14
# 5432-yə bağlanmağa çalışıb toqquşur, qalxmır, backend 5433-də DB tapmır → xəbərlər itir.
# Bu helper hər start-da portu 5433-ə bərpa edir və DB qalxana qədər gözləyir.
# dev.sh (bloklayıcı start) və watchdog.sh (bərpa) tərəfindən `source` olunur.

PG_PREFIX="/opt/homebrew/opt/postgresql@14"   # keg-only — tam yol lazımdır
PG_BIN="$PG_PREFIX/bin"
PG_DATA="/opt/homebrew/var/postgresql@14"
PG_CONF="$PG_DATA/postgresql.conf"
PG_PORT="${PG_PORT:-5433}"

pg_ready() { "$PG_BIN/pg_isready" -q -h localhost -p "$PG_PORT" 2>/dev/null; }

# Konfiqdə aktiv "port = <PG_PORT>" yoxdursa qoy. PG_PORT_CHANGED=1 → restart lazımdır.
pg_enforce_port() {
  PG_PORT_CHANGED=0
  [ -f "$PG_CONF" ] || return 0
  grep -qE "^[[:space:]]*port[[:space:]]*=[[:space:]]*${PG_PORT}([[:space:]]|#|$)" "$PG_CONF" && return 0
  # köhnə/şərhli rəqəmli port sətirlərini sil (yalnız "port = <rəqəm>"), düzgününü əlavə et
  sed -i '' -E "/^[[:space:]]*#?[[:space:]]*port[[:space:]]*=[[:space:]]*[0-9]/d" "$PG_CONF"
  printf 'port = %s\t\t\t\t# NexusIQ: pg@14 %s-də (PG18 5432-ni tutur) — pg_ensure.sh\n' \
    "$PG_PORT" "$PG_PORT" >> "$PG_CONF"
  PG_PORT_CHANGED=1
}

# pg@14-ü 5433-də qaldır və hazır olana qədər gözlə. 0 = hazır, 1 = uğursuz.
ensure_pg() {
  pg_enforce_port
  if pg_ready && [ "${PG_PORT_CHANGED:-0}" = 0 ]; then
    return 0   # onsuz da düzgün portda işləyir
  fi
  # dəyişiklik olub və ya işləmir → restart (dayanmış/işləyən — hər ikisini tutur)
  brew services restart postgresql@14 >/dev/null 2>&1 || true
  for _ in $(seq 1 15); do pg_ready && return 0; sleep 1; done
  # fallback: brew services məhdud kontekstdə öldürülə bilir — birbaşa pg_ctl ilə qaldır
  "$PG_BIN/pg_ctl" -D "$PG_DATA" -o "-p $PG_PORT" -l "$PG_DATA/server.log" start >/dev/null 2>&1 || true
  for _ in $(seq 1 10); do pg_ready && return 0; sleep 1; done
  return 1
}
