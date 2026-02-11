import cv2
import numpy as np
import os
from moviepy.editor import ImageClip, CompositeVideoClip

class ClipGenerationService:
    def __init__(self):
        pass
    
    def generate_clip(self, image_path: str, duration: float, output_path: str):
        """
        Generate a video clip from a static image
        """
        try:
            # Method 1: Using MoviePy (simpler approach)
            self._generate_clip_with_moviepy(image_path, duration, output_path)
            
            return output_path
            
        except Exception as e:
            # Fallback to OpenCV method
            try:
                self._generate_clip_with_opencv(image_path, duration, output_path)
                return output_path
            except Exception as e2:
                raise Exception(f"Failed to generate clip: {str(e)}, Fallback also failed: {str(e2)}")
    
    def _generate_clip_with_moviepy(self, image_path: str, duration: float, output_path: str):
        """
        Generate video clip using MoviePy
        """
        # Create image clip
        img_clip = ImageClip(image_path)
        
        # Set duration
        img_clip = img_clip.set_duration(duration)
        
        # Add some basic motion (slow zoom)
        def zoom_in(t):
            return 1 + 0.1 * t / duration
        
        img_clip = img_clip.resize(lambda t: 1 + 0.1 * t / duration)
        
        # Write to file
        img_clip.write_videofile(
            output_path,
            fps=24,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True
        )
        
        img_clip.close()
    
    def _generate_clip_with_opencv(self, image_path: str, duration: float, output_path: str):
        """
        Generate video clip using OpenCV (fallback method)
        """
        # Read the image
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not read image: {image_path}")
        
        height, width, layers = img.shape
        size = (width, height)
        
        # Calculate fps and total frames
        fps = 24
        total_frames = int(duration * fps)
        
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, size)
        
        # Generate frames with slight zoom effect
        for i in range(total_frames):
            # Calculate zoom factor
            zoom_factor = 1 + (0.1 * i / total_frames)
            
            # Apply zoom
            new_width = int(width / zoom_factor)
            new_height = int(height / zoom_factor)
            
            # Crop and resize
            start_x = (width - new_width) // 2
            start_y = (height - new_height) // 2
            
            cropped = img[start_y:start_y + new_height, start_x:start_x + new_width]
            zoomed = cv2.resize(cropped, (width, height))
            
            out.write(zoomed)
        
        out.release()
