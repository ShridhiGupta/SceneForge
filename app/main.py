from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import video, auth, decision_engine, rag_memory, quality_evaluation, multi_agent, metrics, cost_optimization
from app.core.database import engine
from app.models import video as video_model

video_model.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SceneForge - AI Video Generation Platform",
    description="A distributed AI workflow system for generating videos from scripts",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(video.router, prefix="/api/v1/videos", tags=["videos"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(decision_engine.router, prefix="/api/v1")
app.include_router(rag_memory.router, prefix="/api/v1")
app.include_router(quality_evaluation.router, prefix="/api/v1")
app.include_router(multi_agent.router, prefix="/api/v1")
app.include_router(metrics.router, prefix="/api/v1")
app.include_router(cost_optimization.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "SceneForge AI Video Generation Platform"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
