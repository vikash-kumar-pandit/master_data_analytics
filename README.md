# DataStudio 2026 — Production-Grade Big Data Analytics Platform

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/Frontend-React-61DAFB?style=flat-square&logo=react)](https://react.dev/)
[![TailwindCSS](https://img.shields.io/badge/UI-TailwindCSS-38B2AC?style=flat-square&logo=tailwind-css)](https://tailwindcss.com/)
[![TypeScript](https://img.shields.io/badge/Language-TypeScript-3178C6?style=flat-square&logo=typescript)](https://www.typescriptlang.org/)
[![Docker](https://img.shields.io/badge/Deploy-Docker-2496ED?style=flat-square&logo=docker)](https://www.docker.com/)

## 📋 Project Overview

DataStudio 2026 is a full-stack, production-grade big data analytics platform designed for real-time metrics visualization, secure user authentication, and scalable data processing. Built following 2026 industry standards with a modular, type-safe architecture.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│           React Frontend (Port 5173)        │
│  - TanStack Query (Server State)            │
│  - TailwindCSS (Styling)                    │
│  - Axios (HTTP Client)                      │
└──────────────────┬──────────────────────────┘
                   │ JWT Bearer Token
                   ▼
┌─────────────────────────────────────────────┐
│          FastAPI Backend (Port 8000)        │
│  - JWT Authentication                       │
│  - Global Exception Handler                 │
│  - Structured Logging                       │
│  - Protected Routes                         │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│        Database / Data Sources (Future)     │
│  - PostgreSQL / BigQuery / Kafka            │
└─────────────────────────────────────────────┘
```

---

## 🚀 Tech Stack

| Layer       | Technology                                     |
|-------------|------------------------------------------------|
| Frontend    | React 18, TypeScript, Vite, TailwindCSS        |
| State Mgmt  | TanStack Query, Zustand                        |
| Backend     | FastAPI, Uvicorn, Pydantic                     |
| Security    | JWT (python-jose), OAuth2                      |
| DevOps      | Docker, Docker Compose, Terraform              |
| Testing     | Pytest                                         |

---

## 📦 Project Structure

```
├── backend/                  # FastAPI server
│   ├── main.py              # Entry point + routes
│   ├── auth.py              # JWT authentication logic
│   └── requirements.txt     # Python dependencies
├── frontend/                 # React application
│   ├── src/
│   │   ├── components/
│   │   │   ├── dashboard/   # StatCard, Charts, Tables
│   │   │   └── layout/      # Header, Footer, MainLayout
│   │   ├── pages/           # Login, Dashboard
│   │   ├── services/        # API client (Axios)
│   │   ├── App.tsx          # Root component
│   │   └── main.tsx         # Entry point
│   ├── package.json
│   └── tsconfig.json
├── terraform/               # GCP infrastructure
├── docker-compose.yml       # Production deployment
└── README.md
```

---

## 🛠️ Local Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- npm / yarn

### 1. Clone the repository
```bash
git clone <your-repo-url>
cd datastudio-2026
```

### 2. Backend Setup
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```
✅ Backend running at: `http://localhost:8000`
📚 API Docs: `http://localhost:8000/docs`

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
✅ Frontend running at: `http://localhost:5173`

---

## 🔐 API Endpoints

| Method | Endpoint   | Auth     | Description                          |
|--------|------------|----------|--------------------------------------|
| POST   | `/token`   | Public   | Get JWT access token (login)         |
| GET    | `/stats`   | Bearer   | Fetch dashboard metrics              |
| GET    | `/health`  | Public   | Health check (for monitoring)        |

### Sample Login Request
```bash
curl -X POST http://localhost:8000/token \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'
```

### Sample Authenticated Request
```bash
curl http://localhost:8000/stats \
  -H "Authorization: Bearer <your_access_token>"
```

---

## 🐳 Docker Deployment

```bash
docker-compose -f docker-compose.prod.yml up -d
```

---

## 🧪 Testing

```bash
cd backend
pytest
```

---

## 📈 Roadmap

- [x] JWT Authentication
- [x] Protected Routes
- [x] Global Error Handling
- [x] Structured Logging
- [ ] PostgreSQL + SQLAlchemy ORM
- [ ] Alembic migrations
- [ ] Real-time WebSocket updates
- [ ] BigQuery / Kafka integration
- [ ] Multi-tenant support
- [ ] Role-based access control (RBAC)

---

## 📄 License

MIT License — feel free to use this in your own projects.

---

## 🤝 Contributing

Pull requests welcome! For major changes, please open an issue first to discuss.

---

**Built with ❤️ for the 2026 production era.**
