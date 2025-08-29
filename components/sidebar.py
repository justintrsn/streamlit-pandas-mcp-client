"""Sidebar component for pandas-chat-app"""

import streamlit as st
import os
from pathlib import Path
from typing import Optional
from datetime import datetime  # Fix: Move this import to the top
from config import get_settings, get_prompt_manager
from utils import get_logger, clear_async_cache, run_async
from core import MCPClient


def render_sidebar():
    """Render the sidebar with all configuration options"""
    
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Create tabs for organization
        tab1, tab2, tab3, tab4 = st.tabs(["🔌 Connection", "📝 Prompt", "🔍 Logs", "🔄 Reset"])
        
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
    """Render connection configuration (MCP + OpenAI)"""
    settings = get_settings()
    logger = get_logger()
    
    # MCP Server Connection
    st.subheader("🔌 MCP Server")
    
    # Connection status
    if st.session_state.get('mcp_tools'):
        st.success(f"✅ Connected ({len(st.session_state.mcp_tools)} tools)")
        if st.session_state.get('mcp_connected_at'):
            connected_at = datetime.fromisoformat(st.session_state.mcp_connected_at)
            duration = (datetime.now() - connected_at).seconds
            if duration < 60:
                st.caption(f"Connected {duration}s ago")
            elif duration < 3600:
                st.caption(f"Connected {duration//60}m ago")
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
                # Update settings with new URL
                settings.mcp_sse_url = mcp_url
                
                # Connect
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
                    
                    # Show tool categories
                    categories = mcp_client.get_tools_by_category()
                    with st.expander("Available Tools", expanded=False):
                        for category, tool_list in categories.items():
                            st.write(f"**{category}** ({len(tool_list)})")
                            for tool in tool_list[:3]:
                                st.caption(f"  • {tool}")
                            if len(tool_list) > 3:
                                st.caption(f"  ... and {len(tool_list)-3} more")
                else:
                    st.error("No tools found on server")
                    
            except Exception as e:
                st.error(f"Connection failed: {str(e)}")
                logger.log("error", f"MCP connection failed: {str(e)}")
    
    # Advanced MCP settings
    with st.expander("Advanced Settings"):
        timeout = st.number_input(
            "Timeout (seconds)",
            min_value=5,
            max_value=120,
            value=settings.mcp_timeout,
            help="Connection timeout"
        )
        settings.mcp_timeout = timeout
    
    st.divider()
    
    # OpenAI Configuration
    st.subheader("🤖 OpenAI")
    
    # API Key input (always empty by default for security)
    api_key = st.text_input(
        "API Key",
        type="password",
        value=st.session_state.get('openai_api_key', ''),
        help="Your OpenAI API key (sk-...)",
        placeholder="sk-..."
    )
    
    if api_key:
        st.session_state.openai_api_key = api_key
        settings.openai_api_key = api_key
        st.success("✅ API key set")
    else:
        st.warning("⚠️ Enter API key to use OpenAI")
        
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
        
        max_tool_calls = st.number_input(
            "Max Tool Calls",
            1, 20,
            settings.max_tool_calls
        )
        settings.max_tool_calls = max_tool_calls


def render_prompt_config():
    """Render prompt configuration section"""
    prompt_manager = get_prompt_manager()
    settings = get_settings()
    
    # Use the prompt manager's UI
    prompt_manager.create_prompt_editor_ui()
    
    # Show prompt comparison
    with st.expander("📊 Prompt Comparison"):
        comparison = prompt_manager.compare_prompts()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Default Length", f"{comparison['default_length']} chars")
            st.metric("Default Lines", comparison['default_lines'])
        with col2:
            st.metric("Custom Length", f"{comparison['custom_length']} chars")
            st.metric("Custom Lines", comparison['custom_lines'])
            
        if comparison['is_different']:
            st.info(f"Custom prompt differs by {abs(comparison['length_diff'])} characters")
        else:
            st.info("Custom prompt matches default")


def render_debug_logs():
    """Render debug logs section"""
    logger = get_logger()
    settings = get_settings()
    
    st.subheader("🔍 Debug Logs")
    
    # Log statistics
    stats = logger.get_log_stats()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Log Entries", stats['total_recent'])
        st.metric("App Log", f"{stats['app_log_size_kb']:.1f} KB")
    with col2:
        counts = stats['recent_counts']
        errors = counts.get('ERROR', 0) + counts.get('CRITICAL', 0)
        st.metric("Errors", errors)
        st.metric("MCP Log", f"{stats['mcp_log_size_kb']:.1f} KB")
        
    # Log viewer
    st.divider()
    
    # Filter options
    col1, col2 = st.columns(2)
    with col1:
        log_level_filter = st.selectbox(
            "Filter Level",
            options=["ALL", "INFO", "WARNING", "ERROR", "MCP", "CHART"],
            index=0
        )
    with col2:
        num_logs = st.slider("Show Last", 5, 50, 20)
        
    # Display logs
    level_filter = None if log_level_filter == "ALL" else log_level_filter
    recent_logs = logger.get_recent_logs(num_logs, level_filter)
    
    if recent_logs:
        for log in reversed(recent_logs):
            # Color code by level
            level = log['level']
            if level in ['ERROR', 'CRITICAL']:
                st.error(f"[{log['timestamp']}] {log['message']}")
            elif level == 'WARNING':
                st.warning(f"[{log['timestamp']}] {log['message']}")
            elif level == 'MCP':
                st.info(f"[{log['timestamp']}] 🔧 {log['message']}")
            elif level == 'CHART':
                st.success(f"[{log['timestamp']}] 📊 {log['message']}")
            else:
                st.caption(f"[{log['timestamp']}] {log['message']}")
    else:
        st.info("No logs to display")
        
    # Tool execution history from session state
    if st.session_state.get('tool_logs'):
        st.divider()
        st.caption("Recent Tool Calls:")
        for log in st.session_state.tool_logs[-5:]:
            with st.expander(f"{log['timestamp']} - {log['tool']}"):
                st.json(log)
                
    # Clear logs button
    if st.button("🗑️ Clear Logs"):
        logger.clear_recent()
        st.session_state.tool_logs = []
        st.success("Logs cleared")


def render_clear_controls():
    """Render clear/reset controls"""
    st.subheader("🔄 Reset Options")
    
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
            
    if st.button("🔄 Clear All Data", type="primary", use_container_width=True):
        # Clear everything except connection
        for key in list(st.session_state.keys()):
            if key not in ['openai_api_key', 'mcp_tools', 'mcp_connected_at']:
                del st.session_state[key]
        clear_async_cache()
        get_logger().clear_recent()
        st.success("All data cleared")
        st.rerun()
        
    # Dangerous zone
    with st.expander("⚠️ Danger Zone"):
        st.warning("This will reset everything including settings and connections")
        if st.button("🔴 Factory Reset", type="secondary", use_container_width=True):
            # Clear all session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            # Reset settings
            from config import reset_settings
            reset_settings()
            # Clear cache
            clear_async_cache()
            st.success("Factory reset complete")
            st.rerun()