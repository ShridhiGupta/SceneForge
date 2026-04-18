# SceneForge — AI Video Generation Pipeline Engine

A distributed, fault-tolerant pipeline system for generating videos from scripts using AI.  
Designed for long-running, failure-prone, and media-heavy workloads.

---

## Overview

SceneForge converts user-provided scripts into fully rendered videos using a multi-stage asynchronous pipeline. Each stage operates independently, supports retries, and is designed for scalability.

---

## Core Pipeline

Script → Scenes → Images → Clips → Final Video

Each stage:
- Executes asynchronously
- Can fail and retry independently
- Maintains state for observability and recovery

---

## Architecture

Frontend (React)
        │
        ▼
FastAPI Backend (Orchestrator)
        │
        ▼
Redis Queue  →  Celery Workers
        │
        ▼
PostgreSQL (State + Metadata)
        │
        ▼
Media Storage (Images, Clips, Videos)

---

## Key Features

- Distributed task execution using Celery and Redis
- Fault-tolerant pipeline with retry and error handling
- Scalable architecture with horizontal worker expansion
- Real-time progress tracking from frontend
- Efficient asset management for media files
- Modular service-based backend design

---

## Tech Stack

### Backend
- FastAPI
- Celery
- Redis
- PostgreSQL
- SQLAlchemy
- Alembic
- MoviePy / OpenCV
- Pillow

### Frontend
- React
- TailwindCSS
- Framer Motion
- Axios

### Infrastructure
- Docker
- Docker Compose

---

## Project Structure
sceneforge/
├── app/
│ ├── api/
│ ├── core/
│ ├── models/
│ ├── services/
│ ├── tasks/
│ ├── utils/
│ ├── celery_app.py
│ └── main.py
├── frontend/
├── alembic/
├── uploads/
├── docker-compose.yml
├── Dockerfile
└── requirements.txt


---

## Getting Started

### Prerequisites

- Docker
- Docker Compose
- Git

---

### Installation

```bash
git clone <repository-url>
cd sceneforge
cp .env.example .env
```

Update .env with required configuration.

### Run the System
```bash
docker-compose up -d
```
### Initialize Database
```bash
docker-compose exec backend alembic upgrade head
```
### Access Services
Frontend: http://localhost:3000
Backend API: http://localhost:8000
API Docs: http://localhost:8000/docs
### Environment Variables
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/sceneforge
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30

UPLOAD_DIR=./uploads
MAX_FILE_SIZE=100MB

OPENAI_API_KEY=optional
STABILITY_API_KEY=optional
```
### API Endpoints
#### Authentication
```bash
POST /api/v1/auth/token
```
#### Videos
```bash
GET /api/v1/videos
POST /api/v1/videos
GET /api/v1/videos/{id}
DELETE /api/v1/videos/{id}
```
### Monitoring
#### Celery
```bash
docker-compose exec celery-worker celery -A app.celery_app inspect active
docker-compose exec celery-worker celery -A app.celery_app inspect stats
```
#### Database
```bash
docker-compose exec db psql -U sceneforge -d sceneforge
```
### Development
#### Backend
```bash
cd app
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
pip install -r ../requirements.txt
uvicorn main:app --reload
```
#### Frontend
```bash
cd frontend
npm install
npm start
```
#### Run Worker
```bash
cd app
celery -A celery_app worker --loglevel=info
```
#### Database Migrations
```bash
alembic revision --autogenerate -m "message"
alembic upgrade head
alembic downgrade -1
```
#### Deployment Considerations
- Use HTTPS
- Configure reverse proxy (Nginx)
- Enable logging and monitoring
- Store media in cloud storage (S3 or GCS)
- Use CDN for video delivery
- Set up automated backups
- Scaling Strategy
- Add more Celery workers for parallel processing
- Use database read replicas for scaling reads
- Offload media storage to cloud object storage
- Introduce task prioritization queues if needed
- 
#### Security
- Store secrets in environment variables
- Validate all user inputs
- Implement authentication and authorization
- Restrict file uploads and size limits
- Regularly update dependencies
- Common Issues
- Celery not processing tasks
- Ensure Redis is running
- Check worker logs
- Database connection issues
- Verify DATABASE_URL
- Ensure PostgreSQL container is running
- Frontend not connecting
- Check API base URL
- Verify CORS settings
- 
#### Logs
```bash
docker-compose logs -f backend
docker-compose logs -f celery-worker
docker-compose logs -f frontend
```
License

# MIT License
