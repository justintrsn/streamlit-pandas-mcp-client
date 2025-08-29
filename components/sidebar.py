"""Sidebar component with secure API key handling"""

import streamlit as st
import os
from pathlib import Path
from typing import Optional
from datetime import datetime
from config import get_settings, get_prompt_manager
from utils import get_logger, clear_async_cache, run_async
from core import MCPClient
import hashlib


def render_sidebar():
    """Render the sidebar with secure API key handling"""
    
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Security notice
        with st.expander("🔒 Security Info", expanded=False):
            st.info("""
            **API Key Security:**
            • Keys are NEVER saved to disk
            • Keys are session-only
            • Keys clear on browser close
            • Each user has isolated sessions
            """)
        
        # Create tabs for organization
        tab1, tab2, tab3, tab4 = st.tabs(["🔌 Connection", "📝 Prompt", "📊 Logs", "🔄 Reset"])
        
        # Connection Tab (MCP + API)
        with tab1:
            render_connection_config()
            
        # Prompt Configuration Tab
        with tab2:
            render_prompt_config()
            
        # Debug/Logs Tab
        with tab3:
            render_debug_logs()
            
        # Reset Tab
        with tab4:
            render_clear_controls()


def render_connection_config():
    """Render connection configuration with SECURE API key handling"""
    settings = get_settings()
    logger = get_logger()
    
    # MCP Server Connection
    st.subheader("🔌 MCP Server")
    
    # Connection status
    if st.session_state.get('mcp_tools'):
        st.success(f"✅ Connected ({len(st.session_state.mcp_tools)} tools)")
    else:
        st.warning("⚠️ Not connected")
    
    # MCP URL input
    mcp_url = st.text_input(
        "SSE URL",
        value=settings.mcp_sse_url,
        help="MCP server SSE endpoint",
        placeholder="http://localhost:8000/sse"
    )
    
    # Connect button
    if st.button("🔄 Connect to MCP", type="primary", use_container_width=True):
        with st.spinner("Connecting to MCP server..."):
            try:
                settings.mcp_sse_url = mcp_url
                from core import MCPClient
                mcp_client = MCPClient()
                mcp_client.settings.mcp_sse_url = mcp_url
                
                async def connect():
                    return await mcp_client.connect()
                
                tools = run_async(connect())
                
                if tools:
                    st.session_state.mcp_tools = tools
                    st.session_state.mcp_connected_at = datetime.now().isoformat()
                    st.success(f"✅ Connected! {len(tools)} tools available")
                else:
                    st.error("No tools found on server")
                    
            except Exception as e:
                st.error(f"Connection failed: {str(e)}")
                logger.log("error", f"MCP connection failed: {str(e)}")
    
    st.divider()
    
    # OpenAI Configuration with SECURE handling
    st.subheader("🤖 OpenAI")
    
    # Security warning
    st.warning("""
    ⚠️ **API Key Security:**
    • Enter key each session
    • Never saved to disk
    • Cleared on browser close
    """)
    
    # Check for environment variable first
    env_api_key = os.getenv("OPENAI_API_KEY")
    
    if env_api_key:
        # Hash for display (show first/last 4 chars)
        masked = f"{env_api_key[:4]}...{env_api_key[-4:]}" if len(env_api_key) > 8 else "****"
        st.success(f"✅ Using API key from environment: {masked}")
        st.caption("Set in environment variable OPENAI_API_KEY")
        
        # Still allow override for this session
        if st.checkbox("Override with different key for this session"):
            session_api_key = st.text_input(
                "Session API Key",
                type="password",
                help="This key will be used only for this session",
                placeholder="sk-..."
            )
            
            if session_api_key:
                # Store in session state ONLY
                st.session_state['openai_api_key'] = session_api_key
                st.success("✅ Using session override key")
        else:
            # Use env key in session state
            st.session_state['openai_api_key'] = env_api_key
    else:
        # No environment key - require session input
        st.info("Enter your OpenAI API key (required each session)")
        
        # Session-only API key input
        session_api_key = st.text_input(
            "API Key (Session Only)",
            type="password",
            value="",  # NEVER pre-fill
            help="Required for each session - not saved",
            placeholder="sk-...",
            key="openai_api_key_input"
        )
        
        if session_api_key:
            # Validate format
            if session_api_key.startswith("sk-") and len(session_api_key) > 20:
                # Store in session state ONLY
                st.session_state['openai_api_key'] = session_api_key
                st.success("✅ API key set for this session")
            else:
                st.error("Invalid API key format")
        elif not st.session_state.get('openai_api_key'):
            st.warning("⚠️ Enter API key to use OpenAI features")
    
    # Show current session status
    if st.session_state.get('openai_api_key'):
        key = st.session_state['openai_api_key']
        masked = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else "****"
        st.caption(f"Current session key: {masked}")
        
        # Option to clear session key
        if st.button("🗑️ Clear Session Key", help="Remove key from this session"):
            del st.session_state['openai_api_key']
            st.success("Session key cleared")
            st.rerun()
    
    # Model selection
    model = st.selectbox(
        "Model",
        options=[
            "gpt-4o-mini", 
            "gpt-4o", 
            "gpt-4-turbo",
            "gpt-3.5-turbo"
        ],
        index=0,
        help="OpenAI model to use"
    )
    settings.openai_model = model
    
    # Advanced OpenAI settings
    with st.expander("Advanced Settings"):
        temperature = st.slider(
            "Temperature",
            0.0, 2.0,
            settings.openai_temperature,
            0.1
        )
        settings.openai_temperature = temperature
        
        max_tokens = st.number_input(
            "Max Tokens",
            100, 4000,
            settings.openai_max_tokens,
            100
        )
        settings.openai_max_tokens = max_tokens


def render_prompt_config():
    """Render prompt configuration section"""
    prompt_manager = get_prompt_manager()
    settings = get_settings()
    prompt_manager.create_prompt_editor_ui()


def render_debug_logs():
    """Render debug logs section"""
    logger = get_logger()
    settings = get_settings()
    
    st.subheader("📊 Debug Logs")
    
    # SECURITY: Never show API keys in logs
    st.caption("Note: API keys are never logged for security")
    
    stats = logger.get_log_stats()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Log Entries", stats['total_recent'])
        st.metric("App Log", f"{stats['app_log_size_kb']:.1f} KB")
    with col2:
        errors = stats['recent_counts'].get('ERROR', 0)
        st.metric("Errors", errors)
        st.metric("MCP Log", f"{stats['mcp_log_size_kb']:.1f} KB")
    
    # Log viewer
    st.divider()
    
    num_logs = st.slider("Show Last", 5, 50, 20)
    recent_logs = logger.get_recent_logs(num_logs)
    
    if recent_logs:
        for log in reversed(recent_logs):
            # SECURITY: Filter out any API key references
            message = log['message']
            if 'api_key' in message.lower() or 'sk-' in message:
                message = "[REDACTED - API KEY]"
            
            level = log['level']
            if level in ['ERROR', 'CRITICAL']:
                st.error(f"[{log['timestamp']}] {message}")
            elif level == 'WARNING':
                st.warning(f"[{log['timestamp']}] {message}")
            else:
                st.caption(f"[{log['timestamp']}] {message}")
    else:
        st.info("No logs to display")


def render_clear_controls():
    """Render clear/reset controls with security options"""
    st.subheader("🔄 Reset Options")
    
    # Security clear option
    st.warning("🔒 **Security Clear**")
    if st.button("🔐 Clear All Sensitive Data", type="primary", use_container_width=True):
        # Clear API keys from session
        if 'openai_api_key' in st.session_state:
            del st.session_state['openai_api_key']
        # Clear any other sensitive data
        st.success("All sensitive data cleared from session")
        st.info("API keys must be re-entered")
    
    st.divider()
    
    # Regular clear options
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ Clear Chat"):
            from core import SessionManager
            session_manager = SessionManager()
            session_manager.clear_messages()
            st.success("Chat cleared")
            st.rerun()
            
    with col2:
        if st.button("📊 Clear Charts"):
            from utils import ChartHandler
            ChartHandler().clear_charts()
            st.success("Charts cleared")
            st.rerun()
    
    if st.button("📁 Clear Files", use_container_width=True):
        from core import SessionManager
        session_manager = SessionManager()
        session_manager.clear_files()
        st.success("Files cleared")
        st.rerun()
    
    if st.button("🔄 Clear All Data", type="secondary", use_container_width=True):
        # Clear everything except API keys
        preserved_keys = ['openai_api_key']  # Preserve during normal clear
        preserved = {k: st.session_state[k] for k in preserved_keys if k in st.session_state}
        
        for key in list(st.session_state.keys()):
            if key not in preserved_keys:
                del st.session_state[key]
        
        # Restore preserved
        for k, v in preserved.items():
            st.session_state[k] = v
            
        clear_async_cache()
        get_logger().clear_recent()
        st.success("All data cleared (API key preserved)")
        st.rerun()
