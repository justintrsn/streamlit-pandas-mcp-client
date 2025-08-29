"""Session management for pandas-chat-app"""

import streamlit as st
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

# Safe imports for Streamlit Cloud
try:
    from config import get_settings
    from utils import get_logger, ChartHandler
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config import get_settings
    from utils import get_logger, ChartHandler


class SessionManager:
    """Manage Streamlit session state and data persistence"""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger()
        self.chart_handler = ChartHandler()
        self._initialize_session()
    
    def _initialize_session(self):
        """Initialize session state with default values"""
        if "session_id" not in st.session_state:
            st.session_state["session_id"] = str(uuid.uuid4())
        
        defaults = {
            "messages": [],
            "uploaded_files": {},
            "files_content": {},
            "mcp_tools": None,
            "mcp_connected_at": None,
            "tool_logs": [],
            "generated_charts": [],
            "openai_api_key": "",
            "use_custom_prompt": False,
            "current_chart_index": None,
            "chart_display_settings": {"height": 500, "show_inline": True, "expand_by_default": True},
            "async_cache": {},
            "async_timings": []
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        return st.session_state.get(key, default)
    
    def set(self, key: str, value: Any):
        st.session_state[key] = value
    
    def update(self, updates: Dict[str, Any]):
        for key, value in updates.items():
            st.session_state[key] = value
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a message to the conversation"""
        if "messages" not in st.session_state:
            st.session_state["messages"] = []
        
        message = {"role": role, "content": content, "timestamp": datetime.now().isoformat()}
        if metadata:
            message.update(metadata)
        
        st.session_state["messages"].append(message)
        
        limit = 50
        if self.settings:
            try:
                limit = self.settings.message_history_limit
            except:
                pass
        
        if len(st.session_state["messages"]) > limit:
            st.session_state["messages"] = st.session_state["messages"][-limit:]
        
        if self.logger:
            self.logger.log("info", f"{role.title()} message added")
    
    def add_file(self, filename: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add an uploaded file to session"""
        if "uploaded_files" not in st.session_state:
            st.session_state["uploaded_files"] = {}
        if "files_content" not in st.session_state:
            st.session_state["files_content"] = {}
        
        file_info = {"size": len(content) if content else 0, "upload_time": datetime.now().isoformat()}
        if metadata:
            file_info.update(metadata)
        
        st.session_state["uploaded_files"][filename] = file_info
        st.session_state["files_content"][filename] = content
        
        if self.logger:
            self.logger.log_file_operation("upload", filename, len(content), success=True)
    
    def remove_file(self, filename: str):
        """Remove a file from session"""
        if "uploaded_files" in st.session_state and filename in st.session_state["uploaded_files"]:
            del st.session_state["uploaded_files"][filename]
        if "files_content" in st.session_state and filename in st.session_state["files_content"]:
            del st.session_state["files_content"][filename]
        
        if self.logger:
            self.logger.log_file_operation("remove", filename, success=True)
    
    def get_files(self) -> Dict[str, str]:
        return st.session_state.get("files_content", {})
    
    def get_messages(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get conversation messages"""
        messages = st.session_state.get("messages", [])
        if limit and limit > 0:
            return messages[-limit:]
        return messages
    
    def set_tools(self, tools: List[Dict[str, Any]]):
        st.session_state["mcp_tools"] = tools
        st.session_state["mcp_connected_at"] = datetime.now().isoformat()
    
    def get_tools(self) -> Optional[List[Dict[str, Any]]]:
        return st.session_state.get("mcp_tools")
    
    def is_connected(self) -> bool:
        return bool(st.session_state.get("mcp_tools"))
    
    def clear_messages(self):
        st.session_state["messages"] = []
        if self.logger:
            self.logger.log("info", "Messages cleared")
    
    def clear_files(self):
        count = len(st.session_state.get("uploaded_files", {}))
        st.session_state["uploaded_files"] = {}
        st.session_state["files_content"] = {}
        if self.logger:
            self.logger.log("info", f"Cleared {count} files")
    
    def clear_charts(self):
        count = len(st.session_state.get("generated_charts", []))
        st.session_state["generated_charts"] = []
        st.session_state["current_chart_index"] = None
        if self.logger:
            self.logger.log("info", f"Cleared {count} charts")
    
    def clear_all(self, keep_connection: bool = True):
        preserved = {}
        if keep_connection:
            if "mcp_tools" in st.session_state:
                preserved["mcp_tools"] = st.session_state["mcp_tools"]
            if "mcp_connected_at" in st.session_state:
                preserved["mcp_connected_at"] = st.session_state["mcp_connected_at"]
        
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        for key, value in preserved.items():
            st.session_state[key] = value
        
        self._initialize_session()
        
        if self.logger:
            self.logger.log("info", f"Session cleared")
    
    def export_session(self) -> Dict[str, Any]:
        session_id = st.session_state.get("session_id", "unknown")
        session_id_short = str(session_id)[:8] if session_id and session_id != "unknown" else "unknown"
        
        return {
            "session_id": session_id_short,
            "messages": st.session_state.get("messages", []),
            "uploaded_files": list(st.session_state.get("uploaded_files", {}).keys()),
            "charts_count": len(st.session_state.get("generated_charts", [])),
            "tools_count": len(st.session_state.get("mcp_tools", [])) if st.session_state.get("mcp_tools") else 0,
            "connected": self.is_connected(),
            "timestamp": datetime.now().isoformat()
        }
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "messages": len(st.session_state.get("messages", [])),
            "files": len(st.session_state.get("uploaded_files", {})),
            "charts": len(st.session_state.get("generated_charts", [])),
            "tools": len(st.session_state.get("mcp_tools", [])) if st.session_state.get("mcp_tools") else 0,
            "tool_calls": len(st.session_state.get("tool_logs", [])),
            "cache_size": len(st.session_state.get("async_cache", {})),
            "memory_kb": self._estimate_memory_usage() / 1024
        }
    
    def _estimate_memory_usage(self) -> int:
        total = 0
        try:
            for content in st.session_state.get("files_content", {}).values():
                if isinstance(content, (str, bytes)):
                    total += len(content)
            for chart in st.session_state.get("generated_charts", []):
                if "html" in chart and isinstance(chart["html"], str):
                    total += len(chart["html"])
            for message in st.session_state.get("messages", []):
                content = message.get("content", "")
                if isinstance(content, str):
                    total += len(content)
        except:
            pass
        return total
    
    def validate_state(self) -> tuple[bool, List[str]]:
        errors = []
        if not st.session_state.get("openai_api_key"):
            errors.append("OpenAI API key not set")
        if not self.is_connected():
            errors.append("MCP server not connected")
        
        files = st.session_state.get("uploaded_files", {})
        contents = st.session_state.get("files_content", {})
        
        for filename in files:
            if filename not in contents:
                errors.append(f"File content missing for {filename}")
        
        for filename in contents:
            if filename not in files:
                errors.append(f"File info missing for {filename}")
        
        return len(errors) == 0, errors
