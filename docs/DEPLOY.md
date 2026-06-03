# Деплой на прод (Vercel)

Единый чеклист для **censorai.vercel.app**. Следуйте порядку каждый раз — так прод совпадает с git и не теряются правки.

## Архитектура

| Сервис | Путь | Роль |
|--------|------|------|
| `frontend` | `/` | Next.js UI |
| `backend` | `/api` | FastAPI, Replicate, ffmpeg, Postgres |

Конфиг: корневой [`vercel.json`](../vercel.json) (`experimentalServices`).

---

## Перед каждым деплоем

### 1. Код в git

```bash
git status
git add -A   # только если все изменения нужны в проде
git commit -m "кратко: зачем (не только что)"
git push origin main
```

**Не деплоить с большим объёмом незакоммиченных файлов** — `vercel deploy` возьмёт рабочую папку, но GitHub/Vercel Git Integration потом откатит прод.

### 2. Локальная проверка (по возможности)

```bash
# backend
cd backend && .venv/bin/python test_video_segmentation.py

# frontend lint/build (опционально)
cd frontend && npm run build
```

### 3. Секреты на Vercel (Dashboard → Project → Settings → Environment Variables)

Обязательно на **Production** (и при необходимости Preview):

| Переменная | Где нужна | Откуда |
|------------|-----------|--------|
| `POSTGRES_URL` | backend | Storage → Postgres (Neon) |
| `BLOB_READ_WRITE_TOKEN` | **backend** | Storage → Blob store |
| `BLOB_STORE_ID` | backend | из Blob store |
| `REPLICATE_API_TOKEN` | backend | replicate.com |
| `REPLICATE_MODEL` | backend | `google/gemini-3.5-flash` |
| `VIDEO_PROVIDER` | backend | `replicate` |
| `AUTH_SECRET` | backend | свой секрет (сессии) |
| `PUBLIC_API_BASE_URL` | backend | `https://censorai.vercel.app` |

`BLOB_READ_WRITE_TOKEN` на **frontend-сервисе не обязателен** — токены для загрузки выдаёт `POST /api/files/blob-upload` на backend.

Подключение store: Storage → выбрать store → **Connect to Project** → сервис **backend**.

---

## Деплой

### Вариант A — из git (предпочтительно)

1. Push в `main`.
2. Vercel Dashboard → Deployments — дождаться **Ready** у production.
3. Убедиться, что деплой собран с нужного коммита (SHA в карточке деплоя).

### Вариант B — CLI с машины

```bash
cd /path/to/censorai
git push origin main   # сначала push!

npx vercel deploy --prod --yes
```

Требуется: `npx vercel login`, проект привязан к репо.

**После CLI-деплоя** всё равно закоммитьте и запушьте тот же код в `main`.

---

## Проверка после деплоя (5 минут)

```bash
PROD=https://censorai.vercel.app

# 1) API и БД
curl -sS "$PROD/api/health" | python3 -m json.tool
# Ожидаем: "database": "postgres", "ephemeral_db": false

# 2) Blob пишется
curl -sS -X POST "$PROD/api/files/blob-selftest" | python3 -m json.tool
# Ожидаем: "ok": true

# 3) Токен для клиентской загрузки
curl -sS -X POST "$PROD/api/files/blob-upload" \
  -H "Content-Type: application/json" \
  -d '{"type":"blob.generate-client-token","payload":{"pathname":"videos/smoke.mp4","multipart":true}}' \
  | head -c 120
# Ожидаем: HTTP 200 и "clientToken":"vercel_blob_client_...
```

В браузере: жёсткое обновление **Cmd+Shift+R**, тестовая загрузка малого MP4.

### Логи

```bash
npx vercel logs censorai.vercel.app --since 15m
# во время загрузки:
npx vercel logs censorai.vercel.app --follow
```

Ожидаемая цепочка для успешного файла:

1. `POST /api/files/blob-upload` (или `blob-selftest`)
2. *(браузер → Blob CDN — в логах не видно)*
3. `POST /api/files/from-blob`
4. для длинных: `Using bundled ffmpeg` → Replicate → `Deleted blob`

---

## Операции на проде

### Очистка Blob (если квота Hobby 1 GB)

```bash
# сначала dry-run
curl -sS -X POST "$PROD/api/files/blob-cleanup" \
  -H "Content-Type: application/json" \
  -d '{"secret":"censor-demo-2026","dry_run":true}'

# удаление сирот (не трогает файлы в статусе analyzing/uploaded/processing)
curl -sS -X POST "$PROD/api/files/blob-cleanup" \
  -H "Content-Type: application/json" \
  -d '{"secret":"censor-demo-2026"}'
```

После анализа исходники удаляются сами (`DELETE_BLOB_AFTER_ANALYSIS=true`).

### Откат

Vercel Dashboard → Deployments → предыдущий **Ready** → **Promote to Production**.

Или:

```bash
npx vercel rollback   # интерактивно в CLI
```

---

## Локальная разработка (не прод)

```bash
npm run setup
# секреты: backend/.env + backend/.env.secrets (см. scripts/import-secrets.sh)
./scripts/dev.sh
# UI http://localhost:3005 , API http://localhost:8000
```

Локально большие файлы: `BLOB_READ_WRITE_TOKEN` в `backend/.env.secrets` или chunk-upload.

---

## Частые ошибки

| Симптом | Причина | Действие |
|---------|---------|----------|
| «Сервер не выдал токен» | `blob-upload` 500 на backend | Проверить `BLOB_*` на **backend**, redeploy |
| Застряло на 1–10% «в облако» | Медленный интернет / 2 файла параллельно | Грузить по одному; подождать |
| Storage quota exceeded | Blob Hobby 1 GB | `blob-cleanup`, Dashboard Storage |
| `No space left on device` (ffmpeg) | Старый деплой / много сегментов в /tmp | Актуальный код: один сегмент в /tmp |
| `database: sqlite` на health | Нет Postgres | Подключить Postgres store к backend |

---

## Чеклист одной строкой

```
commit → push main → deploy → health postgres → blob-selftest ok →
blob-upload ok → smoke upload в UI → logs from-blob
```

Подробнее про первичную настройку Vercel: [scripts/vercel-setup.md](../scripts/vercel-setup.md).
