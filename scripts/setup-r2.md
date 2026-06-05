# Cloudflare R2 для censorai (бесплатно ~10 GB)

После настройки прод выбирает **R2 вместо Vercel Blob** (`GET /api/files/upload-strategy` → `s3`).

## 1. Создать bucket

1. https://dash.cloudflare.com → **R2** → **Create bucket**
2. Имя, например: `censorai-videos`
3. Location: **Europe (EEUR)** или ближе к пользователям

## 2. API token (это не «пароль» от аккаунта)

1. R2 → **Manage R2 API Tokens** → **Create API token**
2. Permission: **Object Read & Write** на bucket
3. Сохраните **две строки** (показываются один раз):
   - **Access Key ID** → `S3_ACCESS_KEY`
   - **Secret Access Key** → `S3_SECRET_KEY` (длинная секретная строка, не пароль Cloudflare)

Пароль от cloudflare.com здесь **не нужен** — только эти два ключа.

## 3. Account ID

Dashboard → R2 → справа **Account ID** (32 символа).

## 4. Переменные в Vercel

**Project → Settings → Environment Variables → Production** (сервис **backend**):

| Переменная | Значение |
|------------|----------|
| `S3_ENDPOINT_URL` | `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` |
| `S3_ACCESS_KEY` | Access Key ID |
| `S3_SECRET_KEY` | Secret Access Key |
| `S3_BUCKET` | `censorai-videos` |
| `S3_REGION` | `auto` |

`BLOB_READ_WRITE_TOKEN` можно оставить — будет запасным путём, если R2 не настроен.

## 5. Redeploy

```bash
git push origin main
# или
npx vercel deploy --prod --yes
```

## 6. Проверка

```bash
curl -sS https://censorai.vercel.app/api/health | jq .env.has_object_storage
# true

curl -sS https://censorai.vercel.app/api/files/upload-strategy | jq .
# { "method": "s3", "object_storage": true, ... }
```

В UI загрузка: **«Загрузка в хранилище…»** (R2), не «в облако» (Blob).

## Локально

Добавьте в `backend/.env.secrets`:

```env
S3_ENDPOINT_URL=https://<ACCOUNT_ID>.r2.cloudflarestorage.com
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
S3_BUCKET=censorai-videos
S3_REGION=auto
```

После анализа файлы в R2 удаляются (`DELETE_BLOB_AFTER_ANALYSIS` действует и для `s3://`).
