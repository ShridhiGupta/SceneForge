import requests
import os
from PIL import Image
import io
from app.core.config import settings

class ImageGenerationService:
    def __init__(self):
        self.stability_api_key = settings.stability_api_key
        self.openai_api_key = settings.openai_api_key
    
    def generate_image(self, prompt: str, output_path: str):
        """
        Generate an image from text prompt using AI service
        Currently using Stability AI as example, but can be adapted for other services
        """
        try:
            # For demo purposes, create a placeholder image
            # In production, replace with actual AI image generation API call
            
            # Example using Stability AI (you'll need to implement actual API call)
            # response = self._call_stability_api(prompt)
            
            # Placeholder: create a simple colored image with text
            self._create_placeholder_image(prompt, output_path)
            
            return output_path
            
        except Exception as e:
            raise Exception(f"Failed to generate image: {str(e)}")
    
    def _call_stability_api(self, prompt: str):
        """
        Call Stability AI API for image generation
        """
        url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
        
        headers = {
            "Authorization": f"Bearer {self.stability_api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "text_prompts": [{"text": prompt}],
            "cfg_scale": 7,
            "height": 1024,
            "width": 1024,
            "samples": 1,
            "steps": 30
        }
        
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    
    def _create_placeholder_image(self, prompt: str, output_path: str):
        """
        Create a placeholder image for demo purposes
        """
        from PIL import Image, ImageDraw, ImageFont
        
        # Create a 1024x1024 image
        img = Image.new('RGB', (1024, 1024), color=(73, 109, 137))
        draw = ImageDraw.Draw(img)
        
        # Add text
        try:
            # Try to use a nice font
            font = ImageFont.truetype("arial.ttf", 40)
        except:
            font = ImageFont.load_default()
        
        # Wrap text
        words = prompt.split()
        lines = []
        current_line = []
        
        for word in words:
            current_line.append(word)
            test_line = ' '.join(current_line)
            if draw.textlength(test_line, font=font) > 900:
                current_line.pop()
                lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        # Draw text
        y_position = 100
        for line in lines[:10]:  # Limit to 10 lines
            draw.text((50, y_position), line, fill=(255, 255, 255), font=font)
            y_position += 60
        
        # Save image
        img.save(output_path)
