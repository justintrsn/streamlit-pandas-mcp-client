"""
File Management Page
"""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_settings
from components import render_file_manager, render_sidebar
from core import SessionManager

# Initialize
settings = get_settings()
session_manager = SessionManager()

# Page config
st.set_page_config(
    page_title="Files - " + settings.app_title,
    page_icon="📁",
    layout=settings.app_layout
)

def main():
    st.title("📁 File Management")
    
    # Sidebar
    render_sidebar()
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### Upload and manage your data files
        
        Upload CSV, Excel, JSON, or Parquet files to analyze with natural language queries.
        
        **Workflow:**
        1. Upload files here
        2. Go to Chat page to analyze
        3. View generated charts in Charts page
        """)
        
        # File manager
        render_file_manager()
    
    with col2:
        # File statistics
        files = session_manager.get('uploaded_files', {})
        
        if files:
            st.metric("Total Files", len(files))
            
            total_size = sum(f.get('size', 0) for f in files.values())
            st.metric("Total Size", f"{total_size / (1024*1024):.2f} MB")
            
            st.divider()
            
            # Quick actions
            st.subheader("Quick Actions")
            
            # Use navigation buttons instead of switch_page
            if st.button("💬 Go to Chat", type="primary", use_container_width=True):
                st.markdown('<meta http-equiv="refresh" content="0; url=/">', unsafe_allow_html=True)
                
            if st.button("📈 View Charts", use_container_width=True):
                st.markdown('<meta http-equiv="refresh" content="0; url=/2_📊_Charts">', unsafe_allow_html=True)
                
            if st.button("🗑️ Clear All Files", use_container_width=True):
                session_manager.clear_files()
                st.rerun()
        else:
            st.info("No files uploaded yet")
            st.caption("Upload files to get started with data analysis")

if __name__ == "__main__":
    main()