"""Chat Agent page for the MCP Client application."""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from utils.session_state import initialize_session_state
from utils.security import check_api_key_status, secure_api_key_input
from components.mcp_client import display_connection_status
from components.chat_interface import chat_interface

def main():
    """Main function for chat agent page."""
    st.set_page_config(
        page_title="Chat Agent - MCP Client",
        page_icon="💬",
        layout="wide"
    )
    
    # Initialize session state
    initialize_session_state()
    
    # Header
    st.title("💬 Data Analysis Assistant")
    st.markdown("*Chat with an AI agent about your data and analysis tasks*")
    
    # Status check
    col1, col2 = st.columns(2)
    
    with col1:
        api_configured = check_api_key_status()
        if api_configured:
            st.success("🤖 AI Assistant Ready")
        else:
            st.error("🔑 API Key Required")
    
    with col2:
        mcp_connected = st.session_state.get("mcp_connected", False)
        if mcp_connected:
            st.success("🔗 Data Server Connected")
        else:
            st.warning("🔗 Limited functionality without MCP server")
    
    st.divider()
    
    # Main content
    if not api_configured:
        st.markdown("### 🔐 Configuration Required")
        st.info("Please configure your OpenAI API key to start chatting with the AI assistant.")
        
        # Inline API key setup
        with st.expander("🔑 Configure API Key", expanded=True):
            secure_api_key_input()
        
        return
    
    # Chat interface
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Main chat interface
        chat_interface.render_chat_interface()
    
    with col2:
        # Chat sidebar with context and help
        st.markdown("### 📊 Data Context")
        
        if st.session_state.uploaded_files:
            st.markdown("**Files:**")
            for file_name in st.session_state.uploaded_files:
                st.markdown(f"- 📄 {file_name}")
        
        if st.session_state.loaded_dataframes:
            st.markdown("**DataFrames:**")
            for df_name, df_info in st.session_state.loaded_dataframes.items():
                rows = df_info.get("rows", 0)
                cols = df_info.get("columns", 0)
                st.markdown(f"- 📊 {df_name} ({rows}×{cols})")
        
        if st.session_state.generated_charts:
            st.markdown("**Charts:**")
            for chart_id, chart_info in st.session_state.generated_charts.items():
                chart_type = chart_info.get("type", "chart")
                st.markdown(f"- 📈 {chart_type}")
        
        if not any([st.session_state.uploaded_files, 
                   st.session_state.loaded_dataframes, 
                   st.session_state.generated_charts]):
            st.info("📂 Upload some data to get started!")
        
        st.divider()
        
        # MCP Server status
        st.markdown("### 🔗 Server Status")
        display_connection_status()
        
        st.divider()
        
        # Example questions
        st.markdown("### 💡 Example Questions")
        
        examples = [
            "What columns are in my data?",
            "Show me data summary",
            "Create a chart",
            "Find correlations",
            "Check for missing values",
            "Suggest analysis steps"
        ]
        
        for example in examples:
            if st.button(example, key=f"example_{hash(example)}", use_container_width=True):
                # Add example to chat
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": example,
                    "metadata": {},
                    "timestamp": st.session_state.get("timestamp", "")
                })
                st.rerun()

if __name__ == "__main__":
    main()