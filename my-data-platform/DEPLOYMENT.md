# Deployment Guide — Make the project available 24/7

This guide explains how to host the frontend and backend so users can access the app 24/7.

Summary (recommended setup):
- Frontend: Deploy static site to GitHub Pages (workflow added). Alternatively Netlify/Vercel.
- Backend: Deploy FastAPI app to Render / Railway / Fly / Heroku (Render recommended for simplicity).

1) Frontend (automatic via GitHub Actions)
- I added `.github/workflows/deploy_frontend.yml` which builds `frontend` and deploys `frontend/dist` to the repository's `gh-pages` branch.
- To enable GitHub Pages for your repo:
  - Push this repository to GitHub.
  - In the repository Settings → Pages, set Source to the `gh-pages` branch (or let Actions create it and then enable).

Notes:
- The workflow triggers on pushes to `main` or `master`.
- The site will be available at `https://<your-github-username>.github.io/<repo-name>/`.

2) Backend (options)
- Option A — Render (recommended):
  - Create a free Render account and connect your repo.
  - Create a new Web Service, point to the `backend` directory, set the start command to:
    - `uvicorn backend.main:app --host 0.0.0.0 --port 10000 --reload` (remove `--reload` for production)
  - Add required environment variables in the Render dashboard (SECRET keys, DB path, SMTP settings, etc.).

- Option B — Railway / Fly / Heroku: similar steps—create a project, point to the repo, provide start command and env vars.

- Option C — Container (any provider): Build a Docker image and deploy.
  - Create `Dockerfile` in `backend/` (example below) and push to Render or any container host.

Example simple Dockerfile (manual create in `backend/Dockerfile`):
```
FROM python:3.11-slim
WORKDIR /app
COPY ./backend /app
RUN pip install --upgrade pip
# If you have requirements.txt, uncomment next line
# COPY backend/requirements.txt /app/requirements.txt
# RUN pip install -r requirements.txt
RUN pip install uvicorn fastapi polars fpdf python-multipart
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

3) CORS and frontend <-> backend connectivity
- If frontend is served from `https://<user>.github.io/<repo>/`, set `VITE_API_URL` in frontend build or use relative path.
- Ensure FastAPI `CORSMiddleware` allows the frontend origin.

4) Continuous deployment for backend
- Use Render's native GitHub integration with `render.yaml` for automatic deploys on push.
- The repo also includes a Dockerfile and GHCR workflow as an optional image build path, but it is not required for the Render deployment.

5) Custom domain (optional)
- Configure GitHub Pages custom domain for frontend and configure backend custom domain or proxy.

If you want, I can:
- (A) Walk through setting up Render and create the exact service configuration.
- (B) Add a Docker Hub publish workflow instead of GHCR if you prefer that registry.

Tell me which option you prefer and I'll continue: create Dockerfile, add backend CI/CD, or walk you through Render setup step-by-step.

6) Render IaaS automation (recommended)
- I added a `render.yaml` at the repo root so Render can auto-create the backend service from the repo.
- To use it:
  1. Push this repo to GitHub.
  2. In Render, create a new web service and choose "Connect a repository".
  3. Render will detect `render.yaml` and create `my-data-platform-backend` from it.
  4. Add the runtime env vars in the Render dashboard (`SMTP_*`, `SENTRY_DSN`, and any DB overrides you need).
  5. Deploy — Render will run the `buildCommand` and `startCommand` automatically.

Notes on `render.yaml`:
- It uses `uvicorn backend.main:app` and expects `requirements.txt` in `backend/` (file added).
- The file includes placeholder env vars — move secrets into Render's secret manager rather than committing them.

If you'd like, I can also:
- (C) Configure a Render Health Check URL or custom domains and update CORS accordingly.

