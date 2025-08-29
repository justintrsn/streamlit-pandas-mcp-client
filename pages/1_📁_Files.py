"""
Charts Gallery Page
"""

import streamlit as st
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

# Add custom CSS to make sidebar page names bigger
st.markdown("""
<style>
    /* Make sidebar page links bigger and bolder */
    [data-testid="stSidebarNav"] li div a {
        font-size: 20px !important;
        font-weight: 600 !important;
        padding: 0.75rem 1rem !important;
        margin: 0.25rem 0 !important;
    }
    
    /* Make the current page highlighted better */
    [data-testid="stSidebarNav"] li div a[aria-selected="true"] {
        background-color: rgba(255, 75, 75, 0.1);
        border-left: 4px solid #FF4B4B;
        font-weight: 700 !important;
    }
    
    /* Increase spacing between pages */
    [data-testid="stSidebarNav"] li {
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

def main():
    st.title("📊 Charts Gallery")
    
    # Sidebar
    render_sidebar()
    
    # Chart gallery
    charts = st.session_state.get('generated_charts', [])
    
    if not charts:
        st.info("No charts generated yet")
        st.markdown("""
        ### How to create charts:
        1. Upload data files in the [Files page](../Files)
        2. Go to [Chat page](../app.py) and ask questions like:
           - "Create a bar chart of top categories"
           - "Show correlation heatmap"
           - "Plot time series of sales"
        3. Charts will appear here automatically
        """)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📁 Upload Files", type="primary", use_container_width=True):
                st.switch_page("pages/1_📁_Files.py")
        with col2:
            if st.button("💬 Start Chat", use_container_width=True):
                st.switch_page("app.py")
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
        st.session_state.chart_display_settings = {'height': height}
    
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
                import base64
                b64 = base64.b64encode(chart['html'].encode()).decode()
                filename = f"{chart['chart_type']}_{chart['timestamp'].strftime('%Y%m%d_%H%M%S')}.html"
                href = f'<a href="data:text/html;base64,{b64}" download="{filename}"><button>📥 Download</button></a>'
                st.markdown(href, unsafe_allow_html=True)
                
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