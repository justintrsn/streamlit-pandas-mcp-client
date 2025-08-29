#!/usr/bin/env python3
"""
Pandas Data Chat - Home Page (Main Chat Interface)
"""

import streamlit as st
from pathlib import Path

# Import configuration
from config import get_settings, get_prompt_manager

# Import core modules
from core import MCPClient, OpenAIHandler, SessionManager

# Import components
from components import render_sidebar, render_chat_interface

# Import utilities
from utils import get_logger, ChartHandler, run_async

# Initialize settings and logger
settings = get_settings()
logger = get_logger()

# Page configuration
st.set_page_config(
    page_title="Pandas Data Chat",
    page_icon="🏠",
    layout=settings.app_layout,
    initial_sidebar_state=settings.sidebar_state
)

# Add custom CSS to make sidebar page names bigger
st.markdown("""
<style>
    /* Make sidebar page links bigger */
    .css-w770g5 {
        font-size: 18px !important;
        font-weight: 500 !important;
    }
    
    /* Make the page names in sidebar bigger */
    [data-testid="stSidebarNav"] li div a {
        font-size: 18px !important;
        font-weight: 500 !important;
        padding: 0.75rem 1rem !important;
    }
    
    /* Make the current page highlighted better */
    [data-testid="stSidebarNav"] li div a[aria-selected="true"] {
        background-color: rgba(255, 255, 255, 0.1);
        font-weight: 600 !important;
    }
    
    /* Increase spacing between pages */
    [data-testid="stSidebarNav"] li {
        margin-bottom: 0.5rem;
    }
    
    /* Style the main navigation header */
    [data-testid="stSidebarNav"] {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

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
    """Main chat interface"""
    
    # Title
    st.title(f"🏠 Welcome to {settings.app_title}")
    st.markdown("### Chat with your data using natural language")
    
    # Check connection status
    if not session_manager.is_connected() or not session_manager.get('openai_api_key'):
        with st.container():
            st.info("💡 **Getting Started**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if not session_manager.get('openai_api_key'):
                    st.warning("⚠️ OpenAI API Key Required")
                    st.markdown("Enter your API key in the sidebar →")
                else:
                    st.success("✅ OpenAI Connected")
                    
            with col2:
                if not session_manager.is_connected():
                    st.warning("⚠️ MCP Server Not Connected")
                    st.markdown("Connect in the sidebar →")
                else:
                    st.success("✅ MCP Connected")
                    
            if session_manager.is_connected() and session_manager.get('openai_api_key'):
                st.markdown("---")
                st.markdown("✨ **You're all set!** Upload files in the [Files page](./1_📁_Files) and start chatting!")
    
    # Chat interface
    is_ready = render_chat_interface()
    
    # Sidebar
    render_sidebar()
    
    # Chat input (must be at root level due to Streamlit constraints)
    if prompt := st.chat_input("Ask about your data...", disabled=not is_ready):
        handle_user_input(prompt)


def handle_user_input(prompt: str):
    """Handle user input and process with OpenAI/MCP"""
    
    # Validate state
    if not session_manager.get('openai_api_key'):
        st.error("Please enter your OpenAI API key in the sidebar.")
        return
        
    if not session_manager.is_connected():
        st.error("Please connect to MCP server in the sidebar first.")
        return
        
    # Check if files are uploaded
    files = session_manager.get_files()
    if not files:
        st.warning("💡 Tip: Upload data files in the [Files page](./1_📁_Files) to analyze them")
    
    # Add user message
    session_manager.add_message("user", prompt)
    
    # Display user message
    with st.chat_message("user"):
        st.write(prompt)
    
    # Process with OpenAI
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
        
        # Show link to charts if any were created
        if chart_indices:
            st.success(f"📊 {len(chart_indices)} chart(s) created! View them in the [Charts page](./2_📊_Charts)")
        
    except Exception as e:
        error_msg = f"Error processing request: {str(e)}"
        st.error(error_msg)
        logger.log("error", error_msg)
        
        # Add error to session
        session_manager.add_message("assistant", f"I encountered an error: {str(e)}")


if __name__ == "__main__":
    main()