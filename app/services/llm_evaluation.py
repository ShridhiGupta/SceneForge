import os
import time
import base64
import logging
from typing import Optional
from openai import OpenAI
from PIL import Image
import io
from app.schemas.quality_evaluation import LLMEvaluationResult
from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMEvaluator:
    """
    LLM-based image quality evaluator using vision models
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
        self.model = "gpt-4-vision-preview"
        self.max_image_size = (1024, 1024)  # Resize images to reduce API costs
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64 for API"""
        try:
            # Open and resize image
            with Image.open(image_path) as img:
                img = img.convert("RGB")
                
                # Resize if too large
                if img.size[0] > self.max_image_size[0] or img.size[1] > self.max_image_size[1]:
                    img.thumbnail(self.max_image_size, Image.Resampling.LANCZOS)
                
                # Convert to bytes
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='JPEG', quality=85)
                img_byte_arr = img_byte_arr.getvalue()
                
                # Encode to base64
                base64_str = base64.b64encode(img_byte_arr).decode('utf-8')
                return base64_str
                
        except Exception as e:
            logger.error(f"Failed to encode image {image_path}: {e}")
            raise
    
    def _create_evaluation_prompt(self, text_prompt: str) -> str:
        """Create evaluation prompt for LLM"""
        return f"""You are an expert image quality evaluator. Your task is to evaluate how well an image matches the given prompt.

Prompt: "{text_prompt}"

Please evaluate the image based on:
1. How well it matches the prompt description
2. Overall visual quality and aesthetics
3. Technical quality (resolution, clarity, composition)
4. Any missing elements or inaccuracies

Respond in this exact JSON format:
{{
    "matches_prompt": true/false,
    "quality_score": 0.0-1.0,
    "reasoning": "Detailed explanation of your evaluation",
    "confidence": 0.0-1.0
}}

Be objective and thorough in your evaluation. Consider both literal interpretation and creative interpretation of the prompt."""
    
    def evaluate_image_quality(self, image_path: str, text_prompt: str) -> LLMEvaluationResult:
        """
        Evaluate image quality using LLM vision model
        """
        start_time = time.time()
        
        try:
            if not self.client:
                raise ValueError("OpenAI client not available")
            
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image not found: {image_path}")
            
            if not text_prompt or not text_prompt.strip():
                raise ValueError("Text prompt cannot be empty")
            
            # Encode image
            base64_image = self._encode_image(image_path)
            
            # Create evaluation prompt
            evaluation_prompt = self._create_evaluation_prompt(text_prompt)
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": evaluation_prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "low"  # Use low detail to reduce costs
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500,
                temperature=0.1  # Low temperature for consistent evaluation
            )
            
            # Parse response
            content = response.choices[0].message.content
            
            # Extract JSON from response
            import json
            try:
                # Clean up response to extract JSON
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0].strip()
                elif "{" in content and "}" in content:
                    json_str = content[content.find("{"):content.rfind("}")+1]
                else:
                    raise ValueError("No JSON found in response")
                
                evaluation_data = json.loads(json_str)
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response: {content}")
                raise ValueError(f"Invalid JSON in LLM response: {e}")
            
            # Validate required fields
            required_fields = ["matches_prompt", "quality_score", "reasoning", "confidence"]
            for field in required_fields:
                if field not in evaluation_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate field types and ranges
            if not isinstance(evaluation_data["matches_prompt"], bool):
                raise ValueError("matches_prompt must be boolean")
            
            quality_score = float(evaluation_data["quality_score"])
            if not (0.0 <= quality_score <= 1.0):
                raise ValueError("quality_score must be between 0.0 and 1.0")
            
            confidence = float(evaluation_data["confidence"])
            if not (0.0 <= confidence <= 1.0):
                raise ValueError("confidence must be between 0.0 and 1.0")
            
            processing_time = (time.time() - start_time) * 1000
            
            return LLMEvaluationResult(
                matches_prompt=evaluation_data["matches_prompt"],
                quality_score=quality_score,
                reasoning=evaluation_data["reasoning"],
                confidence=confidence,
                processing_time_ms=processing_time,
                model_used=self.model
            )
            
        except Exception as e:
            logger.error(f"LLM evaluation failed: {e}")
            raise
    
    def quick_evaluate(self, image_path: str, text_prompt: str) -> LLMEvaluationResult:
        """
        Quick evaluation with simplified prompt for faster processing
        """
        start_time = time.time()
        
        try:
            # Encode image
            base64_image = self._encode_image(image_path)
            
            # Simplified prompt
            simple_prompt = f"""Rate this image against the prompt: "{text_prompt}"

Return JSON:
{{
    "matches_prompt": true/false,
    "quality_score": 0.0-1.0,
    "reasoning": "Brief explanation",
    "confidence": 0.0-1.0
}}"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": simple_prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "low"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=200,
                temperature=0.1
            )
            
            # Parse response (simplified parsing)
            content = response.choices[0].message.content
            json_str = content[content.find("{"):content.rfind("}")+1]
            evaluation_data = json.loads(json_str)
            
            processing_time = (time.time() - start_time) * 1000
            
            return LLMEvaluationResult(
                matches_prompt=evaluation_data.get("matches_prompt", False),
                quality_score=float(evaluation_data.get("quality_score", 0.0)),
                reasoning=evaluation_data.get("reasoning", "Quick evaluation"),
                confidence=float(evaluation_data.get("confidence", 0.5)),
                processing_time_ms=processing_time,
                model_used=self.model
            )
            
        except Exception as e:
            logger.error(f"Quick LLM evaluation failed: {e}")
            raise
    
    def get_model_info(self) -> dict:
        """Get model information"""
        return {
            "model": self.model,
            "available": self.client is not None,
            "max_image_size": self.max_image_size,
            "supports_vision": True
        }
    
    def is_available(self) -> bool:
        """Check if LLM evaluator is available"""
        return self.client is not None


# Singleton instance
llm_evaluator = LLMEvaluator()
