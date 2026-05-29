# Деплой на Vercel (Services)

## 1. Import

1. https://vercel.com/new → Import `AndrewAntoshkin/censorai`
2. **Root Directory:** оставьте **пустым** (корень репозитория, не `frontend`)
3. Framework Preset: **Services** (определится по `vercel.json`)

## 2. Переменные окружения

| Переменная | Значение |
|------------|----------|
| `REPLICATE_API_TOKEN` | токен с replicate.com |
| `REPLICATE_MODEL` | `google/gemini-3.5-flash` |
| `VIDEO_PROVIDER` | `replicate` |

### Blob Storage (для файлов > 4 МБ)

1. Vercel Dashboard → проект → **Storage** → **Create Database** → **Blob**
2. Подключите store к проекту — появится `BLOB_READ_WRITE_TOKEN`
3. Redeploy

## 3. Deploy

После деплоя:
- UI: `https://censorai.vercel.app/`
- API: `https://censorai.vercel.app/api/health`

Фронт ходит на `/api/...` на том же домене — отдельный `NEXT_PUBLIC_API_URL` не нужен.

## Структура

```
vercel.json          ← frontend (Next.js) + backend (FastAPI)
frontend/            ← UI
backend/             ← API + Replicate
```
