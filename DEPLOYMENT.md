# GoBase Deployment

## Recommended Demo Setup

- Backend: Render Web Service
- Frontend: Render Static Site or Vercel
- Data: committed demo JSON files and static images
- User database: SQLite by default for demo, PostgreSQL via `DATABASE_URL` for production

## Backend Environment

Render uses a Docker backend service so Selenium can run Chromium in the cloud.

- Runtime: Docker
- Service name: `gobase-api-docker`
- Dockerfile path: `cpbl-backend/Dockerfile`
- Docker context: `.`

Environment variables:

```env
CPBL_SEASON_YEAR=2026
CPBL_DATA_DIR=/app
FLASK_DEBUG=0
CHROME_BIN=/usr/bin/chromium
CHROMEDRIVER_PATH=/usr/bin/chromedriver
```

Optional production database:

```env
DATABASE_URL=postgresql://...
```

## Frontend Environment

Vite needs the API URL at build time:

```env
VITE_API_BASE=https://gobase-api-docker.onrender.com/api
VITE_CPBL_SEASON_YEAR=2026
```

Frontend build settings:

- Root directory: `cpbl-vue`
- Build command: `npm ci && npm run build`
- Publish directory: `dist`

## Image Notes

Team logos and player photos are served by Flask from:

```txt
cpbl-backend/static/image/teams
cpbl-backend/static/image/players
```

The frontend builds image URLs from `VITE_API_BASE`, so deployed images load from:

```txt
https://YOUR_BACKEND_URL/static/image/...
```

## Deploy Flow

1. Commit and push changes to GitHub.
2. Deploy the backend first.
3. Copy the backend public URL.
4. Set `VITE_API_BASE` on the frontend service.
5. Deploy the frontend.
6. Check:

```txt
https://YOUR_BACKEND_URL/api/health
https://YOUR_BACKEND_URL/api/selenium/health
https://YOUR_FRONTEND_URL
```

`/api/selenium/health` should return `{"status":"ok","title":"selenium-ok"}` when Chromium is available in the deployed container.

Render cannot change an existing service from the Python runtime to Docker after it is created, so this project keeps the original `gobase-api` service and adds `gobase-api-docker`. After the Docker API is healthy, the old `gobase-api` service can be removed from the Render dashboard.
