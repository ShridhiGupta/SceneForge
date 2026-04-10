import time
import uuid
import logging
from typing import Optional, List
from app.schemas.quality_evaluation import (
    QualityEvaluationRequest, 
    QualityEvaluationResponse, 
    CombinedQualityResult,
    QualityThreshold,
    EvaluationMethod,
    QualityFailure
)
from app.services.clip_evaluation import clip_evaluator
from app.services.llm_evaluation import llm_evaluator
from app.services.decision_executor import decision_executor
from app.schemas.decision_engine import FailureContext, PipelineStage, FailureType

logger = logging.getLogger(__name__)


class QualityEvaluator:
    """
    Combined quality evaluation system using CLIP and LLM
    """
    
    def __init__(self):
        self.clip_evaluator = clip_evaluator
        self.llm_evaluator = llm_evaluator
        self.default_threshold = 0.5
        self.default_clip_weight = 0.6
        self.default_llm_weight = 0.4
    
    async def evaluate_quality(self, request: QualityEvaluationRequest) -> QualityEvaluationResponse:
        """
        Evaluate image quality using specified methods
        """
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        try:
            # Validate request
            if not request.methods:
                request.methods = [EvaluationMethod.COMBINED]
            
            # Initialize results
            clip_result = None
            llm_result = None
            
            # Perform evaluations based on requested methods
            for method in request.methods:
                if method == EvaluationMethod.CLIP_SCORE:
                    clip_result = self._evaluate_clip(request.image_path, request.prompt)
                elif method == EvaluationMethod.LLM_EVALUATION:
                    llm_result = await self._evaluate_llm(request.image_path, request.prompt)
                elif method == EvaluationMethod.COMBINED:
                    # For combined, we need both evaluations
                    clip_result = self._evaluate_clip(request.image_path, request.prompt)
                    llm_result = await self._evaluate_llm(request.image_path, request.prompt)
            
            # Calculate combined result
            if EvaluationMethod.COMBINED in request.methods:
                combined_result = self._calculate_combined_score(
                    clip_result, 
                    llm_result, 
                    request.clip_weight, 
                    request.llm_weight,
                    request.min_quality_threshold
                )
            else:
                # Create combined result from single method
                combined_result = self._create_single_method_result(
                    clip_result, llm_result, request.min_quality_threshold
                )
            
            processing_time = (time.time() - start_time) * 1000
            combined_result.evaluation_time_ms = processing_time
            
            # Check if quality passes threshold
            if not combined_result.passes_threshold:
                await self._handle_quality_failure(request, combined_result)
            
            return QualityEvaluationResponse(
                request_id=request_id,
                success=True,
                result=combined_result,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            logger.error(f"Quality evaluation failed: {e}")
            processing_time = (time.time() - start_time) * 1000
            
            return QualityEvaluationResponse(
                request_id=request_id,
                success=False,
                error=str(e),
                processing_time_ms=processing_time
            )
    
    def _evaluate_clip(self, image_path: str, prompt: str):
        """Evaluate using CLIP"""
        try:
            return self.clip_evaluator.evaluate_image_text_similarity(image_path, prompt)
        except Exception as e:
            logger.error(f"CLIP evaluation failed: {e}")
            raise
    
    async def _evaluate_llm(self, image_path: str, prompt: str):
        """Evaluate using LLM"""
        try:
            return self.llm_evaluator.evaluate_image_quality(image_path, prompt)
        except Exception as e:
            logger.error(f"LLM evaluation failed: {e}")
            raise
    
    def _calculate_combined_score(
        self, 
        clip_result, 
        llm_result, 
        clip_weight: float, 
        llm_weight: float,
        min_threshold: float
    ) -> CombinedQualityResult:
        """Calculate combined quality score"""
        
        # Normalize weights
        total_weight = clip_weight + llm_weight
        if total_weight == 0:
            clip_weight = llm_weight = 0.5
        else:
            clip_weight = clip_weight / total_weight
            llm_weight = llm_weight / total_weight
        
        # Calculate weighted score
        final_score = (clip_result.clip_score * clip_weight) + (llm_result.quality_score * llm_weight)
        
        # Determine quality threshold category
        quality_threshold = self._get_quality_threshold(final_score)
        
        # Check if passes minimum threshold
        passes_threshold = final_score >= min_threshold
        
        return CombinedQualityResult(
            final_score=final_score,
            quality_threshold=quality_threshold,
            clip_result=clip_result,
            llm_result=llm_result,
            clip_weight=clip_weight,
            llm_weight=llm_weight,
            passes_threshold=passes_threshold,
            threshold_used=min_threshold
        )
    
    def _create_single_method_result(
        self, 
        clip_result, 
        llm_result, 
        min_threshold: float
    ) -> CombinedQualityResult:
        """Create combined result from single evaluation method"""
        
        if clip_result and not llm_result:
            # CLIP only
            final_score = clip_result.clip_score
            clip_weight = 1.0
            llm_weight = 0.0
            # Create dummy LLM result
            llm_result = type('LLMResult', (), {
                'quality_score': final_score,
                'matches_prompt': final_score > 0.5,
                'reasoning': 'CLIP-based evaluation only',
                'confidence': clip_result.confidence,
                'model_used': 'N/A'
            })()
        elif llm_result and not clip_result:
            # LLM only
            final_score = llm_result.quality_score
            clip_weight = 0.0
            llm_weight = 1.0
            # Create dummy CLIP result
            clip_result = type('CLIPResult', (), {
                'clip_score': final_score,
                'confidence': llm_result.confidence,
                'processing_time_ms': 0.0,
                'model_used': 'N/A'
            })()
        else:
            # Neither available
            raise ValueError("At least one evaluation method must be available")
        
        quality_threshold = self._get_quality_threshold(final_score)
        passes_threshold = final_score >= min_threshold
        
        return CombinedQualityResult(
            final_score=final_score,
            quality_threshold=quality_threshold,
            clip_result=clip_result,
            llm_result=llm_result,
            clip_weight=clip_weight,
            llm_weight=llm_weight,
            passes_threshold=passes_threshold,
            threshold_used=min_threshold
        )
    
    def _get_quality_threshold(self, score: float) -> QualityThreshold:
        """Determine quality threshold category"""
        if score < 0.3:
            return QualityThreshold.VERY_LOW
        elif score < 0.5:
            return QualityThreshold.LOW
        elif score < 0.7:
            return QualityThreshold.MEDIUM
        elif score < 0.85:
            return QualityThreshold.HIGH
        else:
            return QualityThreshold.VERY_HIGH
    
    async def _handle_quality_failure(self, request: QualityEvaluationRequest, result: CombinedQualityResult):
        """Handle quality failure by triggering decision engine"""
        try:
            # Create quality failure record
            quality_failure = QualityFailure(
                image_path=request.image_path,
                prompt=request.prompt,
                model_used=request.model_used,
                quality_score=result.final_score,
                evaluation_result=result,
                failure_reason=f"Quality score {result.final_score:.2f} below threshold {result.threshold_used:.2f}",
                suggested_action="modify_prompt" if result.llm_result.matches_prompt else "retry"
            )
            
            # Create failure context for decision engine
            failure_context = FailureContext(
                task_name="quality_evaluation",
                stage=PipelineStage.IMAGE,
                error_logs=quality_failure.failure_reason,
                retry_count=0,
                output_quality_score=result.final_score,
                cost_so_far=0.0,  # Add actual cost if available
                model_used=request.model_used,
                prompt_used=request.prompt,
                additional_context={
                    "image_path": request.image_path,
                    "video_id": request.video_id,
                    "scene_id": request.scene_id,
                    "task_id": request.task_id,
                    "quality_failure": quality_failure.dict()
                }
            )
            
            # Trigger decision engine
            decision_result = await decision_executor.handle_failure(failure_context)
            
            logger.info(f"Quality failure handled: {decision_result}")
            
        except Exception as e:
            logger.error(f"Failed to handle quality failure: {e}")
    
    def quick_evaluate(self, image_path: str, prompt: str, threshold: float = 0.5) -> CombinedQualityResult:
        """
        Quick evaluation for pipeline integration
        """
        try:
            # Try CLIP first (faster)
            if self.clip_evaluator.is_available():
                clip_result = self.clip_evaluator.evaluate_image_text_similarity(image_path, prompt)
                
                # If CLIP score is clearly good or bad, skip LLM
                if clip_result.clip_score >= 0.8 or clip_result.clip_score <= 0.3:
                    return self._create_single_method_result(clip_result, None, threshold)
            
            # Use LLM for ambiguous cases
            if self.llm_evaluator.is_available():
                import asyncio
                llm_result = asyncio.run(self.llm_evaluator.evaluate_image_quality(image_path, prompt))
                return self._calculate_combined_score(
                    clip_result, llm_result, 0.6, 0.4, threshold
                )
            
            # Fallback to CLIP only
            if clip_result:
                return self._create_single_method_result(clip_result, None, threshold)
            
            raise ValueError("No evaluation methods available")
            
        except Exception as e:
            logger.error(f"Quick evaluation failed: {e}")
            raise
    
    def get_system_status(self) -> dict:
        """Get evaluation system status"""
        return {
            "clip_available": self.clip_evaluator.is_available(),
            "llm_available": self.llm_evaluator.is_available(),
            "clip_model": self.clip_evaluator.get_model_info(),
            "llm_model": self.llm_evaluator.get_model_info(),
            "default_threshold": self.default_threshold,
            "default_weights": {
                "clip": self.default_clip_weight,
                "llm": self.default_llm_weight
            }
        }
    
    def is_available(self) -> bool:
        """Check if quality evaluation is available"""
        return self.clip_evaluator.is_available() or self.llm_evaluator.is_available()


# Singleton instance
quality_evaluator = QualityEvaluator()
