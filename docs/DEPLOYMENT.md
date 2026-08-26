# Deployment Guide

This project uses a GitHub-driven deployment flow:

```text
Pull request -> GitHub Actions -> merge to main
  -> Render builds the backend Dockerfile after checks pass
  -> Vercel builds and promotes the React frontend after checks pass
```

## 1. Before connecting cloud accounts

1. Install Docker Desktop and verify `docker compose version`.
2. Run the backend and frontend verification suites.
3. Push both repositories and protect `main`: require a pull request, require
   the CI and CodeQL checks, block force pushes, and dismiss stale approvals.
4. Never put real data in the free Render database. It expires after 30 days
   and has no managed backup.

## 2. Render backend and PostgreSQL

1. Sign in to Render with GitHub and authorize only the backend repository.
2. Open **Blueprints**, choose **New Blueprint Instance**, select this repository,
   and apply `render.yaml`.
3. Wait for the database, Docker build, migrations, and health check to pass.
4. Record the API URL, for example `https://inventory-saas-api.onrender.com`.
5. In the web service environment, add:

   - `CORS_ALLOWED_ORIGINS=https://<project>.vercel.app`
   - `CSRF_TRUSTED_ORIGINS=https://<project>.vercel.app`
   - `SENTRY_DSN=<backend project DSN>`
   - `APP_RELEASE=<git SHA>` when release tracking is configured

6. Verify `/api/v1/health/live/`, `/api/v1/health/ready/`, `/api/v1/docs/`, and
   `/admin/login/` over HTTPS. Do not print `SECRET_KEY` or `DATABASE_URL`.

The free service runs migrations from the container entrypoint. After upgrading
the web service, set `RUN_MIGRATIONS=false` and configure Render's pre-deploy
command as `python manage.py migrate --noinput`.

## 3. Vercel frontend

1. Import `inventory-saas-frontend` from GitHub into Vercel.
2. Keep the detected Vite build command (`npm run build`) and output (`dist`).
3. Configure Production and Preview variables:

   - `VITE_API_BASE_URL=https://<backend>.onrender.com/api/v1`
   - `VITE_PASSWORD_RESET_ENABLED=false`
   - `VITE_SENTRY_DSN=<frontend project DSN>`
   - `VITE_APP_ENVIRONMENT=production`

4. Enable Vercel Deployment Checks for the frontend CI workflow.
5. Deploy, then add the final Vercel origin to the backend CORS/CSRF variables
   and redeploy the backend.
6. Verify direct navigation to `/login`, `/register`, and `/products`; the SPA
   rewrite in `vercel.json` must return the application instead of 404.

## 4. SMS activation

Password recovery remains hidden while the provider is unavailable. After a
Kavenegar account and approved OTP template exist:

1. Set `SMS_BACKEND=kavenegar`, `KAVENEGAR_API_KEY`, and `KAVENEGAR_TEMPLATE`
   only in Render secrets.
2. Confirm an OTP reaches a test phone from the Render region.
3. Set `VITE_PASSWORD_RESET_ENABLED=true` in Vercel and redeploy.
4. Test request, incorrect code, expiry, successful reset, replay denial, login,
   and revocation of the old refresh token.

## 5. Release acceptance

Run the workflow in `DEMO_CHECKLIST.md`, inspect both Sentry projects, confirm
the uptime monitor sees readiness, and record the deployed Git SHAs. A failed
check must prevent promotion in both platforms.
