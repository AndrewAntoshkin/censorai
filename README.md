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

## Продакшен (GitHub Pages + Render API)

| Компонент | Где | URL |
|-----------|-----|-----|
| Фронтенд | GitHub Pages | https://andrewantoshkin.github.io/censorai/ |
| API (FastAPI + Replicate) | Render | https://censorai-api.onrender.com |

Фронт ходит в API по `NEXT_PUBLIC_API_URL` (GitHub Secret). Загрузка видео и анализ через Replicate работают, когда API поднят.

### Один раз: задеплоить API на Render

1. Откройте (или нажмите Deploy):  
   **https://render.com/deploy?repo=https://github.com/AndrewAntoshkin/censorai**
2. Войдите в Render (GitHub OAuth).
3. В переменных окружения укажите **`REPLICATE_API_TOKEN`** (тот же, что в `backend/.env`).
4. Дождитесь статуса **Live** (~5–10 мин).

Проверка: https://censorai-api.onrender.com/api/health → `{"status":"ok",...}`

### Секреты GitHub (уже настроены скриптом)

```bash
./scripts/setup-production.sh   # из backend/.env → GitHub Secrets
```

- `REPLICATE_API_TOKEN` — для CI (опционально)
- `NEXT_PUBLIC_API_URL` — `https://censorai-api.onrender.com`

После деплоя API перезапустите workflow **Deploy demo to GitHub Pages** (Actions → Run workflow).

### Обновить встроенные демо-примеры на Pages

```bash
cd backend && python3 seed_demo.py && python3 export_demo_static.py
git add frontend/public/demo/ && git commit -m "Update demo bundle" && git push
```

## Структура

- `backend/` — API, Replicate, SQLite
- `frontend/` — Next.js UI
- `frontend/public/demo/` — JSON для статического демо
