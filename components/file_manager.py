"""File management component for uploading and managing data files."""

import streamlit as st
from typing import List, Dict, Any, Optional
from pathlib import Path
import pandas as pd
from utils.temp_storage import temp_manager
from components.mcp_client import run_async_task
from utils.security import sanitize_filename
from components.mcp_client import mcp_client, ensure_mcp_connection
from config.settings import settings

class FileManager:
    """Handles file upload, preview, and management operations."""
    
    def __init__(self):
        self.allowed_types = settings.ALLOWED_FILE_TYPES
        self.max_size_mb = settings.MAX_FILE_SIZE_MB
    
    def render_file_uploader(self):
        """Render the file upload interface."""
        st.subheader("📁 File Upload")
        
        # File uploader
        uploaded_files = st.file_uploader(
            "Choose data files",
            type=self.allowed_types,
            accept_multiple_files=True,
            help=f"Supported formats: {', '.join(self.allowed_types)}. Max size: {self.max_size_mb}MB per file."
        )
        
        if uploaded_files:
            for uploaded_file in uploaded_files:
                self._process_uploaded_file(uploaded_file)
    
    def _process_uploaded_file(self, uploaded_file):
        """Process a single uploaded file."""
        file_name = sanitize_filename(uploaded_file.name)
        file_size = len(uploaded_file.getvalue())
        
        # Check file size
        if file_size > self.max_size_mb * 1024 * 1024:
            st.error(f"❌ File {file_name} is too large ({file_size / (1024*1024):.1f}MB). Max size: {self.max_size_mb}MB")
            return
        
        # Check if already uploaded
        if file_name in st.session_state.uploaded_files:
            st.warning(f"⚠️ File {file_name} already uploaded")
            return
        
        # Save file temporarily
        with st.spinner(f"Uploading {file_name}..."):
            file_info = temp_manager.save_uploaded_file(uploaded_file, file_name)
            
            if file_info:
                # Add to session state
                st.session_state.uploaded_files[file_name] = file_info
                st.success(f"✅ {file_name} uploaded successfully ({self._format_size(file_size)})")
                
                # Auto-upload to MCP server
                self._upload_to_mcp_server(file_name, file_info["path"])
    
    def _upload_to_mcp_server(self, file_name: str, file_path: str):
        """Upload file to MCP server."""
        try:
            client = ensure_mcp_connection()
            result = run_async_task(client.upload_file(file_path, file_name))
            
            if result and result.get("success"):
                st.success(f"📤 {file_name} uploaded to MCP server")
                # Update file info
                st.session_state.uploaded_files[file_name]["mcp_uploaded"] = True
            else:
                st.error(f"❌ Failed to upload {file_name} to MCP server")
                
        except Exception as e:
            st.error(f"Error uploading to MCP server: {e}")
    
    def render_file_list(self):
        """Render list of uploaded files with management options."""
        if not st.session_state.uploaded_files:
            st.info("📂 No files uploaded yet")
            return
        
        st.subheader("📋 Uploaded Files")
        
        for file_name, file_info in st.session_state.uploaded_files.items():
            with st.expander(f"📄 {file_name}", expanded=False):
                self._render_file_details(file_name, file_info)
    
    def _render_file_details(self, file_name: str, file_info: Dict[str, Any]):
        """Render detailed file information and actions."""
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown(f"""
            **File:** {file_info.get('original_name', file_name)}  
            **Type:** {file_info.get('type', 'Unknown')}  
            **Size:** {self._format_size(file_info.get('size', 0))}  
            **Status:** {'✅ Loaded to MCP' if file_info.get('mcp_uploaded') else '⏳ Local only'}
            """)
        
        with col2:
            # Action buttons
            if st.button("🔍 Preview", key=f"preview_{file_name}"):
                self._preview_file(file_name)
            
            if st.button("📊 Load Data", key=f"load_{file_name}"):
                self._load_dataframe(file_name)
            
            if st.button("🗑️ Delete", key=f"delete_{file_name}"):
                self._delete_file(file_name)
    
    def _preview_file(self, file_name: str):
        """Preview file contents."""
        try:
            client = ensure_mcp_connection()
            result = run_async_task(client.preview_file(file_name, rows=10))
            
            if result and result.get("success"):
                preview_data = result.get("preview", {})
                
                st.markdown("### 👀 File Preview")
                
                # Show metadata
                metadata = preview_data.get("metadata", {})
                if metadata:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Rows", metadata.get("rows", "N/A"))
                    with col2:
                        st.metric("Columns", metadata.get("columns", "N/A"))
                    with col3:
                        st.metric("File Size", self._format_size(metadata.get("size_bytes", 0)))
                
                # Show sample data
                sample_data = preview_data.get("sample", [])
                if sample_data:
                    st.markdown("**Sample Data:**")
                    df_preview = pd.DataFrame(sample_data)
                    st.dataframe(df_preview, use_container_width=True)
                
            else:
                st.error("Failed to preview file")
                
        except Exception as e:
            st.error(f"Error previewing file: {e}")
    
    def _load_dataframe(self, file_name: str):
        """Load file as DataFrame in MCP server."""
        try:
            client = ensure_mcp_connection()
            
            with st.spinner(f"Loading {file_name} as DataFrame..."):
                result = run_async_task(client.load_dataframe(file_name))
            
            if result and result.get("success"):
                df_info = result.get("dataframe_info", {})
                st.success(f"✅ DataFrame loaded: {df_info.get('shape', 'Unknown shape')}")
                
                # Store DataFrame info in session
                st.session_state.loaded_dataframes[file_name] = df_info
                st.session_state.uploaded_files[file_name]["dataframe_loaded"] = True
                
                # Show basic info
                if df_info:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Rows", df_info.get("rows", 0))
                    with col2:
                        st.metric("Columns", df_info.get("columns", 0))
                    with col3:
                        st.metric("Memory Usage", df_info.get("memory_usage", "N/A"))
                
            else:
                st.error("Failed to load DataFrame")
                
        except Exception as e:
            st.error(f"Error loading DataFrame: {e}")
    
    def _delete_file(self, file_name: str):
        """Delete file from both local and MCP server."""
        try:
            # Remove from local storage
            file_info = st.session_state.uploaded_files.get(file_name)
            if file_info:
                temp_manager.delete_file(file_info["path"])
            
            # Remove from session state
            if file_name in st.session_state.uploaded_files:
                del st.session_state.uploaded_files[file_name]
            
            if file_name in st.session_state.loaded_dataframes:
                del st.session_state.loaded_dataframes[file_name]
            
            st.success(f"🗑️ {file_name} deleted successfully")
            st.rerun()
            
        except Exception as e:
            st.error(f"Error deleting file: {e}")
    
    def render_dataframe_list(self):
        """Render list of loaded DataFrames."""
        if not st.session_state.loaded_dataframes:
            st.info("📊 No DataFrames loaded yet")
            return
        
        st.subheader("📊 Loaded DataFrames")
        
        for df_name, df_info in st.session_state.loaded_dataframes.items():
            with st.expander(f"📈 DataFrame: {df_name}", expanded=False):
                self._render_dataframe_details(df_name, df_info)
    
    def _render_dataframe_details(self, df_name: str, df_info: Dict[str, Any]):
        """Render DataFrame details and operations."""
        # Basic info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Shape", f"{df_info.get('rows', 0)} × {df_info.get('columns', 0)}")
        with col2:
            st.metric("Memory", df_info.get("memory_usage", "N/A"))
        with col3:
            st.metric("Data Types", len(df_info.get("dtypes", {})))
        
        # Column information
        if "dtypes" in df_info:
            st.markdown("**Columns:**")
            columns_data = []
            for col, dtype in df_info["dtypes"].items():
                columns_data.append({"Column": col, "Data Type": dtype})
            
            if columns_data:
                st.dataframe(pd.DataFrame(columns_data), use_container_width=True)
        
        # Action buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📊 Suggest Charts", key=f"suggest_{df_name}"):
                self._get_chart_suggestions(df_name)
        
        with col2:
            if st.button("🔗 Correlation", key=f"corr_{df_name}"):
                self._create_correlation_heatmap(df_name)
        
        with col3:
            if st.button("ℹ️ Info", key=f"info_{df_name}"):
                self._show_detailed_info(df_name)
    
    def _get_chart_suggestions(self, df_name: str):
        """Get chart suggestions for DataFrame."""
        try:
            client = ensure_mcp_connection()
            result = run_async_task(client.suggest_charts(df_name))
            
            if result and result.get("success"):
                suggestions = result.get("suggestions", [])
                st.markdown("### 💡 Chart Suggestions")
                
                for suggestion in suggestions:
                    st.markdown(f"**{suggestion.get('type', 'Chart')}:** {suggestion.get('description', 'No description')}")
                    
                    if suggestion.get("config"):
                        if st.button(f"Create {suggestion.get('type', 'Chart')}", 
                                   key=f"create_{df_name}_{suggestion.get('type')}"):
                            self._create_suggested_chart(df_name, suggestion["config"])
            else:
                st.error("Failed to get chart suggestions")
                
        except Exception as e:
            st.error(f"Error getting suggestions: {e}")
    
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
                        "df_name": df_name
                    }
            else:
                st.error("Failed to create correlation heatmap")
                
        except Exception as e:
            st.error(f"Error creating heatmap: {e}")
    
    def _create_suggested_chart(self, df_name: str, chart_config: Dict[str, Any]):
        """Create chart from suggestion."""
        try:
            client = ensure_mcp_connection()
            result = run_async_task(client.create_chart(chart_config))
            
            if result and result.get("success"):
                chart_html = result.get("chart_html", "")
                if chart_html:
                    st.markdown(f"### 📊 {chart_config.get('type', 'Chart')}")
                    st.components.v1.html(chart_html, height=600)
                    
                    # Store chart
                    chart_id = f"{chart_config.get('type', 'chart')}_{df_name}"
                    st.session_state.generated_charts[chart_id] = {
                        "html": chart_html,
                        "type": chart_config.get('type'),
                        "df_name": df_name,
                        "config": chart_config
                    }
            else:
                st.error("Failed to create chart")
                
        except Exception as e:
            st.error(f"Error creating chart: {e}")
    
    def _show_detailed_info(self, df_name: str):
        """Show detailed DataFrame information."""
        try:
            client = ensure_mcp_connection()
            result = run_async_task(client.get_dataframe_info(df_name))
            
            if result and result.get("success"):
                info = result.get("info", {})
                
                st.markdown("### ℹ️ Detailed Information")
                
                # Display comprehensive info
                if "describe" in info:
                    st.markdown("**Statistical Summary:**")
                    describe_df = pd.DataFrame(info["describe"]).T
                    st.dataframe(describe_df, use_container_width=True)
                
                if "missing_values" in info:
                    missing = info["missing_values"]
                    if any(missing.values()):
                        st.markdown("**Missing Values:**")
                        missing_df = pd.DataFrame(list(missing.items()), 
                                                columns=["Column", "Missing Count"])
                        st.dataframe(missing_df, use_container_width=True)
                
                if "data_types" in info:
                    st.markdown("**Data Types:**")
                    types_df = pd.DataFrame(list(info["data_types"].items()), 
                                          columns=["Column", "Type"])
                    st.dataframe(types_df, use_container_width=True)
                    
            else:
                st.error("Failed to get DataFrame info")
                
        except Exception as e:
            st.error(f"Error getting DataFrame info: {e}")
    
    def render_session_summary(self):
        """Render summary of current session."""
        st.subheader("📈 Session Summary")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Files Uploaded", len(st.session_state.uploaded_files))
        
        with col2:
            st.metric("DataFrames Loaded", len(st.session_state.loaded_dataframes))
        
        with col3:
            st.metric("Charts Generated", len(st.session_state.generated_charts))
        
        with col4:
            storage_info = temp_manager.get_storage_usage()
            st.metric("Storage Used", storage_info.get("formatted_size", "0 B"))
        
        # Clear session button
        if st.button("🧹 Clear All Data", type="secondary"):
            if st.confirm("Are you sure you want to clear all data? This cannot be undone."):
                self._clear_all_data()
    
    def _clear_all_data(self):
        """Clear all session data."""
        try:
            # Clear MCP server session
            client = ensure_mcp_connection()
            run_async_task(client.clear_session())
            
            # Clear local session
            st.session_state.uploaded_files.clear()
            st.session_state.loaded_dataframes.clear()
            st.session_state.generated_charts.clear()
            
            # Clean up temp files
            temp_manager.cleanup()
            
            st.success("🧹 All data cleared successfully")
            st.rerun()
            
        except Exception as e:
            st.error(f"Error clearing data: {e}")
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

# Global instance
file_manager = FileManager()