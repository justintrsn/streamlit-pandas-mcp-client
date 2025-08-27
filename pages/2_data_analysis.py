"""Data Analysis page for the MCP Client application."""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from utils.session_state import initialize_session_state
from utils.security import check_api_key_status
from components.mcp_client import display_connection_status, test_mcp_connection
from components.file_manager import file_manager
from components.chart_display import chart_display
from config.settings import settings

def main():
    """Main function for data analysis page."""
    st.set_page_config(
        page_title="Data Analysis - MCP Client",
        page_icon="📊",
        layout="wide"
    )
    
    # Initialize session state
    initialize_session_state()
    
    # Header
    st.title("📊 Data Analysis Dashboard")
    st.markdown("*Upload data, create visualizations, and analyze your datasets*")
    
    # Status indicators
    col1, col2 = st.columns(2)
    
    with col1:
        if check_api_key_status():
            st.success("🔑 OpenAI API configured")
        else:
            st.warning("🔑 API key needed for enhanced features")
    
    with col2:
        if st.session_state.get("mcp_connected", False):
            st.success("🔗 MCP server connected")
        else:
            st.error("🔗 MCP server not connected")
    
    st.divider()
    
    # Main content - with proper connection handling
    if not st.session_state.get("mcp_connected", False):
        st.error("⚠️ Please connect to the MCP server to continue")
        
        # Import the proper connection function
        from components.mcp_client import establish_mcp_connection, display_connection_status
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🔗 Connect to Server", type="primary", key="connect_main"):
                with st.spinner("Establishing connection..."):
                    if establish_mcp_connection():
                        st.success("✅ Connected successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Connection failed")
        
        with col2:
            if st.button("🔄 Refresh Page", key="refresh_main"):
                st.rerun()
        
        # Show connection status widget
        st.divider()
        display_connection_status()
        return
    
    # Content tabs (rest of the function remains the same)
    tab1, tab2, tab3, tab4 = st.tabs(["📤 Upload", "📊 Visualize", "📋 DataFrames", "⚡ Quick Actions"])
    
    with tab1:
        st.markdown("### 📁 Upload Your Data Files")
        file_manager.render_file_uploader()
        
        if st.session_state.uploaded_files:
            st.divider()
            st.markdown("### 📂 Uploaded Files")
            file_manager.render_file_list()
    
    with tab2:
        st.markdown("### 🎨 Create Visualizations")
        chart_display.render_chart_builder()
        
        if st.session_state.generated_charts:
            st.divider()
            chart_display.render_generated_charts()
    
    with tab3:
        st.markdown("### 📊 Manage DataFrames")
        file_manager.render_dataframe_list()
    
    with tab4:
        st.markdown("### ⚡ Quick Actions")
        
        if st.session_state.loaded_dataframes:
            # Quick visualization options
            df_names = list(st.session_state.loaded_dataframes.keys())
            selected_df = st.selectbox("Select DataFrame for quick actions:", df_names)
            
            if selected_df:
                chart_display.render_quick_visualizations(selected_df)
        else:
            st.info("📂 Upload and load data first to use quick actions")
        
        st.divider()
        
        # Session management
        file_manager.render_session_summary()

if __name__ == "__main__":
    main()