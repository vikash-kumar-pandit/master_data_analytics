# my-data-platform

## Backend

Open 3 backend-related terminals.

```bash
cd backend
pip install -r requirements.txt
$env:OPENAI_API_KEY="your_key_here"
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Run Redis and Celery worker in separate terminals:

```bash
docker run -d -p 6379:6379 redis
```

```bash
cd backend
celery -A worker.celery_app worker --loglevel=info
```

## Frontend

Open a separate frontend terminal.

```bash
cd frontend
npm install
npm run dev
```

The frontend expects the backend to be available at `http://localhost:8000`.

If you want GPT-4o insights, set `OPENAI_API_KEY` before starting the backend.

## Final Run Order

1. Start Redis.
2. Start Celery worker.
3. Start FastAPI server.
4. Start Frontend.