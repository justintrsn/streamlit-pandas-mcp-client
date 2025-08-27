"""Security utilities for API key management and validation."""

import streamlit as st
import re
from typing import Optional, Tuple

def validate_openai_api_key(api_key: str) -> Tuple[bool, str]:
    """
    Validate OpenAI API key format.
    
    Returns:
        Tuple of (is_valid, message)
    """
    if not api_key:
        return False, "API key is required"
    
    if not api_key.startswith("sk-"):
        return False, "OpenAI API keys should start with 'sk-'"
    
    # Basic length check (OpenAI keys are typically around 51 characters)
    if len(api_key) < 40:
        return False, "API key appears to be too short"
    
    # Check for valid characters (alphanumeric + hyphens)
    if not re.match(r'^sk-[a-zA-Z0-9\-_]+$', api_key):
        return False, "API key contains invalid characters"
    
    return True, "API key format is valid"

def mask_api_key(api_key: str) -> str:
    """
    Mask API key for display purposes.
    Shows first 7 characters and last 4 characters.
    """
    if not api_key or len(api_key) < 11:
        return "***"
    
    return f"{api_key[:7]}...{api_key[-4:]}"

def secure_api_key_input() -> Optional[str]:
    """
    Create secure API key input widget with validation.
    
    Returns:
        Valid API key or None
    """
    st.subheader("🔐 OpenAI API Configuration")
    
    # Check if we already have a key
    current_key = st.session_state.get("openai_api_key", "")
    
    if current_key:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.success(f"✅ API Key configured: {mask_api_key(current_key)}")
        with col2:
            if st.button("🗑️ Clear Key", key="clear_api_key"):
                st.session_state.openai_api_key = ""
                st.rerun()
        return current_key
    
    # API key input
    api_key = st.text_input(
        "OpenAI API Key",
        type="password",
        placeholder="sk-...",
        help="Enter your OpenAI API key. This will be securely stored in your session.",
        key="api_key_input"
    )
    
    if api_key:
        is_valid, message = validate_openai_api_key(api_key)
        
        if is_valid:
            if st.button("💾 Save API Key", key="save_api_key"):
                st.session_state.openai_api_key = api_key
                st.success("✅ API key saved successfully!")
                st.rerun()
        else:
            st.error(f"❌ Invalid API key: {message}")
    
    if not api_key:
        st.info("🔑 Please enter your OpenAI API key to enable chat functionality.")
        st.markdown("""
        **How to get an API key:**
        1. Go to [OpenAI Platform](https://platform.openai.com/)
        2. Sign in to your account
        3. Navigate to API Keys section
        4. Create a new secret key
        5. Copy and paste it above
        
        💡 Your API key is only stored in your browser session and never transmitted elsewhere.
        """)
    
    return None

def check_api_key_status() -> bool:
    """Check if a valid API key is configured."""
    api_key = st.session_state.get("openai_api_key", "")
    if not api_key:
        return False
    
    is_valid, _ = validate_openai_api_key(api_key)
    return is_valid

def get_secured_api_key() -> Optional[str]:
    """Get the API key if it's valid, otherwise None."""
    if check_api_key_status():
        return st.session_state.openai_api_key
    return None

def display_security_warning():
    """Display security best practices."""
    with st.expander("🛡️ Security Information"):
        st.markdown("""
        **Your data security:**
        - API keys are stored only in your browser session
        - Files are temporarily stored and cleared when you close the app
        - No data is permanently stored on our servers
        - MCP server connections use standard HTTP protocols
        
        **Best practices:**
        - Never share your API key with others
        - Use API keys with minimal required permissions
        - Monitor your OpenAI usage regularly
        - Clear your session when using shared computers
        """)

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal attacks."""
    # Remove path separators and other potentially dangerous characters
    safe_name = re.sub(r'[^\w\-_\.]', '_', filename)
    
    # Ensure it doesn't start with dots or hyphens
    safe_name = re.sub(r'^[\.\-]+', '', safe_name)
    
    # Limit length
    if len(safe_name) > 100:
        name_part, ext = safe_name.rsplit('.', 1) if '.' in safe_name else (safe_name, '')
        safe_name = name_part[:95] + ('.' + ext if ext else '')
    
    return safe_name or "unnamed_file"