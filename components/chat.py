"""Chat interface component for pandas-chat-app"""

import streamlit as st
from typing import List, Dict, Any
from datetime import datetime
from config import get_settings, get_prompt_manager
from utils import get_logger, ChartHandler


def render_chat_interface():
    """Render the main chat interface"""
    
    # Chat header
    render_chat_header()
    
    # Message display area
    render_messages()
    
    # Chat input is handled at app level due to Streamlit constraints
    # Return True if ready for input, False otherwise
    return is_ready_for_input()


def render_chat_header():
    """Render chat header with context info"""
    settings = get_settings()
    
    # Show context information
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        st.subheader("💬 Chat")
        
    with col2:
        # Message count
        if st.session_state.get('messages'):
            st.metric("Messages", len(st.session_state.messages))
            
    with col3:
        # Model indicator
        st.caption(f"Model: {settings.openai_model}")


def render_messages():
    """Render chat messages"""
    
    if not st.session_state.get('messages'):
        # Show welcome message
        render_welcome_message()
        return
        
    # Display messages
    for msg_idx, message in enumerate(st.session_state.messages):
        if message["role"] in ["user", "assistant"]:
            render_message(message, msg_idx)


def render_message(message: Dict[str, Any], index: int):
    """Render a single message"""
    
    with st.chat_message(message["role"]):
        # Display content
        st.write(message["content"])
        
        # Add metadata/actions for assistant messages
        if message["role"] == "assistant":
            render_message_actions(message, index)
            
        # Check if this message has associated charts
        if "chart_indices" in message:
            render_message_charts(message["chart_indices"])


def render_message_actions(message: Dict[str, Any], index: int):
    """Render actions for a message (copy, regenerate, etc.)"""
    
    # Create small action buttons
    col1, col2, col3, col4 = st.columns([1, 1, 1, 6])
    
    with col1:
        if st.button("📋", key=f"copy_{index}", help="Copy response"):
            st.write("")  # Placeholder for copy functionality
            # In real app, would use clipboard API
            
    with col2:
        if st.button("🔄", key=f"regen_{index}", help="Regenerate response"):
            st.session_state.regenerate_index = index
            
    with col3:
        if st.button("📊", key=f"chart_{index}", help="View charts from this response"):
            if "chart_indices" in message:
                st.session_state.show_charts = message["chart_indices"]


def render_message_charts(chart_indices: List[int]):
    """Render charts associated with a message"""
    
    chart_handler = ChartHandler()
    
    if not st.session_state.get('generated_charts'):
        return
        
    for idx in chart_indices:
        if idx < len(st.session_state.generated_charts):
            chart = st.session_state.generated_charts[idx]
            
            # Display inline chart preview
            with st.expander(f"📊 {chart['chart_type']} - View Chart", expanded=False):
                chart_handler.display_chart(
                    chart['html'],
                    height=400,
                    key=f"msg_chart_{idx}"
                )


def render_welcome_message():
    """Render welcome message for new chat"""
    
    settings = get_settings()
    
    st.markdown("""
    ### 👋 Welcome to Pandas Data Chat!
    
    I'm your AI data analysis assistant powered by MCP tools. I can help you:
    
    - 📊 **Analyze data** - Load CSV, Excel, JSON, or Parquet files
    - 📈 **Create visualizations** - Generate interactive charts and graphs
    - 🔍 **Explore datasets** - Run pandas operations and statistical analysis
    - 🧹 **Clean data** - Handle missing values, duplicates, and transformations
    
    **Getting Started:**
    1. Upload your data files using the file manager on the right
    2. Ask me questions about your data in natural language
    3. I'll use MCP tools to analyze and visualize your data
    
    **Example queries:**
    - "Load sales.csv and show me a summary"
    - "Create a bar chart of revenue by category"
    - "Find correlations in the dataset"
    - "Clean the data and remove duplicates"
    """)
    
    # Show connection status
    if not st.session_state.get('mcp_tools'):
        st.warning("⚠️ MCP server not connected. Click 'Connect' in the top bar to start.")
    else:
        st.success(f"✅ Ready to analyze! {len(st.session_state.mcp_tools)} tools available.")


def is_ready_for_input() -> bool:
    """Check if chat is ready for user input"""
    
    # Check API key
    if not st.session_state.get('openai_api_key'):
        st.warning("⚠️ Please enter your OpenAI API key in the sidebar to start chatting.")
        return False
        
    # Check MCP connection
    if not st.session_state.get('mcp_tools'):
        st.warning("⚠️ Please connect to the MCP server using the Connect button above.")
        return False
        
    return True


def prepare_system_message(file_contents: Dict[str, str]) -> str:
    """Prepare the system message with context"""
    
    prompt_manager = get_prompt_manager()
    settings = get_settings()
    
    # Format files info
    files_info = ""
    if file_contents:
        files_info = ", ".join(file_contents.keys())
        
    # Get formatted prompt
    system_prompt = prompt_manager.get_formatted_prompt(
        use_custom=settings.use_custom_prompt,
        files_info=files_info,
        additional_context={
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "model": settings.openai_model,
            "session_files": len(file_contents)
        }
    )
    
    return system_prompt


def prepare_messages_for_api(
    system_message: str,
    context_window: int = 6
) -> List[Dict[str, str]]:
    """Prepare messages for API call with context window"""
    
    messages = [{"role": "system", "content": system_message}]
    
    # Add recent messages (with context window)
    if st.session_state.get('messages'):
        recent_messages = st.session_state.messages[-context_window:]
        for msg in recent_messages:
            if msg["role"] in ["user", "assistant"]:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
                
    return messages


def add_user_message(content: str):
    """Add a user message to the chat"""
    
    st.session_state.messages.append({
        "role": "user",
        "content": content,
        "timestamp": datetime.now().isoformat()
    })
    
    # Log
    logger = get_logger()
    logger.log("info", f"User message: {content[:100]}...")


def add_assistant_message(content: str, chart_indices: List[int] = None):
    """Add an assistant message to the chat"""
    
    message = {
        "role": "assistant",
        "content": content,
        "timestamp": datetime.now().isoformat()
    }
    
    if chart_indices:
        message["chart_indices"] = chart_indices
        
    st.session_state.messages.append(message)
    
    # Log
    logger = get_logger()
    logger.log("info", f"Assistant response: {content[:100]}...")
    
    # Trim messages if exceeding limit
    settings = get_settings()
    if len(st.session_state.messages) > settings.message_history_limit:
        # Keep system prompts and recent messages
        st.session_state.messages = st.session_state.messages[-settings.message_history_limit:]