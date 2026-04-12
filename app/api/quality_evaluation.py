from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from app.schemas.quality_evaluation import (
    QualityEvaluationRequest, 
    QualityEvaluationResponse,
    QualityMetrics
)
from app.services.quality_evaluation import quality_evaluator
from app.services.clip_evaluation_mock import clip_evaluator
from app.services.llm_evaluation import llm_evaluator
from typing import Optional
import os
import uuid
import aiofiles
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quality-evaluation", tags=["quality-evaluation"])


@router.post("/evaluate", response_model=QualityEvaluationResponse)
async def evaluate_quality(request: QualityEvaluationRequest):
    """
    Evaluate image quality using CLIP and LLM methods
    """
    try:
        response = await quality_evaluator.evaluate_quality(request)
        return response
    except Exception as e:
        logger.error(f"Quality evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluate-upload")
async def evaluate_uploaded_image(
    file: UploadFile = File(...),
    prompt: str = Query(..., description="Prompt used for image generation"),
    model_used: str = Query(default="unknown", description="AI model used"),
    threshold: float = Query(default=0.5, ge=0.0, le=1.0),
    methods: str = Query(default="combined", description="Evaluation methods: clip, llm, combined")
):
    """
    Evaluate uploaded image quality
    """
    try:
        # Save uploaded file temporarily
        upload_dir = "uploads/temp"
        os.makedirs(upload_dir, exist_ok=True)
        
        file_id = str(uuid.uuid4())
        file_extension = file.filename.split(".")[-1] if file.filename else "jpg"
        temp_path = os.path.join(upload_dir, f"{file_id}.{file_extension}")
        
        async with aiofiles.open(temp_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        try:
            # Parse methods
            from app.schemas.quality_evaluation import EvaluationMethod
            method_map = {
                "clip": [EvaluationMethod.CLIP_SCORE],
                "llm": [EvaluationMethod.LLM_EVALUATION],
                "combined": [EvaluationMethod.COMBINED]
            }
            evaluation_methods = method_map.get(methods.lower(), [EvaluationMethod.COMBINED])
            
            # Create evaluation request
            request = QualityEvaluationRequest(
                image_path=temp_path,
                prompt=prompt,
                model_used=model_used,
                methods=evaluation_methods,
                min_quality_threshold=threshold
            )
            
            # Evaluate
            response = await quality_evaluator.evaluate_quality(request)
            
            return {
                "success": True,
                "result": response.dict() if response.success else None,
                "error": response.error if not response.success else None,
                "file_info": {
                    "filename": file.filename,
                    "size": len(content),
                    "temp_path": temp_path
                }
            }
            
        finally:
            # Clean up temporary file
            try:
                os.remove(temp_path)
            except:
                pass
    
    except Exception as e:
        logger.error(f"Upload evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quick-evaluate")
async def quick_evaluate(
    image_path: str = Query(..., description="Path to image file"),
    prompt: str = Query(..., description="Prompt to evaluate against"),
    threshold: float = Query(default=0.5, ge=0.0, le=1.0)
):
    """
    Quick quality evaluation (synchronous for testing)
    """
    try:
        if not os.path.exists(image_path):
            raise HTTPException(status_code=404, detail=f"Image not found: {image_path}")
        
        result = quality_evaluator.quick_evaluate(image_path, prompt, threshold)
        
        return {
            "success": True,
            "result": result.dict(),
            "image_path": image_path,
            "prompt": prompt
        }
        
    except Exception as e:
        logger.error(f"Quick evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system-status")
async def get_system_status():
    """
    Get quality evaluation system status
    """
    try:
        return {
            "quality_evaluator": quality_evaluator.get_system_status(),
            "available": quality_evaluator.is_available()
        }
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clip-status")
async def get_clip_status():
    """
    Get CLIP evaluator status
    """
    try:
        return {
            "available": clip_evaluator.is_available(),
            "model_info": clip_evaluator.get_model_info()
        }
    except Exception as e:
        logger.error(f"CLIP status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/llm-status")
async def get_llm_status():
    """
    Get LLM evaluator status
    """
    try:
        return {
            "available": llm_evaluator.is_available(),
            "model_info": llm_evaluator.get_model_info()
        }
    except Exception as e:
        logger.error(f"LLM status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-comparison")
async def test_comparison(
    image_path: str = Query(..., description="Path to image file"),
    prompt: str = Query(..., description="Prompt to evaluate against"),
    threshold: float = Query(default=0.5, ge=0.0, le=1.0)
):
    """
    Test comparison between CLIP and LLM evaluation methods
    """
    try:
        if not os.path.exists(image_path):
            raise HTTPException(status_code=404, detail=f"Image not found: {image_path}")
        
        # Evaluate with CLIP
        clip_result = None
        if clip_evaluator.is_available():
            clip_result = clip_evaluator.evaluate_image_text_similarity(image_path, prompt)
        
        # Evaluate with LLM
        llm_result = None
        if llm_evaluator.is_available():
            llm_result = await llm_evaluator.evaluate_image_quality(image_path, prompt)
        
        # Calculate combined
        if clip_result and llm_result:
            combined = quality_evaluator._calculate_combined_score(
                clip_result, llm_result, 0.6, 0.4, threshold
            )
        else:
            combined = None
        
        return {
            "image_path": image_path,
            "prompt": prompt,
            "threshold": threshold,
            "clip_result": clip_result.dict() if clip_result else None,
            "llm_result": llm_result.dict() if llm_result else None,
            "combined_result": combined.dict() if combined else None,
            "recommendation": "PASS" if combined and combined.passes_threshold else "FAIL"
        }
        
    except Exception as e:
        logger.error(f"Test comparison failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Health check for quality evaluation system
    """
    try:
        clip_available = clip_evaluator.is_available()
        llm_available = llm_evaluator.is_available()
        system_available = quality_evaluator.is_available()
        
        overall_status = "healthy" if system_available else "degraded"
        
        return {
            "status": overall_status,
            "components": {
                "clip_evaluator": "healthy" if clip_available else "unhealthy",
                "llm_evaluator": "healthy" if llm_available else "unhealthy",
                "quality_evaluator": "healthy" if system_available else "unhealthy"
            },
            "available_methods": {
                "clip": clip_available,
                "llm": llm_available,
                "combined": system_available
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
