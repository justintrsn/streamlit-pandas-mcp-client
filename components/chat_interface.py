"""Chat interface component for interacting with OpenAI agent."""

import streamlit as st
import openai
from typing import List, Dict, Any, Optional
import json
import time
from utils.security import get_secured_api_key, check_api_key_status
from utils.session_state import add_chat_message, clear_chat_history
from components.mcp_client import mcp_client, ensure_mcp_connection, run_async_task

class ChatInterface:
    """Handles chat functionality with OpenAI integration."""
    
    def __init__(self):
        self.model = "gpt-4"
        self.max_tokens = 1000
        self.temperature = 0.7
    
    def render_chat_interface(self):
        """Render the main chat interface."""
        st.subheader("💬 Data Analysis Assistant")
        
        # Check API key
        if not check_api_key_status():
            st.warning("🔑 Please configure your OpenAI API key to use the chat feature")
            return
        
        # Chat controls
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.markdown("**Ask questions about your data or request analysis operations**")
        
        with col2:
            if st.button("🧹 Clear Chat", key="clear_chat"):
                clear_chat_history()
                st.rerun()
        
        with col3:
            if st.button("💡 Help", key="chat_help"):
                self._show_help()
        
        # Chat history display
        self._render_chat_history()
        
        # Chat input
        self._render_chat_input()
    
    def _render_chat_history(self):
        """Render chat message history."""
        chat_container = st.container()
        
        with chat_container:
            if not st.session_state.chat_history:
                st.info("👋 Start a conversation! Ask questions about your data or request analysis operations.")
                return
            
            for i, message in enumerate(st.session_state.chat_history):
                if message["role"] == "user":
                    st.chat_message("user").write(message["content"])
                elif message["role"] == "assistant":
                    with st.chat_message("assistant"):
                        st.write(message["content"])
                        
                        # Display any metadata (charts, data, etc.)
                        metadata = message.get("metadata", {})
                        if metadata.get("chart_html"):
                            st.components.v1.html(metadata["chart_html"], height=500)
                        
                        if metadata.get("dataframe"):
                            st.dataframe(metadata["dataframe"], use_container_width=True)
    
    def _render_chat_input(self):
        """Render chat input and handle user messages."""
        # Chat input
        user_input = st.chat_input("Ask about your data or request analysis operations...")
        
        if user_input:
            # Add user message
            add_chat_message("user", user_input)
            
            # Generate response
            with st.spinner("🤖 Thinking..."):
                response = self._generate_response(user_input)
            
            if response:
                # Add assistant response
                add_chat_message("assistant", response["content"], response.get("metadata"))
                
                st.rerun()
    
    def _generate_response(self, user_input: str) -> Optional[Dict[str, Any]]:
        """Generate response using OpenAI and MCP operations."""
        try:
            api_key = get_secured_api_key()
            if not api_key:
                return {"content": "❌ OpenAI API key not configured"}
            
            # Set up OpenAI client
            client = openai.OpenAI(api_key=api_key)
            
            # Build context about current session
            context = self._build_session_context()
            
            # Create system prompt
            system_prompt = self._create_system_prompt(context)
            
            # Prepare messages
            messages = [
                {"role": "system", "content": system_prompt},
                *self._get_recent_chat_context(),
                {"role": "user", "content": user_input}
            ]
            
            # Call OpenAI
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            assistant_message = response.choices[0].message.content
            
            # Check if the response includes MCP operations
            mcp_result = self._execute_mcp_operations(assistant_message, user_input)
            
            return {
                "content": assistant_message,
                "metadata": mcp_result
            }
            
        except Exception as e:
            return {"content": f"❌ Error generating response: {e}"}
    
    def _build_session_context(self) -> Dict[str, Any]:
        """Build context about current session state."""
        return {
            "uploaded_files": list(st.session_state.uploaded_files.keys()),
            "loaded_dataframes": {
                name: {
                    "shape": (info.get("rows", 0), info.get("columns", 0)),
                    "columns": list(info.get("dtypes", {}).keys())
                }
                for name, info in st.session_state.loaded_dataframes.items()
            },
            "generated_charts": list(st.session_state.generated_charts.keys()),
            "mcp_connected": st.session_state.get("mcp_connected", False)
        }
    
    def _create_system_prompt(self, context: Dict[str, Any]) -> str:
        """Create system prompt with session context."""
        return f"""You are a data analysis assistant with access to a pandas MCP server. You can help users analyze data, create visualizations, and answer questions about their datasets.

Current Session Context:
- Uploaded files: {context['uploaded_files']}
- Loaded DataFrames: {json.dumps(context['loaded_dataframes'], indent=2)}
- Generated charts: {context['generated_charts']}
- MCP server connected: {context['mcp_connected']}

You can:
1. Answer questions about the loaded data
2. Suggest data analysis operations
3. Recommend chart types and visualizations
4. Help with pandas operations
5. Provide insights about data quality and patterns

When users ask for specific operations (creating charts, data analysis, etc.), provide clear instructions and suggest specific actions they can take in the interface.

Be helpful, concise, and data-focused. If users ask for operations that require MCP server calls, explain what they need to do in the interface to accomplish their goal.
"""
    
    def _get_recent_chat_context(self) -> List[Dict[str, str]]:
        """Get recent chat messages for context (last 10 messages)."""
        recent_messages = st.session_state.chat_history[-10:] if st.session_state.chat_history else []
        
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in recent_messages
            if msg["role"] in ["user", "assistant"]
        ]
    
    def _execute_mcp_operations(self, assistant_message: str, user_input: str) -> Dict[str, Any]:
        """Check if response should trigger MCP operations and execute them."""
        metadata = {}
        
        # Simple keyword-based operation detection
        # In a more sophisticated version, this could use function calling
        
        try:
            # Check for chart creation requests
            if any(word in user_input.lower() for word in ["chart", "graph", "plot", "visualize"]):
                # Try to auto-suggest charts for available DataFrames
                if st.session_state.loaded_dataframes:
                    df_name = list(st.session_state.loaded_dataframes.keys())[0]
                    client = ensure_mcp_connection()
                    suggestions = run_async_task(client.suggest_charts(df_name))
                    
                    if suggestions and suggestions.get("success"):
                        metadata["chart_suggestions"] = suggestions.get("suggestions", [])
            
            # Check for data info requests
            if any(word in user_input.lower() for word in ["info", "describe", "summary", "overview"]):
                if st.session_state.loaded_dataframes:
                    df_name = list(st.session_state.loaded_dataframes.keys())[0]
                    client = ensure_mcp_connection()
                    info = run_async_task(client.get_dataframe_info(df_name))
                    
                    if info and info.get("success"):
                        metadata["dataframe_info"] = info.get("info", {})
        
        except Exception as e:
            metadata["error"] = str(e)
        
        return metadata
    
    def _show_help(self):
        """Display help information for chat interface."""
        with st.expander("💡 Chat Help", expanded=True):
            st.markdown("""
            **What you can ask:**
            
            🔍 **Data Questions:**
            - "What columns are in my dataset?"
            - "Show me summary statistics"
            - "Are there any missing values?"
            - "What's the data type of each column?"
            
            📊 **Visualization Requests:**
            - "Create a bar chart of sales by month"
            - "Show correlation between variables"
            - "Make a scatter plot of price vs. quantity"
            - "Suggest the best chart for my data"
            
            🔧 **Analysis Operations:**
            - "Find outliers in the data"
            - "Calculate correlation matrix"
            - "Group data by category"
            - "Filter data where value > 100"
            
            💡 **Tips:**
            - Be specific about column names and operations
            - Ask for step-by-step guidance for complex tasks
            - Request explanations of analysis results
            - Ask for recommendations on next steps
            """)
    
    def render_suggested_questions(self):
        """Render suggested questions based on loaded data."""
        if not st.session_state.loaded_dataframes:
            return
        
        st.markdown("### 💡 Suggested Questions")
        
        suggestions = [
            "What does my data look like?",
            "Show me summary statistics",
            "Are there any missing values I should know about?",
            "What charts would work well with this data?",
            "Find any interesting patterns or outliers"
        ]
        
        col1, col2 = st.columns(2)
        
        for i, suggestion in enumerate(suggestions):
            with col1 if i % 2 == 0 else col2:
                if st.button(suggestion, key=f"suggestion_{i}"):
                    # Add as user message and generate response
                    add_chat_message("user", suggestion)
                    
                    with st.spinner("🤖 Analyzing..."):
                        response = self._generate_response(suggestion)
                    
                    if response:
                        add_chat_message("assistant", response["content"], response.get("metadata"))
                    
                    st.rerun()

# Global instance
chat_interface = ChatInterface()