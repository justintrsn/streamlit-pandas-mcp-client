"""Chart detection and handling utilities for pandas-chat-app"""

import json
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path
from typing import Dict, Optional, Any, List
from datetime import datetime
import base64
import time


class ChartHandler:
    """Handle chart detection, storage, and display from MCP tool responses"""
    
    def __init__(self):
        # Chart-generating tools to monitor
        self.chart_tools = [
            'create_chart_tool',
            'create_correlation_heatmap_tool',
            'create_time_series_chart_tool'
        ]
        
        # Initialize session state for charts if needed
        self._init_session_state()
        
    def _init_session_state(self):
        """Initialize session state for chart storage"""
        if 'generated_charts' not in st.session_state:
            st.session_state.generated_charts = []
            
        if 'chart_display_settings' not in st.session_state:
            st.session_state.chart_display_settings = {
                'height': 500,
                'show_inline': True,
                'expand_by_default': True
            }
            
    def detect_chart_in_response(
        self,
        tool_name: str,
        result: str
    ) -> Optional[Dict[str, Any]]:
        """
        Detect if the tool response contains a chart.
        
        Args:
            tool_name: Name of the MCP tool
            result: JSON string response from the tool
            
        Returns:
            Chart info dict if chart detected, None otherwise
        """
        if tool_name not in self.chart_tools:
            return None
            
        try:
            result_data = json.loads(result)
            
            # Check for successful chart creation
            if result_data.get('success') and 'filepath' in result_data:
                return {
                    'filepath': result_data['filepath'],
                    'filename': result_data.get('filename', 'chart.html'),
                    'chart_type': result_data.get('chart_type', 'chart'),
                    'dataframe': result_data.get('df_name', 'data'),
                    'metadata': result_data.get('metadata', {}),
                    'tool': tool_name,
                    'timestamp': datetime.now()
                }
        except (json.JSONDecodeError, KeyError):
            pass
            
        return None
        
    def store_chart(
        self,
        chart_info: Dict[str, Any],
        html_content: str
    ) -> int:
        """
        Store chart in session state.
        
        Args:
            chart_info: Chart metadata from detection
            html_content: HTML content of the chart
            
        Returns:
            Index of stored chart
        """
        chart_data = {
            **chart_info,
            'html': html_content,
            'id': f"chart_{int(time.time() * 1000)}",
            'displayed': False
        }
        
        st.session_state.generated_charts.append(chart_data)
        
        # Keep only last 20 charts to manage memory
        if len(st.session_state.generated_charts) > 20:
            st.session_state.generated_charts = st.session_state.generated_charts[-20:]
            
        return len(st.session_state.generated_charts) - 1
        
    def display_chart(
        self,
        html_content: str,
        height: Optional[int] = None,
        key: Optional[str] = None,
        in_expander: bool = False,
        title: Optional[str] = None
    ):
        """
        Display chart in Streamlit.
        
        Args:
            html_content: HTML content to display
            height: Height in pixels
            key: Unique key for component
            in_expander: Whether to wrap in expander
            title: Title for expander if used
        """
        height = height or st.session_state.chart_display_settings['height']
        
        if in_expander:
            title = title or "📊 Chart"
            expanded = st.session_state.chart_display_settings['expand_by_default']
            
            with st.expander(title, expanded=expanded):
                self._render_html_component(html_content, height, key)
                self._add_chart_controls(html_content, title)
        else:
            self._render_html_component(html_content, height, key)
            
    def _render_html_component(
        self,
        html_content: str,
        height: int,
        key: Optional[str] = None
    ):
        """Render HTML using Streamlit components"""
        
        # Ensure responsive design
        html_content = self._prepare_html_for_streamlit(html_content)
        
        # Use iframe component for better isolation
        components.html(
            html_content,
            height=height,
            scrolling=True
        )
        
    def _prepare_html_for_streamlit(self, html_content: str) -> str:
        """Modify HTML to work well in Streamlit iframe"""
        
        # Make chart responsive
        replacements = [
            ('<canvas id="chart"', '<canvas id="chart" style="max-width: 100%; height: auto;"'),
            ('width: 800px', 'width: 100%'),
            ('width: 1000px', 'width: 100%'),
        ]
        
        for old, new in replacements:
            html_content = html_content.replace(old, new)
            
        # Add viewport meta if missing
        if '<meta name="viewport"' not in html_content:
            html_content = html_content.replace(
                '</head>',
                '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n</head>'
            )
            
        return html_content
        
    def _add_chart_controls(self, html_content: str, title: str):
        """Add download and fullscreen controls"""
        
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            # Download button
            b64 = base64.b64encode(html_content.encode()).decode()
            filename = f"{title.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            
            href = f'<a href="data:text/html;base64,{b64}" download="{filename}" style="text-decoration: none;"><button style="padding: 0.25rem 1rem; background-color: #FF4B4B; color: white; border: none; border-radius: 0.25rem; cursor: pointer;">📥 Download</button></a>'
            st.markdown(href, unsafe_allow_html=True)
            
        with col2:
            # Fullscreen button
            if st.button("🔍 Fullscreen", key=f"fs_{title}_{time.time()}"):
                self._show_fullscreen_modal(html_content, title)
                
    def _show_fullscreen_modal(self, html_content: str, title: str):
        """Display chart in fullscreen modal"""
        
        modal = st.container()
        with modal:
            if st.button("✕ Close", key=f"close_{time.time()}"):
                st.rerun()
            st.markdown(f"### {title}")
            components.html(html_content, height=800, scrolling=True)
            
    def render_chart_gallery(self):
        """Render gallery of all generated charts in sidebar"""
        
        if not st.session_state.generated_charts:
            st.info("No charts generated yet")
            return
            
        st.subheader("📊 Chart Gallery")
        
        # Display settings
        with st.expander("Display Settings"):
            st.session_state.chart_display_settings['height'] = st.slider(
                "Chart Height",
                300, 800, 
                st.session_state.chart_display_settings['height'],
                step=50
            )
            st.session_state.chart_display_settings['show_inline'] = st.checkbox(
                "Show charts inline",
                st.session_state.chart_display_settings['show_inline']
            )
            
        # List charts (newest first)
        for idx, chart in enumerate(reversed(st.session_state.generated_charts)):
            time_str = chart['timestamp'].strftime('%H:%M:%S')
            chart_name = f"{chart['chart_type']} - {time_str}"
            
            with st.expander(chart_name, expanded=False):
                # Chart info
                st.caption(f"📊 **Type:** {chart['chart_type']}")
                st.caption(f"📈 **Data:** {chart.get('dataframe', 'N/A')}")
                st.caption(f"🕒 **Created:** {chart['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Metadata if available
                if chart.get('metadata'):
                    st.caption("**Metadata:**")
                    for key, value in chart['metadata'].items():
                        st.caption(f"  • {key}: {value}")
                
                # Action buttons
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("View", key=f"view_{idx}_{chart['id']}"):
                        st.session_state.current_chart_index = len(st.session_state.generated_charts) - idx - 1
                        
                with col2:
                    # Download button
                    b64 = base64.b64encode(chart['html'].encode()).decode()
                    filename = f"{chart['chart_type']}_{chart['timestamp'].strftime('%Y%m%d_%H%M%S')}.html"
                    
                    href = f'<a href="data:text/html;base64,{b64}" download="{filename}">📥 Save</a>'
                    st.markdown(href, unsafe_allow_html=True)
                    
    def display_current_chart(self):
        """Display the currently selected chart in main area"""
        
        if 'current_chart_index' not in st.session_state:
            return False
            
        if not st.session_state.generated_charts:
            return False
            
        idx = st.session_state.current_chart_index
        if idx >= len(st.session_state.generated_charts):
            return False
            
        chart = st.session_state.generated_charts[idx]
        
        # Display with title
        st.markdown(f"### 📊 {chart['chart_type'].title()}")
        st.caption(f"Created: {chart['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} | Data: {chart.get('dataframe', 'N/A')}")
        
        # Render the chart
        self.display_chart(
            chart['html'],
            height=600,
            key=f"main_chart_{chart['id']}"
        )
        
        return True
        
    def clear_charts(self):
        """Clear all stored charts"""
        st.session_state.generated_charts = []
        if 'current_chart_index' in st.session_state:
            del st.session_state.current_chart_index
            
    def get_charts_summary(self) -> Dict[str, Any]:
        """Get summary statistics about generated charts"""
        
        if not st.session_state.generated_charts:
            return {
                'total': 0,
                'types': {},
                'latest': None
            }
            
        charts = st.session_state.generated_charts
        
        # Count by type
        type_counts = {}
        for chart in charts:
            chart_type = chart.get('chart_type', 'unknown')
            type_counts[chart_type] = type_counts.get(chart_type, 0) + 1
            
        return {
            'total': len(charts),
            'types': type_counts,
            'latest': charts[-1]['timestamp'].strftime('%H:%M:%S') if charts else None,
            'memory_kb': sum(len(c['html']) for c in charts) / 1024
        }
        
    def export_all_charts(self) -> Optional[str]:
        """Export all charts as a combined HTML file"""
        
        if not st.session_state.generated_charts:
            return None
            
        # Create combined HTML
        combined_html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Chart Gallery Export</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; }
        .chart-container { margin-bottom: 50px; border-bottom: 2px solid #ccc; padding-bottom: 30px; }
        .chart-header { background: #f0f0f0; padding: 10px; margin-bottom: 20px; }
        h2 { color: #333; }
        .metadata { color: #666; font-size: 0.9em; }
    </style>
</head>
<body>
    <h1>Chart Gallery Export</h1>
    <p>Generated: {timestamp}</p>
    <hr>
""".format(timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        for idx, chart in enumerate(st.session_state.generated_charts, 1):
            chart_section = f"""
    <div class="chart-container">
        <div class="chart-header">
            <h2>Chart {idx}: {chart['chart_type'].title()}</h2>
            <div class="metadata">
                <p>Created: {chart['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>Data: {chart.get('dataframe', 'N/A')}</p>
            </div>
        </div>
        <div class="chart-content">
            {chart['html']}
        </div>
    </div>
"""
            combined_html += chart_section
            
        combined_html += """
</body>
</html>"""
        
        return combined_html