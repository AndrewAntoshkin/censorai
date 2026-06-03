# фреймчек (CensorAI)

AI-анализ видеоконтента на соответствие требованиям законодательства РФ. Бэкенд — FastAPI + Replicate (Gemini), фронтенд — Next.js.

## Быстрый старт (локально)

```bash
# Один раз
npm run setup
cp backend/.env.example backend/.env   # или используйте готовый backend/.env

# Postgres (опционально; иначе SQLite в backend/censorai.db)
docker compose up -d postgres redis

# Backend + frontend
./scripts/dev.sh
# или в двух терминалах: npm run dev:backend && npm run dev
```

Откройте http://localhost:3005

**Первый вход:** `/register` → код организации `FRAMECHECK2026` (см. `FRAMECHECK_REGISTRATION_CODE` в `.env`).  
Супер-админ: email `SUPER_ADMIN_EMAIL` (по умолчанию `andrew.antoshkin@gmail.com`) — переключение организаций в сайдбаре.

Новая организация для клиента:

```bash
cd backend && .venv/bin/python scripts/create_org_code.py --name "Клиент" --slug client --code CLIENT2026
```

Дорожная карта этапов: [docs/ROADMAP.md](docs/ROADMAP.md)

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

- `backend/` — API, Replicate, Postgres (или SQLite без Docker)
- `frontend/` — Next.js UI
- `frontend/public/demo/` — JSON для статического демо
