"""Session management with secure API key handling"""

import streamlit as st
from typing import Dict, Any, List, Optional
from datetime import datetime
from config import get_settings
from utils import get_logger, ChartHandler
import hashlib
import uuid


class SessionManager:
    """Manage Streamlit session state with security isolation"""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger()
        self.chart_handler = ChartHandler()
        self._initialize_session()
        self._ensure_session_id()
    
    def _ensure_session_id(self):
        """Ensure each session has a unique ID for isolation"""
        if 'session_id' not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())
            self.logger.log("info", f"New session created: {st.session_state.session_id[:8]}...")
    
    def _initialize_session(self):
        """Initialize session state with secure defaults"""
        
        defaults = {
            'messages': [],
            'uploaded_files': {},
            'files_content': {},
            'mcp_tools': None,
            'mcp_connected_at': None,
            'tool_logs': [],
            'generated_charts': [],
            # SECURITY: API key is NOT initialized from settings
            # It must be explicitly set each session
            'use_custom_prompt': self.settings.use_custom_prompt,
            'current_chart_index': None,
            'chart_display_settings': {
                'height': self.settings.chart_height,
                'show_inline': True,
                'expand_by_default': self.settings.chart_expand_default
            },
            'async_cache': {},
            'async_timings': [],
            'session_id': None  # Unique session identifier
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from session state"""
        # SECURITY: Special handling for API keys
        if 'api_key' in key.lower():
            # Only return from session state, never from settings
            return st.session_state.get(key, default)
        return st.session_state.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set value in session state with security checks"""
        # SECURITY: Log warning for API key storage attempts
        if 'api_key' in key.lower():
            self.logger.log("warning", f"API key stored in session (key: {key[:20]}...)")
            # Store in session but never persist
        st.session_state[key] = value
    
    def get_api_key(self) -> Optional[str]:
        """Securely get API key from session only"""
        # SECURITY: Only from session state, never from settings/disk
        return st.session_state.get('openai_api_key')
    
    def set_api_key(self, api_key: str):
        """Securely set API key for this session only"""
        if api_key and api_key.startswith("sk-"):
            st.session_state['openai_api_key'] = api_key
            # Log that key was set (but not the key itself)
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:8]
            self.logger.log("info", f"API key set for session (hash: {key_hash})")
            return True
        return False
    
    def clear_api_key(self):
        """Clear API key from session"""
        if 'openai_api_key' in st.session_state:
            del st.session_state['openai_api_key']
            self.logger.log("info", "API key cleared from session")
    
    def clear_sensitive_data(self):
        """Clear all sensitive data from session"""
        sensitive_keys = [
            'openai_api_key',
            'api_key',
            'secret',
            'token',
            'password'
        ]
        
        cleared = []
        for key in list(st.session_state.keys()):
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                del st.session_state[key]
                cleared.append(key)
        
        if cleared:
            self.logger.log("info", f"Cleared sensitive data: {len(cleared)} items")
        
        return cleared
    
    def is_authenticated(self) -> bool:
        """Check if session has valid API key"""
        api_key = self.get_api_key()
        return bool(api_key and api_key.startswith("sk-") and len(api_key) > 20)
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get session information (excluding sensitive data)"""
        return {
            'session_id': st.session_state.get('session_id', 'unknown')[:8],
            'authenticated': self.is_authenticated(),
            'messages': len(st.session_state.get('messages', [])),
            'files': len(st.session_state.get('uploaded_files', {})),
            'charts': len(st.session_state.get('generated_charts', [])),
            'mcp_connected': self.is_connected(),
            'timestamp': datetime.now().isoformat()
        }
    
    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None):
        """Add a message to the conversation"""
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "session_id": st.session_state.get('session_id', 'unknown')[:8]
        }
        
        if metadata:
            # SECURITY: Filter out any API keys from metadata
            filtered_metadata = {
                k: v for k, v in metadata.items() 
                if 'api_key' not in k.lower() and 'secret' not in k.lower()
            }
            message.update(filtered_metadata)
        
        st.session_state.messages.append(message)
        
        # Trim if exceeding limit
        if len(st.session_state.messages) > self.settings.message_history_limit:
            st.session_state.messages = st.session_state.messages[-self.settings.message_history_limit:]
        
        self.logger.log("info", f"{role.title()} message added: {content[:50]}...")
    
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
    
    def get_files(self) -> Dict[str, str]:
        """Get all uploaded file contents"""
        return st.session_state.get('files_content', {})
    
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
    
    def clear_all(self, keep_connection: bool = True, keep_auth: bool = False):
        """Clear all session data with options"""
        
        # Items to preserve
        preserved = {}
        
        if keep_connection:
            preserved['mcp_tools'] = st.session_state.get('mcp_tools')
            preserved['mcp_connected_at'] = st.session_state.get('mcp_connected_at')
        
        # SECURITY: Only preserve API key if explicitly requested
        if keep_auth and st.session_state.get('openai_api_key'):
            # Log security warning
            self.logger.log("warning", "API key preserved during clear (keep_auth=True)")
            preserved['openai_api_key'] = st.session_state.get('openai_api_key')
        
        # Clear everything
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        # Restore preserved items
        for key, value in preserved.items():
            if value is not None:
                st.session_state[key] = value
        
        # Reinitialize
        self._initialize_session()
        self._ensure_session_id()
        
        self.logger.log("info", f"Session cleared (keep_connection={keep_connection}, keep_auth={keep_auth})")
    
    def export_session(self) -> Dict[str, Any]:
        """Export session data for debugging (excludes sensitive data)"""
        
        return {
            'session_id': st.session_state.get('session_id', 'unknown')[:8],
            'messages': st.session_state.get('messages', []),
            'uploaded_files': list(st.session_state.get('uploaded_files', {}).keys()),
            'charts_count': len(st.session_state.get('generated_charts', [])),
            'tools_count': len(st.session_state.get('mcp_tools', [])) if st.session_state.get('mcp_tools') else 0,
            'connected': self.is_connected(),
            'authenticated': self.is_authenticated(),  # Just boolean, not the key
            'timestamp': datetime.now().isoformat()
        }
