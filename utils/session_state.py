"""Session state management for the Streamlit application."""

import streamlit as st
from typing import Dict, List, Any, Optional
import tempfile
import shutil
from pathlib import Path

def initialize_session_state():
    """Initialize all session state variables."""
    
    # Configuration
    if "config_validated" not in st.session_state:
        st.session_state.config_validated = False
    
    # API Key management
    if "openai_api_key" not in st.session_state:
        st.session_state.openai_api_key = ""
    
    # File management
    if "uploaded_files" not in st.session_state:
        st.session_state.uploaded_files = {}
    
    if "temp_dir" not in st.session_state:
        # Create temporary directory that persists during session
        st.session_state.temp_dir = tempfile.mkdtemp(prefix="mcp_client_")
    
    # DataFrame tracking
    if "loaded_dataframes" not in st.session_state:
        st.session_state.loaded_dataframes = {}
    
    # Chart management
    if "generated_charts" not in st.session_state:
        st.session_state.generated_charts = {}
    
    # Chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # MCP connection status
    if "mcp_connected" not in st.session_state:
        st.session_state.mcp_connected = False
    
    # Current page tracking
    if "current_page" not in st.session_state:
        st.session_state.current_page = "Data_Analysis"

def cleanup_session():
    """Clean up temporary files and session data."""
    try:
        # Clean up temporary directory
        if "temp_dir" in st.session_state:
            temp_path = Path(st.session_state.temp_dir)
            if temp_path.exists():
                shutil.rmtree(temp_path, ignore_errors=True)
        
        # Clear session state
        for key in ["uploaded_files", "loaded_dataframes", "generated_charts"]:
            if key in st.session_state:
                st.session_state[key].clear()
                
    except Exception as e:
        st.error(f"Error during cleanup: {e}")

def add_uploaded_file(file_name: str, file_path: str, file_size: int):
    """Add uploaded file to session tracking."""
    st.session_state.uploaded_files[file_name] = {
        "path": file_path,
        "size": file_size,
        "uploaded_at": st.session_state.get("timestamp", ""),
        "dataframe_loaded": False
    }

def remove_uploaded_file(file_name: str):
    """Remove uploaded file from session and filesystem."""
    if file_name in st.session_state.uploaded_files:
        file_info = st.session_state.uploaded_files[file_name]
        file_path = Path(file_info["path"])
        
        # Remove from filesystem
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            st.error(f"Error removing file: {e}")
        
        # Remove from session
        del st.session_state.uploaded_files[file_name]
        
        # Remove associated DataFrame if loaded
        if file_name in st.session_state.loaded_dataframes:
            del st.session_state.loaded_dataframes[file_name]

def add_chat_message(role: str, content: str, metadata: Optional[Dict] = None):
    """Add message to chat history."""
    message = {
        "role": role,
        "content": content,
        "metadata": metadata or {},
        "timestamp": st.session_state.get("timestamp", "")
    }
    st.session_state.chat_history.append(message)

def clear_chat_history():
    """Clear all chat messages."""
    st.session_state.chat_history.clear()

def get_temp_file_path(filename: str) -> str:
    """Get temporary file path for uploaded file."""
    temp_dir = Path(st.session_state.temp_dir)
    return str(temp_dir / filename)

def register_dataframe(df_name: str, df_info: Dict[str, Any]):
    """Register a loaded DataFrame in session state."""
    st.session_state.loaded_dataframes[df_name] = df_info

def get_file_summary() -> Dict[str, Any]:
    """Get summary of current session files and data."""
    return {
        "uploaded_files": len(st.session_state.uploaded_files),
        "loaded_dataframes": len(st.session_state.loaded_dataframes),
        "generated_charts": len(st.session_state.generated_charts),
        "chat_messages": len(st.session_state.chat_history),
        "temp_dir_size": _get_directory_size(st.session_state.get("temp_dir", ""))
    }

def _get_directory_size(path: str) -> int:
    """Calculate total size of directory in bytes."""
    try:
        total_size = 0
        path_obj = Path(path)
        if path_obj.exists():
            for file_path in path_obj.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        return total_size
    except Exception:
        return 0

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

def cleanup_on_session_end():
    """Register cleanup function to run when session ends."""
    if "cleanup_registered" not in st.session_state:
        import atexit
        from utils.temp_storage import temp_manager
        atexit.register(temp_manager.cleanup)
        st.session_state.cleanup_registered = True