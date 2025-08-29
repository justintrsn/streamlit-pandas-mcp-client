"""
Charts Gallery Page
"""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_settings
from components import render_sidebar
from utils import ChartHandler
from core import SessionManager

# Initialize
settings = get_settings()
session_manager = SessionManager()
chart_handler = ChartHandler()

# Page config
st.set_page_config(
    page_title="Charts - " + settings.app_title,
    page_icon="📊",
    layout=settings.app_layout
)

def main():
    st.title("📊 Charts Gallery")
    
    # Sidebar
    render_sidebar()
    
    # Navigation info
    with st.expander("📍 Navigation Help"):
        st.info("Use the sidebar to navigate between pages: Main Chat, Files, and Charts")
    
    # Chart gallery
    charts = st.session_state.get('generated_charts', [])
    
    if not charts:
        st.info("No charts generated yet")
        st.markdown("""
        ### How to create charts:
        1. **Upload data files** in the Files page (use sidebar to navigate)
        2. **Go to Chat page** and ask questions like:
           - "Create a bar chart of top categories"
           - "Show correlation heatmap"
           - "Plot time series of sales"
        3. Charts will appear here automatically
        """)
        
        # Navigation guidance
        st.divider()
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            #### 📁 Need to upload files?
            Use the **sidebar** to navigate to the **Files** page
            """)
            
        with col2:
            st.markdown("""
            #### 💬 Ready to analyze?
            Use the **sidebar** to navigate to the main **Chat** page
            """)
        
        return
    
    # Chart controls
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.metric("Total Charts", len(charts))
        
    with col2:
        if st.button("📥 Export All", use_container_width=True):
            html_content = chart_handler.export_all_charts()
            if html_content:
                st.download_button(
                    label="Download Gallery HTML",
                    data=html_content,
                    file_name="chart_gallery.html",
                    mime="text/html"
                )
                
    with col3:
        if st.button("🗑️ Clear All", use_container_width=True):
            chart_handler.clear_charts()
            st.rerun()
    
    st.divider()
    
    # Display settings
    with st.expander("Display Settings"):
        height = st.slider(
            "Chart Height",
            300, 800,
            st.session_state.get('chart_display_settings', {}).get('height', 500),
            step=50
        )
        if 'chart_display_settings' not in st.session_state:
            st.session_state.chart_display_settings = {}
        st.session_state.chart_display_settings['height'] = height
    
    # Display charts in grid
    for idx, chart in enumerate(reversed(charts)):
        with st.container():
            # Chart header
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.subheader(f"{chart['chart_type'].title()}")
                st.caption(f"Created: {chart['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
                
            with col2:
                # Download individual chart
                st.download_button(
                    label="📥 Download",
                    data=chart['html'],
                    file_name=f"{chart['chart_type']}_{chart['timestamp'].strftime('%Y%m%d_%H%M%S')}.html",
                    mime="text/html",
                    key=f"download_{idx}"
                )
                
            with col3:
                if st.button("🗑️", key=f"delete_{idx}", help="Delete this chart"):
                    charts.pop(len(charts) - idx - 1)
                    st.rerun()
            
            # Display chart
            chart_handler.display_chart(
                chart['html'],
                height=height,
                key=f"chart_{idx}_{chart.get('id', idx)}"
            )
            
            # Chart metadata
            with st.expander("Chart Details"):
                if 'dataframe' in chart:
                    st.write(f"**Data Source:** {chart['dataframe']}")
                if 'metadata' in chart and chart['metadata']:
                    st.write("**Metadata:**")
                    for key, value in chart['metadata'].items():
                        st.write(f"- {key}: {value}")
            
            st.divider()

if __name__ == "__main__":
    main()
