import os
import time
import logging
from typing import Optional
import random
from PIL import Image
from app.schemas.quality_evaluation import CLIPScoreResult
from app.core.config import settings

logger = logging.getLogger(__name__)


class CLIPEvaluator:
    """
    Mock CLIP-based image-text similarity evaluator
    Used when the actual CLIP package is not available
    """
    
    def __init__(self):
        self.device = "cpu"
        self.model_name = "ViT-B/32"
        self.model = "mock_model"
        self.preprocess = "mock_preprocess"
        logger.info(f"Mock CLIP evaluator initialized (CLIP package not available)")
    
    def evaluate_image_text_similarity(self, image_path: str, text_prompt: str) -> CLIPScoreResult:
        """
        Mock evaluate image-text similarity using random scoring
        """
        start_time = time.time()
        
        try:
            # Validate inputs
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image not found: {image_path}")
            
            if not text_prompt or not text_prompt.strip():
                raise ValueError("Text prompt cannot be empty")
            
            # Generate mock score based on text length and image size
            text_length = len(text_prompt)
            
            try:
                image = Image.open(image_path)
                image_size = image.size[0] * image.size[1]
            except:
                image_size = 100000  # Default size
            
            # Generate a pseudo-random but consistent score
            base_score = 0.5  # Base score
            text_factor = min(text_length / 200, 0.3)  # Text length factor
            size_factor = min(image_size / 1000000, 0.2)  # Image size factor
            
            # Add some randomness but keep it consistent for same inputs
            seed = hash(text_path + str(image_size)) % 1000
            random.seed(seed)
            random_factor = (random.random() - 0.5) * 0.2
            
            clip_score = base_score + text_factor + size_factor + random_factor
            clip_score = max(0.0, min(1.0, clip_score))  # Clamp to 0-1
            
            # Calculate confidence based on score magnitude
            confidence = abs(clip_score - 0.5) * 2  # Higher confidence for extreme scores
            
            processing_time = (time.time() - start_time) * 1000
            
            return CLIPScoreResult(
                clip_score=clip_score,
                confidence=confidence,
                processing_time_ms=processing_time,
                model_used=f"mock/{self.model_name.lower().replace('/', '-')}"
            )
            
        except Exception as e:
            logger.error(f"Mock CLIP evaluation failed: {e}")
            raise
    
    def batch_evaluate(self, image_paths: list[str], text_prompts: list[str]) -> list[CLIPScoreResult]:
        """
        Mock batch evaluate multiple image-text pairs
        """
        if len(image_paths) != len(text_prompts):
            raise ValueError("Number of image paths and text prompts must match")
        
        results = []
        for image_path, text_prompt in zip(image_paths, text_prompts):
            try:
                result = self.evaluate_image_text_similarity(image_path, text_prompt)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to evaluate {image_path}: {e}")
                # Add a failed result
                results.append(CLIPScoreResult(
                    clip_score=0.0,
                    confidence=0.0,
                    processing_time_ms=0.0,
                    model_used=self.model_name
                ))
        
        return results
    
    def get_model_info(self) -> dict:
        """Get model information"""
        return {
            "model_name": self.model_name,
            "device": self.device,
            "available": True,
            "input_resolution": 224,
            "note": "Mock CLIP evaluator - using simulated scores"
        }
    
    def is_available(self) -> bool:
        """Check if CLIP evaluator is available"""
        return True


# Singleton instance
clip_evaluator = CLIPEvaluator()
