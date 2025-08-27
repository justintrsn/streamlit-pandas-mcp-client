"""Temporary storage utilities for file management."""

import streamlit as st
import tempfile
import shutil
from pathlib import Path
from typing import BinaryIO, Optional, Dict, List, Any
import uuid
import time
import os

class TempFileManager:
    """Manage temporary files for the session."""
    
    def __init__(self):
        self.temp_dir = self._get_or_create_temp_dir()
    
    def _get_or_create_temp_dir(self) -> Path:
        """Get or create session-specific temporary directory."""
        if "temp_dir" not in st.session_state:
            st.session_state.temp_dir = tempfile.mkdtemp(prefix="mcp_client_")
        
        temp_path = Path(st.session_state.temp_dir)
        temp_path.mkdir(exist_ok=True)
        return temp_path
    
    def save_uploaded_file(self, uploaded_file: BinaryIO, custom_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Save uploaded file to temporary directory.
        
        Args:
            uploaded_file: Streamlit uploaded file object
            custom_name: Optional custom filename
            
        Returns:
            Dictionary with file information
        """
        try:
            # Generate unique filename
            original_name = uploaded_file.name
            file_id = str(uuid.uuid4())[:8]
            
            if custom_name:
                file_name = f"{file_id}_{custom_name}"
            else:
                file_name = f"{file_id}_{original_name}"
            
            file_path = self.temp_dir / file_name
            
            # Write file
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getvalue())
            
            # Get file info
            file_stat = file_path.stat()
            
            file_info = {
                "id": file_id,
                "original_name": original_name,
                "stored_name": file_name,
                "path": str(file_path),
                "size": file_stat.st_size,
                "uploaded_at": time.time(),
                "type": self._detect_file_type(original_name)
            }
            
            return file_info
            
        except Exception as e:
            st.error(f"Error saving file: {e}")
            return {}
    
    def delete_file(self, file_path: str) -> bool:
        """Delete a file from temporary storage."""
        try:
            path = Path(file_path)
            if path.exists() and path.parent == self.temp_dir:
                path.unlink()
                return True
            return False
        except Exception as e:
            st.error(f"Error deleting file: {e}")
            return False
    
    def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get information about a stored file."""
        try:
            path = Path(file_path)
            if not path.exists():
                return None
            
            stat = path.stat()
            return {
                "name": path.name,
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "type": self._detect_file_type(path.name)
            }
        except Exception:
            return None
    
    def list_files(self) -> List[Dict[str, Any]]:
        """List all files in temporary directory."""
        files = []
        try:
            for file_path in self.temp_dir.glob("*"):
                if file_path.is_file():
                    info = self.get_file_info(str(file_path))
                    if info:
                        files.append({
                            **info,
                            "path": str(file_path)
                        })
        except Exception as e:
            st.error(f"Error listing files: {e}")
        
        return files
    
    def cleanup(self):
        """Clean up all temporary files."""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception as e:
            st.error(f"Error during cleanup: {e}")
    
    def get_storage_usage(self) -> Dict[str, Any]:
        """Get current storage usage statistics."""
        total_size = 0
        file_count = 0
        
        try:
            for file_path in self.temp_dir.glob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
                    file_count += 1
        except Exception:
            pass
        
        return {
            "total_size": total_size,
            "file_count": file_count,
            "formatted_size": self.format_size(total_size)
        }
    
    def _detect_file_type(self, filename: str) -> str:
        """Detect file type from extension."""
        suffix = Path(filename).suffix.lower()
        
        type_map = {
            '.csv': 'CSV',
            '.tsv': 'TSV', 
            '.xlsx': 'Excel',
            '.xls': 'Excel',
            '.json': 'JSON',
            '.parquet': 'Parquet',
            '.pq': 'Parquet'
        }
        
        return type_map.get(suffix, 'Unknown')
    
    def format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

# Global instance
temp_manager = TempFileManager()

# Cleanup function for session end
def cleanup_on_session_end():
    """Register cleanup function to run when session ends."""
    if "cleanup_registered" not in st.session_state:
        import atexit
        atexit.register(temp_manager.cleanup)
        st.session_state.cleanup_registered = True