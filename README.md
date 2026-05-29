# фреймчек (CensorAI)

AI-анализ видеоконтента на соответствие требованиям законодательства РФ. Бэкенд — FastAPI + Replicate (Gemini), фронтенд — Next.js.

## Быстрый старт (локально)

```bash
# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # добавьте REPLICATE_API_TOKEN
uvicorn app.main:app --reload --port 8000

# Frontend (другой терминал)
cd frontend
npm install
npm run dev
```

Откройте http://localhost:3005

## Тест Replicate

```bash
cd backend
source .env  # или export REPLICATE_API_TOKEN=...
python3 test_analyze.py /path/to/video.mp4
```

## Продакшен на Vercel (рекомендуется)

Фронт + API на одном домене. Загрузка и Replicate работают после деплоя.

**Инструкция:** [scripts/vercel-setup.md](scripts/vercel-setup.md)

Кратко:
1. https://vercel.com/new → Import `AndrewAntoshkin/censorai`
2. **Root Directory:** корень репо (пусто), preset **Services**
3. Env: `REPLICATE_API_TOKEN`, `REPLICATE_MODEL=google/gemini-3.5-flash`
4. Deploy

## GitHub Pages (только витрина)

| URL | Назначение |
|-----|------------|
| https://andrewantoshkin.github.io/censorai/ | Статическая демо-витрина |

Для живого API на Pages задайте `NEXT_PUBLIC_API_URL` в GitHub Secrets (например URL Vercel).

### Обновить встроенные демо-примеры на Pages

```bash
cd backend && python3 seed_demo.py && python3 export_demo_static.py
git add frontend/public/demo/ && git commit -m "Update demo bundle" && git push
```

## Структура

- `backend/` — API, Replicate, SQLite
- `frontend/` — Next.js UI
- `frontend/public/demo/` — JSON для статического демо
