"""File Manager page for the MCP Client application."""

import streamlit as st
import sys
from pathlib import Path
import pandas as pd
from typing import Dict

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from utils.session_state import initialize_session_state
from utils.temp_storage import temp_manager
from components.mcp_client import display_connection_status, ensure_mcp_connection, run_async_task
from components.file_manager import file_manager
from components.chart_display import chart_display

def main():
    """Main function for file manager page."""
    st.set_page_config(
        page_title="File Manager - MCP Client",
        page_icon="📁",
        layout="wide"
    )
    
    # Initialize session state
    initialize_session_state()
    
    # Header
    st.title("📁 File Management Center")
    st.markdown("*Upload, manage, and preview your data files*")
    
    # Connection status
    if not st.session_state.get("mcp_connected", False):
        st.error("⚠️ MCP server connection required for file operations")
        display_connection_status()
        return
    
    # Main content
    tab1, tab2, tab3, tab4 = st.tabs([
        "📤 Upload Files", 
        "📂 File Browser", 
        "📊 DataFrame Manager", 
        "🔧 Advanced Operations"
    ])
    
    with tab1:
        render_upload_tab()
    
    with tab2:
        render_browser_tab()
    
    with tab3:
        render_dataframe_tab()
    
    with tab4:
        render_advanced_tab()

def render_upload_tab():
    """Render file upload tab."""
    st.markdown("### 📤 Upload Data Files")
    
    # Upload interface
    file_manager.render_file_uploader()
    
    # Upload statistics
    if st.session_state.uploaded_files:
        st.divider()
        
        st.markdown("### 📊 Upload Statistics")
        
        # Calculate stats
        total_size = sum(
            info.get("size", 0) 
            for info in st.session_state.uploaded_files.values()
        )
        
        file_types = {}
        for info in st.session_state.uploaded_files.values():
            file_type = info.get("type", "Unknown")
            file_types[file_type] = file_types.get(file_type, 0) + 1
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Files", len(st.session_state.uploaded_files))
        
        with col2:
            st.metric("Total Size", temp_manager._format_size(total_size))
        
        with col3:
            st.metric("File Types", len(file_types))
        
        # File type breakdown
        if file_types:
            st.markdown("**File Type Distribution:**")
            type_df = pd.DataFrame(
                list(file_types.items()),
                columns=["File Type", "Count"]
            )
            st.dataframe(type_df, use_container_width=True)

def render_browser_tab():
    """Render file browser tab."""
    st.markdown("### 📂 File Browser")
    
    if not st.session_state.uploaded_files:
        st.info("📂 No files uploaded yet")
        return
    
    # File list with detailed view
    for file_name, file_info in st.session_state.uploaded_files.items():
        with st.expander(f"📄 {file_name}", expanded=False):
            
            # File metadata
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"""
                **Original Name:** {file_info.get('original_name', file_name)}  
                **File Type:** {file_info.get('type', 'Unknown')}  
                **Size:** {temp_manager._format_size(file_info.get('size', 0))}  
                **Status:** {'✅ Loaded as DataFrame' if file_info.get('dataframe_loaded') else '📄 File only'}  
                **MCP Status:** {'✅ Uploaded' if file_info.get('mcp_uploaded') else '⏳ Local only'}
                """)
            
            with col2:
                # Action buttons
                if st.button("🔍 Preview", key=f"browser_preview_{file_name}"):
                    _preview_file_detailed(file_name)
                
                if not file_info.get("dataframe_loaded"):
                    if st.button("📊 Load Data", key=f"browser_load_{file_name}"):
                        file_manager._load_dataframe(file_name)
                        st.rerun()
                
                if st.button("🗑️ Delete", key=f"browser_delete_{file_name}"):
                    if st.confirm(f"Delete {file_name}?"):
                        file_manager._delete_file(file_name)

def render_dataframe_tab():
    """Render DataFrame management tab."""
    st.markdown("### 📊 DataFrame Manager")
    
    if not st.session_state.loaded_dataframes:
        st.info("📊 No DataFrames loaded yet")
        
        # Show available files to load
        if st.session_state.uploaded_files:
            st.markdown("**Available Files to Load:**")
            for file_name, file_info in st.session_state.uploaded_files.items():
                if not file_info.get("dataframe_loaded"):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"📄 {file_name} ({file_info.get('type', 'Unknown')})")
                    with col2:
                        if st.button("📊 Load", key=f"df_load_{file_name}"):
                            file_manager._load_dataframe(file_name)
                            st.rerun()
        return
    
    # DataFrame operations
    for df_name, df_info in st.session_state.loaded_dataframes.items():
        with st.expander(f"📊 {df_name}", expanded=True):
            _render_dataframe_operations(df_name, df_info)

def render_advanced_tab():
    """Render advanced operations tab."""
    st.markdown("### 🔧 Advanced File Operations")
    
    # Bulk operations
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🔄 Bulk Actions")
        
        if st.button("📊 Load All as DataFrames", key="bulk_load_all"):
            _bulk_load_dataframes()
        
        if st.button("🔍 Preview All Files", key="bulk_preview"):
            _bulk_preview_files()
        
        if st.button("📈 Create Charts for All", key="bulk_charts"):
            _bulk_create_charts()
    
    with col2:
        st.markdown("#### 🧹 Cleanup Actions")
        
        if st.button("🗑️ Clear Uploaded Files", key="clear_files"):
            if st.confirm("Clear all uploaded files?"):
                _clear_uploaded_files()
        
        if st.button("🧹 Clear DataFrames", key="clear_dataframes"):
            if st.confirm("Clear all DataFrames?"):
                _clear_dataframes()
        
        if st.button("🗑️ Clear Everything", key="clear_everything"):
            if st.confirm("Clear ALL session data? This cannot be undone."):
                file_manager._clear_all_data()
    
    st.divider()
    
    # Server operations
    st.markdown("### 🖥️ Server Operations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("ℹ️ Get Server Session Info", key="server_info"):
            _get_server_session_info()
    
    with col2:
        if st.button("🧹 Clear Server Session", key="clear_server"):
            if st.confirm("Clear server-side session data?"):
                _clear_server_session()

def _preview_file_detailed(file_name: str):
    """Show detailed file preview."""
    try:
        client = ensure_mcp_connection()
        result = run_async_task(client.preview_file(file_name, rows=20))
        
        if result and result.get("success"):
            st.markdown(f"### 👀 Preview: {file_name}")
            
            preview_data = result.get("preview", {})
            
            # Metadata
            metadata = preview_data.get("metadata", {})
            if metadata:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Rows", metadata.get("rows", "N/A"))
                with col2:
                    st.metric("Columns", metadata.get("columns", "N/A"))
                with col3:
                    st.metric("Size", temp_manager._format_size(metadata.get("size_bytes", 0)))
                with col4:
                    st.metric("Type", metadata.get("file_type", "Unknown"))
            
            # Sample data
            sample_data = preview_data.get("sample", [])
            if sample_data:
                st.markdown("**Sample Data (First 20 rows):**")
                df_preview = pd.DataFrame(sample_data)
                st.dataframe(df_preview, use_container_width=True)
            
            # Column info
            columns_info = preview_data.get("columns_info", {})
            if columns_info:
                st.markdown("**Column Information:**")
                col_df = pd.DataFrame([
                    {
                        "Column": col,
                        "Type": info.get("dtype", "Unknown"),
                        "Non-Null": info.get("non_null_count", "N/A"),
                        "Unique": info.get("unique_count", "N/A")
                    }
                    for col, info in columns_info.items()
                ])
                st.dataframe(col_df, use_container_width=True)
        
        else:
            st.error("Failed to preview file")
            
    except Exception as e:
        st.error(f"Error previewing file: {e}")

def _render_dataframe_operations(df_name: str, df_info: Dict):
    """Render operations for a specific DataFrame."""
    # Basic info display
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Rows", df_info.get("rows", 0))
    with col2:
        st.metric("Columns", df_info.get("columns", 0))
    with col3:
        st.metric("Memory", df_info.get("memory_usage", "N/A"))
    with col4:
        st.metric("Types", len(df_info.get("dtypes", {})))
    
    # Operations
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Quick Bar Chart", key=f"quick_bar_{df_name}"):
            chart_display._create_auto_chart(df_name, "bar")
    
    with col2:
        if st.button("📈 Quick Line Chart", key=f"quick_line_{df_name}"):
            chart_display._create_auto_chart(df_name, "line")
    
    with col3:
        if st.button("🔥 Correlation Map", key=f"quick_corr_{df_name}"):
            chart_display._create_correlation_heatmap(df_name)

def _bulk_load_dataframes():
    """Load all uploaded files as DataFrames."""
    success_count = 0
    error_count = 0
    
    with st.spinner("Loading all files as DataFrames..."):
        for file_name, file_info in st.session_state.uploaded_files.items():
            if not file_info.get("dataframe_loaded"):
                try:
                    file_manager._load_dataframe(file_name)
                    success_count += 1
                except Exception:
                    error_count += 1
    
    if success_count > 0:
        st.success(f"✅ Loaded {success_count} DataFrames")
    if error_count > 0:
        st.error(f"❌ Failed to load {error_count} files")

def _bulk_preview_files():
    """Preview all uploaded files."""
    for file_name in st.session_state.uploaded_files:
        with st.expander(f"👀 Preview: {file_name}"):
            _preview_file_detailed(file_name)

def _bulk_create_charts():
    """Create automatic charts for all DataFrames."""
    if not st.session_state.loaded_dataframes:
        st.warning("No DataFrames available for chart creation")
        return
    
    success_count = 0
    
    with st.spinner("Creating charts for all DataFrames..."):
        for df_name in st.session_state.loaded_dataframes:
            try:
                chart_display._create_auto_chart(df_name, "bar")
                success_count += 1
            except Exception:
                pass
    
    if success_count > 0:
        st.success(f"✅ Created charts for {success_count} DataFrames")
    else:
        st.warning("No charts could be created automatically")

def _clear_uploaded_files():
    """Clear all uploaded files."""
    st.session_state.uploaded_files.clear()
    temp_manager.cleanup()
    st.success("🗑️ All uploaded files cleared")
    st.rerun()

def _clear_dataframes():
    """Clear all loaded DataFrames."""
    st.session_state.loaded_dataframes.clear()
    st.success("🗑️ All DataFrames cleared")
    st.rerun()

def _get_server_session_info():
    """Get server session information."""
    try:
        client = ensure_mcp_connection()
        result = run_async_task(client.get_session_info())
        
        if result and result.get("success"):
            session_info = result.get("session_info", {})
            
            st.markdown("### 🖥️ Server Session Information")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Server DataFrames", len(session_info.get("dataframes", [])))
            
            with col2:
                st.metric("Server Memory Usage", session_info.get("memory_usage", "N/A"))
            
            with col3:
                st.metric("Session Duration", session_info.get("session_duration", "N/A"))
            
            # Detailed info
            if session_info.get("dataframes"):
                st.markdown("**Server DataFrames:**")
                server_df_data = []
                for df_name, df_details in session_info["dataframes"].items():
                    server_df_data.append({
                        "Name": df_name,
                        "Shape": f"{df_details.get('rows', 0)}×{df_details.get('columns', 0)}",
                        "Memory": df_details.get("memory_usage", "N/A")
                    })
                
                if server_df_data:
                    st.dataframe(pd.DataFrame(server_df_data), use_container_width=True)
        
        else:
            st.error("Failed to get server session info")
            
    except Exception as e:
        st.error(f"Error getting server info: {e}")

def _clear_server_session():
    """Clear server-side session data."""
    try:
        client = ensure_mcp_connection()
        result = run_async_task(client.clear_session())
        
        if result and result.get("success"):
            st.success("🧹 Server session cleared successfully")
            
            # Also clear local session state
            st.session_state.loaded_dataframes.clear()
            
        else:
            st.error("Failed to clear server session")
            
    except Exception as e:
        st.error(f"Error clearing server session: {e}")

if __name__ == "__main__":
    main()