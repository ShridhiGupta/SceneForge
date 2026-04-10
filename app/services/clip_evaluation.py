import os
import time
import logging
from typing import Optional
import torch
from PIL import Image
import clip
from app.schemas.quality_evaluation import CLIPScoreResult
from app.core.config import settings

logger = logging.getLogger(__name__)


class CLIPEvaluator:
    """
    CLIP-based image-text similarity evaluator
    """
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_name = "ViT-B/32"
        self.model = None
        self.preprocess = None
        self._load_model()
    
    def _load_model(self):
        """Load CLIP model"""
        try:
            # Load model
            self.model, self.preprocess = clip.load(self.model_name, device=self.device)
            self.model.eval()
            logger.info(f"CLIP model {self.model_name} loaded on {self.device}")
        except Exception as e:
            logger.error(f"Failed to load CLIP model: {e}")
            raise
    
    def evaluate_image_text_similarity(self, image_path: str, text_prompt: str) -> CLIPScoreResult:
        """
        Evaluate image-text similarity using CLIP
        """
        start_time = time.time()
        
        try:
            # Validate inputs
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image not found: {image_path}")
            
            if not text_prompt or not text_prompt.strip():
                raise ValueError("Text prompt cannot be empty")
            
            # Load and preprocess image
            image = Image.open(image_path).convert("RGB")
            image_tensor = self.preprocess(image).unsqueeze(0).to(self.device)
            
            # Tokenize text
            text_tokens = clip.tokenize([text_prompt]).to(self.device)
            
            # Get features
            with torch.no_grad():
                image_features = self.model.encode_image(image_tensor)
                text_features = self.model.encode_text(text_tokens)
                
                # Normalize features
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)
                
                # Calculate cosine similarity
                similarity = torch.matmul(image_features, text_features.T).squeeze()
                clip_score = similarity.item()
                
                # Convert to 0-1 range (CLIP outputs -1 to 1)
                clip_score = (clip_score + 1) / 2
                
                # Calculate confidence based on score magnitude
                confidence = abs(clip_score - 0.5) * 2  # Higher confidence for extreme scores
            
            processing_time = (time.time() - start_time) * 1000
            
            return CLIPScoreResult(
                clip_score=clip_score,
                confidence=confidence,
                processing_time_ms=processing_time,
                model_used=f"openai/{self.model_name.lower().replace('/', '-')}"
            )
            
        except Exception as e:
            logger.error(f"CLIP evaluation failed: {e}")
            raise
    
    def batch_evaluate(self, image_paths: list[str], text_prompts: list[str]) -> list[CLIPScoreResult]:
        """
        Batch evaluate multiple image-text pairs
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
            "available": self.model is not None,
            "input_resolution": self.model.visual.input_resolution if self.model else None
        }
    
    def is_available(self) -> bool:
        """Check if CLIP evaluator is available"""
        return self.model is not None and self.preprocess is not None


# Singleton instance
clip_evaluator = CLIPEvaluator()
