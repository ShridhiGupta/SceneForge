from fastapi import APIRouter, HTTPException, Depends
from app.schemas.decision_engine import DecisionRequest, DecisionResponse, FailureContext
from app.services.decision_engine import decision_engine
from app.services.decision_executor import decision_executor
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/decision-engine", tags=["decision-engine"])


@router.post("/analyze", response_model=DecisionResponse)
async def analyze_failure(request: DecisionRequest):
    """
    Analyze a failure and get recovery decision
    """
    try:
        decision = await decision_engine.analyze_failure(request.context)
        
        return DecisionResponse(
            decision=decision,
            processing_time_ms=None  # Could be added if needed
        )
    except Exception as e:
        logger.error(f"Decision analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute")
async def execute_decision(context: FailureContext) -> Dict[str, Any]:
    """
    Handle failure and execute decision
    """
    try:
        result = await decision_executor.handle_failure(context)
        return result
    except Exception as e:
        logger.error(f"Decision execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_decision_engine_status() -> Dict[str, Any]:
    """
    Get decision engine status
    """
    return {
        "available": decision_engine.is_available(),
        "engine_type": "llm" if decision_engine.is_available() else "rule_based",
        "openai_configured": decision_engine.client is not None
    }


@router.post("/test")
async def test_decision_engine(context: FailureContext) -> Dict[str, Any]:
    """
    Test decision engine with sample data
    """
    try:
        # Get decision
        decision = await decision_engine.analyze_failure(context)
        
        # Don't execute, just return decision
        return {
            "decision": decision.dict(),
            "context": context.dict(),
            "success": True
        }
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return {
            "decision": None,
            "context": context.dict(),
            "success": False,
            "error": str(e)
        }
