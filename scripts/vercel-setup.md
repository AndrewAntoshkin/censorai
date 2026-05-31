# Деплой на Vercel (Services)

## 1. Import

1. https://vercel.com/new → Import `AndrewAntoshkin/censorai`
2. **Root Directory:** оставьте **пустым** (корень репозитория, не `frontend`)
3. Framework Preset: **Services** (определится по `vercel.json`)

## 2. Storage (обязательно для прода)

### Postgres — P0

Без внешней БД SQLite лежит в `/tmp` **на каждом инстансе отдельно** → проекты и статусы анализа теряются.

1. Vercel Dashboard → **Storage** → **Postgres** (или подключите Neon)
2. Подключите store к проекту `censorai`
3. Vercel автоматически проставит `POSTGRES_URL` — backend подхватит его сам

Проверка после деплоя:

```bash
curl https://censorai.vercel.app/api/health
# {"status":"ok","database":"postgres","ephemeral_db":false}
```

Если `"database":"sqlite","ephemeral_db":true` — Postgres не подключён.

### Blob — для загрузки видео

1. Vercel Dashboard → **Storage** → **Blob**
2. Подключите к проекту → появится `BLOB_READ_WRITE_TOKEN`

На проде фронт грузит видео **напрямую в Blob** (`/upload/blob`), затем регистрирует URL через `/api/files/from-blob?auto_analyze=1`. Chunk-upload на Vercel больше не используется.

## 3. Переменные окружения

| Переменная | Значение |
|------------|----------|
| `REPLICATE_API_TOKEN` | токен с replicate.com |
| `REPLICATE_MODEL` | `google/gemini-3.5-flash` |
| `VIDEO_PROVIDER` | `replicate` |
| `POSTGRES_URL` | автоматически из Vercel Postgres |
| `BLOB_READ_WRITE_TOKEN` | автоматически из Vercel Blob |
| `PUBLIC_API_BASE_URL` | `https://censorai.vercel.app` (опционально, для signed URL >100 МБ) |

## 4. Deploy

После деплоя:
- UI: `https://censorai.vercel.app/`
- API: `https://censorai.vercel.app/api/health`

Фронт ходит на `/api/...` на том же домене — отдельный `NEXT_PUBLIC_API_URL` не нужен.

## Архитектура загрузки (prod)

```
Браузер → Vercel Blob (public URL)
       → POST /api/files/from-blob?auto_analyze=1  (Postgres)
       → Replicate start_analysis(blob_url)
       → poll GET /api/files/{id} до status=analyzed
```

## Локальная разработка

```bash
cd backend && uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev
```

Локально: Postgres из `.env`, загрузка через `/api/files/upload` (файлы ≤4 МБ) или chunk-upload (>4 МБ).

## Структура

```
vercel.json          ← frontend (Next.js) + backend (FastAPI)
frontend/            ← UI + /upload/blob route
backend/             ← API + Replicate
```
