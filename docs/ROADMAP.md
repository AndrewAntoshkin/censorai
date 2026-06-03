# План масштабирования фреймчек

Поэтапная дорожная карта. Каждый этап должен оставлять продукт рабочим.

## Этап 1 — База, профили, организации ✅

- **Postgres** как основная БД (`docker compose up -d postgres`)
- **Пользователи**: регистрация с **кодом организации**, вход, cookie-сессия, профиль
- **Организации**: каждый пользователь в одной org; проекты внутри org; демо привязано к «Фреймчек»
- **Супер-админ** (`SUPER_ADMIN_EMAIL`): роль `super_admin`, домашняя org — Фреймчек, переключатель org в сайдбаре
- **Коды**: дефолт `FRAMECHECK2026` в `.env`; новые org — `python scripts/create_org_code.py`
- **Обратная совместимость**: при `AUTH_REQUIRED=false` — без логина как раньше

Локально с профилями:

```bash
docker compose up -d postgres
cd backend && cp .env.example .env   # AUTH_REQUIRED=true
uvicorn app.main:app --reload --port 8000
```

## Этап 2 — Фоновая оркестрация анализа 🚧 (в работе)

- ✅ arq + Redis: воркер опрашивает все `analyzing`, без piggyback на GET
- ✅ `./scripts/run_worker.sh` или `docker compose up worker`
- ✅ Dev: `GET /api/worker/poll-once` — ручной тик
- ⏳ Таблица `analysis_jobs`: `queued` → `processing` → `done` / `failed`
- ⏳ Retry / DLQ / visibility timeout

```bash
docker compose up -d redis
./scripts/run_worker.sh
```

## Этап 3 — Хранилище и провайдер

- Object storage (R2/S3) + signed URL вместо Vercel Blob для батча
- Vertex AI Gemini напрямую (geoblock, стоимость)

## Этап 4 — Двухпроходный анализ

- ASR + scene detection → мультимодалка только по флагам
- Пилот 10 эпизодов для $/час и качества

## Этап 5 — Наблюдаемость

- Throughput, ошибки, стоимость/час, прогресс батча
