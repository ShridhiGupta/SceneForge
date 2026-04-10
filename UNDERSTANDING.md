# SceneForge: AI Video Generation Platform - Deep Technical Understanding

## 1. High-Level Overview

### Problem Solved
SceneForge is an AI-powered video generation platform that converts text scripts into professional videos using distributed AI workflows. The core problem is orchestrating multiple AI models (image generation, quality evaluation, decision making) while maintaining quality, managing costs, and handling failures intelligently.

### Architecture Choice Rationale
The system uses a **multi-agent architecture with LangGraph** because:
- **Complex Orchestration**: Video generation requires coordinating multiple specialized AI services
- **Intelligent Decision Making**: Failures need context-aware recovery strategies using LLM + RAG memory
- **Cost Optimization**: Different AI models have varying cost-quality tradeoffs requiring dynamic selection
- **Scalability**: Distributed processing allows parallel scene generation

### System Design Flow
```
Frontend (React) 
    |
    v
Backend (FastAPI) 
    |
    v
Multi-Agent System (LangGraph)
    |
    v
AI Services (OpenAI, Stability AI, CLIP)
    |
    v
Database (SQLite) + Vector Store (FAISS)
```

## 2. Project Structure Walkthrough

### Core Application Structure
```
e:\SceneForge\
    app\
    |--- api\              # FastAPI route definitions
    |--- agents\           # Multi-agent system implementation
    |--- core\              # Configuration and database setup
    |--- models\            # SQLAlchemy ORM models
    |--- schemas\           # Pydantic data validation schemas
    |--- services\          # Business logic and external integrations
    |--- tasks\             # Celery distributed task definitions
    |--- utils\             # Utility functions and helpers
    |--- logging\           # Structured logging and metrics
```

### Folder Responsibilities

**`app/api/`** - API Layer
- **Purpose**: Define HTTP endpoints and request/response handling
- **Key Files**: `video.py`, `metrics.py`, `cost_optimization.py`, `multi_agent.py`
- **Why**: Clean separation of HTTP concerns from business logic

**`app/agents/`** - Multi-Agent System
- **Purpose**: Implement intelligent agents for pipeline orchestration
- **Key Files**: `scene_agent.py`, `image_generation_agent.py`, `quality_evaluation_agent.py`, `decision_agent.py`
- **Why**: Each agent has single responsibility, enabling independent scaling and testing

**`app/services/`** - Business Logic Layer
- **Purpose**: Core business logic and external service integrations
- **Key Files**: `decision_engine.py`, `rag_memory.py`, `cost_quality_optimizer.py`
- **Why**: Centralized business logic, reusable across different interfaces

**`app/models/`** - Data Layer
- **Purpose**: Database schema definitions using SQLAlchemy ORM
- **Key Files**: `video.py`, `memory.py`
- **Why**: Type-safe database operations with clear relationships

**`app/schemas/`** - Validation Layer
- **Purpose**: Request/response validation using Pydantic
- **Key Files**: `decision_engine.py`, `quality_evaluation.py`, `cost_optimization.py`
- **Why**: Input validation, serialization, and API documentation

**`app/tasks/`** - Distributed Processing
- **Purpose**: Celery tasks for background job processing
- **Key Files**: `image_tasks.py`, `video_tasks.py`
- **Why**: Asynchronous processing for long-running AI operations

## 3. Frontend Architecture

### Tech Stack
- **React**: Component-based UI development
- **TypeScript**: Type safety and better developer experience
- **TailwindCSS**: Utility-first styling for rapid development
- **Lucide Icons**: Consistent iconography

### Component Structure
```
src/
    components/
        ui/              # Reusable UI components
        video/           # Video-specific components
        forms/           # Form components
    pages/              # Page-level components
    hooks/              # Custom React hooks
    services/           # API communication layer
    types/              # TypeScript type definitions
```

### State Management
- **React State**: Local component state with useState/useReducer
- **API State**: Server state managed through custom hooks
- **No Global State**: Intentionally simple to avoid complexity

### API Communication
```typescript
// API service pattern
const api = {
  videos: {
    create: (data) => axios.post('/api/v1/videos', data),
    get: (id) => axios.get(`/api/v1/videos/${id}`),
    update: (id, data) => axios.put(`/api/v1/videos/${id}`, data)
  }
}
```

### Authentication Flow
1. User submits login form
2. Frontend sends credentials to `/api/v1/auth/login`
3. Backend validates and returns JWT token
4. Frontend stores token in localStorage
5. Token included in Authorization header for subsequent requests

## 4. Backend Architecture

### Entry Point: `main.py`
```python
app = FastAPI(
    title="SceneForge - AI Video Generation Platform",
    description="A distributed AI workflow system for generating videos from scripts"
)

# Middleware setup
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"])
```

### Routing Layer
Routes are organized by feature domain:
```python
app.include_router(video.router, prefix="/api/v1/videos")
app.include_router(auth.router, prefix="/api/v1/auth")
app.include_router(decision_engine.router, prefix="/api/v1")
app.include_router(multi_agent.router, prefix="/api/v1")
```

### Controller Pattern
Controllers in `app/api/` handle:
- HTTP request validation
- Business logic delegation to services
- Response formatting
- Error handling

### Service Layer
Services in `app/services/` contain:
- Core business logic
- External API integrations
- Complex computations
- Data transformations

### Middleware Stack
1. **CORS Middleware**: Handle cross-origin requests
2. **Authentication Middleware**: JWT token validation (if implemented)
3. **Logging Middleware**: Request/response logging
4. **Error Handling Middleware**: Centralized error processing

## 5. API Flow (Request-Response Lifecycle)

### Step-by-Step API Call Flow

#### Video Creation Example
```
1. Client Request
   POST /api/v1/videos
   Body: {title: string, script: string}

2. Middleware Layer
   - CORS check
   - Request logging
   - Authentication (if required)

3. Route Handler (video.py)
   @router.post("/")
   async def create_video(video: VideoCreate)

4. Input Validation
   - Pydantic schema validation
   - Type checking
   - Required field validation

5. Business Logic (video_service.py)
   - Create Video record
   - Parse script into scenes
   - Initialize pipeline state

6. Database Operation
   - SQLAlchemy ORM transaction
   - Video record insertion
   - Scene record creation

7. Response Formatting
   - Serialize with Pydantic
   - HTTP 201 Created
   - Return created video data

8. Client Response
   HTTP/1.1 201 Created
   Body: {id: int, title: string, status: string, ...}
```

### Multi-Agent Workflow Flow
```
1. Client Request
   POST /api/v1/multi-agent/execute
   Body: {video_id: int, script: string}

2. Workflow Initialization
   - Create PipelineState
   - Initialize agents
   - Start LangGraph workflow

3. Agent Execution Sequence
   Scene Agent -> Image Generation Agent -> Quality Agent -> Decision Agent

4. State Management
   - Immutable state passing between agents
   - Shared context for communication
   - Decision history tracking

5. Response
   - Final pipeline state
   - Generated video metadata
   - Quality and cost metrics
```

## 6. Database Layer

### Database Choice: SQLite
**Why SQLite:**
- **Development Simplicity**: No external database server needed
- **Portability**: Single file database
- **ACID Compliance**: Reliable transactions
- **Python Integration**: Excellent SQLAlchemy support

### Schema Design

#### Core Entities
```python
class Video(Base):
    id: int (Primary Key)
    title: str
    script: str
    status: VideoStatus
    progress: float
    created_at: datetime
    updated_at: datetime

class Scene(Base):
    id: int (Primary Key)
    video_id: int (Foreign Key -> Video.id)
    scene_number: int
    description: str
    image_path: str
    quality_score: float
    retry_count: int
    generation_cost: float
    model_used: str

class FailureMemoryDB(Base):
    id: int (Primary Key)
    failure_type: FailureType
    stage: PipelineStage
    error_logs: str
    prompt_used: str
    action_taken: RecoveryAction
    success: bool
    created_at: datetime
```

### Relationships
- **Video -> Scenes**: One-to-many (cascade delete)
- **Video -> Clips**: One-to-many
- **Scene -> Quality Results**: One-to-many
- **Failure Memory -> Embeddings**: One-to-many

### Query Patterns
```python
# SQLAlchemy ORM queries
video = db.query(Video).filter(Video.id == video_id).first()
scenes = db.query(Scene).filter(Scene.video_id == video_id).all()
failed_scenes = db.query(Scene).filter(Scene.status == TaskStatus.FAILED).all()
```

### Vector Store Integration
```python
# FAISS for similarity search
vector_store = FAISSVectorStore()
similar_failures = vector_store.search_similar_failures(embedding, top_k=5)
```

## 7. Authentication & Authorization

### Password Hashing
```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

**Why Hashing:**
- **Security**: Plain text passwords are never stored
- **Breach Protection**: Hashed passwords useless if database compromised
- **Industry Standard**: bcrypt is battle-tested and widely adopted

**Salting in bcrypt:**
- **Automatic**: bcrypt handles salting automatically
- **Unique Salt**: Each password gets unique random salt
- **Rainbow Table Resistance**: Salting prevents precomputed hash attacks

### JWT Token Authentication
```python
from jose import JWTError, jwt
from datetime import datetime, timedelta

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        return username
    except JWTError:
        return None
```

**Token Creation:**
- **Payload**: User identity + expiration
- **Signing**: HMAC-SHA256 with secret key
- **Expiration**: 30 minutes by default

**Token Verification:**
- **Signature Validation**: Ensures token wasn't tampered
- **Expiration Check**: Prevents token replay attacks
- **User Extraction**: Returns username for authorization

**Token Storage:**
- **Client Side**: localStorage in browser
- **Server Side**: Stateless (no server storage needed)
- **Transmission**: Authorization header: `Bearer <token>`

### Authorization Model
Current implementation uses **basic authentication**. Role-based access can be added:

```python
# Future role-based implementation
class User(Base):
    id: int
    username: str
    email: str
    hashed_password: str
    role: UserRole  # ADMIN, USER, VIEWER
    is_active: bool

def require_role(required_role: UserRole):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = get_current_user()
            if current_user.role != required_role:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

## 8. Security Considerations

### Sensitive Data Protection
```python
# Environment variables for secrets
class Settings(BaseSettings):
    database_url: str
    secret_key: str
    openai_api_key: str
    stability_api_key: str
    
    class Config:
        env_file = ".env"
        case_sensitive = True
```

### Attack Vector Mitigations

#### SQL Injection Prevention
```python
# SQLAlchemy ORM prevents SQL injection
# Never use raw SQL strings with user input
video = db.query(Video).filter(Video.id == video_id).first()  # Safe
# Bad: f"SELECT * FROM videos WHERE id = {user_input}"  # Vulnerable
```

#### XSS Prevention
```python
# FastAPI automatically escapes HTML in responses
# Pydantic validation ensures data types
class VideoCreate(BaseModel):
    title: str  # FastAPI will escape this in JSON responses
    script: str
```

#### CSRF Protection
```python
# FastAPI CSRF middleware can be added
from fastapi_csrf_protect import CsrfProtect

csrf = CsrfProtect(secret_key="your-secret-key")
app.include_router(csrf.router)
```

#### Rate Limiting
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v1/videos")
@limiter.limit("5/minute")
async def create_video(video: VideoCreate):
    pass
```

### Security Best Practices
1. **Environment Variables**: All secrets in `.env` file
2. **HTTPS**: Enforce SSL in production
3. **Input Validation**: Pydantic schemas for all inputs
4. **Error Handling**: Don't expose internal details in errors
5. **Logging**: Log security events without sensitive data

## 9. Error Handling & Validation

### Input Validation Strategy
```python
# Pydantic schemas for validation
class VideoCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    script: str = Field(..., min_length=10)
    
    @validator('title')
    def validate_title(cls, v):
        if not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()
```

### Error Handling Hierarchy
```python
# Global exception handler
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "type": "validation_error"}
    )

# Service-level error handling
try:
    result = await some_operation()
except SpecificException as e:
    logger.error(f"Operation failed: {e}")
    raise HTTPException(status_code=400, detail=str(e))

# Database error handling
except SQLAlchemyError as e:
    db.rollback()
    logger.error(f"Database error: {e}")
    raise HTTPException(status_code=500, detail="Database operation failed")
```

### Consistent Error Responses
```python
# Standardized error response format
{
    "detail": "Human readable error message",
    "type": "error_type",
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "uuid-1234"
}
```

## 10. Scalability & Performance

### Current Scalability Characteristics

#### Strengths
- **Horizontal Processing**: Multiple scenes can be processed in parallel
- **Agent Independence**: Each agent can be scaled independently
- **Asynchronous Processing**: Celery enables background job distribution
- **Stateless Design**: Easy to load balance across multiple instances

#### Bottlenecks Under High Load
1. **SQLite**: Single-file database limits concurrent writes
2. **Memory Usage**: Large models loaded in memory
3. **API Rate Limits**: External AI service limitations
4. **File Storage**: Local file storage doesn't scale horizontally

### Production-Scale Improvements

#### Database Scaling
```python
# Replace SQLite with PostgreSQL
DATABASE_URL=postgresql://user:pass@localhost/dbname

# Add connection pooling
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30
)
```

#### Distributed Architecture
```python
# Redis for distributed caching
REDIS_URL=redis://localhost:6379

# Multiple Celery workers
celery -A app.celery_app worker --loglevel=info --concurrency=4

# Load balancer configuration
upstream backend {
    server app1:8000;
    server app2:8000;
    server app3:8000;
}
```

#### Microservices Decomposition
```
API Gateway -> [Video Service, Scene Service, AI Service, Decision Service]
                -> [PostgreSQL, Redis, Vector DB]
```

#### Performance Optimizations
```python
# Database indexing
class Scene(Base):
    __table_args__ = (
        Index('idx_scene_video_id', 'video_id'),
        Index('idx_scene_status', 'status'),
    )

# Caching with Redis
from fastapi_cache import FastAPICache
cache = FastAPICache()

@cache(expire=300)
async def get_video(video_id: int):
    return db.query(Video).filter(Video.id == video_id).first()

# Async database operations
from databases import Database
database = Database(DATABASE_URL)

async def get_videos():
    return await database.fetch_all("SELECT * FROM videos")
```

#### Monitoring & Observability
```python
# Prometheus metrics
from prometheus_client import Counter, Histogram

video_requests = Counter('video_requests_total', ['method', 'endpoint'])
video_duration = Histogram('video_request_duration_seconds')

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    video_requests.labels(method=request.method, endpoint=request.url.path).inc()
    video_duration.observe(duration)
    
    return response
```

### FAANG-Scale Architecture
```python
# Event-driven architecture
from kafka import KafkaProducer

producer = KafkaProducer(
    bootstrap_servers=['kafka1:9092', 'kafka2:9092', 'kafka3:9092']
)

# Event sourcing for audit trails
class VideoEvent(BaseModel):
    event_id: str
    event_type: str
    aggregate_id: str
    data: dict
    timestamp: datetime

# CQRS pattern
class VideoCommand(BaseModel):
    video_id: str
    command: str
    data: dict

class VideoQuery(BaseModel):
    query_type: str
    parameters: dict
```

## 11. Interview-Ready Explanations

### "Explain this project in 2 minutes"
"SceneForge is an AI-powered video generation platform that converts text scripts into professional videos. The system uses a multi-agent architecture where specialized agents handle different aspects: Scene Agent parses scripts, Image Generation Agent creates visuals using AI models like DALL-E and Stable Diffusion, Quality Evaluation Agent ensures output quality using CLIP and GPT-4 Vision, and Decision Agent handles failures intelligently using LLM + RAG memory. The system includes cost optimization to balance quality and expense, structured logging for metrics, and can scale horizontally using Celery for distributed processing."

### "Explain the backend design decisions"
"The backend uses FastAPI for its high performance and automatic API documentation. We chose a multi-agent architecture with LangGraph because video generation requires coordinating multiple AI services with complex decision-making. Each agent has a single responsibility, making the system modular and testable. We use SQLAlchemy with SQLite for development simplicity but designed it to easily migrate to PostgreSQL for production. The decision engine uses RAG memory to learn from past failures, making the system smarter over time. Cost optimization uses utility functions to balance quality and expense, crucial for managing AI model costs."

### "Explain authentication in this project"
"Currently, SceneForge uses basic JWT authentication with bcrypt password hashing. When users log in, their credentials are validated against hashed passwords in the database. Successful authentication returns a JWT token stored client-side and sent in Authorization headers. The system uses Pydantic for input validation and FastAPI's security features for protection. For production, I would add role-based access control, refresh tokens, and integrate with OAuth providers like Google or GitHub."

### "If you had more time, what would you improve?"
"First, I'd implement comprehensive role-based access control with OAuth integration. Second, I'd migrate from SQLite to PostgreSQL with connection pooling for better scalability. Third, I'd add comprehensive monitoring with Prometheus and Grafana. Fourth, I'd implement event sourcing for audit trails and better debugging. Fifth, I'd add automated testing with CI/CD pipelines. Sixth, I'd optimize the multi-agent system with better load balancing and fault tolerance. Finally, I'd add a frontend dashboard for real-time pipeline monitoring and manual intervention capabilities."

### "How does the decision engine work?"
"The decision engine uses LLM + RAG memory to make intelligent recovery decisions. When a task fails, it retrieves similar past failures from the vector database, creates a context-rich prompt with the failure details and historical context, and sends it to GPT-4 for decision-making. The LLM returns structured JSON with the recommended action (retry, modify prompt, switch model), confidence score, and reasoning. The system then executes the decision and stores the outcome in RAG memory for future learning, creating a self-improving system."

### "How do you handle cost optimization?"
"Cost optimization uses a utility function U = alpha * quality - beta * cost. Each AI model has a profile with cost per call, expected quality, and reliability. The system calculates utility scores for all available models and selects the one with the highest score that meets constraints. It includes budget constraint handling, model switching logic, and spending optimization. The decision engine is cost-aware, considering budget limitations when making recovery decisions, and can suggest cheaper alternatives when appropriate."

### "What's the multi-agent architecture?"
"The multi-agent architecture uses LangGraph to orchestrate specialized agents: Scene Agent processes scripts into scenes, Image Generation Agent creates images using AI models, Quality Evaluation Agent assesses output quality, Decision Agent handles failures intelligently, and Cost Optimization Agent manages expenses. Each agent operates independently but shares state through a centralized PipelineState object. The system uses conditional routing between agents based on results and can implement retry loops and error recovery. This design enables parallel processing, independent scaling, and modular development."

### "How do you ensure quality?"
"Quality is ensured through multiple layers: CLIP-based text-image similarity scoring, GPT-4 Vision evaluation for detailed quality assessment, and a combined scoring system with configurable thresholds. The Quality Evaluation Agent compares results against quality thresholds and triggers the Decision Agent for low-quality outputs. The system tracks quality before and after interventions, enabling measurement of improvement. RAG memory helps learn from quality failures, and the cost-quality optimizer ensures we don't sacrifice quality for cost savings."

### "What's the RAG memory system?"
"The RAG memory system stores failure experiences and uses FAISS vector similarity to retrieve relevant past failures. When making decisions, the system encodes the failure context into embeddings, searches for top 5 similar failures, and includes them in the LLM prompt as context. This enables the system to learn from past experiences and bias decisions toward previously successful strategies. The memory includes failure type, prompt, model, action taken, success/failure outcome, and quality scores for comprehensive learning."
