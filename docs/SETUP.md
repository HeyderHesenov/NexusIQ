# Quraşdırma — Lokal

> Bu fayl NexusIQ-u lokal maşında işə salmaq üçün mühit addımlarını göstərir.
> Töhfə qaydaları üçün bax [CONTRIBUTING.md](../CONTRIBUTING.md).

## 0. Tələblər
- Python 3.13+ (backend `argon2-cffi` işlədir; 3.13-də silinən stdlib-ə arxalanmır)
- Node.js 20+
- PostgreSQL (port 5433 — bax aşağıdakı `pg_ensure.sh` qeydi)

## 1. Verilənlər bazasını yarat
Terminalda işlət:
```bash
# Postgres işləyirmi yoxla (bu maşında port 5433-dədir)
brew services start postgresql@14

# Baza yarat
createdb -p 5433 nexusiq
```
> Əgər `createdb` istifadəçi xətası verərsə, `.env`-dəki
> `DATABASE_URL` istifadəçi/parol/portunu öz Postgres-inə uyğunlaşdır
> (cari konfiqurasiya: `localhost:5433/nexusiq`).

## 2. Backend qur
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # LLM açarları AI funksiyaları üçün lazımdır (opsional)
```

İşə sal:
```bash
uvicorn app.main:app --reload --port 8001
```
Yoxla: http://localhost:8001/docs  və  http://localhost:8001/api/v1/health

## 3. Frontend qur
```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```
Yoxla: http://localhost:3000

## Tək əmrlə işə salma (tövsiyə olunur)
Backend və frontend-i ayrıca başlatmaq əvəzinə bir əmr:
```bash
./scripts/dev.sh      # Postgres + backend (8001) + frontend (3000) — sağlamlığı gözləyir
./scripts/status.sh   # backend/db/frontend sağlamlığı
./scripts/stop.sh     # dayandırmaq üçün
```
`dev.sh` artıq işləyəni təkrar başlatmır və xəbərlər hazır olana qədər gözləyir.
Loglar: `~/Library/Logs/nexusiq/{backend,frontend}.log`.

> Qeyd: reboot-dan sonra `./scripts/dev.sh` yenidən işlət. (Avtomatik auto-start
> macOS-da layihə `~/Desktop`-da olduğu üçün Full Disk Access tələb edərdi — bu isə
> təhlükəsizlik güzəşti olduğundan seçilmədi.) Frontend backend qısa kəsiləndə özü
> sağalır (timeout + avtomatik retry).

## Yardımçı skriptlər (`scripts/`)
`dev.sh`/`status.sh`/`stop.sh`-dan başqa iki skript var — nə etdiklərini bilmək vacibdir,
çünki hər ikisi görünməz təsir edir:

- **`watchdog.sh`** — **`dev.sh` bunu avtomatik başladır**. Fon prosesi kimi hər ~2
  dəqiqədən bir backend/frontend sağlamlığını yoxlayır və düşəni **yenidən dirildir**.
  Nəticə: `stop.sh` işlətmədən prosesi öldürsən, watchdog onu geri qaytaracaq (bilməyən
  üçün sürpriz). Tam dayandırmaq üçün `./scripts/stop.sh` işlət (watchdog-u da dayandırır).

- **`pg_ensure.sh`** — Postgres-in `:5433`-də qalxdığına zəmanət verən öz-özünü sağaldan
  start. **Diqqət: sistem `postgresql.conf`-unu `sed -i` ilə dəyişdirə bilər** (portu 5433-ə
  sabitləmək üçün) və xidməti restart edir. `:5432`-də yad PostgreSQL versiyası varsa
  toqquşmanın qarşısını alır. Yalnız loopback-a bağlanır.

## Qeyd
- LLM açarları (provayder-agnostik) yalnız AI funksiyaları (chat, brif, xülasə, embedding)
  üçün lazımdır — boş buraxılsa həmin funksiyalar zərif söndürülür, qalan sayt işləyir.
- Reboot-dan sonra `./scripts/dev.sh` yenidən işlət. Avtomatik auto-start (launchd)
  macOS-da layihə `~/Desktop`-da olduğu üçün Full Disk Access tələb edərdi — təhlükəsizlik
  güzəşti olduğundan seçilməyib.
