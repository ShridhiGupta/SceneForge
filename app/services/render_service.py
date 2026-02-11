import os
from moviepy.editor import VideoFileClip, concatenate_videoclips
import cv2

class RenderService:
    def __init__(self):
        pass
    
    def render_final_video(self, clip_paths: list, output_path: str):
        """
        Combine multiple video clips into a final video
        """
        try:
            # Method 1: Using MoviePy (preferred)
            self._render_with_moviepy(clip_paths, output_path)
            
            return output_path
            
        except Exception as e:
            # Fallback to OpenCV method
            try:
                self._render_with_opencv(clip_paths, output_path)
                return output_path
            except Exception as e2:
                raise Exception(f"Failed to render final video: {str(e)}, Fallback also failed: {str(e2)}")
    
    def _render_with_moviepy(self, clip_paths: list, output_path: str):
        """
        Render final video using MoviePy
        """
        # Load all clips
        clips = []
        for clip_path in clip_paths:
            if os.path.exists(clip_path):
                clip = VideoFileClip(clip_path)
                clips.append(clip)
            else:
                raise ValueError(f"Clip file not found: {clip_path}")
        
        if not clips:
            raise ValueError("No valid clips found")
        
        # Concatenate clips
        final_clip = concatenate_videoclips(clips, method="compose")
        
        # Write final video
        final_clip.write_videofile(
            output_path,
            fps=24,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True
        )
        
        # Close all clips
        for clip in clips:
            clip.close()
        final_clip.close()
    
    def _render_with_opencv(self, clip_paths: list, output_path: str):
        """
        Render final video using OpenCV (fallback method)
        """
        # Get video properties from first clip
        cap = cv2.VideoCapture(clip_paths[0])
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        # Process each clip
        for clip_path in clip_paths:
            if os.path.exists(clip_path):
                cap = cv2.VideoCapture(clip_path)
                
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    
                    out.write(frame)
                
                cap.release()
            else:
                print(f"Warning: Clip file not found: {clip_path}")
        
        out.release()
