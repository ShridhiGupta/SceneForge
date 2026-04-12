import cv2
import numpy as np
import os
import time
import logging

logger = logging.getLogger(__name__)

class ClipGenerationService:
    """
    Mock video clip generation service
    Used when MoviePy is not available
    """
    
    def __init__(self):
        self.fps = 30
        logger.info("Mock ClipGenerationService initialized")
    
    def generate_clip(self, image_path: str, duration: float, output_path: str):
        """
        Generate a mock video clip from a static image
        Creates a simple video with the static image
        """
        try:
            # Validate inputs
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image not found: {image_path}")
            
            if duration <= 0:
                raise ValueError("Duration must be positive")
            
            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Read the image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not read image: {image_path}")
            
            height, width = image.shape[:2]
            
            # Calculate video parameters
            total_frames = int(duration * self.fps)
            
            # Create video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_writer = cv2.VideoWriter(
                output_path, 
                fourcc, 
                self.fps, 
                (width, height)
            )
            
            if not video_writer.isOpened():
                raise RuntimeError("Could not create video writer")
            
            # Write the same frame for the entire duration
            for _ in range(total_frames):
                video_writer.write(image)
            
            # Release the writer
            video_writer.release()
            
            logger.info(f"Mock video clip created: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to generate clip: {e}")
            raise
    
    def generate_clip_with_transitions(self, image_path: str, duration: float, output_path: str, 
                                     fade_in: float = 0.5, fade_out: float = 0.5):
        """
        Generate a video clip with fade transitions
        """
        try:
            # Validate inputs
            if fade_in + fade_out > duration:
                raise ValueError("Fade durations cannot exceed total duration")
            
            # Read the image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not read image: {image_path}")
            
            height, width = image.shape[:2]
            total_frames = int(duration * self.fps)
            
            # Create video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_writer = cv2.VideoWriter(
                output_path, 
                fourcc, 
                self.fps, 
                (width, height)
            )
            
            if not video_writer.isOpened():
                raise RuntimeError("Could not create video writer")
            
            # Calculate fade frame counts
            fade_in_frames = int(fade_in * self.fps)
            fade_out_frames = int(fade_out * self.fps)
            normal_frames = total_frames - fade_in_frames - fade_out_frames
            
            # Generate frames with transitions
            for frame_num in range(total_frames):
                if frame_num < fade_in_frames:
                    # Fade in: gradually increase opacity
                    alpha = (frame_num + 1) / fade_in_frames
                    frame = cv2.addWeighted(image, alpha, np.zeros_like(image), 1 - alpha, 0)
                elif frame_num < fade_in_frames + normal_frames:
                    # Normal: full opacity
                    frame = image.copy()
                else:
                    # Fade out: gradually decrease opacity
                    fade_progress = (frame_num - fade_in_frames - normal_frames) / fade_out_frames
                    alpha = 1 - fade_progress
                    frame = cv2.addWeighted(image, alpha, np.zeros_like(image), 1 - alpha, 0)
                
                video_writer.write(frame)
            
            video_writer.release()
            
            logger.info(f"Mock video clip with transitions created: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to generate clip with transitions: {e}")
            raise
    
    def get_video_info(self, video_path: str) -> dict:
        """
        Get video information
        """
        try:
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Video not found: {video_path}")
            
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                raise RuntimeError("Could not open video file")
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = frame_count / fps if fps > 0 else 0
            
            cap.release()
            
            return {
                "fps": fps,
                "frame_count": frame_count,
                "width": width,
                "height": height,
                "duration": duration,
                "file_size": os.path.getsize(video_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check if the service is available"""
        return True
    
    def get_supported_formats(self) -> list[str]:
        """Get supported video formats"""
        return ['.mp4', '.avi', '.mov', '.mkv']
