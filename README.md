# SceneForge - AI Video Generation Platform

A distributed, long-running, failure-prone, media-heavy AI workflow system for generating videos from user scripts using a pipeline-based approach: scene → image → clip → final render.

## 🚀 Features

- **Distributed Architecture**: Built with FastAPI, Celery, and Redis for scalable video processing
- **AI-Powered**: Generates images from text descriptions using AI services
- **Pipeline Processing**: Scene → Image → Clip → Final Video rendering
- **Failure Handling**: Robust retry mechanisms and error tracking
- **Asset Management**: Efficient handling of images, video clips, and final videos
- **Modern UI**: Beautiful, animated React frontend with real-time progress tracking
- **PostgreSQL**: Reliable data storage with comprehensive models
- **Docker Support**: Easy deployment with containerization

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React UI      │    │   FastAPI       │    │   PostgreSQL    │
│   (Frontend)    │◄──►│   (Backend)     │◄──►│   (Database)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Celery        │    │   Redis         │
                       │   (Workers)     │◄──►│   (Queue)       │
                       └─────────────────┘    └─────────────────┘
```

## 📋 Workflow

1. **User submits script** → Creates video record
2. **Scene parsing** → Splits script into individual scenes
3. **Image generation** → AI generates images for each scene
4. **Clip creation** → Converts images to video clips with animations
5. **Final rendering** → Combines clips into final video
6. **Asset management** → Tracks and manages all media files

## 🛠️ Tech Stack

### Backend
- **FastAPI**: Modern, fast web framework for building APIs
- **Celery**: Distributed task queue for long-running processes
- **Redis**: Message broker and result backend
- **PostgreSQL**: Robust relational database
- **SQLAlchemy**: ORM for database operations
- **Alembic**: Database migrations
- **MoviePy/OpenCV**: Video processing
- **Pillow**: Image processing

### Frontend
- **React**: Modern UI framework
- **Framer Motion**: Smooth animations
- **TailwindCSS**: Utility-first CSS framework
- **Lucide React**: Beautiful icons
- **Axios**: HTTP client for API calls

### Infrastructure
- **Docker**: Containerization
- **Docker Compose**: Multi-container orchestration

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd sceneforge
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start all services**
   ```bash
   docker-compose up -d
   ```

4. **Initialize database**
   ```bash
   # Run database migrations
   docker-compose exec backend alembic upgrade head
   ```

5. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## 📁 Project Structure

```
sceneforge/
├── app/                          # Backend application
│   ├── api/                      # API routes
│   │   ├── auth.py              # Authentication endpoints
│   │   └── video.py             # Video management endpoints
│   ├── core/                     # Core configuration
│   │   ├── config.py            # Settings and environment
│   │   └── database.py          # Database connection
│   ├── models/                   # Database models
│   │   └── video.py             # Video, Scene, Clip models
│   ├── services/                 # Business logic
│   │   ├── image_service.py     # AI image generation
│   │   ├── clip_service.py      # Video clip creation
│   │   └── render_service.py    # Final video rendering
│   ├── tasks/                    # Celery tasks
│   │   ├── video_tasks.py       # Video workflow orchestration
│   │   ├── image_tasks.py       # Image generation tasks
│   │   ├── clip_tasks.py        # Clip generation tasks
│   │   └── render_tasks.py     # Rendering tasks
│   ├── utils/                    # Utilities
│   │   ├── error_handler.py     # Error handling and retry logic
│   │   └── asset_manager.py     # File management
│   ├── celery_app.py            # Celery configuration
│   └── main.py                  # FastAPI application entry
├── frontend/                     # React frontend
│   ├── src/
│   │   ├── components/          # Reusable components
│   │   ├── pages/              # Page components
│   │   ├── contexts/           # React contexts
│   │   └── utils/              # Frontend utilities
│   ├── public/                 # Static assets
│   └── package.json            # Frontend dependencies
├── alembic/                     # Database migrations
├── uploads/                     # Generated media files
├── docker-compose.yml           # Docker orchestration
├── Dockerfile                   # Backend container
└── requirements.txt             # Python dependencies
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Database
DATABASE_URL=postgresql://sceneforge:sceneforge123@localhost:5432/sceneforge

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI Services (Optional)
OPENAI_API_KEY=your-openai-api-key
STABILITY_API_KEY=your-stability-api-key

# File Storage
UPLOAD_DIR=./uploads
MAX_FILE_SIZE=100MB
```

## 📊 API Endpoints

### Authentication
- `POST /api/v1/auth/token` - Login and get access token

### Videos
- `GET /api/v1/videos` - List all videos
- `POST /api/v1/videos` - Create new video
- `GET /api/v1/videos/{id}` - Get video details
- `DELETE /api/v1/videos/{id}` - Delete video

### Documentation
- `GET /docs` - Interactive API documentation (Swagger)
- `GET /redoc` - Alternative API documentation

## 🔍 Monitoring

### Celery Monitoring
```bash
# View active tasks
docker-compose exec celery-worker celery -A app.celery_app inspect active

# View worker stats
docker-compose exec celery-worker celery -A app.celery_app inspect stats
```

### Database Monitoring
```bash
# Connect to PostgreSQL
docker-compose exec db psql -U sceneforge -d sceneforge
```

## 🧪 Development

### Running Locally

1. **Backend setup**
   ```bash
   cd app
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r ../requirements.txt
   uvicorn main:app --reload
   ```

2. **Frontend setup**
   ```bash
   cd frontend
   npm install
   npm start
   ```

3. **Celery worker**
   ```bash
   cd app
   celery -A celery_app worker --loglevel=info
   ```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## 🔒 Security Considerations

- Change default passwords and secrets in production
- Use HTTPS in production
- Implement proper authentication and authorization
- Validate all user inputs
- Use environment variables for sensitive data
- Regularly update dependencies

## 🚀 Deployment

### Production Deployment

1. **Set up production environment variables**
2. **Use SSL certificates**
3. **Set up reverse proxy (nginx)**
4. **Configure proper logging**
5. **Set up monitoring and alerts**
6. **Regular backups**

### Scaling

- **Horizontal scaling**: Add more Celery workers
- **Database scaling**: Use read replicas
- **File storage**: Use cloud storage (S3, GCS)
- **CDN**: For static assets and videos

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Troubleshooting

### Common Issues

1. **Database connection failed**
   - Check if PostgreSQL is running
   - Verify connection string in .env

2. **Celery tasks not processing**
   - Check Redis connection
   - Verify Celery worker is running

3. **Frontend not connecting to backend**
   - Check API URL configuration
   - Verify CORS settings

### Logs

```bash
# View backend logs
docker-compose logs -f backend

# View Celery logs
docker-compose logs -f celery-worker

# View frontend logs
docker-compose logs -f frontend
```

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Check the documentation
- Review the troubleshooting section
#   S c e n e F o r g e  
 