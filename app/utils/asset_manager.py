import os
import shutil
from typing import List, Optional
from pathlib import Path
import hashlib

class AssetManager:
    def __init__(self, base_dir: str = "uploads"):
        self.base_dir = Path(base_dir)
        self.images_dir = self.base_dir / "images"
        self.clips_dir = self.base_dir / "clips"
        self.videos_dir = self.base_dir / "videos"
        
        # Ensure directories exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """
        Create necessary directories if they don't exist
        """
        for directory in [self.images_dir, self.clips_dir, self.videos_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def get_image_path(self, filename: str) -> str:
        """
        Get full path for an image file
        """
        return str(self.images_dir / filename)
    
    def get_clip_path(self, filename: str) -> str:
        """
        Get full path for a clip file
        """
        return str(self.clips_dir / filename)
    
    def get_video_path(self, filename: str) -> str:
        """
        Get full path for a video file
        """
        return str(self.videos_dir / filename)
    
    def save_uploaded_file(self, file_content: bytes, filename: str, asset_type: str) -> str:
        """
        Save uploaded file to appropriate directory
        """
        if asset_type == "image":
            file_path = self.get_image_path(filename)
        elif asset_type == "clip":
            file_path = self.get_clip_path(filename)
        elif asset_type == "video":
            file_path = self.get_video_path(filename)
        else:
            raise ValueError(f"Unknown asset type: {asset_type}")
        
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        return file_path
    
    def delete_asset(self, file_path: str) -> bool:
        """
        Delete an asset file
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            print(f"Failed to delete asset {file_path}: {str(e)}")
            return False
    
    def cleanup_orphaned_assets(self, active_paths: List[str]) -> int:
        """
        Clean up assets that are no longer referenced in the database
        """
        deleted_count = 0
        
        # Get all files in asset directories
        all_files = []
        for directory in [self.images_dir, self.clips_dir, self.videos_dir]:
            all_files.extend([str(f) for f in directory.rglob("*") if f.is_file()])
        
        # Delete files not in active_paths
        for file_path in all_files:
            if file_path not in active_paths:
                if self.delete_asset(file_path):
                    deleted_count += 1
        
        return deleted_count
    
    def get_file_hash(self, file_path: str) -> str:
        """
        Get MD5 hash of a file
        """
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""
    
    def get_file_size(self, file_path: str) -> int:
        """
        Get file size in bytes
        """
        try:
            return os.path.getsize(file_path)
        except Exception:
            return 0
    
    def get_asset_info(self, file_path: str) -> dict:
        """
        Get information about an asset file
        """
        if not os.path.exists(file_path):
            return {"exists": False}
        
        return {
            "exists": True,
            "size": self.get_file_size(file_path),
            "hash": self.get_file_hash(file_path),
            "modified_time": os.path.getmtime(file_path)
        }
    
    def duplicate_asset(self, source_path: str, new_filename: str) -> Optional[str]:
        """
        Duplicate an asset file
        """
        if not os.path.exists(source_path):
            return None
        
        # Determine destination directory based on file extension
        file_ext = Path(source_path).suffix.lower()
        if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
            dest_path = self.get_image_path(new_filename)
        elif file_ext in ['.mp4', '.avi', '.mov', '.mkv']:
            dest_path = self.get_clip_path(new_filename)
        else:
            dest_path = self.get_video_path(new_filename)
        
        try:
            shutil.copy2(source_path, dest_path)
            return dest_path
        except Exception as e:
            print(f"Failed to duplicate asset: {str(e)}")
            return None
