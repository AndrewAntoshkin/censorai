# План масштабирования фреймчек

Поэтапная дорожная карта. Каждый этап должен оставлять продукт рабочим.

## Этап 1 — База, профили, организации ✅

- **Postgres** как основная БД (`docker compose up -d postgres`)
- **Пользователи**: регистрация с **кодом организации**, вход, cookie-сессия, профиль
- **Организации**: каждый пользователь в одной org; проекты внутри org; демо привязано к «Фреймчек»
- **Супер-админ** (`SUPER_ADMIN_EMAIL`): роль `super_admin`, домашняя org — Фреймчек, переключатель org в сайдбаре
- **Коды**: дефолт `FRAMECHECK2026` в `.env`; новые org — `python scripts/create_org_code.py`
- **Обратная совместимость**: при `AUTH_REQUIRED=false` — без логина как раньше

## Этап 2 — Фоновая оркестрация анализа ✅

- arq + Redis: воркер опрашивает все `analyzing`, без piggyback на GET
- `./scripts/run_worker.sh` или `docker compose up worker`
- Dev: `GET /api/worker/poll-once?secret=...` (см. `WORKER_DEV_POLL_SECRET`; на Vercel отключён)
- Таблица `analysis_jobs`: `queued` → `processing` → `completed` / `failed`
- Retry: stale recovery, cap `ANALYSIS_JOB_MAX_ATTEMPTS`
- Kickoff/poll с `FOR UPDATE SKIP LOCKED` — безопасно для нескольких воркеров

```bash
docker compose up -d redis
./scripts/run_worker.sh
```

## Этап 3 — Хранилище и Replicate ✅

- **Продакшен-анализ только через Replicate** (`REPLICATE_API_TOKEN`, `VIDEO_PROVIDER` игнорируется если не `replicate`)
- **S3/MinIO/R2**: загрузки в бакет, presigned URL для модели и `/replicate-media`
- Подпись media URL: `AUTH_SECRET` (fallback: `REPLICATE_API_TOKEN`)

## Этап 4 — Cascade pre-pass (пилот) ✅

- `ANALYSIS_CASCADE_ENABLED=true` — ffmpeg по локальному файлу или temp-скачивание с S3
- Подсказки по таймкодам в промпт Replicate (экономия 5–10× — отдельный эпик, сегментный проход)

## Этап 5 — Наблюдаемость ✅

- `GET /api/ops/metrics` (супер-админ), страница `/ops`

---

### Локальный запуск

```bash
docker compose up -d postgres redis
cd backend && cp .env.example .env
# REPLICATE_API_TOKEN, REDIS_URL, опционально S3_*, WORKER_DEV_POLL_SECRET
uvicorn main:app --reload --port 8000
./scripts/run_worker.sh
```

Регистрация: `/register`, код `FRAMECHECK2026`.
