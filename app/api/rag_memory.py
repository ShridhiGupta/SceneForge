from fastapi import APIRouter, HTTPException, Depends, Query
from app.schemas.rag_memory import (
    FailureMemory, 
    MemoryQuery, 
    MemorySearchResponse, 
    MemoryStats
)
from app.services.rag_memory import rag_memory_service
from app.services.vector_store import vector_store
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag-memory", tags=["rag-memory"])


@router.post("/store", response_model=Dict[str, Any])
async def store_memory(memory: FailureMemory):
    """
    Store a failure memory in the RAG system
    """
    try:
        memory_id = await rag_memory_service.store_failure_memory(memory)
        
        if memory_id:
            return {
                "success": True,
                "memory_id": memory_id,
                "message": "Memory stored successfully"
            }
        else:
            return {
                "success": False,
                "memory_id": None,
                "message": "Failed to store memory"
            }
    except Exception as e:
        logger.error(f"Failed to store memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=MemorySearchResponse)
async def search_similar_failures(query: MemoryQuery):
    """
    Search for similar past failures
    """
    try:
        response = await rag_memory_service.search_similar_failures(query)
        return response
    except Exception as e:
        logger.error(f"Failed to search similar failures: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=MemoryStats)
async def get_memory_stats(days: int = Query(default=30, ge=1, le=365)):
    """
    Get memory statistics for the past N days
    """
    try:
        stats = await rag_memory_service.get_memory_stats(days)
        return stats
    except Exception as e:
        logger.error(f"Failed to get memory stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/successful-strategies")
async def get_successful_strategies(
    failure_type: str,
    stage: str,
    limit: int = Query(default=5, ge=1, le=20)
):
    """
    Get most successful recovery strategies for a specific failure type and stage
    """
    try:
        strategies = rag_memory_service.get_successful_strategies(
            failure_type=failure_type,
            stage=stage,
            limit=limit
        )
        return {
            "failure_type": failure_type,
            "stage": stage,
            "strategies": strategies,
            "total": len(strategies)
        }
    except Exception as e:
        logger.error(f"Failed to get successful strategies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vector-store/status")
async def get_vector_store_status():
    """
    Get vector store status and statistics
    """
    try:
        stats = vector_store.get_stats()
        return {
            "available": vector_store.is_available(),
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Failed to get vector store status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-search")
async def test_memory_search(
    error_logs: str,
    stage: str,
    prompt: str = "",
    model: str = "",
    top_k: int = Query(default=5, ge=1, le=20)
):
    """
    Test memory search with sample data
    """
    try:
        from app.schemas.rag_memory import MemoryQuery, FailureType, PipelineStage
        
        # Convert stage string to enum
        try:
            stage_enum = PipelineStage(stage.lower())
        except ValueError:
            stage_enum = PipelineStage.IMAGE
        
        # Auto-classify failure type
        failure_type = FailureType.UNKNOWN
        error_lower = error_logs.lower()
        if "timeout" in error_lower:
            failure_type = FailureType.TIMEOUT
        elif "api" in error_lower or "http" in error_lower:
            failure_type = FailureType.API_ERROR
        elif "quality" in error_lower:
            failure_type = FailureType.LOW_QUALITY
        elif "memory" in error_lower or "resource" in error_lower:
            failure_type = FailureType.RESOURCE_EXHAUSTION
        
        query = MemoryQuery(
            failure_type=failure_type,
            stage=stage_enum,
            error_logs=error_logs,
            prompt_used=prompt,
            model_used=model,
            top_k=top_k,
            min_similarity=0.6,
            require_success=True
        )
        
        response = await rag_memory_service.search_similar_failures(query)
        
        return {
            "query": query.dict(),
            "results": response.dict(),
            "message": f"Found {len(response.results)} similar failures"
        }
        
    except Exception as e:
        logger.error(f"Test search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear")
async def clear_memory(confirm: bool = Query(default=False)):
    """
    Clear all memory data (DANGEROUS - requires confirmation)
    """
    if not confirm:
        raise HTTPException(
            status_code=400, 
            detail="This action is dangerous. Set confirm=true to proceed."
        )
    
    try:
        # This would need to be implemented in the service
        # For now, just return a warning
        return {
            "message": "Memory clearing not implemented in this demo",
            "warning": "This would delete all stored failure memories"
        }
    except Exception as e:
        logger.error(f"Failed to clear memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Health check for RAG memory system
    """
    try:
        vector_available = vector_store.is_available()
        service_available = rag_memory_service.is_available()
        
        return {
            "status": "healthy" if vector_available and service_available else "degraded",
            "vector_store_available": vector_available,
            "service_available": service_available,
            "components": {
                "vector_store": "healthy" if vector_available else "unhealthy",
                "rag_service": "healthy" if service_available else "unhealthy"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
