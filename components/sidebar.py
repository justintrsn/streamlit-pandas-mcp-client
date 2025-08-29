"""Sidebar component for pandas-chat-app"""

import streamlit as st
import os
from pathlib import Path
from typing import Optional
from config import get_settings, get_prompt_manager
from utils import get_logger, ChartHandler, clear_async_cache


def render_sidebar():
    """Render the sidebar with all configuration options"""
    
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Create tabs for organization
        tab1, tab2, tab3, tab4 = st.tabs(["🔑 API", "📝 Prompt", "📊 Charts", "🔍 Logs"])
        
        # API Configuration Tab
        with tab1:
            render_api_config()
            
        # Prompt Configuration Tab
        with tab2:
            render_prompt_config()
            
        # Charts Tab
        with tab3:
            render_charts_gallery()
            
        # Debug/Logs Tab
        with tab4:
            render_debug_logs()
            
        # Bottom section - Clear/Reset
        st.divider()
        render_clear_controls()


def render_api_config():
    """Render API configuration section"""
    settings = get_settings()
    
    st.subheader("OpenAI Configuration")
    
    # API Key input
    api_key = st.text_input(
        "OpenAI API Key",
        type="password",
        value=settings.openai_api_key,
        help="Your OpenAI API key (sk-...)"
    )
    
    if api_key:
        st.session_state.openai_api_key = api_key
        settings.openai_api_key = api_key
        
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
    
    # Advanced settings
    with st.expander("Advanced Settings"):
        # Temperature
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=2.0,
            value=settings.openai_temperature,
            step=0.1,
            help="Controls randomness in responses"
        )
        settings.openai_temperature = temperature
        
        # Max tokens
        max_tokens = st.number_input(
            "Max Tokens",
            min_value=100,
            max_value=4000,
            value=settings.openai_max_tokens,
            step=100,
            help="Maximum response length"
        )
        settings.openai_max_tokens = max_tokens
        
        # Max tool calls
        max_tool_calls = st.number_input(
            "Max Tool Calls",
            min_value=1,
            max_value=20,
            value=settings.max_tool_calls,
            help="Maximum MCP tool calls per request"
        )
        settings.max_tool_calls = max_tool_calls
        
    # MCP Server settings
    st.divider()
    st.subheader("MCP Server")
    
    # Show connection status
    if st.session_state.get('mcp_tools'):
        st.success(f"✅ Connected ({len(st.session_state.mcp_tools)} tools)")
    else:
        st.warning("⚠️ Not connected")
        
    # MCP URL (advanced)
    with st.expander("Server Settings"):
        mcp_url = st.text_input(
            "MCP SSE URL",
            value=settings.mcp_sse_url,
            help="MCP server endpoint"
        )
        settings.mcp_sse_url = mcp_url
        
        timeout = st.number_input(
            "Timeout (seconds)",
            min_value=5,
            max_value=120,
            value=settings.mcp_timeout,
            help="Connection timeout"
        )
        settings.mcp_timeout = timeout
        
        if st.button("💾 Save Settings"):
            settings.save_to_env()
            st.success("Settings saved to .env")


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


def render_charts_gallery():
    """Render charts gallery section"""
    chart_handler = ChartHandler()
    
    st.subheader("📊 Chart Gallery")
    
    # Get summary
    summary = chart_handler.get_charts_summary()
    
    if summary['total'] > 0:
        # Display metrics
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Charts", summary['total'])
        with col2:
            st.metric("Memory", f"{summary['memory_kb']:.1f} KB")
            
        # Chart type breakdown
        if summary['types']:
            st.caption("Chart Types:")
            for chart_type, count in summary['types'].items():
                st.caption(f"  • {chart_type}: {count}")
                
        st.divider()
        
        # Render gallery
        chart_handler.render_chart_gallery()
        
        # Export option
        st.divider()
        if st.button("📥 Export All Charts"):
            html_content = chart_handler.export_all_charts()
            if html_content:
                st.download_button(
                    label="Download Gallery HTML",
                    data=html_content,
                    file_name="chart_gallery.html",
                    mime="text/html"
                )
    else:
        st.info("No charts generated yet")
        st.caption("Charts will appear here after creation")


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
            st.session_state.messages = []
            st.success("Chat cleared")
            st.rerun()
            
    with col2:
        if st.button("📊 Clear Charts"):
            ChartHandler().clear_charts()
            st.success("Charts cleared")
            st.rerun()
            
    if st.button("🔄 Clear All Data", type="primary"):
        # Clear everything
        for key in list(st.session_state.keys()):
            if key not in ['openai_api_key', 'mcp_tools']:  # Keep connection
                del st.session_state[key]
        clear_async_cache()
        get_logger().clear_recent()
        st.success("All data cleared")
        st.rerun()
        
    # Dangerous zone
    with st.expander("⚠️ Danger Zone"):
        st.warning("This will reset everything including settings")
        if st.button("🔴 Factory Reset", type="secondary"):
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