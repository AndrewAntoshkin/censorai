# Деплой на Vercel

## 1. Импорт проекта

1. Откройте https://vercel.com/new
2. **Import** репозитория `AndrewAntoshkin/censorai`
3. **Root Directory:** `frontend`
4. Framework: Next.js (определится автоматически)

## 2. Переменные окружения

| Переменная | Значение |
|------------|----------|
| `REPLICATE_API_TOKEN` | токен с replicate.com |
| `REPLICATE_MODEL` | `google/gemini-3.5-flash` |
| `VIDEO_PROVIDER` | `replicate` |

`NEXT_PUBLIC_API_URL` **не нужен** — API на том же домене (`/api/...`).

## 3. Deploy

Нажмите **Deploy**. Через 2–3 минуты сайт будет на `https://censorai-xxx.vercel.app`.

## 4. Локальная разработка

```bash
# Терминал 1 — API
cd backend && uvicorn app.main:app --reload --port 8000

# Терминал 2 — UI
cd frontend && npm run dev
```

## Примечание

- GitHub Pages остаётся демо-витриной: https://andrewantoshkin.github.io/censorai/
- Полная версия с загрузкой — на Vercel
