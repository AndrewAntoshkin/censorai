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

## Демо на GitHub Pages

Статическая сборка с 5 готовыми примерами анализа (без загрузки новых видео).

1. Создайте репозиторий на GitHub и запушьте код:

```bash
git init
git add .
git commit -m "Initial commit with GitHub Pages demo"
git branch -M main
git remote add origin https://github.com/YOUR_USER/censorai.git
git push -u origin main
```

2. В репозитории: **Settings → Pages → Build and deployment → Source: GitHub Actions**.

3. После успешного workflow демо будет по адресу:

`https://YOUR_USER.github.io/censorai/`

### Обновить демо-данные

После новых анализов в локальной БД:

```bash
cd backend
python3 seed_demo.py
python3 export_demo_static.py
git add frontend/public/demo/
git commit -m "Update demo bundle"
git push
```

### Полный режим (с API)

Если бэкенд задеплоен отдельно (Render, Fly.io и т.д.), в workflow можно убрать `NEXT_PUBLIC_DEMO_MODE` и задать `NEXT_PUBLIC_API_URL` как GitHub secret.

## Структура

- `backend/` — API, Replicate, SQLite
- `frontend/` — Next.js UI
- `frontend/public/demo/` — JSON для статического демо
