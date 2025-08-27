"""Main Streamlit application for MCP Data Analysis Client."""

import streamlit as st
from streamlit_option_menu import option_menu
import time
from pathlib import Path

# Import our components
from config.settings import settings
from utils.session_state import initialize_session_state, cleanup_on_session_end
from utils.security import secure_api_key_input, display_security_warning, check_api_key_status
from components.mcp_client import display_connection_status, test_mcp_connection
from components.file_manager import file_manager
from components.chart_display import chart_display
from components.chat_interface import chat_interface

def configure_page():
    """Configure Streamlit page settings."""
    st.set_page_config(
        page_title=settings.PAGE_TITLE,
        page_icon=settings.PAGE_ICON,
        layout=settings.LAYOUT,
        initial_sidebar_state="expanded"
    )
    
    # Add custom CSS
    try:
        css_file = settings.STATIC_DIR / "style.css"
        if css_file.exists():
            with open(css_file) as f:
                st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except Exception:
        pass  # CSS is optional

def render_sidebar():
    """Render the application sidebar."""
    with st.sidebar:
        st.title("🎛️ Control Panel")
        
        # API Key Configuration
        secure_api_key_input()
        
        st.divider()
        
        # MCP Server Status - Updated section
        st.markdown("### 🔗 Server Connection")
        
        # Import proper connection functions
        from components.mcp_client import establish_mcp_connection
        
        if st.session_state.get("mcp_connected", False):
            st.success("✅ Connected")
            if st.button("🔄 Reconnect", key="sidebar_reconnect"):
                with st.spinner("Reconnecting..."):
                    if establish_mcp_connection():
                        st.rerun()
        else:
            st.error("❌ Not Connected")
            if st.button("🔗 Connect Now", key="sidebar_connect"):
                with st.spinner("Connecting..."):
                    if establish_mcp_connection():
                        st.success("Connected!")
                        st.rerun()
                    else:
                        st.error("Connection failed")
        
        st.divider()
        
        # Security info
        display_security_warning()

def render_main_navigation():
    """Render main navigation menu."""
    selected = option_menu(
        menu_title=None,
        options=["📊 Data Analysis", "💬 Chat Assistant", "📁 File Manager"],
        icons=["graph-up", "chat-dots", "folder"],
        menu_icon="cast",
        default_index=0,
        orientation="horizontal",
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#ff6b6b", "font-size": "18px"},
            "nav-link": {
                "font-size": "16px",
                "text-align": "center",
                "margin": "0px",
                "--hover-color": "#f0f0f0",
            },
            "nav-link-selected": {"background-color": "#ff6b6b"},
        },
    )
    
    return selected

def render_data_analysis_page():
    """Render the data analysis page."""
    st.title("📊 Data Analysis Dashboard")
    
    # Check prerequisites
    if not check_api_key_status():
        st.warning("🔑 Configure your OpenAI API key in the sidebar to unlock all features")
    
    # Check MCP connection - use establish function instead of just checking
    if not st.session_state.get("mcp_connected", False):
        st.warning("🔗 Connect to MCP server to start analyzing data")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔗 Connect to MCP Server", type="primary"):
                from components.mcp_client import establish_mcp_connection
                with st.spinner("Connecting to MCP server..."):
                    if establish_mcp_connection():
                        st.success("✅ Connected successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Connection failed. Please check if the server is running.")
        with col2:
            if st.button("🔄 Retry Connection"):
                st.rerun()
        return
    
    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["📂 File Upload", "📊 Charts", "📋 DataFrames"])
    
    with tab1:
        file_manager.render_file_uploader()
        st.divider()
        file_manager.render_session_summary()
    
    with tab2:
        chart_display.render_chart_builder()
        st.divider()
        chart_display.render_generated_charts()
    
    with tab3:
        file_manager.render_dataframe_list()
        
        # Quick visualizations for loaded DataFrames
        if st.session_state.loaded_dataframes:
            st.divider()
            df_name = st.selectbox(
                "Quick Visualizations for:", 
                list(st.session_state.loaded_dataframes.keys()),
                key="quick_viz_select"
            )
            if df_name:
                chart_display.render_quick_visualizations(df_name)

def render_chat_page():
    """Render the chat assistant page."""
    st.title("💬 Data Analysis Assistant")
    
    # Check prerequisites
    if not check_api_key_status():
        st.error("🔑 Please configure your OpenAI API key in the sidebar to use the chat feature")
        return
    
    if not st.session_state.get("mcp_connected", False):
        st.warning("🔗 Connect to MCP server for enhanced data operations")
    
    # Main chat interface
    chat_interface.render_chat_interface()
    
    # Suggested questions
    if st.session_state.loaded_dataframes:
        st.divider()
        chat_interface.render_suggested_questions()

def render_file_manager_page():
    """Render the file manager page."""
    st.title("📁 File Management")
    
    if not st.session_state.get("mcp_connected", False):
        st.warning("🔗 Please connect to MCP server first")
        return
    
    # File operations
    tab1, tab2 = st.tabs(["📤 Upload Files", "📋 Manage Files"])
    
    with tab1:
        file_manager.render_file_uploader()
    
    with tab2:
        file_manager.render_file_list()
        
        st.divider()
        
        # Bulk operations
        st.subheader("🔧 Bulk Operations")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📊 Load All as DataFrames", type="secondary"):
                _load_all_dataframes()
        
        with col2:
            if st.button("🧹 Clear All Files", type="secondary"):
                if st.confirm("Delete all uploaded files?"):
                    file_manager._clear_all_data()

def _load_all_dataframes():
    """Load all uploaded files as DataFrames."""
    try:
        for file_name in st.session_state.uploaded_files:
            if not st.session_state.uploaded_files[file_name].get("dataframe_loaded"):
                file_manager._load_dataframe(file_name)
        st.success("✅ All files loaded as DataFrames")
    except Exception as e:
        st.error(f"Error loading DataFrames: {e}")

def main():
    """Main application function."""
    # Configure page
    configure_page()
    
    # Initialize session state
    initialize_session_state()
    
    # Register cleanup
    cleanup_on_session_end()
    
    # Update timestamp for session tracking
    st.session_state.timestamp = time.time()
    
    # Ensure directories exist
    settings.ensure_directories()
    
    # Render sidebar
    render_sidebar()
    
    # Main content
    st.markdown("# 🚀 MCP Data Analysis Client")
    st.markdown("*Powered by Pandas MCP Server & OpenAI*")
    
    # Navigation
    selected_page = render_main_navigation()
    
    st.divider()
    
    # Render selected page
    if "Data Analysis" in selected_page:
        render_data_analysis_page()
    elif "Chat Assistant" in selected_page:
        render_chat_page()
    elif "File Manager" in selected_page:
        render_file_manager_page()

if __name__ == "__main__":
    main()