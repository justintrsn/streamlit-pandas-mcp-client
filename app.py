#!/usr/bin/env python3
"""
Pandas Data Chat - Streamlit app with MCP integration
"""

import streamlit as st
from pathlib import Path

# Import configuration
from config import get_settings, get_prompt_manager

# Import core modules
from core import MCPClient, OpenAIHandler, SessionManager

# Import components
from components import (
    render_sidebar,
    render_chat_interface,
    render_file_manager,
    render_connection_status
)

# Import utilities
from utils import get_logger, ChartHandler, run_async

# Initialize settings and logger
settings = get_settings()
logger = get_logger()

# Page configuration
st.set_page_config(
    page_title=settings.app_title,
    page_icon=settings.app_icon,
    layout=settings.app_layout,
    initial_sidebar_state=settings.sidebar_state
)

# Initialize core modules
@st.cache_resource
def init_core_modules():
    """Initialize core modules (cached across reruns)"""
    mcp_client = MCPClient()
    openai_handler = OpenAIHandler(mcp_client)
    return mcp_client, openai_handler

mcp_client, openai_handler = init_core_modules()
session_manager = SessionManager()
chart_handler = ChartHandler()

# Main app
def main():
    """Main application entry point"""
    
    # Title
    st.title(f"{settings.app_icon} {settings.app_title}")
    
    # Top bar with connection status
    render_connection_status()
    
    # Connect to MCP if not connected
    if not session_manager.is_connected() and not st.session_state.get('mcp_tools'):
        if st.button("Connect to MCP Server", type="primary"):
            with st.spinner("Connecting..."):
                try:
                    tools = run_async(mcp_client.connect())
                    session_manager.set_tools(tools)
                    st.success(f"Connected! {len(tools)} tools available.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Connection failed: {str(e)}")
                    logger.log("error", f"MCP connection failed: {str(e)}")
    
    # Main layout
    col1, col2 = st.columns([2, 1])
    
    # Chat interface (left column)
    with col1:
        is_ready = render_chat_interface()
    
    # File manager (right column)
    with col2:
        render_file_manager()
    
    # Sidebar
    render_sidebar()
    
    # Display current chart if selected
    if session_manager.get('current_chart_index') is not None:
        with col1:
            chart_handler.display_current_chart()
    
    # Chat input (must be at root level due to Streamlit constraints)
    if prompt := st.chat_input("Ask about your data...", disabled=not is_ready):
        handle_user_input(prompt, col1)


def handle_user_input(prompt: str, display_column):
    """Handle user input and process with OpenAI/MCP"""
    
    # Validate state
    if not session_manager.get('openai_api_key'):
        st.error("Please enter your OpenAI API key in the sidebar.")
        return
        
    if not session_manager.is_connected():
        st.error("Please connect to MCP server first.")
        return
    
    # Add user message
    session_manager.add_message("user", prompt)
    
    # Display user message
    with display_column:
        with st.chat_message("user"):
            st.write(prompt)
    
    # Process with OpenAI
    with display_column:
        with st.chat_message("assistant"):
            process_assistant_response(prompt)


def process_assistant_response(user_prompt: str):
    """Process and display assistant response"""
    
    # Initialize OpenAI if needed
    api_key = session_manager.get('openai_api_key')
    if not api_key:
        st.error("OpenAI API key not found")
        return
        
    openai_handler.initialize(api_key)
    
    # Prepare messages
    file_contents = session_manager.get_files()
    messages = openai_handler.prepare_messages(user_prompt, file_contents)
    
    # Get tools
    tools = session_manager.get_tools()
    if not tools:
        st.error("No MCP tools available")
        return
    
    try:
        # Process with OpenAI
        response, chart_indices = openai_handler.process_message(
            messages,
            tools,
            file_contents
        )
        
        # Display response
        st.write(response)
        
        # Add to session
        session_manager.add_message(
            "assistant",
            response,
            {"chart_indices": chart_indices} if chart_indices else None
        )
        
    except Exception as e:
        error_msg = f"Error processing request: {str(e)}"
        st.error(error_msg)
        logger.log("error", error_msg)
        
        # Add error to session
        session_manager.add_message("assistant", f"I encountered an error: {str(e)}")


if __name__ == "__main__":
    main()