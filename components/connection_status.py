"""Connection status component for pandas-chat-app"""

import streamlit as st
from typing import Optional, List, Dict, Any
from datetime import datetime
from config import get_settings
from utils import get_logger, run_async_with_timeout


def render_connection_status():
    """Render the top connection status bar"""
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown("Upload files and analyze with natural language")
        
    with col2:
        render_connection_indicator()
        
    with col3:
        render_connect_button()


def render_connection_indicator():
    """Render MCP connection status indicator"""
    
    if st.session_state.get('mcp_tools'):
        tools_count = len(st.session_state.mcp_tools)
        st.success(f"🟢 Connected ({tools_count} tools)")
        
        # Show last connection time if available
        if st.session_state.get('mcp_connected_at'):
            connected_at = datetime.fromisoformat(st.session_state.mcp_connected_at)
            duration = (datetime.now() - connected_at).seconds
            if duration < 60:
                st.caption(f"Connected {duration}s ago")
            elif duration < 3600:
                st.caption(f"Connected {duration//60}m ago")
            else:
                st.caption(f"Connected {duration//3600}h ago")
    else:
        st.warning("🔴 Not connected")
        st.caption("Click Connect to start")


def render_connect_button():
    """Render the connect/reconnect button"""
    
    settings = get_settings()
    logger = get_logger()
    
    # Button text based on connection state
    is_connected = bool(st.session_state.get('mcp_tools'))
    button_text = "🔄 Reconnect" if is_connected else "🔄 Connect"
    button_help = "Reconnect to MCP server" if is_connected else "Connect to MCP server"
    
    if st.button(button_text, help=button_help):
        connect_to_mcp_server()


def connect_to_mcp_server():
    """Connect to the MCP server and retrieve tools"""
    
    settings = get_settings()
    logger = get_logger()
    
    with st.spinner("Connecting to MCP server..."):
        try:
            # Import here to avoid circular imports
            from mcp import ClientSession
            from mcp.client.sse import sse_client
            
            async def get_tools():
                async with sse_client(url=settings.mcp_sse_url) as streams:
                    async with ClientSession(*streams) as session:
                        await session.initialize()
                        response = await session.list_tools()
                        
                        tools = []
                        for tool in response.tools:
                            tools.append({
                                "type": "function",
                                "function": {
                                    "name": tool.name,
                                    "description": tool.description or f"Tool: {tool.name}",
                                    "parameters": tool.inputSchema if tool.inputSchema else {
                                        "type": "object",
                                        "properties": {},
                                        "required": []
                                    }
                                }
                            })
                        return tools
            
            # Connect with timeout
            tools = run_async_with_timeout(get_tools(), timeout=settings.mcp_timeout)
            
            if tools:
                # Store tools and connection info
                st.session_state.mcp_tools = tools
                st.session_state.mcp_connected_at = datetime.now().isoformat()
                
                # Log connection
                logger.log("info", f"Connected to MCP server: {len(tools)} tools available")
                
                # Show success message with tool categories
                tool_categories = categorize_tools(tools)
                
                st.success(f"✅ Connected successfully! {len(tools)} tools available.")
                
                # Show tool breakdown
                with st.expander("Available Tools", expanded=False):
                    for category, tool_names in tool_categories.items():
                        st.write(f"**{category}** ({len(tool_names)} tools)")
                        for name in tool_names[:5]:  # Show first 5
                            st.caption(f"  • {name}")
                        if len(tool_names) > 5:
                            st.caption(f"  ... and {len(tool_names)-5} more")
            else:
                st.error("No tools found on MCP server")
                logger.log("error", "No tools returned from MCP server")
                
        except TimeoutError:
            st.error(f"Connection timed out after {settings.mcp_timeout} seconds")
            logger.log("error", f"MCP connection timeout: {settings.mcp_sse_url}")
            
        except Exception as e:
            st.error(f"Failed to connect: {str(e)}")
            logger.log("error", f"MCP connection failed: {str(e)}")
            
            # Show troubleshooting tips
            with st.expander("Troubleshooting Tips"):
                st.markdown("""
                1. **Check server is running**: Ensure the MCP server is started
                2. **Verify URL**: Check the MCP_SSE_URL in settings
                3. **Network issues**: Ensure no firewall blocking the connection
                4. **Server logs**: Check server logs for errors
                """)


def categorize_tools(tools: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Categorize tools by their function"""
    
    categories = {
        "Data Loading": [],
        "Data Analysis": [],
        "Visualization": [],
        "File Management": [],
        "Session Management": [],
        "Other": []
    }
    
    for tool in tools:
        name = tool["function"]["name"]
        
        # Categorize based on name patterns
        if any(x in name for x in ["load", "read", "upload", "preview"]):
            categories["Data Loading"].append(name)
        elif any(x in name for x in ["pandas", "validate", "execution", "metadata"]):
            categories["Data Analysis"].append(name)
        elif any(x in name for x in ["chart", "visualization", "plot", "graph", "heatmap"]):
            categories["Visualization"].append(name)
        elif any(x in name for x in ["file", "temp", "format"]):
            categories["File Management"].append(name)
        elif any(x in name for x in ["session", "clear", "info"]):
            categories["Session Management"].append(name)
        else:
            categories["Other"].append(name)
            
    # Remove empty categories
    return {k: v for k, v in categories.items() if v}


def check_connection_health() -> Dict[str, Any]:
    """Check health of MCP connection"""
    
    if not st.session_state.get('mcp_tools'):
        return {
            "connected": False,
            "status": "Not connected",
            "tools_count": 0
        }
        
    # Calculate connection duration
    connected_at = st.session_state.get('mcp_connected_at')
    if connected_at:
        duration = (datetime.now() - datetime.fromisoformat(connected_at)).seconds
    else:
        duration = 0
        
    return {
        "connected": True,
        "status": "Connected",
        "tools_count": len(st.session_state.mcp_tools),
        "connection_duration_seconds": duration,
        "connected_at": connected_at
    }


def display_connection_details():
    """Display detailed connection information"""
    
    health = check_connection_health()
    
    if not health["connected"]:
        st.warning("Not connected to MCP server")
        return
        
    st.success(f"Connected to MCP server")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Tools Available", health["tools_count"])
        
    with col2:
        duration = health["connection_duration_seconds"]
        if duration < 60:
            st.metric("Connected For", f"{duration}s")
        elif duration < 3600:
            st.metric("Connected For", f"{duration//60}m")
        else:
            st.metric("Connected For", f"{duration//3600}h")
            
    with col3:
        settings = get_settings()
        st.metric("Server", settings.mcp_sse_url.split("://")[1].split("/")[0])
        
    # Tool list
    if st.session_state.get('mcp_tools'):
        with st.expander("Tool Details"):
            tool_categories = categorize_tools(st.session_state.mcp_tools)
            
            for category, tools in tool_categories.items():
                st.write(f"**{category}**")
                for tool_name in tools:
                    # Find full tool info
                    tool_info = next(
                        (t for t in st.session_state.mcp_tools 
                         if t["function"]["name"] == tool_name),
                        None
                    )
                    if tool_info:
                        desc = tool_info["function"].get("description", "No description")
                        st.caption(f"• `{tool_name}`: {desc[:100]}...")