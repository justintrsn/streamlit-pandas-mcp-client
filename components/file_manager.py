"""File management component for pandas-chat-app"""

import streamlit as st
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from config import get_settings
from utils import get_logger


def render_file_manager():
    """Render the file upload and management interface"""
    
    st.subheader("📁 Files")
    
    # File uploader
    render_file_uploader()
    
    # Display uploaded files
    render_uploaded_files()
    
    # File statistics
    if st.session_state.get('uploaded_files'):
        render_file_stats()


def render_file_uploader():
    """Render file upload widget"""
    
    settings = get_settings()
    logger = get_logger()
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Upload data files",
        type=settings.allowed_file_types,
        accept_multiple_files=True,
        help=f"Max size: {settings.max_file_size_mb}MB per file"
    )
    
    if uploaded_files:
        for file in uploaded_files:
            # Check if already uploaded
            if file.name not in st.session_state.get('uploaded_files', {}):
                # Check file size
                file_size_mb = file.size / (1024 * 1024)
                
                if file_size_mb > settings.max_file_size_mb:
                    st.error(f"❌ {file.name} exceeds {settings.max_file_size_mb}MB limit")
                    logger.log_file_operation(
                        "upload_failed",
                        file.name,
                        file.size,
                        success=False,
                        error=f"File too large: {file_size_mb:.2f}MB"
                    )
                    continue
                    
                try:
                    # Read file content
                    content = file.getvalue().decode('utf-8', errors='ignore')
                    
                    # Store in session state
                    if 'uploaded_files' not in st.session_state:
                        st.session_state.uploaded_files = {}
                    if 'files_content' not in st.session_state:
                        st.session_state.files_content = {}
                        
                    st.session_state.uploaded_files[file.name] = {
                        'size': file.size,
                        'type': file.type,
                        'upload_time': datetime.now().isoformat()
                    }
                    st.session_state.files_content[file.name] = content
                    
                    st.success(f"✅ {file.name} uploaded successfully")
                    
                    # Log upload
                    logger.log_file_operation(
                        "upload",
                        file.name,
                        file.size,
                        success=True
                    )
                    
                except Exception as e:
                    st.error(f"❌ Failed to upload {file.name}: {str(e)}")
                    logger.log_file_operation(
                        "upload_failed",
                        file.name,
                        file.size,
                        success=False,
                        error=str(e)
                    )


def render_uploaded_files():
    """Display list of uploaded files"""
    
    if not st.session_state.get('uploaded_files'):
        st.info("No files uploaded yet. Upload CSV, Excel, JSON, or Parquet files to analyze.")
        return
        
    st.markdown("**Uploaded Files:**")
    
    for filename, info in st.session_state.uploaded_files.items():
        render_file_item(filename, info)


def render_file_item(filename: str, info: Dict):
    """Render a single file item with actions"""
    
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        # File icon based on extension
        ext = Path(filename).suffix.lower()
        icon = get_file_icon(ext)
        
        # Display filename with size
        size_kb = info['size'] / 1024
        st.write(f"{icon} **{filename}** ({size_kb:.1f} KB)")
        
    with col2:
        # Preview button
        if st.button("👁️", key=f"preview_{filename}", help="Preview file"):
            preview_file(filename)
            
    with col3:
        # Remove button
        if st.button("🗑️", key=f"remove_{filename}", help="Remove file"):
            remove_file(filename)


def get_file_icon(extension: str) -> str:
    """Get icon for file type"""
    
    icons = {
        '.csv': '📊',
        '.tsv': '📊',
        '.xlsx': '📈',
        '.xls': '📈',
        '.json': '📄',
        '.parquet': '📦'
    }
    
    return icons.get(extension, '📄')


def preview_file(filename: str):
    """Show preview of file content"""
    
    if filename not in st.session_state.get('files_content', {}):
        st.error("File content not found")
        return
        
    content = st.session_state.files_content[filename]
    
    # Show in expander
    with st.expander(f"Preview: {filename}", expanded=True):
        # Truncate for display
        lines = content.split('\n')[:20]
        total_lines = len(content.split('\n'))
        if total_lines > 20:
            lines.append("... (truncated)")
            
        st.code('\n'.join(lines), language='text')
        
        # File info
        st.caption(f"Total lines: {total_lines}")
        st.caption(f"Total characters: {len(content)}")


def remove_file(filename: str):
    """Remove a file from session state"""
    
    logger = get_logger()
    
    if filename in st.session_state.get('uploaded_files', {}):
        del st.session_state.uploaded_files[filename]
        
    if filename in st.session_state.get('files_content', {}):
        del st.session_state.files_content[filename]
        
    st.success(f"Removed {filename}")
    
    # Log removal
    logger.log_file_operation("remove", filename, success=True)
    
    st.rerun()


def render_file_stats():
    """Render statistics about uploaded files"""
    
    with st.expander("📊 File Statistics"):
        files = st.session_state.get('uploaded_files', {})
        
        # Calculate stats
        total_files = len(files)
        total_size = sum(f['size'] for f in files.values())
        total_size_mb = total_size / (1024 * 1024)
        
        # File types
        file_types = {}
        for filename in files.keys():
            ext = Path(filename).suffix.lower()
            file_types[ext] = file_types.get(ext, 0) + 1
            
        # Display metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Files", total_files)
            
        with col2:
            st.metric("Total Size", f"{total_size_mb:.2f} MB")
            
        with col3:
            st.metric("File Types", len(file_types))
            
        # File type breakdown
        if file_types:
            st.caption("File Types:")
            for ext, count in file_types.items():
                st.caption(f"  • {ext}: {count}")
                
        # Recent uploads
        if files:
            st.caption("Recent Uploads:")
            sorted_files = sorted(
                files.items(),
                key=lambda x: x[1].get('upload_time', ''),
                reverse=True
            )[:5]
            
            for filename, info in sorted_files:
                upload_time = info.get('upload_time', '')
                if upload_time:
                    dt = datetime.fromisoformat(upload_time)
                    time_str = dt.strftime("%H:%M:%S")
                    st.caption(f"  • {filename} - {time_str}")


def get_files_for_prompt() -> str:
    """Get formatted list of files for system prompt"""
    
    if not st.session_state.get('uploaded_files'):
        return ""
        
    files = list(st.session_state.uploaded_files.keys())
    return ", ".join(files)


def clear_all_files():
    """Clear all uploaded files"""
    
    logger = get_logger()
    
    count = len(st.session_state.get('uploaded_files', {}))
    
    st.session_state.uploaded_files = {}
    st.session_state.files_content = {}
    
    logger.log("info", f"Cleared {count} uploaded files")
    
    return count