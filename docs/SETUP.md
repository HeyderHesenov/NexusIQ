# Quraşdırma — Lokal

> Bu fayl SƏNİN əl ilə görəcəyin addımları göstərir.
> Kodun hamısını mən yazıram; aşağıdakılar mühit qurğusudur.

## 0. Tələblər (artıq sistemdə var ✓)
- Python 3.10 ✓
- Node.js 22 ✓
- PostgreSQL 14 (Homebrew) ✓

## 1. Verilənlər bazasını yarat
Terminalda işlət:
```bash
# Postgres işləyirmi yoxla
brew services start postgresql@14

# Baza yarat
createdb nexusfx
```
> Əgər `createdb` istifadəçi xətası verərsə, `.env`-dəki
> `DATABASE_URL` istifadəçi/parolunu öz Postgres istifadəçinə uyğunlaşdır.

## 2. Backend qur
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # sonra AI key-ləri Addım 4/7-də əlavə edəcəyik
```

İşə sal:
```bash
uvicorn app.main:app --reload --port 8000
```
Yoxla: http://localhost:8000/docs  və  http://localhost:8000/api/v1/health

## 3. Frontend qur
```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```
Yoxla: http://localhost:3000

## Qeyd
- AI açarları (OpenAI + Anthropic) yalnız Addım 4 və 7-də lazımdır.
- O addımlara çatanda səndən açarları istəyəcəm.
