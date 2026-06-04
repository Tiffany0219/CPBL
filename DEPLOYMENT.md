# GoBase Deployment

## Recommended Demo Setup

- Backend: Render Web Service
- Frontend: Render Static Site or Vercel
- Data: committed demo JSON files and static images
- User database: SQLite by default for demo, PostgreSQL via `DATABASE_URL` for production

## Backend Environment

Render web service:

- Root directory: repo root
- Build command: `pip install -r cpbl-backend/requirements.txt`
- Start command: `cd cpbl-backend && gunicorn app:app --bind 0.0.0.0:$PORT`

Environment variables:

```env
CPBL_SEASON_YEAR=2026
CPBL_DATA_DIR=/opt/render/project/src/cpbl-backend
FLASK_DEBUG=0
```

Optional production database:

```env
DATABASE_URL=postgresql://...
```

## Frontend Environment

Vite needs the API URL at build time:

```env
VITE_API_BASE=https://YOUR_BACKEND_URL/api
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
https://YOUR_FRONTEND_URL
```
