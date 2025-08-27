"""Chart display component for rendering Chart.js visualizations."""

import streamlit as st
from typing import Dict, Any, List, Optional
from components.mcp_client import ensure_mcp_connection, run_async_task
from config.settings import settings

class ChartDisplay:
    """Handles chart creation and display using Chart.js from MCP server."""
    
    def __init__(self):
        self.chart_types = [
            "bar", "line", "pie", "doughnut", "scatter", "bubble", "radar", "polarArea"
        ]
    
    def render_chart_builder(self):
        """Render interactive chart builder interface."""
        st.subheader("📊 Chart Builder")
        
        # Check if we have loaded DataFrames
        if not st.session_state.loaded_dataframes:
            st.info("📂 Please load some data first to create charts")
            return
        
        # DataFrame selection
        df_names = list(st.session_state.loaded_dataframes.keys())
        selected_df = st.selectbox("Select DataFrame", df_names, key="chart_df_select")
        
        if not selected_df:
            return
        
        # Get DataFrame info for column selection
        df_info = st.session_state.loaded_dataframes[selected_df]
        columns = list(df_info.get("dtypes", {}).keys())
        
        # Chart type selection
        col1, col2 = st.columns(2)
        
        with col1:
            chart_type = st.selectbox("Chart Type", self.chart_types, key="chart_type_select")
        
        with col2:
            chart_title = st.text_input("Chart Title", 
                                      value=f"{chart_type.title()} Chart - {selected_df}",
                                      key="chart_title_input")
        
        # Column selection based on chart type
        self._render_column_selection(chart_type, columns)
        
        # Chart options
        with st.expander("⚙️ Chart Options", expanded=False):
            self._render_chart_options()
        
        # Create chart button
        if st.button("🎨 Create Chart", type="primary", key="create_chart_btn"):
            self._create_chart(selected_df, chart_type, chart_title)
    
    def _render_column_selection(self, chart_type: str, columns: List[str]):
        """Render column selection based on chart type."""
        if chart_type in ["bar", "line"]:
            col1, col2 = st.columns(2)
            with col1:
                st.selectbox("X-Axis Column", columns, key="x_column")
            with col2:
                st.multiselect("Y-Axis Columns", columns, key="y_columns")
        
        elif chart_type in ["pie", "doughnut"]:
            col1, col2 = st.columns(2)
            with col1:
                st.selectbox("Label Column", columns, key="label_column")
            with col2:
                st.selectbox("Value Column", columns, key="value_column")
        
        elif chart_type in ["scatter", "bubble"]:
            col1, col2 = st.columns(2)
            with col1:
                st.selectbox("X-Axis Column", columns, key="x_column")
            with col2:
                st.selectbox("Y-Axis Column", columns, key="y_column")
            
            if chart_type == "bubble":
                st.selectbox("Size Column", columns, key="size_column")
        
        else:  # radar, polarArea
            st.multiselect("Data Columns", columns, key="data_columns")
    
    def _render_chart_options(self):
        """Render chart customization options."""
        col1, col2 = st.columns(2)
        
        with col1:
            st.number_input("Chart Width", 
                          min_value=400, max_value=1200, 
                          value=settings.CHART_WIDTH, 
                          key="chart_width")
            
            st.checkbox("Show Legend", value=True, key="show_legend")
            
            st.selectbox("Color Scheme", 
                        ["default", "blues", "greens", "reds", "purples", "rainbow"],
                        key="color_scheme")
        
        with col2:
            st.number_input("Chart Height", 
                          min_value=300, max_value=800, 
                          value=settings.CHART_HEIGHT, 
                          key="chart_height")
            
            st.checkbox("Show Grid", value=True, key="show_grid")
            
            st.checkbox("Enable Animation", value=True, key="enable_animation")
    
    def _create_chart(self, df_name: str, chart_type: str, title: str):
        """Create chart using MCP server."""
        try:
            # Build chart configuration
            chart_config = self._build_chart_config(df_name, chart_type, title)
            
            if not chart_config:
                st.error("❌ Invalid chart configuration")
                return
            
            client = ensure_mcp_connection()
            
            with st.spinner("Creating chart..."):
                result = run_async_task(client.create_chart(chart_config))
            
            if result and result.get("success"):
                chart_html = result.get("chart_html", "")
                
                if chart_html:
                    st.markdown(f"### {title}")
                    st.components.v1.html(
                        chart_html, 
                        height=st.session_state.get("chart_height", settings.CHART_HEIGHT)
                    )
                    
                    # Store chart
                    chart_id = f"{chart_type}_{df_name}_{len(st.session_state.generated_charts)}"
                    st.session_state.generated_charts[chart_id] = {
                        "html": chart_html,
                        "type": chart_type,
                        "df_name": df_name,
                        "title": title,
                        "config": chart_config,
                        "created_at": st.session_state.get("timestamp", "")
                    }
                    
                    st.success("✅ Chart created successfully!")
                else:
                    st.error("❌ No chart data received")
            else:
                error_msg = result.get("error", "Unknown error") if result else "No response"
                st.error(f"❌ Failed to create chart: {error_msg}")
                
        except Exception as e:
            st.error(f"Error creating chart: {e}")
    
    def _build_chart_config(self, df_name: str, chart_type: str, title: str) -> Optional[Dict[str, Any]]:
        """Build chart configuration from user inputs."""
        config = {
            "dataframe_name": df_name,
            "chart_type": chart_type,
            "title": title,
            "width": st.session_state.get("chart_width", settings.CHART_WIDTH),
            "height": st.session_state.get("chart_height", settings.CHART_HEIGHT),
            "options": {
                "legend": st.session_state.get("show_legend", True),
                "grid": st.session_state.get("show_grid", True),
                "animation": st.session_state.get("enable_animation", True)
            }
        }
        
        # Add chart-specific configuration
        if chart_type in ["bar", "line"]:
            x_col = st.session_state.get("x_column")
            y_cols = st.session_state.get("y_columns")
            if not x_col or not y_cols:
                st.error("Please select X and Y columns")
                return None
            config.update({"x_column": x_col, "y_columns": y_cols})
        
        elif chart_type in ["pie", "doughnut"]:
            label_col = st.session_state.get("label_column")
            value_col = st.session_state.get("value_column")
            if not label_col or not value_col:
                st.error("Please select label and value columns")
                return None
            config.update({"label_column": label_col, "value_column": value_col})
        
        elif chart_type in ["scatter", "bubble"]:
            x_col = st.session_state.get("x_column")
            y_col = st.session_state.get("y_column")
            if not x_col or not y_col:
                st.error("Please select X and Y columns")
                return None
            config.update({"x_column": x_col, "y_column": y_col})
            
            if chart_type == "bubble":
                size_col = st.session_state.get("size_column")
                if size_col:
                    config["size_column"] = size_col
        
        else:  # radar, polarArea
            data_cols = st.session_state.get("data_columns")
            if not data_cols:
                st.error("Please select data columns")
                return None
            config["data_columns"] = data_cols
        
        # Add color scheme
        color_scheme = st.session_state.get("color_scheme", "default")
        if color_scheme != "default":
            config["color_scheme"] = color_scheme
        
        return config
    
    def render_generated_charts(self):
        """Render all generated charts."""
        if not st.session_state.generated_charts:
            st.info("📊 No charts generated yet")
            return
        
        st.subheader("🎨 Generated Charts")
        
        for chart_id, chart_info in st.session_state.generated_charts.items():
            with st.expander(f"📈 {chart_info.get('title', chart_id)}", expanded=True):
                
                # Chart metadata
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.caption(f"**Type:** {chart_info.get('type', 'Unknown')}")
                with col2:
                    st.caption(f"**DataFrame:** {chart_info.get('df_name', 'Unknown')}")
                with col3:
                    if st.button("🗑️ Remove", key=f"remove_chart_{chart_id}"):
                        del st.session_state.generated_charts[chart_id]
                        st.rerun()
                
                # Display chart
                chart_html = chart_info.get("html", "")
                if chart_html:
                    st.components.v1.html(chart_html, height=600)
                else:
                    st.error("Chart data not available")
    def _create_correlation_heatmap(self, df_name: str):
        """Create correlation heatmap for DataFrame."""
        try:
            client = ensure_mcp_connection()
            result = run_async_task(client.create_correlation_heatmap(df_name))
            
            if result and result.get("success"):
                chart_html = result.get("chart_html", "")
                if chart_html:
                    st.markdown("### 🔥 Correlation Heatmap")
                    st.components.v1.html(chart_html, height=600)
                    
                    # Store chart in session
                    chart_id = f"corr_{df_name}"
                    st.session_state.generated_charts[chart_id] = {
                        "html": chart_html,
                        "type": "correlation_heatmap",
                        "df_name": df_name,
                        "title": f"Correlation Heatmap - {df_name}",
                        "created_at": st.session_state.get("timestamp", "")
                    }
                    st.success("✅ Heatmap created successfully!")
            else:
                st.error("Failed to create correlation heatmap")
                
        except Exception as e:
            st.error(f"Error creating heatmap: {e}")

    def _create_suggested_chart(self, df_name: str, chart_config: Dict[str, Any]):
        """Create chart from suggestion configuration."""
        try:
            self._create_chart(df_name, chart_config.get("type", "bar"), chart_config.get("title", "Chart"))
        except Exception as e:
            st.error(f"Error creating suggested chart: {e}")
    
    def render_quick_visualizations(self, df_name: str):
        """Render quick visualization options for a specific DataFrame."""
        st.markdown(f"### 🚀 Quick Visualizations - {df_name}")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📊 Auto Bar Chart", key=f"auto_bar_{df_name}"):
                self._create_auto_chart(df_name, "bar")
        
        with col2:
            if st.button("📈 Auto Line Chart", key=f"auto_line_{df_name}"):
                self._create_auto_chart(df_name, "line")
        
        with col3:
            if st.button("🔥 Correlation Heatmap", key=f"auto_corr_{df_name}"):
                self._create_correlation_heatmap(df_name)
    
    def _create_auto_chart(self, df_name: str, chart_type: str):
        """Create automatic chart with smart defaults."""
        try:
            client = ensure_mcp_connection()
            
            # Get chart suggestions first
            suggestions_result = run_async_task(client.suggest_charts(df_name))
            
            if suggestions_result and suggestions_result.get("success"):
                suggestions = suggestions_result.get("suggestions", [])
                
                # Find matching chart type suggestion
                matching_suggestion = None
                for suggestion in suggestions:
                    if suggestion.get("type") == chart_type:
                        matching_suggestion = suggestion
                        break
                
                if matching_suggestion and matching_suggestion.get("config"):
                    self._create_suggested_chart(df_name, matching_suggestion["config"])
                else:
                    st.warning(f"No automatic {chart_type} chart available for this data")
            else:
                st.error("Failed to get chart suggestions")
                
        except Exception as e:
            st.error(f"Error creating automatic chart: {e}")

# Global instance
chart_display = ChartDisplay()