"""Session management for pandas-chat-app"""

import streamlit as st
from typing import Dict, Any, List, Optional
from datetime import datetime
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
        
        defaults = {
            'messages': [],
            'uploaded_files': {},
            'files_content': {},
            'mcp_tools': None,
            'mcp_connected_at': None,
            'tool_logs': [],
            'generated_charts': [],
            'openai_api_key': self.settings.openai_api_key,
            'use_custom_prompt': self.settings.use_custom_prompt,
            'current_chart_index': None,
            'chart_display_settings': {
                'height': self.settings.chart_height,
                'show_inline': True,
                'expand_by_default': self.settings.chart_expand_default
            },
            'async_cache': {},
            'async_timings': []
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
                
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from session state"""
        return st.session_state.get(key, default)
        
    def set(self, key: str, value: Any):
        """Set value in session state"""
        st.session_state[key] = value
        
    def update(self, updates: Dict[str, Any]):
        """Update multiple values in session state"""
        for key, value in updates.items():
            st.session_state[key] = value
            
    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None):
        """Add a message to the conversation"""
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        if metadata:
            message.update(metadata)
            
        st.session_state.messages.append(message)
        
        # Trim if exceeding limit
        if len(st.session_state.messages) > self.settings.message_history_limit:
            st.session_state.messages = st.session_state.messages[-self.settings.message_history_limit:]
            
        self.logger.log("info", f"{role.title()} message added: {content[:50]}...")
        
    def add_file(self, filename: str, content: str, metadata: Dict[str, Any] = None):
        """Add an uploaded file to session"""
        
        file_info = {
            'size': len(content),
            'upload_time': datetime.now().isoformat()
        }
        
        if metadata:
            file_info.update(metadata)
            
        st.session_state.uploaded_files[filename] = file_info
        st.session_state.files_content[filename] = content
        
        self.logger.log_file_operation("upload", filename, len(content), success=True)
        
    def remove_file(self, filename: str):
        """Remove a file from session"""
        
        if filename in st.session_state.uploaded_files:
            del st.session_state.uploaded_files[filename]
            
        if filename in st.session_state.files_content:
            del st.session_state.files_content[filename]
            
        self.logger.log_file_operation("remove", filename, success=True)
        
    def get_files(self) -> Dict[str, str]:
        """Get all uploaded file contents"""
        return st.session_state.get('files_content', {})
        
    def get_messages(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get conversation messages"""
        messages = st.session_state.get('messages', [])
        
        if limit:
            return messages[-limit:]
        return messages
        
    def set_tools(self, tools: List[Dict[str, Any]]):
        """Set MCP tools in session"""
        st.session_state.mcp_tools = tools
        st.session_state.mcp_connected_at = datetime.now().isoformat()
        
    def get_tools(self) -> Optional[List[Dict[str, Any]]]:
        """Get MCP tools from session"""
        return st.session_state.get('mcp_tools')
        
    def is_connected(self) -> bool:
        """Check if MCP is connected"""
        return bool(st.session_state.get('mcp_tools'))
        
    def clear_messages(self):
        """Clear conversation messages"""
        st.session_state.messages = []
        self.logger.log("info", "Messages cleared")
        
    def clear_files(self):
        """Clear uploaded files"""
        count = len(st.session_state.get('uploaded_files', {}))
        st.session_state.uploaded_files = {}
        st.session_state.files_content = {}
        self.logger.log("info", f"Cleared {count} files")
        
    def clear_charts(self):
        """Clear generated charts"""
        count = len(st.session_state.get('generated_charts', []))
        st.session_state.generated_charts = []
        st.session_state.current_chart_index = None
        self.logger.log("info", f"Cleared {count} charts")
        
    def clear_all(self, keep_connection: bool = True):
        """Clear all session data"""
        
        # Items to preserve if keeping connection
        preserved = {}
        if keep_connection:
            preserved = {
                'mcp_tools': st.session_state.get('mcp_tools'),
                'mcp_connected_at': st.session_state.get('mcp_connected_at'),
                'openai_api_key': st.session_state.get('openai_api_key')
            }
            
        # Clear everything
        for key in list(st.session_state.keys()):
            del st.session_state[key]
            
        # Restore preserved items
        for key, value in preserved.items():
            if value is not None:
                st.session_state[key] = value
                
        # Reinitialize
        self._initialize_session()
        
        self.logger.log("info", f"Session cleared (keep_connection={keep_connection})")
        
    def export_session(self) -> Dict[str, Any]:
        """Export session data for backup/debugging"""
        
        return {
            'messages': st.session_state.get('messages', []),
            'uploaded_files': list(st.session_state.get('uploaded_files', {}).keys()),
            'charts_count': len(st.session_state.get('generated_charts', [])),
            'tools_count': len(st.session_state.get('mcp_tools', [])) if st.session_state.get('mcp_tools') else 0,
            'connected': self.is_connected(),
            'timestamp': datetime.now().isoformat()
        }
        
    def get_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        
        return {
            'messages': len(st.session_state.get('messages', [])),
            'files': len(st.session_state.get('uploaded_files', {})),
            'charts': len(st.session_state.get('generated_charts', [])),
            'tools': len(st.session_state.get('mcp_tools', [])) if st.session_state.get('mcp_tools') else 0,
            'tool_calls': len(st.session_state.get('tool_logs', [])),
            'cache_size': len(st.session_state.get('async_cache', {})),
            'memory_kb': self._estimate_memory_usage() / 1024
        }
        
    def _estimate_memory_usage(self) -> int:
        """Estimate memory usage of session state in bytes"""
        
        total = 0
        
        # Files content
        for content in st.session_state.get('files_content', {}).values():
            total += len(content)
            
        # Charts HTML
        for chart in st.session_state.get('generated_charts', []):
            if 'html' in chart:
                total += len(chart['html'])
                
        # Messages (rough estimate)
        for message in st.session_state.get('messages', []):
            total += len(message.get('content', ''))
            
        return total
        
    def validate_state(self) -> tuple[bool, List[str]]:
        """Validate session state integrity"""
        
        errors = []
        
        # Check API key if needed
        if not st.session_state.get('openai_api_key') and not self.settings.openai_api_key:
            errors.append("OpenAI API key not set")
            
        # Check MCP connection
        if not self.is_connected():
            errors.append("MCP server not connected")
            
        # Check for orphaned files
        files = st.session_state.get('uploaded_files', {})
        contents = st.session_state.get('files_content', {})
        
        for filename in files:
            if filename not in contents:
                errors.append(f"File content missing for {filename}")
                
        for filename in contents:
            if filename not in files:
                errors.append(f"File info missing for {filename}")
                
        return len(errors) == 0, errors